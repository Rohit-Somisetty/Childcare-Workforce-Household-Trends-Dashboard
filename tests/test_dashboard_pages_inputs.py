"""Input readiness checks for dashboard pages."""

from __future__ import annotations

import pytest

from dashboard.utils.load_data import load_all_data

SUBGROUP_COLUMNS = {"frame", "indicator", "subgroup_type", "estimate", "ci_low", "ci_high"}
STATE_COLUMNS = {"frame", "state", "indicator", "estimate"}


def test_subgroup_datasets_have_expected_columns() -> None:
    bundle = load_all_data()
    datasets = {
        "household": bundle.subgroups_household,
        "provider": bundle.subgroups_provider,
    }
    for name, df in datasets.items():
        if df is None or df.empty:
            pytest.skip(f"Subgroup dataset for {name} missing in this environment.")
        missing = SUBGROUP_COLUMNS - set(df.columns)
        assert not missing, f"{name} subgroup export missing columns: {sorted(missing)}"


def test_state_heatmap_has_indicator_columns() -> None:
    bundle = load_all_data()
    state_df = bundle.state_heatmap
    if state_df is None or state_df.empty:
        pytest.skip("State heatmap export unavailable in this environment.")
    missing = STATE_COLUMNS - set(state_df.columns)
    assert not missing, f"State heatmap missing columns: {sorted(missing)}"
