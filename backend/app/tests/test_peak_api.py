"""端到端：时段维护接口 + 计费命中/快照/试算不落库。

依赖种子数据：EVENING_PEAK 18:00–22:00（启用，优先级10）、
NIGHT_PEAK 22:00–06:00 跨日（启用，优先级20）、MIDDAY_PEAK 停用。
"""


def test_seed_windows_listed(client):
    items = client.get("/api/peak-windows").json()["items"]
    codes = {w["code"] for w in items}
    assert {"EVENING_PEAK", "NIGHT_PEAK", "MIDDAY_PEAK"} <= codes


def test_create_window_and_hit(client):
    body = {
        "code": "MORNING_TEST",
        "start_time": "07:00",
        "end_time": "09:00",
        "cross_day": False,
        "priority": 40,
        "enabled": True,
        "note": "早尖峰",
    }
    r = client.post("/api/peak-windows", json=body)
    assert r.status_code == 201, r.text
    wid = r.json()["id"]

    bill = client.post(
        "/api/bill",
        json={"kwh": 120, "peak": True, "persist": False, "anchor_date": "2026-09-17T08:00"},
    ).json()
    assert bill["peak_hit"] is True
    assert bill["window_code"] == "MORNING_TEST"
    assert bill["factor"] == 1.2
    assert bill["factor_source"] == "settings.peak_factor"
    assert bill["run_id"] is None

    # 清理
    assert client.post(f"/api/peak-windows/{wid}/disable").status_code == 200


def test_bill_miss_outside_windows(client):
    r = client.post(
        "/api/bill",
        json={"kwh": 120, "peak": True, "persist": False, "anchor_date": "2026-09-17T12:30"},
    )
    body = r.json()
    assert body["peak_hit"] is False
    assert body["miss_reason"] == "outside_windows"
    assert body["factor"] == 1.0
    assert body["factor_source"] == "default_1.0"


def test_cross_day_hit_after_midnight(client):
    body = client.post(
        "/api/bill",
        json={"kwh": 200, "peak": True, "persist": False, "anchor_date": "2026-09-17T02:00"},
    ).json()
    assert body["window_code"] == "NIGHT_PEAK"
    assert body["factor"] == 1.2


def test_peak_without_anchor_returns_422(client):
    r = client.post("/api/bill", json={"kwh": 120, "peak": True, "persist": False})
    assert r.status_code == 422
    assert "锚定日" in r.json()["detail"]


def test_peak_unchecked_matches_legacy_behavior(client):
    body = client.post("/api/bill", json={"kwh": 120, "peak": False, "persist": False}).json()
    assert body["factor"] == 1.0
    assert body["miss_reason"] == "peak_not_requested"
    assert body["total"] == 62.40
    assert body["run_id"] is None


def test_non_cross_day_start_after_end_rejected(client):
    r = client.post(
        "/api/peak-windows",
        json={"code": "BAD_ONE", "start_time": "18:00", "end_time": "09:00"},
    )
    assert r.status_code == 422
    assert "跨日" in r.json()["detail"]


def test_same_priority_overlap_conflict_names_two_codes(client):
    created = client.post(
        "/api/peak-windows",
        json={"code": "TMP_A", "start_time": "10:00", "end_time": "11:00", "priority": 50},
    ).json()
    r = client.post(
        "/api/peak-windows",
        json={"code": "TMP_B", "start_time": "10:30", "end_time": "11:30", "priority": 50},
    )
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "TMP_A" in detail and "TMP_B" in detail
    # 冲突的第二条不得落库
    assert client.post(f"/api/peak-windows/{created['id']}/disable").status_code == 200


def test_different_priority_overlap_allowed(client):
    a = client.post(
        "/api/peak-windows",
        json={"code": "TMP_C", "start_time": "14:00", "end_time": "15:00", "priority": 60},
    ).json()
    r = client.post(
        "/api/peak-windows",
        json={"code": "TMP_D", "start_time": "14:30", "end_time": "15:30", "priority": 61},
    )
    assert r.status_code == 201, r.text
    b = r.json()
    client.post(f"/api/peak-windows/{a['id']}/disable")
    client.post(f"/api/peak-windows/{b['id']}/disable")


def test_duplicate_code_rejected(client):
    r = client.post(
        "/api/peak-windows",
        json={"code": "EVENING_PEAK", "start_time": "07:00", "end_time": "08:00"},
    )
    assert r.status_code == 422


def test_trial_creates_no_bill_run_and_persist_pins_factor(client):
    before = len(client.get("/api/history").json()["items"])
    trial = client.post(
        "/api/bill",
        json={"kwh": 220, "peak": True, "persist": False, "anchor_date": "2026-09-17T19:00"},
    ).json()
    assert trial["run_id"] is None
    after_trial = len(client.get("/api/history").json()["items"])
    assert after_trial == before

    saved = client.post(
        "/api/bill",
        json={
            "kwh": 220,
            "peak": True,
            "persist": True,
            "anchor_date": "2026-09-17T19:00",
            "account_id": 1,
        },
    ).json()
    assert saved["run_id"] is not None
    detail = client.get(f"/api/history/{saved['run_id']}").json()
    import json

    snap = json.loads(detail["result_json"])["peak_snapshot"]
    assert snap["window_code"] == "EVENING_PEAK"
    assert snap["factor"] == 1.2


def test_disabled_window_history_still_resolvable(client):
    # 停用时段后：新测算不再命中；旧运行的快照仍保留 window_code
    items = client.get("/api/peak-windows").json()["items"]
    night = next(w for w in items if w["code"] == "NIGHT_PEAK")
    saved = client.post(
        "/api/bill",
        json={"kwh": 100, "peak": True, "persist": True, "anchor_date": "2026-09-17T03:00"},
    ).json()
    assert saved["window_code"] == "NIGHT_PEAK"

    client.post(f"/api/peak-windows/{night['id']}/disable")
    now_miss = client.post(
        "/api/bill",
        json={"kwh": 100, "peak": True, "persist": False, "anchor_date": "2026-09-17T03:00"},
    ).json()
    assert now_miss["miss_reason"] == "outside_windows"

    import json

    old = client.get(f"/api/history/{saved['run_id']}").json()
    snap = json.loads(old["result_json"])["peak_snapshot"]
    assert snap["window_code"] == "NIGHT_PEAK"
    assert snap["factor"] == 1.2

    # 恢复启用，避免影响其他用例顺序
    client.put(f"/api/peak-windows/{night['id']}", json={"enabled": True})
