from datetime import datetime, timedelta
import re
import time
from typing import Iterable, Tuple


def weighted_avg(couples: Iterable[Tuple[float, float]]) -> float:
    """Calculate the weighted average of a list of values."""
    total = 0
    weight = 0
    for value, weight_ in couples:
        total += value * weight_
        weight += weight_
    if weight == 0:
        return 0
    return total / weight


def parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse a datetime string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    value = value.strip("Z").split(".")[0]
    return datetime.fromisoformat(value)


def minmax(min_max: tuple[float, float], value: float) -> float:
    """Trim a value between {min} and {max}."""
    min_, max_ = min_max
    if value > max_:
        return max_
    if value < min_:
        return min_
    return value


def flatten_keys(d: dict, sep: str = "_", lowercase: bool = True):
    """Flatten a nested dictionary by concatenating keys with a separator."""

    def flatten(d, parent_key="", sep="_"):
        items = []
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if lowercase:
                new_key = new_key.lower()
            if isinstance(v, dict):
                items.extend(flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    return flatten(d, sep=sep)


def normalize_between(
    min: float,
    max: float,
    value: float,
    trim: bool = True,
) -> float:
    """Normalize a value from [{min},{max}] to [0,1]"""
    out = (value - min) / (max - min)
    if out < 0 and trim:
        return 0
    if out > 1 and trim:
        return 1
    return out


def parse_duration(d: str | timedelta | datetime | int | float) -> timedelta | None:
    """Parse a duration from int, string, timedelta or datetime."""
    if not d:
        return None
    if isinstance(d, timedelta):
        return d
    if isinstance(d, int | float):
        return timedelta(seconds=d)
    try:
        return timedelta(seconds=float(d))
    except Exception:
        pass

    try:
        return datetime.now() - datetime.fromisoformat(d)
    except Exception:
        if m := re.match(r"((\d+)y)?((\d+)m)?((\d+)d)?(([\d\.]+)s)?", d, re.I):
            years = int(m.group(2)) if m.group(1) else 0
            months = int(m.group(4)) if m.group(3) else 0
            days = int(m.group(6)) if m.group(5) else 0
            seconds = float(m.group(8)) if m.group(8) else 0
            return timedelta(days=(years * 365) + (months * 30) + days, seconds=seconds)
        raise ValueError(f"Invalid duration format: {d}")
