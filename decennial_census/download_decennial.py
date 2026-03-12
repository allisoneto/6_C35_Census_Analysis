"""
Download decennial census data for block groups in Massachusetts.

Data sources (checked in order):
  - NHGIS: If nhgis_{year}_block_groups.csv exists in data/raw/, use it.
    Use for 1990 (no Census API) and optionally 2000/2010/2020 to get
    the same columns as 1990 (income, housing values, etc.).
  - Census API: Fallback for 2000/2010/2020 when no NHGIS file exists.
    Limited to SF1/PL vars: population, housing, race/ethnicity only.

Create NHGIS extracts at https://data2.nhgis.org/main (free registration).
Variable codes differ by year; see decennial_variable_mapping.csv.
"""

import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import pandas as pd

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
STATE_FIPS = "25"  # Massachusetts
CENSUS_API_BASE = "https://api.census.gov/data"

# Core variables by year (Census API variable names)
# 2020 PL (Redistricting Data)
VARS_2020 = [
    "P1_001N",   # Total population
    "H1_001N",   # Total housing units
    "H1_002N",   # Occupied
    "H1_003N",   # Vacant
    "P2_001N",   # Total (race/ethnicity)
    "P2_002N",   # Hispanic or Latino
    "P2_003N",   # Not Hispanic or Latino
    "P2_005N",   # White alone
    "P2_006N",   # Black alone
    "P2_007N",   # AIAN alone
    "P2_008N",   # Asian alone
    "P2_009N",   # NHPI alone
    "P2_010N",   # Some other race alone
    "P2_011N",   # Two or more races
]

# 2010 SF1 (H001 has only H001001 at block group; H003 has occupancy)
VARS_2010 = [
    "P001001",   # Total population
    "H001001",   # Total housing units
    "H003001",   # Total (occupancy)
    "H003002",   # Occupied
    "H003003",   # Vacant
    "P002001",   # Total (race)
    "P002002",   # Hispanic
    "P002003",   # Not Hispanic
    "P003002",   # White
    "P003003",   # Black
    "P003004",   # AIAN
    "P003005",   # Asian
    "P003006",   # NHPI
    "P003007",   # Other
    "P003008",   # Two or more
]

# 2000 SF1 (H001 has only H001001; H003 has occupancy)
VARS_2000 = [
    "P001001",   # Total population
    "H001001",   # Total housing units
    "H003001",   # Total (occupancy)
    "H003002",   # Occupied
    "H003003",   # Vacant
    "P004002",   # Hispanic
    "P004003",   # Not Hispanic
    "P003002",   # White
    "P003003",   # Black
    "P003004",   # AIAN
    "P003005",   # Asian
    "P003006",   # NHPI
    "P003007",   # Other
    "P003008",   # Two or more
]


def _build_geoid_from_row(row_values: list, headers: list, year: int) -> str:
    """
    Build 12-digit GEOID from Census API response row.

    Parameters
    ----------
    row_values : list
        Row values from API response.
    headers : list
        Column headers from API response.
    year : int
        Census year (affects tract format).

    Returns
    -------
    str
        12-digit GEOID (state + county + tract + block group).
    """
    state = county = tract = bg = ""
    for h, v in zip(headers, row_values):
        val = str(v or "").strip()
        h_lower = h.lower()
        if h_lower == "state":
            state = val
        elif h_lower == "county":
            county = val.zfill(3) if val else ""
        elif h_lower == "tract":
            tract = re.sub(r"\D", "", val)[:6].zfill(6) if val else ""
        elif "block" in h_lower and "group" in h_lower:
            bg = str(int(float(val))) if val and val != "" else ""
    return state + county + tract + bg


def download_census_api(
    year: int,
    api_key: str,
    geoids_filter: list[str] | None = None,
) -> pd.DataFrame:
    """
    Download decennial census block group data from Census API.

    Parameters
    ----------
    year : int
        Census year (2000, 2010, or 2020).
    api_key : str
        Census API key.
    geoids_filter : list[str], optional
        If provided, filter to these GEOIDs only.

    Returns
    -------
    pd.DataFrame
        Block group data with GEOID and census variables.
    """
    if year == 2020:
        dataset = "dec/pl"
        vars_list = VARS_2020
    elif year == 2010:
        dataset = "dec/sf1"
        vars_list = VARS_2010
    elif year == 2000:
        dataset = "dec/sf1"
        vars_list = VARS_2000
    else:
        raise ValueError(f"Census API does not support year {year}; use NHGIS for 1990")

    vars_str = ",".join(vars_list)
    # Massachusetts county FIPS codes
    ma_counties = ["001", "003", "005", "007", "009", "011", "013", "015", "017", "021", "023", "025", "027"]

    all_dfs = []
    for county in ma_counties:
        url = (
            f"{CENSUS_API_BASE}/{year}/{dataset}?"
            f"get={vars_str}&"
            f"for=block%20group:*&"
            f"in=state:{STATE_FIPS}%20county:{county}"
        )
        if api_key:
            url += f"&key={api_key}"

        try:
            req = Request(url, headers={"User-Agent": "Decennial-Census-MBTA-Pipeline/1.0"})
            with urlopen(req, timeout=90) as r:
                data = json.loads(r.read().decode())
        except HTTPError as e:
            body = ""
            try:
                body = e.fp.read().decode()[:200] if e.fp else ""
            except Exception:
                pass
            print(f"    HTTP {e.code} county {county}: {body}")
            continue
        except (URLError, json.JSONDecodeError) as e:
            print(f"    Error county {county}: {e}")
            continue

        if len(data) < 2:
            continue

        headers = [str(h) for h in data[0]]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        df["GEOID"] = [_build_geoid_from_row(row.tolist(), headers, year) for _, row in df.iterrows()]
        all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=["GEOID"])
    if geoids_filter:
        geoids_filter = [str(g) for g in geoids_filter]
        combined = combined[combined["GEOID"].isin(geoids_filter)]

    return combined


