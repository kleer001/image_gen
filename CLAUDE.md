# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Configuration, scripts, workflows, and model catalog for a local image generation stack. The actual tools (ComfyUI, A1111, comfyui-mcp-server) are cloned into gitignored subdirectories and managed separately. Only configs, scripts, workflows, and `models/MODELS.md` are tracked.

## Running the Stack

```bash
imggen          # start ComfyUI + MCP server, open browser
imggen stop     # kill both
imggen status   # check what's running
```

`imggen` is a bash function in `~/.bash_aliases.sh`. It:
1. Starts ComfyUI (port 8188) from `comfyui/.venv`
2. Waits for ComfyUI to be healthy
3. Starts comfyui-mcp-server (port 9000) from `comfyui-mcp-server/.venv`
4. Opens Firefox at `http://127.0.0.1:8188`

A1111 is independent: `cd automatic1111 && ./webui.sh` (port 7860).

## Generator Environments

Multiple isolated generators share one `models/` dir. Production ComfyUI stays
pinned and frozen; each model family needing a newer engine gets its own pinned
instance. One heavy GPU job at a time across all of them. Full detail (install,
VRAM, quant paths, how to add one) in [`ENVIRONMENTS.md`](ENVIRONMENTS.md).

| Env | Port | Engine | For |
|---|---|---|---|
| `comfyui/` | 8188 | ComfyUI v0.17.0 | Production: Flux.1, SDXL/Illustrious, Kontext, WAN/Hunyuan/Ovi |
| `comfyui-mcp-server/` | 9000 | — | MCP layer over production |
| `automatic1111/` | 7860 | A1111 | Standalone SDXL webui |
| `comfyui_flux2/` | 8189 | ComfyUI v0.24.0 | FLUX.2 Klein 9B (`flux2_*.py`) |
| `ideogram4_env/` | — | diffusers venv | Ideogram 4.0 (`ideogram4_t2i.py`) |
| `comfyui_v26/` | 8190 | ComfyUI v0.26.2 | Krea 2 Turbo, Bernini-R, Depth Anything 3 |
| `comfyui_h3/` | 8191 | ComfyUI v0.35.0 (cu130) | MiniMax H3 video+audio (`h3_t2v.py`) |

A `SessionStart` hook (`scripts/check_envs_documented.py`) warns if a top-level
generator dir is missing from `ENVIRONMENTS.md`.

## INDEX.md Auto-Sync

`INDEX.md` is kept current automatically:

- **Claude Code hook** — `scripts/sync_index.py` runs at the end of every Claude session (Stop hook in `.claude/settings.json`)
- **Filesystem watcher** — `scripts/watch_models.sh` uses `inotifywait` to fire the same script the moment a download finishes or a file is deleted; start it alongside the stack:

```bash
nohup bash scripts/watch_models.sh >> /tmp/watch_models.log 2>&1 &
```

`sync_index.py` behaviour:
- Removes table rows for files no longer on disk
- Appends new files to an `## Unindexed` section (filename + size, `TODO` for metadata)
- Never touches existing annotated rows
- Updates the `Last updated` timestamp

## Updating the Pipeline

To keep the stack at the state of the art, run a periodic **update sweep**:
digest the current repo state, then scan the open-weights landscape for breakthroughs in
**models, LoRAs, and workflows** that improve what the repo already does.

- **Runbook:** [`UPDATE.html`](UPDATE.html) — the authoritative, Claude-facing instruction page
  (HTML by design, for richer structure as LLM context). It is **report-only**: the sweep writes a
  dated digest to `radar/<YYYY-MM-DD>.md` and never downloads, installs, or edits the catalog.
- **Invoke:** the `/model-radar` skill, or open `UPDATE.html` and follow it (equivalent).
- **Cadence:** ~weekly. A `SessionStart` hook runs `scripts/check_sweep_due.py`, which nudges when
  the newest digest is > 7 days old. For unattended runs, install `scripts/update_sweep.sh` as a
  weekly cron on the rig.

## Installing from Scratch

```bash
./scripts/install_comfyui.sh       # clone + venv + PyTorch cu121 + requirements
./scripts/install_a1111.sh         # clone + link webui-user.sh
./scripts/install_comfyui_mcp.sh   # clone + venv + mcp/requests/Pillow
```

## Architecture

