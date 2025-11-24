"""
count_keywords_json.py
Created: 2025-11-23 19:32
Author: VuLe@UMass Amherst
Last updated: 2025-11-23 19:32
Last modified by: VuLe@UMass Amherst
License: © Copyright 2025, Vu Le
Desc:
"""

import sys
import json
from pathlib import Path
from typing import Set

DEFAULT_PATH = Path("/mnt/data/8491878A-AFDF-4C04-89A8-2D8A95270117.png")


def read_json_records(path: Path):
    """
    Yield records (dicts) from either:
     - a single JSON array file, or
     - newline-delimited JSON (NDJSON)
    """
    text = path.read_text(encoding="utf-8")
    text = text.strip()
    if not text:
        return
    # If it starts with '[' treat as a JSON array
    if text.startswith("["):
        try:
            arr = json.loads(text)
            if isinstance(arr, list):
                for rec in arr:
                    yield rec
                return
        except json.JSONDecodeError:
            # fall through to NDJSON handling
            pass

    # NDJSON fallback: parse line-by-line
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            yield rec
        except json.JSONDecodeError:
            # skip invalid lines but warn
            print(
                f"Warning: skipping invalid JSON on line {lineno} in {path}",
                file=sys.stderr,
            )
            continue


def main(argv):
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_PATH
    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        return 2

    unique: Set[str] = set()
    null_or_missing = 0
    total = 0

    for rec in read_json_records(path):
        total += 1
        kw = rec.get("found_with_keyword") if isinstance(rec, dict) else None
        if kw is None:
            null_or_missing += 1
            continue
        # Normalize type to str
        if not isinstance(kw, str):
            kw = str(kw)
        unique.add(kw)

    print(f"Input file: {path}")
    print(f"Total records processed: {total}")
    print(f"Records with missing/null found_with_keyword: {null_or_missing}")
    print(f"Unique found_with_keyword count: {len(unique)}")
    if unique:
        print("Unique keywords:")
        for k in sorted(unique):
            print(" -", k)

    print(f"the total number of unique keywords scraped is {len(unique)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
