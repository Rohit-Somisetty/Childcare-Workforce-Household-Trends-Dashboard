"""Filtering helpers shared across dashboard pages."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .load_data import get_latest_wave


def indicator_kind(name: Optional[str]) -> str:
    """Return ``pct`` when the indicator ends with ``_pct`` else ``num``."""
    if not name:
        return "num"
    return "pct" if str(name).endswith("_pct") else "num"


def filter_latest_wave(
    dataset: Optional[pd.DataFrame],
    frame: str,
    indicators_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """Restrict ``dataset`` to the latest wave observed for ``frame``."""
    if dataset is None or dataset.empty:
        columns = list(dataset.columns) if dataset is not None else None
        return pd.DataFrame(columns=columns)

    working = dataset.copy()
    if "frame" in working.columns:
        mask = working["frame"].astype(str).str.lower() == frame.lower()
        working = working[mask]

    if indicators_df is None or indicators_df.empty:
        return working

    latest = get_latest_wave(indicators_df, match_frame=frame)
    if latest is None:
        return working

    filters = []
    latest_wave = latest.get("wave")
    latest_wave_id = latest.get("wave_id")
    latest_month = latest.get("survey_month")
    latest_end = latest.get("wave_end_date")

    if pd.notna(latest_wave) and "wave" in working.columns:
        filters.append(working["wave"] == latest_wave)
    if pd.notna(latest_wave_id) and "wave_id" in working.columns:
        filters.append(working["wave_id"].astype(str) == str(latest_wave_id))
    if pd.notna(latest_month) and "survey_month" in working.columns:
        working["survey_month"] = pd.to_datetime(working["survey_month"], errors="coerce")
        filters.append(working["survey_month"] == latest_month)
    if pd.notna(latest_end) and "wave_end_date" in working.columns:
        working["wave_end_date"] = pd.to_datetime(working["wave_end_date"], errors="coerce")
        filters.append(working["wave_end_date"] == latest_end)

    if not filters:
        return working

    combined = filters[0]
    for condition in filters[1:]:
        combined = combined | condition
    return working[combined]


__all__ = ["filter_latest_wave", "indicator_kind"]
