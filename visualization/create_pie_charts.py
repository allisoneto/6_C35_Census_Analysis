"""
Create pie charts for grouped census variables (e.g., rent burden, units in structure).

Supports single block group, or aggregated across selected GEOIDs.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from utils import ACS_NULL, DATA_ATTRIBUTION, get_pie_groups, get_source_label, human_readable_dir_name, load_data

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "pie_charts"


def create_pie_chart(
    data: pd.DataFrame,
    group_name: str,
    source: str = "acs",
    geoid: str | None = None,
    year: int | None = None,
    aggregate_geoids: list[str] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path | None:
    """
    Create a pie chart for a variable group (e.g., rent burden buckets).

    Parameters
    ----------
    data : pd.DataFrame
        Long-format census data (from load_data).
    group_name : str
        Pie group name from mapping (e.g., housing_cost_burden, units_in_structure).
    source : str
        "acs" or "decennial".
    geoid : str, optional
        Single block group GEOID. If None, use aggregate_geoids.
    year : int, optional
        Year to use. If None, use latest year in data.
    aggregate_geoids : list of str, optional
        GEOIDs to aggregate (sum) for the chart.
    output_dir : Path
        Output directory.

    Returns
    -------
    Path or None
        Path to saved PNG, or None if failed.
    """
    _, _, mapping_df = load_data(source)
    groups = get_pie_groups(mapping_df, source)

    if group_name not in groups:
        return None

    info = groups[group_name]
    denom_var = info["denominator"]
    components = info["components"]

    # Filter data
    sub = data.copy()
    if year is not None:
        sub = sub[sub["year"] == year]
    if sub.empty:
        year = int(data["year"].max()) if "year" in data.columns else None
        sub = data[data["year"] == year] if year is not None else data

    if geoid:
        sub = sub[sub["GEOID"].astype(str) == str(geoid)]
    elif aggregate_geoids:
        sub = sub[sub["GEOID"].astype(str).isin(aggregate_geoids)]

    if sub.empty:
        return None

    # Sum across rows (aggregation)
    totals = {}
    for c in components:
        if c in sub.columns:
            vals = sub[c].replace(ACS_NULL, None)
            totals[c] = vals.sum()
        else:
            totals[c] = 0

    # For pie charts, slices must sum to 100%. Use sum(components) as denominator
    # so the distribution among the displayed categories is shown correctly.
    # (Using table total would give slices that don't add to 100% when showing
    # only a subset of categories, e.g., rent burden 30%+ but not under-30%.)
    comp_sum = sum(totals.values())
    denom_val = comp_sum
    if denom_val <= 0:
        return None

    # Build labels and sizes
    labels = []
    sizes = []
    for c in components:
        v = totals.get(c, 0) or 0
        if v > 0:
            pct = v / denom_val
            labels.append(_shorten_label(mapping_df, c))
            sizes.append(pct)

    if not sizes:
        return None

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
    group_title = group_name.replace("_", " ").title()
    year_str = str(year) if year else "aggregated"
    source_label = get_source_label(source)
    ax.set_title(
        f"{group_title} — Composition by Category\n{source_label} ({year_str})",
        fontsize=13,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.02,
        f"{DATA_ATTRIBUTION} | Aggregated across selected block groups.",
        fontsize=9,
        color="gray",
        ha="center",
    )
    plt.tight_layout(rect=[0, 0.05, 1, 1])

    # Organize by pie group (human-readable)
    group_dir = output_dir / human_readable_dir_name(group_name)
    group_dir.mkdir(parents=True, exist_ok=True)
    label = geoid or ("agg_" + str(len(aggregate_geoids or [])) + "geoids")
    out_path = group_dir / f"{group_name}_{label}_{year or 'agg'}.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    return out_path


def _shorten_label(mapping_df: pd.DataFrame, var: str) -> str:
    """Get shortened human-readable label for variable."""
    row = mapping_df[mapping_df["variable"] == var]
    if row.empty:
        return var
    name = row["human_readable_name"].iloc[0]
    # Truncate long labels
    if len(name) > 30:
        return name[:27] + "..."
    return name


def create_all_pie_charts(
    source: str,
    geoid: str | None = None,
    year: int | None = None,
    aggregate_geoids: list[str] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> list[Path]:
    """
    Create pie charts for all pie groups in the mapping.

    Parameters
    ----------
    source : str
        "acs" or "decennial".
    geoid : str, optional
        Single GEOID.
    year : int, optional
        Year.
    aggregate_geoids : list of str, optional
        GEOIDs to aggregate.
    output_dir : Path
        Output directory.

    Returns
    -------
    list of Path
        Paths to created PNGs.
    """
    long_df, _, mapping_df = load_data(source)
    groups = get_pie_groups(mapping_df, source)

    if not geoid and not aggregate_geoids:
        # Default: use first few GEOIDs as sample for aggregated view
        sample_geoids = long_df["GEOID"].drop_duplicates().head(3).astype(str).tolist()
        aggregate_geoids = sample_geoids

    created = []
    for group_name in groups:
        p = create_pie_chart(
            long_df,
            group_name,
            source=source,
            geoid=geoid,
            year=year,
            aggregate_geoids=aggregate_geoids,
            output_dir=output_dir,
        )
        if p:
            created.append(p)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Create pie charts for grouped census variables.")
    parser.add_argument("--source", choices=["acs", "decennial"], default="acs")
    parser.add_argument("--geoid", type=str, default=None, help="Single block group GEOID")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--aggregate-geoids", type=str, default=None, help="Comma-separated GEOIDs to aggregate")
    parser.add_argument("--group", type=str, default=None, help="Specific pie group name")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    aggregate_geoids = [g.strip() for g in args.aggregate_geoids.split(",")] if args.aggregate_geoids else None

    long_df, _, _ = load_data(args.source)

    if args.group:
        created = []
        p = create_pie_chart(
            long_df,
            args.group,
            source=args.source,
            geoid=args.geoid,
            year=args.year,
            aggregate_geoids=aggregate_geoids,
            output_dir=args.output_dir,
        )
        if p:
            created.append(p)
    else:
        created = create_all_pie_charts(
            args.source,
            geoid=args.geoid,
            year=args.year,
            aggregate_geoids=aggregate_geoids,
            output_dir=args.output_dir,
        )

    print(f"Created {len(created)} pie charts in {args.output_dir}")


if __name__ == "__main__":
    main()
