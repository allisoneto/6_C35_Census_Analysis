"""
Shared utilities for TOD visualization: data loading, merge on GEOID, transformations.

Provides unified load_data(source) for ACS and decennial, plus apply_transformation()
for raw, count, per_aland, per_population, and proportion.
"""

import re
from pathlib import Path
from typing import Literal

import geopandas as gpd
import pandas as pd

# Project root (parent of visualization/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Paths by source
ACS_LONG_PATH = PROJECT_ROOT / "acs" / "data" / "output" / "block_groups_acs_overlap_long.csv"
ACS_GEO_PATH = PROJECT_ROOT / "acs" / "data" / "output" / "block_groups_acs_overlap.geojson"
ACS_MAPPING_PATH = PROJECT_ROOT / "acs" / "data" / "acs_variable_mapping.csv"

DECENNIAL_LONG_PATH = PROJECT_ROOT / "decennial_census" / "data" / "merged" / "block_groups_decennial_merged_long.csv"
DECENNIAL_GEO_PATH = PROJECT_ROOT / "decennial_census" / "data" / "merged" / "block_groups_decennial_merged.geojson"
DECENNIAL_MAPPING_PATH = PROJECT_ROOT / "decennial_census" / "data" / "decennial_variable_mapping_nhgis.csv"

# MBTA route lines for map overlay (GeoJSON with route_color, route_id, etc.)
MBTA_LINES_PATH = PROJECT_ROOT / "data" / "mbta_lines" / "lines.geojson"
MBTA_LINE_WIDTH = 0.5  # Thin lines on top of choropleths

# Boston zoom: extent for zoomed choropleths. Bounds in WGS84 (lon, lat): west, south, east, north.
# Tight zoom on core Red/Green area: Boston, Cambridge, Somerville, Brookline, Jamaica Plain.
# Excludes Braintree/Quincy (south), Riverside/Newton (west), Wonderland (northeast).
BOSTON_ZOOM_BOUNDS_WGS84 = (-71.17, 42.30, -71.04, 42.40)

# Census null sentinel (ACS uses this for null/median)
ACS_NULL = -666666666


def load_data(
    source: Literal["acs", "decennial"],
) -> tuple[pd.DataFrame, gpd.GeoDataFrame, pd.DataFrame]:
    """
    Load long-format data, geometry (with ALAND), and variable mapping for a source.

    Parameters
    ----------
    source : {"acs", "decennial"}
        Data source to load.

    Returns
    -------
    tuple of (pd.DataFrame, gpd.GeoDataFrame, pd.DataFrame)
        (long_df, geo_gdf, mapping_df). long_df has GEOID, year, census vars.
        geo_gdf has GEOID, geometry, and land area (ALAND or ALAND10).
        mapping_df has variable, human_readable_name, transformations, denominator, pie_group.
    """
    if source == "acs":
        long_path = ACS_LONG_PATH
        geo_path = ACS_GEO_PATH
        mapping_path = ACS_MAPPING_PATH
    else:
        long_path = DECENNIAL_LONG_PATH
        geo_path = DECENNIAL_GEO_PATH
        mapping_path = DECENNIAL_MAPPING_PATH

    long_df = pd.read_csv(long_path)
    long_df["GEOID"] = long_df["GEOID"].astype(str)

    geo_gdf = gpd.read_file(geo_path)
    # Normalize GEOID column name (decennial may use GEOID10 or GEOID)
    if "GEOID" not in geo_gdf.columns and "GEOID10" in geo_gdf.columns:
        geo_gdf["GEOID"] = geo_gdf["GEOID10"].astype(str)
    else:
        geo_gdf["GEOID"] = geo_gdf["GEOID"].astype(str)

    mapping_df = pd.read_csv(mapping_path)

    return long_df, geo_gdf, mapping_df


def get_aland_column(geo_gdf: gpd.GeoDataFrame, source: Literal["acs", "decennial"]) -> str:
    """
    Return the land area column name for the given source.

    Parameters
    ----------
    geo_gdf : gpd.GeoDataFrame
        Geometry dataframe (used to check which column exists).
    source : {"acs", "decennial"}
        Data source.

    Returns
    -------
    str
        Column name for land area (ALAND or ALAND10).
    """
    if source == "acs":
        return "ALAND" if "ALAND" in geo_gdf.columns else "ALAND10"
    return "ALAND10" if "ALAND10" in geo_gdf.columns else "ALAND"


def get_population_column(source: Literal["acs", "decennial"]) -> str:
    """Return the total population variable for the given source."""
    return "B01001_001E" if source == "acs" else "CL8AA"


