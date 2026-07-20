// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import path from "node:path";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { ensureQdrantReady } from "../../src/services/docker.js";
import { indexProject } from "../../src/services/indexer.js";
import { ensureOllamaReady } from "../../src/services/ollama.js";
import {
  getWatchedProjects,
  isWatching,
  startWatching,
  stopAllWatchers,
  stopWatching,
} from "../../src/services/watcher.js";
import {
  createFixtureProject,
  type FixtureProject,
  isDockerAvailable,
} from "../helpers/fixtures.js";
import { cleanupTestCollections, waitForOllama, waitForQdrant } from "../helpers/setup.js";

const dockerAvailable = isDockerAvailable();

describe.skipIf(!dockerAvailable)("watcher service", () => {
  let fixture: FixtureProject;

  beforeAll(async () => {
    await ensureQdrantReady();
    await ensureOllamaReady();
    await waitForQdrant();
    await waitForOllama();

    fixture = createFixtureProject("watcher-test");

    // Index the project first so the watcher has a collection to update
    await indexProject(fixture.root);
  }, 180_000);

  afterAll(async () => {
    await stopAllWatchers();
    fixture.cleanup();
    await cleanupTestCollections(fixture.root);
  });

  afterEach(async () => {
    // Stop watchers between tests
    if (isWatching(fixture.root)) {
      await stopWatching(fixture.root);
    }
  });

  describe("startWatching / stopWatching", () => {
    it("starts watching a project", async () => {
      await startWatching(fixture.root);
      expect(isWatching(fixture.root)).toBe(true);
    });

    it("includes the project in watched list", async () => {
      await startWatching(fixture.root);
      const watched = getWatchedProjects();
      expect(watched).toContain(path.resolve(fixture.root));
    });

    it("stops watching a project", async () => {
      await startWatching(fixture.root);
      expect(isWatching(fixture.root)).toBe(true);

      await stopWatching(fixture.root);
      expect(isWatching(fixture.root)).toBe(false);
    });

    it("does not error when stopping a non-watched project", async () => {
      await expect(stopWatching("/nonexistent/path")).resolves.not.toThrow();
    });

    it("is idempotent — starting twice does not error", async () => {
      await startWatching(fixture.root);
      await startWatching(fixture.root);
      expect(isWatching(fixture.root)).toBe(true);
    });
  });

  describe("stopAllWatchers", () => {
    it("stops all active watchers", async () => {
      await startWatching(fixture.root);
      expect(getWatchedProjects().length).toBeGreaterThan(0);

      await stopAllWatchers();
      expect(getWatchedProjects()).toHaveLength(0);
    });
  });

  describe("getWatchedProjects", () => {
    it("returns empty list when nothing is watched", async () => {
      await stopAllWatchers();
      expect(getWatchedProjects()).toHaveLength(0);
    });

    it("returns all watched projects", async () => {
      await startWatching(fixture.root);
      const projects = getWatchedProjects();
      expect(projects.length).toBe(1);
      expect(projects[0]).toBe(path.resolve(fixture.root));
    });
  });
});
