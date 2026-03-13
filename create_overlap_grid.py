"""
Create a spatial grid with stop-buffer overlap counts for Tableau.

Each grid cell records how many MBTA stop buffers (0.5 mile radius) contain
the cell's center point, broken out by route_desc and route_color.
Output is a GeoJSON suitable for Tableau with:
  - grid_id: unique cell identifier
  - overlap_desc_<route_desc>: count per route type (e.g., overlap_desc_Local_Bus)
  - overlap_color_<hex>: count per route color (e.g., overlap_color_FFC72C)
  - geometry: polygon for the grid cell

Usage:
  python create_overlap_grid.py

Output:
  data/mbta_stops_with_buffer/tableau_ready/overlap_grid.geojson
"""
import re
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
BUFFER_PATH = DATA_DIR / "mbta_stops_with_buffer/tableau_ready/stops_buffer.geojson"
OUTPUT_PATH = DATA_DIR / "mbta_stops_with_buffer/tableau_ready/grid_station_counts.geojson"

# -----------------------------------------------------------------------------
# Load stop buffers
# -----------------------------------------------------------------------------
print(f"Loading stop buffers from {BUFFER_PATH}...")
buffers_gdf = gpd.read_file(BUFFER_PATH)

# Ensure we have a projected CRS for accurate grid sizing (meters)
# Boston is in EPSG:32619 (UTM zone 19N)
buffers_gdf = buffers_gdf.to_crs(epsg=32619)

# Normalize route_desc and route_color for consistent grouping
buffers_gdf["route_desc"] = buffers_gdf["route_desc"].fillna("Unknown").astype(str).str.strip()
# route_color: strip # and normalize (e.g., #FFC72C -> FFC72C)
buffers_gdf["route_color"] = (
    buffers_gdf["route_color"].fillna("Unknown").astype(str).str.strip().str.lstrip("#").str.upper()
)
buffers_gdf.loc[buffers_gdf["route_color"] == "", "route_color"] = "Unknown"

# Exclude rail replacement bus (temporary service during rail outages)
rail_replacement = buffers_gdf["route_desc"].str.lower().str.replace(" ", "_") == "rail_replacement_bus"
buffers_gdf = buffers_gdf[~rail_replacement].copy()
print(f"  Excluded rail replacement bus; {len(buffers_gdf)} stop-route buffers remaining")

# Get bounding box of all buffers (study area)
bounds = buffers_gdf.total_bounds
minx, miny, maxx, maxy = bounds

# Add small buffer to edges so we don't miss boundary overlaps
margin = 500  # meters
minx -= margin
miny -= margin
maxx += margin
maxy += margin

# -----------------------------------------------------------------------------
# Create grid in projected CRS (meters)
# -----------------------------------------------------------------------------
# 250m x 250m cells
CELL_SIZE_M = 250

x_cells = int((maxx - minx) / CELL_SIZE_M) + 1
y_cells = int((maxy - miny) / CELL_SIZE_M) + 1

print(f"Creating grid: {x_cells} x {y_cells} cells ({x_cells * y_cells} total)...")

grid_cells = []
cell_id = 0
for i in range(x_cells):
    for j in range(y_cells):
        x0 = minx + i * CELL_SIZE_M
        y0 = miny + j * CELL_SIZE_M
        x1 = x0 + CELL_SIZE_M
        y1 = y0 + CELL_SIZE_M
        geom = box(x0, y0, x1, y1)
        grid_cells.append({"grid_id": cell_id, "geometry": geom})
        cell_id += 1

grid_gdf = gpd.GeoDataFrame(grid_cells, crs="EPSG:32619")

# -----------------------------------------------------------------------------
# Spatial join: count buffers that contain each cell's center
# -----------------------------------------------------------------------------
# Use cell centroids (points); count how many buffers contain each point.

grid_centroids = grid_gdf.copy()
grid_centroids["geometry"] = grid_gdf.geometry.centroid

print("Computing point-in-polygon (cell center within buffer)...")
joined = gpd.sjoin(grid_centroids, buffers_gdf, how="inner", predicate="within")

def _safe_desc_col(s: str) -> str:
    """Convert route_desc to column name: overlap_desc_<sanitized>."""
    sanitized = re.sub(r"[^\w]", "_", s).strip("_") or "Unknown"
    return f"overlap_desc_{sanitized}"

def _safe_desc_route_cleaned_col(s: str) -> str:
    """Convert route_desc to column name: overlap_desc_route_cleaned_<sanitized>."""
    sanitized = re.sub(r"[^\w]", "_", s).strip("_") or "Unknown"
    return f"overlap_desc_route_cleaned_{sanitized}"

def _safe_color_col(s: str) -> str:
    """Convert route_color (hex) to column name: overlap_color_<hex>."""
    sanitized = re.sub(r"[^\w]", "_", str(s).strip()).strip("_") or "Unknown"
    return f"overlap_color_{sanitized}"

def _safe_color_route_cleaned_col(s: str) -> str:
    """Convert route_color to column name: overlap_color_route_cleaned_<hex>."""
    sanitized = re.sub(r"[^\w]", "_", str(s).strip()).strip("_") or "Unknown"
    return f"overlap_color_route_cleaned_{sanitized}"

# Count distinct (stop_id, route_id) pairs per group - avoids duplicate rows, counts each stop-route once
joined["stop_route"] = joined["stop_id"].astype(str) + "_" + joined["route_id"].astype(str)
overlap_by_desc = (
    joined.groupby(["grid_id", "route_desc"])["stop_route"]
    .nunique()
    .reset_index(name="count")
)
pivoted_desc = overlap_by_desc.pivot(
    index="grid_id", columns="route_desc", values="count"
).reset_index()

