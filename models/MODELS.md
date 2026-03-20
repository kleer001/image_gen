# Model Catalog

All models go in their respective subdirectory under `/media/menser/fauna/image_gen/models/`.
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

## ControlNet (SDXL)

| Model | Dir | Source | Use |
|---|---|---|---|
| **controlnet-canny-sdxl** | `controlnet/` | HuggingFace: `diffusers/controlnet-canny-sdxl-1.0` | Edge/line control |
| **controlnet-depth-sdxl** | `controlnet/` | HuggingFace: `diffusers/controlnet-depth-sdxl-1.0` | Depth/composition |
| **controlnet-openpose-sdxl** | `controlnet/` | HuggingFace: `thibaud/controlnet-openpose-sdxl-1.0` | Pose control |

---

## Upscalers

| Model | Dir | Source | Notes |
|---|---|---|---|
| **4x-UltraSharp** | `upscale_models/` | CivitAI: search "4x UltraSharp" | Best general upscaler |
| **4x-AnimeSharp** | `upscale_models/` | CivitAI: search "4x AnimeSharp" | Anime-tuned |
| **ESRGAN 4x** | `upscale_models/` | HuggingFace: `ai-forever/Real-ESRGAN` | Baseline |

---

## Notes

- CivitAI searches will show multiple versions — sort by "Most Downloaded" and prefer models with active comments/previews.
- For Illustrious XL and NoobAI, prefer LoRAs explicitly tagged for those checkpoints.
- LoRA weights are starting points; adjust per prompt and checkpoint combination.
- Pony Diffusion requires `score_9, score_8_up, score_7_up` prefix in prompts for best results.
