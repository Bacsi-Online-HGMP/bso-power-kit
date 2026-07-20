// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// We need to mock proper-lockfile and logger before importing lock module
vi.mock("proper-lockfile", () => {
  const locks = new Map<string, boolean>();
  return {
    default: {
      lock: vi.fn(async (filePath: string, _opts?: { onCompromised?: (err: Error) => void }) => {
        if (locks.get(filePath)) {
          const err = new Error("Lock file is already being held") as NodeJS.ErrnoException;
          err.code = "ELOCKED";
          throw err;
        }
        locks.set(filePath, true);
        const release = async () => {
          locks.delete(filePath);
        };
        return release;
      }),
      check: vi.fn(async (filePath: string) => {
        return locks.get(filePath) ?? false;
      }),
    },
    // Track the internal map for test manipulation
    __locks: locks,
  };
});

vi.mock("../../src/services/logger.js", () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

import lockfile from "proper-lockfile";
// Import after mocks are set up
import {
  acquireProjectLock,
  getLockHolderPid,
  isProjectLocked,
  releaseAllLocks,
  releaseProjectLock,
  terminateLockHolder,
} from "../../src/services/lock.js";

describe("lock", () => {
  const TEST_PROJECT = "/tmp/socraticode-test-lock-project";
  const LOCK_DIR = path.join(os.tmpdir(), "socraticode-locks");

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset the internal heldLocks map by releasing everything
  });

  afterEach(async () => {
    // Clean up any held locks
    await releaseAllLocks();
    // Clean up lock files we may have created
    try {
      const entries = fs.readdirSync(LOCK_DIR);
      for (const entry of entries) {
        if (entry.includes("socraticode-test")) {
          fs.unlinkSync(path.join(LOCK_DIR, entry));
        }
      }
    } catch {
      // Lock dir may not exist
    }
  });

  describe("acquireProjectLock", () => {
    it("acquires a lock and returns true", async () => {
      const result = await acquireProjectLock(TEST_PROJECT, "index");
      expect(result).toBe(true);
      expect(lockfile.lock).toHaveBeenCalled();
    });

    it("returns true when re-acquiring a lock already held by same process", async () => {
      const first = await acquireProjectLock(TEST_PROJECT, "index");
      expect(first).toBe(true);

      // Second acquire should succeed (same process re-entrant)
      const second = await acquireProjectLock(TEST_PROJECT, "index");
      expect(second).toBe(true);

      // lockfile.lock should only have been called once (second was short-circuited)
      expect(lockfile.lock).toHaveBeenCalledTimes(1);
    });

    it("returns false when lock is held by another process (ELOCKED)", async () => {
      // Make lockfile.lock throw ELOCKED
      vi.mocked(lockfile.lock).mockRejectedValueOnce(
        Object.assign(new Error("Lock file is already being held"), { code: "ELOCKED" }),
      );

      const result = await acquireProjectLock(TEST_PROJECT, "index");
      expect(result).toBe(false);
    });

    it("returns false on unexpected errors", async () => {
      vi.mocked(lockfile.lock).mockRejectedValueOnce(new Error("EACCES: permission denied"));

      const result = await acquireProjectLock(TEST_PROJECT, "index");
      expect(result).toBe(false);
    });

    it("creates lock directory if it does not exist", async () => {
      // The function calls ensureLockDir() which creates the dir
      await acquireProjectLock(TEST_PROJECT, "index");
      expect(fs.existsSync(LOCK_DIR)).toBe(true);
    });

    it("creates the lock file if it does not exist", async () => {
      await acquireProjectLock(TEST_PROJECT, "index");
      // lockfile.lock was called, meaning the file was created first
      expect(lockfile.lock).toHaveBeenCalled();
    });

    it("acquires different locks for different operations", async () => {
      const indexLock = await acquireProjectLock(TEST_PROJECT, "index");
      const watchLock = await acquireProjectLock(TEST_PROJECT, "watch");

      expect(indexLock).toBe(true);
      expect(watchLock).toBe(true);
      expect(lockfile.lock).toHaveBeenCalledTimes(2);
    });
  });

  describe("releaseProjectLock", () => {
    it("releases a held lock", async () => {
      await acquireProjectLock(TEST_PROJECT, "index");
      await releaseProjectLock(TEST_PROJECT, "index");

      // Re-acquiring should work (calls lockfile.lock again)
      vi.mocked(lockfile.lock).mockClear();
      const result = await acquireProjectLock(TEST_PROJECT, "index");
      expect(result).toBe(true);
      expect(lockfile.lock).toHaveBeenCalledTimes(1);
    });

    it("does nothing when no lock is held", async () => {
      // Should not throw
      await expect(releaseProjectLock(TEST_PROJECT, "index")).resolves.toBeUndefined();
    });

    it("handles release errors gracefully", async () => {
      // Acquire a lock, then make the release function throw
      vi.mocked(lockfile.lock).mockResolvedValueOnce(async () => {
        throw new Error("Release failed");
      });
      await acquireProjectLock(TEST_PROJECT, "index");

      // Should not throw even though internal release fails
      await expect(releaseProjectLock(TEST_PROJECT, "index")).resolves.toBeUndefined();
    });
  });

  describe("isProjectLocked", () => {
    it("returns false when no lock exists", async () => {
      vi.mocked(lockfile.check).mockResolvedValueOnce(false);
      const result = await isProjectLocked(TEST_PROJECT, "index");
      expect(result).toBe(false);
    });

    it("returns true when lock is held", async () => {
      await acquireProjectLock(TEST_PROJECT, "index");
      vi.mocked(lockfile.check).mockResolvedValueOnce(true);

      const result = await isProjectLocked(TEST_PROJECT, "index");
      expect(result).toBe(true);
    });

    it("returns false on check errors", async () => {
      vi.mocked(lockfile.check).mockRejectedValueOnce(new Error("Check failed"));
      const result = await isProjectLocked(TEST_PROJECT, "index");
      expect(result).toBe(false);
    });
  });

  describe("getLockHolderPid", () => {
    it("returns null when no lock file exists", async () => {
      const result = await getLockHolderPid("/tmp/nonexistent-project-xyzzy", "index");
      expect(result).toBe(null);
    });

    it("returns null when lock is not held", async () => {
      vi.mocked(lockfile.check).mockResolvedValueOnce(false);
      const result = await getLockHolderPid(TEST_PROJECT, "index");
      expect(result).toBe(null);
    });

    it("returns null for own process PID", async () => {
      // Acquire lock (writes our PID to file), then check
      await acquireProjectLock(TEST_PROJECT, "index");
      vi.mocked(lockfile.check).mockResolvedValueOnce(true);

      const result = await getLockHolderPid(TEST_PROJECT, "index");
      // Our own PID should be filtered out
      expect(result).toBe(null);
    });

    it("returns null when check throws", async () => {
      vi.mocked(lockfile.check).mockRejectedValueOnce(new Error("Check failed"));
      const result = await getLockHolderPid(TEST_PROJECT, "index");
      expect(result).toBe(null);
    });
  });

  describe("terminateLockHolder", () => {
    it("returns terminated: false when no lock holder exists", async () => {
      vi.mocked(lockfile.check).mockResolvedValueOnce(false);
      const result = await terminateLockHolder(TEST_PROJECT, "index");
      expect(result).toEqual({ terminated: false, pid: null });
    });

    it("returns terminated: false and pid: null for non-existent lock", async () => {
      const result = await terminateLockHolder("/tmp/nonexistent-project-xyzzy", "index");
      expect(result.terminated).toBe(false);
      expect(result.pid).toBe(null);
    });
  });

  describe("releaseAllLocks", () => {
    it("releases all held locks", async () => {
      await acquireProjectLock(TEST_PROJECT, "index");
      await acquireProjectLock(TEST_PROJECT, "watch");

      await releaseAllLocks();

      // Both should be released — re-acquiring should call lockfile.lock again
      vi.mocked(lockfile.lock).mockClear();
      const indexResult = await acquireProjectLock(TEST_PROJECT, "index");
      const watchResult = await acquireProjectLock(TEST_PROJECT, "watch");
      expect(indexResult).toBe(true);
      expect(watchResult).toBe(true);
      expect(lockfile.lock).toHaveBeenCalledTimes(2);
    });

    it("does not throw when no locks are held", async () => {
      await expect(releaseAllLocks()).resolves.toBeUndefined();
    });

    it("handles release errors during shutdown gracefully", async () => {
      // Acquire with a release that throws
      vi.mocked(lockfile.lock).mockResolvedValueOnce(async () => {
        throw new Error("Shutdown release failed");
      });
      await acquireProjectLock(TEST_PROJECT, "index");

      // Should not throw
      await expect(releaseAllLocks()).resolves.toBeUndefined();
    });
  });
});
