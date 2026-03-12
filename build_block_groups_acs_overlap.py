"""
Build block groups with ACS data and MBTA stop buffer overlap counts.

Pipeline:
  1. Clip block groups to MBTA Communities
  2. Flatten stop buffers (explode routes array)
  3. Spatial join: block group centroids within buffers
  4. Download ACS Data Profile (DP02-DP05) via Census API
  5. Preprocess ACS (normalize variable names across years)
  6. Join ACS + overlap counts, output GeoJSON and CSV

Usage:
  python build_block_groups_acs_overlap.py

Requires:
  - config.yaml with census_api_key (or skip ACS with empty key)
  - data/mbta_communities_list.csv (with massgis_match)
  - data/mbta_communities/mbta_communities.geojson
  - data/census/tl_2024_25_bg.shp
  - data/mbta_stops_with_buffer/mbta_stops_with_buffer_collapsed.geojson

Output:
  data/output/block_groups_acs_overlap.geojson
  data/output/block_groups_acs_overlap.csv
  data/output/block_groups_acs_overlap_long.csv (all years)
"""

import json
import re
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# Default paths (overridable by config)
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "output"
MBTA_LIST_PATH = DATA_DIR / "mbta_communities_list.csv"
MBTA_BOUNDARIES_PATH = DATA_DIR / "mbta_communities" / "mbta_communities.geojson"
BLOCK_GROUPS_PATH = DATA_DIR / "census" / "tl_2024_25_bg.shp"
BUFFER_PATH = DATA_DIR / "mbta_stops_with_buffer" / "mbta_stops_with_buffer_collapsed.geojson"
ACS_RAW_DIR = DATA_DIR / "census" / "acs_raw"
ACS_NORMALIZED_DIR = DATA_DIR / "census" / "acs_normalized"

# ACS 5-year years available (2009 = 2005-2009 through 2023/2024)
ACS_YEARS = list(range(2009, 2025))  # 2009-2024
DP_TABLES = ["DP02", "DP03", "DP04", "DP05"]
STATE_FIPS = "25"  # Massachusetts

# Census API base URL
CENSUS_API_BASE = "https://api.census.gov/data"


def load_config() -> dict:
    """Load config from config.yaml (simple key: value parser)."""
    cfg = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    v = v.split("#")[0].strip().strip('"').strip("'")
                    cfg[k.strip()] = v
    return cfg


def _safe_desc_col(s: str) -> str:
    """Convert route_desc to column name: overlap_desc_<sanitized>."""
    sanitized = re.sub(r"[^\w]", "_", str(s)).strip("_") or "Unknown"
    return f"overlap_desc_{sanitized}"


def _safe_color_col(s: str) -> str:
    """Convert route_color to column name: overlap_color_<hex>."""
    sanitized = re.sub(r"[^\w]", "_", str(s).strip()).strip("_") or "Unknown"
    return f"overlap_color_{sanitized}"


def _safe_desc_route_cleaned_col(s: str) -> str:
    """Convert route_desc to column name: overlap_desc_route_cleaned_<sanitized>."""
    sanitized = re.sub(r"[^\w]", "_", str(s)).strip("_") or "Unknown"
    return f"overlap_desc_route_cleaned_{sanitized}"


def _safe_color_route_cleaned_col(s: str) -> str:
    """Convert route_color to column name: overlap_color_route_cleaned_<hex>."""
    sanitized = re.sub(r"[^\w]", "_", str(s).strip()).strip("_") or "Unknown"
    return f"overlap_color_route_cleaned_{sanitized}"


