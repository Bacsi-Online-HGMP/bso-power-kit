// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import { describe, expect, it } from "vitest";

/**
 * BATCH_SIZE is evaluated at module load time via an IIFE, so we can't
 * re-import with different env vars in the same process. Instead we test
 * the validation logic directly — this is the exact same code used in
 * src/services/embeddings.ts.
 */
function parseBatchSize(raw: string | undefined): number {
  if (raw === undefined) return 32;
  const num = Number(raw);
  if (!Number.isInteger(num) || num <= 0) {
    throw new Error(
      `Invalid EMBEDDING_BATCH_SIZE: "${raw}". Must be a positive integer.`,
    );
  }
  return num;
}

describe("EMBEDDING_BATCH_SIZE validation", () => {
  it("returns default 32 when env var is undefined", () => {
    expect(parseBatchSize(undefined)).toBe(32);
  });

  it("accepts a valid positive integer string", () => {
    expect(parseBatchSize("64")).toBe(64);
    expect(parseBatchSize("1")).toBe(1);
    expect(parseBatchSize("128")).toBe(128);
  });

  it("rejects trailing non-digit chars like '64abc' (Number.parseInt would accept this)", () => {
    expect(() => parseBatchSize("64abc")).toThrow("EMBEDDING_BATCH_SIZE");
  });

  it("rejects float-like string '1.5' (Number.parseInt would truncate to 1)", () => {
    expect(() => parseBatchSize("1.5")).toThrow("EMBEDDING_BATCH_SIZE");
  });

  it("rejects zero", () => {
    expect(() => parseBatchSize("0")).toThrow("EMBEDDING_BATCH_SIZE");
  });

  it("rejects negative values", () => {
    expect(() => parseBatchSize("-5")).toThrow("EMBEDDING_BATCH_SIZE");
  });

  it("rejects empty string (Number('') === 0)", () => {
    expect(() => parseBatchSize("")).toThrow("EMBEDDING_BATCH_SIZE");
  });

  it("rejects whitespace-only string", () => {
    expect(() => parseBatchSize("  ")).toThrow("EMBEDDING_BATCH_SIZE");
  });

  it("rejects non-numeric string", () => {
    expect(() => parseBatchSize("abc")).toThrow("EMBEDDING_BATCH_SIZE");
  });
});
