# TOD Visualization

Scripts for visualizing ACS and decennial census data by census block group, with transit overlap.

## Requirements

- geopandas, pandas, matplotlib, numpy
- Run from project root with `python -m visualization.<script>`

## Data Sources

- **ACS**: `acs/data/output/block_groups_acs_overlap_long.csv`, `block_groups_acs_overlap.geojson`
- **Decennial**: `decennial_census/data/merged/block_groups_decennial_merged_long.csv`, `block_groups_decennial_merged.geojson`

Variable mappings with transformations: `acs/data/acs_variable_mapping.csv`, `decennial_census/data/decennial_variable_mapping_nhgis.csv`

MBTA route overlay: `data/mbta_lines/lines.geojson` (route_color, route_id). Choropleths and small multiples overlay these as thin colored lines.

## Scripts

| Script | Purpose |
|--------|---------|
| `run_all_visualizations.py` | Centralized pipeline: runs all chart types with curated variables |
| `create_choropleth_maps.py` | Choropleth maps per variable, transform, year (MBTA routes overlaid) |
| `create_bar_chart_comparisons.py` | Bar charts comparing block groups |
| `create_pie_charts.py` | Pie charts for grouped metrics (rent burden, etc.) |
| `create_line_charts.py` | Time series: variable vs year, one line per block group |
| `create_scatter_plots.py` | Scatter: overlap_total vs demographic variable |
| `create_stacked_bar_charts.py` | Stacked bars for pie_group composition |
| `create_small_multiples.py` | Grid of choropleths across years (MBTA routes overlaid) |
| `create_heatmaps.py` | Heatmap: GEOIDs × years or GEOIDs × variables |

## Run All Visualizations

```bash
# Run full pipeline (choropleths + bar, pie, line, scatter, stacked, small multiples, heatmaps)
python -m visualization.run_all_visualizations

# Choropleths only
python -m visualization.run_all_visualizations --choropleth-only

# Skip choropleths (other chart types only)
python -m visualization.run_all_visualizations --skip-choropleth

# Limit years and sources
python -m visualization.run_all_visualizations --years 2019 --sources acs
```

## Individual Script Usage

```bash
# Choropleths (ACS, 2019 only; MBTA routes overlaid by default)
python -m visualization.create_choropleth_maps --source acs --years 2019

# Choropleths without MBTA overlay
python -m visualization.create_choropleth_maps --source acs --years 2019 --no-mbta-overlay

# Bar chart: compare 3 block groups
python -m visualization.create_bar_chart_comparisons 250277304011 250277304014 250092031005 --source acs

# Pie chart: housing cost burden for one block group
python -m visualization.create_pie_charts --geoid 250277304011 --group housing_cost_burden --source acs

# Line chart: population over years
python -m visualization.create_line_charts 250277304011 250277304014 --variable B01001_001E --source acs

# Scatter: transit overlap vs population
python -m visualization.create_scatter_plots --x-var overlap_total --y-var B01001_001E --source acs

# Stacked bar: race of householder across block groups
python -m visualization.create_stacked_bar_charts 250277304011 250277304014 --pie-group race_of_householder --source decennial

# Small multiples: population density 1990-2020
python -m visualization.create_small_multiples --variable CL8AA --transform per_aland --source decennial --years 1990,2000,2010,2020

# Heatmap: block groups × years
python -m visualization.create_heatmaps --source acs --mode geoids_x_years --variable B01001_001E
```

## Output Structure

Outputs are organized by chart type, data source, variable (human-readable name), and transformation:

```
output/
├── maps/
│   ├── acs/
│   │   ├── Total_Population/
│   │   │   ├── count/
│   │   │   └── per_aland/
│   │   └── Median_Household_Income/
│   │       └── count/
│   └── decennial/
│       └── ...
├── bar_charts/
│   ├── acs/
│   │   ├── Total_Population/
│   │   │   └── count/
│   │   └── ...
│   └── decennial/
├── pie_charts/
│   ├── acs/
│   │   ├── Housing_Cost_Burden/
│   │   └── Units_In_Structure/
│   └── decennial/
├── line_charts/
│   ├── acs/
│   │   └── Total_Population/
│   │       ├── count/
│   │       └── per_aland/
│   └── decennial/
├── scatter_plots/
│   ├── acs/
│   │   └── Total_Population/
│   │       ├── count/
│   │       └── per_aland/
│   └── decennial/
├── stacked_bar_charts/
│   ├── acs/
│   │   ├── Housing_Cost_Burden/
│   │   └── ...
│   └── decennial/
├── small_multiples/
│   ├── acs/
│   │   └── Total_Population/
│   │       ├── count/
│   │       └── per_aland/
│   └── decennial/
└── heatmaps/
    ├── acs/
    │   ├── Total_Population/
    │   │   └── count/
    │   └── Block_Groups_x_Variables/
    │       └── count/
    └── decennial/
```

All charts include comprehensive titles, axis labels, data source attribution (U.S. Census Bureau), and descriptive annotations.
