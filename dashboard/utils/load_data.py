"""Data loading helpers for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Optional
import re

import pandas as pd

DATA_BOOTSTRAP_COMMAND = "python scripts/bootstrap_demo_data.py"


@dataclass(frozen=True)
class DatasetSpec:
    """Blueprint describing how to load and clean a CSV dataset."""

    name: str
    relative_path: str
    parse_dates: tuple[str, ...] = ()
    ensure_columns: tuple[str, ...] = ()
    frame: Optional[str] = None
    description: str = ""


DATASET_SPECS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        name="indicators_overall",
        relative_path="data/outputs/indicators_overall.csv",
        parse_dates=("wave_end_date",),
        ensure_columns=(
            "frame",
            "indicator",
            "estimate",
            "ci_low",
            "ci_high",
            "wave",
        ),
        frame="overall",
        description="Household + provider KPI rollups",
    ),
    DatasetSpec(
        name="subgroups_household_latest",
        relative_path="data/outputs/subgroups_household_latest.csv",
        ensure_columns=(
            "frame",
            "subgroup",
            "subgroup_type",
            "indicator",
            "estimate",
            "ci_low",
            "ci_high",
            "n_unweighted",
        ),
        frame="household",
        description="Latest wave household subgroup breakouts",
    ),
    DatasetSpec(
        name="subgroups_provider_latest",
        relative_path="data/outputs/subgroups_provider_latest.csv",
        ensure_columns=(
            "frame",
            "subgroup",
            "subgroup_type",
            "indicator",
            "estimate",
            "ci_low",
            "ci_high",
            "n_unweighted",
        ),
        frame="provider",
        description="Latest wave provider subgroup breakouts",
    ),
    DatasetSpec(
        name="state_indicator_heatmap_latest",
        relative_path="data/outputs/state_indicator_heatmap_latest.csv",
        ensure_columns=(
            "frame",
            "state",
            "indicator",
            "estimate",
            "ci_low",
            "ci_high",
        ),
        description="State-level indicator panel",
    ),
)

SPEC_LOOKUP: Dict[str, DatasetSpec] = {spec.name: spec for spec in DATASET_SPECS}
NORMALIZE_PATTERN = re.compile(r"[^0-9a-zA-Z]+")
NUMERIC_COLUMNS = ("estimate", "ci_low", "ci_high", "n", "n_unweighted")


@dataclass
class DataBundle:
    """Container holding the loaded survey outputs and any errors."""

    frames: Dict[str, Optional[pd.DataFrame]]
    errors: Dict[str, str]
    base_path: Path

    def get(self, name: str) -> Optional[pd.DataFrame]:
        return self.frames.get(name)

    @property
    def indicators_overall(self) -> Optional[pd.DataFrame]:
        return self.get("indicators_overall")

    @property
    def subgroups_household(self) -> Optional[pd.DataFrame]:
        return self.get("subgroups_household_latest")

    @property
    def subgroups_provider(self) -> Optional[pd.DataFrame]:
        return self.get("subgroups_provider_latest")

    @property
    def state_heatmap(self) -> Optional[pd.DataFrame]:
        return self.get("state_indicator_heatmap_latest")

    @property
    def total(self) -> int:
        return len(self.frames)

    @property
    def loaded(self) -> int:
        return sum(df is not None for df in self.frames.values())

    def has_data(self) -> bool:
        return any(df is not None for df in self.frames.values())


def get_project_root() -> Path:
    """Resolve the repository root based on this file's location."""
    return Path(__file__).resolve().parents[2]


def _normalize_columns(columns: Iterable[str]) -> list[str]:
    return [NORMALIZE_PATTERN.sub("_", col.strip().lower()).strip("_") for col in columns]


