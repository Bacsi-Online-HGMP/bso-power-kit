// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import fs from "node:fs";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createIgnoreFilter, shouldIgnore } from "../../src/services/ignore.js";
import { createFixtureProject, type FixtureProject } from "../helpers/fixtures.js";

describe("ignore", () => {
  let fixture: FixtureProject | null = null;
  const savedEnv: Record<string, string | undefined> = {};

  beforeEach(() => {
    savedEnv.RESPECT_GITIGNORE = process.env.RESPECT_GITIGNORE;
  });

  afterEach(() => {
    fixture?.cleanup();
    fixture = null;
    // Restore env
    if (savedEnv.RESPECT_GITIGNORE === undefined) {
      delete process.env.RESPECT_GITIGNORE;
    } else {
      process.env.RESPECT_GITIGNORE = savedEnv.RESPECT_GITIGNORE;
    }
  });

  describe("createIgnoreFilter", () => {
    it("returns an ignore filter object", () => {
      fixture = createFixtureProject("ignore-test");
      const ig = createIgnoreFilter(fixture.root);
      expect(ig).toBeDefined();
      expect(typeof ig.ignores).toBe("function");
    });

    it("ignores node_modules by default", () => {
      fixture = createFixtureProject("ignore-defaults");
      const ig = createIgnoreFilter(fixture.root);
      expect(ig.ignores("node_modules/package/index.js")).toBe(true);
    });

    it("ignores .git by default", () => {
      fixture = createFixtureProject("ignore-git");
      const ig = createIgnoreFilter(fixture.root);
      expect(ig.ignores(".git/config")).toBe(true);
    });

    it("ignores dist by default", () => {
      fixture = createFixtureProject("ignore-dist");
      const ig = createIgnoreFilter(fixture.root);
      expect(ig.ignores("dist/index.js")).toBe(true);
    });

    it("ignores common lock files by default", () => {
      fixture = createFixtureProject("ignore-locks");
      const ig = createIgnoreFilter(fixture.root);
      expect(ig.ignores("package-lock.json")).toBe(true);
      expect(ig.ignores("yarn.lock")).toBe(true);
      expect(ig.ignores("pnpm-lock.yaml")).toBe(true);
    });

    it("ignores .DS_Store by default", () => {
      fixture = createFixtureProject("ignore-ds");
      const ig = createIgnoreFilter(fixture.root);
      expect(ig.ignores(".DS_Store")).toBe(true);
    });

    it("respects .gitignore rules from the project root", () => {
      fixture = createFixtureProject("ignore-gitignore");
      // The fixture already has a .gitignore with "*.log"
      const ig = createIgnoreFilter(fixture.root);
      expect(ig.ignores("debug.log")).toBe(true);
      expect(ig.ignores("error.log")).toBe(true);
    });

    it("does not ignore source files", () => {
      fixture = createFixtureProject("ignore-src");
      const ig = createIgnoreFilter(fixture.root);
      expect(ig.ignores("src/index.ts")).toBe(false);
      expect(ig.ignores("lib/data_processor.py")).toBe(false);
      expect(ig.ignores("README.md")).toBe(false);
    });

    it("reads nested .gitignore files", () => {
      fixture = createFixtureProject("ignore-nested");

      // Create a nested .gitignore
      fs.mkdirSync(path.join(fixture.root, "packages", "sub"), { recursive: true });
      fs.writeFileSync(
        path.join(fixture.root, "packages", "sub", ".gitignore"),
        "temp/\n*.bak\n",
      );

      const ig = createIgnoreFilter(fixture.root);
      // Nested .gitignore patterns should be prefixed with the relative path
      expect(ig.ignores("packages/sub/temp/file.txt")).toBe(true);
      expect(ig.ignores("packages/sub/data.bak")).toBe(true);
    });

    it("reads .socraticodeignore if present", () => {
      fixture = createFixtureProject("ignore-socraticode");

      fs.writeFileSync(
        path.join(fixture.root, ".socraticodeignore"),
        "artifacts/\n*.generated.ts\n",
      );

      const ig = createIgnoreFilter(fixture.root);
      expect(ig.ignores("artifacts/bundle.js")).toBe(true);
      expect(ig.ignores("src/schema.generated.ts")).toBe(true);
      expect(ig.ignores("src/index.ts")).toBe(false);
    });

    it("does not load .socraticodeignore patterns when file is absent", () => {
      fixture = createFixtureProject("ignore-no-socraticode");

      const ig = createIgnoreFilter(fixture.root);
      // A pattern that would only match via .socraticodeignore
      expect(ig.ignores("custom-exclude/file.txt")).toBe(false);
      // Defaults still work
      expect(ig.ignores("node_modules/x.js")).toBe(true);
    });

    it("skips .gitignore when RESPECT_GITIGNORE=false", () => {
      fixture = createFixtureProject("ignore-skip-gitignore");

      // Write a .gitignore with a pattern NOT in built-in defaults
      fs.writeFileSync(
        path.join(fixture.root, ".gitignore"),
        "custom-ignored-dir/\n",
      );

      process.env.RESPECT_GITIGNORE = "false";

      const ig = createIgnoreFilter(fixture.root);
      // .gitignore patterns should be skipped
      expect(ig.ignores("custom-ignored-dir/file.txt")).toBe(false);
      // But default patterns should still be applied
      expect(ig.ignores("node_modules/x.js")).toBe(true);
    });

    it("respects .gitignore by default (RESPECT_GITIGNORE unset)", () => {
      fixture = createFixtureProject("ignore-default-gitignore");

      // Write a .gitignore with a pattern NOT in built-in defaults
      fs.writeFileSync(
        path.join(fixture.root, ".gitignore"),
        "custom-ignored-dir/\n",
      );

      delete process.env.RESPECT_GITIGNORE;

      const ig = createIgnoreFilter(fixture.root);
      // .gitignore patterns should work
      expect(ig.ignores("custom-ignored-dir/file.txt")).toBe(true);
    });

    it("skips nested .gitignore when RESPECT_GITIGNORE=false", () => {
      fixture = createFixtureProject("ignore-skip-nested");

      fs.mkdirSync(path.join(fixture.root, "packages", "sub"), { recursive: true });
      fs.writeFileSync(
        path.join(fixture.root, "packages", "sub", ".gitignore"),
        "temp/\n",
      );

      process.env.RESPECT_GITIGNORE = "false";

      const ig = createIgnoreFilter(fixture.root);
      // Nested .gitignore patterns should NOT be loaded
      expect(ig.ignores("packages/sub/temp/file.txt")).toBe(false);
    });

    it("handles project with no .gitignore", () => {
      fixture = createFixtureProject("ignore-no-gitignore");
      // Remove the .gitignore
      fs.unlinkSync(path.join(fixture.root, ".gitignore"));

      const ig = createIgnoreFilter(fixture.root);
      // Default patterns should still work
      expect(ig.ignores("node_modules/x.js")).toBe(true);
      // Source files should not be ignored
      expect(ig.ignores("src/index.ts")).toBe(false);
    });
  });

  describe("shouldIgnore", () => {
    it("returns true for ignored paths", () => {
      fixture = createFixtureProject("should-ignore-true");
      const ig = createIgnoreFilter(fixture.root);
      expect(shouldIgnore(ig, "node_modules/x.js")).toBe(true);
    });

    it("returns false for non-ignored paths", () => {
      fixture = createFixtureProject("should-ignore-false");
      const ig = createIgnoreFilter(fixture.root);
      expect(shouldIgnore(ig, "src/index.ts")).toBe(false);
    });

    it("ignores Python cache directories", () => {
      fixture = createFixtureProject("should-ignore-pycache");
      const ig = createIgnoreFilter(fixture.root);
      expect(shouldIgnore(ig, "__pycache__/module.pyc")).toBe(true);
    });

    it("ignores build output directories", () => {
      fixture = createFixtureProject("should-ignore-build");
      const ig = createIgnoreFilter(fixture.root);
      expect(shouldIgnore(ig, "build/output.js")).toBe(true);
      expect(shouldIgnore(ig, "out/bundle.js")).toBe(true);
    });

    it("ignores IDE directories", () => {
      fixture = createFixtureProject("should-ignore-ide");
      const ig = createIgnoreFilter(fixture.root);
      expect(shouldIgnore(ig, ".idea/workspace.xml")).toBe(true);
      expect(shouldIgnore(ig, ".vscode/settings.json")).toBe(true);
    });

    it("ignores minified files", () => {
      fixture = createFixtureProject("should-ignore-min");
      const ig = createIgnoreFilter(fixture.root);
      expect(shouldIgnore(ig, "assets/app.min.js")).toBe(true);
      expect(shouldIgnore(ig, "styles/main.min.css")).toBe(true);
    });

    it("ignores coverage directories", () => {
      fixture = createFixtureProject("should-ignore-coverage");
      const ig = createIgnoreFilter(fixture.root);
      // The fixture .gitignore includes "coverage/"
      expect(shouldIgnore(ig, "coverage/lcov.info")).toBe(true);
    });
  });
});
