// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
/**
 * Shared type definitions for embedding providers.
 *
 * Extracted into a separate module to avoid circular dependencies:
 * - embedding-provider.ts (factory) imports provider implementations
 * - provider implementations import these types
 */

// ── Interface ────────────────────────────────────────────────────────────

export interface EmbeddingProvider {
  /** Human-readable provider name (for logs & health checks). */
  readonly name: string;

  /**
   * Ensure the provider is ready to serve embeddings.
   * For Ollama this starts containers / pulls models.
   * For cloud providers this validates the API key.
   *
   * Returns a bag of status flags for the tools layer.
   */
  ensureReady(): Promise<EmbeddingReadinessResult>;

  /** Generate embeddings for one or more texts. */
  embed(texts: string[]): Promise<number[][]>;

  /** Generate a single embedding (convenience). */
  embedSingle(text: string): Promise<number[]>;

  /**
   * Check health / availability.
   * Returns a structured status for the health-check tool.
   */
  healthCheck(): Promise<EmbeddingHealthStatus>;
}

export interface EmbeddingReadinessResult {
  /** True if a model was pulled/downloaded as part of setup. */
  modelPulled: boolean;
  /** True if a Docker container was started (Ollama docker mode only). */
  containerStarted: boolean;
  /** True if a Docker image was pulled (Ollama docker mode only). */
  imagePulled: boolean;
}

export interface EmbeddingHealthStatus {
  /** Provider is reachable and ready. */
  available: boolean;
  /** The model/endpoint is accessible. */
  modelReady: boolean;
  /** Human-readable status lines for the health tool. */
  statusLines: string[];
}
