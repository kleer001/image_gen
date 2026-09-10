#!/bin/bash
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${REPO_ROOT}/comfyui"

if [ -d "$INSTALL_DIR" ]; then
    echo "comfyui/ already exists, skipping clone"
else
    git clone https://github.com/comfyanonymous/ComfyUI "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

python3 -m venv .venv
source .venv/bin/activate

# PyTorch — CUDA 12.1 on Linux/Windows, MPS on macOS
if [[ "$(uname)" == "Darwin" ]]; then
    pip install torch torchvision torchaudio
else
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
fi

pip install -r requirements.txt

# Link shared model config
sed "s|__REPO_ROOT__|${REPO_ROOT}|" "${REPO_ROOT}/configs/comfyui/extra_model_paths.yaml" > "${INSTALL_DIR}/extra_model_paths.yaml"

# Custom nodes
NODES_DIR="${INSTALL_DIR}/custom_nodes"
install_node() {
    local repo="$1"
    local name=$(basename "$repo")
    if [ -d "${NODES_DIR}/${name}" ]; then
        echo "${name} already installed, skipping"
    else
        git clone "$repo" "${NODES_DIR}/${name}"
        if [ -f "${NODES_DIR}/${name}/requirements.txt" ]; then
            pip install -r "${NODES_DIR}/${name}/requirements.txt"
        fi
    fi
}

install_node https://github.com/XLabs-AI/x-flux-comfyui
install_node https://github.com/kijai/ComfyUI-HunyuanVideoWrapper
install_node https://github.com/kijai/ComfyUI-WanVideoWrapper
install_node https://github.com/kijai/ComfyUI-KJNodes
install_node https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved
install_node https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
install_node https://github.com/Fannovel16/comfyui_controlnet_aux
install_node https://github.com/Fannovel16/ComfyUI-Frame-Interpolation
install_node https://github.com/AIFSH/ComfyUI_StoryDiffusion

echo ""
echo "ComfyUI installed."
echo "Run: cd ${INSTALL_DIR} && source .venv/bin/activate && python main.py --listen --port 8188"
