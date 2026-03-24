#!/usr/bin/env python3
"""
install_models.py — Bootstrap the full image_gen model library from scratch.

Checks what's missing, verifies disk space, then downloads everything
with resume support, smart ETAs, and minimal output.

Usage:
    python3 scripts/install_models.py              # full install
    python3 scripts/install_models.py --check      # show missing + disk needed, exit
    python3 scripts/install_models.py --only loras # only download a section
    python3 scripts/install_models.py --skip wan   # skip a section (e.g. 120GB WAN)
    python3 scripts/install_models.py --update-cv  # refresh CivitAI versionIds in models.yaml

Requires:
    PyYAML                    pip install pyyaml
    $CIVITAI_API_KEY  or  ~/.civitai_token
    ~/.cache/huggingface/token  (or $HF_TOKEN)

Note: --update-cv rewrites models.yaml without preserving comments.
"""

import os, sys, time, subprocess, argparse, shutil, json, urllib.request
from datetime import date
from pathlib import Path

REPO   = Path(__file__).parent.parent
MODELS = REPO / "models"
LOG    = REPO / "install_models.log"
YAML   = REPO / "models.yaml"

HF_BASE = "https://huggingface.co"
CV_BASE = "https://civitai.com/api/download/models"
CV_API  = "https://civitai.com/api/v1/models"

# ─── FORMAT HELPERS ──────────────────────────────────────────────────────────

def fmt_size(b):
    if b >= 1_073_741_824: return f"{b/1_073_741_824:.1f}G"
    if b >= 1_048_576:     return f"{b/1_048_576:.0f}M"
    return f"{b/1024:.0f}K"

