st.caption("Interactive trend lines with confidence intervals will be available soon.")
st.info("Use the Overview page to confirm data availability while build-out continues.")
"""Interactive trends page with CI ribbons."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatters import format_num, format_pct
from utils.load_data import RUN_PIPELINE_COMMAND, load_all_data

FRAME_INDICATORS: Dict[str, List[dict]] = {
	"household": [
		{"indicator": "stress_mean", "label": "Avg. stress", "kind": "num"},
		{"indicator": "stress_high_pct", "label": "High stress", "kind": "pct"},
		{"indicator": "food_insecurity_pct", "label": "Food insecurity", "kind": "pct"},
		{
			"indicator": "childcare_difficulty_high_pct",
			"label": "Childcare difficulty",
			"kind": "pct",
		},
		{"indicator": "employment_disruption_pct", "label": "Employment disruption", "kind": "pct"},
	],
	"provider": [
		{"indicator": "stress_mean", "label": "Avg. stress", "kind": "num"},
		{"indicator": "stress_high_pct", "label": "High stress", "kind": "pct"},
		{"indicator": "staff_shortage_pct", "label": "Staff shortages", "kind": "pct"},
		{"indicator": "closure_risk_high_pct", "label": "Closure risk", "kind": "pct"},
	],
}


def _format_value(value: float, kind: str) -> str:
	return format_pct(value) if kind == "pct" else format_num(value)


def _prepare_series(df: pd.DataFrame, frame: str, indicator: str) -> pd.DataFrame:
	if "frame" not in df.columns or "indicator" not in df.columns:
		return pd.DataFrame()
	subset = df[
		(df["frame"].astype(str).str.lower() == frame)
		& (df["indicator"] == indicator)
	].copy()
	if subset.empty:
		return subset
	if "survey_month" in subset.columns:
		subset["survey_month"] = pd.to_datetime(subset["survey_month"], errors="coerce")
	if "wave" in subset.columns:
		subset["wave"] = pd.to_numeric(subset["wave"], errors="coerce")
	sort_cols = [col for col in ("survey_month", "wave") if col in subset.columns]
	subset = subset.sort_values(sort_cols) if sort_cols else subset.reset_index(drop=True)
	if "survey_month" in subset.columns:
		subset["x_axis"] = subset["survey_month"]
	elif "wave_end_date" in subset.columns:
		subset["x_axis"] = pd.to_datetime(subset["wave_end_date"], errors="coerce")
	elif "wave" in subset.columns:
		subset["x_axis"] = subset["wave"]
	else:
		subset["x_axis"] = range(len(subset))
	return subset


st.title("Trends Over Time")
st.caption("Trace each indicator across waves with optional confidence intervals.")

bundle = load_all_data()
if bundle.errors:
	st.warning(
		"Some survey outputs are missing. Run "
		f"`{RUN_PIPELINE_COMMAND}` to regenerate the required CSVs."
	)
	for name, error in bundle.errors.items():
		st.caption(f"• {name}: {error}")

indicators_df = bundle.indicators_overall
if indicators_df is None or indicators_df.empty:
	st.info("Indicators not available yet. Generate survey outputs to explore trends.")
	st.stop()

frame_choice = st.selectbox("Select frame", options=list(FRAME_INDICATORS.keys()), format_func=lambda key: key.capitalize())
indicator_options = FRAME_INDICATORS[frame_choice]
indicator_map = {item["indicator"]: item for item in indicator_options}
available_indicators = [item["indicator"] for item in indicator_options]
indicator_choice = st.selectbox(
	"Select indicator",
	options=available_indicators,
	format_func=lambda key: indicator_map[key]["label"],
)
show_ci = st.toggle("Show 95% CI band", value=True)

series = _prepare_series(indicators_df, frame_choice, indicator_choice)
if series.empty:
	st.info("No trend data available for this indicator yet.")
	st.stop()

kind = indicator_map[indicator_choice]["kind"]
x_values = series["x_axis"].fillna(series.get("wave"))
hover_texts = []
for _, row in series.iterrows():
	timestamp = row.get("survey_month")
	if pd.notna(timestamp):
		wave_label = timestamp.strftime("%b %Y")
	else:
		wave_label = f"Wave {row.get('wave')}"
	ci_present = pd.notna(row.get("ci_low")) and pd.notna(row.get("ci_high"))
	ci_text = (
		f"95% CI {_format_value(row['ci_low'], kind)}-{_format_value(row['ci_high'], kind)}"
		if ci_present
		else ""
	)
	hover_bits = [f"{indicator_map[indicator_choice]['label']} {_format_value(row['estimate'], kind)}", wave_label]
	if ci_text:
		hover_bits.append(ci_text)
	if pd.notna(row.get("n_unweighted")):
		hover_bits.append(f"n={int(float(row['n_unweighted']))}")
	if pd.notna(row.get("n_effective")):
		hover_bits.append(f"n_eff={int(float(row['n_effective']))}")
	hover_texts.append("<br>".join(hover_bits))

fig = go.Figure()
if show_ci and {"ci_low", "ci_high"}.issubset(series.columns):
	ci_df = series.dropna(subset=["ci_low", "ci_high"])
	if not ci_df.empty:
		ci_x = list(ci_df["x_axis"]) + list(ci_df["x_axis"][::-1])
		ci_y = list(ci_df["ci_high"]) + list(ci_df["ci_low"][::-1])
		fig.add_trace(
			go.Scatter(
				x=ci_x,
				y=ci_y,
				fill="toself",
				fillcolor="rgba(99,110,250,0.15)",
				line=dict(color="rgba(0,0,0,0)"),
				hoverinfo="skip",
				name="95% CI",
				showlegend=True,
			)
		)

fig.add_trace(
	go.Scatter(
		x=x_values,
		y=series["estimate"],
		mode="lines+markers",
		name="Estimate",
		hovertemplate="%{text}<extra></extra>",
		text=hover_texts,
	)
)

fig.update_layout(
	margin=dict(l=10, r=10, t=30, b=10),
	yaxis_title=indicator_map[indicator_choice]["label"],
	xaxis_title="Survey month" if series["x_axis"].dtype.kind == "M" else "Wave",
	template="plotly_white",
)

st.plotly_chart(fig, use_container_width=True)

table = series.copy()
if "survey_month" in table.columns:
	table["survey_month"] = table["survey_month"].dt.strftime("%Y-%m-%d")
display_columns = [col for col in ["survey_month", "wave", "estimate", "ci_low", "ci_high", "n_unweighted", "n_effective"] if col in table.columns]
st.markdown("**Underlying series**")
st.dataframe(table[display_columns], use_container_width=True)
