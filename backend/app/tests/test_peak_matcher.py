import pytest

from app.modules.peak_hours.matcher import (
    REASON_DISABLED,
    REASON_HIT,
    REASON_OUTSIDE_WINDOWS,
    PeakWindowConflict,
    Window,
    check_no_conflict,
    evaluate,
    validate_fields,
)


def w(code, start, end, cross=False, prio=10, enabled=True, wid=1):
    return Window(
        id=wid, code=code, start_time=start, end_time=end,
        cross_day=cross, priority=prio, enabled=enabled,
    )


def test_same_day_window_bounds_are_half_open():
    win = w("EVENING", "18:00", "22:00")
    assert win.contains(18 * 60)          # 左闭
    assert win.contains(22 * 60 - 1)
    assert not win.contains(22 * 60)      # 右开
    assert not win.contains(17 * 60 + 59)


def test_cross_day_window_covers_midnight():
    win = w("NIGHT", "22:00", "06:00", cross=True)
    assert win.contains(23 * 60)
    assert win.contains(0)
    assert win.contains(6 * 60 - 1)
    assert not win.contains(6 * 60)
    assert not win.contains(21 * 60 + 59)


def test_non_cross_day_start_after_end_rejected():
    with pytest.raises(ValueError):
        validate_fields("BAD", "18:00", "09:00", False)


def test_cross_day_start_after_end_allowed():
    validate_fields("NIGHT", "22:00", "06:00", True)  # 不抛异常即可


def test_evaluate_highest_priority_wins():
    windows = [
        w("EVENING", "18:00", "22:00", prio=20, wid=1),
        w("STRICT", "19:00", "20:00", prio=10, wid=2),  # 数值更小 → 优先
    ]
    r = evaluate(windows, 19 * 60 + 30)
    assert r["reason"] == REASON_HIT
    assert r["window_code"] == "STRICT"


def test_evaluate_outside_returns_enum_reason():
    r = evaluate([w("EVENING", "18:00", "22:00")], 12 * 60)
    assert r["reason"] == REASON_OUTSIDE_WINDOWS
    assert r["window_code"] is None


def test_evaluate_all_disabled():
    r = evaluate([w("EVENING", "18:00", "22:00", enabled=False)], 19 * 60)
    assert r["reason"] == REASON_DISABLED


def test_same_priority_overlap_conflict_names_both_codes():
    windows = [
        w("EVENING", "18:00", "22:00", prio=10, wid=1),
        w("OTHER", "21:00", "23:00", prio=10, wid=2),
    ]
    with pytest.raises(PeakWindowConflict) as ei:
        check_no_conflict(windows)
    assert "EVENING" in str(ei.value)
    assert "OTHER" in str(ei.value)


def test_different_priority_overlap_is_allowed():
    windows = [
        w("EVENING", "18:00", "22:00", prio=10, wid=1),
        w("OTHER", "21:00", "23:00", prio=20, wid=2),
    ]
    check_no_conflict(windows)  # 不抛异常


def test_cross_day_same_priority_overlap_detected():
    windows = [
        w("NIGHT", "22:00", "06:00", cross=True, prio=10, wid=1),
        w("DAWN", "05:00", "07:00", prio=10, wid=2),
    ]
    with pytest.raises(PeakWindowConflict) as ei:
        check_no_conflict(windows)
    assert {"NIGHT", "DAWN"} == {ei.value.code_a, ei.value.code_b}


def test_disabled_window_does_not_conflict():
    windows = [
        w("EVENING", "18:00", "22:00", prio=10, wid=1),
        w("OTHER", "21:00", "23:00", prio=10, enabled=False, wid=2),
    ]
    check_no_conflict(windows)
