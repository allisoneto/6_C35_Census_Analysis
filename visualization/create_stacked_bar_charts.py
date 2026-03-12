"""
Create stacked bar charts for pie_group composition across block groups.

Uses pie_group variables (e.g., race by tenure) as stacked segments; x = GEOID.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils import ACS_NULL, DATA_ATTRIBUTION, get_pie_groups, get_source_label, human_readable_dir_name, load_data

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "stacked_bar_charts"


def create_stacked_bar_charts(
    geoids: list[str],
    pie_group_name: str,
    source: str = "acs",
    year: int | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path | None:
    """
    Create stacked bar chart: composition (pie_group) across block groups.

    Parameters
    ----------
    geoids : list of str
        Block group GEOIDs to compare.
    pie_group_name : str
        Pie group from mapping (e.g., housing_cost_burden, race_of_householder).
    source : str
        "acs" or "decennial".
    year : int, optional
        Year. If None, use latest.
    output_dir : Path
        Output directory.

    Returns
    -------
    Path or None
        Path to saved PNG.
    """
    long_df, _, mapping_df = load_data(source)
    groups = get_pie_groups(mapping_df, source)

    if pie_group_name not in groups:
        return None

    info = groups[pie_group_name]
    denom_var = info["denominator"]
    components = info["components"]

    sub = long_df[long_df["GEOID"].astype(str).isin(geoids)]
    if sub.empty:
        return None

    if year is not None:
        sub = sub[sub["year"] == year]
    else:
        year = int(sub["year"].max())
        sub = sub[sub["year"] == year]

    if sub.empty:
        return None

    # Build matrix: rows = GEOID, columns = component proportions
    labels = []
    data = []

    for geoid in geoids:
        row_data = sub[sub["GEOID"].astype(str) == str(geoid)]
        if row_data.empty:
            continue

        row_data = row_data.iloc[0]

        comp_vals = []
        for c in components:
            if c in row_data.index:
                v = row_data[c]
                if pd.notna(v) and v != ACS_NULL:
                    comp_vals.append(float(v))
                else:
                    comp_vals.append(0)
            else:
                comp_vals.append(0)

        total = sum(comp_vals)
        if total <= 0:
            continue

        # Use sum(components) so stacked bars sum to 100% per block group
        props = [v / total for v in comp_vals]
        data.append(props)
        labels.append(str(geoid)[-4:])  # Short label

    if not data:
        return None

    data = np.array(data).T  # (n_components, n_geoids)
    comp_labels = [_shorten(mapping_df, c) for c in components]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(labels))
    width = 0.6
    bottom = np.zeros(len(labels))

    colors = plt.cm.Set3(np.linspace(0, 1, len(components)))
    for i, (comp_label, row) in enumerate(zip(comp_labels, data)):
        ax.bar(x, row, width, label=comp_label, bottom=bottom, color=colors[i])
        bottom += row

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Proportion (share of total)", fontsize=11)
    ax.set_xlabel("Census Block Group (last 4 digits of GEOID)", fontsize=11)
    group_title = pie_group_name.replace("_", " ").title()
    source_label = get_source_label(source)
    ax.set_title(
        f"{group_title} — Composition by Block Group\n{source_label} ({year})",
        fontsize=13,
        fontweight="bold",
    )
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", title="Category")
    ax.set_ylim(0, 1)
    fig = ax.get_figure()
    fig.text(
        0.5,
        0.01,
        DATA_ATTRIBUTION,
        fontsize=9,
        color="gray",
        ha="center",
    )
    plt.tight_layout(rect=[0, 0.04, 1, 1])

    # Organize by pie group (human-readable)
    group_dir = output_dir / human_readable_dir_name(pie_group_name)
    group_dir.mkdir(parents=True, exist_ok=True)
    out_path = group_dir / f"{pie_group_name}_n{len(geoids)}geoids_{year}.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    return out_path


def _shorten(mapping_df: pd.DataFrame, var: str) -> str:
    """Short label for variable."""
    row = mapping_df[mapping_df["variable"] == var]
    if row.empty:
        return var
    name = row["human_readable_name"].iloc[0]
    return name[:25] + "..." if len(name) > 25 else name


def main() -> None:
    parser = argparse.ArgumentParser(description="Create stacked bar charts for pie_group composition.")
    parser.add_argument("geoids", nargs="+", help="Block group GEOIDs")
    parser.add_argument("--pie-group", type=str, required=True, help="Pie group name (e.g., housing_cost_burden)")
    parser.add_argument("--source", choices=["acs", "decennial"], default="acs")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    out = create_stacked_bar_charts(
        args.geoids,
        args.pie_group,
        source=args.source,
        year=args.year,
        output_dir=args.output_dir,
    )
    if out:
        print(f"Created {out}")
    else:
        print("No chart created")


if __name__ == "__main__":
    main()
