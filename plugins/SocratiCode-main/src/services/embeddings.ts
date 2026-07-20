// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import { getEmbeddingConfig } from "./embedding-config.js";
import { getEmbeddingProvider } from "./embedding-provider.js";
import { logger } from "./logger.js";

// Number of texts to embed per provider request.
// Configurable via env var EMBEDDING_BATCH_SIZE (positive integer); defaults to 32.
const BATCH_SIZE: number = (() => {
  const raw = process.env.EMBEDDING_BATCH_SIZE;
  if (raw === undefined) return 32;
  const num = Number(raw);
  if (!Number.isInteger(num) || num <= 0) {
    throw new Error(
      `Invalid EMBEDDING_BATCH_SIZE: "${raw}". Must be a positive integer.`,
    );
  }
  return num;
})();
const MAX_RETRIES = 3;
const BASE_DELAY_MS = 500;

/**
 * Inter-batch delay (ms) to respect provider rate limits.
 * Google free tier: 5 RPM → need ~12s between requests.
 * We use a conservative 15s. OpenAI/Ollama have generous limits, so 0.
 */
const PROVIDER_BATCH_DELAY: Record<string, number> = {
  ollama: 0,
  openai: 0,
  google: 15_000, // 15s — stay safely under the free-tier 5 RPM
};

/** Retry an async operation with exponential backoff */
async function withRetry<T>(
  operation: () => Promise<T>,
  label: string,
  maxRetries = MAX_RETRIES,
  baseDelay = BASE_DELAY_MS,
): Promise<T> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (err) {
      lastError = err;
      if (attempt < maxRetries) {
        // Use longer backoff for rate-limit errors (429 / RESOURCE_EXHAUSTED)
        const errMsg = err instanceof Error ? err.message : String(err);
        const isRateLimit = errMsg.includes("429") || errMsg.includes("RESOURCE_EXHAUSTED") || errMsg.includes("quota");
        const delay = isRateLimit
          ? Math.max(baseDelay * 2 ** (attempt - 1), 15_000) // at least 15s for rate limits
          : baseDelay * 2 ** (attempt - 1);
        logger.warn(`${label} failed (attempt ${attempt}/${maxRetries}), retrying in ${delay}ms`, {
          error: errMsg,
        });
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }
  throw lastError;
}

/**
 * Generate embeddings for a batch of texts, handling batching automatically.
 * Texts are pre-truncated to the model's context window inside the provider.
 */
export async function generateEmbeddings(
  texts: string[],
  onBatchComplete?: (processed: number, total: number) => void,
): Promise<number[][]> {
  if (texts.length === 0) return [];

  const provider = await getEmbeddingProvider();
  const config = getEmbeddingConfig();
  const batchDelay = PROVIDER_BATCH_DELAY[config.embeddingProvider] ?? 0;
  const results: number[][] = [];

  for (let i = 0; i < texts.length; i += BATCH_SIZE) {
    // Inter-batch delay to respect provider rate limits (skip first batch)
    if (batchDelay > 0 && i > 0) {
      logger.info(`Rate-limit pause: waiting ${batchDelay / 1000}s before next batch`);
      await new Promise((r) => setTimeout(r, batchDelay));
    }

    const batch = texts.slice(i, i + BATCH_SIZE);
    const batchLabel = `Embedding batch ${Math.floor(i / BATCH_SIZE) + 1}`;
    const embeddings = await withRetry(
      () => provider.embed(batch),
      batchLabel,
    );
    results.push(...embeddings);
    onBatchComplete?.(Math.min(i + batch.length, texts.length), texts.length);
  }

  return results;
}

/**
 * Generate a single query embedding.
 */
export async function generateQueryEmbedding(query: string): Promise<number[]> {
  const provider = await getEmbeddingProvider();
  return withRetry(
    () => provider.embedSingle(`search_query: ${query}`),
    "Query embedding",
  );
}

/**
 * Prepare text for embedding by adding a document prefix.
 * nomic-embed-text uses task prefixes for better retrieval.
 */
export function prepareDocumentText(content: string, filePath: string): string {
  return `search_document: ${filePath}\n${content}`;
}
