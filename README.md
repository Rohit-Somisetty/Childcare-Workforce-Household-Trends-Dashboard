# Childcare Workforce & Household Trends Dashboard

This repository hosts Project 2 for the childcare workforce analytics initiative: a Streamlit dashboard that visualizes household well-being, childcare access, and provider workforce strain using the survey pipeline outputs from Project 1.

## Quick Demo (No Install)

- Open the lightweight factsheet at [docs/demo_dashboard/factsheet_latest.html](docs/demo_dashboard/factsheet_latest.html) in your browser.
- Review the narrative brief at [docs/demo_dashboard/brief_latest.md](docs/demo_dashboard/brief_latest.md).
- Demo figures (up to six PNGs) and screenshot placeholders live in [docs/demo_dashboard/figures](docs/demo_dashboard/figures) and [docs/demo_dashboard/screenshots](docs/demo_dashboard/screenshots).
- Regenerate the demo bundle anytime via `python scripts/export_dashboard_demo.py`.

## Run the Dashboard

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python src/run_pipeline.py --waves 12 --sample_size 25000 --seed 42
streamlit run dashboard/app.py
```

Once the Streamlit server starts, use the sidebar to browse Overview, Trends, Subgroups, and State Explorer pages. Drop fresh screenshots into `docs/demo_dashboard/screenshots/` to keep reviewer packets up to date.

## Data Dependency

All visuals rely on the Project 1 CSV exports located in `data/outputs/` and the reporting artifacts under `reports/`. The command below regenerates every required file using the canonical survey configuration:

```bash
python src/run_pipeline.py --waves 12 --sample_size 25000 --seed 42
```

The demo exporter runs a smaller variant (`--waves 3 --sample_size 2000`) for quick smoke tests. Ensure these exports exist before committing dashboard changes or running CI.