# -----------------------------------------------------------------------------
# Step 1: Clip block groups to MBTA Communities
# -----------------------------------------------------------------------------
def clip_block_groups_to_mbta(
    bg_path: Path,
    mbta_boundaries_path: Path,
) -> gpd.GeoDataFrame:
    """
    Clip block groups to MBTA Community boundaries.

    Parameters
    ----------
    bg_path : Path
        Path to TIGER block group shapefile.
    mbta_boundaries_path : Path
        Path to MBTA communities GeoJSON.

    Returns
    -------
    gpd.GeoDataFrame
        Block groups that intersect MBTA Communities.
    """
    print("Loading block groups and MBTA boundaries...", flush=True)
    bg = gpd.read_file(bg_path)
    mbta = gpd.read_file(mbta_boundaries_path)

    # Ensure same CRS
    mbta = mbta.to_crs(bg.crs)
    # Clip: keep block groups that intersect MBTA
    clipped = gpd.sjoin(bg, mbta[["geometry"]], how="inner", predicate="intersects")
    # Drop duplicate block groups (one BG can touch multiple towns at edges)
    clipped = clipped.drop(columns=[c for c in clipped.columns if c.startswith("index_")])
    clipped = clipped.drop_duplicates(subset=["GEOID"])
    print(f"  Clipped to {len(clipped)} block groups in MBTA Communities")
    return clipped


