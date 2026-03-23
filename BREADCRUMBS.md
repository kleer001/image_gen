# BREADCRUMBS.md

Directives for Claude Code (MCP-driven) operating in this repo.
This is a general-purpose image generation stack. It currently serves as one of the production engines for **RΞΡLΙCΔ**, a 10-minute AI short film — but the stack has its own identity and should remain coherent and useful independent of any single project.

**Hardware:** RTX 3090, 24GB VRAM
**Stack:** `imggen` → ComfyUI (8188) + MCP server (9000)

---

## RΞΡLΙCΔ — Active Client Project

**Project root:** `/home/menser/Dropbox/ART/RΞΡLΙCΔ/`
**GitHub:** `https://github.com/kleer001/REPLIKA` (private)
**Aesthetic:** Psychological drama — brutalist architecture, chiaroscuro low-key lighting, atmospheric haze, anamorphic depth, existentialist pacing.

---

### RΞΡLΙCΔ Project Layout

Production output lives in:

```
/home/menser/Dropbox/ART/RΞΡLΙCΔ/
├── prod/scenes/          ← generated frames and approved shots land here
├── pipeline/comfy/workflows/   ← film-specific workflows live here
│   ├── img/              ← concept art, character sheets, location studies
│   └── vid/              ← video generation workflows
└── pipeline/comfy/prompts/     ← prompt templates per character/location/scene
```

When generating for RΞΡLΙCΔ, write outputs to the project's `prod/scenes/scNNN_*/shots/` directories using the MCP `publish` tool or explicit output paths. Do not leave film outputs in `outputs/comfyui/`.

---

## Stack Capabilities & Upgrade Queue

**Already installed:**
- Flux.1-dev + VAE + text encoders → high-quality stills and concept art ✓
- Illustrious XL → SDXL-based character/illustration work ✓
- 13 Flux LoRAs (anime/illustration/graphic design) ✓

**Gaps in the current stack:**
- No video generation models → no motion sequences
- No upscalers → no high-res output finalization
- No ControlNet models → no pose/depth/structure control
- LoRA library skews anime/graphic design — thin on cinematic/photographic aesthetics
- No AnimateDiff motion modules
- No custom nodes for video pipeline

---

## Download Queue

Work through this in order. Check VRAM budget: Flux and HunyuanVideo cannot load simultaneously — unload between sessions.

### Priority 1: Upscalers (no VRAM cost, immediate quality improvement)

```bash
# 4x-UltraSharp — best general upscaler
wget -O models/upscale_models/4x-UltraSharp.pth \
  "https://civitai.com/api/download/models/125843?token=${CIVITAI_API_KEY}"

# RealESRGAN x4plus — realistic textures
wget -O models/upscale_models/RealESRGAN_x4plus.pth \
  "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"

# 4x-AnimeSharp — for any anime/illustration frames
wget -O models/upscale_models/4x-AnimeSharp.pth \
  "https://civitai.com/api/download/models/16415?token=${CIVITAI_API_KEY}"
```

### Priority 2: ControlNet (essential for spatial control and character consistency)

```bash
# Flux ControlNet Depth v3 — brutalist space composition and staging
hf download XLabs-AI/flux-controlnet-depth-v3 \
  flux-dev-controlnet-depth-v3.safetensors \
  --local-dir models/controlnet/

# Flux ControlNet Canny v3 — hard-edge architectural lines
hf download XLabs-AI/flux-controlnet-canny-v3 \
  flux-dev-controlnet-canny-v3.safetensors \
  --local-dir models/controlnet/

# SDXL ControlNet OpenPose — character pose for Illustrious XL
hf download thibaud/controlnet-openpose-sdxl-1.0 \
  diffusion_pytorch_model.safetensors \
  --local-dir models/controlnet/ \
  --local-dir-use-symlinks False
# rename after: mv models/controlnet/diffusion_pytorch_model.safetensors models/controlnet/controlnet-openpose-sdxl.safetensors
```

### Priority 3: Video Generation — SVD-XT (~9GB, image-to-video)

Best for: character motion, reactive shots, image-driven sequences.
Natively supported in ComfyUI — no extra nodes required.

```bash
hf download stabilityai/stable-video-diffusion-img2vid-xt \
  svd_xt.safetensors \
  --local-dir models/checkpoints/
```

### Priority 4: AnimateDiff Motion Modules (~1.7GB, loop-based motion)

Best for: environmental loops, crowd motion, ambient sequences.
Requires `ComfyUI-AnimateDiff-Evolved` node (see Custom Nodes below).

```bash
hf download guoyww/animatediff-motion-adapter-v1-5-3 \
  mm_sd_v15_v3.ckpt \
  --local-dir models/animatediff_models/

# Camera motion LoRAs (small, highly useful)
hf download guoyww/animatediff-motion-lora-v1-5-3 \
  v2_lora_ZoomIn.ckpt v2_lora_ZoomOut.ckpt \
  v2_lora_PanLeft.ckpt v2_lora_PanRight.ckpt \
  v2_lora_TiltUp.ckpt v2_lora_TiltDown.ckpt \
  --local-dir models/animatediff_motion_lora/
```

> Add `animatediff_models` and `animatediff_motion_lora` to `configs/comfyui/extra_model_paths.yaml` after download.

### Priority 5: HunyuanVideo 1.5 (~14GB FP8, best quality on 3090)

Best for: establishing shots, long cinematic sequences, atmospheric b-roll.
Requires `ComfyUI-HunyuanVideoWrapper` node and its own text encoder.

