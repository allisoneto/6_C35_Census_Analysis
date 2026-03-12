"""
Parse NHGIS time series codebook files to extract variable codes and descriptions.

Extracts:
- Table N: (CODE) Table Name -> table_topic
- Time series XX: Description -> variable (CODE+XX), human_readable_name (Description)

Skips lines containing "Lower bound" or "Upper bound".
Outputs CSV matching ACS format: variable, human_readable_name, table_topic
"""

import re
from pathlib import Path

import pandas as pd

# Regex patterns for parsing codebook format
TABLE_PATTERN = re.compile(r"^Table \d+: \((\w+)\) (.+)")
TIME_SERIES_PATTERN = re.compile(r"^\s*Time series (\w+): (.+)")


def parse_codebook(filepath: Path) -> list[dict]:
    """
    Parse a single NHGIS codebook file and extract variable mappings.

    Parameters
    ----------
    filepath : Path
        Path to the codebook .txt file.

    Returns
    -------
    list[dict]
        List of dicts with keys: variable, human_readable_name, table_topic.
    """
    rows = []
    current_table_code = None
    current_table_topic = None

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            # Skip lines with Lower bound or Upper bound
            if "Lower bound" in line or "Upper bound" in line:
                continue

            # Match Table N: (CODE) Table Name
            table_match = TABLE_PATTERN.match(line.strip())
            if table_match:
                current_table_code = table_match.group(1)
                current_table_topic = table_match.group(2).strip()
                continue

            # Match Time series XX: Description
            ts_match = TIME_SERIES_PATTERN.match(line)
            if ts_match and current_table_code is not None:
                ts_code = ts_match.group(1)
                description = ts_match.group(2).strip()
                variable = f"{current_table_code}{ts_code}"
                rows.append(
                    {
                        "variable": variable,
                        "human_readable_name": description,
                        "table_topic": current_table_topic,
                    }
                )

    return rows


def main() -> None:
    """Parse all NHGIS codebook files and write combined variable mapping CSV."""
    raw_dir = Path(__file__).resolve().parent / "data" / "raw"
    output_path = Path(__file__).resolve().parent / "data" / "decennial_variable_mapping_nhgis.csv"

    codebook_files = sorted(
        raw_dir.glob("nhgis000*_ts_geog2010_blck_grp_codebook.txt")
    )

    all_rows = []
    seen_variables = set()

    for filepath in codebook_files:
        rows = parse_codebook(filepath)
        for row in rows:
            # Deduplicate: same variable may appear in multiple codebooks
            if row["variable"] not in seen_variables:
                seen_variables.add(row["variable"])
                all_rows.append(row)

    df = pd.DataFrame(all_rows)
    df = df.sort_values(["table_topic", "variable"]).reset_index(drop=True)
    df.to_csv(output_path, index=False)
    print(f"Wrote {len(df)} variables to {output_path}")


if __name__ == "__main__":
    main()
