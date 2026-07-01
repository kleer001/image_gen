# Scope — isolated ComfyUI v0.26.x instance

Krea 2 Turbo, Bernini-R 1.3B, and Depth Anything 3 run on this instance. None run
on the production v0.17.0 ComfyUI; per the version-isolation policy they get a new
isolated instance rather than a core upgrade. GPU ceiling: RTX 3090, 24 GB,
**sm_86 (Ampere)**: the GPU has no fp8 *compute*, so comfy dequantizes fp8 weights
to bf16 (they run, no speedup); the Blackwell-only mxfp8/nvfp4 formats are the ones
that truly don't work. LTX-2.3 was evaluated and **dropped** — its one-pass
audio+video overlaps the installed Ovi, and its 29 GB fp8 checkpoint exceeds the
24 GB card (offload-only, slow). The LTX sections below are retained as the
evaluation record.

## Approach: one shared instance, ComfyUI v0.26.x, port 8190

v0.26.0 is the floor that covers all four candidates (Krea 2 partner nodes set
the highest bar; v0.25.0 covers Bernini-R, LTX-2 nodes, Depth Anything 3). One
instance — one venv, one torch build, one `extra_model_paths.yaml` — is simpler
than four and the models don't conflict with each other, only with prod. Leave
the existing `comfyui_flux2/` (v0.24.0, port 8189) frozen; stand up a clean
`comfyui_v26/` beside it, mirroring `scripts/install_comfyui_flux2.sh`.

Ports in use: 8188 prod ComfyUI · 8189 flux2 · 9000 MCP · 7860 A1111 → use **8190**.

## Install checklist (mirror `install_comfyui_flux2.sh`)

1. Clone ComfyUI to `comfyui_v26/`, `git checkout` the newest **v0.26.x** tag
   (pin, do not track master — preserves isolation).
2. `python3 -m venv .venv`; torch/torchvision/torchaudio from the cu121 index
   (same Ampere-OK build as flux2); `pip install -r requirements.txt`.
3. Copy `configs/comfyui/extra_model_paths.yaml` so the instance reuses the
   shared `models/` dir.
4. Custom nodes into `comfyui_v26/custom_nodes/`:
   - `city96/ComfyUI-GGUF` (int8/GGUF loaders — needed by Krea int8, Bernini, LTX int8)
   - `neuregex/ComfyUI-BerniniR`
   - `Lightricks/ComfyUI-LTXVideo`
   - `PozzettiAndrea/ComfyUI-DepthAnythingV3`
   - Krea 2 needs no custom node (core partner nodes in v0.26.0)
5. Launch: `.venv/bin/python main.py --listen --port 8190`.

The only structural additions vs the flux2 script are the explicit version pin
and the custom-node block (FLUX.2 was core-native, so flux2 needed neither).

## Per-item

| Item | Source | sm_86 24 GB path | Custom node | models.yaml |
|---|---|---|---|---|
| **Krea 2 Turbo** (12B T2I) | `krea/Krea-2-Turbo`, `Comfy-Org/Krea-2` | **int8** (~12 GB); not BF16 (24.76 GiB), not fp8_scaled | ComfyUI-GGUF | yes |
| **Depth Anything 3** (depth preproc) | `PozzettiAndrea/ComfyUI-DepthAnythingV3` | fp16, trivial | the node itself | no (node auto-downloads) |
| **Bernini-R 1.3B** (video editor) | `bytedance/Bernini`, `neuregex/Bernini-1.3B-ComfyUI` (~2.6 GB) | fp8/GGUF, well under ceiling | ComfyUI-BerniniR + GGUF | yes |
| **LTX-2.3** (22B audio+video) | `Lightricks/LTX-2.3-fp8`, `Lightricks/ComfyUI-LTXVideo` | **int8** or mxfp8_block32, run solo + offload; fp8_scaled is a hard no | ComfyUI-LTXVideo + GGUF | yes |

Targets under shared `models/`: transformers → `diffusion_models/`, encoders →
`text_encoders/`, VAEs → `vae/`. Bernini-R reuses the installed WAN UMT5-XXL
encoder (confirm the on-disk filename matches what the node expects; symlink if
not).

## VRAM coexistence

