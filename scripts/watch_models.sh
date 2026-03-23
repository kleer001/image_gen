#!/usr/bin/env bash
# watch_models.sh — inotifywait daemon for models/ and workflows/
#
# Fires sync_index.py whenever:
#   - A model/workflow file finishes downloading (close_write)
#   - A file is deleted (delete)
#   - A file is moved in or out (moved_to, moved_from)
#
# Usage:
#   bash scripts/watch_models.sh          # foreground (for debugging)
#   bash scripts/watch_models.sh &        # background daemon
#   nohup bash scripts/watch_models.sh &  # persistent background
#
# Typically started by `imggen` alongside ComfyUI.

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${REPO}/comfyui/.venv/bin/python3"
SYNC="${REPO}/scripts/sync_index.py"
PIDFILE="${REPO}/.watch_models.pid"

MODEL_EXTS=".*\.(safetensors|pth|pt|ckpt|bin|json)$"

echo "[watch_models] Starting. Watching models/ and workflows/"
echo "[watch_models] PID $$"
echo $$ > "${PIDFILE}"

# Debounce: avoid firing multiple times for the same burst of events
last_fired=0
debounce_secs=5

inotifywait -m -r \
  -e close_write,delete,moved_to,moved_from \
  --format '%T %e %w%f' \
  --timefmt '%H:%M:%S' \
  "${REPO}/models" "${REPO}/workflows" 2>/dev/null \
| while IFS= read -r line; do
    # Only react to model/workflow file events
    if echo "$line" | grep -qiE "${MODEL_EXTS}"; then
      now=$(date +%s)
      if (( now - last_fired >= debounce_secs )); then
        last_fired=$now
        echo "[watch_models $(date +%H:%M:%S)] $line"
        "${PYTHON}" "${SYNC}" 2>&1 | sed 's/^/  /'
      fi
    fi
  done

rm -f "${PIDFILE}"
