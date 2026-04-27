# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Configuration, scripts, workflows, and model catalog for a local image generation stack. The actual tools (ComfyUI, A1111, comfyui-mcp-server) are cloned into gitignored subdirectories and managed separately. Only configs, scripts, workflows, and `models/MODELS.md` are tracked.

## Running the Stack

```bash
imggen          # start ComfyUI + MCP server, open browser
imggen stop     # kill both
imggen status   # check what's running
```

`imggen` is a bash function in `~/.bash_aliases.sh`. It:
1. Starts ComfyUI (port 8188) from `comfyui/.venv`
2. Waits for ComfyUI to be healthy
3. Starts comfyui-mcp-server (port 9000) from `comfyui-mcp-server/.venv`
4. Opens Firefox at `http://127.0.0.1:8188`

A1111 is independent: `cd automatic1111 && ./webui.sh` (port 7860).

## INDEX.md Auto-Sync

`INDEX.md` is kept current automatically:

- **Claude Code hook** — `scripts/sync_index.py` runs at the end of every Claude session (Stop hook in `.claude/settings.json`)
- **Filesystem watcher** — `scripts/watch_models.sh` uses `inotifywait` to fire the same script the moment a download finishes or a file is deleted; start it alongside the stack:

```bash
nohup bash scripts/watch_models.sh >> /tmp/watch_models.log 2>&1 &
```

`sync_index.py` behaviour:
- Removes table rows for files no longer on disk
- Appends new files to an `## Unindexed` section (filename + size, `TODO` for metadata)
- Never touches existing annotated rows
- Updates the `Last updated` timestamp

## Installing from Scratch

```bash
./scripts/install_comfyui.sh       # clone + venv + PyTorch cu121 + requirements
./scripts/install_a1111.sh         # clone + link webui-user.sh
./scripts/install_comfyui_mcp.sh   # clone + venv + mcp/requests/Pillow
```

## Architecture

**Shared model directory** — both ComfyUI and A1111 read from `models/`:
- `models/checkpoints/` — SDXL-based `.safetensors` (e.g. Illustrious XL, SVD)
- `models/diffusion_models/` — Flux and video transformers (Flux.1-dev, Flux.1-Kontext-dev, HunyuanVideo, WAN 2.2)
- `models/text_encoders/` — Flux encoders (T5-XXL fp8, CLIP-L) + HunyuanVideo/WAN encoders
- `models/vae/` — VAEs per model family
- `models/loras/` — Flux.1-dev LoRAs (anime, illustration, cartoon, graphic design, film/storyboard, film noir)
- `models/controlnet/` — Flux and SDXL ControlNet models
- `models/upscale_models/` — ESRGAN upscalers
- `models/animatediff_models/` — AnimateDiff motion module
- `models/animatediff_motion_lora/` — Camera motion LoRAs (zoom, pan, tilt)
- `models/MODELS.md` — download catalog with sources and install notes (not authoritative for installed state)

**Config wiring:**
- `configs/comfyui/extra_model_paths.yaml` → copied to `comfyui/extra_model_paths.yaml` by install script; tells ComfyUI to use the shared `models/` dir
- `configs/a1111/webui-user.sh` → copied to `automatic1111/webui-user.sh`; sets `--ckpt-dir`, `--lora-dir`, etc.

**MCP integration** — `.mcp.json` at repo root points Claude Code at the running MCP server (`http://127.0.0.1:9000/mcp`). The MCP server auto-discovers ComfyUI workflow JSON files from `workflows/` and exposes each as a tool. Drop a workflow JSON into `workflows/` and it becomes available after restarting the MCP server.

