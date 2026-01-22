"""Overview page with KPI tiles and insights."""

from __future__ import annotations

import streamlit as st

from utils.formatters import NA_TEXT, format_ci, format_num, format_pct, safe_delta
from utils.insights import compute_kpis, compute_top_insights
from utils.load_data import DATA_BOOTSTRAP_COMMAND, load_all_data

HOUSEHOLD_KPIS = [
    {"indicator": "stress_mean", "label": "Avg. stress", "kind": "num"},
    {"indicator": "stress_high_pct", "label": "High stress", "kind": "pct"},
    {"indicator": "food_insecurity_pct", "label": "Food insecurity", "kind": "pct"},
    {"indicator": "childcare_difficulty_high_pct", "label": "Childcare difficulty", "kind": "pct"},
    {"indicator": "employment_disruption_pct", "label": "Employment disruption", "kind": "pct"},
]

PROVIDER_KPIS = [
    {"indicator": "stress_mean", "label": "Avg. stress", "kind": "num"},
    {"indicator": "stress_high_pct", "label": "High stress", "kind": "pct"},
    {"indicator": "staff_shortage_pct", "label": "Staff shortages", "kind": "pct"},
    {"indicator": "closure_risk_high_pct", "label": "Closure risk", "kind": "pct"},
]


def _format_estimate(value: float, kind: str) -> str:
    return format_pct(value) if kind == "pct" else format_num(value)


def _render_kpi_tiles(section_title: str, frame_key: str, configs: list[dict], kpi_df) -> None:
    st.subheader(section_title)
    st.caption(f"Latest reporting wave · {frame_key.capitalize()} cohort")
    if kpi_df.empty:
        st.info("Metrics will appear once survey outputs are available.")
        return
    lookup = {row["indicator"]: row for _, row in kpi_df.iterrows()}
    for start in range(0, len(configs), 4):
        cols = st.columns(min(4, len(configs) - start))
        for col, config in zip(cols, configs[start : start + 4]):
            row = lookup.get(config["indicator"])
            if row is None:
                col.metric(config["label"], NA_TEXT)
                continue
            kind = config["kind"]
            value_text = _format_estimate(row.get("estimate"), kind)
            delta_text = safe_delta(row.get("estimate"), row.get("prev_estimate"), kind)
            delta_value = None if delta_text == NA_TEXT else delta_text
            col.metric(config["label"], value=value_text, delta=delta_value)
            ci_text = format_ci(
                row.get("estimate"),
                row.get("ci_low"),
                row.get("ci_high"),
                kind=kind,
            )
            col.caption(ci_text)


st.title("Overview · Latest Wave Snapshot")
st.caption("Monitor household and provider well-being at a glance.")

bundle = load_all_data()
if bundle.errors:
    st.warning(
        "Some survey outputs are missing. Run "
        f"`{DATA_BOOTSTRAP_COMMAND}` to regenerate the required CSV exports."
    )
    for name, error in bundle.errors.items():
        st.caption(f"• {name}: {error}")

indicators = bundle.indicators_overall
if indicators is None or indicators.empty:
    st.info("Overall indicators not available yet. Generate survey outputs to see KPIs.")
    st.stop()

household_kpis = compute_kpis(indicators, "household", [cfg["indicator"] for cfg in HOUSEHOLD_KPIS])
provider_kpis = compute_kpis(indicators, "provider", [cfg["indicator"] for cfg in PROVIDER_KPIS])

_render_kpi_tiles("Households", "household", HOUSEHOLD_KPIS, household_kpis)
st.divider()
_render_kpi_tiles("Providers", "provider", PROVIDER_KPIS, provider_kpis)

st.divider()
st.subheader("Top insights")
insights = compute_top_insights(
    indicators,
    subgroups_household=bundle.subgroups_household,
    state_heatmap=bundle.state_heatmap,
)
if insights:
    for text in insights:
        st.markdown(f"- {text}")
else:
    st.info("Insights will populate after the next survey wave is ingested.")
