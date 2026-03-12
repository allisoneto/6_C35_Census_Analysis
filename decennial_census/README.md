# Decennial Census Block Group MBTA Overlap

Produces two output versions:

1. **Merged** (2010 geography): Block groups standardized to 2010 boundaries with 1990-2020 data from NHGIS time series. For consistent change-over-time analysis.
2. **Native** (per-year geometry): Block groups with year-specific boundaries. For hole-free single-year visualization.

## Required Data

### Shared (project root)

- `data/mbta_communities/mbta_communities.geojson`
- `data/mbta_stops_with_buffer/mbta_stops_with_buffer_collapsed.geojson`
- `data/census/tl_2024_25_bg.shp` (2020 block groups; used for native 2020)

### 2010 Block Group Shapefile (for merged + native 2010)

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

### Other decennial data

| Purpose | File | Source |
|---------|------|--------|
| Merged data | `nhgis_timeseries_2010_bg.csv` | [NHGIS Data Finder](https://data2.nhgis.org/main) → Time Series Tables |
| Native 1990 data | `nhgis_1990_block_groups.csv` | NHGIS Data Finder |
| Native 1990/2000 boundaries | `tl_1990_25_bg.shp`, `tl_2000_25_bg.shp` | Census TIGER archive or NHGIS |

Place files in `decennial_census/data/raw/` or `data/census/` as appropriate.

## Configuration

- `decennial_census/config.yaml`: Set `census_api_key` (or leave empty to inherit from project `config.yaml`).
- NHGIS requires free registration; create extracts manually and place CSVs in `data/raw/`.

## Run

**Block groups (merged + native):**
```bash
python -m decennial_census.build_block_groups_decennial_overlap
```

**2010 Census blocks (separate pipeline):**

Uses 2010 block geography; decennial data at block level. Requires block shapefile:

- Download: https://www2.census.gov/geo/tiger/TIGER2010/TABBLOCK/2010/tl_2010_25_tabblock10.zip
- Extract to `data/census/` or `decennial_census/data/raw/`

```bash
python -m decennial_census.build_blocks_2010_overlap
python -m decennial_census.build_blocks_2010_overlap --dry-run   # Skip download/writes
```
