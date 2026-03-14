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
import sys
from pathlib import Path

# Add scripts dir for d3_var_categories
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from d3_var_categories import DECENNIAL_CHORO_APPROVED

# Paths
TOD_VIZ_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = TOD_VIZ_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
MANIFEST_OUT = TOD_VIZ_DIR / "public" / "manifest.json"
CHOROPLETH_DATA_DIR = TOD_VIZ_DIR / "public" / "data" / "choropleth"


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


def scan_d3_choropleth_json() -> dict:
    """
    Scan D3 choropleth folder for acs_*.json and decennial_*.json.
    Used to include per_aland and other transforms for population/housing density
    (persons/land area, housing units/land area) in the interactive D3 viewer,
    even when PNGs were not generated for those transforms.
    """
    result = {"acs": {"variables": []}, "decennial": {"variables": []}}
    if not CHOROPLETH_DATA_DIR.exists():
        return result

    import csv
    acs_mapping = PROJECT_ROOT / "acs" / "data" / "acs_variable_mapping.csv"
    dec_mapping = PROJECT_ROOT / "decennial_census" / "data" / "decennial_variable_mapping_nhgis.csv"
    label_by_var: dict[str, str] = {}
    for path in [acs_mapping, dec_mapping]:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    label_by_var[row["variable"]] = row.get("human_readable_name", row["variable"])

    for source in ["acs", "decennial"]:
        prefix = f"{source}_"
        var_data: dict[str, dict] = {}
        for p in CHOROPLETH_DATA_DIR.glob(f"{prefix}*.json"):
            stem = p.stem
            if not stem.startswith(prefix):
                continue
            # Skip acs_native_* (handled by acs geography selector)
            rest = stem[len(prefix):]
            if rest.startswith("native"):
                continue
            # Variable can contain underscores (e.g. B01001_001E); transform is from fixed set
            known_transforms = ("per_aland", "per_population", "proportion", "count", "raw")
            var_id, transform = None, None
            for t in known_transforms:
                suffix = "_" + t
                if rest.endswith(suffix):
                    var_id = rest[: -len(suffix)]
                    transform = t
                    break
            if var_id is None or transform is None:
                continue
            if var_id not in var_data:
                var_data[var_id] = {
                    "id": var_id,
                    "label": label_by_var.get(var_id, var_id.replace("_", " ")),
                    "transforms": {},
                    "years": set(),
                }
            if transform not in var_data[var_id]["transforms"]:
                var_data[var_id]["transforms"][transform] = []
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                years = data.get("years", [])
                var_data[var_id]["transforms"][transform] = years
                var_data[var_id]["years"].update(years)
            except (json.JSONDecodeError, KeyError):
                pass

        for var_id, data in var_data.items():
            all_years = sorted(data["years"])
            transforms = sorted(data["transforms"].keys())
            result[source]["variables"].append({
                "id": var_id,
                "label": data["label"],
                "transforms": transforms,
                "years": all_years,
            })
    return result


def _merge_choropleth_variables(png_vars: list, json_vars: list) -> list:
    """Merge variable lists by id; union of transforms and years."""
    by_id: dict[str, dict] = {}
    for v in png_vars:
        by_id[v["id"]] = v.copy()
    for v in json_vars:
        vid = v["id"]
        if vid in by_id:
            existing = by_id[vid]
            trans_set = set(existing.get("transforms", [])) | set(v.get("transforms", []))
            year_set = set(existing.get("years", [])) | set(v.get("years", []))
            by_id[vid]["transforms"] = sorted(trans_set)
            by_id[vid]["years"] = sorted(year_set)
        else:
            by_id[vid] = v.copy()
    return list(by_id.values())


def scan_d3_decennial_extras() -> dict:
    """
    Scan D3 choropleth folder for decennial_extras_*.json (variables not in var_list).
    Adds decennial_extras as a source for the interactive D3 viewer.
    """
    result = {"variables": []}
    if not CHOROPLETH_DATA_DIR.exists():
        return result

    import csv
    mapping_path = PROJECT_ROOT / "decennial_census" / "data" / "decennial_variable_mapping_nhgis.csv"
    label_by_var = {}
    if mapping_path.exists():
        with open(mapping_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                label_by_var[row["variable"]] = row.get("human_readable_name", row["variable"])

    # Transforms can contain underscores (e.g. per_aland, per_population); must match
    # before using rsplit to avoid parsing "CM0AA_per_aland" as var="CM0AA_per", trans="aland".
    known_transforms = ("per_aland", "per_population", "proportion", "count", "raw")
    var_data = {}
    for p in CHOROPLETH_DATA_DIR.glob("decennial_extras_*.json"):
        stem = p.stem
        if not stem.startswith("decennial_extras_"):
            continue
        rest = stem[len("decennial_extras_"):]
        var_id, transform = None, None
        for t in known_transforms:
            suffix = "_" + t
            if rest.endswith(suffix):
                var_id = rest[: -len(suffix)]
                transform = t
                break
        if var_id is None or transform is None:
            continue
        if var_id not in var_data:
            var_data[var_id] = {"id": var_id, "label": label_by_var.get(var_id, var_id), "transforms": {}, "years": set()}
        if transform not in var_data[var_id]["transforms"]:
            var_data[var_id]["transforms"][transform] = []
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            years = data.get("years", [])
            var_data[var_id]["transforms"][transform] = years
            var_data[var_id]["years"].update(years)
        except (json.JSONDecodeError, KeyError):
            pass

    for var_id, data in var_data.items():
        all_years = sorted(data["years"])
        transforms = sorted(data["transforms"].keys())
        result["variables"].append({
            "id": var_id,
            "label": data["label"],
            "transforms": transforms,
            "years": all_years,
        })
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
    d3_json = scan_d3_choropleth_json()
    decennial_extras = scan_d3_decennial_extras()

    # Merge D3 choropleth JSON (persons/land, housing/land, etc.) with PNG-derived data
    for source in ["acs", "decennial"]:
        choropleth[source]["variables"] = _merge_choropleth_variables(
            choropleth[source]["variables"],
            d3_json[source]["variables"],
        )

    # Decennial dropdown: only variables in DECENNIAL_CHORO_APPROVED (var_list.yaml).
    # Extras variables go only in Decennial (extras) dropdown.
    choropleth["decennial"]["variables"] = [
        v for v in choropleth["decennial"]["variables"]
        if v["id"] in DECENNIAL_CHORO_APPROVED
    ]

    if decennial_extras["variables"]:
        choropleth["decennial_extras"] = decennial_extras
    pie_chart = scan_pie_charts()
    bar_chart = scan_bar_charts()
    stacked_bar = scan_stacked_bar_charts()
    scatter = scan_scatter_plots()

    chart_types = []
    has_choropleth = any(
        choropleth.get("acs", {}).get("variables")
        or choropleth.get("decennial", {}).get("variables")
        or choropleth.get("decennial_extras", {}).get("variables")
    )
    if has_choropleth:
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
