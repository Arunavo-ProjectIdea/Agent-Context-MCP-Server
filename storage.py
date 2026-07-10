import os
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

class Storage:
    def __init__(self, project_dir: str = "."):
        self.project_dir = os.path.abspath(project_dir)
        self.agentctx_dir = os.path.join(self.project_dir, ".agentctx")
        self.db_path = os.path.join(self.agentctx_dir, "context.db")
        self._init_db()

    def _init_db(self):
        os.makedirs(self.agentctx_dir, exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            ''')
            
            # Progress log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS progress_log (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    entry TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                )
            ''')
            
            # Decisions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    symbol_ref TEXT,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                )
            ''')
            
            # Open questions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS open_questions (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    resolved BOOLEAN NOT NULL DEFAULT 0
                )
            ''')
            
            # Symbols table (Structure Graph)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS symbols (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    symbol_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    content_hash TEXT
                )
            ''')
            
            # Calls table (Structure Graph edges)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calls (
                    caller_id TEXT NOT NULL,
                    callee_id TEXT NOT NULL,
                    FOREIGN KEY(caller_id) REFERENCES symbols(id),
                    FOREIGN KEY(callee_id) REFERENCES symbols(id),
                    PRIMARY KEY(caller_id, callee_id)
                )
            ''')
            
            conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
