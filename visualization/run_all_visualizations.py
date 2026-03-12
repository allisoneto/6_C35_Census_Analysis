"""
Centralized script to run all TOD visualizations.

Runs choropleths for all variables/years/transforms, plus a curated set of
bar charts, pie charts, line charts, scatter plots, stacked bars,
small multiples, and heatmaps with sensible default variables.
"""

import argparse
from pathlib import Path

from create_bar_chart_comparisons import create_bar_chart_comparisons
from create_choropleth_maps import create_all_choropleths
from create_heatmaps import create_heatmaps
from create_line_charts import create_line_charts
from create_pie_charts import create_pie_chart
from create_scatter_plots import create_scatter_plots
from create_small_multiples import create_small_multiples
from create_stacked_bar_charts import create_stacked_bar_charts
from utils import load_data

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

# Sample GEOIDs: pick block groups with varied overlap for comparison
SAMPLE_GEOID_COUNT = 5

# Key variables for non-choropleth chart types
ACS_BAR_VARS = [
    "B01001_001E",   # Total population
    "B25001_001E",   # Total housing units
    "B19013_001E",   # Median household income
    "B08301_010E",   # Public transit commuters
    "B01002_001E",   # Median age
]
DECENNIAL_BAR_VARS = [
    "CL8AA",   # Total population
    "CM7AA",   # Total housing units
    "CN1AA",   # Owner occupied
    "CN1AB",   # Renter occupied
    "CM0AA",   # Male
]

ACS_LINE_VAR = "B01001_001E"
DECENNIAL_LINE_VAR = "CL8AA"

ACS_SCATTER_PAIRS = [
    ("overlap_total", "B01001_001E", "count"),       # transit vs population
    ("overlap_total", "B01001_001E", "per_aland"),   # transit vs population density
    ("overlap_total", "B25001_001E", "per_aland"),    # transit vs housing density
]
DECENNIAL_SCATTER_PAIRS = [
    ("overlap_total", "CL8AA", "count"),
    ("overlap_total", "CL8AA", "per_aland"),
    ("overlap_total", "CM7AA", "per_aland"),
]

ACS_PIE_GROUPS = ["housing_cost_burden", "units_in_structure", "year_structure_built"]
DECENNIAL_PIE_GROUPS = ["race_of_householder", "persons_by_age", "tenure_by_race", "household_size"]

ACS_STACKED_GROUPS = ["housing_cost_burden", "units_in_structure"]
DECENNIAL_STACKED_GROUPS = ["race_of_householder", "household_size", "occupied_by_household_size"]

ACS_SMALL_MULT_VAR = "B01001_001E"
DECENNIAL_SMALL_MULT_VAR = "CL8AA"

ACS_HEATMAP_VAR = "B01001_001E"
DECENNIAL_HEATMAP_VAR = "CL8AA"


def _get_sample_geoids(source: str, n: int = SAMPLE_GEOID_COUNT) -> list[str]:
    """
    Get sample block group GEOIDs from data.

    Prefers GEOIDs with overlap_total > 0 when available (decennial).
    Falls back to first N unique GEOIDs.
    """
    long_df, _, _ = load_data(source)
    long_df["GEOID"] = long_df["GEOID"].astype(str)

    if "overlap_total" in long_df.columns:
        # Use one row per GEOID (latest year) and sort by overlap
        latest = long_df["year"].max()
        sub = long_df[long_df["year"] == latest].drop_duplicates(subset="GEOID")
        sub = sub[sub["overlap_total"] > 0].nlargest(n * 2, "overlap_total")
        geoids = sub["GEOID"].head(n).tolist()
        if geoids:
            return geoids

    # Fallback: first N unique GEOIDs
    geoids = long_df["GEOID"].drop_duplicates().head(n).tolist()
    return geoids


def run_choropleths(
    output_dir: Path,
    sources: list[str],
    years: list[int] | None = None,
    variables: list[str] | None = None,
) -> list[Path]:
    """Run all choropleth maps for specified sources. Outputs to output/maps/acs, output/maps/decennial."""
    created = []
    for source in sources:
        out = output_dir / "maps" / source
        created.extend(
            create_all_choropleths(source, output_dir=out, years=years, variables=variables)
        )
    return created


