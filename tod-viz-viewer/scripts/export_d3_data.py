"""
Export precomputed choropleth variable data to JSON for the D3 interactive viewer.

Uses the same transform logic as visualization/utils.py (apply_transformation,
resolve_denominator) and create_choropleth_maps.py (_compute_global_limits).
Output: public/data/choropleth/{source}_{variable}_{transform}.json

Format: { geoids, years, values: { year: [v1, v2, ...] }, vmin, vmax }
values[year][i] maps to geoids[i]; null for missing.

Run from project root: python tod-viz-viewer/scripts/export_d3_data.py
Or from tod-viz-viewer: python scripts/export_d3_data.py (add parent to path)
"""

import json
import math
import sys
from pathlib import Path

# Project root (fp1) for visualization imports; scripts dir for d3_var_categories
SCRIPT_DIR = Path(__file__).resolve().parent
TOD_VIZ_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = TOD_VIZ_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

import numpy as np
import pandas as pd
from shapely.geometry import box

from visualization.utils import (
    ACS_NULL,
    MBTA_LINES_PATH,
    apply_transformation,
    get_aland_column,
    get_boston_zoom_bounds,
    get_population_column,
    load_data,
    load_data_acs_native,
    merge_long_with_geometry,
    resolve_denominator,
)

from d3_var_categories import get_choropleth_source

OUTPUT_DIR = TOD_VIZ_DIR / "public" / "data" / "choropleth"
DATA_DIR = TOD_VIZ_DIR / "public" / "data"

# Massachusetts county FIPS to name (for tooltip "town" display)
MA_COUNTY_NAMES = {
    "001": "Barnstable",
    "003": "Berkshire",
    "005": "Bristol",
    "007": "Dukes",
    "009": "Essex",
    "011": "Franklin",
    "013": "Hampden",
    "015": "Hampshire",
    "017": "Suffolk",
    "019": "Nantucket",
    "021": "Middlesex",
    "023": "Plymouth",
    "025": "Norfolk",
    "027": "Worcester",
}


def _sanitize_for_json(obj):
    """
    Replace NaN/Inf with None so JSON is valid (JavaScript JSON.parse rejects NaN).
    """
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(x) for x in obj]
    if pd.isna(obj):
        return None
    if isinstance(obj, (int, float)) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def _compute_global_limits(
    long_df,
    geo_gdf,
    mapping_df,
    source: str,
    var: str,
    trans: str,
    years: list[int],
) -> tuple[float | None, float | None]:
    """
    Compute vmin/vmax for variable+transform across all years.
    Matches create_choropleth_maps._compute_global_limits (sigma clipping).
    """
    aland_col = get_aland_column(geo_gdf, source)
    pop_col = get_population_column(source)
    bounds = get_boston_zoom_bounds(geo_gdf.crs, MBTA_LINES_PATH)
    bounds_poly = box(bounds[0], bounds[1], bounds[2], bounds[3])

    var_row = mapping_df[mapping_df["variable"] == var]
    denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None

    vals = []
    for year in years:
        sub = long_df[long_df["year"] == year]
        if sub.empty or var not in sub.columns:
            continue
        merged = merge_long_with_geometry(sub, geo_gdf, aland_col)
        merged = merged[~merged.intersects(bounds_poly)]
        for _, r in merged.iterrows():
            raw = r.get(var)
            aland = r.get(aland_col)
            pop = r.get(pop_col) if pop_col in r.index else None
            denom = resolve_denominator(denom_spec, r, source) if denom_spec else None
            val = apply_transformation(
                raw,
                trans,
                denominator=denom,
                aland=aland,
                population=pop,
                null_sentinel=ACS_NULL if source == "acs" else None,
            )
            if val is not None:
                vals.append(val)

    if not vals:
        return None, None
    mean, std = np.mean(vals), np.std(vals)
    vmin = mean - 2 * std if std > 0 else float(min(vals))
    vmax = mean + 2 * std if std > 0 else float(max(vals))
    return float(vmin), float(vmax)


