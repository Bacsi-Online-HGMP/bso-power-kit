// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
import path from "node:path";
import { mergeExtraExtensions, QDRANT_MODE } from "../constants.js";
import { awaitGraphBuild, isGraphBuildInProgress } from "../services/code-graph.js";
import type { InfraProgressCallback } from "../services/docker.js";
import { ensureQdrantReady, isDockerAvailable } from "../services/docker.js";
import { getEmbeddingConfig } from "../services/embedding-config.js";
import { getEmbeddingProvider } from "../services/embedding-provider.js";
import { getIndexingProgress, indexProject, isIndexingInProgress, removeProjectIndex, requestCancellation, setIndexingProgress, updateProjectIndex } from "../services/indexer.js";
import { isProjectLocked, terminateLockHolder } from "../services/lock.js";
import { logger } from "../services/logger.js";
import { getWatchedProjects, isWatching, startWatching, stopWatching } from "../services/watcher.js";

const DOCKER_NOT_AVAILABLE_MESSAGE = [
  "❌ Docker is not available.",
  "",
  "SocratiCode requires Docker to manage the Qdrant container.",
  "",
  "To fix this:",
  "  1. Install Docker Desktop from https://www.docker.com/products/docker-desktop/",
  "  2. Make sure Docker Desktop is running (check for the whale icon in your system tray/menu bar)",
  "  3. Try this command again",
  "",
  "Alternatively, set QDRANT_MODE=external and point QDRANT_URL at a remote Qdrant server.",
  "",
  "Run codebase_health for a full infrastructure diagnostic.",
].join("\n");

async function ensureInfrastructure(onProgress?: InfraProgressCallback): Promise<string[]> {
  const messages: string[] = [];
  const config = getEmbeddingConfig();

  const docker = await ensureQdrantReady(onProgress);
  if (docker.pulled) messages.push("Pulled Qdrant Docker image.");
  if (docker.started) messages.push("Started Qdrant container.");

  const provider = await getEmbeddingProvider(onProgress);
  const readiness = await provider.ensureReady();
  if (readiness.imagePulled) messages.push("Pulled Ollama Docker image.");
  if (readiness.containerStarted) messages.push("Started Ollama container.");
  if (readiness.modelPulled) messages.push(`Pulled ${config.embeddingModel} model.`);

  return messages;
}

function formatIndexingInProgressMessage(resolvedPath: string, requestedTool: string): string {
  const progress = getIndexingProgress(resolvedPath);
  const lines = [
    `⚠ Indexing is already in progress for: ${resolvedPath}`,
    `Cannot run ${requestedTool} — please wait for the current operation to finish.`,
    "",
  ];

  if (progress) {
    lines.push(`Operation: ${progress.type === "full-index" ? "Full index" : "Incremental update"}`);
    lines.push(`Phase: ${progress.phase}`);
  }

  lines.push("", "Use codebase_status to check current indexing state.");
  return lines.join("\n");
}

