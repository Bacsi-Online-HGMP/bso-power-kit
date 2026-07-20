// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
//
// Tests for issue #55: re-thrown Qdrant errors must surface with operation
// context (function name, parameters, status code, original message) instead
// of the bare "Internal Server Error" the Qdrant REST client produces. Without
// this wrapping the only signal a tool consumer gets via MCP is the literal
// string "Internal Server Error" with no clue about which operation failed.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/services/logger.js", () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

const mockGetCollection = vi.fn();
const mockGetCollections = vi.fn();
const mockRetrieve = vi.fn();
const mockCreateCollection = vi.fn();
const mockCreatePayloadIndex = vi.fn();

vi.mock("@qdrant/js-client-rest", () => ({
  QdrantClient: class {
    getCollection = mockGetCollection;
    getCollections = mockGetCollections;
    retrieve = mockRetrieve;
    createCollection = mockCreateCollection;
    createPayloadIndex = mockCreatePayloadIndex;
  },
}));

describe("qdrant error wrapping (issue #55)", () => {
  beforeEach(() => {
    vi.resetModules();
    mockGetCollection.mockReset();
    mockGetCollections.mockReset();
    mockRetrieve.mockReset();
    mockCreateCollection.mockReset();
    mockCreatePayloadIndex.mockReset();
    // Default: metadata collection already exists, so ensureMetadataCollection
    // returns without trying to create one. Tests that need a fresh state
    // override this in their own setup.
    mockGetCollections.mockResolvedValue({
      collections: [{ name: "socraticode_metadata" }],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("getCollectionInfo", () => {
    it("still returns null on 404 (collection-not-found is not an error)", async () => {
      const notFound: Error & { status?: number } = new Error("Not found");
      notFound.status = 404;
      mockGetCollection.mockRejectedValueOnce(notFound);

      const { getCollectionInfo } = await import("../../src/services/qdrant.js");
      const result = await getCollectionInfo("missing_collection");
      expect(result).toBeNull();
    });

    it("wraps non-404 errors with operation name, collection, and status", async () => {
      const serverErr: Error & { status?: number } = new Error("Internal Server Error");
      serverErr.status = 500;
      mockGetCollection.mockRejectedValueOnce(serverErr);

      const { getCollectionInfo } = await import("../../src/services/qdrant.js");
      await expect(getCollectionInfo("some_collection")).rejects.toThrow(
        /getCollectionInfo\(collection=some_collection\) failed \[status 500\]: Internal Server Error/,
      );
    });

    it("preserves the original error via `cause`", async () => {
      const originalErr: Error & { status?: number } = new Error("boom");
      originalErr.status = 503;
      mockGetCollection.mockRejectedValueOnce(originalErr);

      const { getCollectionInfo } = await import("../../src/services/qdrant.js");
      try {
        await getCollectionInfo("c1");
        expect.fail("expected throw");
      } catch (err) {
        expect((err as Error & { cause?: unknown }).cause).toBe(originalErr);
      }
    });
  });

  describe("loadProjectHashes", () => {
    it("wraps Qdrant errors with collName context", async () => {
      const serverErr: Error & { status?: number } = new Error("Internal Server Error");
      serverErr.status = 500;
      mockRetrieve.mockRejectedValueOnce(serverErr);

      const { loadProjectHashes } = await import("../../src/services/qdrant.js");
      await expect(loadProjectHashes("codebase_xyz")).rejects.toThrow(
        /loadProjectHashes\(collName=codebase_xyz\) failed \[status 500\]: Internal Server Error/,
      );
    });

    it("includes original error as `cause`", async () => {
      const original: Error & { statusCode?: number } = new Error("connection refused");
      original.statusCode = 502;
      mockRetrieve.mockRejectedValueOnce(original);

      const { loadProjectHashes } = await import("../../src/services/qdrant.js");
      try {
        await loadProjectHashes("codebase_abc");
        expect.fail("expected throw");
      } catch (err) {
        expect((err as Error).message).toContain("loadProjectHashes(collName=codebase_abc)");
        expect((err as Error).message).toContain("[status 502]");
        expect((err as Error).message).toContain("connection refused");
        expect((err as Error & { cause?: unknown }).cause).toBe(original);
      }
    });

    it("works without a status code on the underlying error", async () => {
      const noStatus: Error = new Error("opaque failure");
      mockRetrieve.mockRejectedValueOnce(noStatus);

      const { loadProjectHashes } = await import("../../src/services/qdrant.js");
      await expect(loadProjectHashes("codebase_no_status")).rejects.toThrow(
        /loadProjectHashes\(collName=codebase_no_status\) failed: opaque failure/,
      );
    });
  });
});
