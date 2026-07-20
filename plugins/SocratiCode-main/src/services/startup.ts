// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

/**
 * Startup lifecycle helpers — auto-resume and graceful shutdown coordination.
 *
 * Extracted from src/index.ts so the logic can be unit-tested independently
 * of the MCP stdio transport.
 */

import fs from "node:fs";
import path from "node:path";
import { collectionName, projectIdFromPath } from "../config.js";
import { QDRANT_COLLECTION_PREFIX, QDRANT_MODE } from "../constants.js";
import { isDockerAvailable, isQdrantRunning } from "./docker.js";
import { getIndexingInProgressProjects, getPersistedIndexingStatus, indexProject, requestCancellation, updateProjectIndex } from "./indexer.js";
import { getLockHolderPid, releaseAllLocks } from "./lock.js";
import { logger } from "./logger.js";
import { getProjectMetadata, listCodebaseCollections } from "./qdrant.js";
import { isWatching, startWatching, stopAllWatchers } from "./watcher.js";

/**
 * Auto-resume indexed projects on server startup.
 *
 * Which projects are resumed is controlled by two opt-in environment
 * variables (issue #70). Default (both unset) keeps the original behavior:
 * only the project at process.cwd() is considered.
 *
 *   - SOCRATICODE_AUTO_RESUME_PROJECTS: comma-separated list of project
 *     paths to resume. Takes precedence over SOCRATICODE_AUTO_RESUME.
 *   - SOCRATICODE_AUTO_RESUME=all: resume every indexed project that has a
 *     stored path in its Qdrant metadata.
 *
 * Multi-project modes resume strictly sequentially: each project's catch-up
 * (incremental update or interrupted-index recovery) completes before the
 * next starts, so N projects never stampede the embedding provider. Skipped
 * projects (missing directory, no stored path, not indexed) are logged at
 * warn level so misconfiguration is visible.
 *
 * Per project, if the index is complete: start the file watcher and run an
 * incremental update to catch changes made while the MCP was down. If the
 * index is incomplete (interrupted): resume it via indexProject, which skips
 * already-hashed files and honours codebase_stop cancellation; the watcher
 * starts after recovery completes.
 *
 * Runs in the background after server startup — non-blocking, non-fatal.
 *
 * @param projectPath - Override project path for the default single-project
 *   mode (defaults to process.cwd()). Only used by tests — production always
 *   uses process.cwd().
 */
export async function autoResumeIndexedProjects(projectPath?: string): Promise<void> {
  try {
    // In managed mode, check if Docker and Qdrant are already running — don't start them.
    // In external mode, skip Docker checks and let listCodebaseCollections() fail if unreachable.
    if (QDRANT_MODE === "managed") {
      if (!(await isDockerAvailable())) {
        logger.info("Auto-resume: Docker not available, skipping");
        return;
      }
      if (!(await isQdrantRunning())) {
        logger.info("Auto-resume: Qdrant not running, skipping");
        return;
      }
    }

    // Read at call time (not module load) so tests and MCP host configs
    // that set the variables after import are honoured.
    const explicitList = process.env.SOCRATICODE_AUTO_RESUME_PROJECTS?.trim();
    const resumeMode = process.env.SOCRATICODE_AUTO_RESUME?.trim();

    if (explicitList) {
      await resumeProjectList(explicitList);
      return;
    }

    if (resumeMode) {
      if (resumeMode.toLowerCase() === "all") {
        await resumeAllIndexedProjects();
        return;
      }
      logger.warn("Auto-resume: unrecognized SOCRATICODE_AUTO_RESUME value, using default behavior (current project only)", {
        value: resumeMode,
      });
      // Fall through to the default single-project behavior below.
    }

    // Default: only consider the current project
    const resolvedPath = projectPath ?? process.cwd();

    // If CWD is root or home, the MCP host hasn't opened a specific project yet — skip
    if (resolvedPath === "/" || resolvedPath === process.env.HOME) {
      logger.info("Auto-resume: CWD is root/home, no specific project — skipping", { projectPath: resolvedPath });
      return;
    }

    const collections = await listCodebaseCollections();
    await resumeProject(resolvedPath, collections, "info");
  } catch (err) {
    logger.warn("Auto-resume failed (non-fatal)", {
      error: err instanceof Error ? err.message : String(err),
    });
  }
}

/**
 * Resume the explicit comma-separated project list from
 * SOCRATICODE_AUTO_RESUME_PROJECTS, sequentially. Paths are resolved to
 * absolute and deduplicated; entries whose directory does not exist are
 * skipped with a warning. One project failing does not stop the rest.
 */