**Shared model directory** — both ComfyUI and A1111 read from `models/`:
- `models/checkpoints/` — SDXL-based `.safetensors` (e.g. Illustrious XL, SVD)
- `models/diffusion_models/` — Flux and video transformers (Flux.1-dev, Flux.1-Kontext-dev, HunyuanVideo, WAN 2.2)
- `models/text_encoders/` — Flux encoders (T5-XXL fp8, CLIP-L) + HunyuanVideo/WAN encoders
- `models/vae/` — VAEs per model family
- `models/loras/` — Flux.1-dev LoRAs (anime, illustration, cartoon, graphic design, film/storyboard, film noir)
- `models/controlnet/` — Flux and SDXL ControlNet models
- `models/upscale_models/` — ESRGAN upscalers
- `models/animatediff_models/` — AnimateDiff motion module
- `models/animatediff_motion_lora/` — Camera motion LoRAs (zoom, pan, tilt)
- `models/MODELS.md` — download catalog with sources and install notes (not authoritative for installed state)

**Config wiring:**
- `configs/comfyui/extra_model_paths.yaml` → copied to `comfyui/extra_model_paths.yaml` by install script; tells ComfyUI to use the shared `models/` dir
- `configs/a1111/webui-user.sh` → copied to `automatic1111/webui-user.sh`; sets `--ckpt-dir`, `--lora-dir`, etc.

**Two ways to drive the stack:**

1. **Direct ComfyUI HTTP API** (port 8188) — works from any process on the machine: another repo's script, cron, a shell pipeline, a different Claude Code session. No MCP load required. See [`API_USAGE.md`](API_USAGE.md) for curl + Python recipes. Prefer this for cross-repo use.
2. **MCP server** (port 9000) — only reachable when Claude Code starts in a directory whose `.mcp.json` lists the server. Adds workflow auto-discovery, defaults management, and asset registry on top of the raw API. Use this when you want those conveniences inside the current Claude Code session.

To use the MCP from another Claude Code project, add this to that project's `.mcp.json` (start `imggen` from this repo first):

```json
{
  "mcpServers": {
    "comfyui": {
      "type": "streamable-http",
      "url": "http://127.0.0.1:9000/mcp"
    }
  }
}
```

