"""Formatting helpers for Streamlit UI elements."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple, Union

import math

DateLike = Union[str, datetime]

NA_TEXT = "--"


def _coerce_datetime(value: Optional[DateLike]) -> Optional[datetime]:
    """Convert assorted date-like inputs to ``datetime`` if possible."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def format_wave_heading(wave_label: Optional[Union[str, int]], wave_end_date: Optional[DateLike]) -> str:
    """Compose a short human-readable label for the latest survey wave."""
    segments: list[str] = []
    if wave_label not in (None, ""):
        label = str(wave_label).strip()
        if label.isdigit():
            segments.append(f"Wave {label}")
        else:
            segments.append(label)
    dt_value = _coerce_datetime(wave_end_date)
    if dt_value:
        segments.append(f"ending {dt_value:%b %d, %Y}")
    return " ".join(segments) if segments else "Latest reporting wave"


def _is_missing(value: Optional[float]) -> bool:
    if value is None:
        return True
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def format_pct(value: Optional[float], decimals: int = 1) -> str:
    """Format a decimal proportion as a percentage string."""
    if _is_missing(value):
        return NA_TEXT
    pct = value * 100
    return f"{pct:.{decimals}f}%"


def format_num(value: Optional[float], decimals: int = 1) -> str:
    """Format a numeric metric with the requested decimals."""
    if _is_missing(value):
        return NA_TEXT
    return f"{value:.{decimals}f}"


def format_ci(
    est: Optional[float], lo: Optional[float], hi: Optional[float], kind: str = "pct"
) -> str:
    """Return a formatted estimate with a 95% CI span."""
    fmt = format_pct if kind == "pct" else format_num
    est_text = fmt(est)
    lo_text = fmt(lo)
    hi_text = fmt(hi)
    if NA_TEXT in (lo_text, hi_text):
        return est_text
    if kind == "pct":
        lo_core = lo_text.rstrip("%")
        hi_core = hi_text.rstrip("%")
        return f"{est_text} (95% CI {lo_core}-{hi_core}%)"
    return f"{est_text} (95% CI {lo_text}-{hi_text})"


def safe_delta(curr: Optional[float], prev: Optional[float], kind: str = "pct", decimals: int = 1) -> str:
    """Return a delta string comparing current vs prior wave."""
    if _is_missing(curr) or _is_missing(prev):
        return NA_TEXT
    delta = curr - prev
    units = " pts" if kind == "pct" else ""
    scale = 100 if kind == "pct" else 1
    scaled = delta * scale
    sign = "+" if scaled >= 0 else ""
    return f"{sign}{scaled:.{decimals}f}{units}"


def badge_delta(delta_text: str) -> Tuple[str, str]:
    """Map a delta string to qualitative badge text + color hint."""
    if not delta_text or delta_text == NA_TEXT:
        return ("neutral", "secondary")
    if delta_text.startswith("+"):
        return ("increase", "success")
    if delta_text.startswith("-"):
        return ("decrease", "warning")
    return ("neutral", "secondary")
