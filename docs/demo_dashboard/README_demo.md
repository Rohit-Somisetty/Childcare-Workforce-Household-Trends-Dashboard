# Dashboard Demo Package

This folder contains lightweight exports for reviewers:

- **Factsheet**: open `factsheet_latest.html` in a browser
- **Narrative brief**: review `brief_latest.md`
- **Figures**: PNG snapshots will be placed under `figures/`

## Regenerate the demo package

```bash
python scripts/export_dashboard_demo.py
```

The helper script will rerun a tiny slice of the survey pipeline if artifacts are missing:

```bash
python src/run_pipeline.py --waves 3 --sample_size 2000 --seed 42 --out_dir reports
```

## Run the interactive dashboard

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
streamlit run dashboard/app.py
```

The Streamlit views read the same Project 1 outputs that power these demo files.
