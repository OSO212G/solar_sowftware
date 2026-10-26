"""SQLite persistence for projects."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

from suria.domain.simulation_input import SimulationInput

DB_PATH = Path("projects.db")


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT,
            data TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_project(data: dict, project_id: int = None) -> int:
    """Save or update a project. If project_id is provided, UPDATE that row.
    Otherwise, check for existing project with same name and UPDATE, or INSERT new."""
    SimulationInput.model_validate(data)
    init_db()
    conn = _get_conn()
    now = datetime.now().isoformat()

    if project_id:
        conn.execute(
            "UPDATE projects SET name = ?, updated_at = ?, data = ? WHERE id = ?",
            (data["name"], now, json.dumps(data), project_id),
        )
        conn.commit()
        conn.close()
        return project_id

    # Check for existing project with same name
    row = conn.execute("SELECT id FROM projects WHERE name = ?", (data["name"],)).fetchone()
    if row:
        conn.execute(
            "UPDATE projects SET updated_at = ?, data = ? WHERE id = ?",
            (now, json.dumps(data), row["id"]),
        )
        conn.commit()
        conn.close()
        return row["id"]

    conn.execute(
        "INSERT INTO projects (name, created_at, updated_at, data) VALUES (?, ?, ?, ?)",
        (data["name"], now, now, json.dumps(data)),
    )
    proj_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return proj_id


def list_projects():
    init_db()
    conn = _get_conn()
    rows = conn.execute("SELECT id, name, created_at FROM projects ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_project(proj_id: int) -> dict:
    init_db()
    conn = _get_conn()
    row = conn.execute("SELECT data FROM projects WHERE id = ?", (proj_id,)).fetchone()
    conn.close()
    if row:
        return json.loads(row["data"])
    return {}


def delete_project(proj_id: int):
    init_db()
    conn = _get_conn()
    conn.execute("DELETE FROM projects WHERE id = ?", (proj_id,))
    conn.commit()
    conn.close()
