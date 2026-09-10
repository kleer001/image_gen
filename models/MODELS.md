# Model Catalog

All models go in their respective subdirectory under the repo's `models/` directory.
Both ComfyUI and A1111 read from here via config.

---

## Base Checkpoints

### Anime / Illustration

| Model | Dir | Source | Notes |
|---|---|---|---|
| **Illustrious XL v0.1** | `checkpoints/` | HuggingFace: `OnomaAIResearch/Illustrious-xl-early-release-v0` | Best current SDXL anime base |
| **NoobAI XL (Epsilon)** | `checkpoints/` | CivitAI: search "NoobAI XL" | Very popular anime/illustration |
| **Pony Diffusion XL v6** | `checkpoints/` | CivitAI: search "Pony Diffusion XL v6" | Strong for stylized illustration |

### General Purpose / Versatile

| Model | Dir | Source | Notes |
|---|---|---|---|
| **SDXL Base 1.0** | `checkpoints/` | HuggingFace: `stabilityai/stable-diffusion-xl-base-1.0` | Foundational; good LoRA compatibility |
| **SDXL Refiner 1.0** | `checkpoints/` | HuggingFace: `stabilityai/stable-diffusion-xl-refiner-1.0` | Pair with Base for two-stage |

### VAE

| Model | Dir | Source | Notes |
|---|---|---|---|
| **sdxl-vae-fp16-fix** | `vae/` | HuggingFace: `madebyollin/sdxl-vae-fp16-fix` | Fixes NaN artifacts at fp16 — always use this with SDXL |

---

## LoRAs

### Style — Anime

| LoRA | Weight Range | Source | Trigger / Notes |
|---|---|---|---|
| **Anime Lineart Style** | 0.6–0.9 | CivitAI: search "anime lineart xl" | Clean lines, manga look |
| **Anime Screencap** | 0.5–0.8 | CivitAI: search "anime screencap style xl" | TV anime color palette |
| **Studio Ghibli Style** | 0.4–0.7 | CivitAI: search "ghibli style xl" | Soft painterly backgrounds |
| **90s Anime** | 0.5–0.8 | CivitAI: search "90s anime style xl" | Cel-shaded retro look |
| **Manhwa / Webtoon** | 0.5–0.8 | CivitAI: search "manhwa xl" | Korean webtoon style |

### Style — Illustration / Concept Art

| LoRA | Weight Range | Source | Trigger / Notes |
|---|---|---|---|
| **Flat 2D Illustration** | 0.6–1.0 | CivitAI: search "flat illustration xl" | Minimal shading, vector-adjacent |
| **Storybook Illustration** | 0.5–0.8 | CivitAI: search "storybook illustration xl" | Children's book warmth |
| **Watercolor Illustration** | 0.5–0.8 | CivitAI: search "watercolor illustration xl" | Soft washes |
| **Concept Art Style** | 0.4–0.7 | CivitAI: search "concept art xl" | Game/film dev aesthetic |
| **Digital Painting** | 0.5–0.8 | CivitAI: search "digital painting xl" | Textured brush strokes |

### Style — Graphic Design

| LoRA | Weight Range | Source | Trigger / Notes |
|---|---|---|---|
| **Flat Icon / UI Design** | 0.6–1.0 | CivitAI: search "flat icon design xl" | Clean iconography |
| **Bauhaus / Poster Design** | 0.5–0.9 | CivitAI: search "bauhaus poster xl" | Geometric modernist |
| **Swiss International Style** | 0.5–0.9 | CivitAI: search "swiss style poster xl" | Grid-based, typography-heavy |
| **Retro / Vintage Poster** | 0.5–0.8 | CivitAI: search "vintage poster style xl" | Mid-century aesthetic |
| **Risograph Print** | 0.6–0.9 | CivitAI: search "risograph xl" | Limited palette, grain |

### Utility

| LoRA | Weight Range | Source | Notes |
|---|---|---|---|
| **add-detail-xl** | 0.3–0.8 | CivitAI: search "add detail xl" | General detail enhancer |
| **SDXL Lightning (4-step)** | 1.0 | HuggingFace: `ByteDance/SDXL-Lightning` | Fast inference LoRA; use with matching sampler |
| **LCM LoRA SDXL** | 1.0 | HuggingFace: `latent-consistency/lcm-lora-sdxl` | 4–8 step inference; LCM sampler required |

