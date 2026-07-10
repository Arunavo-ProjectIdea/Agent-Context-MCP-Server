# Agent Context MCP Server

Agent Context Server is a portable, tool-agnostic memory and code structure graph for agentic AI tools. It aims to solve the problem of context loss between AI coding sessions by maintaining a persistent "working context" for your projects.

## Features

- **Working Context Tracking**: Persists tasks, progress logs, decisions, and open questions directly to a local SQLite database (`.agentctx/context.db`), enabling seamless cross-tool handoffs.
- **Code Structure Graph**: Uses `tree-sitter` to parse your codebase into a structure graph. Automatically extracts class, function, and method definitions and resolves intra-file function calls for both Python and JavaScript/TypeScript.
- **Incremental Indexing**: Efficiently indexes your files using a SHA-256 content hash to skip unmodified files during re-indexing.
- **Project Export**: Need to backup or share your context? An exposed tool lets you compress and dump your entire `.agentctx` directory into a portable zip archive in seconds.

## Installation

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone https://github.com/your-username/agent-context-server.git
cd agent-context-server

# Install dependencies (MCP SDK, tree-sitter, etc.)
uv sync
```

## Configuring Your Agent

To hook this MCP server into your agent (e.g., OpenCode, Antigravity, Claude Code), add the following entry to your MCP configuration file:

```json
{
  "agent-context-server": {
    "command": "uv",
    "args": ["run", "server.py"]
  }
}
```

*Note: You may also need to configure the working directory parameter (`cwd` or equivalent) to point directly to your `agent-context-server` project folder depending on your agent's MCP setup.*
