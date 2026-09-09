#!/bin/bash
# Isolated ComfyUI for MiniMax H3 — the 33B omni-modal video+audio model, which
# needs a core newer than the production comfyui/ (v0.17.0) and the v0.26 instance
# can load. Separate and pinned so a core bump can't break the production
# WAN/Hunyuan/Ovi nodes or the MCP contract. Reuses the shared models/ dir via
# extra_model_paths.yaml. Weights are pulled separately (see models.yaml).
# See ENVIRONMENTS.md.
set -e

REPO_ROOT="/media/menser/fauna/image_gen"
INSTALL_DIR="${REPO_ROOT}/comfyui_h3"
PORT=8191
# Pinned ComfyUI tag. v0.30.0 is the documented floor for MiniMax H3; v0.35.0 is
# the newest stable and carries the later H3 fixes.
COMFYUI_TAG="v0.35.0"

# H3 is core-native — no custom nodes required.

# Shallow clone straight at the pinned tag. The instance never tracks master, so
# the history is dead weight, and the full clone is large enough that it fails on
# a saturated link (GitHub resets the connection mid-pack). Retried — GitHub is
# flaky from this rig.
if [ ! -d "$INSTALL_DIR/.git" ]; then
    for attempt in 1 2 3; do
        echo "clone attempt ${attempt}/3"
        if git clone --depth 1 --branch "$COMFYUI_TAG" \
             https://github.com/comfyanonymous/ComfyUI "$INSTALL_DIR"; then
            break
        fi
        rm -rf "$INSTALL_DIR"
        sleep 20
    done
fi
[ -d "$INSTALL_DIR/.git" ] || { echo "clone failed after 3 attempts"; exit 1; }

cd "$INSTALL_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# cu130, NOT the cu121 the other instances use. The Comfy-Org H3 repack states:
# "For diffusion models prefer int8_convrot if you are able to use pytorch with
# cu130." int8_convrot is the only quant that fits this 24 GB sm_86 card without
# being dequantized to bf16 the way fp8_scaled is, so cu130 is a hard requirement.
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt

# Reuse the shared models/ dir.
cp "${REPO_ROOT}/configs/comfyui/extra_model_paths.yaml" "${INSTALL_DIR}/extra_model_paths.yaml"

echo ""
echo "Isolated ComfyUI ${COMFYUI_TAG} installed at ${INSTALL_DIR}"
echo "Run: cd ${INSTALL_DIR} && .venv/bin/python main.py --listen --port ${PORT} --disable-pinned-memory"
echo "  (--disable-pinned-memory is required: H3 otherwise page-locks most of"
echo "   system RAM and the OOM-killer fires)"