```bash
# Transformer (FP8 quantized — fits 3090)
hf download Kijai/HunyuanVideo_comfy \
  hunyuan_video_720_fp8_e4m3fn.safetensors \
  --local-dir models/diffusion_models/

# LLM text encoder (required — separate from Flux encoders)
hf download Kijai/llava-llama-3-8b-text-encoder-tokenizer \
  --local-dir models/text_encoders/llava-llama-3-8b/

# HunyuanVideo VAE (separate from flux-ae)
hf download hunyuanvideo-community/HunyuanVideo \
  vae/pytorch_model.pt \
  --local-dir models/vae/hunyuan/
```

VRAM note: HunyuanVideo loads ~16–18GB. Unload Flux between sessions.

### Priority 6: Cinematic & Film-Aesthetic LoRAs

Expands the LoRA library beyond anime/graphic design into photographic and cinematic aesthetics.
Download these for Flux.1-dev (search exact names on CivitAI):

| Target Aesthetic | Search Term | Dir |
|---|---|---|
| Film noir / chiaroscuro | `"film noir flux lora"` | `models/loras/` |
| Cinematic lighting / anamorphic | `"cinematic lighting flux"` | `models/loras/` |
| Brutalist architecture | `"brutalist architecture flux"` | `models/loras/` |
| Industrial environments | `"industrial gritty flux"` | `models/loras/` |
| Atmospheric haze / fog | `"atmospheric fog flux"` | `models/loras/` |
| Film grain / analog texture | `"film grain flux"` | `models/loras/` |

After downloading, add trigger words and weights to `models/MODELS.md` and update `INDEX.md`.

---

## Custom Nodes to Install

Install via ComfyUI Manager or `git clone` into `comfyui/custom_nodes/`. After installing, restart the stack (`imggen stop && imggen`).

| Node | Repo | Enables |
|---|---|---|
| **ComfyUI-VideoHelperSuite** | `Kosinkadink/ComfyUI-VideoHelperSuite` | Frame sequence → MP4 assembly |
| **ComfyUI-AnimateDiff-Evolved** | `Kosinkadink/ComfyUI-AnimateDiff-Evolved` | AnimateDiff motion modules |
| **ComfyUI-Frame-Interpolation** | `Fannovel16/ComfyUI-Frame-Interpolation` | RIFE: 8fps → 24fps smoothing |
| **ComfyUI-HunyuanVideoWrapper** | `kijai/ComfyUI-HunyuanVideoWrapper` | HunyuanVideo 1.5 generation |
| **x-flux-comfyui** | `XLabs-AI/x-flux-comfyui` | Flux ControlNet support |

```bash
cd comfyui/custom_nodes/
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved
git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation
git clone https://github.com/kijai/ComfyUI-HunyuanVideoWrapper
git clone https://github.com/XLabs-AI/x-flux-comfyui
# Install each node's requirements:
for d in ComfyUI-VideoHelperSuite ComfyUI-AnimateDiff-Evolved ComfyUI-Frame-Interpolation ComfyUI-HunyuanVideoWrapper x-flux-comfyui; do
  [ -f "$d/requirements.txt" ] && ../venv/bin/pip install -r "$d/requirements.txt"
done
```

---

## MCP Workflow — RΞΡLΙCΔ Production Example

The MCP server auto-discovers workflows from `workflows/`. Film production workflows belong in the project:

```
/home/menser/Dropbox/ART/RΞΡLΙCΔ/pipeline/comfy/workflows/
├── img/    ← concept art, character studies, location designs
└── vid/    ← video generation (SVD, AnimateDiff, HunyuanVideo)
```

**Option A:** Symlink or copy finished workflows into this repo's `workflows/` for MCP discovery.
**Option B:** Point `COMFY_MCP_WORKFLOW_DIR` at the project's workflow directory directly:
```bash
# In scripts/start_comfyui_mcp.sh, change:
export COMFY_MCP_WORKFLOW_DIR="/home/menser/Dropbox/ART/RΞΡLΙCΔ/pipeline/comfy/workflows"
```

Option B is preferred — keeps workflows and the project in sync without duplication.

### Typical MCP session for a scene

```
1. imggen                          # start stack
2. list_workflows                  # confirm scene workflow is visible
3. run_workflow sc012_establishing \
     PARAM_PROMPT="..."            # generate concept frames
4. view_image <asset_id>           # review in-session
5. publish <asset_id> \
     /home/menser/Dropbox/ART/RΞΡLΙCΔ/prod/scenes/sc012_*/shots/
                                   # write to project
```

---

## extra_model_paths.yaml — Expected Final State

After all downloads, `configs/comfyui/extra_model_paths.yaml` should include:

```yaml
comfyui:
  base_path: /media/menser/fauna/image_gen/models
  checkpoints: checkpoints/
  clip: clip/
  clip_vision: clip_vision/
  controlnet: controlnet/
  diffusion_models: diffusion_models/
  embeddings: embeddings/
  loras: loras/
  style_models: style_models/
  text_encoders: text_encoders/
  upscale_models: upscale_models/
  vae: vae/
  # Video generation
  animatediff_models: animatediff_models/
  animatediff_motion_lora: animatediff_motion_lora/
```

Remember to copy to `comfyui/extra_model_paths.yaml` after editing (`cp configs/comfyui/extra_model_paths.yaml comfyui/`).

---

## After Each Model Download

1. Update `models/MODELS.md` — add filename, trigger words, source URL, recommended weight
2. Update `INDEX.md` — add to the installed table with file size
3. Run `list_models` via MCP to confirm ComfyUI can see it
4. Commit both files: `git add models/MODELS.md INDEX.md && git commit`
   (auto-push hook will push to GitHub)
