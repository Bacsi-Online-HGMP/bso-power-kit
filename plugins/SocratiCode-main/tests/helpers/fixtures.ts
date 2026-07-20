// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
/**
 * Test helpers for SocratiCode test suite.
 *
 * Provides:
 * - Temporary project fixture creation
 * - Docker availability detection
 * - Test collection cleanup
 */

import { execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// ── Docker availability ──────────────────────────────────────────────────

let _dockerAvailable: boolean | null = null;

/**
 * Check if Docker is available for integration tests.
 * Cached after first call.
 */
export function isDockerAvailable(): boolean {
  if (_dockerAvailable !== null) return _dockerAvailable;
  try {
    execSync("docker info", { stdio: "ignore", timeout: 5000 });
    _dockerAvailable = true;
  } catch {
    _dockerAvailable = false;
  }
  return _dockerAvailable;
}

// ── Fixture project creation ─────────────────────────────────────────────

export interface FixtureProject {
  /** Absolute path to the temporary project directory */
  root: string;
  /** Clean up the temporary directory */
  cleanup: () => void;
}

/**
 * Creates a temporary project directory with realistic multi-language source files
 * that have import relationships for graph testing and meaningful content for
 * embedding/search testing.
 */
export function createFixtureProject(name = "test-project"): FixtureProject {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `socraticode-${name}-`));

  // Create directory structure
  fs.mkdirSync(path.join(root, "src"), { recursive: true });
  fs.mkdirSync(path.join(root, "src", "utils"), { recursive: true });
  fs.mkdirSync(path.join(root, "lib"), { recursive: true });

  // ── TypeScript files with imports ──────────────────────────────────────

  fs.writeFileSync(
    path.join(root, "src", "index.ts"),
    `import { greet } from "./utils/helpers.js";
import { UserConfig } from "./types.js";
import { add, multiply } from "./utils/math.js";

/**
 * Main entry point for the application.
 * Initializes the user configuration and starts the greeting service.
 */
export function main(): void {
  const config: UserConfig = {
    name: "World",
    verbose: true,
    maxRetries: 3,
  };

  console.log(greet(config.name));
  console.log("Sum:", add(2, 3));
  console.log("Product:", multiply(4, 5));
}

/**
 * Authentication middleware that validates JWT tokens
 * and checks user permissions against the database.
 */
export function authenticateUser(token: string): boolean {
  if (!token || token.length < 10) {
    return false;
  }
  // Validate token structure
  const parts = token.split(".");
  return parts.length === 3;
}

main();
`,
  );

  fs.writeFileSync(
    path.join(root, "src", "types.ts"),
    `/**
 * Configuration interface for user settings.
 * Controls application behavior and retry logic.
 */
export interface UserConfig {
  name: string;
  verbose: boolean;
  maxRetries: number;
}

/**
 * Represents a database connection with pooling configuration.
 */
export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  poolSize: number;
}

/**
 * Result type for async operations with error handling.
 */
export type Result<T> = { ok: true; value: T } | { ok: false; error: string };
`,
  );

  fs.writeFileSync(
    path.join(root, "src", "utils", "helpers.ts"),
    `/**
 * Helper utilities for string processing and formatting.
 */

/**
 * Generate a greeting message for the given name.
 * Supports customizable greeting prefix.
 */
export function greet(name: string, prefix = "Hello"): string {
  return \`\${prefix}, \${name}!\`;
}

/**
 * Convert a string to title case.
 * Handles edge cases like empty strings and single characters.
 */
export function toTitleCase(str: string): string {
  if (!str) return str;
  return str
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Debounce a function call with the specified delay.
 * Returns a cleanup function to cancel pending invocations.
 */
export function debounce<T extends (...args: unknown[]) => void>(
  fn: T,
  delayMs: number,
): { call: (...args: Parameters<T>) => void; cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return {
    call: (...args) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delayMs);
    },
    cancel: () => {
      if (timer) clearTimeout(timer);
    },
  };
}
`,
  );

  fs.writeFileSync(
    path.join(root, "src", "utils", "math.ts"),
    `/**
 * Mathematical utility functions for numerical operations.
 */

/**
 * Add two numbers together and return the sum.
 */
export function add(a: number, b: number): number {
  return a + b;
}

/**
 * Multiply two numbers and return the product.
 */
export function multiply(a: number, b: number): number {
  return a * b;
}

/**
 * Calculate the factorial of a non-negative integer.
 * Uses iterative approach for better performance.
 */
export function factorial(n: number): number {
  if (n < 0) throw new Error("Factorial is not defined for negative numbers");
  if (n <= 1) return 1;
  let result = 1;
  for (let i = 2; i <= n; i++) {
    result *= i;
  }
  return result;
}

/**
 * Calculate the Fibonacci number at position n.
 * Returns the nth number in the Fibonacci sequence.
 */
export function fibonacci(n: number): number {
  if (n <= 0) return 0;
  if (n === 1) return 1;
  let prev = 0, curr = 1;
  for (let i = 2; i <= n; i++) {
    [prev, curr] = [curr, prev + curr];
  }
  return curr;
}
`,
  );

  // ── Python file ────────────────────────────────────────────────────────

  fs.writeFileSync(
    path.join(root, "lib", "data_processor.py"),
    `"""
Data processing module for CSV and JSON transformations.
Provides utilities for cleaning, filtering, and aggregating data.
"""

import json
from typing import Any, Dict, List, Optional


def load_json_file(filepath: str) -> Dict[str, Any]:
    """Load and parse a JSON file from disk."""
    with open(filepath, 'r') as f:
        return json.load(f)


def filter_records(
    records: List[Dict[str, Any]],
    key: str,
    value: Any,
) -> List[Dict[str, Any]]:
    """Filter a list of records by a specific key-value pair."""
    return [r for r in records if r.get(key) == value]


def aggregate_sum(records: List[Dict[str, Any]], field: str) -> float:
    """Calculate the sum of a numeric field across all records."""
    total = 0.0
    for record in records:
        val = record.get(field, 0)
        if isinstance(val, (int, float)):
            total += val
    return total


class DataPipeline:
    """
    A configurable data pipeline that applies a series of
    transformation steps to input data.
    """

    def __init__(self, name: str):
        self.name = name
        self.steps: List[callable] = []

    def add_step(self, transform: callable) -> 'DataPipeline':
        """Add a transformation step to the pipeline."""
        self.steps.append(transform)
        return self

    def execute(self, data: Any) -> Any:
        """Run all transformation steps in sequence."""
        result = data
        for step in self.steps:
            result = step(result)
        return result
`,
  );

  // ── Config files ───────────────────────────────────────────────────────

  fs.writeFileSync(
    path.join(root, "package.json"),
    `${JSON.stringify(
      {
        name: "test-fixture-project",
        version: "1.0.0",
        type: "module",
        main: "src/index.ts",
      },
      null,
      2,
    )}\n`,
  );

  fs.writeFileSync(
    path.join(root, ".gitignore"),
    `node_modules/
dist/
*.log
.env
coverage/
`,
  );

  // ── Markdown documentation ─────────────────────────────────────────────

  fs.writeFileSync(
    path.join(root, "README.md"),
    `# Test Fixture Project

A sample project used for testing the SocratiCode indexer.

## Features

- TypeScript source files with import relationships
- Python data processing utilities
- Mathematical helper functions
- Authentication middleware example

## Getting Started

Install dependencies and run the application:

\`\`\`bash
npm install
npm start
\`\`\`
`,
  );

  return {
    root,
    cleanup: () => {
      try {
        fs.rmSync(root, { recursive: true, force: true });
      } catch {
        // Ignore cleanup errors
      }
    },
  };
}

/**
 * Add a new file to an existing fixture project.
 * Useful for testing incremental updates.
 */
export function addFileToFixture(
  projectRoot: string,
  relativePath: string,
  content: string,
): void {
  const fullPath = path.join(projectRoot, relativePath);
  fs.mkdirSync(path.dirname(fullPath), { recursive: true });
  fs.writeFileSync(fullPath, content);
}

/**
 * Modify an existing file in a fixture project.
 * Useful for testing watch/update behavior.
 */
export function modifyFixtureFile(
  projectRoot: string,
  relativePath: string,
  content: string,
): void {
  const fullPath = path.join(projectRoot, relativePath);
  if (!fs.existsSync(fullPath)) {
    throw new Error(`File does not exist: ${fullPath}`);
  }
  fs.writeFileSync(fullPath, content);
}

/**
 * Remove a file from a fixture project.
 * Useful for testing incremental removal.
 */
export function removeFixtureFile(projectRoot: string, relativePath: string): void {
  const fullPath = path.join(projectRoot, relativePath);
  if (fs.existsSync(fullPath)) {
    fs.unlinkSync(fullPath);
  }
}
