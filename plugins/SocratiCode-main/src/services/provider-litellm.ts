// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
/**
 * LiteLLM embedding provider.
 *
 * LiteLLM Proxy Server (https://docs.litellm.ai/docs/simple_proxy) exposes an
 * OpenAI-compatible /v1/embeddings endpoint that fans out to 100+ underlying
 * model providers (OpenAI, Anthropic, Cohere, Voyage, HuggingFace, Bedrock,
 * Vertex AI, Ollama, ...). Model aliases are defined in the proxy's config.yaml,
 * so from this client's perspective LiteLLM looks like an OpenAI server speaking
 * arbitrary model names.
 *
 * This provider is intentionally separate from `provider-openai.ts` and
 * `provider-lmstudio.ts` because:
 *   - LiteLLM ALWAYS requires an API key (virtual or master), unlike LM Studio.
 *   - Default port is 4000 and /v1/models lists proxy-registered aliases, not
 *     loaded local models.
 *   - Whether the `dimensions` parameter is honoured depends on the underlying
 *     provider chosen by the proxy alias, so we make it opt-in via
 *     LITELLM_SEND_DIMENSIONS instead of hardcoding it like provider-openai
 *     does for text-embedding-3-*.
 *   - Health check messaging points at proxy-side issues (master key, alias
 *     missing in config.yaml) rather than at SaaS quotas or local model loads.
 *
 * Required env when using this provider:
 *   EMBEDDING_PROVIDER=litellm
 *   LITELLM_API_KEY=<virtual-or-master-key>
 *   EMBEDDING_MODEL=<alias-from-litellm-config-yaml>
 *   EMBEDDING_DIMENSIONS=<dim-of-underlying-model>
 *
 * Optional env:
 *   LITELLM_URL=http://localhost:4000/v1   (default; must include /v1 suffix)
 *   LITELLM_SEND_DIMENSIONS=true           (opt-in; forwards `dimensions` to the
 *                                           proxy for Matryoshka-aware models like
 *                                           text-embedding-3-* or voyage-3 routed
 *                                           via LiteLLM. Default false because
 *                                           non-Matryoshka backends raise on it.)
 *   EMBEDDING_CONTEXT_LENGTH=<tokens>      (defaults to 2048 if model unknown)
 */

import OpenAI from "openai";
import { getEmbeddingConfig } from "./embedding-config.js";
import type { EmbeddingHealthStatus, EmbeddingProvider, EmbeddingReadinessResult } from "./embedding-types.js";
import { logger } from "./logger.js";

// ── Constants ───────────────────────────────────────────────────────────

/**
 * Conservative batch size — LiteLLM is a proxy in front of an arbitrary backend,
 * so the practical batch ceiling depends on whichever provider the alias resolves
 * to (an OpenAI alias tolerates 512+, a self-hosted Ollama alias may OOM at 64+).
 * 256 sits between the OpenAI (512) and LM Studio (64) defaults and rarely
 * triggers proxy-level rate limiting on commercial backends.
 */
const LITELLM_BATCH_SIZE = 256;

/**
 * Conservative chars-per-token ratio for code. Same value as provider-openai
 * and provider-lmstudio; LiteLLM does not retokenize on the proxy hop.
 */
const CHARS_PER_TOKEN_ESTIMATE = 3.0;

/**
 * Fallback context length when EMBEDDING_CONTEXT_LENGTH is unset and the model
 * alias is not in the known-models table. 2048 is a safe lower bound across the
 * common embedding backends LiteLLM proxies (Voyage 16k, OpenAI 8191, Cohere 512,
 * BGE 512). Underestimating only triggers extra client-side truncation; never
 * a request-rejection.
 */
const DEFAULT_CONTEXT_LENGTH = 2048;

// ── Client management ───────────────────────────────────────────────────

let litellmClient: OpenAI | null = null;
let litellmBaseUrl: string | null = null;
let litellmApiKey: string | null = null;

function getClient(): OpenAI {
  const config = getEmbeddingConfig();
  const baseUrl = config.litellmUrl;
  // Read the key from the live env so test harnesses that mutate process.env
  // between calls observe the change without an explicit reset.
  const apiKey = process.env.LITELLM_API_KEY;
  if (!apiKey) {
    throw new Error(
      "LITELLM_API_KEY environment variable is required when using the LiteLLM embedding provider. " +
      "Set it in your MCP config env block. Use either the proxy's master key or a virtual key " +
      "issued via LiteLLM's /key/generate endpoint.",
    );
  }
  if (!litellmClient || litellmBaseUrl !== baseUrl || litellmApiKey !== apiKey) {
    litellmClient = new OpenAI({
      apiKey,
      baseURL: baseUrl,
    });
    litellmBaseUrl = baseUrl;
    litellmApiKey = apiKey;
  }
  return litellmClient;
}

