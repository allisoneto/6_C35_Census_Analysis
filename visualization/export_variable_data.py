"""
Export variable data to CSV in the corresponding output folder.

Iterates through every variable (with choropleth-worthy transforms) and writes
a CSV with GEOID, year, raw value, transformed value, and context columns
to output/maps/{source}/{human_name}/{transform}/.
"""

import argparse
from pathlib import Path

import pandas as pd

from utils import (
    ACS_NULL,
    apply_transformation,
    get_aland_column,
    get_population_column,
    human_readable_dir_name,
    load_data,
    merge_long_with_geometry,
    resolve_denominator,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "maps"


def export_variable_data(
    source: str,
    variable: str,
    transform: str,
    output_dir: Path,
    years: list[int] | None = None,
) -> Path | None:
    """
    Export data for a variable (with transform) to CSV in the corresponding folder.

    Parameters
    ----------
    source : str
        "acs" or "decennial".
    variable : str
        Census variable code (e.g., B01001_001E, CL8AA).
    transform : str
        One of: raw, count, per_aland, per_population, proportion.
    output_dir : Path
        Base output directory (e.g., output/maps).
    years : list of int, optional
        Years to include. Default: all in data.

    Returns
    -------
    Path or None
        Path to saved CSV, or None if failed.
    """
    long_df, geo_gdf, mapping_df = load_data(source)

    if "year" not in long_df.columns:
        return None
    if variable not in long_df.columns:
        return None

    aland_col = get_aland_column(geo_gdf, source)
    if aland_col not in geo_gdf.columns:
        return None

    pop_col = get_population_column(source)

    var_row = mapping_df[mapping_df["variable"] == variable]
    denom_spec = var_row["denominator"].iloc[0] if not var_row.empty else None
    human_name = var_row["human_readable_name"].iloc[0] if not var_row.empty else variable

    sub = long_df.copy()
    if years is not None:
        sub = sub[sub["year"].isin(years)]
    if sub.empty:
        return None

    merged = merge_long_with_geometry(sub, geo_gdf, aland_col)

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

    merged["value_raw"] = merged[variable]
    merged["value_transformed"] = values

    # Build export dataframe: essential columns only (no geometry)
    export_cols = ["GEOID", "year", "value_raw", "value_transformed", aland_col]
    if "overlap_total" in merged.columns:
        export_cols.append("overlap_total")
    export_df = merged[export_cols].copy()
    export_df = export_df.rename(
        columns={
            "value_raw": f"{variable}_raw",
            "value_transformed": f"{variable}_{transform}",
        }
    )

    # Organize by variable (human-readable) and transformation
    var_dir = output_dir / source / human_readable_dir_name(human_name) / transform
    var_dir.mkdir(parents=True, exist_ok=True)
    safe_var = variable.replace("|", "_").replace("+", "_")
    out_name = f"{safe_var}_{transform}_{source}.csv"
    out_path = var_dir / out_name
    export_df.to_csv(out_path, index=False)
    return out_path


def export_all_variable_data(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    sources: list[str] | None = None,
    years: list[int] | None = None,
    variables: list[str] | None = None,
) -> list[Path]:
    """
    Export CSV data for all variables to their corresponding output folders.

    Parameters
    ----------
    output_dir : Path
        Base output directory (e.g., output/maps).
    sources : list of str, optional
        Data sources. Default: ["acs", "decennial"].
    years : list of int, optional
        Years to include. Default: all in data.
    variables : list of str, optional
        Variables to include. Default: all with non-pie_group transforms.

    Returns
    -------
    list of Path
        Paths to created CSVs.
    """
    if sources is None:
        sources = ["acs", "decennial"]

    created = []
    for source in sources:
        long_df, _, mapping_df = load_data(source)

        if years is None:
            years_list = sorted(long_df["year"].dropna().unique().astype(int).tolist())
        else:
            years_list = years

        var_map = mapping_df[mapping_df["transformations"].notna() & (mapping_df["transformations"] != "")]
        var_map = var_map[~var_map["transformations"].str.contains("pie_group", na=False)]

        if variables is not None:
            var_map = var_map[var_map["variable"].isin(variables)]

        for _, row in var_map.iterrows():
            var = row["variable"]
            trans_str = row["transformations"]
            for trans in trans_str.split("|"):
                trans = trans.strip()
                if trans == "pie_group":
                    continue
                p = export_variable_data(
                    source,
                    var,
                    trans,
                    output_dir,
                    years=years_list,
                )
                if p:
                    created.append(p)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export variable data to CSV in corresponding output folders."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Base output directory (default: output/maps)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="acs,decennial",
        help="Comma-separated sources: acs, decennial",
    )
    parser.add_argument(
        "--years",
        type=str,
        default=None,
        help="Comma-separated years (e.g., 2013,2019)",
    )
    parser.add_argument(
        "--variables",
        type=str,
        default=None,
        help="Comma-separated variable codes (default: all)",
    )
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    years = [int(y.strip()) for y in args.years.split(",")] if args.years else None
    variables = [v.strip() for v in args.variables.split(",")] if args.variables else None

    created = export_all_variable_data(
        output_dir=args.output_dir,
        sources=sources,
        years=years,
        variables=variables,
    )
    print(f"Exported {len(created)} CSV files to {args.output_dir}")


if __name__ == "__main__":
    main()