def run_bar_charts(output_dir: Path, sources: list[str], geoids: list[str] | None = None) -> list[Path]:
    """Run bar chart comparisons for key variables. Outputs to output/bar_charts/acs, etc."""
    created = []
    for source in sources:
        g = geoids or _get_sample_geoids(source)
        vars_ = ACS_BAR_VARS if source == "acs" else DECENNIAL_BAR_VARS
        out = output_dir / "bar_charts" / source
        created.extend(
            create_bar_chart_comparisons(g, source=source, variables=vars_, output_dir=out)
        )
    return created


def run_pie_charts(
    output_dir: Path,
    sources: list[str],
    geoids: list[str] | None = None,
    year: int | None = None,
) -> list[Path]:
    """Run pie charts for key groups (aggregated across sample GEOIDs). Outputs to output/pie_charts/acs, etc."""
    created = []
    for source in sources:
        g = geoids or _get_sample_geoids(source)
        groups = ACS_PIE_GROUPS if source == "acs" else DECENNIAL_PIE_GROUPS
        long_df, _, _ = load_data(source)
        out = output_dir / "pie_charts" / source
        for group in groups:
            p = create_pie_chart(
                long_df,
                group,
                source=source,
                aggregate_geoids=g,
                year=year,
                output_dir=out,
            )
            if p:
                created.append(p)
    return created


def run_line_charts(
    output_dir: Path,
    sources: list[str],
    geoids: list[str] | None = None,
    years: list[int] | None = None,
) -> list[Path]:
    """Run line charts (population over time) for sample GEOIDs. Outputs to output/line_charts/acs, etc."""
    created = []
    for source in sources:
        g = geoids or _get_sample_geoids(source)
        var = ACS_LINE_VAR if source == "acs" else DECENNIAL_LINE_VAR
        out = output_dir / "line_charts" / source
        p = create_line_charts(g, var, source=source, years=years, output_dir=out)
        if p:
            created.append(p)
        # Also density over time
        p2 = create_line_charts(g, var, source=source, years=years, transform="per_aland", output_dir=out)
        if p2:
            created.append(p2)
    return created


def run_scatter_plots(
    output_dir: Path,
    sources: list[str],
    year: int | None = None,
) -> list[Path]:
    """Run scatter plots: overlap_total vs key demographics. Outputs to output/scatter_plots/acs, etc."""
    created = []
    for source in sources:
        pairs = ACS_SCATTER_PAIRS if source == "acs" else DECENNIAL_SCATTER_PAIRS
        out = output_dir / "scatter_plots" / source
        for x_var, y_var, y_transform in pairs:
            p = create_scatter_plots(
                x_var=x_var,
                y_var=y_var,
                source=source,
                year=year,
                y_transform=y_transform,
                output_dir=out,
            )
            if p:
                created.append(p)
    return created


def run_stacked_bars(
    output_dir: Path,
    sources: list[str],
    geoids: list[str] | None = None,
    year: int | None = None,
) -> list[Path]:
    """Run stacked bar charts for pie groups. Outputs to output/stacked_bar_charts/acs, etc."""
    created = []
    for source in sources:
        g = geoids or _get_sample_geoids(source)
        groups = ACS_STACKED_GROUPS if source == "acs" else DECENNIAL_STACKED_GROUPS
        out = output_dir / "stacked_bar_charts" / source
        for group in groups:
            p = create_stacked_bar_charts(g, group, source=source, year=year, output_dir=out)
            if p:
                created.append(p)
    return created


def run_small_multiples(
    output_dir: Path,
    sources: list[str],
    years: list[int] | None = None,
) -> list[Path]:
    """Run small multiples (choropleth grid across years). Outputs to output/small_multiples/acs, etc."""
    created = []
    for source in sources:
        var = ACS_SMALL_MULT_VAR if source == "acs" else DECENNIAL_SMALL_MULT_VAR
        out = output_dir / "small_multiples" / source
        p = create_small_multiples(var, "per_aland", source=source, years=years, output_dir=out)
        if p:
            created.append(p)
        p2 = create_small_multiples(var, "count", source=source, years=years, output_dir=out)
        if p2:
            created.append(p2)
    return created


