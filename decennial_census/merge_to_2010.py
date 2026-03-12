"""
Assemble merged decennial output: 2010 block group geography with 1990-2020 data.

NHGIS geographically standardized time series already provides 1990, 2000, 2010, 2020
data on 2010 block group geography. This module joins that data with 2010 boundaries
and overlap counts.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd


def build_merged_output(
    boundaries_2010: gpd.GeoDataFrame,
    overlap_df: pd.DataFrame,
    timeseries_long: pd.DataFrame,
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """
    Build merged GeoJSON and long-format CSV (2010 geography, all years).

    Parameters
    ----------
    boundaries_2010 : gpd.GeoDataFrame
        2010 block groups clipped to MBTA, with GEOID.
    overlap_df : pd.DataFrame
        Overlap counts from compute_overlap_counts (on 2010 centroids).
    timeseries_long : pd.DataFrame
        NHGIS time series data: year, GEOID, census variables.

    Returns
    -------
    tuple[gpd.GeoDataFrame, pd.DataFrame]
        (merged GeoJSON-ready GDF for latest year, long-format CSV DataFrame).
    """
    # Ensure GEOID types match
    boundaries_2010 = boundaries_2010.copy()
    boundaries_2010["GEOID"] = boundaries_2010["GEOID"].astype(str)
    overlap_df = overlap_df.copy()
    overlap_df["GEOID"] = overlap_df["GEOID"].astype(str)
    timeseries_long = timeseries_long.copy()
    timeseries_long["GEOID"] = timeseries_long["GEOID"].astype(str)

    # Join overlap to boundaries
    merged_geo = boundaries_2010.merge(overlap_df, on="GEOID", how="left")

    # Build long format: each row = year + GEOID + vars + overlap
    # Overlap is same for all years (2010 geography)
    geoids = merged_geo["GEOID"].unique()
    years = sorted(timeseries_long["year"].unique()) if "year" in timeseries_long.columns else []

    # Get overlap columns (exclude GEOID)
    overlap_cols = [c for c in overlap_df.columns if c != "GEOID" and c.startswith("overlap_")]

    long_rows = []
    for year in years:
        ts_year = timeseries_long[timeseries_long["year"] == year]
        if ts_year.empty:
            continue

        # Census vars for this year (exclude GEOID, year)
        var_cols = [c for c in ts_year.columns if c not in ("GEOID", "year", "geometry")]
        ts_sub = ts_year[["GEOID"] + var_cols].copy()
        ts_sub["year"] = year

        # Join overlap (same for all years)
        overlap_sub = overlap_df[["GEOID"] + overlap_cols]
        merged_row = ts_sub.merge(overlap_sub, on="GEOID", how="left")
        long_rows.append(merged_row)

    if long_rows:
        long_df = pd.concat(long_rows, ignore_index=True)
    else:
        # No timeseries: create minimal long from boundaries + overlap
        long_df = merged_geo.drop(columns=["geometry"], errors="ignore").copy()
        long_df["year"] = 2020  # placeholder
        cols = ["GEOID", "year"] + ([c for c in overlap_cols if c in long_df.columns] or [])
        long_df = long_df[cols]

    # For merged GeoJSON: use latest year's data + geometry
    latest_year = max(years) if years else 2020
    latest_ts = timeseries_long[timeseries_long["year"] == latest_year] if years else pd.DataFrame()
    if not latest_ts.empty:
        var_cols = [c for c in latest_ts.columns if c not in ("GEOID", "year", "geometry")]
        latest_data = latest_ts[["GEOID"] + var_cols].drop_duplicates(subset=["GEOID"])
        merged_geo = merged_geo.drop(columns=var_cols, errors="ignore")
        merged_geo = merged_geo.merge(latest_data, on="GEOID", how="left")

    return merged_geo, long_df
