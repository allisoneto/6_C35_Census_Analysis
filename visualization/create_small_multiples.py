"""
Create small multiples: grid of choropleth maps for same variable across years.

One panel per year (e.g., 1990, 2000, 2010, 2020).
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
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
    plot_mbta_routes,
    resolve_denominator,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "small_multiples"


def create_small_multiples(
    variable: str,
    transform: str,
    source: str = "acs",
    years: list[int] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path | None:
    """
    Create grid of choropleths: same variable across years.

    Parameters
    ----------
    variable : str
        Census variable code.
    transform : str
        Transformation (count, per_aland, etc.).
    source : str
        "acs" or "decennial".
    years : list of int, optional
        Years to include. Default: all in data.
    output_dir : Path
        Output directory.

    Returns
    -------
    Path or None
        Path to saved PNG.
    """
    long_df, geo_gdf, mapping_df = load_data(source)

    if variable not in long_df.columns:
        return None

    if years is None:
        years = sorted(long_df["year"].dropna().unique().astype(int).tolist())

    aland_col = get_aland_column(geo_gdf, source)
    pop_col = get_population_column(source)

    var_row = mapping_df[mapping_df["variable"] == variable]
    denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None
    human_name = var_row["human_readable_name"].iloc[0] if not var_row.empty else variable

    # Compute global vmin/vmax across all years for consistent color scale across panels.
    all_values = []
    for year in years:
        sub = long_df[long_df["year"] == year]
        if sub.empty:
            continue
        merged = merge_long_with_geometry(sub, geo_gdf, aland_col)
        for _, r in merged.iterrows():
            raw = r.get(variable)
            aland = r.get(aland_col)
            pop = r.get(pop_col) if pop_col in r.index else None
            denom = resolve_denominator(denom_spec, r, source) if denom_spec else None
            val = apply_transformation(
                raw, transform,
                denominator=denom, aland=aland, population=pop,
                null_sentinel=ACS_NULL if source == "acs" else None,
            )
            if val is not None:
                all_values.append(val)
    vmin = float(min(all_values)) if all_values else None
    vmax = float(max(all_values)) if all_values else None

    n = len(years)
    ncols = min(4, n)
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows))
    if n == 1:
        axes = np.array([[axes]])
    elif nrows == 1:
        axes = axes.reshape(1, -1)

    for idx, year in enumerate(years):
        row, col = idx // ncols, idx % ncols
        ax = axes[row, col]

        sub = long_df[long_df["year"] == year]
        if sub.empty:
            ax.set_visible(False)
            continue

        merged = merge_long_with_geometry(sub, geo_gdf, aland_col)

        values = []
        for _, r in merged.iterrows():
            raw = r.get(variable)
            aland = r.get(aland_col)
            pop = r.get(pop_col) if pop_col in r.index else None
            denom = resolve_denominator(denom_spec, r, source) if denom_spec else None

            val = apply_transformation(
                raw,
                transform,
                denominator=denom,
                aland=aland,
                population=pop,
                null_sentinel=ACS_NULL if source == "acs" else None,
            )
            values.append(val)

        merged["_plot_value"] = pd.to_numeric(values, errors="coerce")
        plot_df = merged.dropna(subset=["_plot_value"])

        if plot_df.empty:
            ax.set_visible(False)
            continue

        # Pass norm explicitly; vmin/vmax can be ignored by geopandas, causing white maps
        plot_kwargs = dict(ax=ax, column="_plot_value", legend=False, cmap="viridis", edgecolor="gray", linewidth=0.2)
        if vmin is not None and vmax is not None:
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            if norm.vmax <= norm.vmin:
                norm = mcolors.Normalize(vmin=norm.vmin, vmax=norm.vmin + 1.0)
            plot_kwargs["norm"] = norm
        plot_df.plot(**plot_kwargs)
        plot_mbta_routes(ax, plot_df)
        ax.set_title(str(year), fontsize=11)
        ax.set_axis_off()

    # Hide unused subplots
    for idx in range(n, nrows * ncols):
        row, col = idx // ncols, idx % ncols
        axes[row, col].set_visible(False)

    trans_label = get_transform_label(transform)
    source_label = get_source_label(source)
    fig.suptitle(
        f"{human_name} ({variable}) ({trans_label}) — Choropleth by Year\n{source_label}",
        fontsize=14,
        fontweight="bold",
    )
    # Add shared colorbar with consistent scale across panels
    if vmin is not None and vmax is not None:
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=axes.ravel().tolist(), shrink=0.6)
        cbar.set_label(trans_label, fontsize=10)
    fig.text(
        0.5,
        0.02,
        DATA_ATTRIBUTION,
        fontsize=9,
        color="gray",
        ha="center",
    )
    plt.tight_layout(rect=[0, 0.04, 1, 0.96])

    # Organize by variable (human-readable) and transformation
    var_dir = output_dir / human_readable_dir_name(human_name) / transform
    var_dir.mkdir(parents=True, exist_ok=True)
    safe_var = variable.replace("|", "_").replace("+", "_")
    years_str = "_".join(str(y) for y in years)
    out_path = var_dir / f"{safe_var}_{transform}_{years_str}.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create small multiples: choropleth grid across years.")
    parser.add_argument("--variable", type=str, required=True, help="Census variable code")
    parser.add_argument("--transform", type=str, default="count")
    parser.add_argument("--source", choices=["acs", "decennial"], default="acs")
    parser.add_argument("--years", type=str, default=None, help="Comma-separated years")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    years = [int(y.strip()) for y in args.years.split(",")] if args.years else None

    out = create_small_multiples(
        args.variable,
        args.transform,
        source=args.source,
        years=years,
        output_dir=args.output_dir,
    )
    if out:
        print(f"Created {out}")
    else:
        print("No chart created")


if __name__ == "__main__":
    main()
