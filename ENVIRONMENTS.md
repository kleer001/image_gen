# Generator Environments

This stack runs more than one image/video generator, in isolated installs. The
governing rule: **the production ComfyUI stays pinned and frozen; each model
family that needs a newer engine gets its own isolated, pinned environment**, and
all of them share the single `models/` directory. Only one heavy GPU job runs at
a time across every environment — the 24 GB RTX 3090 cannot co-load two large
transformers.

Two kinds of environment exist: **ComfyUI instances** (each its own clone + venv,
own port) and **plain diffusers venvs** (script-driven, no server/port).

## Ports

| Port | Environment |
|---|---|
| 8188 | production ComfyUI |
| 8189 | FLUX.2 (`comfyui_flux2`) |
| 8190 | v0.26 instance (`comfyui_v26`, planned) |
| 7860 | A1111 |
| 9000 | MCP server |

## Inventory

### Production ComfyUI — `comfyui/` · port 8188 · ComfyUI v0.17.0 (pinned)
The main stack. Runs everything the tracked `workflows/` use: Flux.1-dev,
Flux.1-Kontext, Illustrious/SDXL, WAN 2.2 I2V + VACE, HunyuanVideo, Ovi,
AnimateDiff, upscalers. Pinned at v0.17.0 on purpose — a core bump risks the
WAN/Hunyuan/Ovi custom nodes and the MCP contract, so newer-engine models go to a
separate instance instead.
- Install: `scripts/install_comfyui.sh`
- Run: `imggen` (starts this + MCP, opens Firefox); `imggen stop` / `imggen status`
- Drive: MCP server (port 9000) or the HTTP API (port 8188, see `API_USAGE.md`)

### MCP server — `comfyui-mcp-server/` · port 9000
Adds workflow auto-discovery, defaults, and an asset registry on top of the
production ComfyUI API. Only reachable when Claude Code starts in a dir whose
`.mcp.json` lists it.
- Install: `scripts/install_comfyui_mcp.sh`
- Run: started by `imggen`

### A1111 — `automatic1111/` · port 7860
Standalone AUTOMATIC1111 webui for SDXL, sharing the `models/` dir. Independent of
the ComfyUI stack.
- Install: `scripts/install_a1111.sh`
- Run: `cd automatic1111 && ./webui.sh`

### FLUX.2 instance — `comfyui_flux2/` · port 8189 · ComfyUI v0.24.0 (pinned)
Isolated ComfyUI for FLUX.2 Klein 9B — the production v0.17 cannot run FLUX.2.
FLUX.2 is core-native, so no custom nodes. Reuses `models/` via
`extra_model_paths.yaml`.
- Install: `scripts/install_comfyui_flux2.sh`
- Run: `cd comfyui_flux2 && .venv/bin/python main.py --listen --port 8189`
- Drivers: `scripts/flux2_klein.py`, `flux2_klein_edit.py`, `flux2_character_sheet.py`, `flux2_klein_compare.py`
- VRAM: Klein 9B fp8 ~9 GB, comfortable on 24 GB.

### Ideogram 4 env — `ideogram4_env/` · no port · diffusers venv
Not ComfyUI. A dedicated venv running Ideogram 4.0 (nf4) through diffusers
(`Ideogram4Pipeline`), driven by a script. nf4 build because the fp8 build will
not run on this sm_86 card.
- Model: `models/ideogram-4-nf4-diffusers/`
- Run: `ideogram4_env/.venv/bin/python scripts/ideogram4_t2i.py "prompt"` (or `@scene.json`)
- Strength: structured-JSON prompting (bbox layout + palette) and in-image text.

### v0.26 instance — `comfyui_v26/` · port 8190 · ComfyUI v0.26.2 (pinned)
Isolated ComfyUI for model families newer than v0.17 can load: Krea 2 Turbo,
Bernini-R 1.3B, Depth Anything 3. Details (install order, sm_86 quant paths,
custom nodes, VRAM rules) in `radar/scope-isolated-v26-instance.md`.
- Install: `scripts/install_comfyui_v26.sh`
- Run: `cd comfyui_v26 && .venv/bin/python main.py --listen --port 8190`
- Custom nodes: ComfyUI-GGUF, ComfyUI-BerniniR, ComfyUI-DepthAnythingV3
  (Krea 2 is core-native).

## GPU / coexistence

One heavy GPU job at a time across **all** environments — never run two large
transformers, or two instances' heavy jobs, concurrently on the single 24 GB
3090. Confirm `nvidia-smi` is near-empty before starting WAN-class jobs.
sm_86 (Ampere) caveat: the GPU has no fp8 *compute* — comfy dequantizes fp8
weights to bf16 (they load and run, no fp8 speedup). Genuinely incompatible are
the Blackwell-only formats (mxfp8, nvfp4). Prefer int8 / GGUF / bf16 / fp8.

## Adding an environment

1. Mirror `scripts/install_comfyui_flux2.sh` — clone, venv, **pinned** version,
   reuse `configs/comfyui/extra_model_paths.yaml`; pick the next free port.
2. Add `/<dir>/` to `.gitignore` (these installs are not tracked).
3. Add a row here and to the map in `CLAUDE.md`.

The `SessionStart` drift check (`scripts/check_envs_documented.py`) flags any
top-level generator directory not named in this file.
