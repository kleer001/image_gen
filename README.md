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

**Linux / macOS:**
```bash
git clone https://github.com/kleer001/image_gen.git && cd image_gen && bash scripts/install_comfyui.sh && bash scripts/install_comfyui_mcp.sh && python3 scripts/install_models.py
```

**Windows — open PowerShell as Administrator, then paste into the WSL terminal it opens:**
```powershell
wsl --install
```
```bash
git clone https://github.com/kleer001/image_gen.git && cd image_gen && bash scripts/install_comfyui.sh && bash scripts/install_comfyui_mcp.sh && python3 scripts/install_models.py
```

Clones and wires up ComfyUI + the MCP server, then pulls the full model library (~200GB). Once done, `imggen` starts everything.

<details>
<summary><strong>Manual setup (step by step)</strong></summary>

#### 1. Clone the repo

```bash
git clone https://github.com/kleer001/image_gen.git
cd image_gen
```

#### 2. Install ComfyUI and custom nodes

```bash
bash scripts/install_comfyui.sh
```

Creates a venv, installs PyTorch (CUDA on Linux/Windows, MPS on macOS), installs ComfyUI requirements, and clones all required custom nodes (AnimateDiff, VideoHelperSuite, HunyuanVideoWrapper, WanVideoWrapper, XLabs Flux ControlNet, ControlNet-Aux, Frame-Interpolation, StoryDiffusion, KJNodes).

#### 3. Install the MCP server

```bash
bash scripts/install_comfyui_mcp.sh
```

Clones comfyui-mcp-server, creates its venv, and installs dependencies.

#### 4. Download models

```bash
python3 scripts/install_models.py              # full library (~200GB)
python3 scripts/install_models.py --check      # preview what's missing + disk needed
python3 scripts/install_models.py --skip wan   # skip WAN 2.2 (saves 110GB)
```

Downloads checkpoints, Flux models, video models, LoRAs, ControlNets, VAEs, and upscalers from HuggingFace and CivitAI. Resumes interrupted downloads automatically.

</details>

## Running

```bash
imggen          # start ComfyUI + MCP server, open browser
imggen stop     # kill both
imggen status   # check what's running

# A1111 (independent)
cd automatic1111 && ./webui.sh
```


## GitHub Backup

Only configs, scripts, workflows, and this README are pushed.
Models and outputs stay local only.
