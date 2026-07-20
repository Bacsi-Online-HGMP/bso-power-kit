# Support

## Getting Help

### Documentation

- **[README](README.md)** — Setup, configuration, environment variables, FAQ
- **[Developer Guide](DEVELOPER.md)** — Architecture, data flows, testing, internals

### Community

- **[Discord](https://discord.gg/dHNMKVY2J2)** — Real-time chat: ask "how do I…", get setup help, share what you're building
- **[GitHub Issues](https://github.com/giancarloerra/socraticode/issues)** — Report bugs or request features (use the templates provided)

### Troubleshooting

Before opening an issue, try these steps:

1. **Check the FAQ** in the [README](README.md#faq)
2. **Enable debug logging** — set `SOCRATICODE_LOG_LEVEL=debug` and/or `SOCRATICODE_LOG_FILE=/tmp/socraticode.log` in your MCP config
3. **Check Docker** — run `docker ps` to verify containers are running
4. **Check health** — ask your AI to run `codebase_health` for a full infrastructure status report
5. **Search existing issues** — your question may already have an answer

### Common Issues

| Problem | Solution |
|---------|----------|
| "Docker is not available" | Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| Slow indexing on macOS/Windows | Install [native Ollama](https://ollama.com/download) for GPU acceleration, or use OpenAI embeddings |
| Search returns no results | Ensure the project is indexed (`codebase_status`) |
| MCP host disconnects during indexing | Poll `codebase_status` every ~60s to keep the connection alive; indexing resumes automatically |

## Commercial Support

For commercial licensing or enterprise support, contact **[giancarlo@altaire.com](mailto:giancarlo@altaire.com)**.
