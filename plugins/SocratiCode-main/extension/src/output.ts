// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import * as vscode from "vscode";

/**
 * Shared output channel for the extension. Created once on activation,
 * disposed on deactivation. Use `output()` everywhere instead of
 * `console.log` so users can see logs via the "SocratiCode: Show output /
 * logs" command.
 */
let channel: vscode.OutputChannel | undefined;

export function initOutput(context: vscode.ExtensionContext): void {
  channel = vscode.window.createOutputChannel("SocratiCode");
  context.subscriptions.push(channel);
}

export function output(): vscode.OutputChannel {
  if (!channel) {
    // Defensive fallback for tests or unexpected ordering.
    channel = vscode.window.createOutputChannel("SocratiCode");
  }
  return channel;
}

export function log(message: string): void {
  const ts = new Date().toISOString();
  output().appendLine(`[${ts}] ${message}`);
}
