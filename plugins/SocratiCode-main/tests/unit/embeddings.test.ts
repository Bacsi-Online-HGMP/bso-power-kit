// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetEmbeddingConfig } from "../../src/services/embedding-config.js";
import { resetEmbeddingProvider } from "../../src/services/embedding-provider.js";
import type { EmbeddingProvider } from "../../src/services/embedding-types.js";
import { generateEmbeddings, generateQueryEmbedding, prepareDocumentText } from "../../src/services/embeddings.js";

// ── Mock the provider factory ────────────────────────────────────────────────
// We mock at the module level so pure unit tests never touch Docker/Ollama/API.
vi.mock("../../src/services/embedding-provider.js", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../src/services/embedding-provider.js")>();
  return {
    ...original,
    getEmbeddingProvider: vi.fn(),
  };
});

// Import the mocked version for type-safe access
import { getEmbeddingProvider } from "../../src/services/embedding-provider.js";

// ── Helper ───────────────────────────────────────────────────────────────────

/** Build a fake provider whose embed() returns predictable unit vectors. */
function makeMockProvider(embedImpl?: (texts: string[]) => Promise<number[][]>) {
  const defaultEmbed = async (texts: string[]) => texts.map(() => [0.1, 0.2, 0.3]);
  return {
    name: "mock",
    embed: vi.fn(embedImpl ?? defaultEmbed),
    embedSingle: vi.fn(async (_text: string) => [0.1, 0.2, 0.3]),
    ensureReady: vi.fn(async () => ({ modelPulled: false, containerStarted: false, imagePulled: false })),
    healthCheck: vi.fn(async () => ({ available: true, modelReady: true, statusLines: [] })),
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("embeddings", () => {
  // ── prepareDocumentText ────────────────────────────────────────────────────

  describe("prepareDocumentText", () => {
    it("prepends search_document prefix with file path", () => {
      const result = prepareDocumentText("const x = 1;", "src/index.ts");
      expect(result).toBe("search_document: src/index.ts\nconst x = 1;");
    });

    it("handles empty content", () => {
      const result = prepareDocumentText("", "file.ts");
      expect(result).toBe("search_document: file.ts\n");
    });

    it("handles multi-line content", () => {
      const content = "line1\nline2\nline3";
      const result = prepareDocumentText(content, "src/utils.py");
      expect(result.startsWith("search_document: src/utils.py\n")).toBe(true);
      expect(result).toContain("line1\nline2\nline3");
    });

    it("handles paths with directories", () => {
      const result = prepareDocumentText("code", "src/services/deep/file.ts");
      expect(result).toBe("search_document: src/services/deep/file.ts\ncode");
    });

    it("handles special characters in content", () => {
      const content = "const regex = /^import\\s+(.+)/;";
      const result = prepareDocumentText(content, "test.ts");
      expect(result).toContain(content);
    });
  });

  // ── generateEmbeddings ─────────────────────────────────────────────────────

  describe("generateEmbeddings", () => {
    const mockedGetProvider = vi.mocked(getEmbeddingProvider);

    beforeEach(() => {
      resetEmbeddingConfig();
      resetEmbeddingProvider();
      vi.clearAllMocks();
    });

    afterEach(() => {
      resetEmbeddingConfig();
      resetEmbeddingProvider();
      vi.restoreAllMocks();
    });

    it("returns empty array immediately for empty input (no provider call)", async () => {
      const provider = makeMockProvider();
      mockedGetProvider.mockResolvedValue(provider as unknown as EmbeddingProvider);
      const result = await generateEmbeddings([]);
      expect(result).toEqual([]);
      expect(provider.embed).not.toHaveBeenCalled();
    });

    it("passes texts through a single batch when count ≤ 32", async () => {
      const provider = makeMockProvider();
      mockedGetProvider.mockResolvedValue(provider as unknown as EmbeddingProvider);

      const texts = Array.from({ length: 5 }, (_, i) => `text ${i}`);
      const result = await generateEmbeddings(texts);

      expect(provider.embed).toHaveBeenCalledTimes(1);
      expect(provider.embed).toHaveBeenCalledWith(texts);
      expect(result).toHaveLength(5);
      for (const emb of result) {
        expect(emb).toEqual([0.1, 0.2, 0.3]);
      }
    });

    it("splits into multiple batches when count > 32 and merges results in order", async () => {
      // 33 texts → batch 1: [0..31], batch 2: [32]
      const BATCH_SIZE = 32;
      const texts = Array.from({ length: 33 }, (_, i) => `text-${i}`);
      // Each embed call returns distinct vectors so we can verify ordering
      const provider = makeMockProvider(async (batch) =>
        batch.map((_, j) => [Number(batch[j].replace("text-", ""))])
      );
      mockedGetProvider.mockResolvedValue(provider as unknown as EmbeddingProvider);

      const result = await generateEmbeddings(texts);

      expect(provider.embed).toHaveBeenCalledTimes(2);
      expect(provider.embed).toHaveBeenNthCalledWith(1, texts.slice(0, BATCH_SIZE));
      expect(provider.embed).toHaveBeenNthCalledWith(2, texts.slice(BATCH_SIZE));
      expect(result).toHaveLength(33);
      // Verify embeddings are in the original order: result[i] = [i]
      for (let i = 0; i < result.length; i++) {
        expect(result[i]).toEqual([i]);
      }
    });

    it("calls onBatchComplete with correct progress after each batch", async () => {
      const texts = Array.from({ length: 65 }, (_, i) => `text-${i}`);
      const provider = makeMockProvider();
      mockedGetProvider.mockResolvedValue(provider as unknown as EmbeddingProvider);

      const progress: Array<{ processed: number; total: number }> = [];
      await generateEmbeddings(texts, (processed, total) => {
        progress.push({ processed, total });
      });

      // 65 texts → 3 batches of 32, 32, 1
      expect(progress).toHaveLength(3);
      expect(progress[0]).toEqual({ processed: 32, total: 65 });
      expect(progress[1]).toEqual({ processed: 64, total: 65 });
      expect(progress[2]).toEqual({ processed: 65, total: 65 });
    });

    it("retries on provider failure and succeeds on second attempt", async () => {
      let calls = 0;
      const provider = makeMockProvider(async () => {
        calls++;
        if (calls === 1) throw new Error("transient network error");
        return [[0.5, 0.6]];
      });
      mockedGetProvider.mockResolvedValue(provider as unknown as EmbeddingProvider);

      // Speed up retry delay to avoid slow tests
      vi.useFakeTimers();
      const resultPromise = generateEmbeddings(["text"]);
      // Advance timers for the exponential backoff (500ms base * 2^0 = 500ms)
      await vi.runAllTimersAsync();
      const result = await resultPromise;
      vi.useRealTimers();

      expect(result).toEqual([[0.5, 0.6]]);
      expect(provider.embed).toHaveBeenCalledTimes(2);
    });

    it("throws after MAX_RETRIES (3) exhausted", async () => {
      // Use fake timers to skip the exponential backoff delays without real waits
      vi.useFakeTimers();

      const provider = makeMockProvider(async () => {
        throw new Error("persistent provider failure");
      });
      mockedGetProvider.mockResolvedValue(provider as unknown as EmbeddingProvider);

      const rejected = generateEmbeddings(["text"]).then(
        () => false as const,
        () => true as const,
      );
      // Advance through all backoff delays (500ms + 1000ms = 1500ms)
      await vi.advanceTimersByTimeAsync(3000);
      vi.useRealTimers();

      expect(await rejected).toBe(true);
      expect(provider.embed).toHaveBeenCalledTimes(3);
    }, 10_000);
  });

  // ── generateQueryEmbedding ─────────────────────────────────────────────────

  describe("generateQueryEmbedding", () => {
    const mockedGetProvider = vi.mocked(getEmbeddingProvider);

    beforeEach(() => {
      resetEmbeddingConfig();
      resetEmbeddingProvider();
      vi.clearAllMocks();
    });

    afterEach(() => {
      resetEmbeddingConfig();
      resetEmbeddingProvider();
      vi.restoreAllMocks();
    });

    it("calls provider.embedSingle with search_query prefix", async () => {
      const provider = makeMockProvider();
      mockedGetProvider.mockResolvedValue(provider as unknown as EmbeddingProvider);

      const result = await generateQueryEmbedding("find auth logic");

      expect(provider.embedSingle).toHaveBeenCalledWith("search_query: find auth logic");
      expect(result).toEqual([0.1, 0.2, 0.3]);
    });

    it("retries on transient failure", async () => {
      let calls = 0;
      const provider = makeMockProvider();
      provider.embedSingle = vi.fn(async () => {
        calls++;
        if (calls === 1) throw new Error("timeout");
        return [0.7, 0.8];
      });
      mockedGetProvider.mockResolvedValue(provider as unknown as EmbeddingProvider);

      vi.useFakeTimers();
      const resultPromise = generateQueryEmbedding("test");
      await vi.runAllTimersAsync();
      vi.useRealTimers();

      const result = await resultPromise;
      expect(result).toEqual([0.7, 0.8]);
      expect(provider.embedSingle).toHaveBeenCalledTimes(2);
    });
  });
});
