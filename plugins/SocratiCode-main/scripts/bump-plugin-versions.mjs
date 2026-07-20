#!/usr/bin/env node
// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
//
// release-it `after:bump` hook. Synchronises the version field across
// every plugin / extension manifest in the repo so a single engine
// release also bumps the Claude / Cursor / Codex plugins and the
// VS Code / Open VSX extension. Skips manifests that don't exist.
//
// Usage: node scripts/bump-plugin-versions.mjs <version>

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const MANIFESTS = [
  ".claude-plugin/plugin.json",
  ".cursor-plugin/plugin.json",
  ".codex-plugin/plugin.json",
  "extension/package.json",
];

const version = process.argv[2];
if (!version) {
  console.error("Usage: bump-plugin-versions.mjs <version>");
  process.exit(1);
}

let touched = 0;
for (const rel of MANIFESTS) {
  const path = resolve(process.cwd(), rel);
  if (!existsSync(path)) continue;
  try {
    const json = JSON.parse(readFileSync(path, "utf8"));
    if (json.version === version) continue;
    json.version = version;
    writeFileSync(path, `${JSON.stringify(json, null, 2)}\n`);
    console.log(`bumped ${rel} -> ${version}`);
    touched += 1;
  } catch (err) {
    console.error(`failed to bump ${rel}:`, err.message);
    process.exit(1);
  }
}

if (touched === 0) {
  console.log("no manifests needed bumping");
}
