"""
Create scatter plots: overlap_total (or transit var) vs demographic variable.

Each point = one block group. Optionally filter by year.
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
    get_var_label,
    get_source_label,
    get_transform_label,
    human_readable_dir_name,
    load_data,
    merge_long_with_geometry,
    resolve_denominator,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "scatter_plots"


def create_scatter_plots(
    x_var: str = "overlap_total",
    y_var: str = "B01001_001E",
    source: str = "acs",
    year: int | None = None,
    y_transform: str = "count",
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path | None:
    """
    Create scatter plot: x_var vs y_var. Each point = block group.

    Parameters
    ----------
    x_var : str
        X-axis variable (e.g., overlap_total, overlap_desc_Rapid_Transit).
    y_var : str
        Y-axis variable (census variable).
    source : str
        "acs" or "decennial".
    year : int, optional
        Filter to single year. If None, use latest year.
    y_transform : str
        Transformation for y_var (count, per_aland, etc.).
    output_dir : Path
        Output directory.

    Returns
    -------
    Path or None
        Path to saved PNG.
    """
    long_df, geo_gdf, mapping_df = load_data(source)

    if year is not None:
        sub = long_df[long_df["year"] == year]
    else:
        yr = int(long_df["year"].max())
        sub = long_df[long_df["year"] == yr]
        year = yr

    if sub.empty:
        return None

    if x_var not in sub.columns and x_var not in geo_gdf.columns:
        return None
    if y_var not in sub.columns:
        return None

    aland_col = get_aland_column(geo_gdf, source)
    pop_col = get_population_column(source)

    merged = merge_long_with_geometry(sub, geo_gdf, aland_col)

    # If x_var is in geo but not in long, merge it from geo (e.g., overlap_total for ACS)
    if x_var not in merged.columns and x_var in geo_gdf.columns:
        geo_extra = geo_gdf[["GEOID", x_var]].drop_duplicates(subset="GEOID")
        merged = merged.merge(geo_extra, on="GEOID", how="left")

    if x_var not in merged.columns:
        return None

    x_vals = merged[x_var]

    # Y values (transformed)
    var_row = mapping_df[mapping_df["variable"] == y_var]
    denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None
    human_name = var_row["human_readable_name"].iloc[0] if not var_row.empty else y_var

    y_vals = []
    for _, row in merged.iterrows():
        raw = row.get(y_var)
        aland = row.get(aland_col)
        pop = row.get(pop_col) if pop_col in row.index else None
        denom = resolve_denominator(denom_spec, row, source) if denom_spec else None

        val = apply_transformation(
            raw,
            y_transform,
            denominator=denom,
            aland=aland,
            population=pop,
            null_sentinel=ACS_NULL if source == "acs" else None,
        )
        y_vals.append(val)

    plot_df = pd.DataFrame({"x": x_vals.values, "y": y_vals, "GEOID": merged["GEOID"].values})
    plot_df = plot_df.dropna(subset=["x", "y"])

    if plot_df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(plot_df["x"], plot_df["y"], alpha=0.6, s=20)

    x_label = get_var_label(x_var, mapping_df)
    y_trans_label = get_transform_label(y_transform)
    ax.set_xlabel(x_label, fontsize=11)
    ax.set_ylabel(f"{human_name} ({y_trans_label})", fontsize=11)
    source_label = get_source_label(source)
    ax.set_title(
        f"Transit Overlap vs {human_name} — {year}\n{source_label} | Each point = one census block group",
        fontsize=13,
        fontweight="bold",
    )
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

    # Organize by y-variable (human-readable) and transformation
    var_dir = output_dir / human_readable_dir_name(human_name) / y_transform
    var_dir.mkdir(parents=True, exist_ok=True)
    safe_y = y_var.replace("|", "_").replace("+", "_")
    out_path = var_dir / f"{x_var}_vs_{safe_y}_{year}.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create scatter plots: transit overlap vs demographics.")
    parser.add_argument("--x-var", type=str, default="overlap_total", help="X-axis variable")
    parser.add_argument("--y-var", type=str, default="B01001_001E", help="Y-axis census variable")
    parser.add_argument("--source", choices=["acs", "decennial"], default="acs")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--y-transform", type=str, default="count")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    out = create_scatter_plots(
        x_var=args.x_var,
        y_var=args.y_var,
        source=args.source,
        year=args.year,
        y_transform=args.y_transform,
        output_dir=args.output_dir,
    )
    if out:
        print(f"Created {out}")
    else:
        print("No chart created")


if __name__ == "__main__":
    main()
