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
            subject_id INTEGER,
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

def create_task(task_id: str, file_name: str, subject_id: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO tasks (task_id, status, file_name, subject_id, total_embedded, stored, error_message, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "PROCESSING", file_name, subject_id, 0, 0, None, now, now)
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
        "SELECT task_id, status, file_name, subject_id, total_embedded, stored, error_message, created_at, updated_at FROM tasks WHERE task_id = ?",
        (task_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

from app.ingestion.pdf_type_detection import get_pdf_type
from app.core.helpers import sanitize_filename
from app.ingestion.text_extractor import extract_text
from app.ingestion.create_chunks import create_chunks
from app.embedings.embedder import embed_chunks
from app.embedings.store import store_embedings
from app.core.database import async_session_local
from app.ingestion.scanned_extractor import extract_scanned_pdf
from app.schemas.subject_schemas import SubjectBase
from app.models.subject_models import Subject

async def run_ingestion_task(
        task_id: str,
        temp_filepath: str, 
        original_filename: str,
        subject_id: int
    ):
    try:
        # 1. Read the saved temp file contents
        with open(temp_filepath, "rb") as f:
            contents = f.read()
        
        # 2. Ingest
        update_task_status(task_id, "EXTRACTING_TEXT")
        pdf_type = await get_pdf_type(contents)
        file_name = sanitize_filename(original_filename)
        
        # Resolve subject or dynamically register it if not found
        async with async_session_local() as db:
            subject = await db.get(Subject, subject_id)
            if not subject:
                raise ValueError(f"Subject with id {subject_id} not found")
        
        if pdf_type == "native":
            doc_content_md = await extract_text(contents, file_name, subject.subject_name, subject.subject_id)
            
            update_task_status(task_id, "CHUNKING")
            chunks = create_chunks(md=doc_content_md)
            
            update_task_status(task_id, "EMBEDDING")
            embeddings = embed_chunks(chunks=chunks)
            
            update_task_status(task_id, "STORING")
            stored = store_embedings(embeddings)
        else:
            chunks = await extract_scanned_pdf(contents, file_name, subject.subject_name, subject_id=subject.subject_id)
            
            update_task_status(task_id, "EMBEDDING")
            embeddings = embed_chunks(chunks=chunks)
            
            update_task_status(task_id, "STORING")
            stored = store_embedings(embeddings)
            
        update_task_status(task_id, "COMPLETED", total_embedded=len(embeddings), stored=stored)
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"Error in background ingestion task {task_id}: {error_msg}")
        update_task_status(task_id, "FAILED", error_message=str(e))
    finally:
        # Clean up the local temp PDF file
        try:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        except Exception as e:
            print(f"Error deleting temporary file {temp_filepath}: {e}")
