// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
import path from "node:path";
import type { AsyncSubscription, Event } from "@parcel/watcher";
import watcher from "@parcel/watcher";
import { collectionName, projectIdFromPath } from "../config.js";
import { EXTENSION_LANGUAGE_MAP, SPECIAL_FILES, SUPPORTED_EXTENSIONS } from "../constants.js";
import { invalidateGraphCache } from "./code-graph.js";
import { createIgnoreFilter, shouldIgnore } from "./ignore.js";
import { isIndexingInProgress, updateProjectIndex } from "./indexer.js";
import { acquireProjectLock, isProjectLocked, releaseProjectLock } from "./lock.js";
import { logger } from "./logger.js";
import { getCollectionInfo, getProjectMetadata } from "./qdrant.js";

/** Active subscriptions per project path */
const subscriptions = new Map<string, AsyncSubscription>();

/** Debounce timers per project */
const debounceTimers = new Map<string, NodeJS.Timeout>();

const DEBOUNCE_MS = 2000;

/** Maximum consecutive watcher errors before auto-stopping */
const MAX_WATCHER_ERRORS = 10;
const watcherErrorCounts = new Map<string, number>();

/**
 * Cache of projects confirmed to be watched by another process.
 * Maps resolvedPath → timestamp of last confirmation.
 * Prevents ensureWatcherStarted from retrying the lock on every tool call.
 */
const externalWatchCache = new Map<string, number>();

/** How long to cache the "another process is watching" result before rechecking */
const EXTERNAL_WATCH_CACHE_TTL_MS = 60_000;

function isIndexableFile(filePath: string): boolean {
  const fileName = path.basename(filePath);
  if (SPECIAL_FILES.has(fileName)) return true;
  const ext = path.extname(filePath).toLowerCase();
  // EXTENSION_LANGUAGE_MAP extensions are real source files, so edits to them
  // must trigger an incremental update like any other supported file.
  return SUPPORTED_EXTENSIONS.has(ext) || EXTENSION_LANGUAGE_MAP.has(ext);
}

/**
 * Build ignore globs for @parcel/watcher.
 * These are directory names that should be excluded from native OS watching.
 */
function buildIgnoreGlobs(): string[] {
  return [
    "node_modules",
    ".git",
    ".svn",
    ".hg",
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".tox",
    "target",
    ".gradle",
    ".idea",
    ".vscode",
    ".vs",
    "coverage",
    ".nyc_output",
    ".cache",
    ".parcel-cache",
    ".turbo",
    "vendor",
  ];
}

/**
 * Start watching a project directory for file changes.
 * Uses @parcel/watcher for native OS-level file watching (FSEvents on macOS,
 * ReadDirectoryChangesW on Windows, inotify on Linux). Creates a single native
 * subscription for the entire directory tree — no per-file enumeration.
 *
 * On change, triggers an incremental index update (debounced).
 */
export async function startWatching(
  projectPath: string,
  onProgress?: (message: string) => void,
): Promise<boolean> {
  const resolvedPath = path.resolve(projectPath);

  if (subscriptions.has(resolvedPath)) {
    onProgress?.(`Already watching ${resolvedPath}`);
    return true;
  }

  // Acquire cross-process lock for watching
  const lockAcquired = await acquireProjectLock(resolvedPath, "watch");
  if (!lockAcquired) {
    logger.info("Another process is already watching this project, skipping", { projectPath: resolvedPath });
    onProgress?.(`Another process is already watching ${resolvedPath}, skipping`);
    return false;
  }

  const ig = createIgnoreFilter(resolvedPath);
  const ignoreGlobs = buildIgnoreGlobs();

  // Reset error count
  watcherErrorCounts.set(resolvedPath, 0);

  const scheduleUpdate = () => {
    const existing = debounceTimers.get(resolvedPath);
    if (existing) clearTimeout(existing);

    debounceTimers.set(
      resolvedPath,
      setTimeout(async () => {
        debounceTimers.delete(resolvedPath);
        try {
          onProgress?.(`Detected changes, updating index for ${resolvedPath}...`);

          // Invalidate the code graph cache so it will be rebuilt
          invalidateGraphCache(resolvedPath);

          const result = await updateProjectIndex(resolvedPath, onProgress);
          onProgress?.(
            `Auto-update: ${result.added} added, ${result.updated} updated, ${result.removed} removed`,
          );

          // Note: code graph rebuild is now handled inside updateProjectIndex itself
        } catch (err) {
          // Graceful degradation: log but don't crash the watcher
          const message = err instanceof Error ? err.message : String(err);
          logger.error("Watch auto-update failed", { projectPath: resolvedPath, error: message });
          onProgress?.(`Auto-update failed (will retry on next change): ${message}`);

          // If Qdrant is unreachable, don't spam retries — back off
          if (message.includes("ECONNREFUSED") || message.includes("fetch failed") || message.includes("Request Timeout")) {
            logger.warn("Infrastructure appears down, pausing watcher updates for 30s", { projectPath: resolvedPath });
            await new Promise((resolve) => setTimeout(resolve, 30_000));
          }
        }
      }, DEBOUNCE_MS),
    );
  };

  try {
    const subscription = await watcher.subscribe(
      resolvedPath,
      (err: Error | null, events: Event[]) => {
        if (err) {
          const count = (watcherErrorCounts.get(resolvedPath) ?? 0) + 1;
          watcherErrorCounts.set(resolvedPath, count);

          // Throttle error logging: first 3, then every 100th
          if (count <= 3 || count % 100 === 0) {
            logger.error("File watcher error", {
              projectPath: resolvedPath,
              error: err.message,
              errorCount: count,
            });
          }

          if (count >= MAX_WATCHER_ERRORS) {
            logger.error("Too many watcher errors, stopping watcher", {
              projectPath: resolvedPath,
              totalErrors: count,
            });
            // Stop asynchronously to avoid re-entrancy issues
            stopWatching(resolvedPath).catch(() => { /* already stopping */ });
          }
          return;
        }

        // Reset error count on successful event delivery
        watcherErrorCounts.set(resolvedPath, 0);

        // Filter events: only indexable files that pass ignore rules
        const relevantEvents = events.filter((event) => {
          if (!isIndexableFile(event.path)) return false;
          const relative = path.relative(resolvedPath, event.path);
          if (!relative || relative.startsWith("..")) return false;
          return !shouldIgnore(ig, relative);
        });

        if (relevantEvents.length > 0) {
          scheduleUpdate();
        }
      },
      {
        ignore: ignoreGlobs,
      },
    );

    subscriptions.set(resolvedPath, subscription);
    externalWatchCache.delete(resolvedPath);
    onProgress?.(`Started watching ${resolvedPath}`);
    logger.info("File watcher started", { projectPath: resolvedPath });
    return true;
  } catch (err) {
    // Release lock if subscription failed
    await releaseProjectLock(resolvedPath, "watch");
    const message = err instanceof Error ? err.message : String(err);
    logger.error("Failed to start file watcher", { projectPath: resolvedPath, error: message });
    onProgress?.(`Failed to start watching ${resolvedPath}: ${message}`);
    return false;
  }
}

