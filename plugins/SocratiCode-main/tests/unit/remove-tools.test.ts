// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

/**
 * Unit tests for the "remove" tool handlers:
 *   - codebase_remove      (index-tools.ts)
 *   - codebase_graph_remove (graph-tools.ts)
 *   - codebase_context_remove (context-tools.ts)
 *
 * All external services are mocked — no Docker required.
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

// ── indexer.js mock ──────────────────────────────────────────────────────

const mockIsIndexingInProgress = vi.fn((_path: string) => false);
const mockRequestCancellation = vi.fn((_path: string) => true);
const mockRemoveProjectIndex = vi.fn(async (_path: string) => {});
const mockGetIndexingProgress = vi.fn((_path: string) => null);
const mockSetIndexingProgress = vi.fn((..._args: unknown[]) => {});
const mockIndexProject = vi.fn(async (..._args: unknown[]) => ({ filesIndexed: 0, chunksCreated: 0, cancelled: false }));
const mockUpdateProjectIndex = vi.fn(async (..._args: unknown[]) => ({ added: 0, updated: 0, removed: 0, chunksCreated: 0, cancelled: false }));

vi.mock("../../src/services/indexer.js", () => ({
  isIndexingInProgress: (...args: unknown[]) => mockIsIndexingInProgress(...(args as [string])),
  requestCancellation: (...args: unknown[]) => mockRequestCancellation(...(args as [string])),
  removeProjectIndex: (...args: unknown[]) => mockRemoveProjectIndex(...(args as [string])),
  getIndexingProgress: (...args: unknown[]) => mockGetIndexingProgress(...(args as [string])),
  setIndexingProgress: (...args: unknown[]) => mockSetIndexingProgress(...args),
  indexProject: (...args: unknown[]) => mockIndexProject(...args),
  updateProjectIndex: (...args: unknown[]) => mockUpdateProjectIndex(...args),
}));

// ── code-graph.js mock ──────────────────────────────────────────────────

const mockIsGraphBuildInProgress = vi.fn((_path: string) => false);
const mockAwaitGraphBuild = vi.fn(async (_path: string) => {});
const mockRemoveGraph = vi.fn(async (_path: string) => {});

vi.mock("../../src/services/code-graph.js", () => ({
  isGraphBuildInProgress: (...args: unknown[]) => mockIsGraphBuildInProgress(...(args as [string])),
  awaitGraphBuild: (...args: unknown[]) => mockAwaitGraphBuild(...(args as [string])),
  removeGraph: (...args: unknown[]) => mockRemoveGraph(...(args as [string])),
  // graph-tools imports — provide stubs for unused functions
  findCircularDependencies: vi.fn(() => []),
  generateMermaidDiagram: vi.fn(() => ""),
  getFileDependencies: vi.fn(() => ({ imports: [], importedBy: [] })),
  getGraphBuildProgress: vi.fn(() => null),
  getGraphStats: vi.fn(),
  getGraphStatus: vi.fn(async () => null),
  getLastGraphBuildCompleted: vi.fn(() => null),
  getOrBuildGraph: vi.fn(async () => ({ nodes: [], edges: [] })),
  rebuildGraph: vi.fn(async () => ({ nodes: [], edges: [] })),
}));

// ── watcher.js mock ─────────────────────────────────────────────────────

const mockIsWatching = vi.fn((_path: string) => false);
const mockStopWatching = vi.fn(async (_path: string) => {});

vi.mock("../../src/services/watcher.js", () => ({
  isWatching: (...args: unknown[]) => mockIsWatching(...(args as [string])),
  stopWatching: (...args: unknown[]) => mockStopWatching(...(args as [string])),
  startWatching: vi.fn(async () => true),
  getWatchedProjects: vi.fn(() => []),
  ensureWatcherStarted: vi.fn(),
}));

// ── docker.js mock ──────────────────────────────────────────────────────

vi.mock("../../src/services/docker.js", () => ({
  ensureQdrantReady: vi.fn(async () => ({ pulled: false, started: false })),
  isDockerAvailable: vi.fn(async () => true),
}));

// ── embedding mocks ─────────────────────────────────────────────────────

vi.mock("../../src/services/embedding-config.js", () => ({
  getEmbeddingConfig: vi.fn(() => ({ embeddingModel: "test-model" })),
}));

vi.mock("../../src/services/embedding-provider.js", () => ({
  getEmbeddingProvider: vi.fn(async () => ({
    ensureReady: async () => ({ imagePulled: false, containerStarted: false, modelPulled: false }),
  })),
}));

// ── lock.js mock ────────────────────────────────────────────────────────

const mockIsProjectLocked = vi.fn(async (_path: string, _op: string) => false);
const mockTerminateLockHolder = vi.fn(async (_path: string, _op: string) => ({ terminated: false, pid: null as number | null }));

vi.mock("../../src/services/lock.js", () => ({
  isProjectLocked: (...args: unknown[]) => mockIsProjectLocked(...(args as [string, string])),
  terminateLockHolder: (...args: unknown[]) => mockTerminateLockHolder(...(args as [string, string])),
}));

// ── context-artifacts.js mock ───────────────────────────────────────────

const mockRemoveAllArtifacts = vi.fn(async (_path: string) => {});

vi.mock("../../src/services/context-artifacts.js", () => ({
  removeAllArtifacts: (...args: unknown[]) => mockRemoveAllArtifacts(...(args as [string])),
  loadConfig: vi.fn(async () => null),
  indexAllArtifacts: vi.fn(async () => ({ indexed: [], errors: [] })),
  ensureArtifactsIndexed: vi.fn(async () => ({ reindexed: [], upToDate: [], errors: [] })),
  searchArtifacts: vi.fn(async () => []),
}));

// ── qdrant.js mock ──────────────────────────────────────────────────────

vi.mock("../../src/services/qdrant.js", () => ({
  getCollectionInfo: vi.fn(async () => null),
  loadContextMetadata: vi.fn(async () => null),
}));

// ── ollama.js mock ──────────────────────────────────────────────────────

vi.mock("../../src/services/ollama.js", () => ({
  ensureOllamaReady: vi.fn(async () => {}),
}));

// ── config.js mock ──────────────────────────────────────────────────────

vi.mock("../../src/config.js", () => ({
  projectIdFromPath: vi.fn(() => "test-project-id"),
  contextCollectionName: vi.fn(() => "context_test"),
}));

// ── constants.js mock ───────────────────────────────────────────────────

vi.mock("../../src/constants.js", async (importOriginal) => {
  const original = await importOriginal<Record<string, unknown>>();
  return { ...original, QDRANT_MODE: "managed" };
});

// ── Imports (after mocks) ────────────────────────────────────────────────

import { handleContextTool } from "../../src/tools/context-tools.js";
import { handleGraphTool } from "../../src/tools/graph-tools.js";
import { handleIndexTool } from "../../src/tools/index-tools.js";

// ── Tests ────────────────────────────────────────────────────────────────

const TEST_PATH = "/tmp/test-project";

describe("codebase_remove — stops all in-flight operations before deleting", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("removes index immediately when nothing is in-flight", async () => {
    const result = await handleIndexTool("codebase_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockRemoveProjectIndex).toHaveBeenCalledOnce();
    expect(mockRequestCancellation).not.toHaveBeenCalled();
    expect(mockAwaitGraphBuild).not.toHaveBeenCalled();
  });

  it("stops the watcher before removing", async () => {
    mockIsWatching.mockReturnValueOnce(true);

    const result = await handleIndexTool("codebase_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockStopWatching).toHaveBeenCalledOnce();
    // Watcher stopped before index removed
    expect(mockStopWatching.mock.invocationCallOrder[0])
      .toBeLessThan(mockRemoveProjectIndex.mock.invocationCallOrder[0]);
  });

  it("cancels in-progress indexing and waits for drain", async () => {
    // Simulate indexing that drains after cancellation
    let callCount = 0;
    mockIsIndexingInProgress.mockImplementation(() => {
      callCount++;
      // Return true for the initial check and first few polls, then false
      return callCount <= 3;
    });

    const result = await handleIndexTool("codebase_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockRequestCancellation).toHaveBeenCalledOnce();
    expect(mockRemoveProjectIndex).toHaveBeenCalledOnce();
  });

  it("refuses remove if same-process indexing does not drain within timeout", async () => {
    vi.useFakeTimers();
    // Simulate indexing that never stops — handler must refuse to delete to prevent corruption
    mockIsIndexingInProgress.mockReturnValue(true);

    // Start the handler — it will block on the 5-minute drain loop
    const resultPromise = handleIndexTool("codebase_remove", { projectPath: TEST_PATH });

    // Advance past the 5-minute same-process drain timeout
    await vi.advanceTimersByTimeAsync(5 * 60_000 + 1_000);

    const result = await resultPromise;

    expect(result).toContain("Cannot remove");
    expect(result).toContain("indexing is still running");
    // Index must NOT be deleted — it's still being written to
    expect(mockRemoveProjectIndex).not.toHaveBeenCalled();
    expect(mockRequestCancellation).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });

  it("waits for in-flight graph build before removing", async () => {
    mockIsGraphBuildInProgress.mockReturnValueOnce(true);

    const result = await handleIndexTool("codebase_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockAwaitGraphBuild).toHaveBeenCalledOnce();
    // Graph build awaited before index removed
    expect(mockAwaitGraphBuild.mock.invocationCallOrder[0])
      .toBeLessThan(mockRemoveProjectIndex.mock.invocationCallOrder[0]);
  });

  it("SIGTERMs a cross-process watcher and waits for lock release before removing", async () => {
    // Another process is holding the watch lock; releases it after SIGTERM
    mockIsProjectLocked
      .mockResolvedValueOnce(true)   // initial check: watch lock is held
      .mockResolvedValue(false);     // after SIGTERM: lock released on next poll
    mockTerminateLockHolder.mockResolvedValueOnce({ terminated: true, pid: 9999 });

    const result = await handleIndexTool("codebase_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockTerminateLockHolder).toHaveBeenCalledWith(expect.any(String), "watch");
    expect(mockRemoveProjectIndex).toHaveBeenCalledOnce();
  });

  it("SIGTERMs a cross-process indexing operation and waits for lock release before removing", async () => {
    // Another process is holding the index lock; releases it after SIGTERM
    mockIsProjectLocked
      .mockResolvedValueOnce(false)  // watch lock check: not held
      .mockResolvedValueOnce(true)   // index lock check: held
      .mockResolvedValue(false);     // after SIGTERM: lock released on next poll
    mockTerminateLockHolder.mockResolvedValueOnce({ terminated: true, pid: 8888 });

    const result = await handleIndexTool("codebase_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockTerminateLockHolder).toHaveBeenCalledWith(expect.any(String), "index");
    expect(mockRemoveProjectIndex).toHaveBeenCalledOnce();
  });

  it("handles all three: watcher + indexing + graph build", async () => {
    mockIsWatching.mockReturnValueOnce(true);
    let indexingCallCount = 0;
    mockIsIndexingInProgress.mockImplementation(() => {
      indexingCallCount++;
      return indexingCallCount <= 2;
    });
    mockIsGraphBuildInProgress.mockReturnValueOnce(true);

    const result = await handleIndexTool("codebase_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockStopWatching).toHaveBeenCalledOnce();
    expect(mockRequestCancellation).toHaveBeenCalledOnce();
    expect(mockAwaitGraphBuild).toHaveBeenCalledOnce();
    expect(mockRemoveProjectIndex).toHaveBeenCalledOnce();
  });
});

describe("codebase_graph_remove — waits for in-flight graph build", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("removes graph immediately when no build is in-flight", async () => {
    const result = await handleGraphTool("codebase_graph_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockRemoveGraph).toHaveBeenCalledOnce();
    expect(mockAwaitGraphBuild).not.toHaveBeenCalled();
  });

  it("awaits in-flight graph build before removing", async () => {
    mockIsGraphBuildInProgress.mockReturnValueOnce(true);

    const result = await handleGraphTool("codebase_graph_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockAwaitGraphBuild).toHaveBeenCalledOnce();
    expect(mockRemoveGraph).toHaveBeenCalledOnce();
    // Await happened before remove
    expect(mockAwaitGraphBuild.mock.invocationCallOrder[0])
      .toBeLessThan(mockRemoveGraph.mock.invocationCallOrder[0]);
  });

  it("still removes graph even if the awaited build had failed", async () => {
    mockIsGraphBuildInProgress.mockReturnValueOnce(true);
    // awaitGraphBuild swallows errors internally — mock it as resolving normally
    // (the real implementation catches and swallows any rejection)
    mockAwaitGraphBuild.mockResolvedValueOnce(undefined);

    const result = await handleGraphTool("codebase_graph_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockAwaitGraphBuild).toHaveBeenCalledOnce();
    expect(mockRemoveGraph).toHaveBeenCalledOnce();
  });
});

describe("codebase_context_remove — guards against concurrent indexing", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("removes artifacts when nothing is in-flight", async () => {
    const result = await handleContextTool("codebase_context_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Removed");
    expect(mockRemoveAllArtifacts).toHaveBeenCalledOnce();
  });

  it("refuses removal when indexing is in progress", async () => {
    mockIsIndexingInProgress.mockReturnValueOnce(true);

    const result = await handleContextTool("codebase_context_remove", { projectPath: TEST_PATH });

    expect(result).toContain("Cannot remove");
    expect(result).toContain("indexing is in progress");
    expect(mockRemoveAllArtifacts).not.toHaveBeenCalled();
  });

  it("suggests using codebase_stop when blocked", async () => {
    mockIsIndexingInProgress.mockReturnValueOnce(true);

    const result = await handleContextTool("codebase_context_remove", { projectPath: TEST_PATH });

    expect(result).toContain("codebase_stop");
  });
});
