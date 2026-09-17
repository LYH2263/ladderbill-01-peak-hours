import json
from datetime import datetime

import pytest

from app import seed
from app.db import connect
from app.modules.peak_hours import service
from app.modules.peak_hours.service import (
    NO_ENABLED_WINDOW,
    OUTSIDE_ALL_WINDOWS,
    PEAK_NOT_REQUESTED,
    PeakHoursError,
)
from app.services.billing_service import BillingService

seed.init_db()


@pytest.fixture()
def conn():
    c = connect()
    c.execute("DELETE FROM peak_windows")
    c.execute("DELETE FROM calc_runs")
    c.commit()
    yield c
    c.close()


def make(conn, **kw):
    payload = {"code": "晚高峰", "start": "18:00", "end": "22:00", "priority": 10}
    payload.update(kw)
    return service.create_window(conn, payload)


def test_create_window_roundtrip(conn):
    w = make(conn, note="晚间用电", cross_day=False)
    assert w["code"] == "晚高峰"
    assert w["start"] == "18:00" and w["end"] == "22:00"
    assert w["priority"] == 10 and w["enabled"] is True and w["note"] == "晚间用电"
    assert service.list_windows(conn)[0]["id"] == w["id"]


def test_non_cross_day_start_after_end_rejected(conn):
    with pytest.raises(PeakHoursError, match="开始时刻不得晚于结束时刻"):
        make(conn, start="20:00", end="18:00")


def test_bad_time_format_rejected(conn):
    with pytest.raises(PeakHoursError, match="HH:MM"):
        make(conn, start="25:00")


def test_conflict_names_both_codes(conn):
    make(conn, code="晚高峰", priority=10)
    with pytest.raises(PeakHoursError) as exc:
        make(conn, code="晚高峰二", start="19:00", end="23:00", priority=10)
    assert exc.value.status_code == 409
    assert "晚高峰" in exc.value.message and "晚高峰二" in exc.value.message


def test_overlap_with_different_priority_allowed(conn):
    make(conn, code="晚高峰", priority=10)
    w = make(conn, code="晚间加强", start="19:00", end="21:00", priority=20)
    assert w["enabled"] is True


def test_same_priority_without_overlap_allowed(conn):
    make(conn, code="晚高峰", priority=10)
    w = make(conn, code="午间", start="11:00", end="13:00", priority=10)
    assert w["id"]


def test_cross_day_conflict_detected(conn):
    make(conn, code="夜间", start="23:00", end="01:00", cross_day=True, priority=5)
    with pytest.raises(PeakHoursError, match="跨日子夜"):
        make(conn, code="跨日子夜", start="00:00", end="02:00", priority=5)


def test_update_reenable_conflict_checked(conn):
    make(conn, code="晚高峰", priority=10)
    b = make(conn, code="晚重叠", start="19:00", end="21:00", priority=10, enabled=False)
    service.update_window(conn, b["id"], {"priority": 20, "enabled": True})
    with pytest.raises(PeakHoursError, match="晚高峰"):
        service.update_window(conn, b["id"], {"priority": 10})


def test_disable_keeps_row(conn):
    w = make(conn)
    service.disable_window(conn, w["id"])
    rows = service.list_windows(conn)
    assert len(rows) == 1 and rows[0]["enabled"] is False


def test_match_anchor_cross_day(conn):
    make(conn, code="夜间", start="23:00", end="01:00", cross_day=True, priority=5)
    enabled = service.repository.list_enabled(conn)
    assert service.match_anchor(datetime(2026, 9, 17, 23, 30), enabled)["code"] == "夜间"
    assert service.match_anchor(datetime(2026, 9, 18, 0, 30), enabled)["code"] == "夜间"
    assert service.match_anchor(datetime(2026, 9, 17, 12, 0), enabled) is None


def test_match_anchor_prefers_higher_priority(conn):
    make(conn, code="晚高峰", priority=10)
    make(conn, code="晚间加强", start="19:00", end="21:00", priority=20)
    enabled = service.repository.list_enabled(conn)
    hit = service.match_anchor(datetime(2026, 9, 17, 19, 30), enabled)
    assert hit["code"] == "晚间加强"
    hit = service.match_anchor(datetime(2026, 9, 17, 21, 30), enabled)
    assert hit["code"] == "晚高峰"


def test_bill_hit_applies_settings_factor(conn):
    make(conn)
    with BillingService(conn) as svc:
        r = svc.run_bill(400, True, None, True, datetime(2026, 9, 17, 19, 30))
    assert r["peak_factor"] == 1.2
    assert r["total"] == 309.60
    assert r["peak"]["matched"] is True
    assert r["peak"]["window_code"] == "晚高峰"
    assert r["peak"]["factor"] == 1.2
    assert r["peak"]["factor_source"] == "settings.peak_factor"
    assert r["peak"]["miss_reason"] is None
    assert r["run_id"]


def test_bill_miss_outside_windows(conn):
    make(conn)
    with BillingService(conn) as svc:
        r = svc.run_bill(400, True, None, True, datetime(2026, 9, 17, 12, 0))
    assert r["peak_factor"] == 1.0
    assert r["total"] == 258.00
    assert r["peak"]["matched"] is False
    assert r["peak"]["miss_reason"] == OUTSIDE_ALL_WINDOWS
    assert r["peak"]["window_code"] is None


def test_bill_miss_when_no_enabled_windows(conn):
    make(conn, enabled=False)
    with BillingService(conn) as svc:
        r = svc.run_bill(400, True, None, True, datetime(2026, 9, 17, 19, 30))
    assert r["peak"]["miss_reason"] == NO_ENABLED_WINDOW
    assert r["peak_factor"] == 1.0


def test_bill_without_peak_matches_legacy_behavior(conn):
    make(conn)
    with BillingService(conn) as svc:
        r = svc.run_bill(400, False, None, True, datetime(2026, 9, 17, 19, 30))
    assert r["peak_factor"] == 1.0
    assert r["total"] == 258.00
    assert r["peak"]["miss_reason"] == PEAK_NOT_REQUESTED


def test_trial_run_writes_no_bill_record(conn):
    make(conn)
    with BillingService(conn) as svc:
        r = svc.run_bill(400, True, None, False, datetime(2026, 9, 17, 19, 30))
        assert r["run_id"] is None
        assert svc.list_history(100) == []
        svc.run_bill(400, True, None, True, datetime(2026, 9, 17, 19, 30))
        runs = svc.list_history(100)
    assert len(runs) == 1 and runs[0]["kind"] == "bill"


def test_history_snapshot_pins_factor_after_window_change(conn):
    w = make(conn)
    with BillingService(conn) as svc:
        r = svc.run_bill(400, True, None, True, datetime(2026, 9, 17, 19, 30))
        service.disable_window(conn, w["id"])
        service.update_window(conn, w["id"], {"priority": 99, "note": "已停用"})
        run = svc.get_run(r["run_id"])
    peak = json.loads(run["result_json"])["peak"]
    assert peak["matched"] is True
    assert peak["factor"] == 1.2
    assert peak["window"]["code"] == "晚高峰"
    assert peak["window"]["start"] == "18:00" and peak["window"]["end"] == "22:00"
    assert peak["window"]["priority"] == 10