overlap_by_color = (
    joined.groupby(["grid_id", "route_color"])["stop_route"]
    .nunique()
    .reset_index(name="count")
)
pivoted_color = overlap_by_color.pivot(
    index="grid_id", columns="route_color", values="count"
).reset_index()

# Route-cleaned: count distinct route_id per group - each route at most once per cell
# (multiple stops for same route in area count as 1; reflects route diversity, not stop density)
overlap_desc_route_cleaned = (
    joined.groupby(["grid_id", "route_desc"])["route_id"]
    .nunique()
    .reset_index(name="count")
)
pivoted_desc_rc = overlap_desc_route_cleaned.pivot(
    index="grid_id", columns="route_desc", values="count"
).reset_index()

overlap_color_route_cleaned = (
    joined.groupby(["grid_id", "route_color"])["route_id"]
    .nunique()
    .reset_index(name="count")
)
pivoted_color_rc = overlap_color_route_cleaned.pivot(
    index="grid_id", columns="route_color", values="count"
).reset_index()

# Merge all onto grid (all cells, fill missing with 0)
grid_with_counts = grid_gdf.merge(pivoted_desc, on="grid_id", how="left")
grid_with_counts = grid_with_counts.merge(pivoted_color, on="grid_id", how="left")
grid_with_counts = grid_with_counts.merge(pivoted_desc_rc, on="grid_id", how="left", suffixes=("", "_rc"))
grid_with_counts = grid_with_counts.merge(pivoted_color_rc, on="grid_id", how="left", suffixes=("", "_rc"))

# Rename columns: overlap_desc_<type>, overlap_color_<hex>, and route_cleaned variants
desc_cols = [c for c in pivoted_desc.columns if c != "grid_id"]
color_cols = [c for c in pivoted_color.columns if c != "grid_id"]

rename_desc = {c: _safe_desc_col(c) for c in desc_cols}
rename_color = {c: _safe_color_col(c) for c in color_cols}
rename_desc_rc = {c: _safe_desc_route_cleaned_col(c) for c in desc_cols}
rename_color_rc = {c: _safe_color_route_cleaned_col(c) for c in color_cols}

# Handle _rc suffix from merge (duplicate column names get _rc)
desc_rc_cols = [c for c in grid_with_counts.columns if c.endswith("_rc") and c.replace("_rc", "") in desc_cols]
color_rc_cols = [c for c in grid_with_counts.columns if c.endswith("_rc") and c.replace("_rc", "") in color_cols]
rc_rename = {}
for c in desc_rc_cols:
    rc_rename[c] = rename_desc_rc.get(c.replace("_rc", ""), c)
for c in color_rc_cols:
    rc_rename[c] = rename_color_rc.get(c.replace("_rc", ""), c)
grid_with_counts = grid_with_counts.rename(columns={**rename_desc, **rename_color, **rc_rename})

desc_cols = [rename_desc[c] for c in desc_cols]
color_cols = [rename_color[c] for c in color_cols]
desc_rc_cols = [rename_desc_rc[c] for c in desc_cols]
color_rc_cols = [rename_color_rc[c] for c in color_cols]
route_cols = desc_cols + color_cols + desc_rc_cols + color_rc_cols

# Fill NaN with 0 (cells with no overlaps of that type/color)
grid_with_counts[route_cols] = grid_with_counts[route_cols].fillna(0).astype(int)

# Keep all cells including those with 0 overlaps (set True to drop zero-overlap cells)
FILTER_ZEROS = True
if FILTER_ZEROS:
    total_overlap = grid_with_counts[desc_cols].sum(axis=1)
    grid_with_counts = grid_with_counts[total_overlap > 0].copy()

# Add total overlap for convenience
grid_with_counts["overlap_total"] = grid_with_counts[desc_cols].sum(axis=1)
grid_with_counts["overlap_total_route_cleaned"] = grid_with_counts[desc_rc_cols].sum(axis=1)

# Convert back to WGS84 for Tableau
grid_with_counts = grid_with_counts.to_crs(epsg=4326)

# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
grid_with_counts.to_file(OUTPUT_PATH, driver="GeoJSON")

print(f"Saved {len(grid_with_counts)} grid cells to {OUTPUT_PATH}")
print(f"  Route desc columns: {len(desc_cols)} | Route color columns: {len(color_cols)}")
print(f"  Total overlap range: {grid_with_counts['overlap_total'].min()} - {grid_with_counts['overlap_total'].max()}")

# -----------------------------------------------------------------------------
# Visualize the grid
# -----------------------------------------------------------------------------
import matplotlib.pyplot as plt

# Output path for the visualization
VIZ_PATH = Path(__file__).parent / "visualizations" / "grid_station_counts.png"
VIZ_PATH.parent.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(12, 10))
grid_with_counts.plot(
    ax=ax,
    column="overlap_total",
    cmap="viridis",
    legend=True,
    legend_kwds={"label": "Buffers containing cell center", "shrink": 0.6},
    edgecolor="none",
    alpha=0.85,
)
ax.set_title("MBTA Stop Buffers Containing Cell Center\n(250m × 250m grid, center-point containment)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_aspect("equal")
plt.tight_layout()
plt.savefig(VIZ_PATH, dpi=150, bbox_inches="tight")
plt.close()

print(f"Saved visualization to {VIZ_PATH}")