def _load_nhgis_csv(raw_dir: Path, year: int) -> pd.DataFrame:
    """
    Load block group data from NHGIS CSV for a given year.

    Checks for nhgis_{year}_block_groups.csv or nhgis_{year}_bg.csv.
    Use NHGIS Data Finder (https://data2.nhgis.org/main) to create extracts
    with the same variables as your 1990 extract for column consistency.

    Parameters
    ----------
    raw_dir : Path
        Path to data/raw directory.
    year : int
        Census year (1990, 2000, 2010, or 2020).

    Returns
    -------
    pd.DataFrame
        Block group data with GISJOIN or GEOID and variables.
    """
    paths = [
        raw_dir / f"nhgis_{year}_block_groups.csv",
        raw_dir / f"nhgis_{year}_bg.csv",
    ]
    for p in paths:
        if p.exists():
            df = pd.read_csv(p)
            # NHGIS uses GISJOIN; convert to 12-digit GEOID if needed
            if "GISJOIN" in df.columns and "GEOID" not in df.columns:
                df["GEOID"] = df["GISJOIN"].apply(
                    lambda x: str(x)[1:13] if pd.notna(x) and len(str(x)) >= 13 else ""
                )
            return df

    return pd.DataFrame()


def load_nhgis_1990(raw_dir: Path) -> pd.DataFrame:
    """
    Load 1990 block group data from NHGIS CSV.

    Expected: decennial_census/data/raw/nhgis_1990_block_groups.csv
    Create via NHGIS Data Finder (https://data2.nhgis.org/main):
    - Geographic level: Block Group
    - State: Massachusetts
    - Tables: 1990 SF1 population and housing (add SF3 for income, housing values)

    Parameters
    ----------
    raw_dir : Path
        Path to data/raw directory.

    Returns
    -------
    pd.DataFrame
        Block group data with GISJOIN or GEOID and variables.
    """
    return _load_nhgis_csv(raw_dir, 1990)


def load_nhgis_time_series(raw_dir: Path) -> pd.DataFrame:
    """
    Load NHGIS geographically standardized time series (1990-2020 to 2010 block groups).

    Expected: decennial_census/data/raw/nhgis_timeseries_2010_bg.csv
    From NHGIS Data Finder, Time Series Tables tab:
    - Geographic level: Block Group
    - Standardized to 2010 geography
    - Years: 1990, 2000, 2010, 2020

    Parameters
    ----------
    raw_dir : Path
        Path to data/raw directory.

    Returns
    -------
    pd.DataFrame
        Long-format data with year, GEOID (2010), and variables.
    """
    paths = [
        raw_dir / "nhgis_timeseries_2010_bg.csv",
        raw_dir / "nhgis_ts_2010_bg.csv",
    ]
    for p in paths:
        if p.exists():
            return pd.read_csv(p)

    return pd.DataFrame()


def download_all(
    years: list[int],
    api_key: str,
    raw_dir: Path,
    geoids_filter: list[str] | None = None,
) -> dict[int, pd.DataFrame]:
    """
    Download decennial data for all requested years.

    Parameters
    ----------
    years : list[int]
        Census years (1990, 2000, 2010, 2020).
    api_key : str
        Census API key (for 2000, 2010, 2020).
    raw_dir : Path
        Directory for raw downloads; NHGIS files expected here.
    geoids_filter : list[str], optional
        Filter to these GEOIDs (e.g., MBTA block groups).

    Returns
    -------
    dict[int, pd.DataFrame]
        Year -> DataFrame with GEOID and census variables.
    """
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for year in years:
        # NHGIS: 1990 has no Census API; 2000/2010/2020 can use NHGIS for same columns as 1990
        df = _load_nhgis_csv(raw_dir, year)
        if not df.empty:
            print(f"  Loading {year} from NHGIS file...")
            if geoids_filter:
                geoids_str = [str(g) for g in geoids_filter]
                if "GEOID" in df.columns:
                    df = df[df["GEOID"].isin(geoids_str)]
            results[year] = df
            print(f"    {len(df)} block groups, {len(df.columns) - 1} vars")
        elif year == 1990:
            print("  Loading 1990 from NHGIS file...")
            print("    No nhgis_1990_block_groups.csv found; place NHGIS extract in data/raw/")
        else:
            # Fall back to Census API (limited vars: pop, housing, race/ethnicity only)
            print(f"  Downloading {year} from Census API (limited vars)...")
            df = download_census_api(year, api_key, geoids_filter)
            if not df.empty:
                results[year] = df
                print(f"    {len(df)} block groups, {len(df.columns) - 1} vars")
            else:
                print(f"    No data for {year}")

    return results