def _standardize_dataframe(df: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
    if df.empty:
        return df
    normalized = df.copy()
    normalized.columns = _normalize_columns(normalized.columns)
    for column in spec.ensure_columns:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    if spec.frame:
        normalized["frame"] = spec.frame
    for col in NUMERIC_COLUMNS:
        if col in normalized.columns:
            normalized[col] = pd.to_numeric(normalized[col], errors="coerce")
    if "survey_month" in normalized.columns:
        normalized["survey_month"] = pd.to_datetime(
            normalized["survey_month"], errors="coerce"
        )
    if "wave_end_date" in normalized.columns:
        normalized["wave_end_date"] = pd.to_datetime(
            normalized["wave_end_date"], errors="coerce"
        )
    return normalized


def _load_dataset(spec: DatasetSpec, base_path: Path) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    csv_path = base_path / spec.relative_path
    if not csv_path.exists():
        return None, (
            f"Missing {spec.name} data at '{spec.relative_path}'. "
            f"Run `{DATA_BOOTSTRAP_COMMAND}` to seed demo-ready CSVs."
        )
    try:
        parse_dates = list(spec.parse_dates) if spec.parse_dates else None
        frame = pd.read_csv(csv_path, parse_dates=parse_dates)
    except Exception as exc:  # pragma: no cover - surfaced in the UI
        return None, f"Failed to read {csv_path.name}: {exc}"
    return _standardize_dataframe(frame, spec), None


def _build_bundle(base_path: Path) -> DataBundle:
    frames: Dict[str, Optional[pd.DataFrame]] = {}
    errors: Dict[str, str] = {}
    for spec in DATASET_SPECS:
        frame, error = _load_dataset(spec, base_path)
        frames[spec.name] = frame
        if error:
            errors[spec.name] = error
    return DataBundle(frames=frames, errors=errors, base_path=base_path)


@lru_cache(maxsize=4)
def _load_all_datasets_cached(base_path_str: str) -> DataBundle:
    return _build_bundle(Path(base_path_str))


def load_all_datasets(base_path: Optional[Path] = None, use_cache: bool = True) -> DataBundle:
    """Load every dashboard dataset, optionally caching the result."""
    root = Path(base_path) if base_path else get_project_root()
    root = root.resolve()
    if use_cache:
        return _load_all_datasets_cached(str(root))
    return _build_bundle(root)


def load_all_data(base_path: Optional[Path] = None, use_cache: bool = True) -> DataBundle:
    """Public alias preferred by the dashboard components."""
    return load_all_datasets(base_path=base_path, use_cache=use_cache)


def _prepare_wave_sort(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    if "survey_month" in working.columns:
        working["survey_month"] = pd.to_datetime(working["survey_month"], errors="coerce")
    if "wave_end_date" in working.columns:
        working["wave_end_date"] = pd.to_datetime(working["wave_end_date"], errors="coerce")
    if "wave" in working.columns:
        working["wave"] = pd.to_numeric(working["wave"], errors="coerce")
    return working


def get_latest_wave(frame: Optional[pd.DataFrame], *, match_frame: Optional[str] = None) -> Optional[pd.Series]:
    """Return the latest row for an optional frame filter."""
    if frame is None or frame.empty:
        return None
    working = _prepare_wave_sort(frame)
    if match_frame and "frame" in working.columns:
        mask = working["frame"].astype(str).str.lower() == match_frame.lower()
        working = working[mask]
    if working.empty:
        return None
    sort_cols = [col for col in ("survey_month", "wave_end_date", "wave") if col in working.columns]
    working = working.sort_values(sort_cols) if sort_cols else working
    return working.iloc[-1]


def infer_latest_wave(frame: Optional[pd.DataFrame]) -> Optional[pd.Series]:
    """Return the most recent row in ``frame`` based on wave/date metadata."""
    return get_latest_wave(frame)


def latest_wave_summary(indicators: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Return a tidy summary of the latest wave per frame."""
    if indicators is None or indicators.empty:
        return pd.DataFrame(
            columns=["frame", "wave", "survey_month", "survey_label"]
        )
    working = _prepare_wave_sort(indicators)
    if "frame" not in working.columns:
        return pd.DataFrame(
            columns=["frame", "wave", "survey_month", "survey_label"]
        )
    sort_cols = [col for col in ("survey_month", "wave") if col in working.columns]
    if not sort_cols:
        sort_cols = ["wave"] if "wave" in working.columns else []
    working = working.sort_values(sort_cols) if sort_cols else working
    latest_rows = working.groupby("frame", dropna=True).tail(1)
    summary = latest_rows[[col for col in ("frame", "wave", "survey_month") if col in latest_rows.columns]].copy()
    if "survey_month" in summary.columns:
        summary["survey_month"] = pd.to_datetime(summary["survey_month"], errors="coerce")
        summary["survey_label"] = summary["survey_month"].dt.strftime("%b %Y")
    else:
        summary["survey_label"] = summary.get("wave", pd.Series(dtype="object"))
    return summary.reset_index(drop=True)


__all__ = [
    "DataBundle",
    "DatasetSpec",
    "DATASET_SPECS",
    "DATA_BOOTSTRAP_COMMAND",
    "get_latest_wave",
    "infer_latest_wave",
    "latest_wave_summary",
    "load_all_data",
    "load_all_datasets",
]
