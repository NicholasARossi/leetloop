"""Datetime parsing utilities."""

import re
from datetime import datetime


def parse_iso_datetime(dt_string: str) -> datetime:
    """
    Parse ISO datetime string, handling variable microsecond precision.

    PostgreSQL can return timestamps with variable microsecond precision (1-6 digits),
    but Python's datetime.fromisoformat() before 3.11 requires exactly 0, 3, or 6 digits.
    This function normalizes the microseconds to 6 digits before parsing.
    """
    if not dt_string:
        return datetime.utcnow()

    dt_string = dt_string.replace("Z", "+00:00")

    # Match the fractional seconds and timezone
    match = re.match(r"(.+T\d{2}:\d{2}:\d{2})\.(\d+)([+-]\d{2}:\d{2})?$", dt_string)
    if match:
        base, frac, tz = match.groups()
        # Pad or truncate to exactly 6 digits
        frac = frac[:6].ljust(6, "0")
        dt_string = f"{base}.{frac}{tz or ''}"

    return datetime.fromisoformat(dt_string)
