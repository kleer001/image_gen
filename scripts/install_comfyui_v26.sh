#!/bin/bash
# Isolated ComfyUI v0.26.x for model families the production comfyui/ (v0.17.0)
# cannot load: Krea 2 Turbo, Bernini-R 1.3B, Depth Anything 3. Separate
# and pinned so a core-version bump can't break the production WAN/Hunyuan/Ovi
# nodes or the MCP contract. Reuses the shared models/ dir via extra_model_paths.yaml.
# Sets up the instance + custom nodes only; model weights are pulled separately
# (see models.yaml / radar/scope-isolated-v26-instance.md). See ENVIRONMENTS.md.
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${REPO_ROOT}/comfyui_v26"
PORT=8190
# Pinned ComfyUI tag. v0.26.0 is the floor that covers all four families (Krea 2
# partner nodes set the bar). Confirm the newest stable v0.26.x tag before running
# and bump if needed: https://github.com/comfyanonymous/ComfyUI/releases
COMFYUI_TAG="v0.26.2"

# Custom nodes (Krea 2 needs none — core-native in v0.26.0).
CUSTOM_NODES=(
    "https://github.com/city96/ComfyUI-GGUF"              # GGUF loaders (Bernini GGUF-encoder fallback)
    "https://github.com/neuregex/ComfyUI-BerniniR"        # Bernini-R 1.3B video editor
    "https://github.com/PozzettiAndrea/ComfyUI-DepthAnythingV3"  # depth preprocessor
)

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "comfyui_v26/ already cloned; fetching tags"
    git -C "$INSTALL_DIR" fetch --tags
else
    git clone https://github.com/comfyanonymous/ComfyUI "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
# Pin the engine version (do not track master — preserves isolation).
git checkout "$COMFYUI_TAG"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Match the proven stack: torch + cu121 (Ampere/sm_86 OK; runs fp8/int8 fine).
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# Reuse the shared models/ dir (Krea/Bernini/DA3 files land there).
sed "s|__REPO_ROOT__|${REPO_ROOT}|" "${REPO_ROOT}/configs/comfyui/extra_model_paths.yaml" > "${INSTALL_DIR}/extra_model_paths.yaml"

# Custom nodes into comfyui_v26/custom_nodes/, installing each one's requirements.
mkdir -p "${INSTALL_DIR}/custom_nodes"
cd "${INSTALL_DIR}/custom_nodes"
for repo in "${CUSTOM_NODES[@]}"; do
    name=$(basename "$repo")
    if [ -d "$name/.git" ]; then
        echo "  $name already present; pulling"
        git -C "$name" pull --ff-only
    else
        # Disable git-lfs filters: these node repos LFS-track example assets we
        # don't need (real weights come from models.yaml), and a missing git-lfs
        # binary otherwise stalls the checkout.
        git clone -c filter.lfs.smudge= -c filter.lfs.process= -c filter.lfs.required=false "$repo" "$name"
    fi
    if [ -f "$name/requirements.txt" ]; then
        pip install -r "$name/requirements.txt"
    fi
done

echo ""
echo "Isolated ComfyUI ${COMFYUI_TAG} installed at ${INSTALL_DIR}"
echo "Run: cd ${INSTALL_DIR} && .venv/bin/python main.py --listen --port ${PORT}"
echo "Next: pull weights per models.yaml / radar/scope-isolated-v26-instance.md"
echo "  (sm_86: use int8/GGUF/bf16 or fp8_scaled via dequant — NOT mxfp8/nvfp4)"
