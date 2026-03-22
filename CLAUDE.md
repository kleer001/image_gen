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

## Installing from Scratch

```bash
./scripts/install_comfyui.sh       # clone + venv + PyTorch cu121 + requirements
./scripts/install_a1111.sh         # clone + link webui-user.sh
./scripts/install_comfyui_mcp.sh   # clone + venv + mcp/requests/Pillow
```

## Architecture

**Shared model directory** — both ComfyUI and A1111 read from `models/`:
- `models/checkpoints/` — SDXL-based `.safetensors` (e.g. Illustrious XL)
- `models/diffusion_models/` — Flux transformer (`flux1-dev.safetensors`)
- `models/text_encoders/` — Flux text encoders (T5-XXL fp8, CLIP-L)
- `models/vae/` — VAEs (`sdxl.vae.safetensors`, `flux-ae.safetensors`)
- `models/loras/` — 13 Flux.1-dev LoRAs (anime, illustration, graphic design, logo)
- `models/MODELS.md` — download catalog with sources, trigger words, weights

**Config wiring:**
- `configs/comfyui/extra_model_paths.yaml` → copied to `comfyui/extra_model_paths.yaml` by install script; tells ComfyUI to use the shared `models/` dir
- `configs/a1111/webui-user.sh` → copied to `automatic1111/webui-user.sh`; sets `--ckpt-dir`, `--lora-dir`, etc.

**MCP integration** — `.mcp.json` at repo root points Claude Code at the running MCP server (`http://127.0.0.1:9000/mcp`). The MCP server auto-discovers ComfyUI workflow JSON files from `workflows/` and exposes each as a tool. Drop a workflow JSON into `workflows/` and it becomes available after restarting the MCP server.

## Using the ComfyUI MCP

**Prerequisite:** the stack must be running (`imggen`). Claude Code connects automatically via `.mcp.json` — no manual config needed.

Key tools exposed:
- `generate_image` — text-to-image with the default workflow
- `run_workflow <name>` — run any workflow JSON from `workflows/` by filename (without `.json`)
- `list_workflows` — see all available workflows
- `list_models` — see models ComfyUI can see
- `get_queue_status` — check if jobs are pending/running
- `view_image` — display a generated image

**Adding a workflow:** export any ComfyUI workflow as JSON (Save → Export), drop it in `workflows/`, restart the MCP server (`imggen stop && imggen`). It becomes a callable tool named after the filename.

**Workflow parameters:** to make a workflow accept dynamic inputs, add placeholder strings inside the JSON node inputs:
- `PARAM_PROMPT` — text prompt
- `PARAM_INT_<name>` — integer (e.g. `PARAM_INT_STEPS`)
- `PARAM_FLOAT_<name>` — float (e.g. `PARAM_FLOAT_CFG`)

## Installed Models

| Model | Location | Notes |
|---|---|---|
| Illustrious XL v0.1 | `checkpoints/` | SDXL-based, anime/illustration |
| flux1-dev | `diffusion_models/` | 23GB bf16; load at fp8 in ComfyUI |
| flux-ae | `vae/` | Flux VAE |
| sdxl.vae.safetensors | `vae/` | SDXL VAE (fp16-fix) |
| t5xxl_fp8_e4m3fn | `text_encoders/` | Required for Flux |
| clip_l | `text_encoders/` | Required for Flux |

## LoRA Notes

All 13 LoRAs in `models/loras/` are trained for **Flux.1-dev** only (not SDXL/Illustrious). To use with Illustrious XL, LoRAs must be specifically tagged for Illustrious or SDXL. See `models/MODELS.md` for trigger words and recommended weights.

## Downloading Models

Use `hf download` for HuggingFace (token at `~/.cache/huggingface/token`). Use `wget` with CivitAI API token (`$CIVITAI_API_KEY`) for CivitAI:

```bash
wget -O models/loras/name.safetensors \
  "https://civitai.com/api/download/models/{versionId}?token=${CIVITAI_API_KEY}"
```

Flux.1-dev is a gated model — requires accepting the license at huggingface.co/black-forest-labs/FLUX.1-dev before downloading.
