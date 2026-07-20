// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import * as vscode from "vscode";

/**
 * Strongly-typed access to the `socraticode.*` configuration namespace.
 * Read settings via `getSettings()` rather than
 * `vscode.workspace.getConfiguration` directly so all keys are listed in
 * one place and tracked by TypeScript.
 */

export interface SocratiCodeSettings {
  command: string;
  args: string[];
  env: Record<string, string>;
  showStatusBar: boolean;
}

const SECTION = "socraticode";

export function getSettings(): SocratiCodeSettings {
  const c = vscode.workspace.getConfiguration(SECTION);
  return {
    command: c.get<string>("command", "npx"),
    args: c.get<string[]>("args", ["-y", "socraticode"]),
    env: c.get<Record<string, string>>("env", {}),
    showStatusBar: c.get<boolean>("statusBar", true),
  };
}
