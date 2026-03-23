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

### Checkpoints (SDXL)
| File | Size | Base | Notes |
|---|---|---|---|
| `Illustrious-XL-v0.1.safetensors` | 6.5G | SDXL | Anime/illustration; use `sdxl.vae.safetensors` |

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

---

## Upscalers
| File | Size | Notes |
|---|---|---|
| `4x-UltraSharp.pth` | 64M | Best general upscaler |
| `RealESRGAN_x4plus.pth` | 64M | Realistic textures |

---

## AnimateDiff

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

## In Progress / Pending

- `models/upscale_models/4x-AnimeSharp.pth` — downloading (CivitAI 1140894)
- `models/controlnet/OpenPoseXL2.safetensors` — downloading (thibaud/controlnet-openpose-sdxl-1.0)
- `models/animatediff_models/mm_sd_v15_v3.safetensors` — downloading (guoyww/animatediff-motion-adapter-v1-5-3)
- `models/checkpoints/svd_xt.safetensors` — downloading (~9GB, stabilityai/stable-video-diffusion-img2vid-xt)
- `models/diffusion_models/hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors` — downloading (~14GB, Kijai/HunyuanVideo_comfy)
- `models/text_encoders/llava-llama-3-8b/` — downloading (Kijai/llava-llama-3-8b-text-encoder-tokenizer)
- `models/vae/hunyuan/pytorch_model.pt` — downloading (tencent/HunyuanVideo)

---

## Empty
- `models/embeddings/` — empty
- `models/clip/` — empty
