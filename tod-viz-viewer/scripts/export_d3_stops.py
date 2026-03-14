"""
Export MBTA stops for the D3 interactive choropleth map overlay.

Tries (in order):
  1. data/mbta_stops/tableau_ready/mbta_stops_flattened_.geojson (from parse_json_entries.py)
  2. data/mbta_stops/mbta_stops_collapsed.geojson (flattens in-place from routes array)

Outputs mbta_stops_for_map.json to both tableau_ready and public/data/stops for dev and prod.

Run from project root: python tod-viz-viewer/scripts/export_d3_stops.py
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TOD_VIZ_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = TOD_VIZ_DIR.parent

STOPS_FLATTENED = PROJECT_ROOT / "data" / "mbta_stops" / "tableau_ready" / "mbta_stops_flattened_.geojson"
STOPS_COLLAPSED = PROJECT_ROOT / "data" / "mbta_stops" / "mbta_stops_collapsed.geojson"
OUTPUT_DIRS = [
    PROJECT_ROOT / "data" / "mbta_stops" / "tableau_ready",
    TOD_VIZ_DIR / "public" / "data" / "stops",
]
OUTPUT_FILENAME = "mbta_stops_for_map.json"


def _extract_from_flattened(fc: dict) -> list[dict]:
    """Extract points from mbta_stops_flattened_.geojson format."""
    points = []
    for feature in fc.get("features", []):
        props = feature.get("properties", {})
        lon = props.get("station_longitude") or props.get("lon")
        lat = props.get("station_latitude") or props.get("lat")
        if lon is None or lat is None:
            continue
        color = str(props.get("route_color", "#333333")).strip()
        if color and not color.startswith("#"):
            color = "#" + color
        route_type = props.get("route_type")
        if not isinstance(route_type, (int, float)):
            try:
                route_type = int(route_type) if route_type else -1
            except (ValueError, TypeError):
                route_type = -1
        points.append({
            "lon": float(lon), "lat": float(lat), "route_color": color or "#333333",
            "route_type": int(route_type) if route_type is not None else -1,
            "route_id": str(props.get("route_id", "")),
            "stop_name": str(props.get("stop_name", "")),
            "route_short_name": str(props.get("route_short_name", "") or props.get("route_id", "")),
        })
    return points


def _extract_from_collapsed(fc: dict) -> list[dict]:
    """Extract points from mbta_stops_collapsed.geojson (has routes array per stop)."""
    points = []
    for feature in fc.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry")
        lon, lat = None, None
        if geom and geom.get("type") == "Polygon" and geom.get("coordinates"):
            ring = geom["coordinates"][0]
            if ring:
                n = len(ring)
                lon = sum(c[0] for c in ring) / n
                lat = sum(c[1] for c in ring) / n
        elif geom and geom.get("type") == "Point" and geom.get("coordinates"):
            lon, lat = geom["coordinates"][0], geom["coordinates"][1]
        if lon is None or lat is None:
            continue
        routes_raw = props.get("routes", [])
        routes = json.loads(routes_raw) if isinstance(routes_raw, str) else (routes_raw or [])
        for route in routes:
            color = str(route.get("route_color", "#333333")).strip()
            if color and not color.startswith("#"):
                color = "#" + color
            rt = route.get("route_type")
            if not isinstance(rt, (int, float)):
                try:
                    rt = int(rt) if rt else -1
                except (ValueError, TypeError):
                    rt = -1
            points.append({
                "lon": float(lon), "lat": float(lat), "route_color": color or "#333333",
                "route_type": int(rt) if rt is not None else -1,
                "route_id": str(route.get("route_id", "")),
                "stop_name": str(props.get("stop_name", "")),
                "route_short_name": str(route.get("route_short_name", "") or route.get("route_id", "")),
            })
    return points


def main() -> None:
    """Load stops GeoJSON and export simplified point list for D3 overlay."""
    points = []
    if STOPS_FLATTENED.exists():
        with open(STOPS_FLATTENED, encoding="utf-8") as f:
            points = _extract_from_flattened(json.load(f))
        print(f"Loaded from {STOPS_FLATTENED}")
    elif STOPS_COLLAPSED.exists():
        with open(STOPS_COLLAPSED, encoding="utf-8") as f:
            points = _extract_from_collapsed(json.load(f))
        print(f"Loaded from {STOPS_COLLAPSED}")
    else:
        print(f"Stops files not found. Tried:")
        print(f"  - {STOPS_FLATTENED}")
        print(f"  - {STOPS_COLLAPSED}")
        print("Run parse_json_entries.py first, or ensure mbta_stops_collapsed.geojson exists.")
        return

    for out_dir in OUTPUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / OUTPUT_FILENAME
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(points, f, separators=(",", ":"))
        print(f"Exported {len(points)} stop-route points to {out_file}")


if __name__ == "__main__":
    main()
