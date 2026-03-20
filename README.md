# image_gen

Local image generation setup. Both ComfyUI and A1111 share a single `models/` directory.

**GPU:** RTX 3090 (24GB)
**Ports:** ComfyUI → 8188, A1111 → 7860

---

## Setup

```bash
chmod +x scripts/install_comfyui.sh scripts/install_a1111.sh
./scripts/install_comfyui.sh
./scripts/install_a1111.sh
```

## Running

```bash
# ComfyUI
cd comfyui && source .venv/bin/activate && python main.py --listen --port 8188

# A1111
cd automatic1111 && ./webui.sh
```

## Directory Structure

```
models/         shared model weights (gitignored, see models/MODELS.md for catalog)
configs/        tool configs (tracked)
scripts/        install scripts (tracked)
workflows/      ComfyUI workflow JSONs (tracked)
outputs/        generated images (gitignored)
comfyui/        tool install (gitignored)
automatic1111/  tool install (gitignored)
```

## Adding Models

Drop `.safetensors` files into the appropriate subdirectory under `models/`.
Both tools will pick them up on next launch (or refresh in the UI).
See `models/MODELS.md` for the curated download list.

## Config Changes

- **ComfyUI model paths:** `configs/comfyui/extra_model_paths.yaml`
  - After editing, copy to `comfyui/extra_model_paths.yaml`
- **A1111 launch args:** `configs/a1111/webui-user.sh`
  - After editing, copy to `automatic1111/webui-user.sh`

## GitHub Backup

Only configs, scripts, workflows, and this README are pushed.
Models and outputs stay local only.
