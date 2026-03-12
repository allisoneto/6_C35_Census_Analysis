"""
Build block groups with decennial census data and MBTA stop buffer overlap counts.

Pipeline (merged only):
  1. Clip 2010 block groups to MBTA Communities
  2. Flatten stop buffers, compute overlap counts
  3. Load NHGIS time series (1990-2020 standardized to 2010 geography)
  4. Preprocess (variable alignment, GEOID normalization)
  5. Output merged GeoJSON and long-format CSV

Usage:
  python -m decennial_census.build_block_groups_decennial_overlap

Requires:
  - data/mbta_communities/mbta_communities.geojson
  - data/mbta_stops_with_buffer/mbta_stops_with_buffer_collapsed.geojson
  - Block group boundaries (2010):
    - data/census/tl_2010_25_bg.shp or decennial_census/data/raw/tl_2010_25_bg.shp
    - Or tl_2010_25_bg10.shp (Census 2010 TIGER naming)
  - NHGIS files (place in decennial_census/data/raw/):
    - nhgis_timeseries_2010_bg.csv (required)

Output:
  decennial_census/data/merged/block_groups_decennial_merged.geojson
  decennial_census/data/merged/block_groups_decennial_merged_long.csv
"""

from pathlib import Path

import geopandas as gpd

import sys

# Ensure project root (parent of decennial_census) is in sys.path for imports
PARENT = Path(__file__).resolve().parent.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))


from mbta_overlap_utils import (
    clip_block_groups_to_mbta,
    compute_overlap_counts,
    flatten_stop_buffers,
)

from decennial_census.download_decennial import load_nhgis_time_series
from decennial_census.merge_to_2010 import build_merged_output
from decennial_census.preprocess_decennial import preprocess_for_merged

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
DECENNIAL_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DECENNIAL_ROOT.parent
CONFIG_PATH = DECENNIAL_ROOT / "config.yaml"
PROJECT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# Paths (relative to project root for shared data)
DATA_DIR = PROJECT_ROOT / "data"
MBTA_BOUNDARIES_PATH = DATA_DIR / "mbta_communities" / "mbta_communities.geojson"
BUFFER_PATH = DATA_DIR / "mbta_stops_with_buffer" / "mbta_stops_with_buffer_collapsed.geojson"

# Block group boundaries (2010 census geography only)
BG_2010_PATHS = [
    DATA_DIR / "census" / "tl_2010_25_bg.shp",
    DATA_DIR / "census" / "tl_2010_25_bg10.shp",  # Census 2010 TIGER naming
    DECENNIAL_ROOT / "data" / "raw" / "tl_2010_25_bg.shp",
    DECENNIAL_ROOT / "data" / "raw" / "tl_2010_25_bg10.shp",
]

MAPPING_PATH = DECENNIAL_ROOT / "data" / "decennial_variable_mapping.csv"
RAW_DIR = DECENNIAL_ROOT / "data" / "raw"
MERGED_DIR = DECENNIAL_ROOT / "data" / "merged"


def load_config() -> dict:
    """Load config from decennial config.yaml, fall back to project config for missing keys."""
    cfg = {}
    for path in [CONFIG_PATH, PROJECT_CONFIG_PATH]:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if ":" in line:
                        k, v = line.split(":", 1)
                        v = v.split("#")[0].strip().strip('"').strip("'")
                        # Only add if not already set (decennial overrides project)
                        if k.strip() not in cfg or (cfg[k.strip()] == "" and v):
                            cfg[k.strip()] = v
    return cfg


def _resolve_bg_2010_path() -> Path | None:
    """Return first existing 2010 block group shapefile path."""
    for p in BG_2010_PATHS:
        if p.exists():
            return p
    return None


def _ensure_geoid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure GEOID column exists; construct from components if needed."""
    if "GEOID" in gdf.columns:
        return gdf
    cols = ["STATEFP", "COUNTYFP", "TRACTCE", "BLKGRPCE"]
    if all(c in gdf.columns for c in cols):
        gdf = gdf.copy()
        gdf["GEOID"] = (
            gdf["STATEFP"].astype(str).str.zfill(2)
            + gdf["COUNTYFP"].astype(str).str.zfill(3)
            + gdf["TRACTCE"].astype(str).str.zfill(6)
            + gdf["BLKGRPCE"].astype(str)
        )
        return gdf
    return gdf


def main() -> None:
    """Run decennial pipeline (merged only: 2010 geography, NHGIS time series)."""
    cfg = load_config()

    # Resolve paths
    mbta_path = Path(cfg.get("mbta_boundaries", str(MBTA_BOUNDARIES_PATH)))
    if not mbta_path.is_absolute():
        mbta_path = PROJECT_ROOT / mbta_path
    buffer_path = Path(cfg.get("buffer_path", str(BUFFER_PATH)))
    if not buffer_path.is_absolute():
        buffer_path = PROJECT_ROOT / buffer_path

    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Flatten buffers (shared with ACS pipeline)
    buffers_gdf = flatten_stop_buffers(buffer_path)

    # -------------------------------------------------------------------------
    # Merged version (2010 geography)
    # -------------------------------------------------------------------------
    print("\n--- Merged version (2010 geography) ---")
    bg_2010_path = _resolve_bg_2010_path()
    if not bg_2010_path:
        print("  Error: 2010 block group shapefile not found.")
        print("  Place tl_2010_25_bg.shp in data/census/ or decennial_census/data/raw/")
        print("  Download: https://www2.census.gov/geo/tiger/TIGER2010/BG/2010/tl_2010_25_bg10.zip")
        return

    block_groups_2010 = clip_block_groups_to_mbta(bg_2010_path, mbta_path)
    block_groups_2010 = _ensure_geoid(block_groups_2010)
    geoids_2010 = block_groups_2010["GEOID"].tolist()

    overlap_2010 = compute_overlap_counts(block_groups_2010, buffers_gdf)

    # Load NHGIS time series (2010 geography)
    ts_df = load_nhgis_time_series(RAW_DIR)
    if ts_df.empty:
        print("  Error: NHGIS time series not found.")
        print("  Place nhgis_timeseries_2010_bg.csv in decennial_census/data/raw/")
        return

    ts_processed = preprocess_for_merged(ts_df, MAPPING_PATH, geoids_2010)
    merged_geo, merged_long = build_merged_output(
        block_groups_2010, overlap_2010, ts_processed
    )
    merged_geo = merged_geo.to_crs(epsg=4326)
    merged_geo.to_file(MERGED_DIR / "block_groups_decennial_merged.geojson", driver="GeoJSON")
    merged_long.to_csv(MERGED_DIR / "block_groups_decennial_merged_long.csv", index=False)
    print(f"  Saved {MERGED_DIR / 'block_groups_decennial_merged.geojson'}")
    print(f"  Saved {MERGED_DIR / 'block_groups_decennial_merged_long.csv'} ({len(merged_long)} rows)")

    print("\nDone.")


if __name__ == "__main__":
    main()
