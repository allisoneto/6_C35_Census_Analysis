"""
Create bar chart comparisons between block groups for census variables.

Supports comparing multiple GEOIDs in a single year, or a single GEOID across years.
"""

import argparse
import math
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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "bar_charts"


def compute_bar_chart_limits(
    geoids: list[str],
    source: str,
    years: list[int],
    variables: list[str] | None = None,
    transform: str = "count",
) -> dict[str, tuple[float, float]]:
    """
    Compute min/max value limits per variable across all years for consistent y-axis scaling.

    Parameters
    ----------
    geoids : list of str
        Block group GEOIDs.
    source : str
        "acs" or "decennial".
    years : list of int
        Years to include.
    variables : list of str, optional
        Variables to include. Default: all non-pie_group from mapping.
    transform : str
        Base transformation (per-variable transform from mapping may override).

    Returns
    -------
    dict of str -> (float, float)
        Variable -> (vmin, vmax) for y-axis limits.
    """
    long_df, geo_gdf, mapping_df = load_data(source)
    sub = long_df[long_df["GEOID"].astype(str).isin(geoids) & long_df["year"].isin(years)]
    if sub.empty:
        return {}

    aland_col = get_aland_column(geo_gdf, source)
    pop_col = get_population_column(source)
    merged = merge_long_with_geometry(sub, geo_gdf, aland_col)

    var_map = mapping_df[
        mapping_df["transformations"].notna()
        & (mapping_df["transformations"] != "")
        & ~mapping_df["transformations"].str.contains("pie_group", na=False)
    ]
    if variables:
        var_map = var_map[var_map["variable"].isin(variables)]

    limits = {}
    for _, vrow in var_map.iterrows():
        var = vrow["variable"]
        if var not in merged.columns:
            continue
        trans_opts = vrow["transformations"].split("|")
        trans_opts = [t.strip() for t in trans_opts if t.strip() != "pie_group"]
        transform_use = transform if transform in trans_opts else (trans_opts[0] if trans_opts else transform)
        denom_spec = vrow.get("denominator")

        vals = []
        for _, row in merged.iterrows():
            raw = row.get(var)
            aland = row.get(aland_col)
            pop = row.get(pop_col) if pop_col in row.index else None
            denom = resolve_denominator(denom_spec, row, source) if denom_spec else None
            val = apply_transformation(
                raw, transform_use,
                denominator=denom, aland=aland, population=pop,
                null_sentinel=ACS_NULL if source == "acs" else None,
            )
            if val is not None and math.isfinite(val):
                vals.append(val)
        if vals:
            limits[var] = (float(min(vals)), float(max(vals)))
    return limits


