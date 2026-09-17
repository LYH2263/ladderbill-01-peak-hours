"""尖峰时段（peak hours）模块。

负责维护多条可启用的尖峰时段，并根据账期锚定日的时刻判断是否命中。

时段用每天的开始/结束时刻（``HH:MM``）描述：
- 不跨日（``cross_day=False``）：窗口为 [start, end)，且要求 start <= end；
- 跨日（``cross_day=True``）：窗口为 [start, 24:00) ∪ [00:00, end)。

同一时刻最多只能被一个启用时段命中；当两个启用时段在同一优先级发生
时间重叠时，视为配置冲突，错误信息会点名冲突的两条时段标识（code）。
"""

from app.modules.peak_hours.matcher import (
    MISS_REASONS,
    REASON_DISABLED,
    REASON_HIT,
    REASON_OUTSIDE_WINDOWS,
    PeakWindowConflict,
    Window,
    check_no_conflict,
    evaluate,
)

__all__ = [
    "MISS_REASONS",
    "REASON_DISABLED",
    "REASON_HIT",
    "REASON_OUTSIDE_WINDOWS",
    "PeakWindowConflict",
    "Window",
    "check_no_conflict",
    "evaluate",
]
