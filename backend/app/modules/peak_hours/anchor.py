"""账期锚定日解析：把前端传入的日期/时间字符串折算为当天分钟数。"""

from __future__ import annotations

from datetime import datetime


def anchor_minute(anchor: str) -> int:
    """支持 ``YYYY-MM-DD`` 与 ``YYYY-MM-DDTHH:MM[:SS]`` 两种形式。

    只给日期时锚定到 00:00；结果夹在 [0, 1439]。
    """
    text = anchor.strip()
    try:
        if len(text) == 10:
            datetime.strptime(text, "%Y-%m-%d")
            return 0
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("账期锚定日格式应为 YYYY-MM-DD 或 YYYY-MM-DDTHH:MM") from exc
    return parsed.hour * 60 + parsed.minute


def anchor_label(anchor: str) -> str:
    """供快照阅读的规范化标签。"""
    minute = anchor_minute(anchor)
    hh, mm = divmod(minute, 60)
    date_part = anchor.strip()[:10]
    return f"{date_part} {hh:02d}:{mm:02d}" if len(anchor.strip()) > 10 else date_part