/** Reset client (for testing or LITELLM_URL / LITELLM_API_KEY hot-swap). */
export function resetLiteLLMClient(): void {
  litellmClient = null;
  litellmBaseUrl = null;
  litellmApiKey = null;
}

// ── Pre-truncation ──────────────────────────────────────────────────────

function pretruncateTexts(texts: string[], contextLength: number): string[] {
  if (contextLength <= 0) return texts;
  const maxChars = Math.floor(contextLength * CHARS_PER_TOKEN_ESTIMATE);
  return texts.map((t) => (t.length > maxChars ? t.substring(0, maxChars) : t));
}

// ── Auth-error detection ────────────────────────────────────────────────

/**
 * The OpenAI SDK surfaces 401/403 from LiteLLM as APIError subclasses with a
 * `.status` field. We don't import those classes (avoids a hard dep on the SDK's
 * private subclass exports) and instead duck-type on `.status`.
 */
function isAuthError(err: unknown): boolean {
  if (typeof err !== "object" || err === null) return false;
  const status = (err as { status?: unknown }).status;
  return status === 401 || status === 403;
}

// ── Provider class ──────────────────────────────────────────────────────

export class LiteLLMEmbeddingProvider implements EmbeddingProvider {
  readonly name = "litellm";

  async ensureReady(): Promise<EmbeddingReadinessResult> {
    const config = getEmbeddingConfig();
    // Fail fast with our own message before letting the SDK construct the client.
    const client = getClient();

    // Step 1 — connectivity + auth. Three failure modes share a single round trip:
    // proxy unreachable (DNS/connection refused), bad credentials (401/403), or
    // proxy reachable but mis-configured (500/etc.). Distinguish them so the
    // operator gets a directly actionable hint.
    //
    // Iterate the SDK's auto-paginated AsyncIterable rather than reading
    // .data directly. LiteLLM today returns the entire model_list in one
    // page, so this is functionally a no-op; it keeps the membership check
    // correct if a future LiteLLM build (or an upstream proxy) ever paginates
    // /v1/models the way the OpenAI SDK already expects.
    const allModelIds: string[] = [];
    try {
      for await (const m of client.models.list()) {
        allModelIds.push(m.id);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (isAuthError(err)) {
        throw new Error(
          `LiteLLM rejected the request at ${config.litellmUrl} with an authentication error. ` +
          "Check that LITELLM_API_KEY matches a valid master or virtual key on the proxy " +
          "(see LiteLLM's /key/info endpoint or the proxy's general_settings.master_key). " +
          `Underlying error: ${message}`,
        );
      }
      throw new Error(
        `LiteLLM proxy is not reachable at ${config.litellmUrl}. ` +
        "Make sure the proxy is running (e.g. `litellm --config config.yaml`). " +
        "If you've changed the port or are running it remotely, set LITELLM_URL accordingly " +
        "(e.g. http://litellm.internal:4000/v1) — the URL must include the /v1 suffix. " +
        `Underlying error: ${message}`,
      );
    }

    // Step 2 — alias registered. LiteLLM's /v1/models returns the model_list
    // entries declared in config.yaml; if the configured EMBEDDING_MODEL is
    // missing the proxy will return a NotFoundError on every embed() call,
    // which is opaque under high concurrency. Fail early with a hint that
    // points at the proxy config rather than at the underlying provider.
    const modelRegistered = allModelIds.includes(config.embeddingModel);
    if (!modelRegistered) {
      const known = allModelIds.slice(0, 10).join(", ");
      throw new Error(
        `LiteLLM is reachable at ${config.litellmUrl} but the embedding model ` +
        `"${config.embeddingModel}" is not registered on the proxy. ` +
        "Add it to your LiteLLM config.yaml under model_list (with a model_name matching " +
        "EMBEDDING_MODEL) and restart the proxy — then retry. " +
        (known ? `Currently registered models: ${known}.` : "The proxy currently has no registered models."),
      );
    }

    logger.info("LiteLLM embedding provider ready", {
      baseUrl: config.litellmUrl,
      model: config.embeddingModel,
      sendDimensions: shouldSendDimensions(),
    });
    // LiteLLM is user-managed — no containers, no model pulls.
    return { modelPulled: false, containerStarted: false, imagePulled: false };
  }

  async embed(texts: string[]): Promise<number[][]> {
    if (texts.length === 0) return [];

    const config = getEmbeddingConfig();
    const client = getClient();
    const contextLength = config.embeddingContextLength > 0
      ? config.embeddingContextLength
      : DEFAULT_CONTEXT_LENGTH;
    const truncated = pretruncateTexts(texts, contextLength);

    if (truncated.length <= LITELLM_BATCH_SIZE) {
      return this._embedBatch(client, truncated, config.embeddingModel, config.embeddingDimensions);
    }

    const results: number[][] = [];
    for (let i = 0; i < truncated.length; i += LITELLM_BATCH_SIZE) {
      const batch = truncated.slice(i, i + LITELLM_BATCH_SIZE);
      const embeddings = await this._embedBatch(client, batch, config.embeddingModel, config.embeddingDimensions);
      results.push(...embeddings);
    }
    return results;
  }

  async embedSingle(text: string): Promise<number[]> {
    const results = await this.embed([text]);
    if (results.length === 0) {
      throw new Error("Embedding failed: no result returned");
    }
    return results[0];
  }

  async healthCheck(): Promise<EmbeddingHealthStatus> {
    const config = getEmbeddingConfig();
    const lines: string[] = [];
    const icon = (ok: boolean) => (ok ? "[OK]" : "[MISSING]");

    const hasKey = !!process.env.LITELLM_API_KEY;
    lines.push(
      `${icon(hasKey)} LiteLLM API key: ` +
      (hasKey ? "Configured" : "Missing — set LITELLM_API_KEY in your MCP config"),
    );
    if (!hasKey) {
      return { available: false, modelReady: false, statusLines: lines };
    }

    try {
      const client = getClient();
      // Same auto-pagination treatment as ensureReady — see the comment there
      // for why we iterate rather than reading .data directly.
      const allModelIds: string[] = [];
      for await (const m of client.models.list()) {
        allModelIds.push(m.id);
      }
      lines.push(`${icon(true)} LiteLLM: Reachable at ${config.litellmUrl}`);

      const modelRegistered = allModelIds.includes(config.embeddingModel);
      lines.push(
        `${icon(modelRegistered)} Embedding model (${config.embeddingModel}): ` +
        (modelRegistered
          ? "Registered on the proxy"
          : "Not registered — add it to your LiteLLM config.yaml under model_list and restart the proxy"),
      );

      return { available: true, modelReady: modelRegistered, statusLines: lines };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (isAuthError(err)) {
        lines.push(`${icon(false)} LiteLLM: Auth rejected at ${config.litellmUrl} (${message})`);
      } else {
        lines.push(`${icon(false)} LiteLLM: Not reachable at ${config.litellmUrl} (${message})`);
      }
      return { available: false, modelReady: false, statusLines: lines };
    }
  }

  private async _embedBatch(
    client: OpenAI,
    texts: string[],
    model: string,
    dimensions: number,
  ): Promise<number[][]> {
    // Forwarding `dimensions` is opt-in (LITELLM_SEND_DIMENSIONS=true). The proxy
    // forwards it to the underlying provider verbatim — Matryoshka-aware models
    // (text-embedding-3-*, voyage-3) accept it; others (BGE, nomic-embed,
    // Cohere v3) reject the request. Default off keeps the provider compatible
    // with arbitrary aliases.
    //
    // `encoding_format: "float"` is REQUIRED. The OpenAI SDK (6.x+) defaults to
    // `encoding_format: "base64"` and unconditionally decodes the response with
    // toFloat32Array(). LiteLLM forwards the original provider's response, which
    // for many backends (Ollama, BGE-via-tei, custom HF wrappers) is a JSON
    // float array. The SDK's decode path then runs `Buffer.from(<array>, 'base64')`,
    // Node.js silently drops the encoding for array inputs and clamps each float
    // (<1.0) to uint8 0, producing a zero buffer reinterpreted as a Float32Array
    // of zeros. This is the same bug fixed for LM Studio in commit bb141a0; the
    // failure mode reproduces against any LiteLLM alias whose backend doesn't
    // re-encode to base64. Setting `encoding_format: "float"` makes the SDK skip
    // the decode step entirely.
    const response = await client.embeddings.create({
      model,
      input: texts,
      encoding_format: "float",
      ...(shouldSendDimensions() ? { dimensions } : {}),
    });
    const sorted = response.data.sort((a, b) => a.index - b.index);
    return sorted.map((d) => d.embedding);
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────

function shouldSendDimensions(): boolean {
  const raw = process.env.LITELLM_SEND_DIMENSIONS;
  if (!raw) return false;
  const v = raw.toLowerCase();
  return v === "true" || v === "1" || v === "yes";
}