def export_variable(
    source: str,
    variable: str,
    transform: str,
    output_dir: Path,
) -> Path | None:
    """
    Export precomputed values for one variable+transform to JSON.

    Returns
    -------
    Path or None
        Path to written JSON, or None if failed.
    """
    long_df, geo_gdf, mapping_df = load_data(source)
    aland_col = get_aland_column(geo_gdf, source)
    pop_col = get_population_column(source)

    if "year" not in long_df.columns or variable not in long_df.columns:
        return None

    var_row = mapping_df[mapping_df["variable"] == variable]
    denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None

    # Canonical GEOID order from geometry (matches GeoJSON features)
    geoids = geo_gdf["GEOID"].astype(str).tolist()
    geoid_to_idx = {g: i for i, g in enumerate(geoids)}

    years = sorted(long_df["year"].dropna().unique().astype(int).tolist())
    values_by_year = {}

    for year in years:
        sub = long_df[long_df["year"] == year]
        if sub.empty:
            values_by_year[str(year)] = [None] * len(geoids)
            continue

        merged = merge_long_with_geometry(sub, geo_gdf, aland_col)
        arr = [None] * len(geoids)

        for _, row in merged.iterrows():
            geoid = str(row["GEOID"])
            if geoid not in geoid_to_idx:
                continue
            raw = row.get(variable)
            aland = row.get(aland_col)
            pop = row.get(pop_col) if pop_col in row.index else None
            denom = (
                resolve_denominator(denom_spec, row, source) if denom_spec else None
            )
            val = apply_transformation(
                raw,
                transform,
                denominator=denom,
                aland=aland,
                population=pop,
                null_sentinel=ACS_NULL if source == "acs" else None,
            )
            arr[geoid_to_idx[geoid]] = val

        values_by_year[str(year)] = arr

    vmin, vmax = _compute_global_limits(
        long_df, geo_gdf, mapping_df, source, variable, transform, years
    )
    if vmin is None or vmax is None:
        vmin, vmax = 0.0, 1.0

    out = _sanitize_for_json({
        "geoids": geoids,
        "years": years,
        "values": values_by_year,
        "vmin": vmin,
        "vmax": vmax,
    })

    # Use effective source: decennial vs decennial_extras per var_list
    effective_source = get_choropleth_source(source, variable)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{effective_source}_{variable}_{transform}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    return out_path


def export_variable_acs_native(
    variable: str,
    transform: str,
    output_dir: Path,
) -> Path | None:
    """
    Export precomputed values for one ACS variable+transform using 2020 geography.

    Output: acs_native_{variable}_{transform}.json
    Returns None if 2020 geography files do not exist.
    """
    loaded = load_data_acs_native()
    if loaded is None:
        return None

    long_df, geo_gdf, mapping_df = loaded
    aland_col = get_aland_column(geo_gdf, "acs")
    if aland_col not in geo_gdf.columns:
        return None

    pop_col = get_population_column("acs")

    if "year" not in long_df.columns or variable not in long_df.columns:
        return None

    var_row = mapping_df[mapping_df["variable"] == variable]
    denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None

    geoids = geo_gdf["GEOID"].astype(str).tolist()
    geoid_to_idx = {g: i for i, g in enumerate(geoids)}

    years = sorted(long_df["year"].dropna().unique().astype(int).tolist())
    values_by_year = {}

    for year in years:
        sub = long_df[long_df["year"] == year]
        if sub.empty:
            values_by_year[str(year)] = [None] * len(geoids)
            continue

        merged = merge_long_with_geometry(sub, geo_gdf, aland_col)
        arr = [None] * len(geoids)

        for _, row in merged.iterrows():
            geoid = str(row["GEOID"])
            if geoid not in geoid_to_idx:
                continue
            raw = row.get(variable)
            aland = row.get(aland_col)
            pop = row.get(pop_col) if pop_col in row.index else None
            denom = (
                resolve_denominator(denom_spec, row, "acs") if denom_spec else None
            )
            val = apply_transformation(
                raw,
                transform,
                denominator=denom,
                aland=aland,
                population=pop,
                null_sentinel=ACS_NULL,
            )
            arr[geoid_to_idx[geoid]] = val

        values_by_year[str(year)] = arr

    vmin, vmax = _compute_global_limits(
        long_df, geo_gdf, mapping_df, "acs", variable, transform, years
    )
    if vmin is None or vmax is None:
        vmin, vmax = 0.0, 1.0

    # Sanitize NaN/Inf to None so JSON is valid (JavaScript JSON.parse rejects NaN)
    out = _sanitize_for_json({
        "geoids": geoids,
        "years": years,
        "values": values_by_year,
        "vmin": vmin,
        "vmax": vmax,
    })

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"acs_native_{variable}_{transform}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    return out_path


