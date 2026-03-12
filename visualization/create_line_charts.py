"""
Create line charts (time series) for census variables across years.

One line per block group; x = year, y = variable value.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from utils import (
    ACS_NULL,
    DATA_ATTRIBUTION,
    apply_transformation,
    get_aland_column,
    get_population_column,
    get_source_label,
    get_transform_label,
    human_readable_dir_name,
    load_data,
    merge_long_with_geometry,
    resolve_denominator,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "line_charts"


def create_line_charts(
    geoids: list[str],
    variable: str,
    source: str = "acs",
    years: list[int] | None = None,
    transform: str = "count",
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path | None:
    """
    Create a line chart: variable vs year, one line per block group.

    Parameters
    ----------
    geoids : list of str
        Block group GEOIDs to plot.
    variable : str
        Census variable code.
    source : str
        "acs" or "decennial".
    years : list of int, optional
        Years to include. Default: all in data.
    transform : str
        Transformation (count, raw, per_aland, etc.).
    output_dir : Path
        Output directory.

    Returns
    -------
    Path or None
        Path to saved PNG.
    """
    long_df, geo_gdf, mapping_df = load_data(source)

    sub = long_df[long_df["GEOID"].astype(str).isin(geoids)]
    if sub.empty:
        return None

    if variable not in sub.columns:
        return None

    if years:
        sub = sub[sub["year"].isin(years)]
    if sub.empty:
        return None

    aland_col = get_aland_column(geo_gdf, source)
    pop_col = get_population_column(source)

    merged = merge_long_with_geometry(sub, geo_gdf, aland_col)

    var_row = mapping_df[mapping_df["variable"] == variable]
    denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None
    human_name = var_row["human_readable_name"].iloc[0] if not var_row.empty else variable

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
    plot_df = merged.dropna(subset=["_plot_value"])

    if plot_df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    for geoid in plot_df["GEOID"].unique():
        g = plot_df[plot_df["GEOID"] == geoid].sort_values("year")
        ax.plot(g["year"], g["_plot_value"], marker="o", label=str(geoid))

    trans_label = get_transform_label(transform)
    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel(f"{human_name} ({trans_label})", fontsize=11)
    source_label = get_source_label(source)
    ax.set_title(
        f"{human_name} — Time Series by Block Group\n{source_label}",
        fontsize=13,
        fontweight="bold",
    )
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", title="Block Group (GEOID)")
    ax.grid(True, alpha=0.3)
    fig.text(
        0.5,
        0.01,
        DATA_ATTRIBUTION,
        fontsize=9,
        color="gray",
        ha="center",
    )
    plt.tight_layout(rect=[0, 0.04, 1, 1])

    # Organize by variable (human-readable) and transformation
    var_dir = output_dir / human_readable_dir_name(human_name) / transform
    var_dir.mkdir(parents=True, exist_ok=True)
    safe_var = variable.replace("|", "_").replace("+", "_")
    out_path = var_dir / f"{safe_var}_n{len(geoids)}geoids.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create line charts (time series) for census variables.")
    parser.add_argument("geoids", nargs="+", help="Block group GEOIDs")
    parser.add_argument("--variable", type=str, required=True, help="Census variable code")
    parser.add_argument("--source", choices=["acs", "decennial"], default="acs")
    parser.add_argument("--years", type=str, default=None, help="Comma-separated years")
    parser.add_argument("--transform", type=str, default="count")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    years = [int(y.strip()) for y in args.years.split(",")] if args.years else None

    out = create_line_charts(
        args.geoids,
        args.variable,
        source=args.source,
        years=years,
        transform=args.transform,
        output_dir=args.output_dir,
    )
    if out:
        print(f"Created {out}")
    else:
        print("No chart created (missing data or invalid parameters)")


if __name__ == "__main__":
    main()
