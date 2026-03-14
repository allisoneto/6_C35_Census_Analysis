"""
Scan the output/ directory for visualization PNGs and generate manifest.json.

The manifest describes available chart types, sources (acs/decennial), variables,
transforms, and years. Used by the Svelte viewer to populate dropdowns and resolve
image paths.

Run from tod-viz-viewer/: python scripts/build_manifest.py
Output: public/manifest.json
"""

import json
import re
from pathlib import Path

# Output dir is ../output relative to tod-viz-viewer
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT.parent / "output"
MANIFEST_OUT = SCRIPT_DIR.parent / "public" / "manifest.json"


def _human_to_snake(name: str) -> str:
    """Convert Human_Readable_Name to snake_case for variable id."""
    return name.replace(" ", "_").replace("-", "_").lower()


def scan_choropleths() -> dict:
    """Scan maps/{source}/{Human_Name}/{transform}/*.png"""
    result = {"acs": {"variables": []}, "decennial": {"variables": []}}
    maps_dir = OUTPUT_DIR / "maps"
    if not maps_dir.exists():
        return result

    for source in ["acs", "decennial"]:
        source_dir = maps_dir / source
        if not source_dir.exists():
            continue

        # Collect: var_id -> {label, transforms: {transform: [years]}}
        var_data: dict[str, dict] = {}

        for human_dir in source_dir.iterdir():
            if not human_dir.is_dir() or human_dir.name == "boston_zoom":
                continue
            human_name = human_dir.name

            for transform_dir in human_dir.iterdir():
                if not transform_dir.is_dir():
                    continue
                # Skip boston_zoom subfolder for manifest (we use full region by default)
                if transform_dir.name == "boston_zoom":
                    continue
                transform = transform_dir.name

                for png in transform_dir.glob("*.png"):
                    # Pattern: {source}_{variable}_{transform}_{year}.png
                    # Variable can contain underscores (e.g. B01001_001E)
                    parts = png.stem.split("_")
                    if (
                        len(parts) >= 4
                        and parts[0] == source
                        and parts[-2] == transform
                        and parts[-1].isdigit()
                    ):
                        var_id = "_".join(parts[1:-2])
                        year = int(parts[-1])
                        if var_id not in var_data:
                            var_data[var_id] = {
                                "id": var_id,
                                "label": human_name.replace("_", " "),
                                "transforms": {},
                            }
                        if transform not in var_data[var_id]["transforms"]:
                            var_data[var_id]["transforms"][transform] = []
                        var_data[var_id]["transforms"][transform].append(year)

        # Convert to manifest format
        for var_id, data in var_data.items():
            all_years = set()
            transforms = []
            for t, years in data["transforms"].items():
                transforms.append(t)
                all_years.update(years)
            result[source]["variables"].append(
                {
                    "id": var_id,
                    "label": data["label"],
                    "transforms": sorted(transforms),
                    "years": sorted(all_years),
                }
            )

    return result


def scan_pie_charts() -> dict:
    """Scan pie_charts/{source}/{Human_Group}/{group}_agg_Ngeoids_{year}.png"""
    result = {"acs": {"variables": []}, "decennial": {"variables": []}}
    pie_dir = OUTPUT_DIR / "pie_charts"
    if not pie_dir.exists():
        return result

    for source in ["acs", "decennial"]:
        source_dir = pie_dir / source
        if not source_dir.exists():
            continue

        group_data: dict[str, dict] = {}

        for human_dir in source_dir.iterdir():
            if not human_dir.is_dir():
                continue
            human_name = human_dir.name

            for png in human_dir.glob("*.png"):
                # Pattern: {group}_agg_Ngeoids_{year}.png
                match = re.match(r"^(.+)_agg_\d+geoids_(\d{4})\.png$", png.name)
                if match:
                    group_id = match.group(1)
                    year = int(match.group(2))
                    if group_id not in group_data:
                        group_data[group_id] = {
                            "id": group_id,
                            "label": human_name.replace("_", " "),
                            "years": [],
                        }
                    group_data[group_id]["years"].append(year)

        for group_id, data in group_data.items():
            result[source]["variables"].append(
                {
                    "id": group_id,
                    "label": data["label"],
                    "years": sorted(set(data["years"])),
                }
            )

    return result


def scan_bar_charts() -> dict:
    """Scan bar_charts/{source}/{var}_{geoid_label}_{year}.png"""
    result = {"acs": {"variables": []}, "decennial": {"variables": []}}
    bar_dir = OUTPUT_DIR / "bar_charts"
    if not bar_dir.exists():
        return result

    for source in ["acs", "decennial"]:
        source_dir = bar_dir / source
        if not source_dir.exists():
            continue

        var_data: dict[str, dict] = {}

        for png in source_dir.glob("*.png"):
            # Pattern: {var}_n5geoids_{year}.png or similar
            match = re.match(r"^(.+)_n\d+geoids_(\d{4})\.png$", png.name)
            if match:
                var_id = match.group(1)
                year = int(match.group(2))
                if var_id not in var_data:
                    var_data[var_id] = {"id": var_id, "label": var_id, "years": []}
                var_data[var_id]["years"].append(year)

        for var_id, data in var_data.items():
            result[source]["variables"].append(
                {
                    "id": var_id,
                    "label": data["label"],
                    "years": sorted(set(data["years"])),
                }
            )

    return result