def merge_long_with_geometry(
    long_df: pd.DataFrame,
    geo_gdf: gpd.GeoDataFrame,
    aland_col: str,
    *,
    geometry_as_base: bool = True,
) -> gpd.GeoDataFrame:
    """
    Merge long-format data with geometry on GEOID.

    Parameters
    ----------
    long_df : pd.DataFrame
        Long data with GEOID, year, census vars.
    geo_gdf : gpd.GeoDataFrame
        Geometry with GEOID, geometry, and land area.
    aland_col : str
        Name of land area column (ALAND or ALAND10).
    geometry_as_base : bool, optional
        If True (default), keep all block groups from geometry; block groups
        with no long data get NaN for census vars. If False, keep only block
        groups that appear in long_df (legacy behavior).

    Returns
    -------
    gpd.GeoDataFrame
        Merged dataframe. Keeps geometry and aland from geo_gdf.
    """
    geo_subset = geo_gdf[["GEOID", "geometry", aland_col]].copy()
    if geometry_as_base:
        # Keep all block groups from geometry; missing long data -> NaN
        merged = geo_subset.merge(long_df, on="GEOID", how="left")
    else:
        merged = long_df.merge(geo_subset, on="GEOID", how="left")
    # Defragment: merge of wide long_df (many census columns) creates fragmented
    # GeoDataFrame; .copy() yields contiguous memory and avoids PerformanceWarning.
    return merged.copy()


def apply_transformation(
    value: float,
    transform: str,
    *,
    denominator: float | None = None,
    aland: float | None = None,
    population: float | None = None,
    null_sentinel: float = ACS_NULL,
) -> float | None:
    """
    Apply a transformation to a raw value.

    Parameters
    ----------
    value : float
        Raw census value.
    transform : str
        One of: raw, count, per_aland, per_population, proportion.
    denominator : float, optional
        Denominator for proportion (e.g., total housing units).
    aland : float, optional
        Land area in sq m for per_aland.
    population : float, optional
        Total population for per_population.
    null_sentinel : float
        Value treated as null (e.g., -666666666 for ACS).

    Returns
    -------
    float or None
        Transformed value, or None if invalid/missing.
    """
    if value is None or (null_sentinel is not None and value == null_sentinel):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None

    if transform == "raw" or transform == "count":
        return v

    if transform == "per_aland":
        if aland is None or aland <= 0:
            return None
        return v / aland

    if transform == "per_population":
        if population is None or population <= 0:
            return None
        return v / population

    if transform == "proportion":
        if denominator is None or denominator <= 0:
            return None
        return v / denominator

    return None


def resolve_denominator(
    denom_spec: str,
    row: pd.Series,
    source: Literal["acs", "decennial"],
) -> float | None:
    """
    Resolve denominator from mapping spec (e.g., B25001_001E or var1+var2 for sums).

    Parameters
    ----------
    denom_spec : str
        Denominator variable(s), possibly with + for sums (e.g., var1+var2).
    row : pd.Series
        Row of data with variable values.
    source : {"acs", "decennial"}
        Data source (for context; column names are in the row).

    Returns
    -------
    float or None
        Sum of denominator columns if present, else None.
    """
    if not denom_spec or pd.isna(denom_spec):
        return None
    parts = str(denom_spec).split("+")
    total = 0.0
    for p in parts:
        col = p.strip()
        if col and col in row.index:
            val = row[col]
            if pd.notna(val) and val != ACS_NULL:
                try:
                    total += float(val)
                except (TypeError, ValueError):
                    pass
    return total if total > 0 else None


# Chart formatting: source labels and attribution for comprehensive titles/annotations
SOURCE_LABELS: dict[str, str] = {
    "acs": "ACS 5-Year Estimates",
    "decennial": "Decennial Census",
}
DATA_ATTRIBUTION = "Source: U.S. Census Bureau. Geography: Census block groups."
TRANSFORM_LABELS: dict[str, str] = {
    "raw": "raw value",
    "count": "count",
    "per_aland": "per sq m",
    "per_population": "per capita",
    "proportion": "proportion",
}


def get_source_label(source: Literal["acs", "decennial"]) -> str:
    """Return human-readable data source label for chart titles/annotations."""
    return SOURCE_LABELS.get(source, source)


def get_transform_label(transform: str) -> str:
    """Return human-readable transformation label (e.g., 'per sq m')."""
    return TRANSFORM_LABELS.get(transform, transform)


