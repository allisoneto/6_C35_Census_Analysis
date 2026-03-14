"""
Remove decennial choropleth JSON files when decennial_extras exists for the same variable+transform.

When a variable has both decennial_* and decennial_extras_* files, we keep only decennial_extras
and remove the decennial version (extras takes precedence).

Run from tod-viz-viewer/: python scripts/clean_choropleth_overlap.py
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CHOROPLETH_DIR = SCRIPT_DIR.parent / "public" / "data" / "choropleth"


def main() -> None:
    if not CHOROPLETH_DIR.exists():
        print(f"Choropleth dir not found: {CHOROPLETH_DIR}")
        return

    # Build set of (variable, transform) that exist in decennial_extras
    extras_pairs: set[tuple[str, str]] = set()
    for p in CHOROPLETH_DIR.glob("decennial_extras_*.json"):
        stem = p.stem
        if not stem.startswith("decennial_extras_"):
            continue
        rest = stem[len("decennial_extras_"):]
        parts = rest.rsplit("_", 1)
        if len(parts) != 2:
            continue
        var_id, transform = parts
        extras_pairs.add((var_id, transform))

    # Find decennial files to remove (same var+transform exists in extras)
    to_remove: list[Path] = []
    for p in CHOROPLETH_DIR.glob("decennial_*.json"):
        if p.name.startswith("decennial_extras_"):
            continue
        stem = p.stem
        if not stem.startswith("decennial_"):
            continue
        rest = stem[len("decennial_"):]
        parts = rest.rsplit("_", 1)
        if len(parts) != 2:
            continue
        var_id, transform = parts
        if (var_id, transform) in extras_pairs:
            to_remove.append(p)

    for p in to_remove:
        print(f"Removing {p.name}")
        p.unlink()

    print(f"Removed {len(to_remove)} decennial files (duplicates of decennial_extras)")


if __name__ == "__main__":
    main()