def export_metadata(source: str, output_dir: Path = DATA_DIR) -> Path | None:
    """
    Export block group metadata (population by year, land area, county/town) for tooltip
    and time-series weighted averages. Output goes to tod-viz-viewer/public/data/ so
    all runtime data is self-contained within the viewer.

    Parameters
    ----------
    source : {"acs", "decennial"}
        Data source.
    output_dir : Path, optional
        Base output directory (tod-viz-viewer/public/data).

    Returns
    -------
    Path or None
        Path to written JSON, or None if failed.
    """
    from visualization.utils import (
        ACS_GEO_PATH,
        ACS_LONG_PATH,
        DECENNIAL_GEO_PATH,
        DECENNIAL_LONG_PATH,
    )

    if source == "acs":
        geo_path = ACS_GEO_PATH
        long_path = ACS_LONG_PATH
    else:
        geo_path = DECENNIAL_GEO_PATH
        long_path = DECENNIAL_LONG_PATH

    if not geo_path.exists() or not long_path.exists():
        return None

    import geopandas as gpd

    geo_gdf = gpd.read_file(geo_path)
    if "GEOID" not in geo_gdf.columns and "GEOID10" in geo_gdf.columns:
        geo_gdf["GEOID"] = geo_gdf["GEOID10"].astype(str)
    else:
        geo_gdf["GEOID"] = geo_gdf["GEOID"].astype(str)

    aland_col = get_aland_column(geo_gdf, source)
    pop_col = get_population_column(source)
    county_col = "COUNTYFP10" if "COUNTYFP10" in geo_gdf.columns else "COUNTYFP"

    geoids = geo_gdf["GEOID"].tolist()
    land_area = geo_gdf[aland_col].fillna(0).astype(float).tolist() if aland_col in geo_gdf.columns else [0.0] * len(geoids)
    county_fips = (
        geo_gdf[county_col].astype(str).str.zfill(3).tolist()
        if county_col in geo_gdf.columns
        else [""] * len(geoids)
    )
    county_names = [MA_COUNTY_NAMES.get(c, c or "—") for c in county_fips]

    long_df = pd.read_csv(long_path)
    long_df["GEOID"] = long_df["GEOID"].astype(str)
    geoid_to_idx = {g: i for i, g in enumerate(geoids)}
    years = sorted(long_df["year"].dropna().unique().astype(int).tolist())
    population_by_year = {}

    for year in years:
        sub = long_df[long_df["year"] == year]
        if sub.empty or pop_col not in sub.columns:
            population_by_year[str(year)] = [None] * len(geoids)
            continue
        arr = [None] * len(geoids)
        for _, row in sub.iterrows():
            geoid = str(row["GEOID"])
            if geoid in geoid_to_idx:
                val = row.get(pop_col)
                arr[geoid_to_idx[geoid]] = None if pd.isna(val) else float(val)
        population_by_year[str(year)] = arr

    out = _sanitize_for_json({
        "geoids": geoids,
        "years": years,
        "population": population_by_year,
        "land_area": land_area,
        "county_fips": county_fips,
        "county_name": county_names,
    })

    out_dir = output_dir / "metadata"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"block_groups_{source}_metadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    return out_path