def run_heatmaps(
    output_dir: Path,
    sources: list[str],
    geoids: list[str] | None = None,
    years: list[int] | None = None,
) -> list[Path]:
    """Run heatmaps: GEOIDs x years. Outputs to output/heatmaps/acs, etc."""
    created = []
    for source in sources:
        g = geoids or _get_sample_geoids(source)
        var = ACS_HEATMAP_VAR if source == "acs" else DECENNIAL_HEATMAP_VAR
        out = output_dir / "heatmaps" / source
        p = create_heatmaps(
            source=source,
            geoids=g,
            variable=var,
            years=years,
            mode="geoids_x_years",
            output_dir=out,
        )
        if p:
            created.append(p)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run all TOD visualizations: choropleths + curated bar, pie, line, scatter, stacked bar, small multiples, heatmaps."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Base output directory (charts go in output/maps, output/bar_charts, etc.)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="acs,decennial",
        help="Comma-separated: acs, decennial",
    )
    parser.add_argument(
        "--years",
        type=str,
        default=None,
        help="Comma-separated years to limit (e.g., 2013,2019 or 1990,2000,2010,2020)",
    )
    parser.add_argument(
        "--choropleth-only",
        action="store_true",
        help="Only run choropleths (skip other chart types)",
    )
    parser.add_argument(
        "--skip-choropleth",
        action="store_true",
        help="Skip choropleths (run only other chart types)",
    )
    parser.add_argument(
        "--choropleth-variables",
        type=str,
        default=None,
        help="Comma-separated variable codes to limit choropleths (default: all)",
    )
    args = parser.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    years = [int(y.strip()) for y in args.years.split(",")] if args.years else None
    choropleth_vars = [v.strip() for v in args.choropleth_variables.split(",")] if args.choropleth_variables else None

    all_created: list[Path] = []

    if not args.skip_choropleth:
        print("Running choropleths...")
        all_created.extend(
            run_choropleths(args.output_dir, sources, years=years, variables=choropleth_vars))
        print(f"  Created {len([c for c in all_created if 'maps' in str(c)])} choropleths")

    if not args.choropleth_only:
        geoids_acs = _get_sample_geoids("acs") if "acs" in sources else []
        geoids_dec = _get_sample_geoids("decennial") if "decennial" in sources else []
        geoids = geoids_acs or geoids_dec
        year_filter = years[-1] if years else None

        print("Running bar charts...")
        n_before = len(all_created)
        all_created.extend(run_bar_charts(args.output_dir, sources, geoids))
        print(f"  Created {len(all_created) - n_before} bar charts")

        print("Running pie charts...")
        n_before = len(all_created)
        all_created.extend(run_pie_charts(args.output_dir, sources, geoids, year=year_filter))
        print(f"  Created {len(all_created) - n_before} pie charts")

        print("Running line charts...")
        n_before = len(all_created)
        all_created.extend(run_line_charts(args.output_dir, sources, geoids, years=years))
        print(f"  Created {len(all_created) - n_before} line charts")

        print("Running scatter plots...")
        n_before = len(all_created)
        all_created.extend(run_scatter_plots(args.output_dir, sources, year=year_filter))
        print(f"  Created {len(all_created) - n_before} scatter plots")

        print("Running stacked bar charts...")
        n_before = len(all_created)
        all_created.extend(run_stacked_bars(args.output_dir, sources, geoids, year=year_filter))
        print(f"  Created {len(all_created) - n_before} stacked bar charts")

        print("Running small multiples...")
        n_before = len(all_created)
        all_created.extend(run_small_multiples(args.output_dir, sources, years=years))
        print(f"  Created {len(all_created) - n_before} small multiples")

        print("Running heatmaps...")
        n_before = len(all_created)
        all_created.extend(run_heatmaps(args.output_dir, sources, geoids, years=years))
        print(f"  Created {len(all_created) - n_before} heatmaps")

    print(f"\nTotal: {len(all_created)} visualizations in {args.output_dir}")


if __name__ == "__main__":
    main()
