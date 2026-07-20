# SocratiCode VS Code / Open VSX extension changelog

All notable changes to the extension are documented here. The extension
version tracks the engine version where possible.

## 1.7.2

Initial release.

### Features

- Auto-registers the SocratiCode MCP server in VS Code's MCP host (Copilot
  agent mode, Cline, Continue, Roo Code) via
  `vscode.lm.registerMcpServerDefinitionProvider`. No `mcp.json` editing
  required.
- Activity-bar sidebar with "Indexed projects" tree view and welcome
  content.
- Status-bar item with click-to-open-sidebar.
- Webview-based interactive graph viewer (reads the HTML produced by the
  engine's `codebase_graph_visualize` tool).
- Getting-started walkthrough (index your project, try search and the
  interactive graph).
- Commands palette entries:
  - SocratiCode: Index current workspace
  - SocratiCode: Open interactive graph
  - SocratiCode: Refresh indexed projects
  - SocratiCode: Open getting-started walkthrough
  - SocratiCode: Show output / logs
- Output channel for engine logs.
- Engine env-var passthrough via `socraticode.env`, so external Qdrant,
  alternate embedding providers, project IDs and other engine knobs all
  work out of the box.