def get_boston_zoom_bounds(
    target_crs,
    mbta_path: Path | None = None,
    buffer_deg: float = 0.0,
) -> tuple[float, float, float, float]:
    """
    Get bounding box for Boston area (Red/Green core) in target CRS.

    Uses BOSTON_ZOOM_BOUNDS_WGS84 for a tight zoom on Boston, Cambridge,
    Somerville, Brookline, Jamaica Plain. Returns (minx, miny, maxx, maxy).

    Parameters
    ----------
    target_crs
        CRS of the geometry to clip to (e.g., plot_gdf.crs).
    mbta_path : Path, optional
        Unused; kept for API compatibility.
    buffer_deg : float, optional
        Buffer in degrees to expand bounds. Default 0.

    Returns
    -------
    tuple of float
        (minx, miny, maxx, maxy) in target_crs.
    """
    minx, miny, maxx, maxy = BOSTON_ZOOM_BOUNDS_WGS84
    if buffer_deg:
        minx -= buffer_deg
        miny -= buffer_deg
        maxx += buffer_deg
        maxy += buffer_deg
    box_gdf = gpd.GeoDataFrame(
        geometry=[__box_to_polygon(minx, miny, maxx, maxy)],
        crs="EPSG:4326",
    )
    box_gdf = box_gdf.to_crs(target_crs)
    return tuple(box_gdf.total_bounds)


def __box_to_polygon(minx: float, miny: float, maxx: float, maxy: float):
    """Create a box polygon from bounds (for CRS transform)."""
    from shapely.geometry import box

    return box(minx, miny, maxx, maxy)


def plot_mbta_routes(ax, plot_gdf: gpd.GeoDataFrame, mbta_path: Path | None = None) -> None:
    """
    Overlay MBTA route lines on the given axes using their assigned colors.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes to draw on (choropleth already plotted).
    plot_gdf : gpd.GeoDataFrame
        Block group geometry (used for CRS and bounds).
    mbta_path : Path, optional
        Path to MBTA lines GeoJSON. Default: MBTA_LINES_PATH.
    """
    path = mbta_path or MBTA_LINES_PATH
    if not path.exists():
        return
    try:
        routes = gpd.read_file(path)
    except Exception:
        return
    if routes.empty:
        return
    # Exclude bus routes: GTFS route_type 3 = Bus; or route_desc contains "Bus"
    if "route_type" in routes.columns:
        routes = routes[routes["route_type"] != 3].copy()
    elif "route_desc" in routes.columns:
        routes = routes[~routes["route_desc"].astype(str).str.lower().str.contains("bus", na=False)].copy()
    if routes.empty:
        return
    target_crs = plot_gdf.crs
    if routes.crs != target_crs:
        routes = routes.to_crs(target_crs)
    color_col = "route_color" if "route_color" in routes.columns else None
    for idx, row in routes.iterrows():
        color = "#333333"
        if color_col and pd.notna(row.get(color_col)):
            c = str(row[color_col]).strip()
            if c and not c.startswith("#"):
                c = "#" + c
            if c:
                color = c
        # row.geometry is a Shapely MultiLineString; wrap in GeoSeries to use .plot()
        gpd.GeoSeries([row.geometry], crs=routes.crs).plot(
            ax=ax, color=color, linewidth=MBTA_LINE_WIDTH, zorder=10
        )


def get_var_label(var_code: str, mapping_df: pd.DataFrame) -> str:
    """Return human-readable axis label for a variable (e.g., overlap_total -> Transit overlap area)."""
    if var_code == "overlap_total":
        return "Transit overlap area (sq m)"
    if var_code.startswith("overlap_"):
        return var_code.replace("_", " ").title()
    row = mapping_df[mapping_df["variable"] == var_code]
    if not row.empty:
        return str(row["human_readable_name"].iloc[0])
    return var_code.replace("_", " ").title()


def human_readable_dir_name(name: str) -> str:
    """
    Convert human-readable name or snake_case to safe directory name.

    Examples: "Total population" -> "Total_Population", "housing_cost_burden" -> "Housing_Cost_Burden".

    Parameters
    ----------
    name : str
        Variable/group name (human-readable or snake_case).

    Returns
    -------
    str
        Safe directory name (alphanumeric + underscores).
    """
    s = str(name).strip()
    if not s:
        return "unknown"
    # Convert snake_case to Title Case for readability
    s = s.replace("_", " ").title()
    # Remove special chars, collapse spaces/hyphens to single underscore
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s).strip("_")
    return s or "unknown"


def get_pie_groups(mapping_df: pd.DataFrame, source: Literal["acs", "decennial"]) -> dict:
    """
    Build pie_group -> {denominator, components} from mapping.

    Parameters
    ----------
    mapping_df : pd.DataFrame
        Variable mapping with denominator, pie_group columns.
    source : {"acs", "decennial"}
        Data source (unused; structure is same).

    Returns
    -------
    dict
        {pie_group_name: {"denominator": str, "components": [str, ...]}}
    """
    groups: dict = {}
    for _, row in mapping_df.iterrows():
        pg = row.get("pie_group")
        if pd.isna(pg) or not str(pg).strip():
            continue
        var = row["variable"]
        denom = row.get("denominator", "")
        if pg not in groups:
            groups[pg] = {"denominator": str(denom) if pd.notna(denom) else "", "components": []}
        groups[pg]["components"].append(var)
    return groups
