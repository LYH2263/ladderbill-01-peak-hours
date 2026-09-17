"""Persistence for peak_hours: the peak_windows table.

Times are stored as minutes since midnight (0..1439) so overlap and
matching stay simple integer comparisons; the API layer speaks "HH:MM".
"""

import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS peak_windows(
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    start_min INTEGER NOT NULL,
    end_min INTEGER NOT NULL,
    cross_day INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    note TEXT,
    created_at TEXT,
    updated_at TEXT
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["cross_day"] = bool(d["cross_day"])
    d["enabled"] = bool(d["enabled"])
    return d


def list_all(conn: sqlite3.Connection) -> list[dict]:
    q = """
    SELECT id, code, start_min, end_min, cross_day, priority, enabled, note, created_at, updated_at
    FROM peak_windows
    ORDER BY enabled DESC, priority DESC, code
    """
    return [_row_to_dict(r) for r in conn.execute(q).fetchall()]


def list_enabled(conn: sqlite3.Connection) -> list[dict]:
    q = """
    SELECT id, code, start_min, end_min, cross_day, priority, enabled, note, created_at, updated_at
    FROM peak_windows WHERE enabled=1
    ORDER BY priority DESC, code
    """
    return [_row_to_dict(r) for r in conn.execute(q).fetchall()]


def get(conn: sqlite3.Connection, window_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM peak_windows WHERE id=?", (window_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_by_code(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute("SELECT * FROM peak_windows WHERE code=?", (code,)).fetchone()
    return _row_to_dict(row) if row else None


def insert(conn: sqlite3.Connection, fields: dict) -> int:
    now = _now()
    cur = conn.execute(
        """
        INSERT INTO peak_windows(code, start_min, end_min, cross_day, priority, enabled, note, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            fields["code"],
            fields["start_min"],
            fields["end_min"],
            int(fields["cross_day"]),
            fields["priority"],
            int(fields["enabled"]),
            fields.get("note"),
            now,
            now,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def update(conn: sqlite3.Connection, window_id: int, fields: dict) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE peak_windows SET {cols}, updated_at=? WHERE id=?",
        (*fields.values(), _now(), window_id),
    )
    conn.commit()
