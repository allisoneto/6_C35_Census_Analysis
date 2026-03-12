"""
Download 2010 decennial census block-level data from Census API.

Block geography requires one API request per tract. For MBTA communities
(~1000+ tracts), this can take several minutes. Use --dry-run to skip download.
"""

import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import pandas as pd

STATE_FIPS = "25"
CENSUS_API_BASE = "https://api.census.gov/data"

# 2010 SF1 block-level variables (P001001, H001001, etc. available at block)
VARS_2010_BLOCK = [
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


def _build_block_geoid_from_row(row_values: list, headers: list) -> str:
    """
    Build 15-digit block GEOID from Census API response.

    Parameters
    ----------
    row_values : list
        Row values from API response.
    headers : list
        Column headers from API response.

    Returns
    -------
    str
        15-digit GEOID (state + county + tract + block).
    """
    state = county = tract = block = ""
    for h, v in zip(headers, row_values):
        val = str(v or "").strip()
        h_lower = h.lower()
        if h_lower == "state":
            state = val
        elif h_lower == "county":
            county = val.zfill(3) if val else ""
        elif h_lower == "tract":
            tract = re.sub(r"\D", "", val)[:6].zfill(6) if val else ""
        elif h_lower == "block":
            block = re.sub(r"\D", "", val)[:4].zfill(4) if val else ""
    return state + county + tract + block


def download_blocks_2010(
    geoids: list[str],
    api_key: str,
    *,
    dry_run: bool = False,
    delay_seconds: float = 0.1,
) -> pd.DataFrame:
    """
    Download 2010 decennial census block data for given GEOIDs.

    Makes one API request per tract; filters to requested block GEOIDs.

    Parameters
    ----------
    geoids : list[str]
        Block GEOIDs (15-digit) to fetch.
    api_key : str
        Census API key.
    dry_run : bool, optional
        If True, skip download and return empty DataFrame.
    delay_seconds : float, optional
        Delay between API requests to avoid rate limiting.

    Returns
    -------
    pd.DataFrame
        Block data with GEOID and census variables.
    """
    if dry_run:
        print("  [dry-run] Would request 2010 block data for", len(geoids), "blocks")
        return pd.DataFrame()

    geoids = [str(g) for g in geoids]
    # Extract unique (county, tract) from 15-digit GEOIDs: state(2) county(3) tract(6) block(4)
    tract_tuples = set()
    for g in geoids:
        if len(g) >= 11:
            county = g[2:5]
            tract = g[5:11]
            tract_tuples.add((county, tract))

    tract_tuples = sorted(tract_tuples)
    print(f"  Requesting 2010 block data for {len(tract_tuples)} tracts...")

    vars_str = ",".join(VARS_2010_BLOCK)
    geoids_set = set(geoids)
    all_dfs = []

    for i, (county, tract) in enumerate(tract_tuples):
        url = (
            f"{CENSUS_API_BASE}/2010/dec/sf1?"
            f"get={vars_str}&"
            f"for=block:*&"
            f"in=state:{STATE_FIPS}%20county:{county}%20tract:{tract}"
        )
        if api_key:
            url += f"&key={api_key}"

        try:
            req = Request(url, headers={"User-Agent": "MBTA-Blocks-Pipeline/1.0"})
            with urlopen(req, timeout=90) as r:
                data = json.loads(r.read().decode())
        except HTTPError as e:
            try:
                body = e.fp.read().decode()[:200] if e.fp else ""
            except Exception:
                body = ""
            print(f"    HTTP {e.code} county {county} tract {tract}: {body}")
            continue
        except (URLError, json.JSONDecodeError) as e:
            print(f"    Error county {county} tract {tract}: {e}")
            continue

        if len(data) < 2:
            continue

        headers = [str(h) for h in data[0]]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        df["GEOID"] = [_build_block_geoid_from_row(row.tolist(), headers) for _, row in df.iterrows()]
        df = df[df["GEOID"].isin(geoids_set)]
        if not df.empty:
            all_dfs.append(df)

        if delay_seconds > 0:
            time.sleep(delay_seconds)

        if (i + 1) % 100 == 0:
            print(f"    Progress: {i + 1}/{len(tract_tuples)} tracts")

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=["GEOID"])
    print(f"  Retrieved {len(combined)} blocks, {len(combined.columns) - 1} vars")
    return combined
