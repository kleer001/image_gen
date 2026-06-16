# TODO — unverified items

Things that could not be verified from the cloud session (HuggingFace and most
hosts are blocked by the environment's network policy, and ComfyUI is not
running here). Verify these on the actual rig before relying on them. Each item
notes the file it affects and how to confirm it.

## WAN 2.1 VACE — catalog entry (`models.yaml`)

- [x] **Exact fp8 filename + size.** Confirmed: `Wan2_1-VACE_module_14B_fp8_e4m3fn.safetensors`
      exists on `Kijai/WanVideo_comfy` and is on disk at 2.84 GB. The catalog filename is
      correct; `size: 0` retained (installer treats any non-empty file as complete).
      Official bf16 source repo: <https://huggingface.co/Wan-AI/Wan2.1-VACE-14B>.
- [ ] **License/usage** — Apache-2.0 per the model card; re-confirm before redistribution.

## VACE reference-to-video workflow (`scaffolds/wan_vace_r2v.json`)

This is a SCAFFOLD adapted by hand from `workflows/wan22_i2v_a14b.json`. It lives
in `scaffolds/` (not `workflows/`) on purpose so the MCP server does **not**
auto-register it until validated. Open it in the ComfyUI graph editor with
ComfyUI-WanVideoWrapper installed and reconcile each item below:

- [x] **Model loading path.** Reconciled against wrapper `df8f3e4` (2026-02-22):
      the VACE module is NOT a standalone model. Fixed — the scaffold now loads the
      base `Wan2_1-T2V-14B_fp8_e4m3fn.safetensors` in `WanVideoModelLoader` and
      attaches the VACE module via a `WanVideoVACEModelSelect` node into the loader's
      `extra_model` input (the `vace_model` fn-param is legacy, not an exposed input).
      NOTE: the base T2V model was missing from disk (only the VACE module was) — now
      cataloged in `models.yaml` and downloading from `Kijai/WanVideo_comfy`.
- [x] **`WanVideoVACEEncode` input names.** Verified against the installed node:
      required `vae, width, height, num_frames, strength, vace_start_percent,
      vace_end_percent`; optional `input_frames, ref_images, input_masks,
      prev_vace_embeds, tiled_vae`; output 0 = `vace_embeds` (`WANVIDIMAGE_EMBEDS`).
      The scaffold's R2V wiring (vae, ref_images, width, height, num_frames, strength,
      vace_start/end, tiled_vae) matches; `input_frames`/`input_masks` correctly omitted.
- [x] **Sampler conditioning input.** Verified: `WanVideoSampler.image_embeds` takes
      `WANVIDIMAGE_EMBEDS`, exactly what `WanVideoVACEEncode` emits. The scaffold's
      `image_embeds: ["89", 0]` wiring is correct.
- [x] **Sampler settings.** Switched off the 25-step placeholder: the workflow now
      runs the lightx2v CFG-step distill LoRA (`WanVideoLoraSelect` strength 1.0 ->
      loader `lora`) at `steps: 6, cfg: 1.0, shift: 8`. Validated render: ~3m16s for
      832x480/49f on the 3090 (cfg 1 = single forward pass per step), cleaner output
      than the 25-step baseline.
- [x] **Removed `WanVideoTorchCompileSettings`.** torch.compile/inductor emits fp8
      kernels that fail on this card (RTX 3090 / sm_86 < 89). Eager fp8 runs fine.
- [x] **Promotion.** Done — `scaffolds/wan_vace_r2v.json` -> `workflows/wan_vace_r2v.json`
      (`_scaffold` key stripped), `scripts/video_vace.py` `WORKFLOW_FILE` repointed.
      NOTE: ComfyUI was NOT restarted (MCP server isn't running this session; the driver
      reads the workflow over the HTTP API directly). Run `imggen stop && imggen` when
      MCP-based `run_workflow("wan_vace_r2v")` access is wanted.

## VACE driver (`scripts/video_vace.py`)

- [x] Validated end-to-end against a live ComfyUI: reference upload, prompt/dims/seed
      patching, single-sampler seed, ref_images wiring, and clip output all confirmed.
      Also added the missing preflight + freeze-guard arm (mirroring video_shot.py).

