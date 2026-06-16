import sqlite3
import os
from datetime import datetime

DB_PATH = "data/subjects.db"

def init_task_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            file_name TEXT,
            subject TEXT,
            total_embedded INTEGER,
            stored INTEGER,
            error_message TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB on module import
init_task_db()

def create_task(task_id: str, file_name: str, subject: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO tasks (task_id, status, file_name, subject, total_embedded, stored, error_message, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "PROCESSING", file_name, subject, 0, 0, None, now, now)
    )
    conn.commit()
    conn.close()

def update_task_status(task_id: str, status: str, total_embedded: int = 0, stored: int = 0, error_message: str | None = None) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        UPDATE tasks
        SET status = ?, total_embedded = ?, stored = ?, error_message = ?, updated_at = ?
        WHERE task_id = ?
        """,
        (status, total_embedded, stored, error_message, now, task_id)
    )
    conn.commit()
    conn.close()

def get_task(task_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT task_id, status, file_name, subject, total_embedded, stored, error_message, created_at, updated_at FROM tasks WHERE task_id = ?",
        (task_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None
