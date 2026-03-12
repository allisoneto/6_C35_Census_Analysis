"""
Parse MBTA stops GeoJSON with embedded route arrays and prepare flat outputs for Tableau.

This script flattens the nested routes array in mbta_stops_collapsed.geojson
so each stop-route combination becomes a separate row. Outputs preserve GeoJSON format
and polygon geometry for spatial visualization in Tableau.

Tableau workflow:
    1. Load mbta_stops_flattened.geojson (polygons) or mbta_stops_flattened.csv as primary
    2. Load mbta_lines_deduplicated.geojson (or mbta_routes_lookup.csv) as secondary
    3. Join on route_id (same data type: string)
"""

from pathlib import Path
import json
import csv

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent
STOPS_PATH = PROJECT_ROOT / "data" / "mbta_stops" / "mbta_stops_collapsed.geojson"
LINES_PATH = PROJECT_ROOT / "data" / "mbta_lines" / "mbta_lines_deduplicated.geojson"
OUTPUT_DIR = PROJECT_ROOT / "data" / "mbta_stops" / "tableau_ready"


def load_geojson(path: Path) -> dict:
    """Load a GeoJSON file and return the parsed dict."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def flatten_stops_for_tableau(stops_geojson: dict) -> tuple[list[dict], list[dict]]:
    """
    Flatten stops so each stop-route pair is one row, preserving polygon geometry.

    Parameters
    ----------
    stops_geojson : dict
        GeoJSON FeatureCollection of stops with a 'routes' array in properties.

    Returns
    -------
    tuple[list[dict], list[dict]]
        (flat_rows_for_csv, geojson_features) - flat rows for CSV and GeoJSON
        Feature dicts with geometry for GeoJSON output.
    """
    rows = []
    features = []
    stop_attrs = (
        "stop_id", "stop_code", "stop_name", "zone_id", "stop_url",
        "parent_station", "wheelchair_boarding", "level_id"
    )
    route_attrs = (
        "route_id", "agency_id", "route_short_name", "route_long_name",
        "route_desc", "route_type", "route_url", "route_color",
        "route_text_color", "route_sort_order", "network_id"
    )

    for feature in stops_geojson.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        # routes can be a list (already parsed) or a JSON string (needs parsing)
        routes_raw = props.get("routes", [])
        if isinstance(routes_raw, str):
            routes = json.loads(routes_raw) if routes_raw else []
        else:
            routes = routes_raw or []

        # Extract stop-level attributes
        stop_data = {k: props.get(k) for k in stop_attrs}

        # Compute centroid for CSV (Tableau can use lat/lon when no geometry)
        lon, lat = None, None
        if geom and geom.get("type") == "Polygon":
            coords = geom.get("coordinates", [[]])[0]
            if coords:
                n = len(coords)
                lon = sum(c[0] for c in coords) / n
                lat = sum(c[1] for c in coords) / n

        stop_data["lon"] = lon
        stop_data["lat"] = lat

        for route in routes:
            row = {**stop_data}
            for k in route_attrs:
                row[k] = route.get(k)
            rows.append(row)

            # Build GeoJSON feature with full polygon geometry preserved
            # Include centroid lon/lat in properties for Tableau point mapping
            props_flat = {k: row.get(k) for k in stop_attrs + route_attrs}
            props_flat["station_longitude"] = lon
            props_flat["station_latitude"] = lat
            features.append({
                "type": "Feature",
                "properties": props_flat,
                "geometry": geom.copy() if geom else None,
            })

    return rows, features


def extract_routes_lookup(lines_geojson: dict) -> list[dict]:
    """
    Extract a flat routes lookup table from the lines GeoJSON.

    Parameters
    ----------
    lines_geojson : dict
        GeoJSON FeatureCollection of route lines.

    Returns
    -------
    list[dict]
        List of route attribute dicts (no geometry).
    """
    route_attrs = (
        "route_id", "agency_id", "agency_name", "route_short_name",
        "route_long_name", "route_desc", "route_type", "route_url",
        "route_color", "route_text_color", "route_sort_order", "network_id"
    )
    rows = []
    for feature in lines_geojson.get("features", []):
        props = feature.get("properties", {})
        rows.append({k: props.get(k) for k in route_attrs})
    return rows


def write_csv(rows: list[dict], path: Path, fieldnames: list[str] | None = None) -> None:
    """Write rows to CSV with consistent column order."""
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_geojson(features: list[dict], path: Path, crs: dict | None = None) -> None:
    """
    Write a GeoJSON FeatureCollection with optional CRS.

    Parameters
    ----------
    features : list[dict]
        List of GeoJSON Feature dicts (each with type, properties, geometry).
    path : Path
        Output file path.
    crs : dict, optional
        Coordinate reference system, e.g. {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}.
    """
    fc = {"type": "FeatureCollection", "features": features}
    if crs:
        fc["crs"] = crs
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2, ensure_ascii=False)


def main() -> None:
    """Load datasets, flatten stops, and write Tableau-ready outputs."""
    # Load GeoJSON files
    stops_data = load_geojson(STOPS_PATH)
    lines_data = load_geojson(LINES_PATH)

    # Flatten stops: one row per (stop, route) pair, preserving polygon geometry
    flattened_stops, geojson_features = flatten_stops_for_tableau(stops_data)
    routes_lookup = extract_routes_lookup(lines_data)

    # Preserve CRS from source for proper spatial reference in Tableau
    crs = stops_data.get("crs")

    # Define column order for Tableau (route_id first for easy join)
    stop_cols = [
        "route_id", "stop_id", "stop_code", "stop_name", "zone_id", "stop_url",
        "parent_station", "wheelchair_boarding", "level_id",
        "lon", "lat",
        "route_short_name", "route_long_name", "route_desc", "route_type",
        "route_url", "route_color", "route_text_color", "route_sort_order", "network_id"
    ]
    route_cols = [
        "route_id", "agency_id", "agency_name", "route_short_name",
        "route_long_name", "route_desc", "route_type", "route_url",
        "route_color", "route_text_color", "route_sort_order", "network_id"
    ]

    # Write outputs
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(flattened_stops, OUTPUT_DIR / "mbta_stops_flattened.csv", fieldnames=stop_cols)
    write_csv(routes_lookup, OUTPUT_DIR / "mbta_routes_lookup.csv", fieldnames=route_cols)
    write_geojson(geojson_features, OUTPUT_DIR / "mbta_stops_flattened_.geojson", crs=crs)

    print(f"Wrote {len(flattened_stops)} stop-route rows to {OUTPUT_DIR / 'mbta_stops_flattened.csv'}")
    print(f"Wrote {len(geojson_features)} features (with polygons) to {OUTPUT_DIR / 'mbta_stops_flattened.geojson'}")
    print(f"Wrote {len(routes_lookup)} route rows to {OUTPUT_DIR / 'mbta_routes_lookup.csv'}")
    print("\nTableau: Load mbta_stops_flattened.geojson for polygon maps; join on route_id with mbta_lines")


if __name__ == "__main__":
    main()
