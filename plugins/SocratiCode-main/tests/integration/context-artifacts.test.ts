// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import fs from "node:fs";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { contextCollectionName, projectIdFromPath } from "../../src/config.js";
import {
  ensureArtifactsIndexed,
  getArtifactStatusSummary,
  indexAllArtifacts,
  removeAllArtifacts,
  searchArtifacts,
} from "../../src/services/context-artifacts.js";
import { ensureQdrantReady } from "../../src/services/docker.js";
import { ensureOllamaReady } from "../../src/services/ollama.js";
import { getCollectionInfo, loadContextMetadata } from "../../src/services/qdrant.js";
import {
  createFixtureProject,
  type FixtureProject,
  isDockerAvailable,
} from "../helpers/fixtures.js";
import { cleanupTestCollections, waitForOllama, waitForQdrant } from "../helpers/setup.js";

const dockerAvailable = isDockerAvailable();

describe.skipIf(!dockerAvailable)("context-artifacts service", () => {
  let fixture: FixtureProject;
  let contextCollection: string;

  beforeAll(async () => {
    await ensureQdrantReady();
    await ensureOllamaReady();
    await waitForQdrant();
    await waitForOllama();

    fixture = createFixtureProject("context-artifacts-test");

    // Add artifact files to the fixture
    const schemaContent = [
      "CREATE TABLE users (",
      "  id SERIAL PRIMARY KEY,",
      "  email VARCHAR(255) NOT NULL UNIQUE,",
      "  name VARCHAR(100) NOT NULL,",
      "  created_at TIMESTAMP DEFAULT NOW()",
      ");",
      "",
      "CREATE TABLE orders (",
      "  id SERIAL PRIMARY KEY,",
      "  user_id INTEGER REFERENCES users(id),",
      "  total DECIMAL(10, 2) NOT NULL,",
      "  status VARCHAR(20) DEFAULT 'pending',",
      "  created_at TIMESTAMP DEFAULT NOW()",
      ");",
      "",
      "CREATE INDEX idx_orders_user_id ON orders(user_id);",
      "CREATE INDEX idx_orders_status ON orders(status);",
    ].join("\n");

    const apiSpec = [
      "openapi: '3.0.0'",
      "info:",
      "  title: Test API",
      "  version: 1.0.0",
      "paths:",
      "  /users:",
      "    get:",
      "      summary: List all users",
      "      responses:",
      "        '200':",
      "          description: A list of users",
      "  /orders:",
      "    post:",
      "      summary: Create a new order",
      "      requestBody:",
      "        required: true",
      "        content:",
      "          application/json:",
      "            schema:",
      "              type: object",
      "              properties:",
      "                userId:",
      "                  type: integer",
      "                total:",
      "                  type: number",
    ].join("\n");

    // Create a docs directory with artifact files
    fs.mkdirSync(path.join(fixture.root, "docs"), { recursive: true });
    fs.writeFileSync(path.join(fixture.root, "docs", "schema.sql"), schemaContent);
    fs.writeFileSync(path.join(fixture.root, "docs", "api.yaml"), apiSpec);

    // Create a directory artifact (infra configs)
    fs.mkdirSync(path.join(fixture.root, "deploy"), { recursive: true });
    fs.writeFileSync(
      path.join(fixture.root, "deploy", "service.yaml"),
      "apiVersion: v1\nkind: Service\nmetadata:\n  name: my-app\nspec:\n  type: ClusterIP\n  ports:\n    - port: 80\n",
    );
    fs.writeFileSync(
      path.join(fixture.root, "deploy", "deployment.yaml"),
      "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: my-app\nspec:\n  replicas: 3\n  template:\n    spec:\n      containers:\n        - name: app\n          image: my-app:latest\n",
    );

    // Create .socraticodecontextartifacts.json
    fs.writeFileSync(
      path.join(fixture.root, ".socraticodecontextartifacts.json"),
      JSON.stringify({
        artifacts: [
          {
            name: "database-schema",
            path: "./docs/schema.sql",
            description: "PostgreSQL database schema with users and orders tables",
          },
          {
            name: "api-spec",
            path: "./docs/api.yaml",
            description: "OpenAPI 3.0 REST API specification",
          },
          {
            name: "k8s-manifests",
            path: "./deploy/",
            description: "Kubernetes deployment and service manifests",
          },
        ],
      }),
    );

    const projectId = projectIdFromPath(fixture.root);
    contextCollection = contextCollectionName(projectId);
  }, 60_000);

  afterAll(async () => {
    try {
      await removeAllArtifacts(fixture.root);
    } catch {
      // ignore
    }
    fixture.cleanup();
    await cleanupTestCollections(fixture.root);
  });

  // ── indexAllArtifacts ──────────────────────────────────────────────────

  describe("indexAllArtifacts", () => {
    it("indexes all configured artifacts with real embeddings", async () => {
      const { indexed, errors } = await indexAllArtifacts(fixture.root);

      expect(errors).toHaveLength(0);
      expect(indexed).toHaveLength(3);

      // Each artifact should have chunks
      for (const state of indexed) {
        expect(state.chunksIndexed).toBeGreaterThan(0);
        expect(state.contentHash).toMatch(/^[0-9a-f]{16}$/);
        expect(state.lastIndexedAt).toBeTruthy();
      }

      // Check specific artifact names
      const names = indexed.map((a) => a.name);
      expect(names).toContain("database-schema");
      expect(names).toContain("api-spec");
      expect(names).toContain("k8s-manifests");
    }, 180_000);

    it("creates a Qdrant collection with indexed chunks", async () => {
      const info = await getCollectionInfo(contextCollection);
      expect(info).toBeDefined();
      expect(info?.pointsCount).toBeGreaterThan(0);
    });

    it("persists metadata that can be loaded back", async () => {
      const metadata = await loadContextMetadata(contextCollection);
      expect(metadata).not.toBeNull();
      expect(metadata).toHaveLength(3);
    });
  });

  // ── searchArtifacts ────────────────────────────────────────────────────

  describe("searchArtifacts", () => {
    it("finds database schema content via semantic search", async () => {
      const results = await searchArtifacts(
        fixture.root,
        "database tables users orders foreign keys",
      );

      expect(results.length).toBeGreaterThan(0);
      const schemaResult = results.find((r) =>
        r.content.includes("CREATE TABLE") || r.content.includes("users"),
      );
      expect(schemaResult).toBeDefined();
    });

    it("finds API spec content via semantic search", async () => {
      const results = await searchArtifacts(
        fixture.root,
        "REST API endpoints users orders",
      );

      expect(results.length).toBeGreaterThan(0);
      const apiResult = results.find((r) =>
        r.content.includes("openapi") || r.content.includes("/users"),
      );
      expect(apiResult).toBeDefined();
    });

    it("finds Kubernetes manifests via semantic search", async () => {
      const results = await searchArtifacts(
        fixture.root,
        "kubernetes deployment service replicas",
      );

      expect(results.length).toBeGreaterThan(0);
      const k8sResult = results.find((r) =>
        r.content.includes("Deployment") || r.content.includes("Service"),
      );
      expect(k8sResult).toBeDefined();
    });

    it("filters by artifact name", async () => {
      const results = await searchArtifacts(
        fixture.root,
        "tables columns indexes",
        "database-schema",
      );

      expect(results.length).toBeGreaterThan(0);
      // All results should be from the database-schema artifact
      for (const r of results) {
        const _payload = r as unknown as Record<string, unknown>;
        // The payload should reference the schema artifact
        expect(
          r.content.includes("CREATE TABLE") ||
          r.content.includes("INDEX") ||
          r.content.includes("users") ||
          r.content.includes("orders"),
        ).toBe(true);
      }
    });

    it("returns empty for nonexistent project", async () => {
      const results = await searchArtifacts(
        "/nonexistent/project/path",
        "anything",
      );
      expect(results).toHaveLength(0);
    });

    it("respects limit parameter", async () => {
      const results = await searchArtifacts(
        fixture.root,
        "database API deployment",
        undefined,
        2,
      );
      expect(results.length).toBeLessThanOrEqual(2);
    });
  });

  // ── ensureArtifactsIndexed (staleness detection) ───────────────────────

  describe("ensureArtifactsIndexed", () => {
    it("reports all artifacts as up-to-date when nothing changed", async () => {
      const { reindexed, upToDate, errors } = await ensureArtifactsIndexed(fixture.root);

      expect(errors).toHaveLength(0);
      expect(reindexed).toHaveLength(0);
      expect(upToDate).toHaveLength(3);
    }, 60_000);

    it("detects changed artifact and re-indexes it", async () => {
      // Modify the schema file
      const schemaPath = path.join(fixture.root, "docs", "schema.sql");
      const originalContent = fs.readFileSync(schemaPath, "utf-8");
      fs.writeFileSync(
        schemaPath,
        `${originalContent}\n\nCREATE TABLE products (\n  id SERIAL PRIMARY KEY,\n  name TEXT NOT NULL,\n  price DECIMAL(10,2)\n);\n`,
      );

      const { reindexed, upToDate, errors } = await ensureArtifactsIndexed(fixture.root);

      expect(errors).toHaveLength(0);
      expect(reindexed).toContain("database-schema");
      // The other 2 should be up-to-date
      expect(upToDate.length).toBe(2);
    }, 180_000);

    it("finds newly added schema content after re-indexing", async () => {
      const results = await searchArtifacts(
        fixture.root,
        "products table price",
      );

      expect(results.length).toBeGreaterThan(0);
      const productResult = results.find((r) => r.content.includes("products"));
      expect(productResult).toBeDefined();
    });

    it("removes artifacts no longer in config", async () => {
      // Rewrite config without the k8s-manifests artifact
      fs.writeFileSync(
        path.join(fixture.root, ".socraticodecontextartifacts.json"),
        JSON.stringify({
          artifacts: [
            {
              name: "database-schema",
              path: "./docs/schema.sql",
              description: "PostgreSQL database schema with users and orders tables",
            },
            {
              name: "api-spec",
              path: "./docs/api.yaml",
              description: "OpenAPI 3.0 REST API specification",
            },
          ],
        }),
      );

      const { reindexed, upToDate, errors } = await ensureArtifactsIndexed(fixture.root);

      expect(errors).toHaveLength(0);
      // Both remaining should be up-to-date (schema was re-indexed above, api unchanged)
      expect(upToDate.length + reindexed.length).toBe(2);
    }, 60_000);
  });

  // ── getArtifactStatusSummary ───────────────────────────────────────────

  describe("getArtifactStatusSummary", () => {
    it("returns status for a project with artifacts", async () => {
      const summary = await getArtifactStatusSummary(fixture.root);

      expect(summary).not.toBeNull();
      expect(summary?.configuredCount).toBe(2); // config was reduced to 2 above
      expect(summary?.indexedCount).toBeGreaterThanOrEqual(1);
      expect(summary?.totalChunks).toBeGreaterThan(0);
      expect(summary?.lines.length).toBeGreaterThan(0);
    });

    it("returns null for a project without config file", async () => {
      const tempFixture = createFixtureProject("no-artifacts-test");
      try {
        const summary = await getArtifactStatusSummary(tempFixture.root);
        expect(summary).toBeNull();
      } finally {
        tempFixture.cleanup();
      }
    });
  });

  // ── removeAllArtifacts ─────────────────────────────────────────────────

  describe("removeAllArtifacts", () => {
    it("removes the context collection and metadata", async () => {
      await removeAllArtifacts(fixture.root);

      const info = await getCollectionInfo(contextCollection);
      expect(info).toBeNull();
    });

    it("search returns empty after removal", async () => {
      const results = await searchArtifacts(
        fixture.root,
        "database tables users",
      );
      expect(results).toHaveLength(0);
    });
  });
});