# -----------------------------------------------------------------------------
# Step 2: Flatten stop buffers
# -----------------------------------------------------------------------------
def flatten_stop_buffers(buffer_path: Path) -> gpd.GeoDataFrame:
    """
    Flatten mbta_stops_with_buffer_collapsed.geojson to one row per stop-route.

    Parameters
    ----------
    buffer_path : Path
        Path to collapsed buffer GeoJSON.

    Returns
    -------
    gpd.GeoDataFrame
        One row per (stop, route) with geometry, route_desc, route_color, etc.
    """
    print("Flattening stop buffers...")
    with open(buffer_path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry")
        routes_raw = props.get("routes", [])
        if isinstance(routes_raw, str):
            routes = json.loads(routes_raw) if routes_raw else []
        else:
            routes = routes_raw or []

        for route in routes:
            row = {
                "stop_id": props.get("stop_id"),
                "stop_code": props.get("stop_code"),
                "stop_name": props.get("stop_name"),
                "route_id": route.get("route_id"),
                "route_desc": route.get("route_desc"),
                "route_color": route.get("route_color"),
            }
            row["geometry"] = shape(geom) if geom else None
            rows.append(row)

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    # Normalize route_desc and route_color
    gdf["route_desc"] = gdf["route_desc"].fillna("Unknown").astype(str).str.strip()
    gdf["route_color"] = (
        gdf["route_color"].fillna("Unknown").astype(str).str.strip().str.lstrip("#").str.upper()
    )
    gdf.loc[gdf["route_color"] == "", "route_color"] = "Unknown"
    # Exclude rail replacement bus
    rail_replacement = gdf["route_desc"].str.lower().str.replace(" ", "_") == "rail_replacement_bus"
    gdf = gdf[~rail_replacement].copy()
    print(f"  {len(gdf)} stop-route buffers")
    return gdf


# -----------------------------------------------------------------------------
# Step 3: Spatial join for overlap counts
# -----------------------------------------------------------------------------
def compute_overlap_counts(
    block_groups: gpd.GeoDataFrame,
    buffers_gdf: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    For each block group centroid, count buffers that contain it, by route_desc and route_color.

    Parameters
    ----------
    block_groups : gpd.GeoDataFrame
        Block groups (with GEOID).
    buffers_gdf : gpd.GeoDataFrame
        Flattened stop buffers.

    Returns
    -------
    pd.DataFrame
        GEOID and overlap count columns.
    """
    print("Computing overlap counts (centroid within buffer)...")
    # Project to UTM for accurate geometry
    utm = "EPSG:32619"
    bg_proj = block_groups.to_crs(utm)
    buf_proj = buffers_gdf.to_crs(utm)

    centroids = bg_proj[["GEOID", "geometry"]].copy()
    centroids["geometry"] = centroids.geometry.centroid

    # Use spatial index: centroids (points) within buffers (polygons)
    joined = gpd.sjoin(centroids, buf_proj, how="inner", predicate="within")

    joined["stop_route"] = joined["stop_id"].astype(str) + "_" + joined["route_id"].astype(str)

    # Pivot by route_desc
    overlap_desc = (
        joined.groupby(["GEOID", "route_desc"])["stop_route"]
        .nunique()
        .reset_index(name="count")
    )
    pivoted_desc = overlap_desc.pivot(index="GEOID", columns="route_desc", values="count").reset_index()

    overlap_color = (
        joined.groupby(["GEOID", "route_color"])["stop_route"]
        .nunique()
        .reset_index(name="count")
    )
    pivoted_color = overlap_color.pivot(index="GEOID", columns="route_color", values="count").reset_index()

    # Route-cleaned
    overlap_desc_rc = (
        joined.groupby(["GEOID", "route_desc"])["route_id"]
        .nunique()
        .reset_index(name="count")
    )
    pivoted_desc_rc = overlap_desc_rc.pivot(index="GEOID", columns="route_desc", values="count").reset_index()

    overlap_color_rc = (
        joined.groupby(["GEOID", "route_color"])["route_id"]
        .nunique()
        .reset_index(name="count")
    )
    pivoted_color_rc = overlap_color_rc.pivot(index="GEOID", columns="route_color", values="count").reset_index()

    # Merge
    result = block_groups[["GEOID"]].drop_duplicates().merge(pivoted_desc, on="GEOID", how="left")
    result = result.merge(pivoted_color, on="GEOID", how="left", suffixes=("", "_dup"))
    result = result.merge(pivoted_desc_rc, on="GEOID", how="left", suffixes=("", "_rc"))
    result = result.merge(pivoted_color_rc, on="GEOID", how="left", suffixes=("", "_rc"))

    # Rename columns
    desc_cols = [c for c in pivoted_desc.columns if c != "GEOID"]
    color_cols = [c for c in pivoted_color.columns if c != "GEOID"]
    rename_desc = {c: _safe_desc_col(c) for c in desc_cols}
    rename_color = {c: _safe_color_col(c) for c in color_cols}
    rename_desc_rc = {c: _safe_desc_route_cleaned_col(c) for c in desc_cols}
    rename_color_rc = {c: _safe_color_route_cleaned_col(c) for c in color_cols}

    # Handle duplicate column names from merge
    for c in list(result.columns):
        if c.endswith("_rc") and c.replace("_rc", "") in desc_cols:
            result = result.rename(columns={c: rename_desc_rc.get(c.replace("_rc", ""), c)})
        elif c.endswith("_rc") and c.replace("_rc", "") in color_cols:
            result = result.rename(columns={c: rename_color_rc.get(c.replace("_rc", ""), c)})
        elif c in desc_cols and c != "GEOID":
            result = result.rename(columns={c: rename_desc[c]})
        elif c in color_cols and c != "GEOID":
            result = result.rename(columns={c: rename_color[c]})

    # Drop _dup columns if any
    result = result[[c for c in result.columns if not c.endswith("_dup")]]

    # Fill NaN with 0
    overlap_cols = [c for c in result.columns if c.startswith("overlap_")]
    result[overlap_cols] = result[overlap_cols].fillna(0).astype(int)

    desc_final = [rename_desc[c] for c in desc_cols]
    result["overlap_total"] = result[desc_final].sum(axis=1)

    print(f"  Overlap columns: {len(overlap_cols)}")
    return result


# -----------------------------------------------------------------------------
# Step 4: Download ACS Data Profile (or Detailed Tables fallback)
# -----------------------------------------------------------------------------
# Note: ACS 5-year Profile may not support block groups in all years.
# We use Detailed Tables (B-series) as fallback - key variables for Narrative Profile + TOD.
#
# Data Profile (DP02-DP05) when available covers:
#   DP02: Social (households, marital status, language, mobility, education, disability)
#   DP03: Economic (employment, income, poverty, commuting, SNAP)
#   DP04: Housing (type, tenure, costs, heating fuel)
#   DP05: Demographics (population, age, sex, race, Hispanic origin)
#
# Fallback + TOD-relevant additions:
FALLBACK_VARS = [
    # Demographics
    "B01001_001E",  # Total population
    "B01002_001E",  # Median age
    # Income & poverty
    "B19013_001E",  # Median household income
    "B17001_002E",  # Income below poverty
    "B17001_001E",  # Population for poverty
    # Housing
    "B25001_001E",  # Total housing units
    "B25077_001E",  # Median home value
    "B25064_001E",  # Median gross rent
    "B25003_002E",  # Owner-occupied units
    "B25003_003E",  # Renter-occupied units
    # Employment
    "B23025_002E",  # In labor force
    "B23025_005E",  # Employed
    # Commuting (TOD core)
    "B08301_001E",  # Workers
    "B08301_003E",  # Drove alone
    "B08301_010E",  # Public transit
    "B08301_017E",  # Bicycle
    "B08301_018E",  # Walked
    "B08301_019E",  # Worked from home
    "B08303_001E",  # Mean commute time (minutes)
    # Vehicle ownership (TOD: car-free households)
    "B25044_002E",  # Owner units, no vehicle
    "B25044_009E",  # Renter units, no vehicle
    "B25044_003E",  # Owner units, 1 vehicle
    "B25044_010E",  # Renter units, 1 vehicle
    # Housing cost burden (TOD: affordability)
    "B25070_001E",  # Gross rent as % of income - total
    "B25070_007E",  # 30-34.9% (moderate burden)
    "B25070_008E",  # 35-39.9%
    "B25070_009E",  # 40-49.9%
    "B25070_010E",  # 50%+ (severe burden)
    # Units in structure (TOD: multi-family vs single-family)
    "B25024_001E",  # Total
    "B25024_002E",  # 1 unit, detached
    "B25024_003E",  # 1 unit, attached
    "B25024_004E",  # 2 units
    "B25024_005E",  # 3 or 4 units
    "B25024_006E",  # 5 to 9 units
    "B25024_007E",  # 10 to 19 units
    "B25024_008E",  # 20 to 49 units
    "B25024_009E",  # 50 or more units
    # Year structure built (TOD: new construction near transit)
    "B25034_001E",  # Total
    "B25034_002E",  # 2014 or later
    "B25034_003E",  # 2010 to 2013
    "B25034_004E",  # 2000 to 2009
    "B25034_005E",  # 1990 to 1999
    "B25034_006E",  # 1980 to 1989
    "B25034_007E",  # 1970 to 1979
    "B25034_008E",  # 1960 to 1969
    "B25034_009E",  # 1950 to 1959
    "B25034_010E",  # 1940 to 1949
    "B25034_011E",  # 1939 or earlier
    # Occupancy/vacancy (TOD: market tightness)
    "B25002_001E",  # Total housing units
    "B25002_002E",  # Occupied
    "B25002_003E",  # Vacant
    # Household size (TOD: density proxy)
    "B25010_001E",  # Average household size
]


def get_profile_variables(year: int) -> list[str]:
    """Fetch variable names for DP02-DP05 from Census API."""
    vars_all = []
    for table in DP_TABLES:
        url = f"{CENSUS_API_BASE}/{year}/acs/acs5/profile/groups/{table}.json"
        try:
            req = Request(url, headers={"User-Agent": "MBTA-ACS-Pipeline/1.0"})
            with urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
                for v in data.get("variables", {}):
                    if v.startswith(table) and not v.endswith("A") and not v.endswith("MA"):
                        vars_all.append(v)
        except (HTTPError, URLError, json.JSONDecodeError) as e:
            print(f"    Warning: could not fetch {table} for {year}: {e}")
    return vars_all


def _build_geoid_from_row(row_values: list, headers: list) -> str:
    """Build GEOID from Census API response row (list of values + headers)."""
    state = county = tract = bg = ""
    for h, v in zip(headers, row_values):
        val = str(v or "")
        h_lower = h.lower()
        if h_lower == "state":
            state = val
        elif h_lower == "county":
            county = val
        elif h_lower == "tract":
            tract = val
        elif "block" in h_lower and "group" in h_lower:
            bg = val
    return state + county + tract + bg


def download_acs_for_block_groups(
    geoids: list[str],
    years: list[int],
    api_key: str,
) -> dict[int, pd.DataFrame]:
    """
    Download ACS Data Profile for block groups, by year.
    Falls back to Detailed Tables if Profile not available at block group level.

    Parameters
    ----------
    geoids : list[str]
        List of block group GEOIDs.
    years : list[int]
        Years to download.
    api_key : str
        Census API key.

    Returns
    -------
    dict[int, pd.DataFrame]
        Year -> DataFrame with GEOID and ACS variables.
    """
    counties = sorted(set(g[2:5] for g in geoids))
    results = {}

    for year in years:
        print(f"  Downloading ACS {year}...")
        vars_list = get_profile_variables(year)
        use_profile = bool(vars_list)
        if not use_profile:
            vars_list = FALLBACK_VARS

        batch_size = 50
        dfs = []
        for i in range(0, len(vars_list), batch_size):
            batch = vars_list[i : i + batch_size]
            vars_str = ",".join(batch)
            for county in counties:
                if use_profile:
                    url = (
                        f"{CENSUS_API_BASE}/{year}/acs/acs5/profile?"
                        f"get={vars_str}&"
                        f"for=block%20group:*&"
                        f"in=state:{STATE_FIPS}%20county:{county}"
                    )
                else:
                    url = (
                        f"{CENSUS_API_BASE}/{year}/acs/acs5?"
                        f"get={vars_str}&"
                        f"for=block%20group:*&"
                        f"in=state:{STATE_FIPS}%20county:{county}"
                    )
                if api_key:
                    url += f"&key={api_key}"
                try:
                    req = Request(url, headers={"User-Agent": "MBTA-ACS-Pipeline/1.0"})
                    with urlopen(req, timeout=90) as r:
                        data = json.loads(r.read().decode())
                    if len(data) < 2:
                        continue
                    headers = [str(h) for h in data[0]]
                    rows = data[1:]
                    df = pd.DataFrame(rows, columns=headers)
                    geoid_col = [
                        _build_geoid_from_row(row.tolist(), headers)
                        for _, row in df.iterrows()
                    ]
                    df["GEOID"] = geoid_col
                    dfs.append(df)
                except (HTTPError, URLError, json.JSONDecodeError):
                    pass  # Silent skip for rate limits or parse errors

        if dfs:
            # Merge batches on GEOID (each batch has different variable columns)
            combined = dfs[0]
            for d in dfs[1:]:
                merge_cols = ["GEOID"] + [c for c in d.columns if c != "GEOID" and c not in combined.columns]
                if len(merge_cols) > 1:
                    combined = combined.merge(d[merge_cols], on="GEOID", how="outer")
            combined = combined.drop_duplicates(subset=["GEOID"])
            combined = combined[combined["GEOID"].isin(geoids)]
            if not combined.empty:
                results[year] = combined
                print(f"    {len(combined)} block groups, {len(combined.columns)-1} vars")
        else:
            print(f"    No data for {year}")

    return results


# -----------------------------------------------------------------------------
# Step 5: ACS Preprocessing
# -----------------------------------------------------------------------------
def preprocess_acs(
    acs_by_year: dict[int, pd.DataFrame],
    geoids: list[str],
) -> pd.DataFrame:
    """
    Normalize ACS data across years into long format.

    Parameters
    ----------
    acs_by_year : dict[int, pd.DataFrame]
        Raw ACS DataFrames by year.
    geoids : list[str]
        Block group GEOIDs to keep.

    Returns
    -------
    pd.DataFrame
        Long-format table with year, GEOID, and ACS variables.
    """
    print("Preprocessing ACS (normalizing across years)...")
    id_cols = ["GEOID", "year"]
    common_vars = None
    all_dfs = []

    for year, df in sorted(acs_by_year.items()):
        if df is None or df.empty:
            continue
        df = df[df["GEOID"].isin(geoids)].copy()
        df["year"] = year
        # Keep geography columns (state, county, tract, block group, GEO_ID) for analysis
        all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    # Reorder: GEOID, year first
    cols = ["GEOID", "year"] + [c for c in combined.columns if c not in ("GEOID", "year")]
    combined = combined[[c for c in cols if c in combined.columns]]
    print(f"  {len(combined)} rows, {len(combined.columns)} columns")
    return combined


# -----------------------------------------------------------------------------
# Step 6: Join and output
# -----------------------------------------------------------------------------
def main() -> None:
    """Run full pipeline."""
    cfg = load_config()
    data_dir = Path(cfg.get("data_dir", DATA_DIR))
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    output_dir = Path(cfg.get("output_dir", OUTPUT_DIR))
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    api_key = (cfg.get("census_api_key") or "").strip()
    acs_years_cfg = cfg.get("acs_years", "")
    acs_years = list(ACS_YEARS)
    if acs_years_cfg:
        # Parse e.g. "2020,2021,2022" or "2020-2022"
        try:
            if "-" in str(acs_years_cfg):
                start, end = map(int, acs_years_cfg.split("-"))
                acs_years = list(range(start, end + 1))
            else:
                acs_years = [int(y.strip()) for y in str(acs_years_cfg).split(",") if y.strip()]
        except ValueError:
            pass

    mbta_list = data_dir / "mbta_communities_list.csv"
    mbta_geojson = data_dir / "mbta_communities" / "mbta_communities.geojson"
    bg_path = data_dir / "census" / "tl_2024_25_bg.shp"
    buffer_path = data_dir / "mbta_stops_with_buffer" / "mbta_stops_with_buffer_collapsed.geojson"

    output_dir.mkdir(parents=True, exist_ok=True)
    ACS_RAW_DIR.mkdir(parents=True, exist_ok=True)
    ACS_NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Clip block groups
    block_groups = clip_block_groups_to_mbta(bg_path, mbta_geojson)
    geoids = block_groups["GEOID"].tolist()

    # Step 2: Flatten buffers
    buffers_gdf = flatten_stop_buffers(buffer_path)

    # Step 3: Overlap counts
    overlap_df = compute_overlap_counts(block_groups, buffers_gdf)

    # Step 4: Download ACS (if key provided)
    acs_by_year = {}
    if api_key:
        acs_by_year = download_acs_for_block_groups(geoids, acs_years, api_key)
    else:
        print("No census_api_key in config; skipping ACS download.", flush=True)

    # Step 5: Preprocess ACS
    acs_long = pd.DataFrame()
    if acs_by_year:
        acs_long = preprocess_acs(acs_by_year, geoids)
        acs_long.to_csv(output_dir / "block_groups_acs_overlap_long.csv", index=False)
        print(f"Saved {output_dir / 'block_groups_acs_overlap_long.csv'}")

    # Step 6: Join and output
    # Latest year ACS for GeoJSON (or just overlap if no ACS)
    latest_year = max(acs_by_year.keys()) if acs_by_year else None
    if latest_year is not None and latest_year in acs_by_year:
        acs_latest = acs_by_year[latest_year]
        acs_latest = acs_latest.drop(columns=["year"], errors="ignore")
        merged = block_groups.merge(overlap_df, on="GEOID", how="left")
        merged = merged.merge(
            acs_latest,
            on="GEOID",
            how="left",
        )
    else:
        merged = block_groups.merge(overlap_df, on="GEOID", how="left")

    print("Writing output files...", flush=True)
    merged = merged.to_crs(epsg=4326)
    merged.to_file(output_dir / "block_groups_acs_overlap.geojson", driver="GeoJSON")
    # Drop geometry for CSV
    merged_csv = merged.drop(columns=["geometry"], errors="ignore")
    merged_csv.to_csv(output_dir / "block_groups_acs_overlap.csv", index=False)

    print(f"\nSaved:")
    print(f"  {output_dir / 'block_groups_acs_overlap.geojson'} ({len(merged)} features)")
    print(f"  {output_dir / 'block_groups_acs_overlap.csv'}")
    if not acs_long.empty:
        print(f"  {output_dir / 'block_groups_acs_overlap_long.csv'} (all years)")


if __name__ == "__main__":
    main()
