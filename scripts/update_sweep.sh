#!/usr/bin/env bash
# update_sweep.sh — run the weekly update sweep unattended.
#
# Drives a headless Claude Code instance to read UPDATE.html and perform the
# update sweep (digest current state -> sweep models/LoRAs/workflows/nodes ->
# write a dated digest under radar/). Report-only: the sweep never installs.
#
# Install as a weekly cron on the rig, e.g.:
#   0 9 * * 1  /path/to/image_gen/scripts/update_sweep.sh
# (Mondays at 09:00). Logs to /tmp/update_sweep.log.
#
# Requires the `claude` CLI on PATH and a logged-in session on the box.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="/tmp/update_sweep.log"

cd "$REPO_DIR"

echo "=== update sweep $(date -Is) ===" >>"$LOG"
claude -p "Read UPDATE.html at the repo root and perform the weekly update sweep: \
digest the current repo state, sweep for state-of-the-art models, LoRAs, and workflows, \
then write the dated digest under radar/. Report only — do not download or install anything." \
  >>"$LOG" 2>&1

echo "=== done $(date -Is) ===" >>"$LOG"
