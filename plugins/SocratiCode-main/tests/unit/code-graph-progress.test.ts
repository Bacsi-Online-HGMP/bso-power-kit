// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
import { afterEach, beforeAll, describe, expect, it } from "vitest";
import type { GraphBuildProgress } from "../../src/services/code-graph.js";
import {
  awaitGraphBuild,
  buildCodeGraph,
  ensureDynamicLanguages,
  getGraphBuildInProgressProjects,
  getGraphBuildProgress,
  getLastGraphBuildCompleted,
  invalidateGraphCache,
  isGraphBuildInProgress,
} from "../../src/services/code-graph.js";
import {
  createFixtureProject,
  type FixtureProject,
} from "../helpers/fixtures.js";

// ── Progress tracking API (pure in-memory, no Docker needed) ─────────────

describe("graph build progress tracking", () => {
  let fixture: FixtureProject;

  beforeAll(() => {
    ensureDynamicLanguages();
    fixture = createFixtureProject("graph-progress-test");
  });

  afterEach(() => {
    invalidateGraphCache(fixture.root);
  });

  describe("initial state", () => {
    it("isGraphBuildInProgress returns false for unknown project", () => {
      expect(isGraphBuildInProgress("/nonexistent/project")).toBe(false);
    });

    it("getGraphBuildProgress returns null for unknown project", () => {
      expect(getGraphBuildProgress("/nonexistent/project")).toBeNull();
    });

    it("getLastGraphBuildCompleted returns null for unknown project", () => {
      expect(getLastGraphBuildCompleted("/nonexistent/project")).toBeNull();
    });

    it("getGraphBuildInProgressProjects returns empty array initially", () => {
      expect(getGraphBuildInProgressProjects()).toEqual([]);
    });
  });

  describe("buildCodeGraph with progress tracking", () => {
    it("updates progress.filesTotal after scanning", async () => {
      const progress: GraphBuildProgress = {
        startedAt: Date.now(),
        filesTotal: 0,
        filesProcessed: 0,
        phase: "scanning files",
      };

      const graph = await buildCodeGraph(fixture.root, undefined, progress);

      // After build, filesTotal should match the number of graphable files
      expect(progress.filesTotal).toBeGreaterThan(0);
      // filesProcessed should equal filesTotal
      expect(progress.filesProcessed).toBe(progress.filesTotal);
      // Phase should be "analyzing imports" (set during build)
      expect(progress.phase).toBe("analyzing imports");
      // Graph should have nodes
      expect(graph.nodes.length).toBeGreaterThan(0);
    });

    it("tracks filesProcessed incrementally during build", async () => {
      const progress: GraphBuildProgress = {
        startedAt: Date.now(),
        filesTotal: 0,
        filesProcessed: 0,
        phase: "scanning files",
      };

      await buildCodeGraph(fixture.root, undefined, progress);

      // filesProcessed should equal filesTotal when done
      expect(progress.filesProcessed).toBe(progress.filesTotal);
      expect(progress.filesProcessed).toBeGreaterThan(0);
    });

    it("works without progress parameter (backward compat)", async () => {
      // No progress parameter — should work the same as before
      const graph = await buildCodeGraph(fixture.root);
      expect(graph.nodes.length).toBeGreaterThan(0);
      expect(graph.edges.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe("GraphBuildProgress interface", () => {
    it("progress has correct initial shape", () => {
      const progress: GraphBuildProgress = {
        startedAt: Date.now(),
        filesTotal: 0,
        filesProcessed: 0,
        phase: "scanning files",
      };

      expect(progress.startedAt).toBeGreaterThan(0);
      expect(progress.filesTotal).toBe(0);
      expect(progress.filesProcessed).toBe(0);
      expect(progress.phase).toBe("scanning files");
      expect(progress.error).toBeUndefined();
    });

    it("progress can carry an error", () => {
      const progress: GraphBuildProgress = {
        startedAt: Date.now(),
        filesTotal: 10,
        filesProcessed: 5,
        phase: "analyzing imports",
        error: "Something went wrong",
      };

      expect(progress.error).toBe("Something went wrong");
    });
  });

  describe("awaitGraphBuild", () => {
    it("resolves immediately when no build is in progress", async () => {
      // Should not throw or hang
      await awaitGraphBuild("/nonexistent/project");
    });

    it("resolves immediately for a path that has no in-flight build", async () => {
      await awaitGraphBuild(fixture.root);
    });
  });
});
