#!/bin/bash
# Start, stop and check the image_gen stack: ComfyUI on :8188 and the MCP
# server on :9000. Logs land in outputs/.
#
#   scripts/imggen.sh [start|stop|status]      (default: start)
#
# For a bare `imggen` command, add an alias to your shell rc:
#   alias imggen='/path/to/image_gen/scripts/imggen.sh'
#
# The browser opened on start is $BROWSER, falling back to xdg-open.
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="$ROOT/outputs"
CMD="${1:-start}"

case "$CMD" in
    start)
        if fuser 8188/tcp > /dev/null 2>&1; then
            echo "[imggen] ComfyUI already running on :8188"
        else
            echo "[imggen] Starting ComfyUI..."
            nohup bash -c "
                cd '$ROOT/comfyui'
                source .venv/bin/activate
                python main.py --listen --port 8188
            " > "$LOGS/comfyui.log" 2>&1 &
            echo "         PID $! -- tail -f $LOGS/comfyui.log"
            echo "[imggen] Waiting for ComfyUI to be ready..."
            until curl -sf http://localhost:8188 > /dev/null 2>&1; do sleep 2; done
            echo "         http://localhost:8188  (ready)"
        fi

        if fuser 9000/tcp > /dev/null 2>&1; then
            echo "[imggen] MCP server already running on :9000"
        else
            echo "[imggen] Starting MCP server..."
            nohup bash -c "
                cd '$ROOT/comfyui-mcp-server'
                export COMFYUI_URL=http://localhost:8188
                export COMFY_MCP_WORKFLOW_DIR='$ROOT/workflows'
                export COMFYUI_OUTPUT_ROOT='$ROOT/outputs/comfyui'
                source .venv/bin/activate
                python server.py
            " > "$LOGS/comfyui-mcp.log" 2>&1 &
            echo "         PID $! -- tail -f $LOGS/comfyui-mcp.log"
            echo "         http://localhost:9000/mcp  (ready)"
        fi

        "${BROWSER:-xdg-open}" http://127.0.0.1:8188/ > /dev/null 2>&1 &
        ;;
    stop)
        fuser -k 8188/tcp > /dev/null 2>&1 && echo "[imggen] ComfyUI stopped"    || echo "[imggen] ComfyUI wasn't running"
        fuser -k 9000/tcp > /dev/null 2>&1 && echo "[imggen] MCP server stopped" || echo "[imggen] MCP server wasn't running"
        ;;
    status)
        fuser 8188/tcp > /dev/null 2>&1 && echo "[imggen] ComfyUI:     running" || echo "[imggen] ComfyUI:     stopped"
        fuser 9000/tcp > /dev/null 2>&1 && echo "[imggen] MCP server:  running" || echo "[imggen] MCP server:  stopped"
        ;;
    *)
        echo "Usage: imggen [start|stop|status]"
        exit 1
        ;;
esac
