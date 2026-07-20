// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

/**
 * Smoke tests for the extension manifest. These don't exercise extension
 * code that imports `vscode` (that requires `@vscode/test-electron`), but
 * they do catch the most common ways an extension breaks before it ever
 * loads: a missing or malformed `package.json` field, a contribution
 * point that disappeared in a refactor, an icon that no longer exists.
 *
 * Run with: `npm test` from `extension/`.
 */

import { strict as assert } from "node:assert";
import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, test } from "node:test";

// __dirname works because tsx loads these tests as CommonJS (the extension's
// package.json has no `"type": "module"` field). Avoiding `import.meta.url`
// keeps the tests compatible with the same `module: Node16` tsconfig the
// runtime code uses.
const extensionRoot = resolve(__dirname, "..", "..");
const manifestPath = join(extensionRoot, "package.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

describe("extension manifest", () => {
  test("declares a valid publisher and name", () => {
    assert.equal(typeof manifest.publisher, "string");
    assert.match(manifest.publisher, /^[a-z0-9][a-z0-9-]*$/i);
    assert.equal(typeof manifest.name, "string");
    assert.match(manifest.name, /^[a-z0-9][a-z0-9-]*$/i);
  });

  test("targets VS Code 1.99+ (required for native MCP API)", () => {
    assert.ok(manifest.engines?.vscode, "engines.vscode missing");
    assert.match(manifest.engines.vscode, /\^1\.(99|\d{3,})/);
  });

  test("declares the SocratiCode MCP provider", () => {
    const providers = manifest.contributes?.mcpServerDefinitionProviders;
    assert.ok(Array.isArray(providers), "mcpServerDefinitionProviders missing");
    assert.equal(providers.length, 1);
    assert.equal(providers[0].id, "socraticode.mcp");
  });

  test("registers all expected commands", () => {
    const commands = manifest.contributes?.commands ?? [];
    const ids = commands.map((c: { command: string }) => c.command);
    for (const expected of [
      "socraticode.indexCurrentWorkspace",
      "socraticode.openInteractiveGraph",
      "socraticode.refreshProjects",
      "socraticode.openWalkthrough",
      "socraticode.openOutput",
    ]) {
      assert.ok(ids.includes(expected), `missing command: ${expected}`);
    }
  });

  test("declares the activity bar container and projects view", () => {
    const containers = manifest.contributes?.viewsContainers?.activitybar;
    assert.ok(Array.isArray(containers));
    assert.ok(containers.some((c: { id: string }) => c.id === "socraticode"));
    const views = manifest.contributes?.views?.socraticode;
    assert.ok(Array.isArray(views));
    assert.ok(views.some((v: { id: string }) => v.id === "socraticode.projects"));
  });

  test("ships the configured icon and walkthrough media files", () => {
    assert.ok(manifest.icon, "icon path missing");
    assert.ok(
      existsSync(join(extensionRoot, manifest.icon)),
      `icon file not found at ${manifest.icon}`,
    );
    const walkthroughs = manifest.contributes?.walkthroughs ?? [];
    for (const wt of walkthroughs) {
      for (const step of wt.steps ?? []) {
        const md = step.media?.markdown;
        if (md) {
          assert.ok(existsSync(join(extensionRoot, md)), `walkthrough markdown missing: ${md}`);
        }
      }
    }
  });

  test("declares the settings the runtime reads", () => {
    const props = manifest.contributes?.configuration?.properties ?? {};
    for (const key of [
      "socraticode.command",
      "socraticode.args",
      "socraticode.env",
      "socraticode.statusBar",
    ]) {
      assert.ok(props[key], `missing settings property: ${key}`);
    }
  });

  test("uses an MCP-host-compatible activation event", () => {
    const events = manifest.activationEvents ?? [];
    assert.ok(
      events.includes("onStartupFinished"),
      "extension must activate on startup so the MCP provider is ready before chat",
    );
  });

  test("declares scripts the CI release workflow expects", () => {
    const scripts = manifest.scripts ?? {};
    for (const key of [
      "compile",
      "typecheck",
      "lint",
      "test",
      "package",
      "publish:vsce",
      "publish:ovsx",
    ]) {
      assert.ok(scripts[key], `missing script: ${key}`);
    }
  });
});
