"""
Shared utilities for MBTA stop buffer overlap with census geography.

Used by ACS, decennial block group, and census block pipelines. Provides:
  - clip_blocks_to_mbta: Clip census blocks to MBTA Community boundaries
  - clip_block_groups_to_mbta: Clip block groups to MBTA Community boundaries
  - flatten_stop_buffers: Flatten collapsed buffer GeoJSON to one row per stop-route
  - compute_overlap_counts: Count buffers containing each unit centroid (blocks or BGs)

Data integrity: These functions operate on geometry and identifiers only.
They do not modify census variable values; overlap counts are computed from
spatial relationships (centroid within buffer).
"""

import json
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape


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


def clip_blocks_to_mbta(
    blocks_path: Path,
    mbta_boundaries_path: Path,
) -> gpd.GeoDataFrame:
    """
    Clip census blocks to MBTA Community boundaries.

    Works with 2010 TIGER block shapefiles (tl_*_tabblock10.shp).
    Ensures GEOID column exists (from GEOID10 or constructed from components).

    Parameters
    ----------
    blocks_path : Path
        Path to TIGER census block shapefile (e.g. tl_2010_25_tabblock10.shp).
    mbta_boundaries_path : Path
        Path to MBTA communities GeoJSON.

    Returns
    -------
    gpd.GeoDataFrame
        Census blocks that intersect MBTA Communities.
    """
    print("Loading census blocks and MBTA boundaries...", flush=True)
    blocks = gpd.read_file(blocks_path)
    mbta = gpd.read_file(mbta_boundaries_path)

    mbta = mbta.to_crs(blocks.crs)
    clipped = gpd.sjoin(blocks, mbta[["geometry"]], how="inner", predicate="intersects")
    clipped = clipped.drop(columns=[c for c in clipped.columns if c.startswith("index_")])

    # Ensure GEOID exists (2010 blocks use GEOID10)
    if "GEOID" not in clipped.columns:
        if "GEOID10" in clipped.columns:
            clipped = clipped.copy()
            clipped["GEOID"] = clipped["GEOID10"].astype(str)
        elif all(c in clipped.columns for c in ["STATEFP10", "COUNTYFP10", "TRACTCE10", "BLOCKCE10"]):
            clipped = clipped.copy()
            clipped["GEOID"] = (
                clipped["STATEFP10"].astype(str).str.zfill(2)
                + clipped["COUNTYFP10"].astype(str).str.zfill(3)
                + clipped["TRACTCE10"].astype(str).str.zfill(6)
                + clipped["BLOCKCE10"].astype(str).str.zfill(4)
            )
        else:
            raise ValueError(
                "Block shapefile must have GEOID, GEOID10, or STATEFP10/COUNTYFP10/TRACTCE10/BLOCKCE10"
            )

    clipped = clipped.drop_duplicates(subset=["GEOID"])
    print(f"  Clipped to {len(clipped)} census blocks in MBTA Communities")
    return clipped


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


def compute_overlap_counts(
    block_groups: gpd.GeoDataFrame,
    buffers_gdf: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    For each unit centroid, count buffers that contain it, by route_desc and route_color.

    Works with block groups or census blocks; requires GEOID and geometry columns.

    Parameters
    ----------
    block_groups : gpd.GeoDataFrame
        Census units (block groups or blocks) with GEOID and geometry.
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
