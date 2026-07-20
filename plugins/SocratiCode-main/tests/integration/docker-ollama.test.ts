// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
import { beforeAll, describe, expect, it } from "vitest";
import {
  ensureOllamaContainerReady,
  ensureQdrantReady,
  isOllamaImagePresent,
  isOllamaRunning,
  isQdrantImagePresent,
  isQdrantRunning,
  resetOllamaContainerReadinessCache,
  resetQdrantReadinessCache,
  isDockerAvailable as srcIsDockerAvailable,
} from "../../src/services/docker.js";
import {
  ensureOllamaReady,
  isModelAvailable,
  isOllamaAvailable,
  resetOllamaReadinessCache,
} from "../../src/services/ollama.js";
import { isDockerAvailable } from "../helpers/fixtures.js";

const dockerAvailable = isDockerAvailable();

describe.skipIf(!dockerAvailable)("docker service", () => {
  beforeAll(() => {
    resetQdrantReadinessCache();
  });

  describe("isDockerAvailable", () => {
    it("returns true when Docker is running", async () => {
      const result = await srcIsDockerAvailable();
      expect(result).toBe(true);
    });
  });

  describe("Qdrant container management", () => {
    it("ensures Qdrant is ready (pulls image and starts container if needed)", async () => {
      resetQdrantReadinessCache();
      const result = await ensureQdrantReady();

      expect(result).toBeDefined();
      expect(typeof result.pulled).toBe("boolean");
      expect(typeof result.started).toBe("boolean");
    });

    it("reports Qdrant image as present after ensure", async () => {
      const present = await isQdrantImagePresent();
      expect(present).toBe(true);
    });

    it("reports Qdrant as running after ensure", async () => {
      const running = await isQdrantRunning();
      expect(running).toBe(true);
    });

    it("returns cached result on second call (no re-pull or re-start)", async () => {
      const result = await ensureQdrantReady();
      // On second call, should not pull or start again (cached)
      expect(result.pulled).toBe(false);
      expect(result.started).toBe(false);
    });

    it("re-checks after cache reset", async () => {
      resetQdrantReadinessCache();
      const result = await ensureQdrantReady();
      // Should succeed but not necessarily pull/start since it's already running
      expect(result).toBeDefined();
    });
  });
});

describe.skipIf(!dockerAvailable)("ollama service", () => {
  beforeAll(async () => {
    resetOllamaReadinessCache();
    // Ensure Qdrant is up first (so Docker is ready), then Ollama
    await ensureQdrantReady();
  });

  describe("Ollama container management", () => {
    it("ensures Ollama container is ready", async () => {
      resetOllamaReadinessCache();
      const result = await ensureOllamaContainerReady();

      expect(result).toBeDefined();
      expect(typeof result.pulled).toBe("boolean");
      expect(typeof result.started).toBe("boolean");
    });

    it("reports Ollama image as present", async () => {
      const present = await isOllamaImagePresent();
      expect(present).toBe(true);
    });

    it("reports Ollama as running", async () => {
      const running = await isOllamaRunning();
      expect(running).toBe(true);
    });

    it("re-checks after Ollama container readiness cache reset", async () => {
      resetOllamaContainerReadinessCache();
      const result = await ensureOllamaContainerReady();
      // Container is already running — should succeed without pulling or starting
      expect(result).toBeDefined();
      expect(typeof result.pulled).toBe("boolean");
      expect(typeof result.started).toBe("boolean");
    });
  });

  describe("Ollama model management", () => {
    it("ensures Ollama (with model) is fully ready", async () => {
      resetOllamaReadinessCache();
      const result = await ensureOllamaReady();

      expect(result).toBeDefined();
      expect(typeof result.modelPulled).toBe("boolean");
    });

    it("reports Ollama as available (HTTP reachable)", async () => {
      const available = await isOllamaAvailable();
      expect(available).toBe(true);
    });

    it("reports the embedding model as available", async () => {
      const available = await isModelAvailable();
      expect(available).toBe(true);
    });
  });
});
