#!/bin/bash
set -e

REPO_ROOT="/media/menser/fauna/image_gen"
INSTALL_DIR="${REPO_ROOT}/comfyui"

if [ -d "$INSTALL_DIR" ]; then
    echo "comfyui/ already exists, skipping clone"
else
    git clone https://github.com/comfyanonymous/ComfyUI "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

python3 -m venv .venv
source .venv/bin/activate

# PyTorch with CUDA 12.1 wheels (compatible with CUDA 12.0 driver)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

pip install -r requirements.txt

# Link shared model config
cp "${REPO_ROOT}/configs/comfyui/extra_model_paths.yaml" "${INSTALL_DIR}/extra_model_paths.yaml"

echo ""
echo "ComfyUI installed."
echo "Run: cd ${INSTALL_DIR} && source .venv/bin/activate && python main.py --listen --port 8188"
