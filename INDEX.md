# INDEX.md

Actual installed state of this machine. Update when adding models or tools.
Last updated: 2026-06-09

---

## Tools

| Tool | Path | Commit | Port |
|---|---|---|---|
| ComfyUI | `comfyui/` | `45d5c83a` | 8188 |
| Automatic1111 | `automatic1111/` | `82a973c0` | 7860 |
| comfyui-mcp-server | `comfyui-mcp-server/` | `e0101b2` | 9000 |

---

## Base Models

### Checkpoints (SDXL / Video)
| File | Size | Base | Notes |
|---|---|---|---|
| `Illustrious-XL-v0.1.safetensors` | 6.5G | SDXL | Anime/illustration; use `sdxl.vae.safetensors` |
| `sd_xl_base_1.0.safetensors` | 6.5G | SDXL | Vanilla SDXL 1.0 base; broadest LoRA compatibility |
| `sd_xl_refiner_1.0.safetensors` | 5.7G | SDXL | Two-stage refinement pass; pair with Base after generation |
| `noobai-xl-vpred10.safetensors` | 6.6G | NoobAI | v-prediction 1.0; distinct base derived from SDXL — use LoRAs tagged for NoobAI specifically |
| `pony-diffusion-xl-v6.safetensors` | 6.5G | Pony | Distinct base derived from SDXL — use LoRAs tagged for Pony; prompts require `score_9, score_8_up, score_7_up` prefix for best results |
| `svd_xt.safetensors` | 9.0G | SVD | Stable Video Diffusion XT — image-to-video, 25 frames |

### Diffusion Models (Flux)
| File | Size | Notes |
|---|---|---|
| `flux1-dev.safetensors` | 23G | Flux.1-dev transformer; load at fp8 in ComfyUI |
| `flux1-canny-dev.safetensors` | 11G | Flux Canny ControlNet (native diffusion model variant) |
| `flux1-depth-dev.safetensors` | 11G | Flux Depth ControlNet (native diffusion model variant) |
| `flux1-kontext-dev.safetensors` | 22.2G | Flux.1-Kontext-dev — in-context image editing; reuses Flux VAE + text encoders |

### VAE
| File | Size | Use with |
|---|---|---|
| `sdxl.vae.safetensors` | 320M | Illustrious XL, SDXL |
| `flux-ae.safetensors` | 320M | Flux.1-dev, Flux.1-Kontext-dev |

> `ae.safetensors` is a symlink → `flux-ae.safetensors` (ComfyUI compatibility alias)

### Text Encoders (Flux only)
| File | Size | Notes |
|---|---|---|
| `clip_l.safetensors` | 235M | Required for Flux |
| `t5xxl_fp8_e4m3fn.safetensors` | 4.6G | Required for Flux; fp8 quantized |

> `t5xxl_fp16.safetensors` is a symlink → `t5xxl_fp8_e4m3fn.safetensors` (fp16 alias for nodes that require that filename)

### Style Models
| File | Size | Notes |
|---|---|---|
| `flux1-redux-dev.safetensors` | 124M | Flux Redux — style/image conditioning |

### Clip Vision
| File | Size | Notes |
|---|---|---|
| `sigclip_vision_patch14_384.safetensors` | 817M | Required for Flux Redux |

---

## LoRAs

> Most LoRAs target **Flux.1-dev**. Exceptions noted per entry.

