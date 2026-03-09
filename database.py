"""SQLite database and filesystem operations for Data Viewer projects."""

import shutil
import sqlite3
import re
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "dataviewer.db"
DATA_DIR = Path(__file__).parent / "data"


def _get_conn():
    return sqlite3.connect(DB_PATH)


def _slugify(name: str) -> str:
    """Derive slug from project name: lowercase, spaces to -, remove special chars."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "project"


def init_db():
    """Create tables if they do not exist."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def create_project(name: str) -> int:
    """Create a project, create data/<slug>/ dir, return project id."""
    init_db()
    slug = _slugify(name)
    created_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO projects (name, slug, created_at) VALUES (?, ?, ?)",
            (name.strip(), slug, created_at),
        )
        project_id = cursor.lastrowid
        conn.commit()

        project_dir = DATA_DIR / slug
        project_dir.mkdir(parents=True, exist_ok=True)

        return project_id
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError(f"Project with name '{name}' or slug '{slug}' already exists")
    finally:
        conn.close()


def list_projects() -> list[tuple[int, str, str]]:
    """Return list of (id, name, slug) for all projects."""
    init_db()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, name, slug FROM projects ORDER BY created_at ASC"
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_project(project_id: int) -> tuple[str, str] | None:
    """Return (name, slug) for project or None if not found."""
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT name, slug FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return row
    finally:
        conn.close()


def add_file(project_id: int, filename: str, data: bytes) -> int:
    """Save file to data/<slug>/<filename>. Overwrites existing file with same name."""
    init_db()
    project = get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    _, slug = project
    project_dir = DATA_DIR / slug
    project_dir.mkdir(parents=True, exist_ok=True)

    # Check for existing files with same base name (exact or timestamped variant)
    stem, suffix = Path(filename).stem, Path(filename).suffix
    pattern = f"{stem}_%{suffix}"  # e.g. OccupationDataSample_%.csv
    conn = _get_conn()
    try:
        existing_list = conn.execute(
            "SELECT id, file_path FROM files WHERE project_id = ? AND (filename = ? OR filename LIKE ?)",
            (project_id, filename, pattern),
        ).fetchall()

        file_path = f"data/{slug}/{filename}"
        full_path = DATA_DIR / slug / filename
        full_path.write_bytes(data)

        if existing_list:
            # Keep first record, update it; delete others and their files
            file_id, _ = existing_list[0]
            conn.execute(
                "UPDATE files SET filename = ?, file_path = ?, uploaded_at = ? WHERE id = ?",
                (filename, file_path, datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), file_id),
            )
            # Delete other matching records and remove their files from disk
            for fid, old_path in existing_list[1:]:
                conn.execute("DELETE FROM files WHERE id = ?", (fid,))
                old_full = Path(__file__).parent / old_path
                if old_full.exists():
                    old_full.unlink()
            # Remove old file for the kept record if path changed
            if existing_list[0][1] != file_path:
                old_full = Path(__file__).parent / existing_list[0][1]
                if old_full.exists():
                    old_full.unlink()
            conn.commit()
            return file_id
        else:
            cursor = conn.execute(
                "INSERT INTO files (project_id, filename, file_path, uploaded_at) VALUES (?, ?, ?, ?)",
                (project_id, filename, file_path, datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
            )
            file_id = cursor.lastrowid
            conn.commit()
            return file_id
    finally:
        conn.close()


def list_files(project_id: int) -> list[tuple[int, str, str]]:
    """Return list of (id, filename, file_path) for project files."""
    init_db()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, filename, file_path FROM files WHERE project_id = ? ORDER BY uploaded_at DESC",
            (project_id,),
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_file_path(file_id: int) -> str | None:
    """Return absolute file path for file id, or None."""
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT file_path FROM files WHERE id = ?", (file_id,)
        ).fetchone()
        if not row:
            return None
        return str(Path(__file__).parent / row[0])
    finally:
        conn.close()


def delete_project(project_id: int) -> None:
    """Delete a project, its file records, and its data directory."""
    init_db()
    project = get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    _, slug = project
    project_dir = DATA_DIR / slug

    conn = _get_conn()
    try:
        conn.execute("DELETE FROM files WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
    finally:
        conn.close()

    if project_dir.exists():
        shutil.rmtree(project_dir)
