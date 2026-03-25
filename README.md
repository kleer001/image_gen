# image_gen

![banner](assets/banner.png)

A production-grade local AI image and video generation stack running on a single RTX 3090. Covers the full range from quick SDXL sketches to state-of-the-art Flux edits, impressionist LoRA styling, and 14B-parameter video generation — all callable by a Claude Code agent via MCP without touching a UI.

**GPU:** RTX 3090 (24GB) &nbsp;|&nbsp; **ComfyUI:** `localhost:8188` &nbsp;|&nbsp; **MCP:** `localhost:9000`

### What it can do

**Image generation**
- Text-to-image — Flux.1-dev (state-of-the-art quality), Illustrious XL (anime/illustration)
- In-context editing — Flux.1-Kontext-dev: edit any image by text instruction ("make it raining", "swap the jacket for a coat")
- Style transfer — Flux Redux (image-prompt conditioning)
- ControlNet — Canny, Depth, Pose for Flux (XLabs v3) and SDXL
- LoRA styling — 15+ styles: anime, retro anime, illustration, cartoon, Disney, comic, Swiss design, Milton Glaser, graffiti, film storyboard, film noir, cinematic

**Video generation**
- Image-to-video — WAN 2.2 I2V 14B (dual high/low noise expert), SVD-XT (25 frames)
- Text-to-video — HunyuanVideo 1.5 (720p FP8), AnimateDiff (SD1.5 loop)
- Camera motion — AnimateDiff LoRAs: zoom in/out, pan left/right, tilt up/down

**Post-processing**
- Upscaling — 4x-UltraSharp, RealESRGAN x4plus, 4x-AnimeSharp

### Claude Code integration

`.mcp.json` wires Claude Code directly to the running MCP server. Every workflow JSON in `workflows/` becomes a callable tool. Claude can generate, iterate, and upscale without leaving the terminal:

```bash
imggen          # start everything, open browser
imggen stop
imggen status
```

See [`INDEX.md`](INDEX.md) for the full installed model inventory (auto-synced) and [`CLAUDE.md`](CLAUDE.md) for agent operating instructions.

---

## Setup

**Prerequisites:** HuggingFace token at `~/.cache/huggingface/token` (needed for Flux.1-dev), CivitAI API key in `$CIVITAI_API_KEY`.

**Linux (CUDA)**
```bash
git clone https://github.com/kleer001/image_gen.git && cd image_gen && \
  bash scripts/install_comfyui.sh && \
  bash scripts/install_comfyui_mcp.sh && \
  python3 scripts/install_models.py
```

**macOS (Apple Silicon / Intel — MPS)**
```bash
git clone https://github.com/kleer001/image_gen.git && cd image_gen && \
  bash scripts/install_comfyui.sh && \
  bash scripts/install_comfyui_mcp.sh && \
  python3 scripts/install_models.py
```

**Windows (WSL2 + CUDA recommended)**
```powershell
wsl --install
```
Then open the WSL terminal and run the Linux one-liner above.

All three clone and wire up ComfyUI + the MCP server, then pull the full model library (~200GB, takes a while). Once done, `imggen` starts everything.

## Running

```bash
imggen          # start ComfyUI + MCP server, open browser
imggen stop     # kill both
imggen status   # check what's running

# A1111 (independent)
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