### Anime
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `Anime-CRABDM-Flux.safetensors` | 19M | `Anime CRABDM style` | 0.6 | [civitai/832858](https://civitai.com/models/832858) |
| `Neurocore-ShadowCircuit-Flux.safetensors` | 74M | `in the style of cksc,` | 0.8–1.0 | [civitai/938811](https://civitai.com/models/938811) |
| `RetroAnime-Flux.safetensors` | 1.1G | none | 0.8–1.2 | [civitai/721039](https://civitai.com/models/721039) |
| `FluxMythSharpL1nes.safetensors` | 74M | `SharpL1nes` | 0.8–1.0 | [civitai/599757](https://civitai.com/models/599757) |

### Illustration (Flux)
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `IllustrationConcept-Flux.safetensors` | 74M | none | 0.4–0.8 | [civitai/858800](https://civitai.com/models/858800) |
| `PainterlyFantasy-Flux.safetensors` | 74M | `in the style of ckpf,` | 0.8–1.0 | [civitai/1059859](https://civitai.com/models/1059859) |

### Illustration (SDXL)
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `watercolor-illustration-sdxl.safetensors` | 244M | none | 0.5–0.8 | [civitai/2795688](https://civitai.com/models/) |
| `LineArtF.safetensors` | 218M | `lineart`, `monochrome`, `greyscale` | 0.5–1.0 | [civitai/596934](https://civitai.com/models/596934) — "Line Art Style [SDXL Pony]"; black-and-white lineart drawings (source verified by file SHA256) |

### Cartoon
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `CharacterDesign-FluxV2.safetensors` | 74M | `CharacterDesignFLUX` | 0.8 | [civitai/100435](https://civitai.com/models/100435) |
| `Disney-Studios-Flux.safetensors` | 74M | `DisneyStudio` + `cartoon` | 0.6–0.8 | [civitai/404277](https://civitai.com/models/404277) |
| `ComicBookPage-Flux.safetensors` | 328M | `comic strip style` | 0.8–1.0 | [civitai/462611](https://civitai.com/models/462611) |

### Graphic Design / Logo
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `SwissDesign-Flux.safetensors` | 19M | `sw1ssdes1gn` | 0.8 | [civitai/816745](https://civitai.com/models/816745) |
| `MiltonGlaser-Flux.safetensors` | 303M | `in the style of milton-glaser` | 0.8 | [civitai/529473](https://civitai.com/models/529473) |
| `GraffitiLogo-Flux.safetensors` | 19M | `graffiti logo` + `black background` | 1.0–1.5 | [civitai/836596](https://civitai.com/models/836596) |
| `LogoMaker1024-Flux.safetensors` | 38M | `Company logo by LogoMaker1024,` | 0.4–1.0 | [civitai/757432](https://civitai.com/models/757432) |

### Film & Storyboard (Flux)
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `film-storyboard.safetensors` | 164M | none | 0.8–1.0 | [ali-vilab/In-Context-LoRA](https://huggingface.co/ali-vilab/In-Context-LoRA) |
| `StoryboardSketch-Flux.safetensors` | 292M | `Storyboard sketch` | 0.7–0.9 | [civitai/162118](https://civitai.com/models/162118) |
| `Storyboarding-v2-Flux.safetensors` | 37M | `storyboarding` | 1.0 | [civitai/1634243](https://civitai.com/models/1634243) |
| `QwenNextScene-v2.safetensors` | 281M | image+text conditioning | — | [lovis93/next-scene-qwen-image-lora](https://huggingface.co/lovis93/next-scene-qwen-image-lora-2509) |

### Film Noir & Cinematic (Flux)
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `FilmNoir-v1-Flux.safetensors` | 164M | `Film Noir`, `1940's` | 0.7–1.0 | [civitai/311769](https://civitai.com/models/311769) |
| `FilmNoir-V1-Flux.safetensors` | 146M | none | 0.8–1.0 | [civitai/1605523](https://civitai.com/models/1605523) |
| `ClassicNeoFilmNoir-Flux.safetensors` | 292M | `Film Noir`, `1940's` | 0.7–1.0 | [civitai/311769](https://civitai.com/models/311769) — ⚠️ same model as FilmNoir-v1 (duplicate download, same versionId) |
| `Cinematic1940s-Flux.safetensors` | 164M | `cinematic_1940s` | 0.8–1.0 | [civitai/1351798](https://civitai.com/models/1351798) |
| `CinematicStyle-v4-Flux.safetensors` | 292M | `Cinematic style` | 0.4–0.6 | [civitai/680417](https://civitai.com/models/680417) |
| `WongKarwai-Cinematic-Flux.safetensors` | 584M | `Wong Kar-wei Cinematic Style`, `Wong Kar-wei`, `Vague background and prospect` | 0.7 | [civitai/667594](https://civitai.com/models/667594) |
| `CinematicFilmStock-Flux.safetensors` | 292M | `cinematic film style`, `filmstrip`, `Kodak film style` | 0.8–1.0 | [civitai/273500](https://civitai.com/models/273500) |
| `RetroCinematic-Flux.safetensors` | 36M | `In the style of ff-rcs` | 0.8–1.0 | [civitai/1109567](https://civitai.com/models/1109567) |

### Realism / Skin (Flux)
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `aidmaRealisticSkin-FLUX-v0.1.safetensors` | 75M | `aidmarealisticskin` | 0.5–1.0 | [civitai/1157318](https://civitai.com/models/1157318) — "Photorealistic Skin ⛔ No plastic"; kills pasted-on/plastic faces |
| `PortraitEngine-v2.0-Flux.safetensors` | 2.4G | none | 0.6–1.0 | [civitai/2067704](https://civitai.com/models/2067704) — "Portrait Engine, Detailed Skin V2.0"; natural pores/texture + cinematic light & film grain. Pairs with gray-bg + soft-key character-sheet convention |

### Graphic Design / Logo (SDXL)
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `bauhaus-design-sdxl.safetensors` | 218M | none | 0.5–0.9 | [civitai/1953791](https://civitai.com/models/) |
| `halftone-xl.safetensors` | 163M | none | 0.5–1.0 | [civitai/359311](https://civitai.com/models/) — halftone/print-texture; closest available SDXL risograph proxy |
| `Minimalist_vector_art.safetensors` | 218M | `ArsMJStyle`, `Minimalist Vector Art` | 1.2–1.5 | [civitai/658816](https://civitai.com/models/658816) — "Minimalist vector art" (Pony); flat minimalist vector style; add `silhouette, monochrome, greyscale, simple background` (source verified by file SHA256) |

### Utility / Speed (SDXL)
| File | Size | Base | Notes |
|---|---|---|---|
| `sdxl-lightning-4step.safetensors` | 376M | SDXL | 4-step fast inference; sampler: `euler`, scheduler: `sgm_uniform`, steps: 4, CFG: 1.0–2.0 |
| `lcm-lora-sdxl.safetensors` | 376M | SDXL | LCM fast inference; sampler: `lcm`, steps: 4–8, CFG: 1.0 |

### Special Tools
| File | Size | Base | Notes |
|---|---|---|---|
| `flux-ip-adapter-v2-xlabs.safetensors` | 1.0G | Flux | XLabs IP-Adapter v2; image prompt conditioning; requires [x-flux-comfyui](https://github.com/XLabs-AI/x-flux-comfyui) |
| `Sketchy-Illustrious.safetensors` | 217M | **Illustrious XL** | Sketchy line-art style; SDXL base (not Flux!) |

### Pony Diffusion V6 XL
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `darkcore_pny.safetensors` | 94M | `s_darkcore style` | 0.8–1.0 | [civitai/605731](https://civitai.com/models/605731/darkcore-style-sdxl-and-pony) — comic-book style: bold lines, washed colors, grim mood; Pony version trained on AutismMix. Used by `antro_workflow_02`. |
| `eyes_enhancer_pony_v3.safetensors` | 218M | none (eye enhancer, positive) | 0.4–0.8 | [civitai/365708](https://civitai.com/models/365708/lora-eyes-enhancer-free-use-or-merge) — beautifies eyes; supports varied pupil types |

### WAN 2.2 I2V — Lightning distill (video)
| File | Size | Base | Weight | Source |
|---|---|---|---|---|
| `wan22_i2v_lightning_4step_high.safetensors` | 1.2G | **WAN 2.2 I2V (high-noise expert)** | 1.0 | [lightx2v/Wan2.2-Lightning](https://huggingface.co/lightx2v/Wan2.2-Lightning) — 4-step distill (rank64 Seko-V1). Wired into `wan22_i2v_a14b.json` (high loader); enables 4 steps @ cfg 1, euler. Pair with the low-noise LoRA. |
| `wan22_i2v_lightning_4step_low.safetensors` | 1.2G | **WAN 2.2 I2V (low-noise expert)** | 1.0 | [lightx2v/Wan2.2-Lightning](https://huggingface.co/lightx2v/Wan2.2-Lightning) — 4-step distill (rank64 Seko-V1). Wired into `wan22_i2v_a14b.json` (low loader). Sharp output at the fast-tier step count; fixes the under-sampled 6-step blur. |

---

## ControlNet

### Flux ControlNet (XLabs v3)
| File | Size | Notes |
|---|---|---|
| `flux-depth-controlnet-v3.safetensors` | 1.4G | Depth/composition control for Flux; requires x-flux-comfyui node |
| `flux-canny-controlnet-v3.safetensors` | 1.4G | Edge/line control for Flux; requires x-flux-comfyui node |

### Flux ControlNet Union
| File | Size | Notes |
|---|---|---|
| `flux-controlnet-union-pro-shakker.safetensors` | 6.2G | Shakker-Labs Union Pro — single model for Canny/Depth/Pose/Tile/MLSD/Normal/Segment |
| `flux-controlnet-union-instantx.safetensors` | 6.2G | InstantX Union — alternate single-model union variant |

### Flux ControlNet (Pose)
| File | Size | Notes |
|---|---|---|
| `flux-openpose-controlnet.safetensors` | 2.8G | OpenPose body+hand pose control for Flux |

### SDXL ControlNet
| File | Size | Notes |
|---|---|---|
| `OpenPoseXL2.safetensors` | 4.7G | Pose control for Illustrious XL / SDXL |
| `controlnet-canny-sdxl.safetensors` | 2.4G | Edge/line control for Illustrious XL / SDXL; use standard `ControlNetLoader` node |
| `controlnet-depth-sdxl.safetensors` | 2.4G | Depth/composition control for Illustrious XL / SDXL; use standard `ControlNetLoader` node |

---

## Upscalers
| File | Size | Notes |
|---|---|---|
| `4x-UltraSharp.pth` | 64M | Best general upscaler |
| `RealESRGAN_x4plus.pth` | 64M | Realistic textures |
| `4x-AnimeSharp.pth` | 64M | Anime/illustration upscaler |

---

## Embeddings (`models/embeddings/`)
| File | Size | Base | Trigger | Notes |
|---|---|---|---|---|
| `zPDXL3.safetensors` | 264K | **Pony Diffusion V6 XL** (and Pony-adjacent) | `embedding:zPDXL3` in negative | "Pony PDXL Negative Embeddings — High Quality V3." Community-standard textual inversion for Pony's known eye/anatomy/censoring failure modes. Used at weight 1.0–2.0 in the **negative** prompt. CivitAI model 332646, version 720175. Does not work on non-Pony checkpoints. |

---

## AnimateDiff

### Motion Module
| File | Size | Notes |
|---|---|---|
| `mm_sd_v15_v3.safetensors` | 1.6G | AnimateDiff motion adapter v1.5-3; required for all AD workflows |

### Camera Motion LoRAs (SD1.5 + AnimateDiff v2)
| File | Size | Notes |
|---|---|---|
| `1600_cseti_1077723_camera-zoomin-10vid_mv2.safetensors` | 113M | Zoom In (16f) |
| `1600_cseti_9192119_camera-zoomout-10vid_mv2.safetensors` | 113M | Zoom Out |
| `1600_cseti_9213319_camera-lateral_left-10vid_mv2.safetensors` | 113M | Pan Left |
| `1600_cseti_6664682_camera-lateral_right-10vid_mv2.safetensors` | 113M | Pan Right |
| `1600_cseti_1720230_camera-crane_up-10vid_mv2.safetensors` | 113M | Tilt Up |
| `1600_cseti_9406077_camera-crane_down-10vid_mv2.safetensors` | 113M | Tilt Down |
| `2800_cseti_1093371_camera-zoomin-32f-10vid_mv2.safetensors` | 113M | Zoom In (32f experimental) |

---

## HunyuanVideo 1.5

> VRAM note: loads ~16–18GB. Cannot run simultaneously with Flux. Requires ComfyUI-HunyuanVideoWrapper.

### Diffusion Model
| File | Dir | Size | Notes |
|---|---|---|---|
| `hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors` | `diffusion_models/` | 13G | CFG-distilled FP8 transformer |

### LLM Text Encoder
| File | Dir | Size | Notes |
|---|---|---|---|
| `model-00001-of-00004.safetensors` | `text_encoders/llava-llama-3-8b/` | 4.6G | LLaVA-LLaMA-3-8B shard 1/4 |
| `model-00002-of-00004.safetensors` | `text_encoders/llava-llama-3-8b/` | 4.7G | LLaVA-LLaMA-3-8B shard 2/4 |
| `model-00003-of-00004.safetensors` | `text_encoders/llava-llama-3-8b/` | 4.6G | LLaVA-LLaMA-3-8B shard 3/4 |
| `model-00004-of-00004.safetensors` | `text_encoders/llava-llama-3-8b/` | 1.1G | LLaVA-LLaMA-3-8B shard 4/4 |

### VAE
| File | Dir | Size | Notes |
|---|---|---|---|
| `pytorch_model.pt` | `vae/hunyuan/` | 940M | HunyuanVideo VAE |

---

## WAN 2.2 I2V

> VRAM note: loads ~18–20GB. Cannot run simultaneously with Flux or HunyuanVideo. Requires ComfyUI-WAN-Wrapper.
> Both `high_noise` and `low_noise` model variants use identical shard filenames.

### Diffusion Models (merged)
| File | Dir | Size | Notes |
|---|---|---|---|
| `wan2.2-i2v-14B-high.safetensors` | `diffusion_models/` | 53G | High-noise expert — handles steps 0–3 in dual-sampler pipeline |
| `wan2.2-i2v-14B-low.safetensors` | `diffusion_models/` | 53G | Low-noise expert — handles steps 3–6 in dual-sampler pipeline |

### Text Encoder
| File | Dir | Size | Notes |
|---|---|---|---|
| `wan-umt5-xxl-enc-bf16.pth` | `text_encoders/` | 10.6G | UMT5-XXL bf16 — required for WAN 2.2 |

### VAE
| File | Dir | Size | Notes |
|---|---|---|---|
| `Wan2.1_VAE.pth` | `vae/wan/` | 484M | WAN 2.1/2.2 VAE |

---

## Workflows

| File | Size | Model | Notes |
|---|---|---|---|
| `flux_txt2img.json` | 18K | **Flux.1-dev** | Text-to-image baseline; uses UNETLoader + DualCLIPLoader |
| `flux_txt2img_checkpoint.json` | 7K | **Flux.1-dev** | Same as above but via CheckpointLoader |
| `flux_inpaint.json` | 10K | **Flux.1-dev** | Inpainting |
| `flux_outpaint.json` | 11K | **Flux.1-dev** | Outpainting |
| `flux_controlnet_canny.json` | 10K | **Flux.1-canny-dev** | Uses native `flux1-canny-dev.safetensors` model (not XLabs ControlNet) |
| `flux_controlnet_depth.json` | 10K | **Flux.1-depth-dev** | Uses native `flux1-depth-dev.safetensors` model directly (LoRA node removed) |
| `flux_redux.json` | 23K | **Flux.1-dev** | Style/image conditioning; requires `flux1-redux-dev.safetensors` + `sigclip_vision_patch14_384.safetensors` |
| `sdxl_basic.json` | 25K | **SDXL Base 1.0 + Refiner** | Two-stage pipeline; both models installed |
| `controlnet_depth.json` | 8K | **Illustrious XL** | Depth ControlNet; uses `controlnet-depth-sdxl.safetensors` via ControlNetLoader |
| `controlnet_pose.json` | 16K | **Illustrious XL** | Pose ControlNet; uses `OpenPoseXL2.safetensors` + `sdxl.vae.safetensors` |
| `img2img.json` | 6K | **Illustrious XL** | Image-to-image; 1024×1024 latent |
| `inpaint.json` | 6K | **Illustrious XL** | Inpainting; 1024×1024 latent |
| `inpaint_outpaint.json` | 8K | **Illustrious XL** | Combined inpaint+outpaint; 1024×1024 latent |
| `lora_basic.json` | 6K | **Illustrious XL** | Single LoRA; 1024×1024 latent — update LoraLoader filename to desired LoRA |
| `lora_multiple.json` | 7K | **Illustrious XL** | Multi-LoRA; 1024×1024 latent — update LoraLoader filenames to desired LoRAs |
| `upscale_esrgan.json` | 6K | **Illustrious XL** | Generate + upscale; uses `4x-UltraSharp.pth`; 1024×1024 latent |
| `hunyuanvideo_t2v.json` | 5K | **HunyuanVideo 1.5** | Text-to-video 720p; requires ComfyUI-HunyuanVideoWrapper + VideoHelperSuite |
| `wan22_i2v_a14b.json` | 20K | **WAN 2.2 A14B** | Image-to-video; dual high/low noise expert samplers; requires ComfyUI-WanVideoWrapper + KJNodes + VideoHelperSuite; ⚠️ may need merged KJ fp8 shards vs. raw shards |
| `flux_kontext_edit.json` | 6K | **Flux.1-Kontext-dev** | In-context image editing; native ComfyUI nodes only; requires ComfyUI ≥0.3.38 |
| `xlabs_controlnet_canny.json` | 8K | **Flux.1-dev** | XLabs Canny ControlNet v3; requires x-flux-comfyui + ComfyUI-ControlNet-Aux |
| `xlabs_controlnet_depth.json` | 8K | **Flux.1-dev** | XLabs Depth ControlNet v3; requires x-flux-comfyui + ComfyUI-ControlNet-Aux |
| `animatediff_txt2vid.json` | 3K | **SD 1.5** | AnimateDiff text-to-video; 16 frames 512x512; uses `v1-5-pruned-emaonly.safetensors`; requires ComfyUI-AnimateDiff-Evolved |
| `antro_workflow_02.json` | 3K | **Pony Diffusion V6 XL + Darkcore LoRA @0.9** | Locked SFW anthro head-portrait recipe — flat-duotone noir, head-and-neck crop. Sampler/scheduler/CFG/steps/clip-skip baked in: `dpmpp_2m` + `karras` + CFG 7.0 + 32 steps + clip skip -2, 1024² square. Full V3-trimmed negative baked in (clothing/torso/emotion/background-disc). Parameters: `PARAM_PROMPT` (full positive — caller supplies score prefix, `s_darkcore style`, `source_furry`, species/breed tags, `duotone/crop/pose` blocks) + `PARAM_INT_SEED`. Used by `ferine_town` portrait pipeline. |
| `storyboard_seed.json` | 2K | **Flux.1-dev + storyboard LoRA** | Storyboard panel-1 seed (text→image). Params: `PARAM_LORA_NAME`, `PARAM_FLOAT_LORA_WEIGHT`, `PARAM_PROMPT`, `PARAM_INT_WIDTH/HEIGHT/STEPS/SEED`, `PARAM_FLOAT_GUIDANCE`. Driven by `scripts/storyboard.py`. |
| `storyboard_panel.json` | 2K | **Flux.1-Kontext-dev + storyboard LoRA** | Storyboard panels 2..N (ref+text→image) — locks character/style across the sheet via Kontext. Same params as seed plus `PARAM_REF_IMAGE`. Driven by `scripts/storyboard.py`. |

---

## Empty
- `models/clip/` — empty

---

## Unindexed — needs annotation

> Auto-detected by sync_index.py. Move each row to its proper section and fill in metadata.

### Diffusion Models (`diffusion_models/`)

| File | Size | Base | Trigger | Source | Notes |
|---|---|---|---|---|---|
| `Wan2_1-VACE_module_14B_fp8_e4m3fn.safetensors` | 2.8G | wan | — | [source](https://huggingface.co/Wan-AI/Wan2.1-VACE-14B) | Official VACE is on the WAN 2.1 base (no official 2.2-VACE exists yet); Apache-2.0. Reuses the installed WAN VAE (Wan2.1_VAE.pth) and UMT5-XXL encoder — no new encoder/VAE download needed. fp8 single-file build runs on 24GB via ComfyUI-WanVideoWrapper + block swap, same envelope as WAN 2.2 I2V (cannot co-load with Flux/HunyuanVideo). size:0 → installer downloads if absent and treats any non-empty file as complete; CONFIRM exact fp8 filename on the Kijai repo before first fetch (bf16 shards live at the Wan-AI source repo). |

### LoRAs (`loras/`)

| File | Size | Base | Trigger | Source | Notes |
|---|---|---|---|---|---|
| `Qwen-Edit-2509-Multiple-angles.safetensors` | 225M | — | — | — | TODO |

### Text Encoders (`text_encoders/`)

| File | Size | Base | Trigger | Source | Notes |
|---|---|---|---|---|---|
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | 8.7G | — | — | — | TODO |

### VAE (`vae/`)

| File | Size | Base | Trigger | Source | Notes |
|---|---|---|---|---|---|
| `qwen_image_vae.safetensors` | 242M | — | — | — | TODO |

### workflows (`workflows/`)

| File | Size | Base | Trigger | Source | Notes |
|---|---|---|---|---|---|
| `qwen_image_edit_multiangle.json` | 1K | — | — | — | TODO |

