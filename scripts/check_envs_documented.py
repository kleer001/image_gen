#!/usr/bin/env python3
"""
check_envs_documented.py — flag generator environments missing from ENVIRONMENTS.md.

Scans the repo root for generator-environment directories (ComfyUI instances and
diffusers venvs) and prints a one-line reminder if any is not named in
ENVIRONMENTS.md. Keeps the environment inventory from drifting as new isolated
instances are added. Always exits 0 so it is safe in a SessionStart hook.

Repo root resolution is path-portable (works on the rig and in remote/web
sessions): $CLAUDE_PROJECT_DIR if set, else the parent of this script's dir.

Run by the SessionStart hook in .claude/settings.json. Also runnable by hand:
    python3 scripts/check_envs_documented.py
"""

import fnmatch
import os
import sys
from pathlib import Path

# A top-level directory whose name matches any of these is a generator environment.
PATTERNS = ("comfyui", "comfyui_*", "comfyui-*", "automatic1111", "*_env")


def repo_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


def env_dirs(root: Path):
    found = set()
    for p in root.iterdir():
        if not p.is_dir() or p.name.startswith("."):
            continue
        if any(fnmatch.fnmatch(p.name, pat) for pat in PATTERNS):
            found.add(p.name)
    return found


def main() -> int:
    root = repo_root()
    doc = root / "ENVIRONMENTS.md"
    dirs = env_dirs(root)
    if not doc.is_file():
        if dirs:
            print("⚠ ENVIRONMENTS.md missing — document these generator envs: "
                  + ", ".join(sorted(dirs)))
        return 0
    text = doc.read_text()
    missing = sorted(d for d in dirs if d not in text)
    if missing:
        print("⚠ Generator env(s) not in ENVIRONMENTS.md: "
              + ", ".join(missing) + " — add them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
