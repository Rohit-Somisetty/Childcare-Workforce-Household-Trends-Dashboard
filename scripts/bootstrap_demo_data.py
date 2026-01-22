"""Generate demo-ready CSVs for the dashboard data layer."""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

SEED = 42
WAVES = [
    (1, "2024-01-31"),
    (2, "2024-02-29"),
    (3, "2024-03-31"),
]
HOUSEHOLD_INDICATORS = [
    "stress_mean",
    "stress_high_pct",
    "food_insecurity_pct",
    "childcare_difficulty_high_pct",
    "employment_disruption_pct",
]
PROVIDER_INDICATORS = [
    "stress_mean",
    "stress_high_pct",
    "staff_shortage_pct",
    "closure_risk_high_pct",
]
SUBGROUP_TYPES = {
    "household": {
        "income_bracket": ["Low", "Middle", "High"],
        "race_ethnicity": ["Black", "Latinx", "White"],
        "urbanicity": ["Urban", "Suburban", "Rural"],
        "state": ["CA", "TX", "NY"],
    },
    "provider": {
        "provider_setting": ["Center", "Home", "Head Start"],
        "urbanicity": ["Urban", "Suburban", "Rural"],
        "state": ["CA", "IL", "WA"],
    },
}
STATE_LIST = ["CA", "TX", "NY", "IL", "WA", "GA"]
REQUIRED_OUTPUTS = [
    "indicators_overall.csv",
    "subgroups_household_latest.csv",
    "subgroups_provider_latest.csv",
    "state_indicator_heatmap_latest.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap demo CSVs for the dashboard")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root to seed (defaults to repository root)",
    )
    return parser.parse_args()


def find_demo_sources(base_dir: Path) -> Dict[str, Path]:
    demo_dir = base_dir / "docs" / "demo_dashboard"
    sources: Dict[str, Path] = {}
    if not demo_dir.exists():
        return sources
    for filename in REQUIRED_OUTPUTS:
        matches = list(demo_dir.rglob(Path(filename).name))
        if matches:
            sources[filename] = matches[0]
    return sources


def copy_from_demo(base_dir: Path, outputs_dir: Path) -> bool:
    sources = find_demo_sources(base_dir)
    copied_any = False
    for filename, source in sources.items():
        dest = outputs_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source.read_bytes())
        copied_any = True
        print(f"Copied demo artifact {source} -> {dest}")
    return copied_any


def _base_estimate(indicator: str, frame: str) -> float:
    base_map = {
        "stress_mean": 22.0 if frame == "household" else 20.0,
        "stress_high_pct": 0.4 if frame == "household" else 0.25,
        "food_insecurity_pct": 0.27,
        "childcare_difficulty_high_pct": 0.45,
        "employment_disruption_pct": 0.2,
        "staff_shortage_pct": 0.35,
        "closure_risk_high_pct": 0.3,
    }
    return base_map.get(indicator, 0.2)


def _generate_estimate(rng: random.Random, indicator: str, frame: str) -> float:
    base_value = _base_estimate(indicator, frame)
    shift = rng.uniform(-0.03, 0.03)
    value = base_value + shift
    if indicator.endswith("_pct"):
        value = max(0.05, min(0.9, value))
    return round(value, 4)


def build_indicator_rows(frame: str, indicators: Iterable[str]) -> List[dict]:
    rng = random.Random(SEED + (0 if frame == "household" else 100))
    rows: List[dict] = []
    for wave_id, wave_end_date in WAVES:
        for indicator in indicators:
            estimate = _generate_estimate(rng, indicator, frame)
            interval = 0.03 if indicator.endswith("_pct") else 0.8
            row = {
                "frame": frame,
                "indicator": indicator,
                "indicator_name": indicator,
                "wave": wave_id,
                "survey_month": wave_end_date,
                "wave_end_date": wave_end_date,
                "estimate": estimate,
                "ci_low": round(max(0, estimate - interval), 4),
                "ci_high": round(min(1 if indicator.endswith("_pct") else 40, estimate + interval), 4),
                "n_unweighted": 2500 if frame == "household" else 1600,
                "n_effective": 2000 if frame == "household" else 1400,
            }
            rows.append(row)
    return rows


