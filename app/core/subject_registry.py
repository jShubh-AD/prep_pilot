import sqlite3
import json
import os
import re
from app.models.ingestion_model import SubjectModel

DB_PATH = "data/subjects.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id TEXT PRIMARY KEY,
            subject_name TEXT UNIQUE NOT NULL,
            university TEXT,
            subject_code TEXT,
            aliases TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB on module import
init_db()

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'[\s-]+', '_', text)

def register_subject(
    subject_name: str,
    subject_id: str | None = None,
    university: str | None = None,
    subject_code: str | None = None,
    aliases: list[str] | None = None
) -> SubjectModel:
    if not subject_id:
        subject_id = slugify(subject_name)
    
    alias_list = aliases or []
    # Ensure subject_name and subject_id themselves are included in list of search keys implicitly,
    # but store custom aliases in database as JSON
    alias_json = json.dumps([a.lower().strip() for a in alias_list])
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO subjects (subject_id, subject_name, university, subject_code, aliases)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(subject_id) DO UPDATE SET
                subject_name=excluded.subject_name,
                university=excluded.university,
                subject_code=excluded.subject_code,
                aliases=excluded.aliases
            """,
            (subject_id, subject_name, university, subject_code, alias_json)
        )
        conn.commit()
    finally:
        conn.close()
        
    return SubjectModel(
        subject_name=subject_name,
        subject_id=subject_id,
        university=university,
        subject_code=subject_code
    )

def resolve_subject(query: str) -> SubjectModel | None:
    query_norm = query.lower().strip()
    if not query_norm:
        return None
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT subject_id, subject_name, university, subject_code, aliases FROM subjects")
    rows = cursor.fetchall()
    conn.close()
    
    for subject_id, subject_name, university, subject_code, aliases_str in rows:
        # Check direct matches
        if query_norm == subject_id.lower() or query_norm == subject_name.lower():
            return SubjectModel(
                subject_name=subject_name,
                subject_id=subject_id,
                university=university,
                subject_code=subject_code
            )
        
        # Check alias matches
        try:
            aliases = json.loads(aliases_str or "[]")
            if query_norm in aliases:
                return SubjectModel(
                    subject_name=subject_name,
                    subject_id=subject_id,
                    university=university,
                    subject_code=subject_code
                )
        except Exception:
            continue
            
    return None