def export_metadata_acs_native(output_dir: Path = DATA_DIR) -> Path | None:
    """Export metadata for ACS native (2020) geography."""
    loaded = load_data_acs_native()
    if loaded is None:
        return None

    long_df, geo_gdf, _ = loaded
    aland_col = get_aland_column(geo_gdf, "acs")
    if aland_col not in geo_gdf.columns:
        return None

    pop_col = get_population_column("acs")
    county_col = "COUNTYFP10" if "COUNTYFP10" in geo_gdf.columns else "COUNTYFP20" if "COUNTYFP20" in geo_gdf.columns else "COUNTYFP"

    geo_gdf["GEOID"] = geo_gdf["GEOID"].astype(str) if "GEOID" in geo_gdf.columns else geo_gdf["GEOID10"].astype(str)
    geoids = geo_gdf["GEOID"].tolist()
    land_area = geo_gdf[aland_col].fillna(0).astype(float).tolist()
    county_fips = (
        geo_gdf[county_col].astype(str).str.zfill(3).tolist()
        if county_col in geo_gdf.columns
        else [""] * len(geoids)
    )
    county_names = [MA_COUNTY_NAMES.get(c, c or "—") for c in county_fips]

    long_df["GEOID"] = long_df["GEOID"].astype(str)
    geoid_to_idx = {g: i for i, g in enumerate(geoids)}
    years = sorted(long_df["year"].dropna().unique().astype(int).tolist())
    population_by_year = {}

    for year in years:
        sub = long_df[long_df["year"] == year]
        if sub.empty or pop_col not in sub.columns:
            population_by_year[str(year)] = [None] * len(geoids)
            continue
        arr = [None] * len(geoids)
        for _, row in sub.iterrows():
            geoid = str(row["GEOID"])
            if geoid in geoid_to_idx:
                val = row.get(pop_col)
                arr[geoid_to_idx[geoid]] = None if pd.isna(val) else float(val)
        population_by_year[str(year)] = arr

    out = _sanitize_for_json({
        "geoids": geoids,
        "years": years,
        "population": population_by_year,
        "land_area": land_area,
        "county_fips": county_fips,
        "county_name": county_names,
    })

    out_dir = output_dir / "metadata"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "block_groups_acs_native_metadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    return out_path


def copy_geo_to_viewer() -> list[Path]:
    """
    Copy GeoJSON files from project data dirs into tod-viz-viewer/public/data/
    so all runtime data is self-contained within the viewer.
    """
    import shutil

    copied = []
    geo_out = DATA_DIR / "geo"
    geo_decennial_out = DATA_DIR / "geo_decennial"
    geo_out.mkdir(parents=True, exist_ok=True)
    geo_decennial_out.mkdir(parents=True, exist_ok=True)

    acs_geo = PROJECT_ROOT / "acs" / "data" / "output" / "block_groups_acs_overlap.geojson"
    acs_geo_2020 = PROJECT_ROOT / "acs" / "data" / "output" / "block_groups_acs_overlap_2020.geojson"
    dec_geo = PROJECT_ROOT / "decennial_census" / "data" / "merged" / "block_groups_decennial_merged.geojson"

    for src, dst_dir in [(acs_geo, geo_out), (acs_geo_2020, geo_out), (dec_geo, geo_decennial_out)]:
        if src.exists():
            dst = dst_dir / src.name
            shutil.copy2(src, dst)
            copied.append(dst)
            print(f"Copied {src.name} to {dst}")

    return copied


