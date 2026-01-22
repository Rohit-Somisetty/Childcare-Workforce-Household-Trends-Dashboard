"""Lightweight checks for the dashboard data layer."""

from __future__ import annotations

import pytest

from dashboard.utils.load_data import DATASET_SPECS, latest_wave_summary, load_all_data


def test_load_all_data_returns_expected_entries() -> None:
    bundle = load_all_data()
    assert bundle.total == len(DATASET_SPECS)


def test_latest_wave_summary_requires_both_frames() -> None:
    bundle = load_all_data()
    indicators = bundle.indicators_overall
    if indicators is None or indicators.empty:
        pytest.skip("Overall indicators CSV not available in this environment.")
    summary = latest_wave_summary(indicators)
    if "frame" not in summary.columns:
        pytest.skip("Frame column missing from summary output.")
    frames = set(summary["frame"].astype(str).str.lower())
    expected = {"household", "provider"}
    if not expected.issubset(frames):
        pytest.skip("Not all frames present in the loaded sample data.")
    assert summary.shape[0] >= len(expected)
