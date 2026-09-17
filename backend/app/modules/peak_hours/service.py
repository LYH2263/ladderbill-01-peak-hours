"""Peak-window domain logic: validation, conflict detection, anchor matching.

A window covers a set of minutes within a day. Non-cross-day windows are the
half-open interval [start, end); cross-day windows wrap past midnight, i.e.
[start, 1440) U [0, end). Two ENABLED windows conflict when their minute sets
overlap while their priorities are equal — the matcher would have no way to
pick a winner, so the write is rejected naming both window codes.
"""

import re
import sqlite3
from datetime import datetime

from app.modules.peak_hours import repository

# Miss-reason enum returned by the billing path when the peak factor is NOT applied.
PEAK_NOT_REQUESTED = "PEAK_NOT_REQUESTED"  # 未勾选尖峰
NO_ENABLED_WINDOW = "NO_ENABLED_WINDOW"  # 当前没有任何启用时段
OUTSIDE_ALL_WINDOWS = "OUTSIDE_ALL_WINDOWS"  # 锚定时刻不在任何启用时段内

_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MINUTES_PER_DAY = 24 * 60


class PeakHoursError(Exception):
    """Readable domain error; the router maps it to an HTTP response."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def parse_hhmm(value: str, field: str) -> int:
    if not isinstance(value, str) or not _HHMM.match(value.strip()):
        raise PeakHoursError(f"{field} 须为 HH:MM 格式（00:00–23:59），收到：{value!r}")
    hh, mm = value.strip().split(":")
    return int(hh) * 60 + int(mm)


def fmt_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def window_segments(start_min: int, end_min: int, cross_day: bool) -> list[tuple[int, int]]:
    """Half-open [start, end) minute segments within one day."""
    if cross_day:
        segs = []
        if start_min < MINUTES_PER_DAY:
            segs.append((start_min, MINUTES_PER_DAY))
        if end_min > 0:
            segs.append((0, end_min))
        return segs
    if end_min <= start_min:
        return []
    return [(start_min, end_min)]


def windows_overlap(a: dict, b: dict) -> bool:
    for sa, ea in window_segments(a["start_min"], a["end_min"], bool(a["cross_day"])):
        for sb, eb in window_segments(b["start_min"], b["end_min"], bool(b["cross_day"])):
            if sa < eb and sb < ea:
                return True
    return False


def matches_minute(window: dict, minute: int) -> bool:
    return any(s <= minute < e for s, e in window_segments(window["start_min"], window["end_min"], bool(window["cross_day"])))


def match_anchor(anchor: datetime, enabled_windows: list[dict]) -> dict | None:
    """Highest-priority enabled window covering the anchor's wall-clock minute."""
    minute = anchor.hour * 60 + anchor.minute
    hits = [w for w in enabled_windows if matches_minute(w, minute)]
    if not hits:
        return None
    return max(hits, key=lambda w: (w["priority"], w["code"]))


def snapshot(window: dict) -> dict:
    """Pinned copy stored in run records so history survives later edits/disables."""
    return {
        "id": window["id"],
        "code": window["code"],
        "start": fmt_hhmm(window["start_min"]),
        "end": fmt_hhmm(window["end_min"]),
        "cross_day": bool(window["cross_day"]),
        "priority": window["priority"],
        "note": window.get("note"),
    }


def _validate_times(start_min: int, end_min: int, cross_day: bool) -> None:
    if not cross_day and start_min > end_min:
        raise PeakHoursError(
            f"未跨日时段的开始时刻不得晚于结束时刻（{fmt_hhmm(start_min)} > {fmt_hhmm(end_min)}）"
        )


def _check_conflicts(conn: sqlite3.Connection, candidate: dict, exclude_id: int | None = None) -> None:
    """Enabled windows may not overlap another enabled window of equal priority."""
    if not candidate["enabled"]:
        return
    for other in repository.list_enabled(conn):
        if exclude_id is not None and other["id"] == exclude_id:
            continue
        if other["priority"] == candidate["priority"] and windows_overlap(other, candidate):
            raise PeakHoursError(
                "启用时段冲突：时段「{a}」与「{b}」优先级相同（{p}）且时间重叠，"
                "请调整优先级或时段范围".format(a=candidate["code"], b=other["code"], p=candidate["priority"]),
                status_code=409,
            )


def list_windows(conn: sqlite3.Connection) -> list[dict]:
    return [to_api(w) for w in repository.list_all(conn)]


