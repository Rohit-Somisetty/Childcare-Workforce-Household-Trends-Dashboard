st.caption("Upcoming: ranked state tables and choropleth-style summaries.")
st.info("State-level indicators will display once the underlying visual components are added.")
"""State explorer with ranked tables and optional heatmap embed."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st

from utils.filters import filter_latest_wave, indicator_kind
from utils.formatters import format_ci, format_num, format_pct
from utils.load_data import RUN_PIPELINE_COMMAND, load_all_data

FRAME_INDICATORS: Dict[str, List[dict]] = {
	"household": [
		{"value": "stress_mean", "label": "Avg. stress"},
		{"value": "stress_high_pct", "label": "High stress"},
		{"value": "food_insecurity_pct", "label": "Food insecurity"},
		{
			"value": "childcare_difficulty_high_pct",
			"label": "Childcare difficulty",
		},
		{
			"value": "employment_disruption_pct",
			"label": "Employment disruption",
		},
	],
	"provider": [
		{"value": "stress_mean", "label": "Avg. stress"},
		{"value": "stress_high_pct", "label": "High stress"},
		{"value": "staff_shortage_pct", "label": "Staff shortages"},
		{"value": "closure_risk_high_pct", "label": "Closure risk"},
	],
}


def _load_state_dataframe(bundle) -> pd.DataFrame:
	if bundle.state_heatmap is not None and not bundle.state_heatmap.empty:
		return bundle.state_heatmap.copy()

	frames: List[pd.DataFrame] = []
	for frame_name, df in (
		("household", bundle.subgroups_household),
		("provider", bundle.subgroups_provider),
	):
		if df is None or df.empty or "subgroup_type" not in df.columns:
			continue
		mask = df["subgroup_type"].astype(str).str.lower() == "state"
		subset = df[mask].copy()
		if subset.empty:
			continue
		if "state" not in subset.columns:
			if "subgroup" in subset.columns:
				subset["state"] = subset["subgroup"]
			elif "subgroup_value" in subset.columns:
				subset["state"] = subset["subgroup_value"]
		subset["frame"] = frame_name
		frames.append(subset)
	if frames:
		return pd.concat(frames, ignore_index=True)
	return pd.DataFrame()


def _format_value(value: float, kind: str) -> str:
	return format_pct(value) if kind == "pct" else format_num(value)


st.title("State Explorer")
st.caption("Rank states by household and provider indicators, or review the heatmap asset.")

bundle = load_all_data()
if bundle.errors:
	st.warning(
		"Some survey outputs are missing. Run "
		f"`{RUN_PIPELINE_COMMAND}` to regenerate the required CSV exports."
	)
	for name, error in bundle.errors.items():
		st.caption(f"• {name}: {error}")

state_df = _load_state_dataframe(bundle)
if state_df.empty:
	st.info("State-level indicators are unavailable. Re-run the pipeline to refresh outputs.")
	st.stop()

frame_choice = st.selectbox("Frame", options=list(FRAME_INDICATORS.keys()), format_func=str.capitalize)
indicator_options = FRAME_INDICATORS[frame_choice]
indicator_map = {item["value"]: item for item in indicator_options}
indicator_choice = st.selectbox(
	"Indicator",
	options=list(indicator_map.keys()),
	format_func=lambda key: indicator_map[key]["label"],
)
view_mode = st.radio("View mode", options=["Ranked table", "Heatmap image"], index=0)

latest_df = filter_latest_wave(state_df, frame_choice, bundle.indicators_overall)
if "indicator" not in latest_df.columns or "state" not in latest_df.columns:
	st.info("State dataset is missing indicator or state columns.")
	st.stop()

filtered = latest_df[latest_df["indicator"] == indicator_choice].copy()
filtered = filtered.dropna(subset=["estimate"])

if filtered.empty:
	st.info("No state rows found for this indicator.")
	st.stop()

kind = indicator_kind(indicator_choice)
ranked = filtered.sort_values("estimate", ascending=False)
top_states = ranked.head(10)
bottom_states = ranked.tail(10).sort_values("estimate")

col_top, col_bottom = st.columns(2)
col_top.markdown("**Top 10 states**")
col_bottom.markdown("**Bottom 10 states**")

def _summarize(df: pd.DataFrame) -> pd.DataFrame:
	base_cols = [col for col in ("state", "estimate", "ci_low", "ci_high", "n_unweighted") if col in df.columns]
	summary = df[base_cols].copy()
	summary["Estimate"] = summary["estimate"].apply(lambda val: _format_value(val, kind))
	summary["95% CI"] = summary.apply(
		lambda row: format_ci(row.get("estimate"), row.get("ci_low"), row.get("ci_high"), kind=kind),
		axis=1,
	)
	if "n_unweighted" in summary.columns:
		summary["n_unweighted"] = summary["n_unweighted"].round().astype("Int64")
	display_cols = ["state", "Estimate", "95% CI"]
	if "n_unweighted" in summary.columns:
		display_cols.append("n_unweighted")
	return summary[display_cols]

col_top.dataframe(_summarize(top_states), use_container_width=True)
col_bottom.dataframe(_summarize(bottom_states), use_container_width=True)

if view_mode == "Ranked table":
	search_query = st.text_input("Search state")
	table_df = ranked.copy()
	if search_query:
		mask = table_df["state"].astype(str).str.contains(search_query, case=False, na=False)
		table_df = table_df[mask]
	table_df["Estimate"] = table_df["estimate"].apply(lambda val: _format_value(val, kind))
	table_df["95% CI"] = table_df.apply(
		lambda row: format_ci(row.get("estimate"), row.get("ci_low"), row.get("ci_high"), kind=kind),
		axis=1,
	)
	if "survey_month" in table_df.columns:
		table_df["survey_month"] = pd.to_datetime(table_df["survey_month"], errors="coerce").dt.strftime("%Y-%m")
	display_columns = ["state", "Estimate", "95% CI"]
	for column in ("n_unweighted", "n_effective", "wave", "survey_month"):
		if column in table_df.columns:
			display_columns.append(column)
	st.markdown("**Full ranking**")
	st.dataframe(table_df[display_columns], use_container_width=True)
	csv_bytes = table_df.to_csv(index=False).encode("utf-8")
	st.download_button(
		label="Download filtered CSV",
		data=csv_bytes,
		file_name=f"state_ranking_{frame_choice}_{indicator_choice}.csv",
		mime="text/csv",
	)
else:
	heatmap_path = Path(bundle.base_path) / "reports" / "figures" / "state_heatmap.png"
	if heatmap_path.exists():
		st.image(str(heatmap_path), caption="State indicator heatmap from latest pipeline run.")
	else:
		st.info(
			"Heatmap asset not found. Run the pipeline ("
			f"`{RUN_PIPELINE_COMMAND}`) and check reports/figures for exported images."
		)
