# Agent Context MCP Server

A portable, tool-agnostic memory and code structure graph for agentic AI coding tools (OpenCode, Antigravity, Claude Code, etc.). 

## 🧠 The Problem
Agentic AI tools typically keep their memory locked inside a single session. When you run out of context tokens or switch to a different AI tool, you lose:
- What you were currently working on (tasks, pending steps).
- Why past technical decisions were made.
- The structural architecture of the codebase.

## 🚀 The Solution
The **Agent Context Server** is an MCP (Model Context Protocol) server that tracks working context and code structure in a lightweight, local SQLite database (`.agentctx/context.db`). It provides a single, portable memory that follows the *project* rather than the *tool*. 

You can start a task in one AI tool, hit a context limit, open a completely different AI tool, and resume exactly where you left off.

## ✨ Features
*   **Working Context Engine:** Tracks active tasks, decisions, progress logs, and open questions across sessions.
*   **Code Structure Graph:** Uses `tree-sitter` to parse and map `Python`, `JavaScript`, and `TypeScript` files, extracting classes, functions, and methods without sending your code to external APIs.
*   **Incremental Indexing:** Smart content-hashing ensures only modified files are re-indexed.
*   **Project Export:** Built-in tools to instantly zip and backup your agent's memory state.
*   **Fully Local & Private:** No LLM calls inside the server; all state is kept entirely locally via SQLite.

## 🛠️ Prerequisites
*   [Python 3.10+](https://www.python.org/)
*   [uv](https://docs.astral.sh/uv/) (Fast Python package and project manager)

## 📦 Installation

1. Clone this repository to your machine:
   ```bash
   git clone [https://github.com/YOUR-USERNAME/agent-context-mcp-server.git](https://github.com/YOUR-USERNAME/agent-context-mcp-server.git)
   cd agent-context-mcp-server
   ```
2. The project uses `uv` for dependency management. The required packages (`mcp`, `tree-sitter`, `tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`) will be automatically managed when you run the server.

## ⚙️ MCP Configuration

To use this server with your preferred agentic AI tool (like Google Antigravity, OpenCode, or Claude Code), add the following to your MCP configuration settings:

```json
{
  "mcpServers": {
    "agent-context-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/agent-context-mcp-server",
        "run",
        "server.py"
      ]
    }
  }
}
```

> **Note:** Replace `/absolute/path/to/agent-context-mcp-server` with the actual path where you cloned this repository. The server will dynamically create the `.agentctx/` directory in whatever project folder your AI agent is currently working in.

---

## 🧰 Available Tools

Once connected, your AI agent will have access to the following tools:

### Working Context
*   **`start_task(title)`**: Creates a new working context task.
*   **`log_progress(task_id, entry, entry_type)`**: Appends a progress log (`step_done`, `error_hit`, `next_step`, `note`).
*   **`log_decision(task_id, decision, reason, symbol_ref)`**: Logs technical decisions and the reasoning behind them.
*   **`add_question(question)` / `resolve_question(question_id)`**: Manages open questions.
*   **`resume(task_id?)`**: Retrieves the full state of the active task to seamlessly pick up work.
*   **`list_tasks(status?)`**: Lists active, done, blocked, or abandoned tasks.

### Structure Graph
*   **`graph.index(path, languages?)`**: Parses a file (`.py`, `.js`, `.ts`, `.jsx`, `.tsx`) and extracts structural symbols.
*   **`graph.get_symbol(name)`**: Retrieves a specific symbol's file path and line numbers.
*   **`graph.trace_calls(symbol_name, direction)`**: Traces inbound or outbound function calls within the same file.
*   **`graph.get_architecture()`**: Returns a high-level overview of the parsed codebase, including files, symbol counts, and root entry points.

### Lifecycle
*   **`project.export()`**: Zips the entire `.agentctx/` directory for safe backup and sharing.

---

## 📄 License
*   **MIT License**
