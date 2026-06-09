#!/bin/bash
# Isolated ComfyUI for FLUX.2 Klein experiments — separate from the production
# comfyui/ (v0.17.0) so a core-version bump can't break the WAN/Hunyuan/Ovi nodes.
# Reuses the shared models/ dir via extra_model_paths.yaml. No video custom nodes:
# FLUX.2 is core-native, so this stays lean.
set -e

REPO_ROOT="/media/menser/fauna/image_gen"
INSTALL_DIR="${REPO_ROOT}/comfyui_flux2"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "comfyui_flux2/ already cloned; pulling latest"
    git -C "$INSTALL_DIR" pull --ff-only
else
    git clone https://github.com/comfyanonymous/ComfyUI "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Match the proven production stack: torch 2.5.1 + cu121 (runs Flux/WAN fp8 fine).
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# Reuse the shared models/ dir (Klein files land there).
cp "${REPO_ROOT}/configs/comfyui/extra_model_paths.yaml" "${INSTALL_DIR}/extra_model_paths.yaml"

echo ""
echo "Isolated FLUX.2 ComfyUI installed at ${INSTALL_DIR}"
echo "Run: cd ${INSTALL_DIR} && .venv/bin/python main.py --listen --port 8189"
