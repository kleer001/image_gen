#!/usr/bin/env python3
"""
Sync INDEX.md to match current filesystem state.

Actions taken:
  - Removes table rows for files that no longer exist on disk
  - Appends new files (not yet in INDEX.md) to an ## Unindexed section
  - Updates the "Last updated" timestamp
  - Never modifies existing rows (preserves hand-written metadata)

Run manually: python3 scripts/sync_index.py
Run by watch_models.sh automatically on file events.
"""

import re
import sys
from datetime import date
from pathlib import Path

YAML = Path(__file__).parent.parent / "models.yaml"


def load_yaml_catalog():
    """
    Load models.yaml and return {filename: entry} for known models.
    Returns empty dict if PyYAML is unavailable or models.yaml is missing.
    """
    try:
        import yaml
    except ImportError:
        return {}
    if not YAML.exists():
        return {}
    try:
        entries = yaml.safe_load(YAML.read_text()) or []
    except Exception:
        return {}
    catalog = {}
    for entry in entries:
        if entry.get("type") == "shards":
            # shards have no single dest — skip (they're rarely unindexed)
            continue
        dest = entry.get("dest", "")
        if dest:
            catalog[Path(dest).name] = entry
    return catalog

REPO = Path(__file__).parent.parent
INDEX = REPO / "INDEX.md"

MODEL_DIRS = {
    "checkpoints":             "Checkpoints",
    "diffusion_models":        "Diffusion Models",
    "vae":                     "VAE",
    "text_encoders":           "Text Encoders",
    "loras":                   "LoRAs",
    "controlnet":              "ControlNet",
    "upscale_models":          "Upscalers",
    "animatediff_models":      "AnimateDiff",
    "animatediff_motion_lora": "AnimateDiff",
    "style_models":            "Style Models",
    "clip_vision":             "Clip Vision",
    "clip":                    "CLIP",
    "embeddings":              "Embeddings",
}

MODEL_EXTS = {".safetensors", ".pth", ".pt", ".ckpt", ".bin"}

WORKFLOW_DIR = REPO / "workflows"


def scan_filesystem():
    """Return dict of {relative_path_str: size_bytes} for all model/workflow files."""
    found = {}

    models_root = REPO / "models"
    for dirpath, dirnames, filenames in models_root.walk() if hasattr(models_root, 'walk') else _walk(models_root):
        # Skip .git and hidden dirs
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fname in filenames:
            if Path(fname).suffix in MODEL_EXTS:
                full = Path(dirpath) / fname
                rel = str(full.relative_to(REPO))
                found[rel] = full.stat().st_size

    if WORKFLOW_DIR.exists():
        for f in WORKFLOW_DIR.glob("*.json"):
            rel = str(f.relative_to(REPO))
            found[rel] = f.stat().st_size

    return found


def _walk(path):
    """Fallback os.walk style for older Python."""
    import os
    for root, dirs, files in os.walk(path):
        yield root, dirs, files


def extract_indexed_files(content):
    """
    Extract all filenames mentioned in backtick table cells from INDEX.md.
    Returns set of filename stems (not full paths) that are currently indexed.
    """
    indexed = set()
    # Match `filename.ext` in table rows
    for m in re.finditer(r"`([^`]+\.(safetensors|pth|pt|ckpt|bin|json))`", content):
        indexed.add(m.group(1))
    return indexed


def remove_rows_for_deleted(content, filesystem_files):
    """Remove table rows whose filename no longer exists on disk."""
    fs_filenames = {Path(p).name for p in filesystem_files}
    lines = content.split("\n")
    result = []
    removed = []

    for line in lines:
        # Check if this is a table row containing a model filename
        m = re.search(r"`([^`]+\.(safetensors|pth|pt|ckpt|bin))`", line)
        if m and line.strip().startswith("|"):
            fname = Path(m.group(1)).name  # handle path-prefixed entries like `subdir/file.safetensors`
            if fname not in fs_filenames:
                removed.append(fname)
                continue  # drop the row
        result.append(line)

    if removed:
        print(f"  Removed {len(removed)} deleted entries: {', '.join(removed)}", file=sys.stderr)

    return "\n".join(result)