def build_subgroup_rows(frame: str, indicators: Iterable[str]) -> List[dict]:
    rng = random.Random(SEED + (200 if frame == "household" else 400))
    rows: List[dict] = []
    subgroups = SUBGROUP_TYPES[frame]
    for wave_id, wave_end_date in WAVES[-1:]:  # latest wave snapshot
        for indicator in indicators:
            base = _generate_estimate(rng, indicator, frame)
            for subgroup_type, values in subgroups.items():
                for subgroup_value in values:
                    noise = rng.uniform(-0.05, 0.05)
                    estimate = base + noise
                    if indicator.endswith("_pct"):
                        estimate = max(0.05, min(0.95, estimate))
                    row = {
                        "frame": frame,
                        "indicator": indicator,
                        "indicator_name": indicator,
                        "wave": wave_id,
                        "survey_month": wave_end_date,
                        "wave_end_date": wave_end_date,
                        "subgroup_type": subgroup_type,
                        "subgroup": subgroup_value,
                        "subgroup_value": subgroup_value,
                        "estimate": round(estimate, 4),
                        "ci_low": round(max(0, estimate - 0.04), 4),
                        "ci_high": round(min(1 if indicator.endswith("_pct") else 40, estimate + 0.04), 4),
                        "n_unweighted": rng.randint(200, 800),
                        "n_effective": rng.randint(150, 600),
                    }
                    rows.append(row)
    return rows


def build_state_rows() -> List[dict]:
    rng = random.Random(SEED + 600)
    rows: List[dict] = []
    for frame, indicators in (("household", HOUSEHOLD_INDICATORS), ("provider", PROVIDER_INDICATORS)):
        for wave_id, wave_end_date in WAVES[-1:]:
            for state in STATE_LIST:
                for indicator in indicators:
                    base = _generate_estimate(rng, indicator, frame)
                    noise = rng.uniform(-0.03, 0.03)
                    estimate = base + noise
                    if indicator.endswith("_pct"):
                        estimate = max(0.05, min(0.95, estimate))
                    rows.append(
                        {
                            "frame": frame,
                            "indicator": indicator,
                            "indicator_name": indicator,
                            "wave": wave_id,
                            "survey_month": wave_end_date,
                            "wave_end_date": wave_end_date,
                            "state": state,
                            "estimate": round(estimate, 4),
                            "ci_low": round(max(0, estimate - 0.03), 4),
                            "ci_high": round(min(1 if indicator.endswith("_pct") else 40, estimate + 0.03), 4),
                            "n_unweighted": rng.randint(80, 300),
                            "n_effective": rng.randint(70, 250),
                        }
                    )
    return rows


def generate_synthetic(outputs_dir: Path) -> None:
    outputs_dir.mkdir(parents=True, exist_ok=True)

    indicators = build_indicator_rows("household", HOUSEHOLD_INDICATORS) + build_indicator_rows(
        "provider", PROVIDER_INDICATORS
    )
    pd.DataFrame(indicators).to_csv(outputs_dir / "indicators_overall.csv", index=False)

    pd.DataFrame(build_subgroup_rows("household", HOUSEHOLD_INDICATORS)).to_csv(
        outputs_dir / "subgroups_household_latest.csv", index=False
    )
    pd.DataFrame(build_subgroup_rows("provider", PROVIDER_INDICATORS)).to_csv(
        outputs_dir / "subgroups_provider_latest.csv", index=False
    )
    pd.DataFrame(build_state_rows()).to_csv(outputs_dir / "state_indicator_heatmap_latest.csv", index=False)
    print(f"Synthetic demo data written to {outputs_dir}")


def ensure_outputs(base_dir: Path) -> None:
    outputs_dir = base_dir / "data" / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    copied = copy_from_demo(base_dir, outputs_dir)
    missing = [name for name in REQUIRED_OUTPUTS if not (outputs_dir / name).exists()]
    if missing:
        print("Generating synthetic demo CSVs for:", ", ".join(missing))
        generate_synthetic(outputs_dir)
    elif copied:
        print("All required CSVs already exist via demo copies.")
    else:
        print("Demo CSVs already present; no action taken.")


def main() -> None:
    args = parse_args()
    ensure_outputs(args.base_dir)


if __name__ == "__main__":
    main()
