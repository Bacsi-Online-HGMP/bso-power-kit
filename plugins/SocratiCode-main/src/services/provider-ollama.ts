// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
/**
 * Ollama embedding provider.
 *
 * Wraps the existing Ollama client logic (Docker or external)
 * into the EmbeddingProvider interface.
 */

import { Ollama } from "ollama";
import type { InfraProgressCallback } from "./docker.js";
import { ensureOllamaContainerReady, isDockerAvailable, isOllamaImagePresent, isOllamaRunning, isQdrantRunning } from "./docker.js";
import { getEmbeddingConfig, setResolvedOllamaMode } from "./embedding-config.js";
import type { EmbeddingHealthStatus, EmbeddingProvider, EmbeddingReadinessResult } from "./embedding-types.js";
import { logger } from "./logger.js";

// ── Client management ────────────────────────────────────────────────────

let ollamaClient: Ollama | null = null;
let ollamaClientHost: string | null = null;

function getClient(): Ollama {
  const config = getEmbeddingConfig();
  if (!ollamaClient || ollamaClientHost !== config.ollamaUrl) {
    ollamaClient = new Ollama({ host: config.ollamaUrl });
    ollamaClientHost = config.ollamaUrl;
  }
  return ollamaClient;
}

// ── Availability checks ─────────────────────────────────────────────────

/** Check if Ollama is reachable */
export async function isOllamaAvailable(): Promise<boolean> {
  try {
    const client = getClient();
    await client.list();
    return true;
  } catch {
    return false;
  }
}

/** Check if the embedding model is already pulled */
export async function isModelAvailable(): Promise<boolean> {
  try {
    const config = getEmbeddingConfig();
    const client = getClient();
    const models = await client.list();
    return models.models.some(
      (m) => m.name === config.embeddingModel || m.name.startsWith(`${config.embeddingModel}:`),
    );
  } catch {
    return false;
  }
}

/** Pull the embedding model */
export async function pullModel(): Promise<void> {
  const config = getEmbeddingConfig();
  logger.info("Pulling embedding model", { model: config.embeddingModel });
  const client = getClient();
  await client.pull({ model: config.embeddingModel });
}

// ── Pre-truncation ──────────────────────────────────────────────────────

/**
 * Conservative chars-per-token ratio for code.
 * Dense minified code ({, }, ;, :, =, . etc.) has close to 1 char per token.
 * Using 1.0 is the safe lower bound and ensures pretruncateTexts always fires
 * before reaching the model's context limit, complementing the MAX_CHUNK_CHARS
 * cap applied during chunking.
 */
const CHARS_PER_TOKEN_ESTIMATE = 1.0;

/** Timeout for pulling the embedding model (15 minutes) */
const MODEL_PULL_TIMEOUT_MS = 15 * 60 * 1000;

/**
 * Pre-truncate texts to stay within the model's context window.
 * Works around an Ollama bug where server-side truncation fails for
 * certain texts and hangs entirely for batched requests.
 * See: https://github.com/ollama/ollama/issues/12710
 */
function pretruncateTexts(texts: string[], contextLength: number): string[] {
  if (contextLength <= 0) return texts;
  const maxChars = Math.floor(contextLength * CHARS_PER_TOKEN_ESTIMATE);
  return texts.map((t) => (t.length > maxChars ? t.substring(0, maxChars) : t));
}

// ── Readiness cache ──────────────────────────────────────────────────────

const READINESS_TTL_MS = 60_000;
let ollamaReadyAt = 0;

/** Reset the cached readiness state */
export function resetOllamaReadinessCache(): void {
  ollamaReadyAt = 0;
}

// ── Auto-detection (OLLAMA_MODE=auto) ────────────────────────────────────

/** Whether the auto-detection probe has run yet */
let _autoDetected = false;

/**
 * Probe localhost:11434 to see if a native Ollama is already running.
 * Result is cached after the first check. Uses a 2s timeout to avoid
 * blocking startup on machines with no native Ollama.
 * Calls setResolvedOllamaMode() to update the config singleton in place.
 */
async function detectNativeOllama(): Promise<boolean> {
  if (_autoDetected) {
    // Already resolved — config was updated in place on first run
    const config = getEmbeddingConfig();
    return config.ollamaMode === "external";
  }
  _autoDetected = true;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2_000);
    const resp = await fetch("http://localhost:11434/api/tags", { signal: controller.signal });
    clearTimeout(timeoutId);
    if (resp.ok) {
      logger.info("Auto-mode: native Ollama detected at http://localhost:11434 — using external mode (GPU-accelerated if available)");
      setResolvedOllamaMode("external", "http://localhost:11434");
      return true;
    }
  } catch {
    // not reachable
  }
  logger.info("Auto-mode: no native Ollama found — using managed Docker container");
  setResolvedOllamaMode("docker", "http://localhost:11435");
  return false;
}

/** Reset the auto-detection cache (for testing). */
export function resetAutoDetectionCache(): void {
  _autoDetected = false;
}

// ── Provider class ──────────────────────────────────────────────────────

export class OllamaEmbeddingProvider implements EmbeddingProvider {
  readonly name = "ollama";
  private onProgress?: InfraProgressCallback;

  constructor(onProgress?: InfraProgressCallback) {
    this.onProgress = onProgress;
  }

