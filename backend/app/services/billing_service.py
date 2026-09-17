from app.db import connect
from app.engines.peak_compare import compare_plain_vs_peak
from app.engines.tier_progressive import calc_bill
from app.modules.peak_hours import repository as peak_repo
from app.modules.peak_hours.anchor import anchor_label, anchor_minute
from app.modules.peak_hours.matcher import REASON_HIT, evaluate
from app.repositories import accounts as accounts_repo
from app.repositories import readings as readings_repo
from app.repositories import runs as runs_repo
from app.repositories import settings as settings_repo
from app.repositories import tiers as tiers_repo

#: 未勾选尖峰（行为与改造前一致）
REASON_PEAK_NOT_REQUESTED = "peak_not_requested"
#: 勾选了尖峰但未提供账期锚定日
REASON_MISSING_ANCHOR = "missing_anchor"

FACTOR_SOURCE_SETTING = "settings.peak_factor"
FACTOR_SOURCE_DEFAULT = "default_1.0"
FACTOR_SOURCE_NONE = "not_applied"


class BillingService:
    def __init__(self):
        self._conn = connect()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def list_accounts(self):
        return accounts_repo.list_all(self._conn)

    def get_account(self, account_id: int):
        return accounts_repo.get(self._conn, account_id)

    def list_tiers(self):
        return tiers_repo.list_ordered(self._conn)

    def list_readings(self):
        return readings_repo.list_all(self._conn)

    def readings_for_account(self, account_id: int):
        return readings_repo.for_account(self._conn, account_id)

    def settings_map(self):
        return settings_repo.get_map(self._conn)

    def run_bill(
        self,
        kwh: float,
        peak: bool,
        account_id: int | None,
        persist: bool,
        anchor_date: str | None = None,
    ) -> dict:
        tiers = tiers_repo.as_calc_rows(self._conn)
        settings_factor = settings_repo.peak_factor(self._conn)

        decision = self._peak_decision(peak, anchor_date, settings_factor)
        result = calc_bill(kwh, tiers, decision["factor"])
        # calc_bill.peak_factor 即“实际使用系数”；决策块补充命中与来源信息
        result.update(
            {
                "peak_requested": peak,
                "peak_hit": decision["hit"],
                "window_code": decision["window_code"],
                "window_id": decision["window_id"],
                "window_priority": decision["priority"],
                "factor": decision["factor"],
                "factor_source": decision["factor_source"],
                "settings_peak_factor": settings_factor,
                "miss_reason": None if decision["hit"] else decision["reason"],
                "anchor_date": anchor_date,
                "anchor_label": anchor_label(anchor_date) if anchor_date else None,
                # 钉选快照：随 result_json 持久化，历史运行不受后续配置变更影响
                "peak_snapshot": {
                    "window_code": decision["window_code"],
                    "window_id": decision["window_id"],
                    "priority": decision["priority"],
                    "factor": decision["factor"],
                    "factor_source": decision["factor_source"],
                    "settings_peak_factor": settings_factor,
                    "anchor_date": anchor_date,
                    "reason": decision["reason"],
                    "hit": decision["hit"],
                },
            }
        )

        run_id = None
        if persist:
            # 只有显式写入路径才落 bill 运行记录；只读试算（persist=False）不产生任何记录
            run_id = runs_repo.insert(
                self._conn,
                "bill",
                {
                    "kwh": kwh,
                    "peak": peak,
                    "account_id": account_id,
                    "anchor_date": anchor_date,
                    "window_code": decision["window_code"],
                    "factor": decision["factor"],
                },
                result,
                account_id,
            )
        return {"run_id": run_id, **result}

    def _peak_decision(self, peak: bool, anchor_date: str | None, settings_factor: float) -> dict:
        base = {
            "hit": False,
            "window_code": None,
            "window_id": None,
            "priority": None,
            "factor": 1.0,
        }
        if not peak:
            return {**base, "reason": REASON_PEAK_NOT_REQUESTED, "factor_source": FACTOR_SOURCE_NONE}
        if not anchor_date:
            raise ValueError("勾选尖峰系数时必须提供账期锚定日（anchor_date）")
        windows = peak_repo.list_enabled_windows(self._conn)
        match = evaluate(windows, anchor_minute(anchor_date))
        if match["reason"] == REASON_HIT:
            return {
                **match,
                "factor": settings_factor,
                "factor_source": FACTOR_SOURCE_SETTING,
            }
        return {**match, "factor": 1.0, "factor_source": FACTOR_SOURCE_DEFAULT}

    def run_compare(self, kwh: float, persist: bool):
        tiers = tiers_repo.as_calc_rows(self._conn)
        pf = settings_repo.peak_factor(self._conn)
        result = compare_plain_vs_peak(kwh, tiers, pf)
        run_id = None
        if persist:
            run_id = runs_repo.insert(self._conn, "compare", {"kwh": kwh}, result, None)
        return {"run_id": run_id, **result}

    def list_history(self, limit: int = 50):
        return runs_repo.list_recent(self._conn, limit)

    def get_run(self, run_id: int):
        return runs_repo.get(self._conn, run_id)

    def dashboard_stats(self):
        accounts = accounts_repo.list_all(self._conn)
        readings = readings_repo.list_all(self._conn)
        clean = [a for a in accounts if "种子" not in a.get("name", "")]
        dirty = [a for a in accounts if "种子" in a.get("name", "")]
        return {
            "account_count": len(accounts),
            "reading_count": len(readings),
            "clean_accounts": len(clean),
            "dirty_accounts": len(dirty),
            "recent_runs": len(runs_repo.list_recent(self._conn, 5)),
        }