def create_window(conn: sqlite3.Connection, payload: dict) -> dict:
    code = (payload.get("code") or "").strip()
    if not code:
        raise PeakHoursError("时段标识不能为空")
    if repository.get_by_code(conn, code):
        raise PeakHoursError(f"时段标识「{code}」已存在", status_code=409)
    fields = {
        "code": code,
        "start_min": parse_hhmm(payload.get("start"), "开始时刻"),
        "end_min": parse_hhmm(payload.get("end"), "结束时刻"),
        "cross_day": bool(payload.get("cross_day", False)),
        "priority": int(payload.get("priority", 0)),
        "enabled": bool(payload.get("enabled", True)),
        "note": (payload.get("note") or None),
    }
    _validate_times(fields["start_min"], fields["end_min"], fields["cross_day"])
    _check_conflicts(conn, fields)
    window_id = repository.insert(conn, fields)
    return to_api(repository.get(conn, window_id))


def update_window(conn: sqlite3.Connection, window_id: int, payload: dict) -> dict:
    current = repository.get(conn, window_id)
    if not current:
        raise PeakHoursError(f"时段 #{window_id} 不存在", status_code=404)
    merged = {
        "code": current["code"],
        "start_min": current["start_min"],
        "end_min": current["end_min"],
        "cross_day": current["cross_day"],
        "priority": current["priority"],
        "enabled": current["enabled"],
        "note": current.get("note"),
    }
    if "code" in payload and payload["code"] is not None:
        code = str(payload["code"]).strip()
        if not code:
            raise PeakHoursError("时段标识不能为空")
        clash = repository.get_by_code(conn, code)
        if clash and clash["id"] != window_id:
            raise PeakHoursError(f"时段标识「{code}」已存在", status_code=409)
        merged["code"] = code
    if "start" in payload and payload["start"] is not None:
        merged["start_min"] = parse_hhmm(payload["start"], "开始时刻")
    if "end" in payload and payload["end"] is not None:
        merged["end_min"] = parse_hhmm(payload["end"], "结束时刻")
    if "cross_day" in payload and payload["cross_day"] is not None:
        merged["cross_day"] = bool(payload["cross_day"])
    if "priority" in payload and payload["priority"] is not None:
        merged["priority"] = int(payload["priority"])
    if "enabled" in payload and payload["enabled"] is not None:
        merged["enabled"] = bool(payload["enabled"])
    if "note" in payload:
        merged["note"] = payload["note"] or None
    _validate_times(merged["start_min"], merged["end_min"], merged["cross_day"])
    _check_conflicts(conn, merged, exclude_id=window_id)
    repository.update(conn, window_id, merged)
    return to_api(repository.get(conn, window_id))


def disable_window(conn: sqlite3.Connection, window_id: int) -> dict:
    """Soft disable: the row stays so historical run snapshots remain traceable."""
    current = repository.get(conn, window_id)
    if not current:
        raise PeakHoursError(f"时段 #{window_id} 不存在", status_code=404)
    repository.update(conn, window_id, {"enabled": 0})
    return to_api(repository.get(conn, window_id))


def resolve_peak(conn: sqlite3.Connection, peak_requested: bool, anchor: datetime, peak_factor: float) -> dict:
    """Decide the factor for a bill run and explain the decision.

    Returns the factor to apply plus the matched-window snapshot (pinned for
    history) or a miss-reason enum when peak_factor must not be applied.
    """
    base = {
        "requested": bool(peak_requested),
        "matched": False,
        "factor": 1.0,
        "factor_source": "none",
        "window_code": None,
        "window": None,
    }
    if not peak_requested:
        return {**base, "miss_reason": PEAK_NOT_REQUESTED}
    enabled = repository.list_enabled(conn)
    if not enabled:
        return {**base, "miss_reason": NO_ENABLED_WINDOW}
    hit = match_anchor(anchor, enabled)
    if not hit:
        return {**base, "miss_reason": OUTSIDE_ALL_WINDOWS}
    return {
        **base,
        "matched": True,
        "factor": float(peak_factor),
        "factor_source": "settings.peak_factor",
        "miss_reason": None,
        "window_code": hit["code"],
        "window": snapshot(hit),
    }


def to_api(row: dict) -> dict:
    return {
        "id": row["id"],
        "code": row["code"],
        "start": fmt_hhmm(row["start_min"]),
        "end": fmt_hhmm(row["end_min"]),
        "cross_day": bool(row["cross_day"]),
        "priority": row["priority"],
        "enabled": bool(row["enabled"]),
        "note": row.get("note"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
