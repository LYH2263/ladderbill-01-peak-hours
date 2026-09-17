"""尖峰时段表的持久化访问。"""

import sqlite3
from datetime import datetime, timezone

from app.modules.peak_hours.matcher import Window

_FIELDS = "id, code, start_time, end_time, cross_day, priority, enabled, note, created_at, updated_at"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_window(row: sqlite3.Row) -> Window:
    return Window(
        id=row["id"],
        code=row["code"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        cross_day=bool(row["cross_day"]),
        priority=row["priority"],
        enabled=bool(row["enabled"]),
        note=row["note"],
    )


def list_all(conn: sqlite3.Connection, enabled_only: bool = False) -> list[dict]:
    sql = f"SELECT {_FIELDS} FROM peak_windows"
    if enabled_only:
        sql += " WHERE enabled=1"
    sql += " ORDER BY priority ASC, id ASC"
    rows = conn.execute(sql).fetchall()
    return [_decode(r) for r in rows]


def list_enabled_windows(conn: sqlite3.Connection) -> list[Window]:
    rows = conn.execute(
        f"SELECT {_FIELDS} FROM peak_windows WHERE enabled=1 ORDER BY priority ASC, id ASC"
    ).fetchall()
    return [_row_to_window(r) for r in rows]


def get(conn: sqlite3.Connection, window_id: int) -> dict | None:
    row = conn.execute(f"SELECT {_FIELDS} FROM peak_windows WHERE id=?", (window_id,)).fetchone()
    return _decode(row) if row else None


def get_by_code(conn: sqlite3.Connection, code: str, exclude_id: int | None = None) -> dict | None:
    if exclude_id is None:
        row = conn.execute("SELECT id FROM peak_windows WHERE code=?", (code,)).fetchone()
    else:
        row = conn.execute(
            "SELECT id FROM peak_windows WHERE code=? AND id<>?", (code, exclude_id)
        ).fetchone()
    return dict(row) if row else None


def insert(
    conn: sqlite3.Connection,
    *,
    code: str,
    start_time: str,
    end_time: str,
    cross_day: bool,
    priority: int,
    enabled: bool,
    note: str | None,
) -> int:
    now = _now()
    cur = conn.execute(
        """
        INSERT INTO peak_windows(code, start_time, end_time, cross_day, priority, enabled, note, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (code, start_time, end_time, int(cross_day), priority, int(enabled), note, now, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def update(conn: sqlite3.Connection, window_id: int, fields: dict) -> None:
    allowed = {"code", "start_time", "end_time", "cross_day", "priority", "enabled", "note"}
    sets, params = [], []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key in ("cross_day", "enabled"):
            value = int(bool(value))
        sets.append(f"{key}=?")
        params.append(value)
    sets.append("updated_at=?")
    params.append(_now())
    params.append(window_id)
    conn.execute(f"UPDATE peak_windows SET {', '.join(sets)} WHERE id=?", params)
    conn.commit()


def set_enabled(conn: sqlite3.Connection, window_id: int, enabled: bool) -> None:
    conn.execute(
        "UPDATE peak_windows SET enabled=?, updated_at=? WHERE id=?",
        (int(enabled), _now(), window_id),
    )
    conn.commit()


def _decode(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["cross_day"] = bool(d["cross_day"])
    d["enabled"] = bool(d["enabled"])
    return d
