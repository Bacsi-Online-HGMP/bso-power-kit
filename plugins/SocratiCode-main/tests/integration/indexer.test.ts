// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { collectionName, projectIdFromPath } from "../../src/config.js";
import { ensureQdrantReady } from "../../src/services/docker.js";
import {
  getIndexableFiles,
  getIndexingInProgressProjects,
  getLastCompleted,
  indexProject,
  isIndexingInProgress,
  removeProjectIndex,
  updateProjectIndex,
} from "../../src/services/indexer.js";
import { ensureOllamaReady } from "../../src/services/ollama.js";
import { getCollectionInfo, searchChunks } from "../../src/services/qdrant.js";
import {
  addFileToFixture,
  createFixtureProject,
  type FixtureProject,
  isDockerAvailable,
  removeFixtureFile,
} from "../helpers/fixtures.js";
import { cleanupTestCollections, waitForOllama, waitForQdrant } from "../helpers/setup.js";

const dockerAvailable = isDockerAvailable();

describe.skipIf(!dockerAvailable)("indexer service", () => {
  let fixture: FixtureProject;
  let collection: string;

  beforeAll(async () => {
    await ensureQdrantReady();
    await ensureOllamaReady();
    await waitForQdrant();
    await waitForOllama();

    fixture = createFixtureProject("indexer-test");
    const projectId = projectIdFromPath(fixture.root);
    collection = collectionName(projectId);
  });

  afterAll(async () => {
    // Clean up: remove index and temp directory
    try {
      await removeProjectIndex(fixture.root);
    } catch {
      // ignore
    }
    fixture.cleanup();
    await cleanupTestCollections(fixture.root);
  });

  describe("getIndexableFiles", () => {
    it("returns files with supported extensions", async () => {
      const files = await getIndexableFiles(fixture.root);

      expect(files.length).toBeGreaterThan(0);

      // Should include our fixture files
      const fileNames = files.map((f) => path.basename(f));
      expect(fileNames).toContain("index.ts");
      expect(fileNames).toContain("types.ts");
      expect(fileNames).toContain("helpers.ts");
      expect(fileNames).toContain("math.ts");
      expect(fileNames).toContain("data_processor.py");
      expect(fileNames).toContain("README.md");
    });

    it("respects .gitignore rules", async () => {
      const files = await getIndexableFiles(fixture.root);

      // .gitignore has "*.log" — no log files should appear
      for (const f of files) {
        expect(f).not.toMatch(/\.log$/);
      }
    });

    it("includes special files like README and package.json", async () => {
      const files = await getIndexableFiles(fixture.root);
      const fileNames = files.map((f) => path.basename(f));

      // README.md and package.json are special files that get indexed
      expect(fileNames).toContain("README.md");
      expect(fileNames).toContain("package.json");

      // Dotfiles are excluded by glob (dot: false)
      expect(fileNames).not.toContain(".gitignore");
    });

    it("excludes node_modules", async () => {
      const files = await getIndexableFiles(fixture.root);
      for (const f of files) {
        expect(f).not.toContain("node_modules");
      }
    });
  });

  describe("indexProject (full index)", () => {
    const progressMessages: string[] = [];

    it("indexes the fixture project with real embeddings", async () => {
      const result = await indexProject(fixture.root, (msg) => {
        progressMessages.push(msg);
      });

      expect(result.filesIndexed).toBeGreaterThan(0);
      expect(result.chunksCreated).toBeGreaterThan(0);
    }, 180_000); // Allow up to 3 minutes for first-time embedding

    it("reports progress during indexing", () => {
      expect(progressMessages.length).toBeGreaterThan(0);
      // Should have messages about finding files and indexing
      expect(progressMessages.some((m) => m.includes("indexable files"))).toBe(true);
    });

    it("creates a Qdrant collection with indexed chunks", async () => {
      const info = await getCollectionInfo(collection);
      expect(info).toBeDefined();
      expect(info?.pointsCount).toBeGreaterThan(0);
    });

    it("tracks last completed indexing", () => {
      const completed = getLastCompleted(fixture.root);
      expect(completed).toBeDefined();
      expect(completed?.type).toBe("full-index");
      expect(completed?.filesProcessed).toBeGreaterThan(0);
      expect(completed?.chunksCreated).toBeGreaterThan(0);
      expect(completed?.durationMs).toBeGreaterThan(0);
      expect(completed?.error).toBeUndefined();
    });

    it("is no longer in progress after completion", () => {
      expect(isIndexingInProgress(fixture.root)).toBe(false);
    });

    it("no projects are in progress", () => {
      const inProgress = getIndexingInProgressProjects();
      expect(inProgress).not.toContain(path.resolve(fixture.root));
    });
  });

  describe("search after indexing", () => {
    it("finds authentication code via semantic search", async () => {
      const results = await searchChunks(
        collection,
        "user authentication with JWT token validation",
        5,
      );

      expect(results.length).toBeGreaterThan(0);
      // Should find the authenticateUser function from src/index.ts
      const authResult = results.find((r) => r.content.includes("authenticateUser"));
      expect(authResult).toBeDefined();
    });

    it("finds mathematical functions via semantic search", async () => {
      const results = await searchChunks(
        collection,
        "fibonacci sequence calculation",
        5,
      );

      expect(results.length).toBeGreaterThan(0);
      const mathResult = results.find((r) => r.content.includes("fibonacci"));
      expect(mathResult).toBeDefined();
    });

    it("finds Python code via semantic search", async () => {
      const results = await searchChunks(
        collection,
        "data processing JSON file loading",
        5,
      );

      expect(results.length).toBeGreaterThan(0);
      const pyResult = results.find((r) => r.language === "python");
      expect(pyResult).toBeDefined();
    });

    it("finds helper utilities via semantic search", async () => {
      const results = await searchChunks(
        collection,
        "string formatting title case conversion",
        5,
      );

      expect(results.length).toBeGreaterThan(0);
      const helperResult = results.find(
        (r) => r.content.includes("toTitleCase") || r.content.includes("greet"),
      );
      expect(helperResult).toBeDefined();
    });
  });

  describe("updateProjectIndex (incremental)", () => {
    it("detects no changes when nothing has changed", async () => {
      const result = await updateProjectIndex(fixture.root);

      // Nothing changed, so minimal or zero updates
      expect(result.added).toBe(0);
      expect(result.updated).toBe(0);
      expect(result.removed).toBe(0);
    }, 120_000);

    it("detects a new file", async () => {
      // Add a new file to the fixture
      addFileToFixture(
        fixture.root,
        "src/newfeature.ts",
        `/**
 * A brand new feature for handling webhook events.
 * Processes incoming HTTP webhook payloads.
 */
export function handleWebhook(payload: unknown): { status: string } {
  if (!payload) return { status: "empty" };
  return { status: "processed" };
}
`,
      );

      const result = await updateProjectIndex(fixture.root, (_msg) => {
        // Just capture progress silently
      });

      expect(result.added).toBeGreaterThanOrEqual(1);
    }, 120_000);

    it("finds the newly added file in search results", async () => {
      const results = await searchChunks(
        collection,
        "webhook event handling HTTP payload processing",
        5,
      );

      expect(results.length).toBeGreaterThan(0);
      const webhookResult = results.find((r) => r.content.includes("handleWebhook"));
      expect(webhookResult).toBeDefined();
    });

    it("detects removed files", async () => {
      removeFixtureFile(fixture.root, "src/newfeature.ts");

      const result = await updateProjectIndex(fixture.root);
      expect(result.removed).toBeGreaterThanOrEqual(1);
    }, 120_000);
  });

  describe("removeProjectIndex", () => {
    it("removes the entire index for the project", async () => {
      await removeProjectIndex(fixture.root);

      const info = await getCollectionInfo(collection);
      expect(info).toBeNull();
    });
  });
});