The 3090 cannot meaningfully co-load two heavy DiTs. LTX-2.3 (int8 ~22 GB) must
run **solo** — same discipline as WAN (confirm `nvidia-smi` near-empty first).
Krea 2 (int8 ~12 GB + Qwen3-VL encoder) is effectively solo in practice.
Bernini-R (~2.6 GB) and Depth Anything 3 (sub-GB) are light. Never run prod
(8188), flux2 (8189), and v26 (8190) heavy jobs concurrently — one heavy GPU
consumer at a time.

## Recommended order (lowest-risk / highest-value first)

1. Stand up the v0.26.x instance + ComfyUI-GGUF; verify it boots clean on 8190
   against shared `models/`.
2. **Krea 2 Turbo (int8)** — highest value, only GGUF as extra dep; validates the box.
3. **Depth Anything 3** — tiny, immediate depth-ControlNet preprocessor upgrade.
4. **Bernini-R 1.3B** — small, reuses UMT5; validate the edit workflow.
5. **LTX-2.3 (int8)** — most VRAM-intensive and finicky on sm_86; do last, solo.

## Open questions to resolve at install time

- LTX-2.3: `Lightricks/LTX-2.3-fp8` is confirmed; pin the exact **int8** (or
  mxfp8_block32) checkpoint repo + size before cataloguing. 22B int8 ≈ 22 GB
  weights alone — expect `--reserve-vram`/offload tuning.
- Krea 2 vendor "16 GB" is a min-VRAM claim, not file size (BF16 = 24.76 GiB);
  plan for int8.
- Bernini-R: determine whether v0.26.x core nodes suffice or the custom node is
  still required for the bundle's task_type/guidance_mode selection.
- Confirm the newest stable v0.26.x patch tag, and that its `requirements.txt`
  torch minimum still has cu121 Ampere wheels.
- Disk: the four families add ~35–40 GB to shared `models/` (volume currently
  has headroom; re-check before pulling).

Sources: [krea/Krea-2-Turbo](https://huggingface.co/krea/Krea-2-Turbo) ·
[bytedance/Bernini](https://github.com/bytedance/Bernini) ·
[neuregex/ComfyUI-BerniniR](https://github.com/neuregex/ComfyUI-BerniniR) ·
[Lightricks/LTX-2.3-fp8](https://huggingface.co/Lightricks/LTX-2.3-fp8) ·
[ComfyUI-DepthAnythingV3](https://github.com/PozzettiAndrea/ComfyUI-DepthAnythingV3) ·
[ComfyUI changelog](https://docs.comfy.org/changelog) ·
[LTX-2.3 models by VRAM](https://ltxworkflow.com/models).

## Validation status (instance on v0.26.2, RTX 3090 / sm_86)

Instance built by `scripts/install_comfyui_v26.sh`, boots on port 8190. Custom
nodes import clean: ComfyUI-GGUF, ComfyUI-BerniniR, ComfyUI-DepthAnythingV3.

- **Krea 2 Turbo: WORKING via `fp8_scaled`.** Generates 1024² in 8 steps. Key
  correction to the original quant plan: fp8 *loads and runs* on sm_86 because
  comfy dequantizes fp8->bf16 when `supports_fp8_compute()` is False (it is, on
  sm_86) — there is no fp8 speedup, but it works. The `int8_convrot` build does
  NOT load on v0.26.2 (`int8_tensorwise` is absent from `comfy/quant_ops.py`
  QUANT_ALGOS — needs a newer core), and the krea2-arch GGUF does NOT load
  (`ComfyUI-GGUF` IMG_ARCH_LIST has no `krea2`). Catalog updated to fp8_scaled.
- **LTX-2.3: dropped.** The installed Lightricks node is checkpoint-based (needs
  the all-in-one `ltx-2.3-22b-dev-fp8` checkpoint + a gemma via
  `LTXAVTextEncoderLoader`), not the separate-GGUF component set first scoped. The
  fp8 checkpoint is 29 GB (exceeds 24 GB, offload-only) and its native audio+video
  overlaps the installed Ovi — not worth the cost on this rig. Catalog entries and
  the ComfyUI-LTXVideo node removed.
- **Bernini-R, Depth Anything 3: nodes import; end-to-end validation pending.**
