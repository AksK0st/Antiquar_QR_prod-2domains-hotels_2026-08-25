#!/usr/bin/env python3
"""Keep 7 newest backups plus one weekly backup for the previous 4 ISO weeks."""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
from pathlib import Path

STAMP = re.compile(r"^(\d{8})T\d{6}Z$")


def parse(path: Path) -> dt.datetime | None:
    match = STAMP.match(path.name)
    if not match:
        return None
    try:
        return dt.datetime.strptime(path.name, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.UTC)
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup_dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    entries = [(p, parse(p)) for p in args.backup_dir.iterdir() if p.is_dir()]
    entries = [(p, ts) for p, ts in entries if ts is not None]
    entries.sort(key=lambda x: x[1], reverse=True)

    keep = {p for p, _ in entries[:7]}
    current = dt.datetime.now(dt.UTC).isocalendar()
    current_key = (current.year, current.week)
    weekly: dict[tuple[int, int], Path] = {}
    for path, ts in entries:
        iso = ts.isocalendar()
        key = (iso.year, iso.week)
        if key == current_key:
            continue
        weekly.setdefault(key, path)
        if len(weekly) >= 4:
            break
    keep.update(weekly.values())

    for path, _ in entries:
        if path in keep:
            print(f"KEEP   {path.name}")
        else:
            print(f"DELETE {path.name}")
            if not args.dry_run:
                shutil.rmtree(path)


if __name__ == "__main__":
    main()
