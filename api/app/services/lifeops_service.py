"""Life Ops service for daily checklist generation, streaks, and stats."""

from datetime import date, datetime, timedelta


# Weekday bitmask: Monday=1, Tuesday=2, Wednesday=4, Thursday=8, Friday=16, Saturday=32, Sunday=64
def should_run_on_date(recurrence_days: int, target_date: date) -> bool:
    """Check if a task should appear on a given date based on its recurrence bitmask."""
    # Python weekday(): Monday=0 .. Sunday=6
    weekday_bit = 1 << target_date.weekday()
    return bool(recurrence_days & weekday_bit)


def generate_daily_items(
    tasks: list[dict],
    categories: dict[str, dict],
    user_id: str,
    target_date: date,
) -> list[dict]:
    """Generate daily checklist items from active tasks for a given date."""
    items = []
    for task in tasks:
        if not task.get("is_active", True):
            continue
        if not should_run_on_date(task.get("recurrence_days", 127), target_date):
            continue

        cat_id = task.get("category_id")
        cat = categories.get(cat_id, {}) if cat_id else {}

        items.append({
            "user_id": user_id,
            "task_id": task["id"],
            "checklist_date": target_date.isoformat(),
            "is_completed": False,
            "sort_order": task.get("sort_order", 0),
            "task_title": task["title"],
            "category_id": cat_id,
            "category_name": cat.get("name"),
        })

    return items


def compute_streak(
    daily_items_by_date: dict[str, list[dict]],
    existing_streak: dict | None,
) -> dict:
    """Compute current streak, longest streak, and total perfect days.

    daily_items_by_date: {date_str: [items]} for recent dates
    existing_streak: current streak row from DB (or None)
    """
    today = date.today()
    current_streak = 0
    total_perfect_days = existing_streak.get("total_perfect_days", 0) if existing_streak else 0
    longest_streak = existing_streak.get("longest_streak", 0) if existing_streak else 0

    # Walk backwards from today
    check_date = today
    for _ in range(365):  # max 1 year lookback
        date_str = check_date.isoformat()
        items = daily_items_by_date.get(date_str, [])

        if not items:
            # No items for this date — could mean no tasks were scheduled
            # If it's today and items haven't been generated yet, skip
            if check_date == today:
                check_date -= timedelta(days=1)
                continue
            break

        all_completed = all(item.get("is_completed", False) for item in items)
        if all_completed:
            current_streak += 1
        else:
            break

        check_date -= timedelta(days=1)

    # Count today as perfect if all done
    today_str = today.isoformat()
    today_items = daily_items_by_date.get(today_str, [])
    if today_items and all(item.get("is_completed", False) for item in today_items):
        last_completed_date = today
    elif existing_streak and existing_streak.get("last_completed_date"):
        last_completed_date = existing_streak["last_completed_date"]
    else:
        last_completed_date = None

    if current_streak > longest_streak:
        longest_streak = current_streak

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "last_completed_date": last_completed_date,
        "total_perfect_days": total_perfect_days,
    }


def compute_completion_rates(
    daily_items_by_date: dict[str, list[dict]],
) -> tuple[list[dict], list[dict]]:
    """Compute weekly and monthly completion rates.

    Returns (weekly_rates, monthly_rates) for the last 4 weeks and 3 months.
    """
    today = date.today()

    # Weekly rates (last 4 weeks)
    weekly_rates = []
    for week_offset in range(4):
        week_start = today - timedelta(days=today.weekday() + 7 * week_offset)
        week_end = week_start + timedelta(days=6)
        completed = 0
        total = 0
        for day_offset in range(7):
            d = week_start + timedelta(days=day_offset)
            if d > today:
                break
            items = daily_items_by_date.get(d.isoformat(), [])
            total += len(items)
            completed += sum(1 for item in items if item.get("is_completed", False))

        rate = (completed / total * 100) if total > 0 else 0.0
        label = f"Week of {week_start.strftime('%b %d')}"
        weekly_rates.append({
            "period": label,
            "completed": completed,
            "total": total,
            "rate": round(rate, 1),
        })

    # Monthly rates (last 3 months)
    monthly_rates = []
    for month_offset in range(3):
        year = today.year
        month = today.month - month_offset
        if month <= 0:
            month += 12
            year -= 1
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        completed = 0
        total = 0
        d = month_start
        while d <= min(month_end, today):
            items = daily_items_by_date.get(d.isoformat(), [])
            total += len(items)
            completed += sum(1 for item in items if item.get("is_completed", False))
            d += timedelta(days=1)

        rate = (completed / total * 100) if total > 0 else 0.0
        label = month_start.strftime("%B %Y")
        monthly_rates.append({
            "period": label,
            "completed": completed,
            "total": total,
            "rate": round(rate, 1),
        })

    return weekly_rates, monthly_rates
