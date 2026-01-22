st.caption("Dynamic bar charts + sortable tables will land here shortly.")
st.info("Hang tight while subgroup indicators are wired to the new data loader.")
"""Interactive subgroup comparisons for households and providers."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.filters import filter_latest_wave, indicator_kind
from utils.formatters import format_ci, format_num, format_pct
from utils.load_data import RUN_PIPELINE_COMMAND, load_all_data

FRAME_CONFIG: Dict[str, Dict[str, List[dict]]] = {
	"household": {
		"indicators": [
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
		"subgroups": [
			{"value": "income_bracket", "label": "Income bracket"},
			{"value": "race_ethnicity", "label": "Race / ethnicity"},
			{"value": "urbanicity", "label": "Urbanicity"},
			{"value": "state", "label": "State"},
		],
	},
	"provider": {
		"indicators": [
			{"value": "stress_mean", "label": "Avg. stress"},
			{"value": "stress_high_pct", "label": "High stress"},
			{"value": "staff_shortage_pct", "label": "Staff shortages"},
			{"value": "closure_risk_high_pct", "label": "Closure risk"},
		],
		"subgroups": [
			{"value": "provider_setting", "label": "Provider setting"},
			{"value": "urbanicity", "label": "Urbanicity"},
			{"value": "state", "label": "State"},
		],
	},
}

SORT_OPTIONS = {
	"estimate": "Estimate (desc)",
	"n_unweighted": "Sample size (desc)",
}


def _label_column(df: pd.DataFrame) -> str:
	for column in ("subgroup", "subgroup_value", "state", "category"):
		if column in df.columns:
			return column
	return "subgroup"


def _format_value(value: float, kind: str) -> str:
	return format_pct(value) if kind == "pct" else format_num(value)


st.title("Subgroup Comparisons")
st.caption("Contrast latest-wave indicators by household or provider segments.")

bundle = load_all_data()
if bundle.errors:
	st.warning(
		"Some survey outputs are missing. Run "
		f"`{RUN_PIPELINE_COMMAND}` to regenerate the required CSV exports."
	)
	for name, error in bundle.errors.items():
		st.caption(f"• {name}: {error}")

frame_choice = st.selectbox("Frame", options=list(FRAME_CONFIG.keys()), format_func=str.capitalize)
indicator_options = FRAME_CONFIG[frame_choice]["indicators"]
indicator_map = {item["value"]: item for item in indicator_options}
indicator_choice = st.selectbox(
	"Indicator",
	options=list(indicator_map.keys()),
	format_func=lambda key: indicator_map[key]["label"],
)
subgroup_options = FRAME_CONFIG[frame_choice]["subgroups"]
subgroup_map = {item["value"]: item for item in subgroup_options}
subgroup_choice = st.selectbox(
	"Subgroup",
	options=list(subgroup_map.keys()),
	format_func=lambda key: subgroup_map[key]["label"],
)
top_n = st.slider("Top N segments", min_value=5, max_value=25, value=10, step=1)
sort_choice = st.selectbox(
	"Sort order",
	options=list(SORT_OPTIONS.keys()),
	format_func=lambda key: SORT_OPTIONS[key],
)
if subgroup_choice == "state":
	use_sample_sort = st.checkbox("Sort states by sample size", value=False)
	if use_sample_sort:
		sort_choice = "n_unweighted"

dataset = (
	bundle.subgroups_household if frame_choice == "household" else bundle.subgroups_provider
)

if dataset is None or dataset.empty:
	st.info("Subgroup datasets not available yet. Run the survey pipeline to populate them.")
	st.stop()

latest_df = filter_latest_wave(dataset, frame_choice, bundle.indicators_overall)
if latest_df.empty:
	st.info("Latest-wave subgroup rows not found for this frame.")
	st.stop()

working = latest_df.copy()
if "subgroup_type" in working.columns:
	subgroup_mask = working["subgroup_type"].astype(str).str.lower() == subgroup_choice
	working = working[subgroup_mask]
working = working[working["indicator"] == indicator_choice]
working = working.dropna(subset=["estimate"])

if working.empty:
	st.info("No subgroup rows for the selected indicator yet.")
	st.stop()

sort_field = sort_choice if sort_choice in working.columns else "estimate"
if working[sort_field].isna().all():
	sort_field = "estimate"
ordered = working.sort_values(sort_field, ascending=False)
chart_df = ordered.head(top_n).copy()
label_col = _label_column(chart_df)
chart_df[label_col] = chart_df[label_col].fillna("Unspecified")
label_display = subgroup_map[subgroup_choice]["label"]

kind = indicator_kind(indicator_choice)
multiplier = 100 if kind == "pct" else 1
chart_df["estimate_plot"] = chart_df["estimate"] * multiplier
if "ci_low" in chart_df.columns:
	chart_df["ci_low_plot"] = chart_df["ci_low"] * multiplier
else:
	chart_df["ci_low_plot"] = chart_df["estimate_plot"]
if "ci_high" in chart_df.columns:
	chart_df["ci_high_plot"] = chart_df["ci_high"] * multiplier
else:
	chart_df["ci_high_plot"] = chart_df["estimate_plot"]
chart_df["ci_high_plot"] = chart_df["ci_high_plot"].fillna(chart_df["estimate_plot"])
chart_df["ci_low_plot"] = chart_df["ci_low_plot"].fillna(chart_df["estimate_plot"])

error_plus = (chart_df["ci_high_plot"] - chart_df["estimate_plot"]).clip(lower=0)
error_minus = (chart_df["estimate_plot"] - chart_df["ci_low_plot"]).clip(lower=0)

hover_texts: List[str] = []
for _, row in chart_df.iterrows():
	pieces = [
		f"{label_display}: {row[label_col]}",
		f"Estimate: {_format_value(row['estimate'], kind)}",
		format_ci(row.get("estimate"), row.get("ci_low"), row.get("ci_high"), kind=kind),
	]
	if pd.notna(row.get("n_unweighted")):
		pieces.append(f"n={int(row['n_unweighted'])}")
	if pd.notna(row.get("n_effective")):
		pieces.append(f"n_eff={int(row['n_effective'])}")
	wave_label = row.get("survey_month")
	if pd.notna(wave_label):
		pieces.append(f"Month: {pd.to_datetime(wave_label).strftime('%b %Y')}")
	elif pd.notna(row.get("wave")):
		pieces.append(f"Wave {int(row['wave'])}")
	hover_texts.append("<br>".join(pieces))

fig = go.Figure(
	data=[
		go.Bar(
			x=chart_df["estimate_plot"],
			y=chart_df[label_col],
			orientation="h",
			error_x=dict(type="data", array=error_plus, arrayminus=error_minus),
			hovertemplate="%{text}<extra></extra>",
			text=hover_texts,
			marker_color="#1f77b4",
		)
	]
)
unit_label = "percentage points" if kind == "pct" else "value"
fig.update_layout(
	template="plotly_white",
	margin=dict(l=0, r=0, t=30, b=0),
	xaxis_title=f"{indicator_map[indicator_choice]['label']} ({unit_label})",
	yaxis=dict(autorange="reversed"),
)

st.plotly_chart(fig, use_container_width=True)

table_df = chart_df.copy()
table_df = table_df.rename(columns={label_col: label_display})
table_df["Estimate"] = table_df["estimate"].apply(lambda val: _format_value(val, kind))
table_df["95% CI"] = table_df.apply(
	lambda row: format_ci(row.get("estimate"), row.get("ci_low"), row.get("ci_high"), kind=kind),
	axis=1,
)
if "survey_month" in table_df.columns:
	table_df["survey_month"] = pd.to_datetime(table_df["survey_month"], errors="coerce").dt.strftime("%Y-%m")

display_columns = [label_display, "Estimate", "95% CI"]
for column in ("n_unweighted", "n_effective", "wave", "survey_month"):
	if column in table_df.columns:
		display_columns.append(column)

st.markdown("**Segment details**")
st.dataframe(table_df[display_columns], use_container_width=True)
