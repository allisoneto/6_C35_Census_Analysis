"""
Create heatmaps: GEOIDs x years or GEOIDs x variables.

Rows = block groups, columns = years or variables; color = value.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
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
    resolve_denominator,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "heatmaps"


def create_heatmaps(
    source: str = "acs",
    geoids: list[str] | None = None,
    variable: str | None = None,
    variables: list[str] | None = None,
    years: list[int] | None = None,
    mode: str = "geoids_x_years",
    transform: str = "count",
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    max_geoids: int = 50,
) -> Path | None:
    """
    Create heatmap: GEOIDs x years or GEOIDs x variables.

    Parameters
    ----------
    source : str
        "acs" or "decennial".
    geoids : list of str, optional
        Block group GEOIDs. If None, use first max_geoids from data.
    variable : str, optional
        Single variable for geoids_x_years mode.
    variables : list of str, optional
        Variables for geoids_x_vars mode.
    years : list of int, optional
        Years to include.
    mode : str
        "geoids_x_years" or "geoids_x_vars".
    transform : str
        Transformation for values.
    output_dir : Path
        Output directory.
    max_geoids : int
        Max GEOIDs if not specified (avoid huge heatmaps).

    Returns
    -------
    Path or None
        Path to saved PNG.
    """
    long_df, geo_gdf, mapping_df = load_data(source)

    if geoids is None:
        geoids = long_df["GEOID"].drop_duplicates().head(max_geoids).astype(str).tolist()

    sub = long_df[long_df["GEOID"].astype(str).isin(geoids)]
    if sub.empty:
        return None

    aland_col = get_aland_column(geo_gdf, source)
    pop_col = get_population_column(source)

    merged = merge_long_with_geometry(sub, geo_gdf, aland_col)

    if mode == "geoids_x_years":
        if variable is None:
            variable = "B01001_001E" if source == "acs" else "CL8AA"
        if variable not in merged.columns:
            return None

        if years is None:
            years = sorted(merged["year"].dropna().unique().astype(int).tolist())

        var_row = mapping_df[mapping_df["variable"] == variable]
        denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None
        human_name = var_row["human_readable_name"].iloc[0] if not var_row.empty else variable

        # Build matrix: rows=GEOID, cols=years
        matrix = []
        for g in geoids:
            row_vals = []
            for yr in years:
                r = merged[(merged["GEOID"].astype(str) == g) & (merged["year"] == yr)]
                if r.empty:
                    row_vals.append(np.nan)
                else:
                    r = r.iloc[0]
                    raw = r.get(variable)
                    aland = r.get(aland_col)
                    pop = r.get(pop_col) if pop_col in r.index else None
                    denom = resolve_denominator(denom_spec, r, source) if denom_spec else None
                    val = apply_transformation(
                        raw, transform,
                        denominator=denom, aland=aland, population=pop,
                        null_sentinel=ACS_NULL if source == "acs" else None,
                    )
                    row_vals.append(val if val is not None else np.nan)
            matrix.append(row_vals)

        data = np.array(matrix)
        x_labels = [str(y) for y in years]
        y_labels = [g[-6:] for g in geoids]
        title = f"{human_name} ({transform})"

    else:  # geoids_x_vars
        if variables is None:
            var_map = mapping_df[
                mapping_df["transformations"].notna()
                & ~mapping_df["transformations"].str.contains("pie_group", na=False)
            ]
            variables = var_map["variable"].head(15).tolist()

        if years:
            merged = merged[merged["year"].isin(years)]
        year = merged["year"].iloc[0] if "year" in merged.columns and not merged.empty else None

        matrix = []
        for g in geoids:
            r = merged[merged["GEOID"].astype(str) == g]
            if r.empty:
                matrix.append([np.nan] * len(variables))
                continue
            r = r.iloc[0]
            row_vals = []
            for var in variables:
                if var not in merged.columns:
                    row_vals.append(np.nan)
                    continue
                var_row = mapping_df[mapping_df["variable"] == var]
                denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None
                raw = r.get(var)
                aland = r.get(aland_col)
                pop = r.get(pop_col) if pop_col in r.index else None
                denom = resolve_denominator(denom_spec, r, source) if denom_spec else None
                val = apply_transformation(
                    raw, transform,
                    denominator=denom, aland=aland, population=pop,
                    null_sentinel=ACS_NULL if source == "acs" else None,
                )
                row_vals.append(val if val is not None else np.nan)
            matrix.append(row_vals)

        data = np.array(matrix)
        x_labels = [_shorten(mapping_df, v) for v in variables]
        y_labels = [g[-6:] for g in geoids]
        trans_label = get_transform_label(transform)
        title = f"Block Groups × Variables ({year})"

    fig, ax = plt.subplots(figsize=(max(8, len(x_labels) * 0.5), max(6, len(y_labels) * 0.25)))
    im = ax.imshow(data, aspect="auto", cmap="viridis")

    ax.set_xticks(np.arange(len(x_labels)))
    ax.set_yticks(np.arange(len(y_labels)))
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.set_yticklabels(y_labels)
    source_label = get_source_label(source)
    trans_label = get_transform_label(transform)
    ax.set_title(
        f"{title}\n{source_label} | Values: {trans_label}",
        fontsize=13,
        fontweight="bold",
    )
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(trans_label, fontsize=10)
    ax.set_xlabel("Years" if mode == "geoids_x_years" else "Variables", fontsize=11)
    ax.set_ylabel("Block Group (last 6 digits of GEOID)", fontsize=11)
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
    if mode == "geoids_x_years" and variable:
        var_dir = output_dir / human_readable_dir_name(human_name) / transform
        safe_var = variable.replace("|", "_").replace("+", "_")
        out_name = f"{mode}_{safe_var}_{transform}.png"
    else:
        var_dir = output_dir / "Block_Groups_x_Variables" / transform
        out_name = f"{mode}_{transform}_{source}.png"
    var_dir.mkdir(parents=True, exist_ok=True)
    out_path = var_dir / out_name
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    return out_path


def _shorten(mapping_df: pd.DataFrame, var: str) -> str:
    row = mapping_df[mapping_df["variable"] == var]
    if row.empty:
        return var
    name = row["human_readable_name"].iloc[0]
    return name[:20] + ".." if len(name) > 20 else name


def main() -> None:
    parser = argparse.ArgumentParser(description="Create heatmaps: GEOIDs x years or GEOIDs x variables.")
    parser.add_argument("--source", choices=["acs", "decennial"], default="acs")
    parser.add_argument("--geoids", type=str, default=None, help="Comma-separated GEOIDs")
    parser.add_argument("--variable", type=str, default=None, help="Variable for geoids_x_years")
    parser.add_argument("--variables", type=str, default=None, help="Comma-separated variables for geoids_x_vars")
    parser.add_argument("--years", type=str, default=None, help="Comma-separated years")
    parser.add_argument("--mode", choices=["geoids_x_years", "geoids_x_vars"], default="geoids_x_years")
    parser.add_argument("--transform", type=str, default="count")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    geoids = [g.strip() for g in args.geoids.split(",")] if args.geoids else None
    variables = [v.strip() for v in args.variables.split(",")] if args.variables else None
    years = [int(y.strip()) for y in args.years.split(",")] if args.years else None

    out = create_heatmaps(
        source=args.source,
        geoids=geoids,
        variable=args.variable,
        variables=variables,
        years=years,
        mode=args.mode,
        transform=args.transform,
        output_dir=args.output_dir,
    )
    if out:
        print(f"Created {out}")
    else:
        print("No chart created")


if __name__ == "__main__":
    main()
