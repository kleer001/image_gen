#!/bin/bash
# Starts the ComfyUI MCP server.
# ComfyUI must already be running on port 8188.

REPO_ROOT="/media/menser/fauna/image_gen"
MCP_DIR="${REPO_ROOT}/comfyui-mcp-server"

export COMFYUI_URL="http://localhost:8188"
export COMFY_MCP_WORKFLOW_DIR="${REPO_ROOT}/workflows"
export COMFYUI_OUTPUT_ROOT="${REPO_ROOT}/outputs/comfyui"

cd "$MCP_DIR"
source .venv/bin/activate
python server.py