def create_bar_chart_comparisons(
    geoids: list[str],
    source: str = "acs",
    years: list[int] | None = None,
    variables: list[str] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    transform: str = "count",
    variable_limits: dict[str, tuple[float, float]] | None = None,
) -> list[Path]:
    """
    Create bar charts comparing selected block groups across variables.

    Parameters
    ----------
    geoids : list of str
        Block group GEOIDs to compare.
    source : str
        "acs" or "decennial".
    years : list of int, optional
        Years to include. Default: all in data.
    variables : list of str, optional
        Variables to plot. Default: all non-pie_group from mapping.
    output_dir : Path
        Output directory.
    transform : str
        Transformation to apply (count, raw, proportion, etc.).
    variable_limits : dict of str -> (float, float), optional
        Per-variable (vmin, vmax) for consistent y-axis scaling across years.

    Returns
    -------
    list of Path
        Paths to created PNGs.
    """
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    
    long_df, geo_gdf, mapping_df = load_data(source)

    sub = long_df[long_df["GEOID"].astype(str).isin(geoids)]
    if sub.empty:
        return []

    if years:
        sub = sub[sub["year"].isin(years)]
    if sub.empty:
        return []

    aland_col = get_aland_column(geo_gdf, source)
    pop_col = get_population_column(source)

    # Merge to get ALAND
    merged = merge_long_with_geometry(sub, geo_gdf, aland_col)

    # Variables to plot
    var_map = mapping_df[
        mapping_df["transformations"].notna()
        & (mapping_df["transformations"] != "")
        & ~mapping_df["transformations"].str.contains("pie_group", na=False)
    ]
    if variables:
        var_map = var_map[var_map["variable"].isin(variables)]

    created = []

    for _, vrow in var_map.iterrows():
        var = vrow["variable"]
        if var not in merged.columns:
            continue
        trans_opts = vrow["transformations"].split("|")
        trans_opts = [t.strip() for t in trans_opts if t.strip() != "pie_group"]
        if transform not in trans_opts and trans_opts:
            transform_use = trans_opts[0]
        else:
            transform_use = transform

        denom_spec = vrow.get("denominator")
        human_name = vrow["human_readable_name"]

        # Compute values per (GEOID, year)
        rows = []
        for _, row in merged.iterrows():
            raw = row.get(var)
            aland = row.get(aland_col)
            pop = row.get(pop_col) if pop_col in row.index else None
            denom = resolve_denominator(denom_spec, row, source) if denom_spec else None

            val = apply_transformation(
                raw,
                transform_use,
                denominator=denom,
                aland=aland,
                population=pop,
                null_sentinel=ACS_NULL if source == "acs" else None,
            )
            if val is not None:
                rows.append(
                    {
                        "GEOID": row["GEOID"],
                        "year": row["year"],
                        "value": val,
                    }
                )

        if not rows:
            continue

        plot_df = pd.DataFrame(rows)

        fig, ax = plt.subplots(figsize=(10, 6))

        trans_label = get_transform_label(transform_use)
        ylabel = f"{human_name} ({trans_label})"
        if len(plot_df["year"].unique()) > 1 and len(plot_df["GEOID"].unique()) > 1:
            # Pivot: GEOID on x, hue by year
            pivot = plot_df.pivot_table(index="GEOID", columns="year", values="value")
            pivot.plot(kind="bar", ax=ax, width=0.8)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.set_xlabel("Census Block Group (GEOID)", fontsize=11)
            ax.legend(title="Year", fontsize=9)
        elif len(plot_df["year"].unique()) > 1:
            # Single GEOID, years on x
            g = plot_df.groupby("year")["value"].first().reset_index()
            ax.bar(g["year"].astype(str), g["value"])
            ax.set_ylabel(ylabel, fontsize=11)
            ax.set_xlabel("Year", fontsize=11)
        else:
            # Multiple GEOIDs, single year
            ax.bar(plot_df["GEOID"], plot_df["value"])
            ax.set_ylabel(ylabel, fontsize=11)
            ax.set_xlabel("Census Block Group (GEOID)", fontsize=11)
            plt.xticks(rotation=45, ha="right")

        # Apply consistent y-axis limits across years when provided
        if variable_limits and var in variable_limits:
            vmin, vmax = variable_limits[var]
            if math.isfinite(vmin) and math.isfinite(vmax):
                ax.set_ylim(vmin, vmax)

        source_label = get_source_label(source)
        ax.set_title(
            f"{human_name} — Block Group Comparison\n{source_label}",
            fontsize=13,
            fontweight="bold",
        )
        fig.text(
            0.5,
            0.01,
            DATA_ATTRIBUTION,
            fontsize=9,
            color="gray",
            ha="center",
        )
        plt.tight_layout(rect=[0, 0.04, 1, 1])

        safe_var = var.replace("|", "_").replace("+", "_")
        geoid_label = f"n{len(geoids)}geoids"
        # Include year in filename when chart shows single year (matches choropleth per-year output)
        years_in_plot = plot_df["year"].unique()
        year_suffix = f"_{int(years_in_plot[0])}" if len(years_in_plot) == 1 else ""
        out_path = output_dir / f"{safe_var}_{geoid_label}{year_suffix}.png"
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        plt.close()
        created.append(out_path)

    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Create bar chart comparisons between block groups.")
    parser.add_argument("geoids", nargs="+", help="Block group GEOIDs to compare")
    parser.add_argument("--source", choices=["acs", "decennial"], default="acs")
    parser.add_argument("--years", type=str, default=None, help="Comma-separated years")
    parser.add_argument("--variables", type=str, default=None, help="Comma-separated variable codes")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--transform", type=str, default="count")
    args = parser.parse_args()

    years = [int(y.strip()) for y in args.years.split(",")] if args.years else None
    variables = [v.strip() for v in args.variables.split(",")] if args.variables else None

    created = create_bar_chart_comparisons(
        args.geoids,
        source=args.source,
        years=years,
        variables=variables,
        output_dir=args.output_dir,
        transform=args.transform,
    )
    print(f"Created {len(created)} bar charts in {args.output_dir}")


if __name__ == "__main__":
    main()
