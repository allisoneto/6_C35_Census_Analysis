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


def preprocess_for_merged(
    nhgis_timeseries: pd.DataFrame,
    mapping_path: Path,
    geoids_filter: list[str] | None = None,
) -> pd.DataFrame:
    """
    Preprocess NHGIS time series data for merged (2010-basis) output.

    NHGIS time series already uses 2010 geography. Ensure GEOID and
    variable names are consistent.

    Parameters
    ----------
    nhgis_timeseries : pd.DataFrame
        NHGIS geographically standardized time series.
    mapping_path : Path
        Path to decennial_variable_mapping.csv.
    geoids_filter : list[str], optional
        If provided, keep only these 2010 GEOIDs.

    Returns
    -------
    pd.DataFrame
        Long-format DataFrame with year, GEOID, canonical variables.
    """
    if nhgis_timeseries is None or nhgis_timeseries.empty:
        return pd.DataFrame()

    df = nhgis_timeseries.copy()

    # NHGIS may use GISJOIN or GEOID; standardize
    if "GISJOIN" in df.columns and "GEOID" not in df.columns:
        df["GEOID"] = df["GISJOIN"].apply(
            lambda x: str(x)[1:13] if pd.notna(x) and len(str(x)) >= 13 else ""
        )
    if "GEOID" in df.columns:
        df["GEOID"] = ensure_geoid_12digit(df["GEOID"])

    # NHGIS time series has YEAR or DATAYEAR column
    year_col = None
    for c in ["YEAR", "DATAYEAR", "year", "Year"]:
        if c in df.columns:
            year_col = c
            break
    if year_col and year_col != "year":
        df["year"] = df[year_col].astype(int)

    if geoids_filter:
        geoids_str = [str(g).zfill(12) if len(str(g)) < 12 else str(g) for g in geoids_filter]
        df = df[df["GEOID"].isin(geoids_str)]

    return df
