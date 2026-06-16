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

## Video post chain (`scaffolds/video_post_upscale_interp.json` + `scripts/video_post.py`)

ESRGAN frame upscale + RIFE interpolation — the OSS substitute for Topaz Video AI.
Scaffold lives in `scaffolds/` so the MCP does not auto-register it. The ESRGAN
half uses installed models (`4x-UltraSharp.pth` etc.); the RIFE half does not yet
exist on the rig.

- [x] **Install ComfyUI-Frame-Interpolation.** Installed at
      `comfyui/custom_nodes/ComfyUI-Frame-Interpolation`. Still verify the node loads
      and the RIFE checkpoint downloads on first run (see schema item below).
- [ ] **`RIFE VFI` node schema.** Scaffold assumes class_type `RIFE VFI` (with a
      space) and inputs `frames, ckpt_name, clear_cache_after_n_frames, multiplier,
      fast_mode, ensemble, scale_factor`. Verify against the installed node — input
      names and the RIFE checkpoint name (`rife47.pth`) drift between releases.
- [ ] **`VHS_LoadVideo` schema + video input path.** Scaffold sets `video` to a
      bare filename and the driver stages the clip into `comfyui/input/`. Confirm
      VHS_LoadVideo reads from the input dir by filename (vs. needing an upload
      endpoint) and that output 0 is the IMAGE batch in this VHS version.
- [ ] **Upscale → interpolate order / VRAM.** Scaffold follows the documented
      order (4x upscale → downscale to target → RIFE). Interpolating already-upscaled
      frames is VRAM-heavy; swapping to interpolate-then-upscale is lighter but does
      more upscale work. Pick per rig headroom.
- [ ] **Target dims.** Default `1664x960` = exact 2x of an 832x480 render
      (aspect-preserving). If you render at other dims, set `--width/--height` to
      2x of those, or the `crop: disabled` ImageScale will stretch.
- [ ] **Promotion.** After it runs clean, move
      `scaffolds/video_post_upscale_interp.json` → `workflows/`, restart
      (`imggen stop && imggen`), repoint `WORKFLOW_FILE` in `scripts/video_post.py`,
      and strip the `_scaffold` key.

## Radar follow-ups (`radar/2026-06-03.md`)

- [ ] **Qwen-Image-2.0 (7B)** — open weights were **not** released as of the sweep.
      Re-check <https://huggingface.co/Qwen/Qwen-Image> for a 2.0 weight drop before
      cataloguing.
- [ ] **LTX-2.3 24 GB fit** — vendor/community guides conflict (one claims 8 GB
      with heavy optimization, another pushes 32 GB for fp8 "production quality").
      Confirm the real 24 GB ceiling/quality tradeoff with the fp8 + distilled
      checkpoint on the rig before committing to it.
