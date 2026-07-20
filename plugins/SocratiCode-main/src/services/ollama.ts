// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
/**
 * Ollama service — re-exports from provider-ollama.ts for backward compatibility.
 *
 * The actual embedding logic now lives in provider-ollama.ts (implementing
 * the EmbeddingProvider interface). This module re-exports the functions
 * that other parts of the codebase (tools, tests) depend on.
 */

export {
  isModelAvailable,
  isOllamaAvailable,
  OllamaEmbeddingProvider,
  pullModel,
  resetOllamaReadinessCache,
} from "./provider-ollama.js";

import { OllamaEmbeddingProvider } from "./provider-ollama.js";

// ── Legacy API (used by tools layer) ─────────────────────────────────────

const _ollamaProvider = new OllamaEmbeddingProvider();

/** Ensure Ollama is ready — either Docker container or external instance */
export async function ensureOllamaReady(): Promise<{ modelPulled: boolean; containerStarted: boolean; imagePulled: boolean }> {
  return _ollamaProvider.ensureReady();
}

/** Generate embeddings for one or more texts (legacy — prefer provider interface) */
export async function embed(texts: string[]): Promise<number[][]> {
  return _ollamaProvider.embed(texts);
}

/** Generate a single embedding (legacy — prefer provider interface) */
export async function embedSingle(text: string): Promise<number[]> {
  return _ollamaProvider.embedSingle(text);
}