**Custom nodes required for some models:**
- XLabs ControlNets (`flux-depth-controlnet-v3`, `flux-canny-controlnet-v3`, union models) require the [x-flux-comfyui](https://github.com/XLabs-AI/x-flux-comfyui) custom node installed in `comfyui/custom_nodes/`
- HunyuanVideo requires [ComfyUI-HunyuanVideoWrapper](https://github.com/kijai/ComfyUI-HunyuanVideoWrapper)
- WAN 2.2 requires [ComfyUI-WAN-Wrapper](https://github.com/kijai/ComfyUI-WanWrapper)
- AnimateDiff requires [ComfyUI-AnimateDiff-Evolved](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved)

**`models.yaml`** — machine-readable model catalog used by `scripts/install_models.py`. Each entry has `url`, `dest`, `size`, `auth`, `base`, `purpose`, and `date`. Add new models here to make them installable via the script.

## Generating Images via MCP

Run `imggen status`; if down, run `imggen` (~30s for both ports healthy). Claude Code connects via `.mcp.json` once the stack is up.

Entry point: `run_workflow(workflow_id, overrides={...})`. `workflow_id` is the filename stem from `workflows/`. Override values must be real JSON types (int, float, str) — stringified numbers fail pydantic validation. Workflows without `PARAM_*` placeholders ignore overrides and run with baked-in defaults.

Tools:
- `run_workflow(workflow_id, overrides=None)`, `list_workflows`, `list_models`
- `get_defaults` / `set_defaults` — baseline image/audio/video settings
- `get_queue_status`, `get_job(prompt_id)`, `cancel_job(prompt_id)`
- `list_assets`, `get_asset_metadata(asset_id)`, `view_image(asset_id)`

Each workflow JSON is also auto-registered as a tool named after its filename.

**Adding a workflow:** export from ComfyUI as JSON, drop in `workflows/`, restart with `imggen stop && imggen`.

**Workflow parameters** (placeholder strings inside node inputs):
- `PARAM_PROMPT` — text prompt
- `PARAM_INT_<name>` — integer (e.g. `PARAM_INT_STEPS`)
- `PARAM_FLOAT_<name>` — float (e.g. `PARAM_FLOAT_CFG`)

See `INDEX.md` for installed models, trigger words, and LoRA weights.

## Capabilities

**Image generation**
- Text-to-image — Flux.1-dev (high quality), Illustrious XL (anime/illustration)
- Image-to-image — SDXL/Illustrious
- Inpainting / outpainting — Flux and SDXL
- In-context image editing — Flux.1-Kontext-dev (edit by text instruction)
- Style conditioning — Flux Redux (image prompt / style transfer)
- ControlNet — Canny, Depth, Pose for Flux; Pose for SDXL
- LoRA styling — anime, retro anime, illustration, cartoon, Disney, comic, Swiss design, Milton Glaser, graffiti logo, film storyboard, film noir, cinematic

**Video generation**
- Image-to-video — WAN 2.2 I2V (high/low noise variants), SVD-XT (25 frames)
- Text-to-video — HunyuanVideo 1.5 (720p FP8), AnimateDiff (loop-based, SD1.5)
- Camera motion control — AnimateDiff camera LoRAs: zoom in/out, pan left/right, tilt up/down

**Post-processing**
- Upscaling — 4x-UltraSharp (general), RealESRGAN x4plus (realistic), 4x-AnimeSharp (anime)

**Installed model inventory:** [`INDEX.md`](INDEX.md) — authoritative for on-disk state (sizes, trigger words, LoRA weights).

## LoRA Notes

Most LoRAs in `models/loras/` target **Flux.1-dev**. Exceptions: `Sketchy-Illustrious.safetensors` targets Illustrious XL; AnimateDiff camera LoRAs in `models/animatediff_motion_lora/` target SD1.5+AnimateDiff. See `INDEX.md` for per-LoRA trigger words and recommended weights.

## Downloading Models

Use `hf download` for HuggingFace (token at `~/.cache/huggingface/token`). Use `wget` with CivitAI API token (`$CIVITAI_API_KEY`) for CivitAI:

```bash
wget -O models/loras/name.safetensors \
  "https://civitai.com/api/download/models/{versionId}?token=${CIVITAI_API_KEY}"
```

Flux.1-dev is a gated model — requires accepting the license at huggingface.co/black-forest-labs/FLUX.1-dev before downloading.
