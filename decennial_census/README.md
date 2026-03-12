# Decennial Census Block Group MBTA Overlap

Produces **merged** output only: 2010 block group geography with 1990-2020 data from NHGIS time series. For consistent change-over-time analysis.

## Required Data

### Shared (project root)

- `data/mbta_communities/mbta_communities.geojson`
- `data/mbta_stops_with_buffer/mbta_stops_with_buffer_collapsed.geojson`

### 2010 Block Group Shapefile

**Option A – Census Bureau web tool**

1. Go to https://www.census.gov/cgi-bin/geo/shapefiles/index.php
2. Select **Year**: 2010
3. Select **Layer type**: Block Groups
4. Select **State**: Massachusetts
5. Click **Download** and extract the ZIP

**Option B – Direct download**

1. Download: https://www2.census.gov/geo/tiger/TIGER2010/BG/2010/tl_2010_25_bg10.zip  
2. Extract to `data/census/` or `decennial_census/data/raw/`  
3. The script looks for `tl_2010_25_bg10.shp` or `tl_2010_25_bg.shp`

**Option C – MassGIS**

- MassGIS 2010 Census block groups: https://www.mass.gov/info-details/massgis-data-2010-us-census  
- Use the CENSUS2010BLOCKGROUPS_POLY layer; export to shapefile if needed.

### NHGIS time series

| Purpose | File | Source |
|---------|------|--------|
| Merged data | `nhgis_timeseries_2010_bg.csv` | [NHGIS Data Finder](https://data2.nhgis.org/main) → Time Series Tables |

Place in `decennial_census/data/raw/`.

## Configuration

- `decennial_census/config.yaml`: Set `census_api_key` (or leave empty to inherit from project `config.yaml`).
- NHGIS requires free registration; create extracts manually and place CSVs in `data/raw/`.

## Run

**Block groups (merged) — ~3,500–7,000 units:**
```bash
python -m decennial_census.build_block_groups_decennial_overlap
```

**2010 Census blocks (separate pipeline) — ~93,000 units. Use only if you need block-level detail.**

Uses 2010 block geography; decennial data at block level. Requires block shapefile (NOT block groups):

- Download: https://www2.census.gov/geo/tiger/TIGER2010/TABBLOCK/2010/tl_2010_25_tabblock10.zip
- Extract to `data/census/` or `decennial_census/data/raw/`

```bash
python -m decennial_census.build_blocks_2010_overlap
python -m decennial_census.build_blocks_2010_overlap --dry-run   # Skip download/writes
```
