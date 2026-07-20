// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
import path from "node:path";
import { contextCollectionName, projectIdFromPath } from "../config.js";
import { SEARCH_MIN_SCORE } from "../constants.js";
import {
  ensureArtifactsIndexed,
  indexAllArtifacts,
  loadConfig,
  removeAllArtifacts,
  searchArtifacts,
} from "../services/context-artifacts.js";
import { ensureQdrantReady } from "../services/docker.js";
import { getEmbeddingConfig } from "../services/embedding-config.js";
import { getEmbeddingProvider } from "../services/embedding-provider.js";
import { isIndexingInProgress } from "../services/indexer.js";
import { logger } from "../services/logger.js";
import { ensureOllamaReady } from "../services/ollama.js";
import { getCollectionInfo, loadContextMetadata } from "../services/qdrant.js";

export async function handleContextTool(
  name: string,
  args: Record<string, unknown>,
): Promise<string> {
  const projectPath = (args.projectPath as string) || process.cwd();
  const resolvedPath = path.resolve(projectPath);

  switch (name) {
    case "codebase_context": {
      // List all artifacts: from config + their index status
      const config = await loadConfig(resolvedPath);

      if (!config?.artifacts?.length) {
        return [
          `No context artifacts configured for: ${resolvedPath}`,
          "",
          "To add context artifacts, create a .socraticodecontextartifacts.json file in your project root:",
          "",
          "{",
          '  "artifacts": [',
          "    {",
          '      "name": "database-schema",',
          '      "path": "./docs/schema.sql",',
          '      "description": "PostgreSQL schema — all tables, indexes, constraints, foreign keys."',
          "    }",
          "  ]",
          "}",
          "",
          "Artifacts can be any text file: SQL schemas, API specs (OpenAPI/Protobuf),",
          "Terraform configs, Kubernetes manifests, architecture docs, etc.",
          "Directories are also supported — all files within will be indexed.",
        ].join("\n");
      }

      const projectId = projectIdFromPath(resolvedPath);
      const collection = contextCollectionName(projectId);
      const existingStates = await loadContextMetadata(collection);
      const stateMap = new Map(
        existingStates?.map((s) => [s.name, s]) ?? [],
      );

      const lines = [
        `Context Artifacts for: ${resolvedPath}`,
        `Config: .socraticodecontextartifacts.json (${config.artifacts.length} artifact${config.artifacts.length === 1 ? "" : "s"})`,
        "",
      ];

      for (const artifact of config.artifacts) {
        const state = stateMap.get(artifact.name);
        const status = state
          ? `✓ indexed (${state.chunksIndexed} chunks, ${state.lastIndexedAt})`
          : "○ not yet indexed";

        lines.push(`━━━ ${artifact.name} ━━━`);
        lines.push(`  Path: ${artifact.path}`);
        lines.push(`  Description: ${artifact.description}`);
        lines.push(`  Status: ${status}`);
        lines.push("");
      }

      lines.push(
        "Use codebase_context_search to search across artifacts.",
        "Use codebase_context_index to index/re-index all artifacts.",
        "Use codebase_context_remove to remove all indexed artifacts.",
      );

      return lines.join("\n");
    }

    case "codebase_context_index": {
      await ensureQdrantReady();
      // Only ensure Ollama infrastructure when using the Ollama embedding provider.
      // For OpenAI/Google providers, just ensure the provider is initialized.
      if (getEmbeddingConfig().embeddingProvider === "ollama") {
        await ensureOllamaReady();
      } else {
        await getEmbeddingProvider();
      }

      const config = await loadConfig(resolvedPath);
      if (!config?.artifacts?.length) {
        return `No artifacts defined in .socraticodecontextartifacts.json at ${resolvedPath}`;
      }

      logger.info("Indexing context artifacts", { projectPath: resolvedPath });
      const { indexed, errors } = await indexAllArtifacts(resolvedPath);

      const lines = [`Context Artifacts — Indexing Complete`, ""];

      if (indexed.length > 0) {
        lines.push(`✓ Indexed ${indexed.length} artifact${indexed.length === 1 ? "" : "s"}:`);
        for (const a of indexed) {
          lines.push(`  • ${a.name} — ${a.chunksIndexed} chunks`);
        }
        lines.push("");
      }

      if (errors.length > 0) {
        lines.push(`✗ ${errors.length} error${errors.length === 1 ? "" : "s"}:`);
        for (const e of errors) {
          lines.push(`  • ${e.name}: ${e.error}`);
        }
        lines.push("");
      }

      lines.push("Artifacts are now searchable via codebase_context_search.");
      return lines.join("\n");
    }

    case "codebase_context_search": {
      await ensureQdrantReady();
      // Only ensure Ollama infrastructure when using the Ollama embedding provider.
      // For OpenAI/Google providers, just ensure the provider is initialized.
      if (getEmbeddingConfig().embeddingProvider === "ollama") {
        await ensureOllamaReady();
      } else {
        await getEmbeddingProvider();
      }

      const query = args.query as string;
      if (!query?.trim()) {
        return "Error: query parameter is required for codebase_context_search.";
      }

      const artifactName = args.artifactName as string | undefined;
      const limit = (args.limit as number) || 10;

      // Auto-index: ensure artifacts are indexed and up to date
      const config = await loadConfig(resolvedPath);
      if (!config?.artifacts?.length) {
        return [
          `No context artifacts configured for: ${resolvedPath}`,
          "",
          "Create a .socraticodecontextartifacts.json file to define artifacts.",
          "Then use codebase_context_search to search them.",
        ].join("\n");
      }

      // Check if collection exists; if not, do full index
      const projectId = projectIdFromPath(resolvedPath);
      const collection = contextCollectionName(projectId);
      const collInfo = await getCollectionInfo(collection);

      if (!collInfo || collInfo.pointsCount === 0) {
        // First time — do full index
        logger.info("Auto-indexing context artifacts (first search)", { projectPath: resolvedPath });
        const { indexed, errors } = await indexAllArtifacts(resolvedPath);
        if (indexed.length === 0 && errors.length > 0) {
          return `Failed to index artifacts:\n${errors.map((e) => `  • ${e.name}: ${e.error}`).join("\n")}`;
        }
      } else {
        // Check for staleness and re-index changed artifacts
        const { reindexed, errors } = await ensureArtifactsIndexed(resolvedPath);
        if (reindexed.length > 0) {
          logger.info("Auto-re-indexed stale artifacts", {
            reindexed,
            projectPath: resolvedPath,
          });
        }
        if (errors.length > 0) {
          logger.warn("Some artifacts failed staleness check", { errors });
        }
      }

      // Search
      const allResults = await searchArtifacts(resolvedPath, query, artifactName, limit);

      // Apply minimum score threshold
      const minScore = (args.minScore as number) ?? SEARCH_MIN_SCORE;
      const results = minScore > 0
        ? allResults.filter((r) => r.score >= minScore)
        : allResults;
      const filteredCount = allResults.length - results.length;

      if (results.length === 0) {
        const filterNote = artifactName ? ` in artifact "${artifactName}"` : "";
        if (filteredCount > 0) {
          return `No results above score threshold ${minScore.toFixed(2)} for "${query}"${filterNote} in context artifacts of ${resolvedPath}.\n${filteredCount} result${filteredCount === 1 ? " was" : "s were"} below the threshold. Try a broader query or lower the minScore parameter.`;
        }
        return `No results found for "${query}"${filterNote} in context artifacts of ${resolvedPath}.\nCheck that your .socraticodecontextartifacts.json defines the relevant artifacts.`;
      }

      const lines = [
        `Context search results for "${query}" (${results.length} match${results.length === 1 ? "" : "es"}):`,
        "",
      ];

      for (const r of results) {
        const artifactLabel = (r as unknown as Record<string, unknown>).artifactName
          ?? r.language;
        lines.push(
          `--- ${r.relativePath} [${artifactLabel}] (lines ${r.startLine}-${r.endLine}) score: ${r.score.toFixed(4)} ---`,
        );
        lines.push(r.content);
        lines.push("");
      }

      if (filteredCount > 0) {
        lines.push(`(${filteredCount} additional result${filteredCount === 1 ? "" : "s"} below score threshold ${minScore.toFixed(2)} omitted)`);
      }

      return lines.join("\n");
    }

    case "codebase_context_remove": {
      // Guard: if indexing/update is in progress it includes context artifact indexing
      if (isIndexingInProgress(resolvedPath)) {
        return [
          `⚠ Cannot remove context artifacts: indexing is in progress for ${resolvedPath}`,
          "",
          "The current indexing/update operation includes context artifact indexing.",
          "Please wait for it to finish (use codebase_status) or stop it with codebase_stop first.",
        ].join("\n");
      }

      await ensureQdrantReady();

      await removeAllArtifacts(resolvedPath);
      return `Removed all indexed context artifacts for: ${resolvedPath}`;
    }

    default:
      return `Unknown context tool: ${name}`;
  }
}
