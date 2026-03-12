"""
Verify MBTA Communities list against MassGIS municipalities.

Loads MassGIS TOWNSSURVEY_POLYM shapefile and matches against mbta_communities_list.csv.
Reports matched count, unmatched names, and handles known aliases (e.g. Manchester =
Manchester-by-the-Sea). Updates the CSV with massgis_match column for join.

Usage:
  python verify_mbta_communities.py

Output:
  data/mbta_communities_list.csv (updated with massgis_match)
  Console report of verification results
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
MBTA_LIST_PATH = DATA_DIR / "mbta_communities_list.csv"
MASSGIS_PATH = DATA_DIR / "mbta_communities" / "TOWNSSURVEY_POLYM.shp"
OUTPUT_PATH = DATA_DIR / "mbta_communities" / "mbta_communities.geojson"

# Known aliases: MBTA list name -> MassGIS TOWN value
# Manchester in MBTA list = Manchester-by-the-Sea in MassGIS
NAME_ALIASES = {
    "Manchester": "Manchester-by-the-Sea",
}


def normalize_name(s: str) -> str:
    """Normalize name for comparison: uppercase, strip."""
    return str(s).strip().upper() if pd.notna(s) else ""


def main() -> None:
    """Verify MBTA Communities against MassGIS and update list."""
    print("Loading MBTA Communities list...")
    mbta_df = pd.read_csv(MBTA_LIST_PATH)
    mbta_names = set(mbta_df["name"].str.strip())

    print("Loading MassGIS municipalities...")
    muni_gdf = gpd.read_file(MASSGIS_PATH)
    massgis_names = set(muni_gdf["TOWN"].str.strip())

    # Build lookup: normalized (lowercase for display) -> original MassGIS name
    massgis_lookup = {t.upper(): t for t in massgis_names}

    # Match each MBTA name
    matched = []
    unmatched = []
    massgis_matches = []

    for name in mbta_df["name"]:
        name_clean = name.strip()
        # Apply alias if needed
        lookup_name = NAME_ALIASES.get(name_clean, name_clean)
        lookup_upper = normalize_name(lookup_name)

        if lookup_upper in massgis_lookup:
            matched.append(name_clean)
            massgis_matches.append(massgis_lookup[lookup_upper])
        else:
            unmatched.append(name_clean)
            massgis_matches.append("")

    mbta_df["massgis_match"] = massgis_matches

    # Save updated CSV
    mbta_df.to_csv(MBTA_LIST_PATH, index=False)
    print(f"\nUpdated {MBTA_LIST_PATH} with massgis_match column")

    # Report
    print(f"\n--- Verification Report ---")
    print(f"Matched: {len(matched)} / {len(mbta_df)}")
    if unmatched:
        print(f"Unmatched MBTA names: {unmatched}")
    else:
        print("All MBTA Communities matched to MassGIS.")

    # Filter MassGIS to MBTA Communities only and save GeoJSON
    mbta_massgis_names = [m for m in massgis_matches if m]
    muni_mbta = muni_gdf[muni_gdf["TOWN"].isin(mbta_massgis_names)].copy()
    muni_mbta = muni_mbta.to_crs(epsg=4326)
    muni_mbta.to_file(OUTPUT_PATH, driver="GeoJSON")
    print(f"\nSaved {len(muni_mbta)} MBTA Community boundaries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
