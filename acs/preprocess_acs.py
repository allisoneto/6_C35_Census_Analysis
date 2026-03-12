"""
Preprocess ACS data for cross-year comparison.

Similar to parse_json_entries.py: handles format changes across ACS vintages.
- Drops character-only variables (suffix A) when numeric (E/PE/M) exists:
  Census returns both DP02_0001E (numeric) and DP02_0001EA (character) in newer
  years; we keep the numeric for analysis.
- Column NAMES are kept as Census codes (DP02_0001E, B01001_001E, etc.) so the
  same variable has the same name across years—enabling direct year-over-year
  comparison without a mapping table.
- Outputs long-format table with year column for time-series analysis.
- Variable values are passed through unchanged; only column selection may change.

Usage:
  python -m acs.preprocess_acs

Input:
  acs/data/raw/ (or ACS data from build_block_groups_acs_overlap)
Output:
  acs/data/normalized/acs_block_groups_mbta_long.csv
"""

from pathlib import Path

import pandas as pd

# Paths: ACS data lives in acs/data/
ACS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ACS_ROOT.parent
ACS_RAW_DIR = ACS_ROOT / "data" / "raw"
ACS_NORMALIZED_DIR = ACS_ROOT / "data" / "normalized"


def normalize_acs_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize ACS columns: drop character (A) vars when numeric exists.

    Does not modify variable values; only removes redundant character columns.
    """
    cols = list(df.columns)
    to_drop = []
    for c in cols:
        if c.endswith("A") or c.endswith("MA"):
            base = c[:-1] if c.endswith("A") else c[:-2] + "M"
            if base in cols or base + "E" in cols or base + "PE" in cols:
                to_drop.append(c)
    return df.drop(columns=[c for c in to_drop if c in df.columns])


def preprocess_acs_by_year(
    acs_by_year: dict[int, pd.DataFrame],
    geoids: list[str] | None = None,
) -> pd.DataFrame:
    """
    Combine ACS data across years into long format.

    Variable values are passed through unchanged.
    """
    all_dfs = []
    for year, df in sorted(acs_by_year.items()):
        if df is None or df.empty:
            continue
        df = df.copy()
        df["year"] = year
        if geoids:
            df = df[df["GEOID"].isin(geoids)]
        df = normalize_acs_columns(df)
        all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    cols = ["GEOID", "year"] + [c for c in combined.columns if c not in ("GEOID", "year")]
    return combined[[c for c in cols if c in combined.columns]]


def main() -> None:
    """Run preprocessing on ACS raw files in acs_raw/ if present."""
    ACS_NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = list(ACS_RAW_DIR.glob("acs_*.csv")) if ACS_RAW_DIR.exists() else []
    if not raw_files:
        print("No raw ACS files in acs/data/raw/; run python -m acs.build_block_groups_acs_overlap with API key.")
        return

    acs_by_year = {}
    for f in raw_files:
        try:
            year = int(f.stem.split("_")[1])
            acs_by_year[year] = pd.read_csv(f)
        except (ValueError, IndexError):
            pass

    if not acs_by_year:
        print("Could not parse years from raw files.")
        return

    long_df = preprocess_acs_by_year(acs_by_year)
    out_path = ACS_NORMALIZED_DIR / "acs_block_groups_mbta_long.csv"
    long_df.to_csv(out_path, index=False)
    print(f"Saved {len(long_df)} rows to {out_path}")


if __name__ == "__main__":
    main()
