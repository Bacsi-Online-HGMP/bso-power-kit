// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
import { beforeAll, describe, expect, it } from "vitest";
import { ensureQdrantReady } from "../../src/services/docker.js";
import { getEmbeddingConfig } from "../../src/services/embedding-config.js";
import {
  generateEmbeddings,
  generateQueryEmbedding,
  prepareDocumentText,
} from "../../src/services/embeddings.js";
import { ensureOllamaReady } from "../../src/services/ollama.js";
import { isDockerAvailable } from "../helpers/fixtures.js";
import { waitForOllama } from "../helpers/setup.js";

const dockerAvailable = isDockerAvailable();

describe.skipIf(!dockerAvailable)("embeddings service", () => {
  const config = getEmbeddingConfig();

  beforeAll(async () => {
    await ensureQdrantReady();
    await ensureOllamaReady();
    await waitForOllama();
  });

  describe("prepareDocumentText", () => {
    it("combines file metadata with content", () => {
      const text = prepareDocumentText(
        "export function greet() { return 'hello'; }",
        "src/utils.ts",
      );

      expect(text).toContain("src/utils.ts");
      expect(text).toContain("greet");
    });

    it("handles empty content", () => {
      const text = prepareDocumentText("", "empty.ts");
      expect(text).toContain("empty.ts");
    });
  });

  describe("generateEmbeddings", () => {
    it("generates embeddings for a batch of texts", async () => {
      const texts = [
        "function add(a, b) { return a + b; }",
        "class UserService { constructor() {} }",
        "const PI = 3.14159;",
      ];

      const embeddings = await generateEmbeddings(texts);

      expect(embeddings).toHaveLength(3);
      for (const emb of embeddings) {
        expect(emb).toHaveLength(config.embeddingDimensions);
      }
    });

    it("generates consistent embeddings for the same text", async () => {
      const text = "function add(a, b) { return a + b; }";
      const [emb1] = await generateEmbeddings([text]);
      const [emb2] = await generateEmbeddings([text]);

      // Embeddings should be very close (not perfectly identical due to floating point)
      expect(emb1).toHaveLength(config.embeddingDimensions);
      expect(emb2).toHaveLength(config.embeddingDimensions);

      // Cosine similarity should be very high
      let dot = 0, norm1 = 0, norm2 = 0;
      for (let i = 0; i < emb1.length; i++) {
        dot += emb1[i] * emb2[i];
        norm1 += emb1[i] * emb1[i];
        norm2 += emb2[i] * emb2[i];
      }
      const similarity = dot / (Math.sqrt(norm1) * Math.sqrt(norm2));
      expect(similarity).toBeGreaterThan(0.99);
    });

    it("generates different embeddings for different content", async () => {
      const embeddings = await generateEmbeddings([
        "authentication middleware with JWT token validation",
        "fibonacci sequence mathematical algorithm calculation",
      ]);

      expect(embeddings).toHaveLength(2);

      // Calculate cosine similarity - should be < 1.0
      let dot = 0, norm1 = 0, norm2 = 0;
      for (let i = 0; i < embeddings[0].length; i++) {
        dot += embeddings[0][i] * embeddings[1][i];
        norm1 += embeddings[0][i] * embeddings[0][i];
        norm2 += embeddings[1][i] * embeddings[1][i];
      }
      const similarity = dot / (Math.sqrt(norm1) * Math.sqrt(norm2));

      // Different texts should have substantially different embeddings
      expect(similarity).toBeLessThan(0.95);
    });

    it("handles a single text", async () => {
      const embeddings = await generateEmbeddings(["single text"]);
      expect(embeddings).toHaveLength(1);
      expect(embeddings[0]).toHaveLength(config.embeddingDimensions);
    });

    it("handles empty array", async () => {
      const embeddings = await generateEmbeddings([]);
      expect(embeddings).toHaveLength(0);
    });
  });

  describe("generateQueryEmbedding", () => {
    it("generates a query embedding", async () => {
      const embedding = await generateQueryEmbedding("search for authentication code");

      expect(embedding).toHaveLength(config.embeddingDimensions);
      for (const val of embedding) {
        expect(Number.isFinite(val)).toBe(true);
      }
    });

    it("produces a semantically relevant embedding", async () => {
      // Generate embeddings for documents
      const [authEmb] = await generateEmbeddings([
        "function authenticateUser(token) { return validateJWT(token); }",
      ]);
      const [mathEmb] = await generateEmbeddings([
        "function fibonacci(n) { return n <= 1 ? n : fibonacci(n-1) + fibonacci(n-2); }",
      ]);

      // Generate query embedding
      const queryEmb = await generateQueryEmbedding("user authentication JWT");

      // The query should be more similar to auth code than math code
      function cosineSim(a: number[], b: number[]): number {
        let dot = 0, n1 = 0, n2 = 0;
        for (let i = 0; i < a.length; i++) {
          dot += a[i] * b[i];
          n1 += a[i] * a[i];
          n2 += b[i] * b[i];
        }
        return dot / (Math.sqrt(n1) * Math.sqrt(n2));
      }

      const authSim = cosineSim(queryEmb, authEmb);
      const mathSim = cosineSim(queryEmb, mathEmb);

      expect(authSim).toBeGreaterThan(mathSim);
    });
  });
});
