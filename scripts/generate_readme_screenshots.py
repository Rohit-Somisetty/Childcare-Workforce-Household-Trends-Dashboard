"""Generate placeholder PNG screenshots for the dashboard README."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

SCREEN_CONFIG: Dict[str, Dict[str, List[str]]] = {
    "overview.png": {
        "title": "Overview KPIs",
        "bullets": [
            "Household + provider stress",
            "CI ribbons + delta vs. prior",
            "Top narrative insights",
        ],
    },
    "trends.png": {
        "title": "Trends View",
        "bullets": [
            "Indicator selector",
            "Line chart with CI band",
            "Sample sizes per wave",
        ],
    },
    "subgroups.png": {
        "title": "Subgroups Explorer",
        "bullets": [
            "Household vs provider split",
            "Sortable bar chart",
            "n / n_eff callouts",
        ],
    },
    "state_explorer.png": {
        "title": "State Explorer",
        "bullets": [
            "Top/bottom 10 states",
            "Search + CSV export",
            "Heatmap placeholder",
        ],
    },
}


def _draw_card(filename: str, title: str, bullets: List[str], output_dir: Path) -> None:
    image = Image.new("RGB", (1280, 720), color=(16, 45, 80))
    draw = ImageDraw.Draw(image)
    draw.rectangle(((40, 40), (1240, 680)), outline=(255, 255, 255), width=4)
    font = ImageFont.load_default()
    draw.text((80, 80), title, fill=(255, 255, 255), font=font)
    for index, bullet in enumerate(bullets, start=1):
        draw.text((120, 140 + index * 60), f"• {bullet}", fill=(200, 230, 255), font=font)
    output_path = (output_dir / filename).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(f"Created {output_path}")


def main() -> None:
    screenshots_dir = Path("docs/demo_dashboard/screenshots")
    for filename, meta in SCREEN_CONFIG.items():
        _draw_card(filename, meta["title"], meta["bullets"], screenshots_dir)


if __name__ == "__main__":
    main()
