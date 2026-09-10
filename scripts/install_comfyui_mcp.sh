#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${REPO_ROOT}/comfyui-mcp-server"

if [ -d "$INSTALL_DIR" ]; then
    echo "comfyui-mcp-server/ already exists, skipping clone"
else
    git clone https://github.com/joenorton/comfyui-mcp-server "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo ""
echo "ComfyUI MCP server installed."
echo "Run: ./scripts/start_comfyui_mcp.sh"
