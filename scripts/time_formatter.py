"""
Time formatting utility for HowLongToBeat durations.
Formats durations into user-specified representation:
  - 3h 15m
  - 5h
  - 1h 23m
  - 55m
  - -- (for N/A / unrecorded)
"""

from typing import Optional, Dict, Any, Union


def format_duration(hours: Optional[Union[float, int]]) -> Dict[str, Any]:
    """
    Converts duration in hours (float/int) into formatted string and minutes for sorting.
    Missing or 0 hours return display '--' and minutes -1 (for pinning to bottom in sorting).
    """
    if hours is None or hours <= 0:
        return {
            "display": "--",
            "minutes": -1,
            "hours": 0.0
        }

    total_minutes = int(round(float(hours) * 60))

    if total_minutes <= 0:
        return {
            "display": "--",
            "minutes": -1,
            "hours": 0.0
        }

    h = total_minutes // 60
    m = total_minutes % 60

    if h == 0:
        display = f"{m}m"
    elif m == 0:
        display = f"{h}h"
    else:
        display = f"{h}h {m}m"

    return {
        "display": display,
        "minutes": total_minutes,
        "hours": round(float(hours), 2)
    }
