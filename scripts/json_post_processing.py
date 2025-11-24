# json_post_processing.py
# Created on: 2025-11-18 16:15:34
# Author: VuLe@macbook
# Last updated: 2025-11-23 18:18:02
# Last modified by: VuLe@UMass Amherst

"""
Convert newline-separated JSON records (NDJSON) of gizmos into a single JSON array
with the target schema, filtering out duplicate gizmo_id values (keep first occurrence).

Usage:
    python json_post_processing.py input.ndjson output.json
"""

import sys
import json
from pathlib import Path
from typing import Any, Dict, Optional


def transform_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform one input record into the desired output shape.
    - copies top-level fields (gizmo_id, from, url, found_with_keyword)
    - builds a 'gizmo' object with added/normalized fields
    - sets tools to [] and status to "available"
    """
    gizmo_id = rec.get("gizmo_id")
    gizmo_in = rec.get("gizmo", {})

    # Defensive reads
    display_in = gizmo_in.get("display", {}) if isinstance(gizmo_in, dict) else {}
    author_in = gizmo_in.get("author", {}) if isinstance(gizmo_in, dict) else {}
    vanity_in = gizmo_in.get("vanity_metrics", {}) if isinstance(gizmo_in, dict) else {}

    out = {
        "gizmo_id": gizmo_id,
        "from": rec.get("from"),
        "url": rec.get("url"),
        "found_with_keyword": rec.get("found_with_keyword"),
        "gizmo": {
            "id": gizmo_id,
            "display": {
                "name": display_in.get("name"),
                "description": None,
                "prompt_starters": [],
                "categories": [],
            },
            "author": {"display_name": author_in.get("display_name")},
            "vanity_metrics": {
                "rating": None,
                # per your example, set these to null even if present in input
                "num_conversations_str": None,
                "rank": None,
            },
        },
        "tools": [],
        "status": "available",
    }

    return out


def main(argv):
    if len(argv) != 3:
        print("Usage: python json_post_processing.py input.ndjson output.json")
        return 1

    in_path = Path(argv[1])
    out_path = Path(argv[2])

    if not in_path.exists():
        print(f"Input file not found: {in_path}")
        return 2

    out_list = []
    seen_ids = set()
    duplicates_skipped = 0
    missing_id_count = 0

    with in_path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid JSON on line {lineno}: {e}")
                continue

            gizmo_id = rec.get("gizmo_id")
            if gizmo_id is None:
                # Option: treat records without gizmo_id as unique (keep them),
                # or skip them. Here we keep them but count them.
                missing_id_count += 1
                out_list.append(transform_record(rec))
                continue

            if gizmo_id in seen_ids:
                duplicates_skipped += 1
                continue

            seen_ids.add(gizmo_id)
            out_list.append(transform_record(rec))

    # Write pretty JSON array
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out_list, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(out_list)} unique records to {out_path}")
    if duplicates_skipped:
        print(f"Skipped {duplicates_skipped} duplicate records (same gizmo_id).")
    if missing_id_count:
        print(f"Kept {missing_id_count} records with missing gizmo_id (no id present).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
