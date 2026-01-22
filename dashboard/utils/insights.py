"""Helpers for extracting narrative insights for the dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pandas as pd

from .formatters import NA_TEXT, format_num, format_pct, safe_delta

DEFAULT_REPORT_PATH = Path("reports/brief_latest.md")

INDICATOR_LABELS = {
    "stress_mean": "average stress",
    "stress_high_pct": "high stress",
    "food_insecurity_pct": "food insecurity",
    "childcare_difficulty_high_pct": "high childcare difficulty",
    "employment_disruption_pct": "employment disruption",
    "staff_shortage_pct": "staff shortages",
    "closure_risk_high_pct": "closure risk",
}


def _is_bullet(line: str) -> bool:
    return line.lstrip().startswith(("- ", "* "))


def load_top_insights(report_path: Path | None = None, limit: int = 5) -> List[str]:
    """Return up to ``limit`` sentences parsed from the latest narrative brief."""
    target = report_path or DEFAULT_REPORT_PATH
    if not target.exists():
        return []
    insights: List[str] = []
    try:
        for raw_line in target.read_text(encoding="utf-8").splitlines():
            if _is_bullet(raw_line):
                insights.append(raw_line.lstrip("-* ").strip())
            if len(insights) >= limit:
                break
    except OSError:
        return []
    return [text for text in insights if text]


def _filter_frame(indicators: Optional[pd.DataFrame], frame: str) -> pd.DataFrame:
    if indicators is None or indicators.empty:
        return pd.DataFrame()
    if "frame" not in indicators.columns:
        return pd.DataFrame()
    mask = indicators["frame"].astype(str).str.lower() == frame.lower()
    return indicators.loc[mask].copy()


def compute_latest_and_previous(
    indicators: Optional[pd.DataFrame], frame: str
) -> Tuple[Optional[pd.Series], Optional[pd.Series], Optional[pd.Timestamp]]:
    """Return the most recent and prior rows for the requested frame."""
    subset = _filter_frame(indicators, frame)
    if subset.empty:
        return None, None, None
    if "survey_month" in subset.columns:
        subset["survey_month"] = pd.to_datetime(subset["survey_month"], errors="coerce")
    if "wave" in subset.columns:
        subset["wave"] = pd.to_numeric(subset["wave"], errors="coerce")
    sort_cols = [col for col in ("survey_month", "wave") if col in subset.columns]
    subset = subset.sort_values(sort_cols) if sort_cols else subset.reset_index(drop=True)
    latest = subset.iloc[-1]
    previous = subset.iloc[-2] if len(subset) > 1 else None
    latest_month = latest.get("survey_month") if "survey_month" in latest.index else None
    return latest, previous, latest_month


def compute_kpis(
    indicators: Optional[pd.DataFrame], frame: str, indicator_names: Sequence[str]
) -> pd.DataFrame:
    """Return per-indicator rows for the latest wave plus prior estimate."""
    subset = _filter_frame(indicators, frame)
    if subset.empty:
        return pd.DataFrame()
    subset = subset[subset["indicator"].isin(indicator_names)].copy()
    if subset.empty:
        return pd.DataFrame()
    if "survey_month" in subset.columns:
        subset["survey_month"] = pd.to_datetime(subset["survey_month"], errors="coerce")
    if "wave" in subset.columns:
        subset["wave"] = pd.to_numeric(subset["wave"], errors="coerce")
    rows: list[dict] = []
    for indicator in indicator_names:
        series = subset[subset["indicator"] == indicator]
        if series.empty:
            continue
        sort_cols = [col for col in ("survey_month", "wave") if col in series.columns]
        series = series.sort_values(sort_cols) if sort_cols else series.reset_index(drop=True)
        latest = series.iloc[-1]
        previous = series.iloc[-2] if len(series) > 1 else None
        rows.append(
            {
                "frame": frame,
                "indicator": indicator,
                "estimate": latest.get("estimate"),
                "ci_low": latest.get("ci_low"),
                "ci_high": latest.get("ci_high"),
                "prev_estimate": previous.get("estimate") if previous is not None else None,
                "wave": latest.get("wave"),
                "survey_month": latest.get("survey_month"),
            }
        )
    return pd.DataFrame(rows)


def _indicator_kind(indicator: str) -> str:
    return "pct" if indicator.endswith("_pct") else "num"


def _format_estimate(value: Optional[float], kind: str) -> str:
    return format_pct(value) if kind == "pct" else format_num(value)


def _delta_sentence(
    kpis: pd.DataFrame,
    indicator: str,
    frame_label: str,
    description: str,
) -> Optional[str]:
    if kpis.empty:
        return None
    row = kpis[kpis["indicator"] == indicator]
    if row.empty:
        return None
    record = row.iloc[0]
    kind = _indicator_kind(indicator)
    estimate_text = _format_estimate(record.get("estimate"), kind)
    delta_text = safe_delta(record.get("estimate"), record.get("prev_estimate"), kind)
    if delta_text == NA_TEXT:
        delta_phrase = "no prior wave for comparison"
    else:
        delta_phrase = f"{delta_text} vs prior wave"
    return f"{frame_label} {description} {estimate_text} ({delta_phrase})."


def _income_gap_sentence(subgroups: Optional[pd.DataFrame]) -> Optional[str]:
    if subgroups is None or subgroups.empty:
        return None
    subset = subgroups.copy()
    column = "subgroup"
    if column not in subset.columns and "subgroup_value" in subset.columns:
        column = "subgroup_value"
    if "indicator" not in subset.columns or "subgroup_type" not in subset.columns:
        return None
    indicator_mask = subset["indicator"] == "food_insecurity_pct"
    type_mask = subset["subgroup_type"].astype(str).str.contains("income", case=False, na=False)
    mask = indicator_mask & type_mask
    subset = subset[mask]
    if subset.empty or column not in subset.columns or "estimate" not in subset.columns:
        return None
    subset = subset.dropna(subset=["estimate"])
    if subset.empty:
        return None
    top = subset.loc[subset["estimate"].idxmax()]
    bottom = subset.loc[subset["estimate"].idxmin()]
    gap = (top["estimate"] - bottom["estimate"]) * 100
    return (
        f"Food insecurity highest for {top[column]} households ({format_pct(top['estimate'])}) "
        f"and lowest for {bottom[column]} ({format_pct(bottom['estimate'])}); "
        f"gap {gap:.1f} pts."
    )


def _state_extremes_sentence(state_df: Optional[pd.DataFrame]) -> Optional[str]:
    if state_df is None or state_df.empty:
        return None
    if "indicator" not in state_df.columns:
        return None
    subset = state_df[state_df["indicator"] == "stress_high_pct"].copy()
    if subset.empty or "state" not in subset.columns or "estimate" not in subset.columns:
        return None
    subset = subset.dropna(subset=["estimate"])
    if subset.empty:
        return None
    top = subset.loc[subset["estimate"].idxmax()]
    bottom = subset.loc[subset["estimate"].idxmin()]
    return (
        f"High stress highest in {top['state']} ({format_pct(top['estimate'])}) "
        f"and lowest in {bottom['state']} ({format_pct(bottom['estimate'])})."
    )


def compute_top_insights(
    indicators: Optional[pd.DataFrame],
    subgroups_household: Optional[pd.DataFrame] = None,
    state_heatmap: Optional[pd.DataFrame] = None,
) -> List[str]:
    """Synthesize up to five deterministic insight bullets."""
    insights: List[str] = []
    household_kpis = compute_kpis(
        indicators,
        frame="household",
        indicator_names=["stress_high_pct", "food_insecurity_pct"],
    )
    provider_kpis = compute_kpis(
        indicators,
        frame="provider",
        indicator_names=["staff_shortage_pct"],
    )

    for indicator, description in (
        ("stress_high_pct", "high stress"),
        ("food_insecurity_pct", "food insecurity"),
    ):
        sentence = _delta_sentence(household_kpis, indicator, "Household", description)
        if sentence:
            insights.append(sentence)

    income_sentence = _income_gap_sentence(subgroups_household)
    if income_sentence:
        insights.append(income_sentence)

    state_sentence = _state_extremes_sentence(state_heatmap)
    if state_sentence:
        insights.append(state_sentence)

    provider_sentence = _delta_sentence(provider_kpis, "staff_shortage_pct", "Provider", "staff shortages")
    if provider_sentence:
        insights.append(provider_sentence)

    return insights[:5]


__all__ = [
    "compute_kpis",
    "compute_latest_and_previous",
    "compute_top_insights",
    "load_top_insights",
]
