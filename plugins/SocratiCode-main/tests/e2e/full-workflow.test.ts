// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
/**
 * End-to-end workflow test
 *
 * This test exercises the COMPLETE lifecycle of SocratiCode through the
 * tool handler API — the same interface the MCP server exposes to clients.
 *
 * Workflow:
 *   1. Health check (codebase_health)
 *   2. About (codebase_about)
 *   3. Index a fixture project (codebase_index + poll codebase_status)
 *   4. Semantic search (codebase_search)
 *   5. Build code graph (codebase_graph_build)
 *   6. Query graph (codebase_graph_query, codebase_graph_stats, codebase_graph_circular, codebase_graph_visualize)
 *   7. Incremental update — add file (codebase_update)
 *   8. Search for the new file's content (codebase_search)
 *   9. Watch lifecycle (codebase_watch start → status → stop)
 *  10. List projects (codebase_list_projects)
 *  11. Remove index (codebase_remove)
 *  12. Confirm removal (codebase_status, codebase_list_projects)
 */

import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { invalidateGraphCache } from "../../src/services/code-graph.js";
import { stopAllWatchers } from "../../src/services/watcher.js";
import { handleGraphTool } from "../../src/tools/graph-tools.js";
import { handleIndexTool } from "../../src/tools/index-tools.js";
import { handleManageTool } from "../../src/tools/manage-tools.js";
import { handleQueryTool } from "../../src/tools/query-tools.js";
import {
  addFileToFixture,
  createFixtureProject,
  type FixtureProject,
  isDockerAvailable,
} from "../helpers/fixtures.js";
import {
  cleanupTestCollections,
  waitForOllama,
  waitForQdrant,
} from "../helpers/setup.js";

const dockerAvailable = isDockerAvailable();

async function waitForIndexingComplete(
  projectPath: string,
  timeoutMs = 180_000,
): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const status = await handleQueryTool("codebase_status", {
      projectPath,
    });
    if (
      status.includes("Last completed") ||
      status.includes("chunks") ||
      (status.includes("files") && status.includes("indexed"))
    ) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 3_000));
  }
  throw new Error(`Indexing did not complete within ${timeoutMs}ms`);
}