def format_size(size_bytes):
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f}G"
    elif size_bytes >= 1_048_576:
        return f"{size_bytes // 1_048_576}M"
    else:
        return f"{size_bytes // 1024}K"


def build_unindexed_section(new_files, catalog=None):
    """Build the ## Unindexed section content for new files.

    If catalog is provided (dict of {filename: yaml_entry}), known files are
    pre-filled with base, trigger, and source from models.yaml.
    """
    catalog = catalog or {}
    lines = [
        "",
        "---",
        "",
        "## Unindexed — needs annotation",
        "",
        "> Auto-detected by sync_index.py. Move each row to its proper section and fill in metadata.",
        "",
    ]

    # Group by model subdir
    by_dir = {}
    for rel_path, size in sorted(new_files.items()):
        p = Path(rel_path)
        parts = p.parts  # e.g. ('models', 'loras', 'foo.safetensors')
        if len(parts) >= 2 and parts[0] == "models":
            subdir = parts[1]
        elif parts[0] == "workflows":
            subdir = "workflows"
        else:
            subdir = "other"
        by_dir.setdefault(subdir, []).append((p.name, size, rel_path))

    for subdir, files in sorted(by_dir.items()):
        section = MODEL_DIRS.get(subdir, subdir)
        lines.append(f"### {section} (`{subdir}/`)")
        lines.append("")
        lines.append("| File | Size | Base | Trigger | Source | Notes |")
        lines.append("|---|---|---|---|---|---|")
        for fname, size, rel in sorted(files):
            entry = catalog.get(fname, {})
            base    = entry.get("base", "—")
            trigger = entry.get("trigger") or "—"
            source  = f"[source]({entry['source']})" if entry.get("source") else "—"
            notes   = entry.get("notes") or "TODO"
            lines.append(
                f"| `{fname}` | {format_size(size)} | {base} | {trigger} | {source} | {notes} |"
            )
        lines.append("")

    return "\n".join(lines)


def update_timestamp(content):
    today = date.today().isoformat()
    return re.sub(
        r"Last updated:.*",
        f"Last updated: {today}",
        content,
        count=1,
    )


def sync():
    if not INDEX.exists():
        print("INDEX.md not found", file=sys.stderr)
        sys.exit(1)

    content = INDEX.read_text()
    filesystem = scan_filesystem()
    catalog = load_yaml_catalog()

    # 1. Remove rows for deleted files
    content = remove_rows_for_deleted(content, filesystem)

    # 2. Strip existing Unindexed section (will rebuild it). Must happen
    #    BEFORE extracting indexed filenames, otherwise files parked in the
    #    Unindexed table count as "indexed" and silently vanish on this run
    #    instead of persisting until annotated into a real section.
    content = re.sub(
        r"\n---\n\n## Unindexed.*",
        "",
        content,
        flags=re.DOTALL,
    )

    # 3. Find files not yet indexed
    indexed_filenames = extract_indexed_files(content)
    fs_filenames_map = {Path(p).name: (p, s) for p, s in filesystem.items()}

    new_files = {}
    for fname, (rel, size) in fs_filenames_map.items():
        if fname not in indexed_filenames:
            new_files[rel] = size

    # 4. Update timestamp
    content = update_timestamp(content)

    # 5. Append new Unindexed section if needed
    if new_files:
        content = content.rstrip() + "\n" + build_unindexed_section(new_files, catalog) + "\n"
        print(f"  Added {len(new_files)} new files to Unindexed section", file=sys.stderr)
    else:
        print("  No new files to index", file=sys.stderr)

    INDEX.write_text(content)
    print(f"INDEX.md updated ({date.today().isoformat()})", file=sys.stderr)


if __name__ == "__main__":
    sync()
