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

- [ ] **Model loading path.** Scaffold loads the VACE module directly via
      `WanVideoModelLoader`. Some wrapper versions instead need the base WAN 2.1
      **T2V** model loaded, with the VACE module attached through a separate
      `WanVideoVACEModelSelect` node feeding a `vace_model` input. Confirm which
      pattern the installed wrapper uses and rewire if needed.
- [ ] **`WanVideoVACEEncode` input names.** Scaffold assumes inputs
      `vae, ref_images, width, height, num_frames, strength, vace_start_percent,
      vace_end_percent, tiled_vae` and output 0 = `vace_embeds`. Verify the exact
      input socket names/order against the installed node (they have drifted
      between wrapper releases). For pure R2V only `ref_images` is wired; `input_frames`
      / `input_masks` (V2V / inpaint) are intentionally omitted.
- [ ] **Sampler conditioning input.** Scaffold feeds VACE embeds into
      `WanVideoSampler.image_embeds` (`["89", 0]`). Confirm the sampler takes
      vace_embeds there vs. a dedicated input in this wrapper version.
- [ ] **Sampler settings.** VACE 2.1-14B is a **single** model (not a 2.2-style
      high/low MoE), so the scaffold uses one sampler with `steps: 25, cfg: 6,
      shift: 8`. Tune these for VACE — values are placeholders.
- [ ] **Promotion.** Once it renders correctly, move
      `scaffolds/wan_vace_r2v.json` → `workflows/wan_vace_r2v.json` and restart
      (`imggen stop && imggen`) so the MCP auto-registers it. Then update
      `scripts/video_vace.py`: set `WORKFLOW_FILE` to the `workflows/` path.
- [ ] Strip the `_scaffold` metadata key when promoting (the driver already
      drops non-node keys at queue time, but a registered workflow should be clean).

## VACE driver (`scripts/video_vace.py`)

- [ ] Python logic is smoke-tested (meta-key stripping, node patching, single
      sampler seed, ref_images wiring), but it has **not** been run end-to-end
      against a live ComfyUI. Validate once the workflow above is confirmed.

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
