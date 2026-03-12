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
  python -m acs.build_block_groups_acs_overlap

Requires:
  - config.yaml with census_api_key (or skip ACS with empty key)
  - data/mbta_communities_list.csv (with massgis_match)
  - data/mbta_communities/mbta_communities.geojson
  - data/census/tl_2024_25_bg.shp
  - data/mbta_stops_with_buffer/mbta_stops_with_buffer_collapsed.geojson

Output:
  acs/data/output/block_groups_acs_overlap.geojson
  acs/data/output/block_groups_acs_overlap.csv
  acs/data/output/block_groups_acs_overlap_long.csv (all years)

Data integrity: Census API values are passed through unchanged. GEOID is derived
from API geography columns (state, county, tract, block group) for consistent joins.
"""

import json
import re
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

import geopandas as gpd
import pandas as pd

from mbta_overlap_utils import (
    clip_block_groups_to_mbta,
    compute_overlap_counts,
    flatten_stop_buffers,
)

# -----------------------------------------------------------------------------
# Configuration (paths relative to project root = parent of acs/)
# -----------------------------------------------------------------------------
ACS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ACS_ROOT.parent
CONFIG_PATHS = [PROJECT_ROOT / "config.yaml", ACS_ROOT / "config.yaml"]

# Shared data (project root)
DATA_DIR = PROJECT_ROOT / "data"
MBTA_LIST_PATH = DATA_DIR / "mbta_communities_list.csv"
MBTA_BOUNDARIES_PATH = DATA_DIR / "mbta_communities" / "mbta_communities.geojson"
BLOCK_GROUPS_PATH = DATA_DIR / "census" / "tl_2024_25_bg.shp"
BUFFER_PATH = DATA_DIR / "mbta_stops_with_buffer" / "mbta_stops_with_buffer_collapsed.geojson"

# ACS-specific data (inside acs/)
ACS_DATA_DIR = ACS_ROOT / "data"
OUTPUT_DIR = ACS_DATA_DIR / "output"
ACS_RAW_DIR = ACS_DATA_DIR / "raw"
ACS_NORMALIZED_DIR = ACS_DATA_DIR / "normalized"

# ACS 5-year block group data: only available from 2013 onward (Census API limitation)
ACS_YEARS = list(range(2013, 2025))  # 2013-2024
DP_TABLES = ["DP02", "DP03", "DP04", "DP05"]
STATE_FIPS = "25"  # Massachusetts

# Census API base URL
CENSUS_API_BASE = "https://api.census.gov/data"


def load_config() -> dict:
    """Load config from acs/config.yaml, then project config.yaml (later overrides earlier for missing keys)."""
    cfg = {}
    for path in CONFIG_PATHS:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if ":" in line:
                        k, v = line.split(":", 1)
                        v = v.split("#")[0].strip().strip('"').strip("'")
                        # Only add if not set or if current value is empty and we have a value
                        if k.strip() not in cfg or (cfg[k.strip()] == "" and v):
                            cfg[k.strip()] = v
    return cfg


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
# Core variables (stable across ACS years) - request first to maximize coverage.
# Extended vars (B25034, B25070) may have different structure in older years.
CORE_VARS = [
    "B01001_001E", "B01002_001E", "B19013_001E", "B17001_002E", "B17001_001E",
    "B25001_001E", "B25077_001E", "B25064_001E", "B25003_002E", "B25003_003E",
    "B23025_002E", "B23025_005E", "B08301_001E", "B08301_003E", "B08301_010E",
    "B08301_017E", "B08301_018E", "B08301_019E", "B08303_001E",
    "B25044_002E", "B25044_009E", "B25044_003E", "B25044_010E",
    "B25024_001E", "B25024_002E", "B25024_003E", "B25024_004E", "B25024_005E",
    "B25024_006E", "B25024_007E", "B25024_008E", "B25024_009E",
    "B25002_001E", "B25002_002E", "B25002_003E", "B25010_001E",
]
# Extended (may fail in older years - try after core)
EXTENDED_VARS = [
    "B25070_001E", "B25070_007E", "B25070_008E", "B25070_009E", "B25070_010E",
    "B25034_001E", "B25034_002E", "B25034_003E", "B25034_004E", "B25034_005E",
    "B25034_006E", "B25034_007E", "B25034_008E", "B25034_009E",
    "B25034_010E", "B25034_011E",
]
FALLBACK_VARS = CORE_VARS + EXTENDED_VARS


def _build_geoid_from_row(row_values: list, headers: list) -> str:
    """
    Build GEOID from Census API response row (list of values + headers).

    Census API returns tract with optional decimals (e.g. "6171.01" for tract 6171.01).
    TIGER uses 6-digit tract codes (e.g. "617101"). We extract digits and pad to 6.
    Values are not modified; this constructs a standard identifier for joins.
    """
    state = county = tract = bg = ""
    for h, v in zip(headers, row_values):
        val = str(v or "").strip()
        h_lower = h.lower()
        if h_lower == "state":
            state = val
        elif h_lower == "county":
            county = val.zfill(3) if val else ""
        elif h_lower == "tract":
            # API may return "6171.01" or "13300"; TIGER needs 6-digit "617101" or "013300"
            tract = re.sub(r"\D", "", val)[:6].zfill(6) if val else ""
        elif "block" in h_lower and "group" in h_lower:
            # Block group 0-9; API may return "1" or "01"
            bg = str(int(float(val))) if val and val != "" else ""
    return state + county + tract + bg


def download_acs_for_block_groups(
    geoids: list[str],
    years: list[int],
    api_key: str,
) -> dict[int, pd.DataFrame]:
    """
    Download ACS Data Profile for block groups, by year.
    Falls back to Detailed Tables if Profile not available at block group level.

    Census API values are stored as returned; no transformation applied.
    """
    counties = sorted(set(g[2:5] for g in geoids))
    results = {}
    geoids = [str(g) for g in geoids]

    for year in years:
        print(f"  Downloading ACS {year}...")
        all_dfs_for_year = []
        var_sets = [(CORE_VARS, "core")]
        if year >= 2015:
            var_sets.append((EXTENDED_VARS, "extended"))
        for vars_list, label in var_sets:
            batch_size = 50
            dfs = []
            for i in range(0, len(vars_list), batch_size):
                batch = vars_list[i : i + batch_size]
                vars_str = ",".join(batch)
                for county in counties:
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
                            print(f"    county {county}: empty response (len={len(data)})")
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
                    except HTTPError as e:
                        try:
                            body = e.fp.read().decode()[:300] if e.fp else str(e)
                        except Exception:
                            body = str(e)
                        print(f"    HTTP {e.code} county {county}: {body}")
                    except (URLError, json.JSONDecodeError) as e:
                        print(f"    Error county {county}: {e}")

            if dfs:
                combined = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["GEOID"])
                combined = combined[combined["GEOID"].isin(geoids)]
                if not combined.empty:
                    all_dfs_for_year.append(combined)

        if all_dfs_for_year:
            combined = all_dfs_for_year[0]
            for d in all_dfs_for_year[1:]:
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


def preprocess_acs(
    acs_by_year: dict[int, pd.DataFrame],
    geoids: list[str],
) -> pd.DataFrame:
    """
    Normalize ACS data across years into long format.

    Filters to geoids and adds year column. Variable values are passed through unchanged.
    """
    print("Preprocessing ACS (normalizing across years)...")
    all_dfs = []

    for year, df in sorted(acs_by_year.items()):
        if df is None or df.empty:
            continue
        df = df[df["GEOID"].isin(geoids)].copy()
        df["year"] = year
        all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    cols = ["GEOID", "year"] + [c for c in combined.columns if c not in ("GEOID", "year")]
    combined = combined[[c for c in cols if c in combined.columns]]
    print(f"  {len(combined)} rows, {len(combined.columns)} columns")
    return combined


def main() -> None:
    """Run full pipeline."""
    cfg = load_config()
    data_dir = Path(cfg.get("data_dir", str(DATA_DIR)))
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    output_dir = Path(cfg.get("output_dir", str(OUTPUT_DIR)))
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    api_key = (cfg.get("census_api_key") or "").strip()
    acs_years_cfg = cfg.get("acs_years", "")
    acs_years = list(ACS_YEARS)
    if acs_years_cfg:
        try:
            if "-" in str(acs_years_cfg):
                start, end = map(int, acs_years_cfg.split("-"))
                acs_years = list(range(start, end + 1))
            else:
                acs_years = [int(y.strip()) for y in str(acs_years_cfg).split(",") if y.strip()]
        except ValueError:
            pass

    acs_years = [y for y in acs_years if y >= 2013]
    if not acs_years:
        print("Warning: no ACS years >= 2013 (block groups unsupported before 2013); skipping ACS.", flush=True)

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

    # Step 5: Preprocess ACS (filter + add year; values unchanged)
    acs_long = pd.DataFrame()
    if acs_by_year:
        acs_long = preprocess_acs(acs_by_year, geoids)
        acs_long.to_csv(output_dir / "block_groups_acs_overlap_long.csv", index=False)
        print(f"Saved {output_dir / 'block_groups_acs_overlap_long.csv'}")

    # Step 6: Join and output (left join; no value modification)
    latest_year = max(acs_by_year.keys()) if acs_by_year else None
    if latest_year is not None and latest_year in acs_by_year:
        acs_latest = acs_by_year[latest_year].copy()
        acs_latest = acs_latest.drop(columns=["year"], errors="ignore")
        acs_latest["GEOID"] = acs_latest["GEOID"].astype(str)
        merged = block_groups.merge(overlap_df, on="GEOID", how="left")
        merged = merged.merge(acs_latest, on="GEOID", how="left")
    else:
        merged = block_groups.merge(overlap_df, on="GEOID", how="left")

    print("Writing output files...", flush=True)
    merged = merged.to_crs(epsg=4326)
    merged.to_file(output_dir / "block_groups_acs_overlap.geojson", driver="GeoJSON")
    merged_csv = merged.drop(columns=["geometry"], errors="ignore")
    merged_csv.to_csv(output_dir / "block_groups_acs_overlap.csv", index=False)

    print(f"\nSaved:")
    print(f"  {output_dir / 'block_groups_acs_overlap.geojson'} ({len(merged)} features)")
    print(f"  {output_dir / 'block_groups_acs_overlap.csv'}")
    if not acs_long.empty:
        print(f"  {output_dir / 'block_groups_acs_overlap_long.csv'} (all years)")


if __name__ == "__main__":
    main()
