"""
Standalone script to export tod_projects.json (no numpy/shapely).
Run from project root: python tod-viz-viewer/scripts/export_tod_only.py
"""

import csv
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOD_VIZ_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = TOD_VIZ_DIR.parent


def _infer_tod_type(notes: str) -> str:
    """Infer TOD type from notes for tooltip display."""
    n = notes.lower()
    if "affordable" in n:
        return "Affordable"
    if "mixed-use" in n or "residential/retail" in n:
        return "Mixed-use"
    if "intermodal" in n or "transit center" in n:
        return "Transit/Station"
    if "commercial" in n or "hq" in n or "retail" in n:
        return "Commercial"
    if "residential" in n or "units" in n or "apartments" in n or "condos" in n:
        return "Residential"
    return "Mixed"


def main() -> None:
    output_dir = TOD_VIZ_DIR / "public" / "data"
    csv_path = PROJECT_ROOT / "tod_projects_locations.csv"
    out_path = output_dir / "tod_projects.json"

    projects = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            notes = row.get("notes", "")
            tod_type = row.get("tod_type", "").strip() or _infer_tod_type(notes)
            projects.append(
                {
                    "year": int(row["year"]),
                    "name": row["name"],
                    "address": row["address"],
                    "city": row["city"],
                    "state": row["state"],
                    "zip": row["zip"],
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "notes": notes,
                    "source": row["source"],
                    "tod_type": tod_type,
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)
    print(f"Exported {len(projects)} TOD projects to {out_path}")


if __name__ == "__main__":
    main()
