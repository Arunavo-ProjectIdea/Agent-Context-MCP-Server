import asyncio
import os
import shutil
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from typing import Optional, List, Dict, Any

from storage import Storage
from working_context import WorkingContext
from structure_graph import StructureGraph

# Initialize dependencies
storage = Storage()
context = WorkingContext(storage)
graph = StructureGraph(storage)

# Create the MCP server
mcp = FastMCP("Agent Context Server")

@mcp.tool()
def start_task(title: str) -> str:
    """Creates a new working context task and returns the task ID."""
    return context.start_task(title)

@mcp.tool()
def log_progress(task_id: str, entry: str, entry_type: str) -> str:
    """
    Appends a progress log entry to the task.
    Valid entry_type values: step_done, error_hit, next_step, note
    """
    return context.log_progress(task_id, entry, entry_type)

@mcp.tool()
def log_decision(task_id: str, decision: str, reason: str, symbol_ref: Optional[str] = None) -> str:
    """Logs a technical decision with its reason to the context."""
    return context.log_decision(task_id, decision, reason, symbol_ref)

@mcp.tool()
def add_question(question: str) -> str:
    """Adds an unresolved open question to the context."""
    return context.add_question(question)

@mcp.tool()
def resolve_question(question_id: str) -> bool:
    """Marks an open question as resolved."""
    return context.resolve_question(question_id)

@mcp.tool()
def resume(task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns the full state of a task (or the most recent active one if not provided):
    active task details, recent progress, decisions, and open questions.
    """
    return context.resume(task_id)

@mcp.tool()
def list_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists tasks, optionally filtered by status (active, done, blocked, abandoned)."""
    return context.list_tasks(status)

@mcp.tool(name="graph.index")
def graph_index(path: str, languages: Optional[List[str]] = None) -> Dict[str, Any]:
    """Parses a given file path and saves the extracted symbols to the symbols table."""
    return graph.index(path, languages)

@mcp.tool(name="graph.get_symbol")
def graph_get_symbol(name: str) -> List[Dict[str, Any]]:
    """Retrieves a symbol's info, file, and line numbers from the database."""
    return graph.get_symbol(name)

@mcp.tool(name="graph.trace_calls")
def graph_trace_calls(symbol_name: str, direction: str) -> List[Dict[str, Any]]:
    """Returns the inbound or outbound call chain for a given symbol. direction: 'inbound' or 'outbound'"""
    return graph.trace_calls(symbol_name, direction)

@mcp.tool(name="graph.get_architecture")
def graph_get_architecture() -> Dict[str, Any]:
    """Returns a basic high-level overview of the parsed codebase, including files, symbol counts, and uncalled symbols."""
    return graph.get_architecture()

@mcp.tool(name="project.export")
def project_export() -> Dict[str, Any]:
    """Creates a compressed zip backup of the entire .agentctx/ directory."""
    agentctx_dir = storage.agentctx_dir
    if not os.path.exists(agentctx_dir):
        return {"error": f"Directory not found: {agentctx_dir}"}
        
    backups_dir = os.path.join(agentctx_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"context_backup_{timestamp}"
    backup_path = os.path.join(backups_dir, backup_filename)
    
    # We zip everything in .agentctx, except we don't want to recursively zip backups if they get too big, 
    # but for simplicity we'll just zip the whole agentctx folder (or just the db).
    # Since sqlite db might be locked, just copying the db or zipping it is fine for a backup.
    shutil.make_archive(backup_path, 'zip', agentctx_dir)
    
    return {
        "status": "success", 
        "backup_path": f"{backup_path}.zip"
    }

def main():
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