  async ensureReady(): Promise<EmbeddingReadinessResult> {
    // Fast path: recently verified as ready
    if (Date.now() - ollamaReadyAt < READINESS_TTL_MS) {
      return { modelPulled: false, containerStarted: false, imagePulled: false };
    }

    // Resolve auto-mode before anything else (probes localhost:11434, updates config in place)
    const config = getEmbeddingConfig();
    if (config.ollamaMode === "auto") {
      await detectNativeOllama();
    }
    let modelPulled = false;
    let containerStarted = false;
    let imagePulled = false;

    if (config.ollamaMode === "docker") {
      const containerResult = await ensureOllamaContainerReady(this.onProgress);
      containerStarted = containerResult.started;
      imagePulled = containerResult.pulled;
    }

    if (!(await isOllamaAvailable())) {
      if (config.ollamaMode === "external") {
        throw new Error(
          `Ollama is not reachable at ${config.ollamaUrl}. ` +
          `Make sure Ollama is running (e.g. "ollama serve") or check OLLAMA_URL in your MCP config.`,
        );
      } else {
        throw new Error(
          "Ollama container is running but not responding. Check Docker logs: docker logs socraticode-ollama",
        );
      }
    }

    if (!(await isModelAvailable())) {
      this.onProgress?.(`Downloading embedding model '${config.embeddingModel}' (first time only, may take a few minutes)...`);
      await this.pullModelWithTimeout(config.embeddingModel);
      modelPulled = true;
    }

    ollamaReadyAt = Date.now();
    return { modelPulled, containerStarted, imagePulled };
  }

  /** Pull the embedding model with a timeout to prevent infinite hangs */
  private async pullModelWithTimeout(model: string): Promise<void> {
    logger.info("Pulling embedding model", { model });
    const client = getClient();

    const pullPromise = client.pull({ model });
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(
        () => reject(new Error(
          `Embedding model download timed out after ${MODEL_PULL_TIMEOUT_MS / 60_000} minutes. ` +
          `The model '${model}' may be too large or the network is slow. Try again.`,
        )),
        MODEL_PULL_TIMEOUT_MS,
      );
    });

    try {
      await Promise.race([pullPromise, timeoutPromise]);
      logger.info("Embedding model pulled successfully", { model });
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      if (msg.includes("timed out")) throw error;
      throw new Error(
        `Failed to download embedding model '${model}'. ` +
        `Check that the model name is correct and Ollama is responsive.\nDetails: ${msg}`,
      );
    }
  }

  async embed(texts: string[]): Promise<number[][]> {
    const config = getEmbeddingConfig();
    const client = getClient();
    // Fall back to a conservative 2048-token window for models not in the
    // known-models table (guessContextLength returns 0 for unknown models,
    // which would disable pretruncateTexts and risk "input length exceeds
    // context length" errors from Ollama).
    const contextLength = config.embeddingContextLength > 0 ? config.embeddingContextLength : 2048;
    const truncated = pretruncateTexts(texts, contextLength);
    const response = await client.embed({ model: config.embeddingModel, input: truncated, truncate: true });
    return response.embeddings;
  }

  async embedSingle(text: string): Promise<number[]> {
    const results = await this.embed([text]);
    return results[0];
  }

  async healthCheck(): Promise<EmbeddingHealthStatus> {
    // Resolve auto-mode first if not yet done
    const rawConfig = getEmbeddingConfig();
    if (rawConfig.ollamaMode === "auto") {
      await detectNativeOllama();
    }
    const config = getEmbeddingConfig();
    const lines: string[] = [];
    const icon = (ok: boolean) => (ok ? "[OK]" : "[MISSING]");

    if (config.ollamaMode === "docker") {
      const docker = await isDockerAvailable();
      lines.push(`${icon(docker)} Docker: ${docker ? "Running" : "Not found — install from https://docker.com"}`);

      if (docker) {
        const [_qdrantRunning, ollamaRunning, ollamaImage] = await Promise.all([
          isQdrantRunning(),
          isOllamaRunning(),
          isOllamaImagePresent(),
        ]);
        lines.push(`${icon(ollamaImage)} Ollama image: ${ollamaImage ? "Pulled" : "Not pulled — will be pulled on first index"}`);
        lines.push(`${icon(ollamaRunning)} Ollama container: ${ollamaRunning ? "Running" : "Not running — will be started on first index"}`);

        const ollamaReachable = ollamaRunning ? await isOllamaAvailable() : false;
        const modelReady = ollamaReachable ? await isModelAvailable() : false;
        lines.push(`${icon(modelReady)} Embedding model (${config.embeddingModel}): ${modelReady ? "Available" : "Not pulled — will be pulled on first index"}`);

        return { available: ollamaReachable, modelReady, statusLines: lines };
      }

      return { available: false, modelReady: false, statusLines: lines };
    }

    // External mode
    const available = await isOllamaAvailable();
    lines.push(`${icon(available)} Ollama (external): ${available ? `Reachable at ${config.ollamaUrl}` : `Not reachable at ${config.ollamaUrl}`}`);

    const modelReady = available ? await isModelAvailable() : false;
    lines.push(`${icon(modelReady)} Embedding model (${config.embeddingModel}): ${modelReady ? "Available" : "Not available — will be pulled on first index"}`);

    return { available, modelReady, statusLines: lines };
  }
}
