# Childcare Workforce & Household Trends Dashboard

This dashboard surfaces key indicators on caregiver well-being, employment stability, childcare access, and provider workforce strain. It is powered by the survey pipeline outputs generated in Project 1.

## Required data exports

The Streamlit app expects the following CSVs under `data/outputs/`:

- `indicators_overall.csv`
- `subgroups_household_latest.csv`
- `subgroups_provider_latest.csv`
- `state_indicator_heatmap_latest.csv`

If any dataset is missing, run the survey pipeline to regenerate them:

```bash
python src/run_pipeline.py --waves 12 --sample_size 25000 --seed 42
```

## Run the dashboard locally

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS / Linux
python -m pip install --upgrade pip
pip install -r requirements.txt
python src/run_pipeline.py --waves 12 --sample_size 25000 --seed 42
streamlit run dashboard/app.py
```

## Project layout

```
dashboard/
  app.py             # Main Streamlit entry point
  pages/             # Multi-page views (Overview, Trends, Subgroups, State Explorer)
  utils/             # Shared helpers (data loading, formatting, insights)
docs/
  dashboard_guide.md
```

## Dashboard pages

- **Overview** – KPI tiles plus narrative insights sourced from `indicators_overall.csv`.
- **Trends** – Plotly line charts with optional 95% CI ribbons using the same indicator feed.
- **Subgroups** – Bar charts + sortable tables powered by `subgroups_household_latest.csv` and `subgroups_provider_latest.csv`. The view automatically filters to the latest survey wave per frame.
- **State Explorer** – Ranked tables (and optional heatmap embed) derived from `state_indicator_heatmap_latest.csv`. If that export is missing, the app falls back to the state rows embedded inside the subgroup CSVs.

All pages read from the Project 1 pipeline outputs; rerun the pipeline whenever you need fresh survey waves:

```bash
python src/run_pipeline.py --waves 12 --sample_size 25000 --seed 42
```

The optional heatmap embed looks for `reports/figures/state_heatmap.png`. Regenerate it by running the pipeline or the reporting scripts in Project 1 before launching Streamlit.

## Next steps

- Capture representative screenshots and drop them in `dashboard/assets/` for review packets.
- Add automated checks for data freshness (e.g., alert when exports are older than N days).
- Wire Subgroups and State Explorer filters into any forthcoming download/reporting workflows.