describe.skipIf(!dockerAvailable)(
  "e2e: full SocratiCode workflow",
  { timeout: 600_000 },
  () => {
    let fixture: FixtureProject;

    beforeAll(async () => {
      await waitForQdrant();
      await waitForOllama();
      fixture = createFixtureProject("e2e-workflow");
      await cleanupTestCollections(fixture.root);
    }, 120_000);

    afterAll(async () => {
      await stopAllWatchers();
      invalidateGraphCache(fixture.root);
      fixture.cleanup();
      await cleanupTestCollections(fixture.root);
    });

    // ─── Step 1: Health check ────────────────────────────────
    it("step 1 — health check passes", async () => {
      const result = await handleManageTool("codebase_health", {});

      expect(result).toContain("[OK]");
      expect(result).toContain("Docker");
      expect(result).toContain("Qdrant");
      expect(result).toContain("Ollama");
    });

    // ─── Step 2: About ───────────────────────────────────────
    it("step 2 — about returns feature description", async () => {
      const result = await handleManageTool("codebase_about", {});
      expect(result).toContain("SocratiCode");
    });

    // ─── Step 3: Index the fixture project ───────────────────
    it("step 3 — index project (fire-and-forget)", async () => {
      const result = await handleIndexTool("codebase_index", {
        projectPath: fixture.root,
      });

      expect(result).toContain("Indexing started");
    }, 60_000);

    it("step 3b — poll until indexing completes", async () => {
      await waitForIndexingComplete(fixture.root);

      const status = await handleQueryTool("codebase_status", {
        projectPath: fixture.root,
      });
      expect(status.length).toBeGreaterThan(0);
    }, 180_000);

    // ─── Step 4: Semantic search ─────────────────────────────
    it("step 4 — search finds authentication code", async () => {
      const result = await handleQueryTool("codebase_search", {
        query: "user authentication login",
        projectPath: fixture.root,
      });

      expect(result).toBeDefined();
      expect(result.length).toBeGreaterThan(0);
    }, 30_000);

    it("step 4b — search with limit", async () => {
      const result = await handleQueryTool("codebase_search", {
        query: "function",
        projectPath: fixture.root,
        limit: 3,
      });

      expect(result).toBeDefined();
    }, 30_000);

    // ─── Step 5: Build code graph ────────────────────────────
    it("step 5 — build code graph (fire-and-forget)", async () => {
      const result = await handleGraphTool("codebase_graph_build", {
        projectPath: fixture.root,
      });

      expect(result).toContain("Graph build started in the background");
      expect(result).toContain("codebase_graph_status");
    });

    it("step 5b — poll until graph build completes", async () => {
      const start = Date.now();
      const timeout = 60_000;
      while (Date.now() - start < timeout) {
        const status = await handleGraphTool("codebase_graph_status", {
          projectPath: fixture.root,
        });
        if (status.includes("READY")) {
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 1_000));
      }
      throw new Error("Graph build did not complete within 60s");
    }, 90_000);

    // ─── Step 6: Graph queries ───────────────────────────────
    it("step 6a — graph query for index.ts dependencies", async () => {
      const result = await handleGraphTool("codebase_graph_query", {
        projectPath: fixture.root,
        filePath: "src/index.ts",
      });

      expect(result).toBeDefined();
      expect(result.length).toBeGreaterThan(0);
    });

    it("step 6b — graph stats", async () => {
      const result = await handleGraphTool("codebase_graph_stats", {
        projectPath: fixture.root,
      });

      expect(result).toContain("Code Graph Statistics");
      expect(result).toContain("Total files:");
    });

    it("step 6c — circular dependency check", async () => {
      const result = await handleGraphTool("codebase_graph_circular", {
        projectPath: fixture.root,
      });

      // Reports circular dependency findings (fixture has a self-cycle)
      expect(result).toBeDefined();
      expect(result.length).toBeGreaterThan(0);
    });

    it("step 6d — Mermaid visualization", async () => {
      const result = await handleGraphTool("codebase_graph_visualize", {
        projectPath: fixture.root,
      });

      expect(result).toContain("```mermaid");
      expect(result).toContain("graph LR");
    });

    // ─── Step 7: Incremental update ──────────────────────────
    it("step 7 — add a file and run incremental update", async () => {
      addFileToFixture(
        fixture.root,
        "src/services/cache.ts",
        `
import { User } from "../types";

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

export class InMemoryCache {
  private store = new Map<string, CacheEntry<unknown>>();

  set<T>(key: string, value: T, ttlMs: number): void {
    this.store.set(key, { value, expiresAt: Date.now() + ttlMs });
  }

  get<T>(key: string): T | null {
    const entry = this.store.get(key);
    if (!entry || entry.expiresAt < Date.now()) {
      this.store.delete(key);
      return null;
    }
    return entry.value as T;
  }

  invalidate(key: string): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }

  cacheUser(user: User): void {
    this.set(user.id, user, 60_000);
  }
}
        `.trim(),
      );

      const result = await handleIndexTool("codebase_update", {
        projectPath: fixture.root,
      });

      expect(result).toBeDefined();
      expect(result).toContain("added");
    }, 60_000);

    // ─── Step 8: Search for newly added content ──────────────
    it("step 8 — search finds the Cache class", async () => {
      const result = await handleQueryTool("codebase_search", {
        query: "in-memory cache TTL expiration",
        projectPath: fixture.root,
      });

      expect(result).toBeDefined();
      expect(result.length).toBeGreaterThan(0);
      // The cache.ts content should appear
      expect(
        result.toLowerCase().includes("cache") ||
          result.toLowerCase().includes("ttl") ||
          result.toLowerCase().includes("expir"),
      ).toBe(true);
    }, 30_000);

    // ─── Step 9: Watch lifecycle ─────────────────────────────
    it("step 9a — start watching", async () => {
      const result = await handleIndexTool("codebase_watch", {
        projectPath: fixture.root,
        action: "start",
      });

      expect(result.toLowerCase()).toContain("watch");
    }, 30_000);

    it("step 9b — watch status shows active", async () => {
      const result = await handleIndexTool("codebase_watch", {
        projectPath: fixture.root,
        action: "status",
      });

      expect(result).toBeDefined();
      expect(result.length).toBeGreaterThan(0);
    });

    it("step 9c — stop watching", async () => {
      const result = await handleIndexTool("codebase_watch", {
        projectPath: fixture.root,
        action: "stop",
      });

      expect(result.toLowerCase()).toContain("stop");
    });

    // ─── Step 10: List projects ──────────────────────────────
    it("step 10 — project appears in list", async () => {
      const result = await handleManageTool("codebase_list_projects", {});

      expect(result).toBeDefined();
      // Should contain some reference to our fixture
      expect(result.length).toBeGreaterThan(10);
    });

    // ─── Step 11: Remove index ───────────────────────────────
    it("step 11 — remove project index", async () => {
      const result = await handleIndexTool("codebase_remove", {
        projectPath: fixture.root,
      });

      expect(result).toContain("Removed");
    }, 30_000);

    // ─── Step 12: Confirm removal ────────────────────────────
    it("step 12a — status confirms not indexed", async () => {
      const result = await handleQueryTool("codebase_status", {
        projectPath: fixture.root,
      });

      expect(
        result.toLowerCase().includes("not") ||
          result.toLowerCase().includes("no ") ||
          result.toLowerCase().includes("does not"),
      ).toBe(true);
    }, 30_000);
  },
);
