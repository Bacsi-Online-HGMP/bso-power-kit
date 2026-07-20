// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

/**
 * Unit tests for the ensureOllamaReady conditional guard in context-tools.ts.
 * Verifies that codebase_context_index and codebase_context_search only call
 * ensureOllamaReady() for the Ollama provider, and use getEmbeddingProvider()
 * for OpenAI/Google.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock("../../src/services/logger.js", () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// ── embedding-config.js mock ─────────────────────────────────────────────

const mockGetEmbeddingConfig = vi.fn(() => ({
  embeddingProvider: "ollama" as string,
  embeddingModel: "test-model",
}));

vi.mock("../../src/services/embedding-config.js", () => ({
  getEmbeddingConfig: (...args: unknown[]) => mockGetEmbeddingConfig(...(args as [])),
}));

// ── embedding-provider.js mock ───────────────────────────────────────────

const mockGetEmbeddingProvider = vi.fn(async () => ({
  embed: vi.fn(),
  ensureReady: vi.fn(async () => ({ imagePulled: false, containerStarted: false, modelPulled: false })),
  health: vi.fn(),
}));

vi.mock("../../src/services/embedding-provider.js", () => ({
  getEmbeddingProvider: (...args: unknown[]) => mockGetEmbeddingProvider(...(args as [])),
}));

// ── ollama.js mock ───────────────────────────────────────────────────────

const mockEnsureOllamaReady = vi.fn(async () => ({
  modelPulled: false,
  containerStarted: false,
  imagePulled: false,
}));

vi.mock("../../src/services/ollama.js", () => ({
  ensureOllamaReady: (...args: unknown[]) => mockEnsureOllamaReady(...(args as [])),
}));

// ── docker.js mock ───────────────────────────────────────────────────────

vi.mock("../../src/services/docker.js", () => ({
  ensureQdrantReady: vi.fn(async () => ({ pulled: false, started: false })),
  isDockerAvailable: vi.fn(async () => true),
}));

// ── qdrant.js mock ───────────────────────────────────────────────────────

vi.mock("../../src/services/qdrant.js", () => ({
  getCollectionInfo: vi.fn(async () => null),
  loadContextMetadata: vi.fn(async () => null),
}));

// ── config.js mock ───────────────────────────────────────────────────────

vi.mock("../../src/config.js", () => ({
  projectIdFromPath: vi.fn(() => "test-project-id"),
  contextCollectionName: vi.fn(() => "context_test"),
}));

// ── indexer.js mock ──────────────────────────────────────────────────────

vi.mock("../../src/services/indexer.js", () => ({
  isIndexingInProgress: vi.fn(() => false),
}));

// ── context-artifacts.js mock ───────────────────────────────────────────

const mockIndexAllArtifacts = vi.fn(async (_path: string) => ({ indexed: [], errors: [] }));
const mockSearchArtifacts = vi.fn(async (_collection: string, _query: string, _limit: number) => []);

vi.mock("../../src/services/context-artifacts.js", () => ({
  loadConfig: vi.fn(async () => ({
    artifacts: [{ name: "test", type: "file", path: "test.md" }],
  })),
  indexAllArtifacts: (...args: unknown[]) => mockIndexAllArtifacts(...(args as [string])),
  searchArtifacts: (...args: unknown[]) => mockSearchArtifacts(...(args as [string, string, number])),
  ensureArtifactsIndexed: vi.fn(async () => ({ reindexed: [], upToDate: [], errors: [] })),
  removeAllArtifacts: vi.fn(async () => {}),
}));

// ── Imports (after mocks) ────────────────────────────────────────────────

import { handleContextTool } from "../../src/tools/context-tools.js";

// ── Tests ────────────────────────────────────────────────────────────────

const TEST_PATH = "/tmp/test-project";

describe("codebase_context_index — embedding provider readiness guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls ensureOllamaReady when embeddingProvider is ollama", async () => {
    mockGetEmbeddingConfig.mockReturnValue({
      embeddingProvider: "ollama",
      embeddingModel: "test-model",
    });

    await handleContextTool("codebase_context_index", {
      projectPath: TEST_PATH,
    });

    expect(mockEnsureOllamaReady).toHaveBeenCalledOnce();
    expect(mockGetEmbeddingProvider).not.toHaveBeenCalled();
  });

  it("calls getEmbeddingProvider (not ensureOllamaReady) when embeddingProvider is openai", async () => {
    mockGetEmbeddingConfig.mockReturnValue({
      embeddingProvider: "openai",
      embeddingModel: "text-embedding-3-small",
    });

    await handleContextTool("codebase_context_index", {
      projectPath: TEST_PATH,
    });

    expect(mockEnsureOllamaReady).not.toHaveBeenCalled();
    expect(mockGetEmbeddingProvider).toHaveBeenCalledOnce();
  });
});

describe("codebase_context_search — embedding provider readiness guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls ensureOllamaReady when embeddingProvider is ollama", async () => {
    mockGetEmbeddingConfig.mockReturnValue({
      embeddingProvider: "ollama",
      embeddingModel: "test-model",
    });

    await handleContextTool("codebase_context_search", {
      projectPath: TEST_PATH,
      query: "test query",
    });

    expect(mockEnsureOllamaReady).toHaveBeenCalledOnce();
    expect(mockGetEmbeddingProvider).not.toHaveBeenCalled();
  });

  it("calls getEmbeddingProvider (not ensureOllamaReady) when embeddingProvider is openai", async () => {
    mockGetEmbeddingConfig.mockReturnValue({
      embeddingProvider: "openai",
      embeddingModel: "text-embedding-3-small",
    });

    await handleContextTool("codebase_context_search", {
      projectPath: TEST_PATH,
      query: "test query",
    });

    expect(mockEnsureOllamaReady).not.toHaveBeenCalled();
    expect(mockGetEmbeddingProvider).toHaveBeenCalledOnce();
  });

  it("calls getEmbeddingProvider (not ensureOllamaReady) when embeddingProvider is google", async () => {
    mockGetEmbeddingConfig.mockReturnValue({
      embeddingProvider: "google",
      embeddingModel: "gemini-embedding-001",
    });

    await handleContextTool("codebase_context_search", {
      projectPath: TEST_PATH,
      query: "test query",
    });

    expect(mockEnsureOllamaReady).not.toHaveBeenCalled();
    expect(mockGetEmbeddingProvider).toHaveBeenCalledOnce();
  });
});