**Custom nodes required for some models:**
- XLabs ControlNets (`flux-depth-controlnet-v3`, `flux-canny-controlnet-v3`, union models) require the [x-flux-comfyui](https://github.com/XLabs-AI/x-flux-comfyui) custom node installed in `comfyui/custom_nodes/`
- HunyuanVideo requires [ComfyUI-HunyuanVideoWrapper](https://github.com/kijai/ComfyUI-HunyuanVideoWrapper)
- WAN 2.2 requires [ComfyUI-WAN-Wrapper](https://github.com/kijai/ComfyUI-WanWrapper)
- AnimateDiff requires [ComfyUI-AnimateDiff-Evolved](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved)

**`models.yaml`** — machine-readable model catalog used by `scripts/install_models.py`. Each entry has `url`, `dest`, `size`, `auth`, `base`, `purpose`, and `date`. Add new models here to make them installable via the script.

## Generating Images via MCP

(For the no-MCP path, see [`API_USAGE.md`](API_USAGE.md).)

Run `imggen status`; if down, run `imggen` (~30s for both ports healthy). Claude Code connects via `.mcp.json` once the stack is up.

Entry point: `run_workflow(workflow_id, overrides={...})`. `workflow_id` is the filename stem from `workflows/`. Override values must be real JSON types (int, float, str) — stringified numbers fail pydantic validation. Workflows without `PARAM_*` placeholders ignore overrides and run with baked-in defaults.

Tools:
- `run_workflow(workflow_id, overrides=None)`, `list_workflows`, `list_models`
- `get_defaults` / `set_defaults` — baseline image/audio/video settings
- `get_queue_status`, `get_job(prompt_id)`, `cancel_job(prompt_id)`
- `list_assets`, `get_asset_metadata(asset_id)`, `view_image(asset_id)`

Each workflow JSON is also auto-registered as a tool named after its filename.

**Adding a workflow:** in ComfyUI, use **Save (API Format)** to export, drop the JSON in `workflows/`, then restart with `imggen stop && imggen`. The MCP server expects API format; UI-format exports (top-level `nodes`/`links`/`groups`) will crash it.

**Workflow parameters** (placeholder strings inside node inputs):
- `PARAM_PROMPT` — text prompt
- `PARAM_INT_<name>` — integer (e.g. `PARAM_INT_STEPS`)
- `PARAM_FLOAT_<name>` — float (e.g. `PARAM_FLOAT_CFG`)

**Showing results to the user:** after generating, build a small local HTML gallery and open it in the user's default browser — it tightens the feedback loop and dodges terminal-image-rendering quirks. See [`BROWSER_DISPLAY.md`](BROWSER_DISPLAY.md) for the full checklist (use a local HTTP server, not `file://`; stage images in a served dir; one URL printed to the user).

See `INDEX.md` for installed models, trigger words, and LoRA weights.

## Capabilities

**Image generation**
- Text-to-image — Flux.1-dev (high quality), Illustrious XL (anime/illustration)
- Image-to-image — SDXL/Illustrious
- Inpainting / outpainting — Flux and SDXL
- In-context image editing — Flux.1-Kontext-dev (edit by text instruction)
- Style conditioning — Flux Redux (image prompt / style transfer)
- ControlNet — Canny, Depth, Pose for Flux; Pose for SDXL
- LoRA styling — anime, retro anime, illustration, cartoon, Disney, comic, Swiss design, Milton Glaser, graffiti logo, film storyboard, film noir, cinematic
- Storyboards — multi-panel sheet with character identity locked across panels via Flux Kontext (see `## Storyboards` below)

**FLUX.2 Klein 9B** — runs on the isolated `comfyui_flux2/` instance (port 8189), not the production MCP stack (v0.17 ComfyUI can't run FLUX.2); see `scripts/install_comfyui_flux2.sh`. Distilled 9B, 4-step.
- Text-to-image — `scripts/flux2_klein.py`
- Reference-driven editing / compositing — `scripts/flux2_klein_edit.py` (one or more `--ref` images via chained ReferenceLatent)
- Character reference sheets — `scripts/flux2_character_sheet.py` (identity-locked turnaround: front → side profile → back → face close-up; the distilled edit snaps front↔profile, so intermediate 3/4 angles need the base 9B model + more steps)

**Video generation**
- Image-to-video — WAN 2.2 I2V (high/low noise variants), SVD-XT (25 frames)
- Text-to-video — HunyuanVideo 1.5 (720p FP8), AnimateDiff (loop-based, SD1.5)
- Camera motion control — AnimateDiff camera LoRAs: zoom in/out, pan left/right, tilt up/down

**Post-processing**
- Upscaling — 4x-UltraSharp (general), RealESRGAN x4plus (realistic), 4x-AnimeSharp (anime)

**Installed model inventory:** [`INDEX.md`](INDEX.md) — authoritative for on-disk state (sizes, trigger words, LoRA weights).

## Reference images

`refs/` and `plates/` are kept in the tree but their contents are not tracked —
reference photos, start frames and plates are the operator's own, and third
party imagery carries licence and likeness terms a public repo cannot pass on.
A fresh clone has empty directories.

Every tracked example therefore names a file that has to be supplied before it
will run:

| Example | Expects |
|---|---|
| `examples/h3_ref2v_benchmark.yaml` | `refs/h3/person.jpg`, `object.jpg`, `place.jpg` |
| `examples/h3_circus.yaml`, `examples/h3_circus_pullout.yaml` | `refs/h3/person.jpg` |
| `examples/storyboard.example.yaml` | `refs/wanderer.png` (optional; without it panel 1 is seeded from the prompt) |
| `examples/vace_shots.example.yaml` | `refs/zara_sheet.png` |
| `examples/pose_walk.example.yaml` | `refs/zara.png`, `refs/grandpa.png` |
| `examples/video_shots.example.yaml` | `plates/car_interior.png`, `plates/neon_street.png` |

Drop in any image at those paths, or edit the path in the copy of the example
you are running. Where a prompt also describes its reference in words — the
h3 examples restate identity because reference tags alone drift — edit the
description to match what was actually supplied, or the words fight the image.

Character references want the sheet craft in `## Storyboards` below: solid
neutral-gray background, soft directional key light.

`workflows/qwen_image_edit_multiangle.json` carries a `LoadImage` filename as
its baked default, the way every exported ComfyUI graph does. Drivers patch it
per run, so the name in the JSON is inert.

## Storyboards

Multi-panel storyboards with character/style consistency across panels.

**Driver:** `scripts/storyboard.py <shotlist.yaml>` reads a shot list, renders each panel via the ComfyUI HTTP API, builds an HTML sheet (CSS grid), serves it on a free port from 8765, and opens it in the browser. Format and defaults are documented in the script's module docstring.

**Workflows:**
- `workflows/storyboard_seed.json` — Flux + storyboard LoRA, text→image. Used for panel 1 when no reference image is supplied.
- `workflows/storyboard_panel.json` — Flux Kontext + storyboard LoRA, ref+text→image. Used for panels 2..N (and all panels when a reference is supplied), so the wanderer / character / style read as the same across the sheet.

**Identity locking** is via Kontext (in-context editing), not PuLID/InstantCharacter — those were evaluated and rejected (PuLID-Flux is upstream-discontinued; InstantCharacter only ships through StoryDiffusion's non-API-format pipeline).

**Storyboard LoRAs (Flux.1-dev, in `models/loras/`):**
- `StoryboardSketch-Flux.safetensors` — pencil-sketch panels. Trigger: `Storyboard sketch`. Weight 0.7–0.9.
- `Storyboarding-v2-Flux.safetensors` — alt sketch flavor. Trigger: `storyboarding`. Weight 1.0.
- `film-storyboard.safetensors` — colored cinematic In-Context-LoRA, no trigger. Weight 0.8–1.0.

**Aspect ratio quirk:** `width`/`height` in the YAML control panel 1 (the seed). Panels 2..N use `FluxKontextImageScale`, which snaps to Kontext's preferred buckets (square, 1184×880, 1248×832, 1392×752, 1456×720, and portrait flips) based on the **reference image's** aspect — *not* the YAML dims. Net effect: set seed dims to your target aspect (e.g. 1024×576 for 16:9) and every panel follows. Per-shot mixed aspects aren't supported by the current driver.

**Cinematic-depth style suffix:** `storyboard.py` appends `DEFAULT_STYLE_SUFFIX` (soft directional key light, volumetric haze, atmospheric perspective, shallow DOF, no blown highlights) to every panel prompt at render time. This "light the air, not just the subject" convention reads as photographed rather than generated and avoids the blown-out edges that produce plastic faces. Override per-sheet with `style_suffix:` in the shot list (`""` disables). Gallery captions still show your original prompt.

**Character reference sheet craft (for the `reference:` image you feed the driver):** generate the character on a **solid neutral-gray background, not white** — pure white kicks light back into the jaw and blows out face edges, baking in glossy/plastic skin that then fights every scene you composite into. Pair gray with **soft directional key light, gentle falloff** (avoid "diffuse/soft lighting" alone — it over-lights). This is a character-sheet convention only; don't force gray backgrounds onto scene panels (that's what the cinematic-depth suffix above is for). For extra skin realism, stack a Flux skin-detailer LoRA (see `radar/` digests) rather than relying on the base model.

## Video delivery

> 🚩 **HARDWARE RED FLAG — WAN video can crash the whole machine.** WAN 2.2 I2V / WAN 2.1 VACE
> load a 14B transformer that, **unquantized** (`base_precision: bf16` + `quantization: disabled`),
> exceeds the 24 GB card and hard-crashes the box (confirmed 2026-06-04). Before running ANY video
> workflow: (1) **confirm with the user** — it can take the machine down; (2) **verify WAN is the
> only heavy GPU job** — `nvidia-smi` should show near-empty VRAM, with no Flux/HunyuanVideo/A1111
> co-loaded (WAN cannot share the GPU); (3) use a **quantized** attention/precision config (fp8
> non-`_scaled`, or install `sageattention`), never bf16/disabled.

Multi-shot video with a browser review gallery, mirroring the storyboard flow.

**Driver:** `scripts/video_shot.py <shotlist.yaml>` reads a shot list, renders each shot via the WAN 2.2 I2V workflow over the ComfyUI HTTP API, builds an HTML `<video>` gallery (CSS grid), serves it on a free port from 8765, and opens it in the browser. Format and defaults are in the script's module docstring; see `examples/video_shots.example.yaml`.

- Each shot needs a **start frame** (`image:`) plus a motion `prompt:`. Image-to-video carries identity/scene from that frame, so render the frame to look how the clip should look (apply the character-sheet + cinematic-depth craft above).
- Unlike the storyboard workflows, `wan22_i2v_a14b.json` has no `PARAM_*` placeholders — the driver patches nodes by `class_type` (prompts on `WanVideoTextEncode`, start frame on `LoadImage`, dims on `ImageResizeKJv2`, length on `WanVideoImageToVideoEncode`, seed on **both** `WanVideoSampler` experts, fps on `VHS_VideoCombine`).
- A cinematic/handheld `style_suffix` is appended to every prompt (`""` disables), echoing the "camera operator life + atmosphere" convention.

**Identity across shots:** WAN I2V locks identity only via the start frame. For true reference-driven / multi-image character locking (the open analog to Seedance-style `@image1..@imageN` conditioning), the migration target is **WAN 2.1 VACE 14B** — catalogued in `models.yaml` (reuses the installed WAN VAE + UMT5 encoder; needs ComfyUI-WanVideoWrapper). Not yet installed; see `radar/` for the rationale.

**Recommended post chain (scaffolded, not yet validated):** WAN renders at 720p → per-frame ESRGAN upscale → **RIFE/FILM frame interpolation** for temporal smoothness (the OSS substitute for Topaz Video AI). Scaffolded in `scaffolds/video_post_upscale_interp.json` + `scripts/video_post.py` (`video_post.py clip.mp4 …` → upscaled/interpolated clip in a browser gallery). RIFE needs a custom node (ComfyUI-Frame-Interpolation) that isn't part of the base stack — install it, then validate per `TODO.md` and promote the scaffold into `workflows/`.

## Pose-driven walking animation (scaffolded, not yet validated)

Posing a **consistent character** in a **simple walking animation** from a driving
walk clip: **DWPose → OpenPose ControlNet → AnimateDiff (SD1.5)**, with an
**IPAdapter** carrying identity across frames. The driving video supplies the gait;
the reference image + prompt supply *who* is walking. Chosen over WAN VACE (the
heavier, red-flagged SOTA path) and per-frame Flux (which flickers) because it's the
lightest path with the best temporal coherence for short walk cycles — runs on a
24GB card with no WAN-style hardware hazard.

**Driver:** `scripts/pose_walk.py <shotlist.yaml>` — per shot takes a driving
`video:` + identity `reference:` + motion `prompt:`; DWPose extracts the skeleton,
the OpenPose ControlNet drives limbs per frame, AnimateDiff keeps it coherent, and
the IPAdapter locks the character. Mirrors the storyboard/`video_shot` flow (HTTP
API + browser gallery); patches the workflow by `class_type` (and by `_meta` title for
the two prompt nodes). See `examples/pose_walk.example.yaml`.

**Workflow:** `scaffolds/dwpose_walk_animatediff.json` (in `scaffolds/`, not
`workflows/`, so the MCP doesn't auto-register it until validated). Needs three
custom nodes (ComfyUI-AnimateDiff-Evolved, comfyui_controlnet_aux, ComfyUI_IPAdapter_plus)
and the SD1.5 + OpenPose-CN + IPAdapter weights (catalogued in `models.yaml`). Authored
from the cloud session, so node schemas are **unverified** — install, validate, and
promote per the `## DWPose walking animation` checklist in `TODO.md`. Tune
`ipadapter_weight` (identity) against `controlnet_strength` (pose). For better faces,
swap the base SD1.5 checkpoint for a stronger character model.

## LoRA Notes

Most LoRAs in `models/loras/` target **Flux.1-dev**. Exceptions: `Sketchy-Illustrious.safetensors` targets Illustrious XL; AnimateDiff camera LoRAs in `models/animatediff_motion_lora/` target SD1.5+AnimateDiff. See `INDEX.md` for per-LoRA trigger words and recommended weights.

## Downloading Models

Use `hf download` for HuggingFace (token at `~/.cache/huggingface/token`). Use `wget` with CivitAI API token (`$CIVITAI_API_KEY`) for CivitAI:

```bash
wget -O models/loras/name.safetensors \
  "https://civitai.com/api/download/models/{versionId}?token=${CIVITAI_API_KEY}"
```

Flux.1-dev is a gated model — requires accepting the license at huggingface.co/black-forest-labs/FLUX.1-dev before downloading.
