// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
/**
 * Shared test setup and cleanup utilities.
 *
 * Provides collection cleanup for integration tests,
 * and infrastructure readiness cache resets.
 */

import { QdrantClient } from "@qdrant/js-client-rest";
import { QDRANT_HOST, QDRANT_PORT } from "../../src/constants.js";

/**
 * Create a Qdrant client for test cleanup operations.
 */
export function createTestQdrantClient(): QdrantClient {
  return new QdrantClient({ host: QDRANT_HOST, port: QDRANT_PORT });
}

/**
 * Delete collections belonging to a specific test project.
 * Only removes collections derived from the given project path,
 * leaving all other projects' collections intact.
 *
 * IMPORTANT: Never use a blanket "delete all codebase_*" approach —
 * that would destroy collections from running SocratiCode instances.
 */
export async function cleanupTestCollections(projectPath: string, client?: QdrantClient): Promise<void> {
  const c = client ?? createTestQdrantClient();
  try {
    const { projectIdFromPath, collectionName, graphCollectionName, contextCollectionName } =
      await import("../../src/config.js");
    const projectId = projectIdFromPath(projectPath);
    const collectionsToDelete = [
      collectionName(projectId),           // codebase_{id}
      graphCollectionName(projectId),      // codegraph_{id}
      contextCollectionName(projectId),    // context_{id}
    ];

    for (const name of collectionsToDelete) {
      try {
        await c.deleteCollection(name);
      } catch {
        // Collection may not exist — ignore
      }
    }

    // Also clean up this project's metadata point (but don't delete the metadata collection itself)
    const { deleteProjectMetadata, deleteContextMetadata } = await import("../../src/services/qdrant.js");
    for (const name of collectionsToDelete) {
      try {
        await deleteProjectMetadata(name);
      } catch {
        // ignore
      }
      try {
        await deleteContextMetadata(name);
      } catch {
        // ignore
      }
    }

    // Reset in-memory caches so ensureMetadataCollection() re-creates if needed
    const { resetMetadataCollectionCache } = await import("../../src/services/qdrant.js");
    resetMetadataCollectionCache();
  } catch {
    // Qdrant may not be running — silently ignore during cleanup
  }
}

/**
 * Delete a specific collection (safe — ignores if not found).
 */
export async function deleteTestCollection(
  collectionName: string,
  client?: QdrantClient,
): Promise<void> {
  const c = client ?? createTestQdrantClient();
  try {
    await c.deleteCollection(collectionName);
  } catch {
    // Ignore
  }
}

/**
 * Reset cached readiness flags so infrastructure checks run fresh.
 * Call this between test suites that test Docker/Ollama startup.
 */
export async function resetReadinessCache(): Promise<void> {
  // Dynamic imports to avoid module initialization side effects in unit tests
  const { resetQdrantReadinessCache } = await import("../../src/services/docker.js");
  const { resetOllamaReadinessCache } = await import("../../src/services/ollama.js");
  resetQdrantReadinessCache();
  resetOllamaReadinessCache();
}

/**
 * Wait for Qdrant to be reachable (used at the top of integration test suites).
 */
export async function waitForQdrant(timeoutMs = 30_000): Promise<boolean> {
  const client = createTestQdrantClient();
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      await client.getCollections();
      return true;
    } catch {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  return false;
}

/**
 * Wait for Ollama to be reachable on its configured port.
 */
export async function waitForOllama(timeoutMs = 30_000): Promise<boolean> {
  const { OLLAMA_HOST: host } = await import("../../src/constants.js");
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${host}/api/tags`);
      if (res.ok) return true;
    } catch {
      // not ready yet
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}
