# INDEX.md

Actual installed state of this machine. Update when adding models or tools.
Last updated: 2026-03-23

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
| `svd_xt.safetensors` | 9.0G | SVD | Stable Video Diffusion XT — image-to-video, 25 frames |

### Diffusion Models (Flux)
| File | Size | Notes |
|---|---|---|
| `flux1-dev.safetensors` | 23G | Flux.1-dev transformer; load at fp8 in ComfyUI |
| `flux1-canny-dev.safetensors` | 11G | Flux Canny ControlNet (native diffusion model variant) |
| `flux1-depth-dev.safetensors` | 11G | Flux Depth ControlNet (native diffusion model variant) |

### VAE
| File | Size | Use with |
|---|---|---|
| `sdxl.vae.safetensors` | 320M | Illustrious XL, SDXL |
| `flux-ae.safetensors` | 320M | Flux.1-dev |

### Text Encoders (Flux only)
| File | Size | Notes |
|---|---|---|
| `clip_l.safetensors` | 235M | Required for Flux |
| `t5xxl_fp8_e4m3fn.safetensors` | 4.6G | Required for Flux; fp8 quantized |

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

All trained for **Flux.1-dev**. Not compatible with Illustrious XL / SDXL.

### Anime
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `Anime-CRABDM-Flux.safetensors` | 19M | `Anime CRABDM style` | 0.6 | [civitai/832858](https://civitai.com/models/832858) |
| `Neurocore-ShadowCircuit-Flux.safetensors` | 74M | `in the style of cksc,` | 0.8–1.0 | [civitai/938811](https://civitai.com/models/938811) |
| `RetroAnime-Flux.safetensors` | 1.1G | none | 0.8–1.2 | [civitai/721039](https://civitai.com/models/721039) |
| `FluxMythSharpL1nes.safetensors` | 74M | `SharpL1nes` | 0.8–1.0 | [civitai/599757](https://civitai.com/models/599757) |

### Illustration
| File | Size | Trigger | Weight | Source |
|---|---|---|---|---|
| `IllustrationConcept-Flux.safetensors` | 74M | none | 0.4–0.8 | [civitai/858800](https://civitai.com/models/858800) |
| `PainterlyFantasy-Flux.safetensors` | 74M | `in the style of ckpf,` | 0.8–1.0 | [civitai/1059859](https://civitai.com/models/1059859) |

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

---

## ControlNet

### Flux ControlNet (XLabs v3)
| File | Size | Notes |
|---|---|---|
| `flux-depth-controlnet-v3.safetensors` | 1.4G | Depth/composition control for Flux; requires x-flux-comfyui node |
| `flux-canny-controlnet-v3.safetensors` | 1.4G | Edge/line control for Flux; requires x-flux-comfyui node |

### SDXL ControlNet
| File | Size | Notes |
|---|---|---|
| `OpenPoseXL2.safetensors` | 4.7G | Pose control for Illustrious XL / SDXL |

---

## Upscalers
| File | Size | Notes |
|---|---|---|
| `4x-UltraSharp.pth` | 64M | Best general upscaler |
| `RealESRGAN_x4plus.pth` | 64M | Realistic textures |
| `4x-AnimeSharp.pth` | 64M | Anime/illustration upscaler |

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

### VAE
| File | Dir | Size | Notes |
|---|---|---|---|

---

## Empty
- `models/embeddings/` — empty
- `models/clip/` — empty

---

## Unindexed — needs annotation

> Auto-detected by sync_index.py. Move each row to its proper section and fill in metadata.

### ControlNet (`controlnet/`)

| File | Size | Base | Trigger | Notes |
|---|---|---|---|---|
| `flux-controlnet-union-instantx.safetensors` | 6.2G | — | — | TODO |
| `flux-controlnet-union-pro-shakker.safetensors` | 6.2G | — | — | TODO |
| `flux-openpose-controlnet.safetensors` | 2.8G | — | — | TODO |

### Diffusion Models (`diffusion_models/`)

| File | Size | Base | Trigger | Notes |
|---|---|---|---|---|
| `diffusion_pytorch_model-00001-of-00006.safetensors` | 9.3G | — | — | TODO |
| `diffusion_pytorch_model-00002-of-00006.safetensors` | 9.3G | — | — | TODO |
| `diffusion_pytorch_model-00003-of-00006.safetensors` | 9.3G | — | — | TODO |
| `flux1-kontext-dev.safetensors` | 22.2G | — | — | TODO |

### LoRAs (`loras/`)

| File | Size | Base | Trigger | Notes |
|---|---|---|---|---|
| `Cinematic1940s-Flux.safetensors` | 164M | — | — | TODO |
| `CinematicFilmStock-Flux.safetensors` | 292M | — | — | TODO |
| `CinematicStyle-v4-Flux.safetensors` | 292M | — | — | TODO |
| `ClassicNeoFilmNoir-Flux.safetensors` | 292M | — | — | TODO |
| `FilmNoir-V1-Flux.safetensors` | 146M | — | — | TODO |
| `FilmNoir-v1-Flux.safetensors` | 164M | — | — | TODO |
| `QwenNextScene-v2.safetensors` | 281M | — | — | TODO |
| `RetroCinematic-Flux.safetensors` | 36M | — | — | TODO |
| `Sketchy-Illustrious.safetensors` | 217M | — | — | TODO |
| `StoryboardSketch-Flux.safetensors` | 292M | — | — | TODO |
| `Storyboarding-v2-Flux.safetensors` | 37M | — | — | TODO |
| `WongKarwai-Cinematic-Flux.safetensors` | 584M | — | — | TODO |
| `film-storyboard.safetensors` | 164M | — | — | TODO |
| `flux-ip-adapter-v2-xlabs.safetensors` | 1008M | — | — | TODO |

### Text Encoders (`text_encoders/`)

| File | Size | Base | Trigger | Notes |
|---|---|---|---|---|
| `model-00001-of-00004.safetensors` | 4.6G | — | — | TODO |
| `model-00002-of-00004.safetensors` | 4.7G | — | — | TODO |
| `model-00003-of-00004.safetensors` | 4.6G | — | — | TODO |
| `model-00004-of-00004.safetensors` | 1.1G | — | — | TODO |
| `t5xxl_fp16.safetensors` | 4.6G | — | — | TODO |
| `wan-umt5-xxl-enc-bf16.pth` | 10.6G | — | — | TODO |

### VAE (`vae/`)

| File | Size | Base | Trigger | Notes |
|---|---|---|---|---|
| `Wan2.1_VAE.pth` | 484M | — | — | TODO |
| `ae.safetensors` | 319M | — | — | TODO |
| `pytorch_model.pt` | 940M | — | — | TODO |

### workflows (`workflows/`)

| File | Size | Base | Trigger | Notes |
|---|---|---|---|---|
| `controlnet_depth.json` | 8K | — | — | TODO |
| `controlnet_pose.json` | 16K | — | — | TODO |
| `flux_continuum_1-7-0.json` | 1M | — | — | TODO |
| `flux_continuum_1-7-1_beta.json` | 1M | — | — | TODO |
| `flux_continuum_light.json` | 824K | — | — | TODO |
| `flux_controlnet_canny.json` | 10K | — | — | TODO |
| `flux_controlnet_depth.json` | 10K | — | — | TODO |
| `flux_inpaint.json` | 10K | — | — | TODO |
| `flux_outpaint.json` | 11K | — | — | TODO |
| `flux_redux.json` | 23K | — | — | TODO |
| `flux_txt2img.json` | 18K | — | — | TODO |
| `flux_txt2img_checkpoint.json` | 7K | — | — | TODO |
| `img2img.json` | 6K | — | — | TODO |
| `inpaint.json` | 6K | — | — | TODO |
| `inpaint_outpaint.json` | 8K | — | — | TODO |
| `lora_basic.json` | 6K | — | — | TODO |
| `lora_multiple.json` | 7K | — | — | TODO |
| `sdxl_basic.json` | 25K | — | — | TODO |
| `upscale_esrgan.json` | 6K | — | — | TODO |

