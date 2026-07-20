// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited
//
// esbuild bundle for the VS Code / Open VSX extension. The extension is
// shipped as a single CommonJS bundle (VS Code's runtime requirement),
// with `vscode` marked external. We avoid `node_modules` in the .vsix
// because everything we need either resolves at runtime via VS Code's
// host (`vscode`) or is part of the Node 18+ stdlib.

import { build, context } from "esbuild";

const watch = process.argv.includes("--watch");

const options = {
  entryPoints: ["src/extension.ts"],
  bundle: true,
  outfile: "dist/extension.js",
  external: ["vscode"],
  format: "cjs",
  platform: "node",
  target: "node18",
  sourcemap: true,
  minify: !watch,
  logLevel: "info",
};

if (watch) {
  const ctx = await context(options);
  await ctx.watch();
  console.log("[esbuild] watching for changes...");
} else {
  await build(options);
}
