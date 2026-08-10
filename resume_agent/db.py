import json
import sqlite3
from pathlib import Path

from models import ResumeBullet

DB_PATH = Path(__file__).parent / "data" / "master_resume.db"
ORIGINAL_DOCX_PATH = Path(__file__).parent / "data" / "master_resume_original.docx"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bullets (
    id TEXT PRIMARY KEY,
    employer TEXT NOT NULL,
    role TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    text TEXT NOT NULL,
    skills TEXT NOT NULL,
    seniority_signal TEXT,
    quantified_outcome TEXT,
    embedding TEXT,
    source_paragraph_index INTEGER
)
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(bullets)")}
    if "source_paragraph_index" not in existing_columns:
        conn.execute("ALTER TABLE bullets ADD COLUMN source_paragraph_index INTEGER")
    return conn


def _row_to_bullet(row: tuple) -> ResumeBullet:
    (id_, employer, role, start_date, end_date, text, skills,
     seniority_signal, quantified_outcome, embedding, source_paragraph_index) = row
    return ResumeBullet(
        id=id_,
        employer=employer,
        role=role,
        start_date=start_date,
        end_date=end_date,
        text=text,
        skills=json.loads(skills),
        seniority_signal=seniority_signal,
        quantified_outcome=quantified_outcome,
        embedding=json.loads(embedding) if embedding is not None else None,
        source_paragraph_index=source_paragraph_index,
    )


def save_bullets(bullets: list[ResumeBullet], replace_all: bool = True, db_path: Path = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        if replace_all:
            conn.execute("DELETE FROM bullets")
        conn.executemany(
            """
            INSERT OR REPLACE INTO bullets
                (id, employer, role, start_date, end_date, text, skills,
                 seniority_signal, quantified_outcome, embedding, source_paragraph_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    b.id, b.employer, b.role, b.start_date, b.end_date, b.text,
                    json.dumps(b.skills), b.seniority_signal, b.quantified_outcome,
                    json.dumps(b.embedding) if b.embedding is not None else None,
                    b.source_paragraph_index,
                )
                for b in bullets
            ],
        )
        conn.commit()
    finally:
        conn.close()


def load_bullets(db_path: Path = DB_PATH) -> list[ResumeBullet]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT id, employer, role, start_date, end_date, text, skills,
                   seniority_signal, quantified_outcome, embedding, source_paragraph_index
            FROM bullets
            """
        ).fetchall()
        return [_row_to_bullet(row) for row in rows]
    finally:
        conn.close()


def get_bullets_by_ids(ids: list[str], db_path: Path = DB_PATH) -> list[ResumeBullet]:
    if not ids:
        return []
    conn = get_connection(db_path)
    try:
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"""
            SELECT id, employer, role, start_date, end_date, text, skills,
                   seniority_signal, quantified_outcome, embedding, source_paragraph_index
            FROM bullets
            WHERE id IN ({placeholders})
            """,
            ids,
        ).fetchall()
        return [_row_to_bullet(row) for row in rows]
    finally:
        conn.close()


def save_original_docx(source_path: Path, db_path: Path = DB_PATH) -> Path:
    """Copies the uploaded master resume docx so docx_export.py can later edit
    its actual paragraphs in place, preserving the original formatting/layout."""
    dest = db_path.parent / ORIGINAL_DOCX_PATH.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(source_path.read_bytes())
    return dest


def load_original_docx_path(db_path: Path = DB_PATH) -> Path | None:
    dest = db_path.parent / ORIGINAL_DOCX_PATH.name
    return dest if dest.exists() else None
