import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from storage import Storage

class WorkingContext:
    def __init__(self, storage: Storage):
        self.storage = storage

    def start_task(self, title: str) -> str:
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self.storage.get_connection() as conn:
            conn.execute(
                "INSERT INTO tasks (id, title, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (task_id, title, "active", now, now)
            )
            conn.commit()
        return task_id

    def log_progress(self, task_id: str, entry: str, entry_type: str) -> str:
        if entry_type not in ["step_done", "error_hit", "next_step", "note"]:
            raise ValueError(f"Invalid entry_type: {entry_type}")
        
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self.storage.get_connection() as conn:
            conn.execute(
                "INSERT INTO progress_log (id, task_id, entry, entry_type, created_at) VALUES (?, ?, ?, ?, ?)",
                (entry_id, task_id, entry, entry_type, now)
            )
            conn.execute(
                "UPDATE tasks SET updated_at = ? WHERE id = ?",
                (now, task_id)
            )
            conn.commit()
        return entry_id

    def log_decision(self, task_id: str, decision: str, reason: str, symbol_ref: Optional[str] = None) -> str:
        decision_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self.storage.get_connection() as conn:
            conn.execute(
                "INSERT INTO decisions (id, task_id, decision, reason, symbol_ref, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (decision_id, task_id, decision, reason, symbol_ref, now)
            )
            if task_id:
                conn.execute(
                    "UPDATE tasks SET updated_at = ? WHERE id = ?",
                    (now, task_id)
                )
            conn.commit()
        return decision_id

    def add_question(self, question: str) -> str:
        question_id = str(uuid.uuid4())
        with self.storage.get_connection() as conn:
            conn.execute(
                "INSERT INTO open_questions (id, question, resolved) VALUES (?, ?, ?)",
                (question_id, question, False)
            )
            conn.commit()
        return question_id

    def resolve_question(self, question_id: str) -> bool:
        with self.storage.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE open_questions SET resolved = 1 WHERE id = ?",
                (question_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def resume(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        with self.storage.get_connection() as conn:
            if not task_id:
                # Find the most recently updated active task
                cursor = conn.execute(
                    "SELECT id FROM tasks WHERE status = 'active' ORDER BY updated_at DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if not row:
                    return {"status": "No active tasks found."}
                task_id = row['id']
            
            task_cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            task = task_cursor.fetchone()
            if not task:
                return {"error": f"Task {task_id} not found."}

            progress_cursor = conn.execute(
                "SELECT * FROM progress_log WHERE task_id = ? ORDER BY created_at ASC", (task_id,)
            )
            progress = [dict(row) for row in progress_cursor.fetchall()]

            decisions_cursor = conn.execute(
                "SELECT * FROM decisions WHERE task_id = ? ORDER BY created_at ASC", (task_id,)
            )
            decisions = [dict(row) for row in decisions_cursor.fetchall()]

            questions_cursor = conn.execute(
                "SELECT * FROM open_questions WHERE resolved = 0"
            )
            questions = [dict(row) for row in questions_cursor.fetchall()]

            return {
                "task": dict(task),
                "progress": progress,
                "decisions": decisions,
                "open_questions": questions
            }

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.storage.get_connection() as conn:
            if status:
                cursor = conn.execute("SELECT * FROM tasks WHERE status = ? ORDER BY updated_at DESC", (status,))
            else:
                cursor = conn.execute("SELECT * FROM tasks ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]