---

## ControlNet

### Flux ControlNet (XLabs v3) — installed
| Model | File | Source | Use |
|---|---|---|---|
| **Flux Depth v3** | `flux-depth-controlnet-v3.safetensors` | HF: `XLabs-AI/flux-controlnet-depth-v3` | Depth/composition; requires x-flux-comfyui node |
| **Flux Canny v3** | `flux-canny-controlnet-v3.safetensors` | HF: `XLabs-AI/flux-controlnet-canny-v3` | Edge/line; requires x-flux-comfyui node |

### SDXL ControlNet — installed/catalog
| Model | File | Source | Use |
|---|---|---|---|
| **OpenPose XL** | `OpenPoseXL2.safetensors` | HF: `thibaud/controlnet-openpose-sdxl-1.0` | Pose control for Illustrious XL |
| **Canny SDXL** | — | HF: `diffusers/controlnet-canny-sdxl-1.0` | Edge/line control |
| **Depth SDXL** | — | HF: `diffusers/controlnet-depth-sdxl-1.0` | Depth/composition |

---

## Upscalers

| Model | File | Source | Notes |
|---|---|---|---|
| **4x-UltraSharp** | `4x-UltraSharp.pth` | CivitAI: model 125843 | Best general upscaler |
| **RealESRGAN x4plus** | `RealESRGAN_x4plus.pth` | GitHub: xinntao/Real-ESRGAN v0.1.0 | Realistic textures |
| **4x-AnimeSharp** | `4x-AnimeSharp.pth` | CivitAI: model 1140894 (versionId) | Anime/illustration frames |

---

## Video Generation

### Stable Video Diffusion XT (~9GB)
| Model | File | Source | Notes |
|---|---|---|---|
| **SVD-XT** | `checkpoints/svd_xt.safetensors` | HF: `stabilityai/stable-video-diffusion-img2vid-xt` | Image-to-video, 25 frames; natively supported in ComfyUI |

### AnimateDiff (SD1.5 loop-based motion)
| Model | File | Source | Notes |
|---|---|---|---|
| **Motion Adapter v1.5-3** | `animatediff_models/mm_sd_v15_v3.safetensors` | HF: `guoyww/animatediff-motion-adapter-v1-5-3` | Core motion module; requires ComfyUI-AnimateDiff-Evolved |
| **Camera LoRAs (7 files)** | `animatediff_motion_lora/1600_cseti_*.safetensors` | HF: `Cseti/Basic_camera_motion_LoRAs_sd15-ad2-v1` | ZoomIn/Out, PanL/R, TiltU/D, ZoomIn-32f |

### HunyuanVideo 1.5 (~14GB FP8, best quality on 3090)
| Model | File | Source | Notes |
|---|---|---|---|
| **Transformer FP8** | `diffusion_models/hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors` | HF: `Kijai/HunyuanVideo_comfy` | CFG-distilled FP8; requires ComfyUI-HunyuanVideoWrapper |
| **LLM Text Encoder** | `text_encoders/llava-llama-3-8b/` | HF: `Kijai/llava-llama-3-8b-text-encoder-tokenizer` | Separate from Flux encoders |
| **VAE** | `vae/hunyuan/pytorch_model.pt` | HF: `tencent/HunyuanVideo` (path: `hunyuan-video-t2v-720p/vae/`) | Separate from flux-ae |

> VRAM note: HunyuanVideo loads ~16–18GB. Cannot run simultaneously with Flux.

---

## Film-Aesthetic LoRAs (Flux.1-dev) — installed

See `INDEX.md § Film Noir & Cinematic` for filenames, sizes, and trigger words.

Installed: FilmNoir-v1, FilmNoir-V1, ClassicNeoFilmNoir, Cinematic1940s, CinematicStyle-v4, WongKarwai-Cinematic, CinematicFilmStock, RetroCinematic (all Flux.1-dev, trigger words TBD)

---

## Notes

- CivitAI searches will show multiple versions — sort by "Most Downloaded" and prefer models with active comments/previews.
- For Illustrious XL and NoobAI, prefer LoRAs explicitly tagged for those checkpoints.
- LoRA weights are starting points; adjust per prompt and checkpoint combination.
- Pony Diffusion requires `score_9, score_8_up, score_7_up` prefix in prompts for best results.