/** Stop watching a project directory */
export async function stopWatching(projectPath: string): Promise<void> {
  const resolvedPath = path.resolve(projectPath);
  const subscription = subscriptions.get(resolvedPath);

  if (subscription) {
    await subscription.unsubscribe();
    subscriptions.delete(resolvedPath);
    watcherErrorCounts.delete(resolvedPath);

    const timer = debounceTimers.get(resolvedPath);
    if (timer) {
      clearTimeout(timer);
      debounceTimers.delete(resolvedPath);
    }

    await releaseProjectLock(resolvedPath, "watch");
    logger.info("File watcher stopped", { projectPath: resolvedPath });
  }
}

/** Stop all active watchers */
export async function stopAllWatchers(): Promise<void> {
  for (const [projectPath] of subscriptions) {
    await stopWatching(projectPath);
  }
}

/** Check if a specific project is being watched */
export function isWatching(projectPath: string): boolean {
  return subscriptions.has(path.resolve(projectPath));
}

/** Get list of currently watched project paths */
export function getWatchedProjects(): string[] {
  return Array.from(subscriptions.keys());
}

/**
 * Check if a project is being watched by any process (this one or another).
 * First checks the in-memory subscriptions map (fast, synchronous), then falls
 * back to checking the cross-process file lock for the "watch" operation.
 */
export async function isWatchedByAnyProcess(projectPath: string): Promise<boolean> {
  const resolvedPath = path.resolve(projectPath);
  if (subscriptions.has(resolvedPath)) return true;
  return isProjectLocked(resolvedPath, "watch");
}

/** Clear the external watch cache. Exported for testing. */
export function clearExternalWatchCache(): void {
  externalWatchCache.clear();
}

/**
 * Ensure the file watcher is running for a project if conditions are met.
 * This is a fire-and-forget, non-blocking, non-fatal helper called by tools
 * (search, status, update, graph) to auto-activate watching on first interaction.
 *
 * Conditions:
 * 1. Not already watching this project
 * 2. No full indexing or incremental update currently in progress
 * 3. A fully indexed and COMPLETED collection exists in Qdrant
 *
 * If any condition fails (including incomplete/interrupted indexes), this
 * silently returns without starting the watcher.
 */
export function ensureWatcherStarted(projectPath: string): void {
  const resolvedPath = path.resolve(projectPath);

  // Already watching in this process — nothing to do
  if (subscriptions.has(resolvedPath)) return;

  // Skip if we recently confirmed another process is watching (avoids retrying on every tool call)
  const cachedAt = externalWatchCache.get(resolvedPath);
  if (cachedAt && Date.now() - cachedAt < EXTERNAL_WATCH_CACHE_TTL_MS) return;

  // Indexing in progress — don't interfere with ongoing operations
  if (isIndexingInProgress(resolvedPath)) return;

  // Fire-and-forget: check collection exists and index is complete, then start watcher
  const projectId = projectIdFromPath(resolvedPath);
  const collection = collectionName(projectId);

  getCollectionInfo(collection)
    .then(async (info) => {
      if (!info) return; // No collection — project not indexed yet
      if (info.pointsCount === 0) return; // Empty collection — index may have been interrupted early

      // Check if indexing was completed (not interrupted)
      const metadata = await getProjectMetadata(collection);
      if (metadata && metadata.indexingStatus !== "completed") {
        logger.info("Skipping watcher auto-start: index is incomplete (interrupted)", {
          projectPath: resolvedPath,
          indexingStatus: metadata.indexingStatus,
          filesIndexed: metadata.filesIndexed,
          filesTotal: metadata.filesTotal,
        });
        return;
      }

      // Re-check conditions after async gap
      if (subscriptions.has(resolvedPath)) return;
      if (isIndexingInProgress(resolvedPath)) return;

      const started = await startWatching(resolvedPath);
      if (started) {
        logger.info("Auto-started file watcher on tool use", { projectPath: resolvedPath });
      } else if (!subscriptions.has(resolvedPath)) {
        // Another process holds the watch lock — cache to avoid retrying on every tool call
        externalWatchCache.set(resolvedPath, Date.now());
      }
    })
    .catch((err) => {
      // Non-fatal — watcher auto-start is opportunistic
      logger.debug("Auto-start watcher check failed (non-fatal)", {
        projectPath: resolvedPath,
        error: err instanceof Error ? err.message : String(err),
      });
    });
}
