// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import { execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import lockfile from "proper-lockfile";
import { projectIdFromPath } from "../config.js";
import { logger } from "./logger.js";

/**
 * Cross-process lock for SocratiCode operations.
 *
 * Uses proper-lockfile for atomic file-based locking that works on
 * macOS, Windows, and Linux. Prevents multiple MCP instances from
 * simultaneously indexing or watching the same project.
 *
 * Lock files are stored in the OS temp directory under a socraticode subfolder.
 * Each lock file is named by project ID and operation type, e.g.:
 *   /tmp/socraticode-locks/cfc52e6ea434-index.lock
 *
 * Staleness: locks are considered stale after 2 minutes (if the holding process
 * crashes without releasing). proper-lockfile handles this automatically.
 */

const LOCK_DIR = path.join(os.tmpdir(), "socraticode-locks");

/** Staleness threshold in ms — if a lock hasn't been refreshed in this time, reclaim it */
const STALE_MS = 120_000; // 2 minutes

/** How often proper-lockfile refreshes the lock (must be < stale/2) */
const UPDATE_MS = 30_000; // 30 seconds

/** Track release functions for locks we hold */
const heldLocks = new Map<string, () => Promise<void>>();

function ensureLockDir(): void {
  if (!fs.existsSync(LOCK_DIR)) {
    fs.mkdirSync(LOCK_DIR, { recursive: true });
  }
}

function lockKey(projectPath: string, operation: string): string {
  const projectId = projectIdFromPath(path.resolve(projectPath));
  return `${projectId}-${operation}`;
}

function lockFilePath(key: string): string {
  return path.join(LOCK_DIR, key);
}

/**
 * Try to acquire a cross-process lock for a project operation.
 *
 * @param projectPath - Absolute path to the project directory
 * @param operation - Operation type: "index" or "watch"
 * @returns true if the lock was acquired, false if another process holds it
 */
export async function acquireProjectLock(projectPath: string, operation: string): Promise<boolean> {
  ensureLockDir();

  const key = lockKey(projectPath, operation);
  const filePath = lockFilePath(key);

  // Ensure the file to lock exists (proper-lockfile requires it)
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, `${process.pid}\n`, "utf-8");
  }

  // If we already hold this lock (same process), return true
  if (heldLocks.has(key)) {
    return true;
  }

  try {
    const release = await lockfile.lock(filePath, {
      stale: STALE_MS,
      update: UPDATE_MS,
      retries: 0, // Don't retry — fail immediately if already locked
      realpath: false, // Don't resolve symlinks — lock the exact path
      onCompromised: (err) => {
        // Lock was compromised (e.g., stale lock reclaimed by another process)
        logger.warn("Lock compromised, another process may have reclaimed it", {
          projectPath,
          operation,
          error: err.message,
        });
        heldLocks.delete(key);
      },
    });

    // Always stamp our PID into the lock file after acquiring it — even if the file
    // already existed with a stale PID from a prior run. getLockHolderPid reads this
    // to identify which process currently owns the lock across process boundaries.
    fs.writeFileSync(filePath, `${process.pid}\n`, "utf-8");

    heldLocks.set(key, release);
    logger.debug("Acquired project lock", { projectPath, operation, key });
    return true;
  } catch (err) {
    // ELOCKED = another process holds the lock
    if (err instanceof Error && (err as NodeJS.ErrnoException).code === "ELOCKED") {
      logger.debug("Lock already held by another process", { projectPath, operation, key });
      return false;
    }
    // Unexpected error — log and treat as unable to acquire
    logger.warn("Failed to acquire project lock", {
      projectPath,
      operation,
      error: err instanceof Error ? err.message : String(err),
    });
    return false;
  }
}

/**
 * Release a previously acquired lock.
 *
 * @param projectPath - Absolute path to the project directory
 * @param operation - Operation type: "index" or "watch"
 */
export async function releaseProjectLock(projectPath: string, operation: string): Promise<void> {
  const key = lockKey(projectPath, operation);
  const release = heldLocks.get(key);

  if (release) {
    try {
      await release();
      logger.debug("Released project lock", { projectPath, operation, key });
    } catch (err) {
      // Lock may already be released (e.g., compromised) — not fatal
      logger.debug("Lock release failed (may already be released)", {
        projectPath,
        operation,
        error: err instanceof Error ? err.message : String(err),
      });
    } finally {
      heldLocks.delete(key);
    }
  }
}

/**
 * Check if a lock is currently held (by any process).
 */
export async function isProjectLocked(projectPath: string, operation: string): Promise<boolean> {
  ensureLockDir();

  const key = lockKey(projectPath, operation);
  const filePath = lockFilePath(key);

  if (!fs.existsSync(filePath)) return false;

  try {
    return await lockfile.check(filePath, {
      stale: STALE_MS,
      realpath: false,
    });
  } catch {
    return false;
  }
}

/**
 * Read the PID stored in the lock file and verify the process is still alive.
 * Returns the PID if the lock is held by a live process, or null otherwise.
 */
export async function getLockHolderPid(projectPath: string, operation: string): Promise<number | null> {
  ensureLockDir();

  const key = lockKey(projectPath, operation);
  const filePath = lockFilePath(key);

  if (!fs.existsSync(filePath)) return null;

  // Only check if the lock is actually held
  try {
    const locked = await lockfile.check(filePath, { stale: STALE_MS, realpath: false });
    if (!locked) return null;
  } catch {
    return null;
  }

  // Read the PID from the lock file content
  try {
    const content = fs.readFileSync(filePath, "utf-8").trim();
    const pid = parseInt(content, 10);
    if (Number.isNaN(pid) || pid <= 0) return null;

    // Don't report our own process as an orphan
    if (pid === process.pid) return null;

    // Check if the process is alive (signal 0 = existence check)
    process.kill(pid, 0);

    return pid;
  } catch {
    // process.kill(pid, 0) throws if process doesn't exist
    return null;
  }
}

/**
 * Attempt to terminate an orphan process holding a project lock.
 * On POSIX (macOS/Linux): sends SIGTERM for graceful shutdown.
 * On Windows: uses `taskkill /F /PID` since cross-process SIGTERM is not supported.
 * Returns true if the termination signal was sent successfully, false otherwise.
 */
export async function terminateLockHolder(projectPath: string, operation: string): Promise<{ terminated: boolean; pid: number | null }> {
  const pid = await getLockHolderPid(projectPath, operation);
  if (pid === null) {
    return { terminated: false, pid: null };
  }

  try {
    if (process.platform === "win32") {
      // process.kill() with signals other than 0 is not supported cross-process on Windows.
      // taskkill /F is a force-kill (no graceful shutdown), but it's the only reliable option.
      execSync(`taskkill /F /PID ${pid}`, { stdio: "ignore" });
      logger.info("Sent taskkill to orphan lock-holder process (Windows)", { pid, projectPath, operation });
    } else {
      process.kill(pid, "SIGTERM");
      logger.info("Sent SIGTERM to orphan lock-holder process", { pid, projectPath, operation });
    }
    return { terminated: true, pid };
  } catch (err) {
    logger.warn("Failed to terminate lock-holder process", {
      pid, projectPath, operation,
      error: err instanceof Error ? err.message : String(err),
    });
    return { terminated: false, pid };
  }
}

/**
 * Release all locks held by this process.
 * Called during graceful shutdown.
 */
export async function releaseAllLocks(): Promise<void> {
  for (const [key, release] of heldLocks) {
    try {
      await release();
      logger.debug("Released lock during shutdown", { key });
    } catch {
      // Best effort during shutdown
    }
  }
  heldLocks.clear();
}
