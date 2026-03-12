# ACS Block Group MBTA Overlap

Build block groups with ACS data and MBTA stop buffer overlap counts.

## Run

```bash
python -m acs.build_block_groups_acs_overlap
```

## Data Integrity

- **Census API values**: Passed through unchanged; no transformation applied to downloaded data.
- **GEOID**: Derived from API geography columns (state, county, tract, block group) for consistent joins with TIGER boundaries.
- **Preprocessing**: Filters to MBTA block groups and adds year column; variable values are unchanged.
- **Output**: Left join of boundaries + overlap + ACS; no value modification.

## Data layout (all under `acs/data/`)

- `acs/data/raw/` – raw ACS downloads (if saved)
- `acs/data/normalized/` – preprocessed long-format output from `preprocess_acs`
- `acs/data/output/` – main pipeline outputs (GeoJSON, CSV)
- `acs/data/acs_variable_mapping.csv` – B-code to label mapping (reference)

## Config

- `config.yaml` at project root: `census_api_key`, `data_dir`, `output_dir` (default `acs/data/output`)
- `acs/config.yaml`: Optional overrides (e.g. `acs_years`)
