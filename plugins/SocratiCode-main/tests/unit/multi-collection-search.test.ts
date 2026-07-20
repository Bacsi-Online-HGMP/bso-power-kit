// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

/**
 * Unit tests for mergeMultiCollectionResults — client-side RRF fusion
 * and deduplication across multiple collection result sets.
 * Tests the pure function directly (no mocks needed).
 */

import { describe, expect, it, vi } from "vitest";
import { mergeMultiCollectionResults } from "../../src/services/qdrant.js";
import type { SearchResult } from "../../src/types.js";

// ── Helpers ─────────────────────────────────────────────────────────────

function makeResult(relativePath: string, score: number, overrides?: Partial<SearchResult>): SearchResult {
  return {
    filePath: `/project/${relativePath}`,
    relativePath,
    content: `content of ${relativePath}`,
    startLine: 1,
    endLine: 10,
    language: "typescript",
    score,
    ...overrides,
  };
}

// ── Tests ────────────────────────────────────────────────────────────────

describe("mergeMultiCollectionResults", () => {
  it("returns empty array for empty input", () => {
    const results = mergeMultiCollectionResults([], 10);
    expect(results).toEqual([]);
  });

  it("returns results from a single collection with project label", () => {
    const results = mergeMultiCollectionResults(
      [
        {
          label: "my-project",
          results: [
            makeResult("src/index.ts", 0.85),
            makeResult("src/utils.ts", 0.72),
          ],
        },
      ],
      10,
    );

    expect(results).toHaveLength(2);
    expect(results[0].project).toBe("my-project");
    expect(results[1].project).toBe("my-project");
    expect(results[0].relativePath).toBe("src/index.ts");
    expect(results[1].relativePath).toBe("src/utils.ts");
  });

  it("merges results from two collections — all unique files present", () => {
    const results = mergeMultiCollectionResults(
      [
        {
          label: "project-a",
          results: [
            makeResult("src/file1.ts", 0.90),
            makeResult("src/file2.ts", 0.80),
          ],
        },
        {
          label: "project-b",
          results: [
            makeResult("src/file3.ts", 0.95),
            makeResult("src/file4.ts", 0.70),
          ],
        },
      ],
      10,
    );

    expect(results).toHaveLength(4);
    const paths = results.map((r) => r.relativePath);
    expect(paths).toContain("src/file1.ts");
    expect(paths).toContain("src/file2.ts");
    expect(paths).toContain("src/file3.ts");
    expect(paths).toContain("src/file4.ts");

    // Correct project labels
    expect(results.find((r) => r.relativePath === "src/file1.ts")?.project).toBe("project-a");
    expect(results.find((r) => r.relativePath === "src/file3.ts")?.project).toBe("project-b");
  });

  it("keeps same relativePath from different projects as separate entries", () => {
    const results = mergeMultiCollectionResults(
      [
        {
          label: "project-a",
          results: [makeResult("src/shared.ts", 0.90, { content: "content from A" })],
        },
        {
          label: "project-b",
          results: [makeResult("src/shared.ts", 0.85, { content: "content from B" })],
        },
      ],
      10,
    );

    // Dedupe key is label::relativePath, so same file in different projects stays separate
    const sharedResults = results.filter((r) => r.relativePath === "src/shared.ts");
    expect(sharedResults).toHaveLength(2);
    expect(sharedResults.map((r) => r.project)).toEqual(
      expect.arrayContaining(["project-a", "project-b"]),
    );
  });

  it("deduplicates same relativePath within the same project", () => {
    const results = mergeMultiCollectionResults(
      [
        {
          label: "project-a",
          results: [
            makeResult("src/shared.ts", 0.90, { content: "first chunk" }),
            makeResult("src/shared.ts", 0.80, { content: "second chunk" }),
          ],
        },
      ],
      10,
    );

    // Same label + same relativePath → deduplicated, first (higher-ranked) wins
    const sharedResults = results.filter((r) => r.relativePath === "src/shared.ts");
    expect(sharedResults).toHaveLength(1);
    expect(sharedResults[0].content).toBe("first chunk");
  });

  it("same relativePath from different projects has independent RRF scores", () => {
    const results = mergeMultiCollectionResults(
      [
        {
          label: "project-a",
          results: [
            makeResult("src/popular.ts", 0.90),
            makeResult("src/only-a.ts", 0.80),
          ],
        },
        {
          label: "project-b",
          results: [
            makeResult("src/popular.ts", 0.85),
            makeResult("src/only-b.ts", 0.75),
          ],
        },
      ],
      10,
    );

    // With label-scoped keys, src/popular.ts from A and B are separate entries
    const popularResults = results.filter((r) => r.relativePath === "src/popular.ts");
    expect(popularResults).toHaveLength(2);

    // Each has a single-collection RRF score: 1/(60+rank)
    // project-a's popular.ts is rank 1 → 1/61
    // project-b's popular.ts is rank 1 → 1/61
    const expectedSingle = 1 / 61;
    for (const r of popularResults) {
      expect(r.score).toBeCloseTo(expectedSingle, 6);
    }
  });

  it("respects the limit parameter", () => {
    const results = mergeMultiCollectionResults(
      [
        {
          label: "a",
          results: [
            makeResult("src/a1.ts", 0.9),
            makeResult("src/a2.ts", 0.8),
            makeResult("src/a3.ts", 0.7),
          ],
        },
        {
          label: "b",
          results: [
            makeResult("src/b1.ts", 0.95),
            makeResult("src/b2.ts", 0.85),
            makeResult("src/b3.ts", 0.75),
          ],
        },
      ],
      3,
    );

    expect(results).toHaveLength(3);
  });

  it("results are sorted by fused RRF score descending", () => {
    const results = mergeMultiCollectionResults(
      [
        {
          label: "a",
          results: [
            makeResult("src/first.ts", 0.90),
            makeResult("src/second.ts", 0.80),
          ],
        },
        {
          label: "b",
          results: [
            makeResult("src/third.ts", 0.95),
          ],
        },
      ],
      10,
    );

    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].score).toBeGreaterThanOrEqual(results[i].score);
    }
  });

  it("handles three collections", () => {
    const results = mergeMultiCollectionResults(
      [
        { label: "a", results: [makeResult("src/a.ts", 0.9)] },
        { label: "b", results: [makeResult("src/b.ts", 0.8)] },
        { label: "c", results: [makeResult("src/c.ts", 0.7)] },
      ],
      10,
    );

    expect(results).toHaveLength(3);
    expect(results.map((r) => r.project)).toEqual(
      expect.arrayContaining(["a", "b", "c"]),
    );
  });

  it("handles empty results from some collections", () => {
    const results = mergeMultiCollectionResults(
      [
        { label: "a", results: [makeResult("src/a.ts", 0.9)] },
        { label: "b", results: [] },
        { label: "c", results: [makeResult("src/c.ts", 0.7)] },
      ],
      10,
    );

    expect(results).toHaveLength(2);
    expect(results.map((r) => r.project)).toEqual(
      expect.arrayContaining(["a", "c"]),
    );
  });
});

// ── searchMultipleCollections tests ─────────────────────────────────────
// searchMultipleCollections calls searchChunks internally (same module),
// so vi.mock cannot intercept those calls. The pure merge logic is
// thoroughly tested above (9 tests). The orchestration layer (includeLinked
// → resolveLinkedCollections → searchMultipleCollections) is tested via
// query-tools.test.ts which mocks at the module boundary.
// Here we only test the empty-input short-circuit which needs no Qdrant.

vi.mock("../../src/services/logger.js", () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

const { searchMultipleCollections } = await import("../../src/services/qdrant.js");

describe("searchMultipleCollections", () => {
  it("returns empty array when collections array is empty", async () => {
    const results = await searchMultipleCollections([], "test", 10);
    expect(results).toEqual([]);
  });
});
