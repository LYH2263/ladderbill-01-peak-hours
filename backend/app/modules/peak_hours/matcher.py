"""尖峰时段的领域逻辑：时刻命中、优先级与重叠冲突校验。

该模块不依赖数据库，``Window`` 只描述时段本身，仓储层负责与表行互转。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MINUTES_PER_DAY = 24 * 60

REASON_HIT = "hit"
REASON_OUTSIDE_WINDOWS = "outside_windows"
REASON_DISABLED = "disabled"

#: 未命中原因枚举（hit 之外的全部取值）
MISS_REASONS = [REASON_OUTSIDE_WINDOWS, REASON_DISABLED]

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass(frozen=True)
class Window:
    id: int | None
    code: str
    start_time: str
    end_time: str
    cross_day: bool
    priority: int
    enabled: bool
    note: str | None = None

    def intervals(self) -> list[tuple[int, int]]:
        """返回窗口在一天 [0, 1440) 内覆盖的半开区间 [start, end)。"""
        start = parse_time(self.start_time)
        end = parse_time(self.end_time)
        if self.cross_day:
            spans = []
            if start < MINUTES_PER_DAY:
                spans.append((start, MINUTES_PER_DAY))
            if end > 0:
                spans.append((0, end))
            return spans
        if start < end:
            return [(start, end)]
        return []

    def contains(self, minute: int) -> bool:
        return any(s <= minute < e for s, e in self.intervals())


class PeakWindowConflict(ValueError):
    """同优先级的两个启用时段时间重叠。"""

    def __init__(self, priority: int, code_a: str, code_b: str):
        self.priority = priority
        self.code_a = code_a
        self.code_b = code_b
        super().__init__(
            f"启用时段冲突：优先级 {priority} 上“{code_a}”与“{code_b}”时间重叠，"
            "请错开时间或调整优先级"
        )


def parse_time(value: str) -> int:
    """``HH:MM`` → 当天分钟数。"""
    if not isinstance(value, str) or not _TIME_RE.match(value):
        raise ValueError(f"时刻格式应为 HH:MM（00:00–23:59），收到：{value!r}")
    hour, minute = (int(x) for x in value.split(":"))
    return hour * 60 + minute


def validate_fields(code: str, start_time: str, end_time: str, cross_day: bool) -> None:
    """跨表通用的字段语义校验。"""
    code = (code or "").strip()
    if not code:
        raise ValueError("时段标识不能为空")
    start = parse_time(start_time)
    end = parse_time(end_time)
    if not cross_day and start > end:
        raise ValueError(
            f"非跨日时段的开始时刻（{start_time}）不得晚于结束时刻（{end_time}），"
            "跨夜时段请勾选跨日"
        )


def _intervals_overlap(a: Window, b: Window) -> bool:
    for sa, ea in a.intervals():
        for sb, eb in b.intervals():
            if sa < eb and sb < ea:
                return True
    return False


def find_conflict(windows: list[Window]) -> tuple[int, str, str] | None:
    enabled = [w for w in windows if w.enabled]
    for i, a in enumerate(enabled):
        for b in enabled[i + 1 :]:
            if a.priority == b.priority and _intervals_overlap(a, b):
                return a.priority, a.code, b.code
    return None


def check_no_conflict(windows: list[Window]) -> None:
    found = find_conflict(windows)
    if found:
        raise PeakWindowConflict(*found)


def evaluate(windows: list[Window], minute: int) -> dict:
    """判断一天中的某分钟是否命中启用时段。

    多个启用时段同时覆盖该时刻时，优先级数值最小的胜出；
    同优先级重叠属于配置冲突，调用方应先用 :func:`check_no_conflict` 拦截。

    返回 ``window_code``/``window_id``/``priority`` 与原因枚举：
    ``hit`` / ``outside_windows`` / ``disabled``。
    """
    enabled = [w for w in windows if w.enabled]
    if not enabled:
        return {
            "hit": False,
            "reason": REASON_DISABLED,
            "window_code": None,
            "window_id": None,
            "priority": None,
        }
    candidates = sorted(
        (w for w in enabled if w.contains(minute)),
        key=lambda w: (w.priority, w.id if w.id is not None else 0),
    )
    if not candidates:
        return {
            "hit": False,
            "reason": REASON_OUTSIDE_WINDOWS,
            "window_code": None,
            "window_id": None,
            "priority": None,
        }
    w = candidates[0]
    return {
        "hit": True,
        "reason": REASON_HIT,
        "window_code": w.code,
        "window_id": w.id,
        "priority": w.priority,
    }
