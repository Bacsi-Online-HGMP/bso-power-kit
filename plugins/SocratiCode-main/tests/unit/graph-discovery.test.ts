// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { ensureDynamicLanguages, getGraphableFiles } from "../../src/services/code-graph.js";

// Regression for the whitelist .gitignore discovery fix: a `/*` then `!/src/`
// pattern ignores everything at the root but re-includes `src/`. The old walk
// passed `src` (no trailing slash) to shouldIgnore, which `/*` matched, so the
// walk bailed and produced an empty graph. Passing `src/` lets it descend and
// the files under the re-included directory are actually picked up.
describe("getGraphableFiles — whitelist .gitignore", () => {
  let root: string;

  beforeAll(() => {
    ensureDynamicLanguages();
    root = fs.mkdtempSync(path.join(os.tmpdir(), "socraticode-discovery-"));
    fs.mkdirSync(path.join(root, "src"), { recursive: true });
    fs.writeFileSync(path.join(root, ".gitignore"), "/*\n!/src/\n");
    fs.writeFileSync(
      path.join(root, "src", "mod.lua"),
      "local function f()\n  return 1\nend\nreturn f\n",
    );
    // A root-level file the `/*` pattern should keep ignored.
    fs.writeFileSync(path.join(root, "ignored.lua"), "return 1\n");
  });

  afterAll(() => {
    try {
      fs.rmSync(root, { recursive: true, force: true });
    } catch {
      // ignore cleanup errors
    }
  });

  it("descends into re-included src/ and discovers its files", async () => {
    const files = await getGraphableFiles(root);
    expect(files).toContain("src/mod.lua");
    // The `/*` pattern still ignores top-level entries that are not re-included.
    expect(files).not.toContain("ignored.lua");
  });
});
