# deepset-mcp

**The official MCP server and Python SDK for the deepset AI platform**

deepset-mcp enables AI agents to build and debug pipelines on the [Haystack Enterprise AI platform](https://www.deepset.ai/products-and-services/deepset-ai-platform) through 30+ specialized tools. It also provides a Python SDK for programmatic access to many platform resources.

## Documentation

📖 **[View the full documentation](https://deepset-ai.github.io/deepset-mcp-server/)**

## Quick Links

- 🔗 **[Haystack Enterprise AI platform](https://www.deepset.ai/products-and-services/deepset-ai-platform)**
- 📚 **[Installation Guide](https://deepset-ai.github.io/deepset-mcp-server/installation/)**
- 🛠️ **[MCP Server Guide](https://deepset-ai.github.io/deepset-mcp-server/guides/mcp_server/)**
- 🐍 **[Python SDK Guide](https://deepset-ai.github.io/deepset-mcp-server/guides/api_sdk/)**

## Development

### Installation

Install the project using [uv](https://docs.astral.sh/uv/):

```bash
# Install uv first
pipx install uv

# Install project with all dependencies
uv sync --locked --all-extras --all-groups
```

### Local Development

If you want to test your changes locally, follow these steps:

1. Add a script run-deepset-mcp.sh that uses the binary from the project's virtual env

```bash
#!/usr/bin/env bash
# Wrapper to run the local deepset-mcp server for Cursor MCP.
# Use this as command so it doesn't depend on uv or PATH.
set -e
cd "$(dirname "$0")"
exec .venv/bin/deepset-mcp
```

2. Use it this way in Cursor:

```bash
    "deepset": {
      "command": "/bin/bash",
      "args": ["/Users/*****/****/deepset-mcp-server/run-deepset-mcp.sh"],
      "cwd": "/Users/*****/****/deepset-mcp-server",
      "env": {
        "DEEPSET_WORKSPACE": "WORKSPACE",
        "DEEPSET_API_KEY": "API_KEY"
      }
    }
```

Note: If you change the codebase, make sure to restart the MCP server.

### Code Quality & Testing

Run code quality checks and tests using the Makefile:

```bash
# Install dependencies
make install

# Code quality
make lint          # Run ruff linting
make format        # Format code with ruff
make types         # Run mypy type checking

# Testing
make test          # Run unit tests (default)
make test-unit     # Run unit tests only
make test-integration     # Run integration tests
make test-all      # Run all tests

# Clean up
make clean         # Remove cache files
```

### Documentation

Documentation is built using [MkDocs](https://www.mkdocs.org/) with the Material theme:

- Configuration: `mkdocs.yml`
- Content: `docs/` directory
- Auto-generated API docs via [mkdocstrings](https://mkdocstrings.github.io/)
- Deployed via GitHub Pages (automated via GitHub Actions on push to main branch)
