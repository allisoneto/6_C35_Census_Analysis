"""
Preprocess decennial census data: align variable names across years.

Uses decennial_variable_mapping.csv to map year-specific variable codes
to canonical names. Handles GEOID normalization for 1990/2000/2010/2020.
"""

from pathlib import Path

import pandas as pd


def load_variable_mapping(mapping_path: Path) -> pd.DataFrame:
    """
    Load decennial variable mapping (canonical_name -> var_1990, var_2000, etc.).

    Parameters
    ----------
    mapping_path : Path
        Path to decennial_variable_mapping.csv.

    Returns
    -------
    pd.DataFrame
        Mapping table with canonical_name and var_YYYY columns.
    """
    if not mapping_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(mapping_path)
    return df


def normalize_to_canonical(
    df: pd.DataFrame,
    year: int,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rename year-specific variables to canonical names.

    Parameters
    ----------
    df : pd.DataFrame
        Raw census data for one year.
    year : int
        Census year (1990, 2000, 2010, 2020).
    mapping : pd.DataFrame
        Variable mapping from load_variable_mapping.

    Returns
    -------
    pd.DataFrame
        DataFrame with canonical variable names (where mapping exists).
    """
    var_col = f"var_{year}"
    if var_col not in mapping.columns:
        return df

    rename = {}
    for _, row in mapping.iterrows():
        canonical = row["canonical_name"]
        var_code = row[var_col]
        if pd.notna(var_code) and str(var_code).strip() and var_code in df.columns:
            rename[var_code] = canonical

    return df.rename(columns=rename)


def ensure_geoid_12digit(series: pd.Series) -> pd.Series:
    """
    Normalize GEOID to 12-digit string (state+county+tract+bg).

    Parameters
    ----------
    series : pd.Series
        GEOID or GISJOIN series.

    Returns
    -------
    pd.Series
        Normalized 12-digit GEOID strings.
    """
    def _norm(g):
        if pd.isna(g):
            return ""
        s = str(g).strip()
        if s.startswith("G"):
            s = s[1:]
        # Keep only digits, take first 12
        digits = "".join(c for c in s if c.isdigit())
        return digits[:12].zfill(12) if len(digits) >= 12 else digits.zfill(12)

    return series.apply(_norm)


def preprocess_native(
    data_by_year: dict[int, pd.DataFrame],
    mapping_path: Path,
    geoids_filter: list[str] | None = None,
) -> dict[int, pd.DataFrame]:
    """
    Preprocess native (year-specific) decennial data.

    Parameters
    ----------
    data_by_year : dict[int, pd.DataFrame]
        Raw data by year from download_decennial.
    mapping_path : Path
        Path to decennial_variable_mapping.csv.
    geoids_filter : list[str], optional
        If provided, keep only these GEOIDs.

    Returns
    -------
    dict[int, pd.DataFrame]
        Year -> preprocessed DataFrame with canonical names.
    """
    mapping = load_variable_mapping(mapping_path)
    result = {}

    for year, df in data_by_year.items():
        if df is None or df.empty:
            continue

        df = df.copy()

        # Normalize GEOID
        if "GEOID" in df.columns:
            df["GEOID"] = ensure_geoid_12digit(df["GEOID"])
        elif "GISJOIN" in df.columns:
            df["GEOID"] = ensure_geoid_12digit(df["GISJOIN"])

        # Apply variable mapping
        if not mapping.empty:
            df = normalize_to_canonical(df, year, mapping)

        if geoids_filter:
            geoids_str = [str(g).zfill(12) if len(str(g)) < 12 else str(g) for g in geoids_filter]
            df = df[df["GEOID"].isin(geoids_str)]

        df["year"] = year
        result[year] = df

    return result


def _reshape_nhgis_wide_to_long(wide_df: pd.DataFrame) -> pd.DataFrame:
    """
    Reshape NHGIS time series from wide format to long format.

    NHGIS time series has one row per block group with columns like CL8AA1990,
    CL8AA2000, CL8AA2010, CL8AA2020. This converts to one row per (GEOID, year)
    with variable columns for that year (excluding L/U confidence bound columns).

    Parameters
    ----------
    wide_df : pd.DataFrame
        NHGIS data in wide format (one row per block group).

    Returns
    -------
    pd.DataFrame
        Long-format data with GEOID, year, and census variables.
    """
    id_cols = [
        c for c in wide_df.columns
        if c in ("GEOID", "GISJOIN", "STATE", "STATEA", "COUNTY", "COUNTYA", "TRACTA", "BLCK_GRPA", "GEOGYEAR")
        or c in ("YEAR", "DATAYEAR", "year", "Year")
    ]
    data_cols = [c for c in wide_df.columns if c not in id_cols]

    years = [1990, 2000, 2010, 2020]
    long_rows = []

    for _, row in wide_df.iterrows():
        geoid = row["GEOID"]
        for year in years:
            year_data = {"GEOID": geoid, "year": year}
            for col in data_cols:
                # Match columns ending with YYYY (value columns, not L/U bounds)
                if col.endswith(str(year)) and not col.endswith(str(year) + "L") and not col.endswith(str(year) + "U"):
                    base_name = col[: -len(str(year))]
                    year_data[base_name] = row[col]
            long_rows.append(year_data)

    return pd.DataFrame(long_rows)


def preprocess_for_merged(
    nhgis_timeseries: pd.DataFrame,
    mapping_path: Path,
    geoids_filter: list[str] | None = None,
) -> pd.DataFrame:
    """
    Preprocess NHGIS time series data for merged (2010-basis) output.

    NHGIS time series is in wide format (one row per block group, columns like
    CL8AA1990, CL8AA2000). This reshapes to long format (one row per GEOID+year)
    and ensures GEOID matches TIGER block group format.

    Parameters
    ----------
    nhgis_timeseries : pd.DataFrame
        NHGIS geographically standardized time series (wide format).
    mapping_path : Path
        Path to decennial_variable_mapping.csv.
    geoids_filter : list[str], optional
        If provided, keep only these 2010 GEOIDs.

    Returns
    -------
    pd.DataFrame
        Long-format DataFrame with year, GEOID, and census variables.
    """
    if nhgis_timeseries is None or nhgis_timeseries.empty:
        return pd.DataFrame()

    df = nhgis_timeseries.copy()

    # Build 12-digit GEOID from components (more reliable than parsing GISJOIN)
    if all(c in df.columns for c in ["STATEA", "COUNTYA", "TRACTA", "BLCK_GRPA"]):
        bg = df["BLCK_GRPA"].astype(str).str.replace(r"\D", "", regex=True)
        bg = bg.where(bg.str.len() > 0, "0").str[-1]
        df["GEOID"] = (
            df["STATEA"].astype(str).str.zfill(2)
            + df["COUNTYA"].astype(str).str.zfill(3)
            + df["TRACTA"].astype(str).str.zfill(6)
            + bg
        )
    elif "GISJOIN" in df.columns and "GEOID" not in df.columns:
        df["GEOID"] = df["GISJOIN"].apply(
            lambda x: str(x)[1:13] if pd.notna(x) and len(str(x)) >= 13 else ""
        )
    if "GEOID" in df.columns:
        df["GEOID"] = ensure_geoid_12digit(df["GEOID"])

    if geoids_filter:
        geoids_str = [str(g).zfill(12) if len(str(g)) < 12 else str(g) for g in geoids_filter]
        df = df[df["GEOID"].isin(geoids_str)]

    # Reshape from wide (one row per block group) to long (one row per GEOID+year)
    df = _reshape_nhgis_wide_to_long(df)

    return df
