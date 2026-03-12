"""
Compare route_ids between MBTA stops and routes datasets.
Visualizes mismatches to help debug Tableau joins.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Circle

# -----------------------------------------------------------------------------
# Load data
# -----------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
with open(DATA_DIR / "mbta_stops/tableau_ready/stops.geojson", encoding="utf-8") as f:
    stops_raw = json.load(f)

with open(DATA_DIR / "mbta_lines/lines.geojson", encoding="utf-8") as f:
    routes_raw = json.load(f)

# Extract properties from GeoJSON features (remove geometry for tabular use)
def _extract_properties(geojson_data):
    """Extract properties from GeoJSON FeatureCollection or list of features."""
    if isinstance(geojson_data, dict) and "features" in geojson_data:
        features = geojson_data["features"]
        return [f.get("properties", {}) for f in features]
    if isinstance(geojson_data, list):
        return [f.get("properties", {}) for f in geojson_data if isinstance(f, dict)]
    return []

stops_list = _extract_properties(stops_raw)
routes_list = _extract_properties(routes_raw)

stops_df = pd.DataFrame(stops_list)
routes_df = pd.DataFrame(routes_list)

# Ensure route_id is string (avoids silent mismatches from type coercion)
stops_df["route_id"] = stops_df["route_id"].astype(str).str.strip()
routes_df["route_id"] = routes_df["route_id"].astype(str).str.strip()

# Unique route IDs
stops_ids = set(stops_df["route_id"].unique())
routes_ids = set(routes_df["route_id"].unique())

# Compute overlap
both = stops_ids & routes_ids
stops_only = stops_ids - routes_ids
routes_only = routes_ids - stops_ids

print(f"Total unique routes in stops:  {len(stops_ids)}")
print(f"Total unique routes in routes: {len(routes_ids)}")
print(f"In both:                       {len(both)}")
print(f"Stops only:                    {len(stops_only)}")
print(f"Routes only:                   {len(routes_only)}")

# -----------------------------------------------------------------------------
# Visualization 1: Bar chart of overlap categories
# -----------------------------------------------------------------------------
OUTPUT_DIR = DATA_DIR.parent
SAVE_KW = {"dpi": 150, "bbox_inches": "tight"}

# Plot 1: Bar chart
fig, ax = plt.subplots(figsize=(8, 5))
categories = ["Both", "Stops Only", "Routes Only"]
counts = [len(both), len(stops_only), len(routes_only)]
colors = ["#2ecc71", "#e74c3c", "#3498db"]
ax.bar(categories, counts, color=colors)
ax.set_xlabel("Match Category")
ax.set_ylabel("Number of Route IDs")
ax.set_title("Route ID Overlap Between Stops and Routes")
ax.tick_params(axis="x", rotation=20)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "plot1_overlap_bar.png", **SAVE_KW)
plt.close()

# Plot 2: Venn-style set diagram
fig, ax = plt.subplots(figsize=(6, 6))
circle_stops = Circle((0.3, 0.5), 0.28, alpha=0.4, color="#e74c3c", label="Stops")
circle_routes = Circle((0.7, 0.5), 0.28, alpha=0.4, color="#3498db", label="Routes")
ax.add_patch(circle_stops)
ax.add_patch(circle_routes)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect("equal")
ax.legend(loc="upper center", fontsize=9)
ax.set_title("Set Overlap (Stops vs Routes)")
ax.text(0.15, 0.5, str(len(stops_only)), ha="center", va="center", fontsize=12, fontweight="bold")
ax.text(0.85, 0.5, str(len(routes_only)), ha="center", va="center", fontsize=12, fontweight="bold")
ax.text(0.5, 0.5, str(len(both)), ha="center", va="center", fontsize=12, fontweight="bold")
ax.axis("off")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "plot2_venn_overlap.png", **SAVE_KW)
plt.close()

# Plot 3: Horizontal bar (coverage by dataset) with bars closer together and legend above
fig, ax = plt.subplots(figsize=(8, 3.4))
labels = ["Stops dataset", "Routes dataset"]
in_both = [len(both), len(both)]
only_in_self = [len(stops_only), len(routes_only)]

# Tighter bar placement: reduce vertical distance, but keep bars comfortably spaced
y_pos = [0.35, 1.05]  # Move bars closer together
bar_height = 0.34     # Reasonable size so bars are not too small

ax.barh(y_pos, in_both, height=bar_height, label="In both", color="#2ecc71", left=0)
ax.barh(y_pos, only_in_self, height=bar_height, label="Only in this dataset", color="#e74c3c", left=in_both)

ax.set_yticks(y_pos)
ax.set_yticklabels(labels)
ax.set_xlabel("Number of Route IDs")
ax.set_title("Coverage by Dataset")
# Move the legend above the plot
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.07), ncol=2, fontsize=9, frameon=False)
plt.tight_layout(rect=[0, 0, 1, 0.95])  # Add space at top for legend
plt.savefig(OUTPUT_DIR / "plot3_coverage_stacked.png", **SAVE_KW)
plt.close()

# Plot 4: Mismatch details table
def _wrap_ids(ids, n_per_line=6, max_total=18):
    """Wrap long route ID lists into multiple lines to prevent overflow."""
    sorted_ids = sorted(ids)[:max_total]
    chunks = [sorted_ids[i : i + n_per_line] for i in range(0, len(sorted_ids), n_per_line)]
    result = "\n  ".join(", ".join(c) for c in chunks)
    return result + ("..." if len(ids) > max_total else "")

fig, ax = plt.subplots(figsize=(8, 6))
ax.axis("off")
stops_sample = _wrap_ids(stops_only)
routes_sample = _wrap_ids(routes_only)
lines = [
    "Mismatched Route IDs (sample):",
    "",
    f"Only in STOPS ({len(stops_only)}):",
    f"  {stops_sample}",
    "",
    f"Only in ROUTES ({len(routes_only)}):",
    f"  {routes_sample}",
]
ax.text(0.02, 0.98, "\n".join(lines), transform=ax.transAxes, fontsize=9,
        verticalalignment="top", fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
ax.set_title("Mismatch Details")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "plot4_mismatch_details.png", **SAVE_KW)
plt.close()

print(f"Saved 4 plots to {OUTPUT_DIR}")