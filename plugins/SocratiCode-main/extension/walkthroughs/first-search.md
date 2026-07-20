# Try a search and the interactive graph

Now your codebase is indexed, two things to try.

## Ask your AI assistant

In Copilot agent mode, Cline, Continue or Roo Code, ask any of:

- "Where is authentication handled in this project?"
- "What breaks if I change the function `processOrder`?"
- "Trace the execution flow of the cron job that runs nightly."
- "Show me every place that talks to the `users` table."

The assistant will call SocratiCode's MCP tools (`codebase_search`,
`codebase_impact`, `codebase_flow`, `codebase_symbol`, etc.) automatically.

## Open the interactive graph

Run **SocratiCode: Open interactive graph** from the command palette. The
graph opens as a webview panel inside VS Code with:

- File and symbol views (toggle between them).
- Blast-radius overlay (click a node to highlight its impact set).
- Search by name.
- PNG export for architects, security reviewers and slide decks.

If no graph has been generated yet, the extension will prompt your AI
assistant to run `codebase_graph_visualize mode="interactive"` first.

## Next steps

- Check **SocratiCode: Show output / logs** if anything looks off.
- Re-open this walkthrough any time via the command palette.
- See the [engine README](https://github.com/giancarloerra/socraticode#readme)
  for configuration knobs (embedding provider, Qdrant mode, project IDs,
  branch-aware indexing, linked projects for cross-repo search).
