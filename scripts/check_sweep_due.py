#!/usr/bin/env python3
"""
check_sweep_due.py — surface the weekly update-sweep cadence.

Finds the repo root, reads the date of the newest radar/ digest, and prints a
one-line reminder if the last sweep is older than the cadence (default 7 days)
or if no digest exists yet. Always exits 0 so it is safe in a SessionStart hook.

Repo root resolution is path-portable (works on the rig and in remote/web
sessions): $CLAUDE_PROJECT_DIR if set, else the parent of this script's dir.

Run by the SessionStart hook in .claude/settings.json. Also runnable by hand:
    python3 scripts/check_sweep_due.py
"""

import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

CADENCE_DAYS = 7
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


def repo_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


def newest_digest_date(radar_dir: Path):
    newest = None
    if not radar_dir.is_dir():
        return None
    for f in radar_dir.iterdir():
        m = DATE_RE.match(f.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if newest is None or d > newest:
            newest = d
    return newest


def main() -> int:
    radar = repo_root() / "radar"
    newest = newest_digest_date(radar)
    if newest is None:
        print("⏰ Update sweep never run — read UPDATE.html and run the first sweep (14-day window).")
        return 0
    age = (date.today() - newest).days
    if age >= CADENCE_DAYS:
        print(
            f"⏰ Update sweep due — last digest {newest.isoformat()} ({age}d ago). "
            "Read UPDATE.html and run the weekly sweep."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