def fmt_eta(secs):
    if secs < 0:    return "?"
    if secs < 60:   return f"{secs:.0f}s"
    if secs < 3600: return f"{secs/60:.0f}m"
    h, m = int(secs // 3600), int((secs % 3600) // 60)
    return f"{h}h {m}m"

def fmt_rate(bps):
    if bps >= 1_048_576: return f"{bps/1_048_576:.1f} MB/s"
    return f"{bps/1024:.0f} KB/s"

# ─── CATALOG ─────────────────────────────────────────────────────────────────

def _load_yaml():
    try:
        import yaml
    except ImportError:
        print("PyYAML required: pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    if not YAML.exists():
        print(f"models.yaml not found at {YAML}", file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load(YAML.read_text())


def _expand_shards(raw, hf_token):
    """Expand a type:shards entry into N individual download entries."""
    sizes = raw["sizes"]
    n = len(sizes)
    hf_subdir = raw.get("hf_subdir", "")
    entries = []
    for i, sz in enumerate(sizes, 1):
        fname = raw["tmpl"].format(i=i, n=n)
        repo_path = f"{hf_subdir}/{fname}" if hf_subdir else fname
        entries.append({
            "section": raw["section"],
            "name":    f"{raw['name']} {i}/{n}",
            "dest":    f"{raw['dest_dir']}/{fname}",
            "url":     f"{HF_BASE}/{raw['hf_repo']}/resolve/main/{repo_path}",
            "size":    sz,
            "auth":    hf_token if raw.get("auth") == "hf" else "",
        })
    return entries


def _resolve_entry(raw, hf_token, cv_token):
    """Convert a single YAML entry to a download dict."""
    auth = raw.get("auth", "none")
    if "civitai_version" in raw:
        token_suffix = f"?token={cv_token}" if cv_token else ""
        url = f"{CV_BASE}/{raw['civitai_version']}{token_suffix}"
    else:
        url = raw["url"]
    return {
        "section": raw["section"],
        "name":    raw["name"],
        "dest":    raw["dest"],
        "url":     url,
        "size":    raw.get("size", 0),
        "auth":    hf_token if auth == "hf" else "",
    }


def load_catalog(hf_token, cv_token):
    """Load models.yaml and return the full ordered list of download entries."""
    raw_entries = _load_yaml()
    items = []
    for raw in raw_entries:
        if raw.get("type") == "shards":
            items.extend(_expand_shards(raw, hf_token))
        else:
            items.append(_resolve_entry(raw, hf_token, cv_token))
    return items

# ─── CIVITAI UPDATE ───────────────────────────────────────────────────────────

def update_civitai(cv_token):
    """
    Hit the CivitAI API for each entry with civitai_model and patch civitai_version
    in models.yaml to the latest available version.

    Rewrites models.yaml without preserving YAML comments.
    """
    import yaml

    entries = _load_yaml()
    today = date.today().isoformat()
    updated = 0

    print(f"\n  Checking CivitAI versions...\n")
    for entry in entries:
        model_id = entry.get("civitai_model")
        if not model_id:
            continue

        url = f"{CV_API}/{model_id}"
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {cv_token}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"  ✗  {entry['name']}: {e}")
            continue

        versions = data.get("modelVersions", [])
        if not versions:
            print(f"  ✗  {entry['name']}: no versions in API response")
            continue

        latest_vid = versions[0]["id"]
        old_vid = entry.get("civitai_version")

        if old_vid != latest_vid:
            entry["civitai_version"] = latest_vid
            entry["date"] = today
            updated += 1
            print(f"  ↑  {entry['name']}: {old_vid} → {latest_vid}")
        else:
            print(f"  ✓  {entry['name']}: up to date (vid={latest_vid})")

    if updated:
        YAML.write_text(
            yaml.dump(entries, allow_unicode=True, sort_keys=False,
                      default_flow_style=False)
        )
        print(f"\n  Updated {updated} entr{'y' if updated == 1 else 'ies'} in models.yaml\n")
    else:
        print(f"\n  All CivitAI entries are up to date.\n")

# ─── DOWNLOAD ENGINE ──────────────────────────────────────────────────────────

def _file_size(path):
    try: return path.stat().st_size
    except FileNotFoundError: return 0


def _is_complete(entry):
    dest = MODELS / entry["dest"]
    if not dest.exists(): return False
    sz = dest.stat().st_size
    return sz > 0 if entry["size"] == 0 else sz >= entry["size"]


def _wget_cmd(url, dest, auth):
    cmd = ["wget", "-c", "-q", "--show-progress", "-O", str(dest), url]
    if auth:
        cmd.insert(3, f"--header=Authorization: Bearer {auth}")
    return cmd


def _poll_progress(proc, dest, entry, stats, start_bytes, t0):
    """Drive proc to completion, printing progress every 30s."""
    last_report = t0
    while proc.poll() is None:
        time.sleep(10)
        now = time.time()
        if now - last_report < 30:
            continue
        cur, elapsed = _file_size(dest), now - t0
        delta = cur - start_bytes
        if elapsed > 0 and delta > 0:
            rate = delta / elapsed
            expected = entry["size"]
            remaining = max(0, expected - cur) if expected > 0 else 0
            eta = fmt_eta(remaining / rate) if remaining > 0 else "?"
            pct = f"{cur/expected*100:.0f}%" if expected > 0 else fmt_size(cur)
            print(f"       {pct}  {fmt_rate(rate)}  ETA {eta}  "
                  f"[overall: {fmt_size(stats['done'])}/{fmt_size(stats['total'])}  "
                  f"~{fmt_eta(stats['eta']())}]")
        last_report = now
    return time.time() - t0


def download(entry, idx, total, stats):
    dest = MODELS / entry["dest"]
    if _is_complete(entry):
        return "skip"

    expected = entry["size"]
    print(f"  ↓  [{idx:2d}/{total}]  {entry['name']}"
          + (f" ({fmt_size(expected)})" if expected > 0 else ""))

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = _wget_cmd(entry["url"], dest, entry.get("auth"))

    for attempt in range(1, 4):
        start_bytes = _file_size(dest)
        proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
        elapsed = _poll_progress(proc, dest, entry, stats, start_bytes, time.time())

        if _is_complete(entry):
            final = _file_size(dest)
            rate = (final - start_bytes) / elapsed if elapsed > 0 else 0
            print(f"       ✓  {fmt_size(final)}  {fmt_eta(elapsed)}  {fmt_rate(rate)}")
            return "ok"

        if attempt < 3:
            print(f"       ✗  attempt {attempt} failed, retrying in 5s...")
            time.sleep(5)

    print(f"       ✗  FAILED (see {LOG.name})")
    with open(LOG, "a") as f:
        f.write(f"FAILED after 3 attempts: {entry['name']} → {dest}\n"
                f"  url: {entry['url']}\n\n")
    return "fail"

# ─── DISK CHECK ──────────────────────────────────────────────────────────────

def check_disk(needed_bytes):
    free = shutil.disk_usage(MODELS).free
    if free < needed_bytes * 1.05:
        print(f"\n  ✗  Insufficient disk space.")
        print(f"     Needed:    {fmt_size(needed_bytes)}")
        print(f"     Available: {fmt_size(free)}")
        sys.exit(1)
    print(f"  Disk: {fmt_size(free)} free, {fmt_size(needed_bytes)} needed — OK")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def _get_token(env_var, path):
    val = os.environ.get(env_var)
    if val: return val
    p = Path(path).expanduser()
    return p.read_text().strip() if p.exists() else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", "--dry-run", action="store_true",
                        help="Show what's missing and disk needed, then exit")
    parser.add_argument("--only", metavar="SECTION",
                        help="Only download this section (e.g. loras, wan, flux)")
    parser.add_argument("--skip", metavar="SECTION",
                        help="Skip this section")
    parser.add_argument("--update-cv", action="store_true",
                        help="Refresh CivitAI versionIds in models.yaml then exit")
    args = parser.parse_args()

    hf_token = _get_token("HF_TOKEN", "~/.cache/huggingface/token")
    cv_token = _get_token("CIVITAI_API_KEY", "~/.civitai_token")

    if args.update_cv:
        if not cv_token:
            print("  ✗  No CivitAI token. Set CIVITAI_API_KEY or ~/.civitai_token")
            sys.exit(1)
        update_civitai(cv_token)
        return

    if not hf_token:
        print("  ⚠  No HuggingFace token. Set HF_TOKEN or ~/.cache/huggingface/token")
    if not cv_token:
        print("  ⚠  No CivitAI token. Set CIVITAI_API_KEY or ~/.civitai_token"
              " — CivitAI downloads will fail.")

    items = load_catalog(hf_token, cv_token)
    all_sections = sorted({i["section"] for i in items})

    if args.only:
        items = [i for i in items if i["section"] == args.only]
        if not items:
            print(f"Unknown section '{args.only}'. Valid: {all_sections}")
            sys.exit(1)
    if args.skip:
        items = [i for i in items if i["section"] != args.skip]

    missing = [i for i in items if not _is_complete(i)]
    needed  = sum(i["size"] for i in missing if i["size"] > 0)

    print(f"\n  image_gen model installer")
    print(f"  {'─'*52}")
    print(f"  Total catalog : {len(items)} files")
    print(f"  Already done  : {len(items) - len(missing)} files")
    print(f"  To download   : {len(missing)} files  (~{fmt_size(needed)})")

    if not missing:
        print("\n  Everything is already installed.\n")
        return

    print()
    for sec in dict.fromkeys(i["section"] for i in missing):
        sec_items = [i for i in missing if i["section"] == sec]
        sz = sum(i["size"] for i in sec_items if i["size"] > 0)
        print(f"  {sec:<16} {len(sec_items):2d} files  {fmt_size(sz)}")
    print()

    check_disk(needed)

    if args.check:
        return

    print()
    t0 = time.time()
    stats = {"done": 0, "total": needed, "eta": None}

    def overall_eta():
        elapsed = time.time() - t0
        if elapsed < 10 or stats["done"] == 0:
            return -1
        rate = stats["done"] / elapsed
        remaining = sum(max(0, e["size"] - _file_size(MODELS / e["dest"]))
                        for e in missing if e["size"] > 0)
        return remaining / rate if rate > 0 else -1

    stats["eta"] = overall_eta

    ok = fail = skip = 0
    for idx, entry in enumerate(missing, 1):
        before = _file_size(MODELS / entry["dest"])
        result = download(entry, idx, len(missing), stats)
        stats["done"] += max(0, _file_size(MODELS / entry["dest"]) - before)
        if result == "ok":     ok += 1
        elif result == "fail": fail += 1
        elif result == "skip": skip += 1

    print(f"\n  {'─'*52}")
    print(f"  Done: {ok}  Failed: {fail}  Skipped: {skip}")
    if fail:
        print(f"  See {LOG} for details on failures.")
    print()


if __name__ == "__main__":
    main()