async function resumeProjectList(rawList: string): Promise<void> {
  const targets = [...new Set(
    rawList
      .split(",")
      .map((p) => p.trim())
      .filter((p) => p.length > 0)
      .map((p) => path.resolve(p)),
  )];

  if (targets.length === 0) {
    logger.warn("Auto-resume: SOCRATICODE_AUTO_RESUME_PROJECTS is set but contains no paths");
    return;
  }

  logger.info("Auto-resume: resuming explicit project list sequentially", { count: targets.length });
  const collections = await listCodebaseCollections();

  for (const target of targets) {
    if (!fs.existsSync(target)) {
      logger.warn("Auto-resume: listed project directory does not exist, skipping", { projectPath: target });
      continue;
    }
    try {
      await resumeProject(target, collections, "warn");
    } catch (err) {
      logger.warn("Auto-resume: project resume failed, continuing with remaining projects", {
        projectPath: target,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }
}

/**
 * Resume every indexed project found in Qdrant (SOCRATICODE_AUTO_RESUME=all),
 * sequentially. Project paths come from each collection's stored metadata;
 * collections without a stored path (indexed before path tracking) and paths
 * that no longer exist on disk are skipped with a warning.
 */
async function resumeAllIndexedProjects(): Promise<void> {
  const collections = await listCodebaseCollections();
  const codebasePrefix = `${QDRANT_COLLECTION_PREFIX}codebase_`;
  const codebaseCollections = collections.filter((c) => c.startsWith(codebasePrefix));

  if (codebaseCollections.length === 0) {
    logger.info("Auto-resume: no indexed projects found, nothing to resume");
    return;
  }

  const targets: string[] = [];
  const seen = new Set<string>();
  for (const coll of codebaseCollections) {
    const metadata = await getProjectMetadata(coll);
    if (!metadata?.projectPath) {
      logger.warn("Auto-resume: project has no stored path (indexed before path tracking), cannot auto-resume. Re-index it once to fix this permanently.", {
        collection: coll,
      });
      continue;
    }
    const resolved = path.resolve(metadata.projectPath);
    if (seen.has(resolved)) continue;
    seen.add(resolved);
    if (!fs.existsSync(resolved)) {
      logger.warn("Auto-resume: indexed project directory no longer exists, skipping", {
        projectPath: resolved,
        collection: coll,
      });
      continue;
    }
    targets.push(resolved);
  }

  logger.info("Auto-resume: resuming all indexed projects sequentially", { count: targets.length });

  for (const target of targets) {
    try {
      await resumeProject(target, collections, "warn");
    } catch (err) {
      logger.warn("Auto-resume: project resume failed, continuing with remaining projects", {
        projectPath: target,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }
}

/**
 * Resume a single project: start its watcher and catch up its index.
 * Awaits the catch-up work to completion so callers can sequence multiple
 * projects without overlapping embedding load.
 *
 * @param resolvedPath - Absolute project path.
 * @param collections - Pre-fetched Qdrant collection names (fetched once per
 *   startup so multi-project modes do not re-query per project).
 * @param skipLogLevel - "warn" in multi-project modes so misconfigured
 *   entries are visible; "info" for the default cwd mode (an unindexed cwd
 *   is normal, not a misconfiguration).
 */
async function resumeProject(
  resolvedPath: string,
  collections: string[],
  skipLogLevel: "info" | "warn",
): Promise<void> {
  const projectId = projectIdFromPath(resolvedPath);
  const collection = collectionName(projectId);

  if (!collections.includes(collection)) {
    if (skipLogLevel === "warn") {
      logger.warn("Auto-resume: project not yet indexed, skipping", { projectPath: resolvedPath });
    } else {
      logger.info("Auto-resume: current project not yet indexed, skipping", { projectPath: resolvedPath });
    }
    return;
  }

  // Check persisted indexing status to detect interrupted indexing
  const persistedStatus = await getPersistedIndexingStatus(resolvedPath);

  if (persistedStatus === "in-progress") {
    // Check if another process is already indexing (orphan from previous session)
    const orphanPid = await getLockHolderPid(resolvedPath, "index");
    if (orphanPid !== null) {
      logger.info("Auto-resume: skipping — another process is still indexing this project", {
        projectPath: resolvedPath, orphanPid,
      });
      return;
    }

    // Index was interrupted — resume it via indexProject.
    // indexProject skips already-hashed files, embeds the rest, and honours
    // codebase_stop cancellation requests (unlike updateProjectIndex's incremental diff).
    // Do NOT start watcher yet — it will start after indexing completes.
    logger.info("Auto-resume: detected incomplete index, resuming indexing", { projectPath: resolvedPath });
    const resumeOnProgress = (msg: string) => logger.info(msg, { tool: "auto-resume", projectPath: resolvedPath });
    try {
      const result = await indexProject(resolvedPath, resumeOnProgress);
      logger.info("Auto-resume: incomplete index recovery completed", {
        projectPath: resolvedPath,
        filesIndexed: result.filesIndexed,
        chunksCreated: result.chunksCreated,
        cancelled: result.cancelled,
      });
      // Now start the watcher after recovery — only if not cancelled
      if (!result.cancelled && !isWatching(resolvedPath)) {
        const started = await startWatching(resolvedPath);
        if (started) {
          logger.info("Auto-resume: started file watcher after recovery", { projectPath: resolvedPath });
        }
      }
    } catch (err) {
      logger.warn("Auto-resume: incomplete index recovery failed (non-fatal)", {
        projectPath: resolvedPath,
        error: err instanceof Error ? err.message : String(err),
      });
    }
    return;
  }

  // Index is complete — start watcher and do incremental catch-up.
  // Watcher startup failure must not skip the catch-up below: a project
  // without a live watcher is degraded, but a project with a stale index
  // is broken for search.
  if (!isWatching(resolvedPath)) {
    try {
      const started = await startWatching(resolvedPath);
      if (started) {
        logger.info("Auto-resume: started file watcher", { projectPath: resolvedPath });
      }
    } catch (err) {
      logger.warn("Auto-resume: failed to start watcher, continuing with incremental catch-up", {
        projectPath: resolvedPath,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  // Incremental update: only re-embeds actually changed files. Awaited so
  // multi-project resume stays sequential (auto-resume as a whole already
  // runs in the background, so this blocks nothing user-facing).
  // Note: updateProjectIndex handles code graph rebuild internally.
  try {
    const result = await updateProjectIndex(resolvedPath);
    const changed = result.added + result.updated + result.removed;
    if (changed > 0) {
      logger.info("Auto-resume: incremental update completed", {
        projectPath: resolvedPath,
        added: result.added,
        updated: result.updated,
        removed: result.removed,
        filesChanged: changed,
      });
    } else {
      logger.info("Auto-resume: index is up to date", { projectPath: resolvedPath });
    }
  } catch (err) {
    logger.warn("Auto-resume: incremental update failed (non-fatal)", {
      projectPath: resolvedPath,
      error: err instanceof Error ? err.message : String(err),
    });
  }
}

/** Wait for any active indexing operations to complete (with timeout). */
export async function awaitActiveIndexing(timeoutMs = 60_000): Promise<void> {
  const active = getIndexingInProgressProjects();
  if (active.length === 0) return;

  logger.info("Waiting for active indexing to complete before shutdown", {
    projects: active,
  });

  const deadline = Date.now() + timeoutMs;
  while (getIndexingInProgressProjects().length > 0 && Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 500));
  }

  const remaining = getIndexingInProgressProjects();
  if (remaining.length > 0) {
    logger.warn("Forcing shutdown — indexing still in progress. Progress is checkpointed; it will resume with no data loss.", {
      projects: remaining,
    });
  }
}

/**
 * Execute graceful shutdown: cancel in-flight indexing, wait for completion,
 * stop watchers, release locks.
 *
 * @param closeServer - Optional callback to close the MCP server.
 */
export async function gracefulShutdown(signal: string, closeServer?: () => Promise<void>): Promise<void> {
  logger.info(`Received ${signal}, shutting down gracefully...`);

  // Signal all in-flight indexing in this process to stop at the next batch boundary
  for (const project of getIndexingInProgressProjects()) {
    requestCancellation(project);
  }

  await awaitActiveIndexing();
  await stopAllWatchers();
  await releaseAllLocks();

  logger.info("Graceful shutdown complete");

  // Close the MCP server transport last — the host may have already severed
  // the stdio pipe (especially on SIGTERM), so server.close() can hang or
  // throw. Wrap in a timeout so the process still exits cleanly.
  if (closeServer) {
    try {
      await Promise.race([
        closeServer(),
        new Promise<void>((resolve) => setTimeout(resolve, 3_000)),
      ]);
    } catch {
      // Broken pipe or transport already closed — not fatal during shutdown
    }
  }
}