## Video post chain (`workflows/video_post_upscale_interp.json` + `scripts/video_post.py`)

ESRGAN frame upscale + RIFE interpolation — the OSS substitute for Topaz Video AI.
VALIDATED + PROMOTED this session. Smoke test: a VACE clip (832×480/49f/16fps)
→ 1664×960/97f/32fps in one pass; upscaled frame clean.

- [x] **ComfyUI-Frame-Interpolation** loads; `rife47.pth` (20.4 MB) auto-downloads
      on first run (first GitHub endpoint 404s, falls back to the Fannovel16 release).
- [x] **`RIFE VFI` node schema.** class_type `RIFE VFI` (with space) confirmed.
      Live node has extra REQUIRED inputs the scaffold lacked: `dtype` (float32),
      `torch_compile` (**false** — fp8 compile fails on sm_86), `batch_size` (1);
      `scale_factor`/`ckpt_name` are combos (`rife47.pth` is a valid option). All added.
- [x] **`VHS_LoadVideo` schema + video input path.** Confirmed: `video` is a combo
      of input-dir files; the driver stages the clip into `comfyui/input/` and passes
      the bare filename; output 0 is the IMAGE batch.
- [x] **Upscale → interpolate order / VRAM.** Documented order (4x upscale → downscale
      → RIFE) ran fine; GPU stayed light (~2 GB) — no need to swap order on this rig.
- [x] **Target dims.** Default `1664x960` = 2x of 832×480; matched the VACE clip.
- [x] **Promotion.** Done — moved to `workflows/`, `_scaffold` stripped, `WORKFLOW_FILE`
      repointed. ComfyUI not restarted (no MCP this session; driver uses the HTTP API).

## Radar follow-ups (`radar/2026-06-03.md`)

- [ ] **Qwen-Image-2.0 (7B)** — open weights were **not** released as of the sweep.
      Re-check <https://huggingface.co/Qwen/Qwen-Image> for a 2.0 weight drop before
      cataloguing.
- [ ] **LTX-2.3 24 GB fit** — vendor/community guides conflict (one claims 8 GB
      with heavy optimization, another pushes 32 GB for fp8 "production quality").
      Confirm the real 24 GB ceiling/quality tradeoff with the fp8 + distilled
      checkpoint on the rig before committing to it.

## DWPose walking animation — scaffold (`scaffolds/dwpose_walk_animatediff.json` + `scripts/pose_walk.py`)

Option-1 pipeline for posing consistent characters in simple walking animations:
**driving walk video → DWPose → OpenPose ControlNet → AnimateDiff (SD1.5), with
IPAdapter carrying the character's identity.** Light enough for a 24GB card, no
WAN-style hardware red-flag. Authored from the cloud session (no GPU/ComfyUI
there), so every node schema below is UNVERIFIED. The workflow lives in
`scaffolds/` so the MCP does not auto-register it until validated.

### 1. Install custom nodes (into `comfyui/custom_nodes/`)

- [ ] **ComfyUI-AnimateDiff-Evolved** (`ADE_*` nodes) — motion module / temporal coherence.
      `git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved`
      (also required by the existing `workflows/animatediff_txt2vid.json`).
- [ ] **comfyui_controlnet_aux** (`DWPreprocessor`) — DWPose skeleton extraction.
      `git clone https://github.com/Fannovel16/comfyui_controlnet_aux` then
      `pip install -r requirements.txt` in the comfyui venv (onnxruntime / mmpose deps).
- [ ] **ComfyUI_IPAdapter_plus** (`IPAdapterUnifiedLoader`, `IPAdapter`) — identity lock.
      `git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus`.
- [ ] **VideoHelperSuite** (`VHS_LoadVideo`, `VHS_VideoCombine`) — already present (the
      video drivers use `VHS_VideoCombine`); confirm `VHS_LoadVideo` loads too.
- [ ] *(optional upgrade)* **ComfyUI-Advanced-ControlNet** — if stock
      `ControlNetApplyAdvanced` mis-maps the per-frame pose batch onto the latent
      batch, swap node 12 for `ControlNetLoaderAdvanced` + `ACN_AdvancedControlNetApply`.

