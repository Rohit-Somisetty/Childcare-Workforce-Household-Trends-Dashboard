"""Entry point for the Childcare Workforce & Household Trends Streamlit app."""

from __future__ import annotations

import streamlit as st

from utils.formatters import format_wave_heading
from utils.load_data import (
    RUN_PIPELINE_COMMAND,
    infer_latest_wave,
    load_all_data,
)

st.set_page_config(
    page_title="Childcare Workforce & Household Trends",
    layout="wide",
    page_icon=":bar_chart:",
)


def main() -> None:
    st.title("Childcare Workforce & Household Trends Dashboard")
    st.caption("Explore caregiver well-being, household stability, and provider workforce strain.")

    data_bundle = load_all_data()
    success_message = f"Loaded {data_bundle.loaded} of {data_bundle.total} expected datasets."
    st.info(success_message)

    if data_bundle.errors:
        st.warning(
            "Some survey outputs are missing. Generate them via "
            f"`{RUN_PIPELINE_COMMAND}` before exploring the full dashboard."
        )
        for dataset_name, error in data_bundle.errors.items():
            st.caption(f"• {dataset_name}: {error}")
    else:
        st.success("All datasets are available. You're ready to explore!")

    st.divider()
    latest_wave = infer_latest_wave(data_bundle.get("indicators_overall"))
    if latest_wave is not None:
        wave_heading = format_wave_heading(
            latest_wave.get("wave_label") or latest_wave.get("wave"),
            latest_wave.get("wave_end_date"),
        )
        st.subheader("Latest wave snapshot")
        st.metric("Reporting wave", wave_heading)
        with st.expander("Preview of latest wave inputs", expanded=False):
            st.dataframe(latest_wave.to_frame().T, use_container_width=True)
    else:
        st.info(
            "Upload or generate survey outputs to unlock the overview, trends, and comparative pages."
        )

    st.divider()
    st.write(
        "Use the left-hand navigation to open Overview, Trends, Subgroups, and State Explorer pages."
    )


if __name__ == "__main__":
    main()