def scan_stacked_bar_charts() -> dict:
    """Scan stacked_bar_charts/{source}/{Human_Group}/{group}_nNgeoids_{year}.png"""
    result = {"acs": {"variables": []}, "decennial": {"variables": []}}
    stacked_dir = OUTPUT_DIR / "stacked_bar_charts"
    if not stacked_dir.exists():
        return result

    for source in ["acs", "decennial"]:
        source_dir = stacked_dir / source
        if not source_dir.exists():
            continue

        group_data: dict[str, dict] = {}

        for human_dir in source_dir.iterdir():
            if not human_dir.is_dir():
                continue
            human_name = human_dir.name

            for png in human_dir.glob("*.png"):
                match = re.match(r"^(.+)_n\d+geoids_(\d{4})\.png$", png.name)
                if match:
                    group_id = match.group(1)
                    year = int(match.group(2))
                    if group_id not in group_data:
                        group_data[group_id] = {
                            "id": group_id,
                            "label": human_name.replace("_", " "),
                            "years": [],
                        }
                    group_data[group_id]["years"].append(year)

        for group_id, data in group_data.items():
            result[source]["variables"].append(
                {
                    "id": group_id,
                    "label": data["label"],
                    "years": sorted(set(data["years"])),
                }
            )

    return result


def scan_scatter_plots() -> dict:
    """Scan scatter_plots/{source}/{Human_Name}/{transform}/overlap_total_vs_{y_var}_{year}.png"""
    result = {"acs": {"variables": []}, "decennial": {"variables": []}}
    scatter_dir = OUTPUT_DIR / "scatter_plots"
    if not scatter_dir.exists():
        return result

    for source in ["acs", "decennial"]:
        source_dir = scatter_dir / source
        if not source_dir.exists():
            continue

        var_data: dict[str, dict] = {}

        for human_dir in source_dir.iterdir():
            if not human_dir.is_dir():
                continue
            human_name = human_dir.name

            for transform_dir in human_dir.iterdir():
                if not transform_dir.is_dir():
                    continue
                transform = transform_dir.name

                for png in transform_dir.glob("*.png"):
                    match = re.match(
                        r"^overlap_total_vs_(.+)_(\d{4})\.png$", png.name
                    )
                    if match:
                        y_var = match.group(1)
                        year = int(match.group(2))
                        var_key = f"{y_var}|{transform}"
                        if var_key not in var_data:
                            var_data[var_key] = {
                                "id": y_var,
                                "label": human_name.replace("_", " "),
                                "transforms": {},
                                "years": [],
                            }
                        var_data[var_key]["transforms"][transform] = True
                        var_data[var_key]["years"].append(year)

        for var_key, data in var_data.items():
            result[source]["variables"].append(
                {
                    "id": data["id"],
                    "label": data["label"],
                    "transforms": list(data["transforms"].keys()),
                    "years": sorted(set(data["years"])),
                }
            )

    return result


def build_manifest() -> dict:
    """Build the full manifest from all chart types."""
    choropleth = scan_choropleths()
    pie_chart = scan_pie_charts()
    bar_chart = scan_bar_charts()
    stacked_bar = scan_stacked_bar_charts()
    scatter = scan_scatter_plots()

    chart_types = []
    if any(choropleth["acs"]["variables"] or choropleth["decennial"]["variables"]):
        chart_types.append("choropleth")
    if any(pie_chart["acs"]["variables"] or pie_chart["decennial"]["variables"]):
        chart_types.append("pie_chart")
    if any(bar_chart["acs"]["variables"] or bar_chart["decennial"]["variables"]):
        chart_types.append("bar_chart")
    if any(
        stacked_bar["acs"]["variables"] or stacked_bar["decennial"]["variables"]
    ):
        chart_types.append("stacked_bar")
    if any(scatter["acs"]["variables"] or scatter["decennial"]["variables"]):
        chart_types.append("scatter")

    return {
        "chartTypes": chart_types,
        "choropleth": choropleth,
        "pie_chart": pie_chart,
        "bar_chart": bar_chart,
        "stacked_bar": stacked_bar,
        "scatter": scatter,
    }


def main() -> None:
    """Generate manifest.json from output/ directory."""
    manifest = build_manifest()
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote manifest to {MANIFEST_OUT} ({len(manifest['chartTypes'])} chart types)")


if __name__ == "__main__":
    main()
