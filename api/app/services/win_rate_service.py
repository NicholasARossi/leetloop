"""Win Rate Service - manages win rate targets, calculations, and snapshots."""

from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from supabase import Client

from app.models.winrate_schemas import (
    DifficultyWinRate,
    SetWinRateTargetsRequest,
    WinRateTargets,
)


class WinRateService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def get_targets(self, user_id: UUID) -> Optional[WinRateTargets]:
        response = (
            self.supabase.table("win_rate_targets")
            .select("*")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if response.data:
            return WinRateTargets(**response.data[0])
        return None

    def set_targets(self, user_id: UUID, request: SetWinRateTargetsRequest) -> WinRateTargets:
        data = {
            "user_id": str(user_id),
            "easy_target": request.easy_target,
            "medium_target": request.medium_target,
            "hard_target": request.hard_target,
            "optimality_threshold": request.optimality_threshold,
            "updated_at": datetime.utcnow().isoformat(),
        }
        response = (
            self.supabase.table("win_rate_targets")
            .upsert(data, on_conflict="user_id")
            .execute()
        )
        return WinRateTargets(**response.data[0])

    def calculate_win_rates(self, user_id: UUID) -> dict:
        user_id_str = str(user_id)
        thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()

        # All-time metric attempts
        alltime_resp = (
            self.supabase.table("metric_attempts")
            .select("difficulty, final_optimal")
            .eq("user_id", user_id_str)
            .execute()
        )

        # 30-day metric attempts
        recent_resp = (
            self.supabase.table("metric_attempts")
            .select("difficulty, final_optimal")
            .eq("user_id", user_id_str)
            .gte("attempted_at", thirty_days_ago)
            .execute()
        )

        def _compute_rates(data: list) -> dict:
            rates = {}
            for diff in ["Easy", "Medium", "Hard"]:
                items = [d for d in data if d["difficulty"] == diff]
                total = len(items)
                optimal = sum(1 for d in items if d["final_optimal"])
                rate = optimal / total if total > 0 else 0.0
                rates[diff.lower()] = {
                    "rate": round(rate, 4),
                    "attempts": total,
                    "optimal": optimal,
                }
            return rates

        return {
            "alltime": _compute_rates(alltime_resp.data or []),
            "thirty_day": _compute_rates(recent_resp.data or []),
        }

    def get_stats(self, user_id: UUID) -> dict:
        targets = self.get_targets(user_id)
        if not targets:
            return {"targets": None, "current_30d": {}, "current_alltime": {}, "trend": []}

        rates = self.calculate_win_rates(user_id)

        # Add target to each difficulty
        target_map = {
            "easy": targets.easy_target,
            "medium": targets.medium_target,
            "hard": targets.hard_target,
        }
        for period in ["alltime", "thirty_day"]:
            for diff in ["easy", "medium", "hard"]:
                if diff in rates[period]:
                    rates[period][diff]["target"] = target_map[diff]

        # Get trend from snapshots (last 30 days)
        thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
        trend_resp = (
            self.supabase.table("win_rate_snapshots")
            .select("snapshot_date, easy_rate_30d, medium_rate_30d, hard_rate_30d")
            .eq("user_id", str(user_id))
            .gte("snapshot_date", thirty_days_ago)
            .order("snapshot_date")
            .execute()
        )

        trend = []
        for row in (trend_resp.data or []):
            trend.append({
                "date": row["snapshot_date"],
                "easy_rate": row["easy_rate_30d"],
                "medium_rate": row["medium_rate_30d"],
                "hard_rate": row["hard_rate_30d"],
            })

        return {
            "targets": targets.model_dump(mode="json"),
            "current_30d": rates["thirty_day"],
            "current_alltime": rates["alltime"],
            "trend": trend,
        }

    def update_snapshot(self, user_id: UUID) -> None:
        rates = self.calculate_win_rates(user_id)
        today = date.today().isoformat()
        user_id_str = str(user_id)

        alltime = rates["alltime"]
        thirty_day = rates["thirty_day"]

        data = {
            "user_id": user_id_str,
            "snapshot_date": today,
            "easy_rate_alltime": alltime.get("easy", {}).get("rate", 0.0),
            "easy_attempts_alltime": alltime.get("easy", {}).get("attempts", 0),
            "easy_optimal_alltime": alltime.get("easy", {}).get("optimal", 0),
            "medium_rate_alltime": alltime.get("medium", {}).get("rate", 0.0),
            "medium_attempts_alltime": alltime.get("medium", {}).get("attempts", 0),
            "medium_optimal_alltime": alltime.get("medium", {}).get("optimal", 0),
            "hard_rate_alltime": alltime.get("hard", {}).get("rate", 0.0),
            "hard_attempts_alltime": alltime.get("hard", {}).get("attempts", 0),
            "hard_optimal_alltime": alltime.get("hard", {}).get("optimal", 0),
            "easy_rate_30d": thirty_day.get("easy", {}).get("rate", 0.0),
            "easy_attempts_30d": thirty_day.get("easy", {}).get("attempts", 0),
            "easy_optimal_30d": thirty_day.get("easy", {}).get("optimal", 0),
            "medium_rate_30d": thirty_day.get("medium", {}).get("rate", 0.0),
            "medium_attempts_30d": thirty_day.get("medium", {}).get("attempts", 0),
            "medium_optimal_30d": thirty_day.get("medium", {}).get("optimal", 0),
            "hard_rate_30d": thirty_day.get("hard", {}).get("rate", 0.0),
            "hard_attempts_30d": thirty_day.get("hard", {}).get("attempts", 0),
            "hard_optimal_30d": thirty_day.get("hard", {}).get("optimal", 0),
        }

        self.supabase.table("win_rate_snapshots").upsert(
            data, on_conflict="user_id,snapshot_date"
        ).execute()

    def check_optimality(self, runtime_percentile: Optional[float], threshold: float = 70.0) -> bool:
        if runtime_percentile is None:
            return False
        return runtime_percentile >= threshold
