"""
Build 2010 census blocks with decennial data and MBTA stop buffer overlap counts.

Separate pipeline from block groups (build_block_groups_decennial_overlap.py).
Uses 2010 Census block geography; decennial data is block-level only.

Pipeline:
  1. Clip 2010 census blocks to MBTA Communities
  2. Flatten stop buffers, compute overlap counts (centroid within buffer)
  3. Download 2010 decennial block data from Census API
  4. Output GeoJSON and CSV

Usage:
  python -m decennial_census.build_blocks_2010_overlap
  python -m decennial_census.build_blocks_2010_overlap --dry-run

Requires:
  - config.yaml with census_api_key
  - data/mbta_communities/mbta_communities.geojson
  - data/mbta_stops_with_buffer/mbta_stops_with_buffer_collapsed.geojson
  - 2010 Census blocks: data/census/tl_2010_25_tabblock10.shp or decennial_census/data/raw/
    (download from https://www2.census.gov/geo/tiger/TIGER2010/TABBLOCK/2010/)

Output:
  decennial_census/data/blocks_2010/blocks_2010_decennial_overlap.geojson
  decennial_census/data/blocks_2010/blocks_2010_decennial_overlap.csv
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

PARENT = Path(__file__).resolve().parent.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

from mbta_overlap_utils import clip_blocks_to_mbta, compute_overlap_counts, flatten_stop_buffers

from decennial_census.download_blocks import download_blocks_2010

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
DECENNIAL_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DECENNIAL_ROOT.parent
CONFIG_PATH = DECENNIAL_ROOT / "config.yaml"
PROJECT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"

DATA_DIR = PROJECT_ROOT / "data"
MBTA_BOUNDARIES_PATH = DATA_DIR / "mbta_communities" / "mbta_communities.geojson"
BUFFER_PATH = DATA_DIR / "mbta_stops_with_buffer" / "mbta_stops_with_buffer_collapsed.geojson"

# 2010 block shapefile paths (check multiple locations)
BLOCK_PATHS = [
    DATA_DIR / "census" / "tl_2010_25_tabblock10.shp",
    DATA_DIR / "census" / "tl_2019_25_tabblock10.shp",  # 2019 TIGER with 2010 blocks
    DECENNIAL_ROOT / "data" / "raw" / "tl_2010_25_tabblock10.shp",
    DECENNIAL_ROOT / "data" / "raw" / "tl_2019_25_tabblock10.shp",
]

BLOCKS_OUTPUT_DIR = DECENNIAL_ROOT / "data" / "blocks_2010"


def load_config() -> dict:
    """Load config from decennial or project config.yaml."""
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
                        if k.strip() not in cfg or (cfg[k.strip()] == "" and v):
                            cfg[k.strip()] = v
    return cfg


def _resolve_block_path() -> Path | None:
    """Return first existing block shapefile path."""
    for p in BLOCK_PATHS:
        if p.exists():
            return p
    return None


def main() -> None:
    """Run 2010 census blocks pipeline."""
    parser = argparse.ArgumentParser(
        description="Build 2010 census blocks with decennial data and MBTA overlap"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Census API download and file writes; print what would be done",
    )
    args = parser.parse_args()
    dry_run = args.dry_run

    cfg = load_config()
    api_key = (cfg.get("census_api_key") or "").strip()

    mbta_path = Path(cfg.get("mbta_boundaries", str(MBTA_BOUNDARIES_PATH)))
    if not mbta_path.is_absolute():
        mbta_path = PROJECT_ROOT / mbta_path
    buffer_path = Path(cfg.get("buffer_path", str(BUFFER_PATH)))
    if not buffer_path.is_absolute():
        buffer_path = PROJECT_ROOT / buffer_path

    BLOCKS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n--- 2010 Census Blocks Pipeline ---")
    if dry_run:
        print("  [DRY RUN] No downloads or writes will be performed\n")

    # 1. Load block shapefile
    block_path = _resolve_block_path()
    if not block_path:
        print("  ERROR: 2010 block shapefile not found.")
        print("  Place tl_2010_25_tabblock10.shp in data/census/ or decennial_census/data/raw/")
        print("  Download: https://www2.census.gov/geo/tiger/TIGER2010/TABBLOCK/2010/")
        return

    print(f"  Using blocks: {block_path}")

    # 2. Clip blocks to MBTA
    blocks = clip_blocks_to_mbta(block_path, mbta_path)
    geoids = blocks["GEOID"].tolist()
    print(f"  {len(geoids)} blocks in MBTA Communities")

    # 3. Flatten buffers and compute overlap
    buffers_gdf = flatten_stop_buffers(buffer_path)
    overlap_df = compute_overlap_counts(blocks, buffers_gdf)

    # 4. Download 2010 decennial block data
    if api_key:  # or not dry_run
        census_df = download_blocks_2010(
            geoids,
            api_key,
            dry_run=dry_run,
            delay_seconds=0.0 if dry_run else 0.1,
        )
    else:
        print("  No census_api_key; skipping download.")
        census_df = pd.DataFrame()

    # 5. Merge and output
    if not dry_run:
        if not census_df.empty:
            census_df = census_df.drop(columns=["state", "county", "tract", "block"], errors="ignore")
            merged = blocks.merge(overlap_df, on="GEOID", how="left")
            merged = merged.merge(census_df, on="GEOID", how="left")
        else:
            merged = blocks.merge(overlap_df, on="GEOID", how="left")

        merged = merged.to_crs(epsg=4326)
        merged.to_file(BLOCKS_OUTPUT_DIR / "blocks_2010_decennial_overlap.geojson", driver="GeoJSON")
        merged.drop(columns=["geometry"], errors="ignore").to_csv(
            BLOCKS_OUTPUT_DIR / "blocks_2010_decennial_overlap.csv", index=False
        )
        print(f"\n  Saved {BLOCKS_OUTPUT_DIR / 'blocks_2010_decennial_overlap.geojson'}")
        print(f"  Saved {BLOCKS_OUTPUT_DIR / 'blocks_2010_decennial_overlap.csv'} ({len(merged)} blocks)")
    else:
        print(f"\n  [dry-run] Would write {len(blocks)} blocks to {BLOCKS_OUTPUT_DIR}/")

    print("\nDone.")


if __name__ == "__main__":
    main()