def copy_lines_to_viewer() -> list[Path]:
    """
    Copy MBTA lines GeoJSON from project data dir into tod-viz-viewer/public/data/lines/
    so all runtime data is self-contained within the viewer.
    """
    import shutil

    copied = []
    lines_src = PROJECT_ROOT / "data" / "mbta_lines" / "lines.geojson"
    lines_out = DATA_DIR / "lines"
    if lines_src.exists():
        lines_out.mkdir(parents=True, exist_ok=True)
        dst = lines_out / "lines.geojson"
        shutil.copy2(lines_src, dst)
        copied.append(dst)
        print(f"Copied {lines_src.name} to {dst}")
    return copied


def export_all(output_dir: Path = OUTPUT_DIR) -> list[Path]:
    """
    Export choropleth data for all variables with non-pie_group transforms.
    For ACS, also exports native (2020 geography) variant if 2020 files exist.
    """
    created = []
    for source in ["acs", "decennial"]:
        long_df, _, mapping_df = load_data(source)
        var_map = mapping_df[
            mapping_df["transformations"].notna()
            & (mapping_df["transformations"] != "")
        ]
        var_map = var_map[~var_map["transformations"].str.contains("pie_group", na=False)]

        for _, row in var_map.iterrows():
            var = row["variable"]
            trans_str = row["transformations"]
            for trans in trans_str.split("|"):
                trans = trans.strip()
                if trans == "pie_group":
                    continue
                try:
                    p = export_variable(source, var, trans, output_dir)
                    if p:
                        created.append(p)
                        print(f"Exported {source} {var} {trans}")
                except Exception as e:
                    print(f"Skip {source} {var} {trans}: {e}")

        # ACS native (2020 geography): export if 2020 files exist
        if source == "acs":
            for _, row in var_map.iterrows():
                var = row["variable"]
                trans_str = row["transformations"]
                for trans in trans_str.split("|"):
                    trans = trans.strip()
                    if trans == "pie_group":
                        continue
                    try:
                        p = export_variable_acs_native(var, trans, output_dir)
                        if p:
                            created.append(p)
                            print(f"Exported acs_native {var} {trans}")
                    except Exception as e:
                        print(f"Skip acs_native {var} {trans}: {e}")

    return created


def _infer_tod_type(notes: str) -> str:
    """
    Infer TOD type from notes when no explicit tod_type column exists.
    Used for tooltip display (residential, affordable, mixed-use, etc.).
    """
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


def export_tod_projects(output_dir: Path | None = None) -> Path:
    """
    Convert tod_projects_locations.csv to JSON. No value transforms.
    Infers tod_type from notes for tooltip display when column is absent.
    """
    import csv

    output_dir = output_dir or (TOD_VIZ_DIR / "public" / "data")
    csv_path = PROJECT_ROOT / "tod_projects_locations.csv"
    out_path = output_dir / "tod_projects.json"

    projects = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            notes = row.get("notes", "")
            # Use explicit tod_type column if present; otherwise infer from notes
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
    return out_path


def main() -> None:
    # Copy GeoJSON and lines into viewer so all runtime data is self-contained
    copied_geo = copy_geo_to_viewer()
    copied_lines = copy_lines_to_viewer()

    # created = export_all()
    tod_path = export_tod_projects()

    # Export metadata for tooltip and time-series (population, land area, county)
    for src in ["acs", "decennial"]:
        try:
            p = export_metadata(src)
            if p:
                print(f"Exported metadata: {p.name}")
        except Exception as e:
            print(f"Skip metadata {src}: {e}")
    try:
        p = export_metadata_acs_native()
        if p:
            print(f"Exported metadata: {p.name}")
    except Exception as e:
        print(f"Skip acs_native metadata: {e}")

    # print(f"Exported {len(created)} variable JSONs to {OUTPUT_DIR}")
    print(f"Exported TOD projects to {tod_path}")
    print(f"Copied {len(copied_geo)} GeoJSON files and {len(copied_lines)} lines file(s) to viewer data dir")


if __name__ == "__main__":
    main()
