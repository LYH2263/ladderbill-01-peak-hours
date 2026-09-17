"""尖峰时段维护服务：字段校验、唯一性与同优先级重叠冲突检查。

冲突采用“写入前预校验”：先在内存中构造变更后的启用时段集合做检查，
通过后才落库，避免写入互相冲突的启用配置。
"""

from __future__ import annotations

from app.db import connect
from app.modules.peak_hours import repository as peak_repo
from app.modules.peak_hours.matcher import (
    Window,
    check_no_conflict,
    validate_fields,
)


class PeakHoursService:
    def __init__(self):
        self._conn = connect()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def list_windows(self, enabled_only: bool = False) -> list[dict]:
        return peak_repo.list_all(self._conn, enabled_only=enabled_only)

    def get_window(self, window_id: int) -> dict | None:
        return peak_repo.get(self._conn, window_id)

    def create_window(self, data: dict) -> dict:
        validate_fields(data["code"], data["start_time"], data["end_time"], data["cross_day"])
        self._require_unique_code(data["code"], None)
        prospective = [self._to_window(r) for r in peak_repo.list_all(self._conn)] + [
            Window(
                id=None,
                code=data["code"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                cross_day=data["cross_day"],
                priority=data["priority"],
                enabled=data["enabled"],
                note=data["note"],
            )
        ]
        check_no_conflict(prospective)
        window_id = peak_repo.insert(self._conn, **data)
        return peak_repo.get(self._conn, window_id)

    def update_window(self, window_id: int, changes: dict) -> dict:
        current = peak_repo.get(self._conn, window_id)
        if not current:
            raise KeyError(window_id)
        merged = {**current, **changes}
        validate_fields(
            merged["code"], merged["start_time"], merged["end_time"], merged["cross_day"]
        )
        if changes.get("code"):
            self._require_unique_code(changes["code"], window_id)
        prospective = [
            self._to_window(merged if r["id"] == window_id else r)
            for r in peak_repo.list_all(self._conn)
        ]
        check_no_conflict(prospective)
        peak_repo.update(self._conn, window_id, changes)
        return peak_repo.get(self._conn, window_id)

    def disable_window(self, window_id: int) -> dict:
        current = peak_repo.get(self._conn, window_id)
        if not current:
            raise KeyError(window_id)
        peak_repo.set_enabled(self._conn, window_id, False)
        return peak_repo.get(self._conn, window_id)

    # --- 内部 ---

    def _require_unique_code(self, code: str, exclude_id: int | None) -> None:
        if peak_repo.get_by_code(self._conn, code, exclude_id):
            raise ValueError(f"时段标识“{code}”已存在，标识必须唯一")

    @staticmethod
    def _to_window(r: dict) -> Window:
        return Window(
            id=r["id"],
            code=r["code"],
            start_time=r["start_time"],
            end_time=r["end_time"],
            cross_day=r["cross_day"],
            priority=r["priority"],
            enabled=r["enabled"],
            note=r["note"],
        )