### 2. Install weights (catalog entries already added to `models.yaml`)

- [ ] `python3 scripts/install_models.py --only checkpoints`  → `v1-5-pruned-emaonly.safetensors`
      (⚠ the old `runwayml/stable-diffusion-v1-5` repo was deleted; catalog points at the
      community mirror `stable-diffusion-v1-5/stable-diffusion-v1-5` — confirm it resolves,
      or swap in a stronger SD1.5 character checkpoint for better faces/hands).
- [ ] `python3 scripts/install_models.py --only controlnet`   → `control_v11p_sd15_openpose_fp16.safetensors`
- [ ] `python3 scripts/install_models.py --only ipadapter`    → `ip-adapter-plus_sd15.safetensors`
- [ ] `python3 scripts/install_models.py --only clip_vision`  → `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors`
- [ ] `python3 scripts/install_models.py --only animatediff`  → `mm_sd_v15_v3.safetensors` (already catalogued; install if absent)
- [ ] **DWPose detector weights** auto-download on first `DWPreprocessor` run into
      `comfyui/custom_nodes/comfyui_controlnet_aux/ckpts` (`yolox_l.onnx`,
      `dw-ll_ucoco_384_bs5.torchscript.pt`). Verify the rig has network access for that
      first run; if the filenames differ from the workflow's `bbox_detector` /
      `pose_estimator` values, update node `3`.

### 3. Config

- [x] Added `ipadapter: ipadapter/` to `configs/comfyui/extra_model_paths.yaml` (was missing).
- [ ] Propagate it: re-run the relevant install script (copies the config into
      `comfyui/extra_model_paths.yaml`), or add the line by hand if ComfyUI is already
      installed. Without it, `models/ipadapter/` won't be discovered.

### 4. Verify node schemas (drift between releases — reconcile in the graph editor)

- [ ] **`DWPreprocessor`** input names (`detect_hand/body/face`, `resolution`,
      `bbox_detector`, `pose_estimator`) and the exact detector filenames.
- [ ] **`VHS_LoadVideo`** — output 0 is the IMAGE batch; `frame_load_cap` /
      `select_every_nth` / `force_rate` behave as assumed; it reads from `comfyui/input/`
      by bare filename (the driver stages the clip there).
- [ ] **`IPAdapterUnifiedLoader`** preset string — scaffold uses `"PLUS (high strength)"`;
      confirm it maps to `ip-adapter-plus_sd15` + the CLIP-ViT-H encoder. Confirm the
      apply node is `IPAdapter` (inputs `model, ipadapter, image, weight, start_at,
      end_at, weight_type`) vs `IPAdapterAdvanced` in the installed version.
- [ ] **Batch match** — `EmptyLatentImage.batch_size` MUST equal the DWPose frame count
      (= VHS `frame_load_cap`). The driver ties both to `num_frames`; the driving clip must
      have ≥ `num_frames × select_every_nth` frames or the batches mismatch.
- [ ] **`ADE_AnimateDiffLoaderGen1`** `beta_schedule: autoselect` is valid for the v3
      motion module; tune `context_length`/`context_overlap` for clips > 16 frames.

### 5. Smoke test

- [ ] Drop a short walk clip at `./drive/walk_loop.mp4` and a character portrait at
      `./refs/zara.png` (neutral-gray bg + soft key, per the character-sheet craft in
      CLAUDE.md), then: `python3 scripts/pose_walk.py examples/pose_walk.example.yaml`.
      Iterate `ipadapter_weight` (identity 0.6→1.0) vs `controlnet_strength` (pose).

### 6. Promotion (once it renders correctly)

- [ ] Move `scaffolds/dwpose_walk_animatediff.json` → `workflows/`, strip the `_scaffold`
      key, restart (`imggen stop && imggen`) so the MCP auto-registers it.
- [ ] Repoint `WORKFLOW_FILE` in `scripts/pose_walk.py` to the `workflows/` path.
- [ ] Add a `## Pose-driven animation` capability note + INDEX.md rows for the new
      models, and consider a gait/motion LoRA pass via `/model-radar`.