export async function handleIndexTool(
  name: string,
  args: Record<string, unknown>,
): Promise<string> {
  const projectPath = (args.projectPath as string) || process.cwd();
  const progressMessages: string[] = [];
  const onProgress = (msg: string) => {
    progressMessages.push(msg);
    logger.info(msg, { tool: name, projectPath });
  };

  switch (name) {
    case "codebase_index": {
      // Concurrency guard: if already indexing, return progress
      const resolved = path.resolve(projectPath);
      if (isIndexingInProgress(resolved)) {
        return formatIndexingInProgressMessage(resolved, "codebase_index");
      }

      // Check Docker availability before anything else (managed mode only)
      if (QDRANT_MODE === "managed" && !(await isDockerAvailable())) {
        return DOCKER_NOT_AVAILABLE_MESSAGE;
      }

      // Set up infrastructure progress tracking so codebase_status shows what's happening
      setIndexingProgress(resolved, {
        type: "full-index",
        startedAt: Date.now(),
        filesTotal: 0,
        filesProcessed: 0,
        phase: "preparing infrastructure",
      });

      const infraProgress: InfraProgressCallback = (msg) => {
        setIndexingProgress(resolved, {
          type: "full-index",
          startedAt: Date.now(),
          filesTotal: 0,
          filesProcessed: 0,
          phase: msg,
        });
        logger.info(msg, { tool: "codebase_index", projectPath: resolved });
      };

      // Infrastructure setup is synchronous — we need Docker/Ollama running before indexing
      let infraMessages: string[];
      try {
        infraMessages = await ensureInfrastructure(infraProgress);
      } catch (error) {
        // Clear the progress on infra failure
        setIndexingProgress(resolved, null);
        const msg = error instanceof Error ? error.message : String(error);
        return `Infrastructure setup failed:\n\n${msg}\n\nRun codebase_health for a full diagnostic.`;
      }

      // Fire-and-forget: start indexing in the background
      const bgOnProgress = (msg: string) => {
        logger.info(msg, { tool: "codebase_index", projectPath: resolved });
      };
      const extraExts = mergeExtraExtensions(args.extraExtensions as string | undefined);

      // Clear infra progress — indexProject will set its own progress
      setIndexingProgress(resolved, null);

      // Start indexing — do NOT await. Runs in the background on the event loop.
      indexProject(resolved, bgOnProgress, extraExts.size > 0 ? extraExts : undefined)
        .then(async (result) => {
          logger.info("Background indexing completed", {
            projectPath: resolved,
            filesIndexed: result.filesIndexed,
            chunksCreated: result.chunksCreated,
            cancelled: result.cancelled,
          });

          // Auto-start watcher only if indexing completed (not cancelled)
          if (!result.cancelled && !isWatching(resolved)) {
            const started = await startWatching(resolved);
            if (started) {
              logger.info("Auto-started file watcher", { projectPath: resolved });
            }
          }
        })
        .catch((err) => {
          const message = err instanceof Error ? err.message : String(err);
          logger.error("Background indexing failed", { projectPath: resolved, error: message });
        });

      // Return immediately with instructions for the LLM
      const lines = [
        ...infraMessages,
        `Indexing started in the background for: ${resolved}`,
        "",
        "IMPORTANT: Indexing is now running asynchronously.",
        "Call codebase_status to check progress. Keep calling it periodically until progress reaches 100%.",
        "Once complete, you can use codebase_search to query the indexed codebase.",
      ];
      return lines.join("\n");
    }

    case "codebase_update": {
      // Concurrency guard: prevent duplicate indexing
      const resolved = path.resolve(projectPath);
      if (isIndexingInProgress(resolved)) {
        return formatIndexingInProgressMessage(resolved, "codebase_update");
      }

      // Check Docker availability before anything else (managed mode only)
      if (QDRANT_MODE === "managed" && !(await isDockerAvailable())) {
        return DOCKER_NOT_AVAILABLE_MESSAGE;
      }

      const infraMessages = await ensureInfrastructure(onProgress);
      const updateExtraExts = mergeExtraExtensions(args.extraExtensions as string | undefined);
      const result = await updateProjectIndex(projectPath, onProgress, updateExtraExts.size > 0 ? updateExtraExts : undefined);
      const lines = [
        ...infraMessages,
        `Updated project index: ${projectPath}`,
        `Added: ${result.added}`,
        `Updated: ${result.updated}`,
        `Removed: ${result.removed}`,
        `New chunks: ${result.chunksCreated}`,
        "",
        "Progress:",
        ...progressMessages,
      ];

      // Auto-start watcher after successful update (not cancelled)
      if (!result.cancelled && !isWatching(resolved)) {
        const started = await startWatching(resolved);
        if (started) {
          logger.info("Auto-started file watcher after update", { projectPath: resolved });
        }
      }

      return lines.join("\n");
    }

    case "codebase_remove": {
      const resolved = path.resolve(projectPath);
      // How long to wait for a SIGTERM'd cross-process to release its lock
      const SIGNAL_TIMEOUT_MS = 10_000;
      // How long to wait for a same-process batch to drain after cancellation.
      // Embedding a large batch (hundreds of chunks) via an external API can take
      // several minutes. 5 minutes is a safe upper bound; the loop exits as soon
      // as the batch finishes, so in the common case it completes in seconds.
      const DRAIN_TIMEOUT_MS = 5 * 60_000;

      /**
       * Poll until isProjectLocked returns false or the timeout elapses.
       * Used after sending SIGTERM so we wait for the other process to exit
       * and release the lock before proceeding with the destructive delete.
       */
      async function waitForLockRelease(operation: string): Promise<void> {
        const start = Date.now();
        while (Date.now() - start < SIGNAL_TIMEOUT_MS) {
          if (!(await isProjectLocked(resolved, operation))) return;
          await new Promise((r) => setTimeout(r, 200));
        }
        logger.warn("Lock was not released within timeout after SIGTERM, proceeding with remove", {
          projectPath: resolved,
          operation,
        });
      }

      // 1a. Stop same-process watcher
      if (isWatching(resolved)) {
        await stopWatching(resolved);
        logger.info("Stopped watcher before removing index", { projectPath: resolved });
      }

      // 1b. Terminate watcher in another process (cross-process)
      if (await isProjectLocked(resolved, "watch")) {
        const { terminated, pid } = await terminateLockHolder(resolved, "watch");
        if (terminated) {
          logger.info("Sent SIGTERM to cross-process watcher before remove", { pid, projectPath: resolved });
          await waitForLockRelease("watch");
        }
      }

      // 2a. Cancel same-process indexing and drain.
      // Track whether indexing was in-flight in THIS process so we do not
      // fall through to the cross-process path below (getLockHolderPid
      // explicitly guards against returning our own PID, so terminateLockHolder
      // can never send ourselves a signal).
      const wasIndexingInThisProcess = isIndexingInProgress(resolved);
      if (wasIndexingInThisProcess) {
        requestCancellation(resolved);
        logger.info("Requested cancellation of in-progress indexing before remove", { projectPath: resolved });
        const drainStart = Date.now();
        while (isIndexingInProgress(resolved) && Date.now() - drainStart < DRAIN_TIMEOUT_MS) {
          await new Promise((r) => setTimeout(r, 200));
        }
        if (isIndexingInProgress(resolved)) {
          // The current batch is still running. Deleting the Qdrant collection now
          // would cause "Not Found" upsert errors as the batch finishes writing.
          // We cannot forcibly interrupt an in-process async batch — cancellation
          // fires at the next batch boundary. Refuse the remove and let the user retry.
          logger.warn("In-process indexing did not drain within 5 min timeout, refusing remove to prevent data corruption", { projectPath: resolved });
          return [
            `⚠ Cannot remove index for ${projectPath}: indexing is still running.`,
            "",
            "Cancellation has been requested. The current embedding batch will finish shortly.",
            "Please wait a moment and try codebase_remove again, or call codebase_stop first.",
          ].join("\n");
        }
      }

      // 2b. Terminate indexing in another process (cross-process only — skip if we
      // already handled it in-process, because terminateLockHolder cannot signal our
      // own PID and would otherwise log a misleading "failed to terminate" warning).
      if (!wasIndexingInThisProcess && (await isProjectLocked(resolved, "index"))) {
        const { terminated, pid } = await terminateLockHolder(resolved, "index");
        if (terminated) {
          logger.info("Sent SIGTERM to cross-process indexing before remove", { pid, projectPath: resolved });
          await waitForLockRelease("index");
        } else {
          logger.warn("Failed to terminate cross-process indexing, proceeding with remove", { projectPath: resolved });
        }
      }

      // 3. Wait for any in-flight graph build to finish
      if (isGraphBuildInProgress(resolved)) {
        logger.info("Waiting for in-flight graph build to finish before remove", { projectPath: resolved });
        await awaitGraphBuild(resolved);
      }

      await removeProjectIndex(projectPath);
      return `Removed index for: ${projectPath}`;
    }

    case "codebase_stop": {
      const resolved = path.resolve(projectPath);

      // Case 1: This process is indexing — cancel in-memory
      if (isIndexingInProgress(resolved)) {
        const requested = requestCancellation(resolved);
        if (!requested) {
          return `No indexing operation is currently running for: ${resolved}`;
        }
        const progress = getIndexingProgress(resolved);
        const phase = progress?.phase ?? "unknown";
        const batches = progress?.batchesProcessed ?? 0;
        const totalBatches = progress?.batchesTotal ?? "?";
        return [
          `Cancellation requested for: ${resolved}`,
          `Current phase: ${phase} (batch ${batches}/${totalBatches})`,
          "",
          "The indexing operation will stop after the current batch finishes and checkpoints.",
          "All progress up to that point is preserved — re-run codebase_index to resume.",
        ].join("\n");
      }

      // Case 2: Another process (orphan) holds the lock — try to SIGTERM it
      if (await isProjectLocked(resolved, "index")) {
        const { terminated, pid } = await terminateLockHolder(resolved, "index");
        if (terminated) {
          return [
            `Sent termination signal to orphan indexing process (PID ${pid}) for: ${resolved}`,
            "",
            "The orphan process should shut down gracefully within a few seconds.",
            "All checkpointed progress is preserved — re-run codebase_index to resume.",
          ].join("\n");
        }
        if (pid !== null) {
          return [
            `Found orphan indexing process (PID ${pid}) for: ${resolved}, but failed to terminate it.`,
            "",
            `You can manually kill it: kill ${pid}`,
            "All checkpointed progress is preserved — re-run codebase_index to resume.",
          ].join("\n");
        }
      }

      return `No indexing operation is currently running for: ${resolved}`;
    }

    case "codebase_watch": {
      const action = args.action as string;

      if (action === "start") {
        await ensureInfrastructure();

        // Catch any changes made while the watcher was not running before starting it.
        const resolved = path.resolve(projectPath);
        let updateSummary = "";
        try {
          const result = await updateProjectIndex(resolved, onProgress);
          const changed = result.added + result.updated + result.removed;
          if (changed > 0) {
            updateSummary = `\nCaught up ${changed} change(s) since last session: ${result.added} added, ${result.updated} updated, ${result.removed} removed.`;
          } else {
            updateSummary = "\nIndex is already up to date.";
          }
        } catch (err) {
          // Non-fatal — watcher still starts even if catch-up update fails
          const msg = err instanceof Error ? err.message : String(err);
          logger.warn("codebase_watch: catch-up update failed (non-fatal)", { projectPath: resolved, error: msg });
          updateSummary = `\nWarning: could not run catch-up update (${msg}). Watcher started anyway.`;
        }

        if (!isWatching(resolved)) {
          const started = await startWatching(resolved);
          if (!started) {
            // Check if another process holds the watch lock
            if (await isProjectLocked(resolved, "watch")) {
              return `Already watched by another process: ${projectPath}${updateSummary}`;
            }
            return `Failed to start watching: ${projectPath}${updateSummary}`;
          }
        }
        return `Started watching: ${projectPath}${updateSummary}`;
      }

      if (action === "stop") {
        await stopWatching(projectPath);
        return `Stopped watching: ${projectPath}`;
      }

      // status
      const watched = getWatchedProjects();
      const resolved = path.resolve(projectPath);
      // Check if the current project is watched by another process (cross-process lock)
      const watchedByOtherProcess = !watched.includes(resolved) && await isProjectLocked(resolved, "watch");
      if (watched.length === 0 && !watchedByOtherProcess) {
        return "No projects are currently being watched.";
      }
      const statusItems = watched.map((p) => `  - ${p}`);
      if (watchedByOtherProcess) {
        statusItems.push(`  - ${resolved} (watched by another process)`);
      }
      return `Currently watching:\n${statusItems.join("\n")}`;
    }

    default:
      return `Unknown tool: ${name}`;
  }
}
