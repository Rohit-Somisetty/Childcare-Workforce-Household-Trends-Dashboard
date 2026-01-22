"""Generate lightweight demo exports for reviewer walkthroughs."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

PIPELINE_CMD = [
    "python",
    "src/run_pipeline.py",
    "--waves",
    "3",
    "--sample_size",
    "2000",
    "--seed",
    "42",
    "--out_dir",
    "reports",
]

FIGURE_LIMIT = 6


@dataclass(frozen=True)
class Artifact:
    source: Path
    destination: Path

    def exists(self) -> bool:
        return self.source.exists()


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_pipeline_outputs(root: Path, required: Iterable[Path]) -> None:
    missing = [path for path in required if not path.exists()]
    if not missing:
        return
    print("Missing artifacts detected, running lightweight pipeline...")
    subprocess.run(PIPELINE_CMD, cwd=root, check=True)


def copy_artifacts(artifacts: Iterable[Artifact]) -> None:
    for artifact in artifacts:
        artifact.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(artifact.source, artifact.destination)
        print(f"Copied {artifact.source} -> {artifact.destination}")


def copy_figures(figures_src: Path, figures_dest: Path) -> List[Path]:
    copied: List[Path] = []
    if not figures_src.exists():
        print("No figures directory found; skipping figure copy.")
        return copied
    figures_dest.mkdir(parents=True, exist_ok=True)
    png_files = sorted(figures_src.glob("*.png"))[:FIGURE_LIMIT]
    for png in png_files:
        target = figures_dest / png.name
        shutil.copy2(png, target)
        copied.append(target)
    if copied:
        print(f"Copied {len(copied)} figure(s) to {figures_dest}.")
    else:
        print("No PNG files were copied; ensure the reporting pipeline generated figures.")
    return copied


def write_demo_readme(dest_dir: Path) -> None:
    readme_path = dest_dir / "README_demo.md"
    content = f"""# Dashboard Demo Package\n\nThis folder contains lightweight exports for reviewers:\n\n- **Factsheet**: open `factsheet_latest.html` in a browser\n- **Narrative brief**: see `brief_latest.md`\n- **Figures**: PNG snapshots placed under `figures/`\n\n## Regenerate the demo package\n\n```bash\npython scripts/export_dashboard_demo.py\n```\n\nThis script will rerun a small version of the survey pipeline:\n\n```bash\n{' '.join(PIPELINE_CMD)}\n```\n\n## Run the interactive dashboard\n\n```bash\npython -m venv .venv\n.venv\\Scripts\\activate  # Windows\npip install -r requirements.txt\nstreamlit run dashboard/app.py\n```\n\nThe Streamlit pages will read the same Project 1 outputs that power these demo files.\n"""
    readme_path.write_text(content, encoding="utf-8")
    print(f"Wrote {readme_path}")


def main() -> None:
    root = get_repo_root()
    reports_dir = root / "reports"
    demo_dir = root / "docs" / "demo_dashboard"
    figures_demo_dir = demo_dir / "figures"
    screenshots_dir = demo_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    required_sources = [
        reports_dir / "brief_latest.md",
        reports_dir / "factsheet_latest.html",
    ]
    ensure_pipeline_outputs(root, required_sources)

    artifacts = [
        Artifact(source=reports_dir / "brief_latest.md", destination=demo_dir / "brief_latest.md"),
        Artifact(source=reports_dir / "factsheet_latest.html", destination=demo_dir / "factsheet_latest.html"),
    ]
    copy_artifacts(artifacts)
    copy_figures(reports_dir / "figures", figures_demo_dir)
    write_demo_readme(demo_dir)
    print("Demo export complete.")


if __name__ == "__main__":
    main()
