"""
Diagnose block groups that appear in geometry but not in ACS/decennial long data.

Run from project root:
  python -m visualization.diagnose_missing_block_groups [acs|decennial]

Helps identify why some block groups are missing from choropleth maps.
"""

import argparse
from pathlib import Path

import pandas as pd

try:
    import geopandas as gpd
except ImportError:
    gpd = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACS_LONG = PROJECT_ROOT / "acs" / "data" / "output" / "block_groups_acs_overlap_long.csv"
ACS_GEO = PROJECT_ROOT / "acs" / "data" / "output" / "block_groups_acs_overlap.geojson"
DECENNIAL_LONG = PROJECT_ROOT / "decennial_census" / "data" / "merged" / "block_groups_decennial_merged_long.csv"
DECENNIAL_GEO = PROJECT_ROOT / "decennial_census" / "data" / "merged" / "block_groups_decennial_merged.geojson"


def diagnose(source: str) -> None:
    """Compare GEOIDs in geometry vs long data."""
    if source == "acs":
        long_path, geo_path = ACS_LONG, ACS_GEO
    else:
        long_path, geo_path = DECENNIAL_LONG, DECENNIAL_GEO

    if not long_path.exists():
        print(f"Long file not found: {long_path}")
        return
    if not geo_path.exists():
        print(f"Geometry file not found: {geo_path}")
        return

    long_df = pd.read_csv(long_path)
    long_df["GEOID"] = long_df["GEOID"].astype(str)

    if gpd is None:
        print("geopandas not installed; reading GeoJSON with json for GEOID list only.")
        import json
        with open(geo_path) as f:
            gj = json.load(f)
        geo_ids = {str(f["properties"].get("GEOID") or f["properties"].get("GEOID10", "")) for f in gj["features"]}
    else:
        geo_gdf = gpd.read_file(geo_path)
        if "GEOID" not in geo_gdf.columns and "GEOID10" in geo_gdf.columns:
            geo_gdf["GEOID"] = geo_gdf["GEOID10"].astype(str)
        geo_ids = set(geo_gdf["GEOID"].astype(str))

    long_ids = set(long_df["GEOID"])

    in_geo_not_long = geo_ids - long_ids
    in_long_not_geo = long_ids - geo_ids

    print(f"\n--- {source.upper()} ---")
    print(f"Block groups in geometry: {len(geo_ids)}")
    print(f"Block groups in long (any year): {len(long_ids)}")
    print(f"In geometry but NOT in long (missing from maps): {len(in_geo_not_long)}")
    print(f"In long but NOT in geometry: {len(in_long_not_geo)}")

    if in_geo_not_long and gpd:
        geo_gdf = gpd.read_file(geo_path)
        if "GEOID" not in geo_gdf.columns:
            geo_gdf["GEOID"] = geo_gdf["GEOID10"].astype(str)
        aland_col = "ALAND10" if "ALAND10" in geo_gdf.columns else "ALAND"
        missing = geo_gdf[geo_gdf["GEOID"].astype(str).isin(in_geo_not_long)]
        if aland_col in missing.columns:
            top = missing.nlargest(10, aland_col)[["GEOID", aland_col]]
            print(f"\nLargest missing (by land area):")
            print(top.to_string(index=False))
        print(f"\nSample missing GEOIDs: {list(in_geo_not_long)[:10]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose missing block groups in geometry vs long data.")
    parser.add_argument("source", choices=["acs", "decennial"], default="acs", nargs="?")
    args = parser.parse_args()
    diagnose(args.source)


if __name__ == "__main__":
    main()
