"""
Create choropleth maps for census variables by year and transformation.

For each (variable, year, transformation) where transformation is not pie_group,
generates a choropleth map. Supports both ACS and decennial data sources.
MBTA route lines are overlaid on top using their assigned colors.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from utils import (
    ACS_NULL,
    DATA_ATTRIBUTION,
    MBTA_LINES_PATH,
    apply_transformation,
    get_aland_column,
    get_population_column,
    get_source_label,
    get_transform_label,
    human_readable_dir_name,
    load_data,
    merge_long_with_geometry,
    plot_mbta_routes,
    resolve_denominator,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "maps"


def create_choropleth(
    source: str,
    variable: str,
    transform: str,
    year: int,
    output_dir: Path,
    *,
    title: str | None = None,
    mbta_lines_path: Path | None = None,
    overlay_mbta: bool = True,
) -> Path | None:
    """
    Create a single choropleth map.

    Parameters
    ----------
    source : str
        "acs" or "decennial".
    variable : str
        Census variable code (e.g., B01001_001E, CL8AA).
    transform : str
        One of: raw, count, per_aland, per_population, proportion.
    year : int
        Data year.
    output_dir : Path
        Directory for output PNG.
    title : str, optional
        Map title. Defaults to variable + transform + year.
    mbta_lines_path : Path, optional
        Path to MBTA lines GeoJSON. Default: data/mbta_lines/lines.geojson.
    overlay_mbta : bool
        If True, overlay MBTA routes on top. Default True.

    Returns
    -------
    Path or None
        Path to saved PNG, or None if failed.
    """
    long_df, geo_gdf, mapping_df = load_data(source)

    # Filter to year
    if "year" not in long_df.columns:
        return None
    sub = long_df[long_df["year"] == year]
    if sub.empty:
        return None

    if variable not in sub.columns:
        return None

    aland_col = get_aland_column(geo_gdf, source)
    if aland_col not in geo_gdf.columns:
        return None

    pop_col = get_population_column(source)

    # Get mapping for denominator
    var_row = mapping_df[mapping_df["variable"] == variable]
    denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None
    human_name = var_row["human_readable_name"].iloc[0] if not var_row.empty else variable

    # Merge with geometry
    merged = merge_long_with_geometry(sub, geo_gdf, aland_col)

    # Compute transformed value per row
    values = []
    for _, row in merged.iterrows():
        raw = row.get(variable)
        aland = row.get(aland_col)
        pop = row.get(pop_col) if pop_col in row.index else None
        denom = resolve_denominator(denom_spec, row, source) if denom_spec else None

        val = apply_transformation(
            raw,
            transform,
            denominator=denom,
            aland=aland,
            population=pop,
            null_sentinel=ACS_NULL if source == "acs" else None,
        )
        values.append(val)

    merged["_plot_value"] = values

    # Keep all block groups; those with no data get NaN (shown as gray via missing_kwds)
    plot_df = merged
    if plot_df.empty:
        return None
    # Skip when column has no valid data (geopandas fails with empty colormap)
    if not plot_df["_plot_value"].notna().any():
        return None

    # Plot: missing_kwds shows block groups with no/suppressed data in light gray
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    plot_df.plot(
        ax=ax,
        column="_plot_value",
        legend=True,
        cmap="YlOrRd",
        edgecolor="gray",
        linewidth=0.2,
        missing_kwds={"color": "lightgray", "label": "No data"},
    )
    # Overlay MBTA routes as thin lines using their assigned colors
    if overlay_mbta:
        plot_mbta_routes(ax, plot_df, mbta_lines_path or MBTA_LINES_PATH)
    ax.set_axis_off()

    if title is None:
        trans_label = get_transform_label(transform)
        title = f"{human_name} ({variable}) ({trans_label}) — {year}"
    ax.set_title(title, fontsize=14, fontweight="bold")
    # Attribution at bottom: data source and census bureau
    source_label = get_source_label(source)
    fig.text(
        0.5,
        0.02,
        f"{source_label} | {DATA_ATTRIBUTION}",
        fontsize=9,
        color="gray",
        ha="center",
    )
    plt.subplots_adjust(bottom=0.08)

    # Organize by variable (human-readable) and transformation
    var_dir = output_dir / human_readable_dir_name(human_name) / transform
    var_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{source}_{variable}_{transform}_{year}.png"
    out_path = var_dir / out_name
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    return out_path


def create_all_choropleths(
    source: str,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    years: list[int] | None = None,
    variables: list[str] | None = None,
    overlay_mbta: bool = True,
    mbta_lines_path: Path | None = None,
) -> list[Path]:
    """
    Create choropleth maps for all (variable, year, transform) combinations.

    Parameters
    ----------
    source : str
        "acs" or "decennial".
    output_dir : Path
        Output directory.
    years : list of int, optional
        Years to include. Default: all in data.
    variables : list of str, optional
        Variables to include. Default: all with non-pie_group transforms.
    overlay_mbta : bool
        If True, overlay MBTA routes on choropleths. Default True.
    mbta_lines_path : Path, optional
        Path to MBTA lines GeoJSON. Default: data/mbta_lines/lines.geojson.

    Returns
    -------
    list of Path
        Paths to created PNGs.
    """
    long_df, _, mapping_df = load_data(source)

    if years is None:
        years = sorted(long_df["year"].dropna().unique().astype(int).tolist())

    # Variables with choropleth-worthy transforms (exclude pie_group only)
    var_map = mapping_df[mapping_df["transformations"].notna() & (mapping_df["transformations"] != "")]
    var_map = var_map[~var_map["transformations"].str.contains("pie_group", na=False)]

    if variables is not None:
        var_map = var_map[var_map["variable"].isin(variables)]

    created = []
    for _, row in var_map.iterrows():
        var = row["variable"]
        trans_str = row["transformations"]
        human_name = row["human_readable_name"]
        for trans in trans_str.split("|"):
            trans = trans.strip()
            if trans == "pie_group":
                continue
            for year in years:
                p = create_choropleth(
                    source,
                    var,
                    trans,
                    year,
                    output_dir,
                    title=f"{human_name} ({var}) ({trans}) — {year}",
                    overlay_mbta=overlay_mbta,
                    mbta_lines_path=mbta_lines_path,
                )
                if p:
                    created.append(p)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Create choropleth maps for census variables.")
    parser.add_argument("--source", choices=["acs", "decennial"], default="acs", help="Data source")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--years", type=str, default=None, help="Comma-separated years (e.g., 2013,2019)")
    parser.add_argument("--variables", type=str, default=None, help="Comma-separated variable codes")
    parser.add_argument(
        "--no-mbta-overlay",
        action="store_true",
        help="Disable MBTA route overlay on maps",
    )
    parser.add_argument(
        "--mbta-lines",
        type=Path,
        default=None,
        help="Path to MBTA lines GeoJSON (default: data/mbta_lines/lines.geojson)",
    )
    args = parser.parse_args()

    years = None
    if args.years:
        years = [int(y.strip()) for y in args.years.split(",")]

    variables = None
    if args.variables:
        variables = [v.strip() for v in args.variables.split(",")]

    created = create_all_choropleths(
        args.source,
        args.output_dir,
        years=years,
        variables=variables,
        overlay_mbta=not args.no_mbta_overlay,
        mbta_lines_path=args.mbta_lines,
    )
    print(f"Created {len(created)} choropleth maps in {args.output_dir}")


if __name__ == "__main__":
    main()
