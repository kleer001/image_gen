# SHEET_TODO.md — Integrate VNCCS (Visual Novel Character Creation Suite)

Integration plan for wiring [`AHEKOT/ComfyUI_VNCCS`](https://github.com/AHEKOT/ComfyUI_VNCCS)
(v2.1.0) into this stack as a first-class capability: **consistent character
sprite sheets for visual novels / games** — base character → clothing sets →
emotion sets → finished sprites → optional LoRA dataset.

This is a checklist + design doc, not the implementation. Work top to bottom;
each task lists the exact file to touch and what to change.

---

## 0. Read this first — the one big caveat

**VNCCS is GUI-driven, not API-driven.** Its core nodes (`VNCCS Character
Creator`, `VNCCS Pose Generator`, `VNCCS Emotion Studio`, `VNCCS Character
Selector`, `Sprite Generator`) carry custom web-UI widgets and stateful
side effects — e.g. the "Create New Character" button provisions the
on-disk character folder, and Emotion Studio uses a visual selection grid.

That collides head-on with how this repo automates ComfyUI:

- `CLAUDE.md` and the MCP server expect **API-format** workflows. UI-format
  exports (top-level `nodes`/`links`/`groups`) **crash the MCP server**.
- `scripts/storyboard.py` and the MCP `run_workflow` path run workflows
  *headless* over the HTTP API with `PARAM_*` placeholder substitution.

**Conclusion (updated after source investigation):** VNCCS is GUI-*first*, but
the pipeline **can run headlessly** — its nodes are almost all pure compute.
Two things stand between you and `/prompt` automation, both solvable (§5.5):

1. The bundled `VN_Step*.json` are **UI-format** (top-level
   `nodes`/`links`/`groups`) and **will crash the MCP server**. Re-export each
   via ComfyUI **Save (API Format)** before placing any in `workflows/`. Do not
   drop the shipped UI-format files in there as-is.
2. One bootstrap step — provisioning a character's folder + config — lives in a
   front-end button (`GET /vnccs/create`), not in any node, so it doesn't fire
   on a `/prompt` POST. Trigger it with a one-line HTTP call or a ~1-line node
   patch, per character.

With those handled, all 5 stages run over the HTTP API on the same no-MCP path
as `scripts/storyboard.py`. Until then, the fastest path to a first sheet is the
**browser at `localhost:8188`**. Full headless recipe + per-stage breakdown in §5.5.

---

## 1. How it fits the existing architecture

| Concern | This repo today | VNCCS need | Action |
|---|---|---|---|
| Base model | Illustrious-XL-v0.1 (SDXL) already installed | "Any Illustrious-based SDXL" | ✅ none — reuse existing checkpoint |
| Model dir | shared `models/` via `configs/comfyui/extra_model_paths.yaml` | adds `ultralytics/`, `sams/` categories | ⚠️ add two new path keys (§2.2) |
| Custom nodes | cloned explicitly in `scripts/install_comfyui.sh` | VNCCS + several transitive node deps | ⚠️ add to install script (§2.1) |
| Model fetch | `models.yaml` → `scripts/install_models.py` | 14 files on VNCCS HF (~7.4 GB) + 3 face detectors elsewhere | ⚠️ add entries (§2.3, §3) |
| Automation | MCP + HTTP API, API-format workflows | UI-format workflows + 1 stateful bootstrap route | ⚠️ headless-capable with tweaks (§5.5) |
| VRAM | RTX 3090 24 GB | tuned for 8 GB (RMBG ≤1408) | ✅ comfortable headroom |
| Output | `outputs/` + `comfyui/output/` (gitignored) | `comfyui/output/VN_CharacterCreatorSuit/<NAME>/{Sheets,Sprites,Lora}` | ✅ none — already gitignored |

VNCCS is SDXL/Illustrious-based, so it does **not** contend with the Flux /
HunyuanVideo / WAN VRAM budget — it's in the same family as the existing
`sdxl_basic` / `controlnet_pose` workflows.

---

## 1.5 Branch selection — decide this first

Investigated `main`, `cleanup`, `CharacterStudio` (2026-05-26). All three carry
an identical README, so the branch differences are code-only.

| Branch | Version | Head | Last commit | vs `main` | Verdict |
|---|---|---|---|---|---|
| `main` | 2.1.0 | `7c3281f` | 2026-01-10 | — | ✅ **clone this** — stable, lean deps |
| `cleanup` | 3.0.0 | `808bab6` | 2026-05-26 | +83 | ⚠️ active next-release; heavy/fragile deps |
| `CharacterStudio` | 2.1.0 | `c7ac927` | 2026-01-20 | +10 | ❌ avoid — stale 3D PoC, vendors MakeHuman |

**Recommendation: clone `main`.** It's the only released line; deps are light
(`torch, numpy, Pillow, opencv-python, huggingface_hub, timm`); a failed import
crashes loudly instead of silently skipping the pack. Untouched since January
but it works. `scripts/install_comfyui.sh`'s `install_node` clones the default
branch (`main`) — so the §2.1 line needs no `-b` flag for this choice.

**`cleanup` (v3.0.0) is the real development line** — 83 commits, a CI test
suite, and new "Control Center" + pipeline nodes (`VNCCS_ControlCenter`,
`CharacterCreatorV2`, `CharacterCloner`, `ClothesDesigner`, `SpriteManager`,
`SubgraphPipeline`, **`vnccs_api`**). Adopt it ONLY if you want v3 features and
can absorb the cost:
- Heavy `requirements.txt`: **`llama-cpp-python>=0.3.16`** (needs a C/C++
  toolchain — a classic headless pip failure), plus `trimesh, lightning,
  lightning_utilities, plyfile, jaxtyping, roma, einops, json_repair` and
  `huggingface-hub[torch]>=0.22`.
- Registration is wrapped in one `try/except` that prints `CRITICAL
  REGISTRATION ERROR` and continues — a missing dep makes the **whole pack
  silently fail to load**. Always verify nodes registered after install.
- Removed the `CharacterPreview` node; renamed workflows `*_v1.json` → `*_v2.4.json`.
- The new **`vnccs_api`** node hints at first-class v3 API support — but it is
  **not required**: `main` is already headless-capable with a small tweak
  (§5.5), so this does not force the `cleanup` choice.

**`CharacterStudio`** is a dead 3D-pose-editor experiment (tip commit literally
"123"; vendors an entire MakeHuman app + a "worldmirror" 3D model — hundreds of
unrelated `.py` files). Do not use.

- [x] **Decision (2026-05-26): target `main`.** Revisit `cleanup` only if v3's
      Control Center / `vnccs_api` headless hook later proves worth the
      `llama-cpp-python` build. If you switch, `git clone -b cleanup` and pin to
      `808bab6`.

---

## 2. Integration checklist

### 2.1 Custom nodes — edit `scripts/install_comfyui.sh`

Add VNCCS to the `install_node` list (currently `scripts/install_comfyui.sh:45-53`):

```bash
install_node https://github.com/AHEKOT/ComfyUI_VNCCS
```

The `install_node` helper runs `pip install -r requirements.txt` for the node.
VNCCS's `requirements.txt` is `torch, numpy, Pillow, opencv-python,
huggingface_hub` — **but its `pyproject.toml` also lists `timm`**, which is
missing from `requirements.txt`. Add a `pip install timm` after the clone, or
confirm a sibling node already pulls it.

- [ ] Add the `install_node` line for VNCCS.
- [ ] Ensure `timm` gets installed (not in VNCCS `requirements.txt`).
- [ ] **Verify transitive node deps** (§4) — VNCCS's README tells users to run
      Comfy Manager → "Install missing custom nodes", which means it depends on
      nodes it does not vendor. Our installer is scripted, not Manager-driven,
      so these must be enumerated explicitly. Inspect the VNCCS node `.py`
      imports / its workflow JSONs to confirm the exact set before finalizing.

### 2.2 Model directories — edit `configs/comfyui/extra_model_paths.yaml`

VNCCS uses two model categories the shared config doesn't expose yet
(`ultralytics` for YOLO face detectors, `sams` for Segment-Anything). Add:

```yaml
    ultralytics: ultralytics/
    sams: sams/
```

- [ ] Add `ultralytics:` and `sams:` keys under the `comfyui:` block.
- [ ] Re-copy to the live install: `cp configs/comfyui/extra_model_paths.yaml comfyui/extra_model_paths.yaml`
      (the install script does this at `scripts/install_comfyui.sh:28`).
- [ ] Create dirs: `models/ultralytics/bbox/`, `models/ultralytics/segm/`, `models/sams/`.
- [ ] Note: `ultralytics`/`sams` are ComfyUI-Impact-Pack conventions — confirm
      Impact Pack (or VNCCS itself) reads them via `extra_model_paths.yaml`
      rather than a hardcoded `ComfyUI/models/...` path. If hardcoded, symlink.

### 2.3 Model catalog — add entries to `models.yaml`

Add the files in §3 as new entries. Conventions to follow (matching existing
entries):

- Source repo is HuggingFace **`MIUProject/VNCCS`**, `auth: hf`.
- URL form: `https://huggingface.co/MIUProject/VNCCS/resolve/main/<path>`.
- Use `section: vnccs` so `--only vnccs` / `--skip vnccs` work
  (`install_models.py` keys off the `section` field).
- Use the **exact byte sizes from §3a** (HF tree is verified) so the disk-check
  and progress/ETA logic work (`scripts/install_models.py:181-185`).
- Preserve VNCCS's **sub-folder layout** inside `loras/` and `controlnet/`
  (e.g. `loras/DMD2/...`, `loras/qwen/VNCCS/...`, `controlnet/SDXL/...`) — the
  VNCCS workflows reference LoRAs/ControlNets by that relative path.

- [ ] Add the 14 single-file entries from §3a to `models.yaml`. The QWEN
      collection is a **known, fixed set of 5 files** (not an open-ended
      folder), so just hand-list them like any other entry — no new
      `hf_folder` handler needed.
- [ ] Decide on the §3b ultralytics detectors (separate source, or let
      Impact-Subpack auto-download).
- [ ] Run `python3 scripts/install_models.py --check --only vnccs` to confirm
      the new section parses and reports correctly.

### 2.4 Download the models

All VNCCS HF files (including QWEN) are now single `models.yaml` entries:

```bash
python3 scripts/install_models.py --only vnccs
```

As a fallback / to mirror the whole repo in one shot (matches the verified tree
exactly):

```bash
hf download MIUProject/VNCCS --include "models/*" \
  --local-dir models --local-dir-use-symlinks False
```

(The VNCCS HF repo nests everything under a top-level `models/` dir, so its
`models/loras/...` maps 1:1 onto this repo's `models/loras/...`.)

- [x] HF tree verified 2026-05-26 — paths/sizes in §3a are exact; `ultralytics/`
      is gone from the repo (see §3b).

### 2.5 Verification / smoke test

- [ ] `imggen` (or `cd comfyui && source .venv/bin/activate && python main.py --listen --port 8188`).
- [ ] Confirm VNCCS nodes register: ComfyUI console shows VNCCS loaded with no
      import errors; nodes appear in the add-node menu under the VNCCS category.
- [ ] Open `VN_Step1_CharSheetGenerator` (classic SDXL) — the most
      dependency-light path — name a throwaway character, click **Create New
      Character**, run, and confirm a sheet lands in
      `comfyui/output/VN_CharacterCreatorSuit/<NAME>/Sheets/`.
- [ ] Confirm the face-detailer / RMBG / upscale stages don't error (these
      exercise the `ultralytics`, `sams`, `upscale_models` additions).
- [ ] If using the QWEN workflows (`VN_Step1_QWEN_*`), confirm the QWEN LoRA
      folder resolved.

### 2.6 Documentation updates

- [ ] **`CLAUDE.md`** — under `## Capabilities`, add a "Visual novel character
      sheets" line; add a short `## Character Sheets (VNCCS)` section near
      `## Storyboards` explaining it's **browser-first but headless-capable**
      (§0, §5.5), the 5-stage pipeline, and the output path. Cross-reference: identity
      locking here is via a dedicated character-sheet pipeline (SDXL +
      `vn_character_sheet` LoRA + face detailer), distinct from the Flux
      Kontext approach used by storyboards.
- [ ] **`INDEX.md`** — add VNCCS to the Tools table (custom node + commit), add
      the new models (new "VNCCS" subsection under LoRAs/ControlNet/Upscalers
      plus new "Face Detection (Ultralytics)" and "SAM" sections), and register
      the new `models/ultralytics/` and `models/sams/` dirs.
- [ ] **`README.md`** — add a bullet under capabilities for VN character sheets.
- [ ] Confirm `scripts/sync_index.py` behavior: it only manages `models/`
      inventory, so the new model files will surface in INDEX's `## Unindexed`
      section automatically — annotate them by hand afterward.

---

## 3. Required models

HF tree **verified** against `https://huggingface.co/MIUProject/VNCCS/tree/main`
on 2026-05-26 (paths, filenames, and byte sizes below are exact). Destinations
are relative to the shared `models/` dir. Sub-folders are significant — keep
them; the VNCCS workflows reference LoRAs/ControlNets by that relative path.

### 3a. From `MIUProject/VNCCS` (URL: `…/resolve/main/<dest>`)

| `dest` (under `models/`) | Purpose | Size |
|---|---|---|
| `loras/vn_character_sheet_v4.safetensors` | Char-sheet consistency LoRA (v4, current) | 218M |
| `loras/vn_character_sheet.safetensors` | Char-sheet LoRA (v1, legacy workflows) | 218M |
| `loras/DMD2/dmd2_sdxl_4step_lora_fp16.safetensors` | DMD2 4-step distill (fast sampling) | 376M |
| `loras/IL/mimimeter.safetensors` | Illustrious helper LoRA | 50M |
| `loras/qwen/VNCCS/ClothesHelperUltimateV1_000005100.safetensors` | QWEN clothes-helper LoRA | 141M |
| `loras/qwen/VNCCS/EmotionCoreV1_000003000.safetensors` | QWEN emotion LoRA (v1) | 281M |
| `loras/qwen/VNCCS/EmotionCoreV2_000004700.safetensors` | QWEN emotion LoRA (v2, current) | 281M |
| `loras/qwen/VNCCS/TransferClothes_000006700.safetensors` | QWEN clothes-transfer LoRA | 281M |
| `loras/qwen/VNCCS/poser_helper_v2_000004200.safetensors` | QWEN pose-helper LoRA (v2) | 281M |
| `controlnet/SDXL/AnytestV4.safetensors` | SDXL "anytest" ControlNet | 2.3G |
| `controlnet/SDXL/IllustriousXL_openpose.safetensors` | Illustrious OpenPose ControlNet | 2.3G |
| `sams/sam_vit_b_01ec64.pth` | Segment-Anything ViT-B | 358M |
| `upscale_models/4x_APISR_GRL_GAN_generator.pth` | 4× anime upscaler (APISR GRL) | 6.2M |
| `upscale_models/2x_APISR_RRDB_GAN_generator.pth` | 2× anime upscaler (APISR RRDB) | 17M |

Total from VNCCS HF ≈ **7.4 GB**. Note: the **QWEN path is `loras/qwen/VNCCS/`
(lowercase `qwen`, then a `VNCCS/` subdir)** — the README's `QWEN/` is stale.
The repo also ships `model_updater.json` (VNCCS's own download manifest); the
node may self-fetch/update some of these — worth checking before duplicating.

### 3b. NOT on the VNCCS HF repo — source elsewhere

The `ultralytics/` face detectors the README lists were **removed** from the HF
repo (latest commit there is literally "Delete models/ultralytics"). They are
standard Impact-Pack/adetailer assets — fetch from the canonical
[`Bingsu/adetailer`](https://huggingface.co/Bingsu/adetailer) set instead:

| `dest` (under `models/`) | Purpose | Note |
|---|---|---|
| `ultralytics/bbox/face_yolov8m.pt` | Face bbox detector (YOLOv8m) | in `Bingsu/adetailer` |
| `ultralytics/bbox/face_yolov9c.pt` | Face bbox detector (YOLOv9c) | in `Bingsu/adetailer` |
| `ultralytics/segm/face_yolov8m-seg_60.pt` | Face segmentation (YOLOv8m-seg) | confirm exact filename/source |

- [ ] Confirm the three detector filenames against `Bingsu/adetailer` before
      adding URLs (esp. the `-seg_60` variant). Impact-Subpack can also
      auto-download these on first use — if so, these rows are optional.

**Checkpoint:** none required — VNCCS uses an Illustrious-based SDXL checkpoint,
and `Illustrious-XL-v0.1.safetensors` is already installed (`INDEX.md`).

Example `models.yaml` entry shape (single file — use the exact sizes above so
the installer's progress/ETA/disk-check work):

```yaml
- section: vnccs
  name: VNCCS Character Sheet v4
  dest: loras/vn_character_sheet_v4.safetensors
  url: https://huggingface.co/MIUProject/VNCCS/resolve/main/loras/vn_character_sheet_v4.safetensors
  size: 228452916
  auth: hf
  base: sdxl
  purpose: Character-sheet consistency LoRA for VNCCS
  source: https://huggingface.co/MIUProject/VNCCS
  date: '2026-05-26'
```

---

## 4. Custom-node dependency matrix (verify before scripting §2.1)

VNCCS is one node pack, but its workflows reference functionality from other
packs (hence the README's "Install missing custom nodes" step). The list below
is **corroborated by the issue tracker** (§4.5) — version skew between these and
ComfyUI is the #1 source of breakage, so pin them.

| Capability in VNCCS | Required node pack | Installed here? |
|---|---|---|
| Face Detailer + `UltralyticsDetectorProvider` + `SAMLoader` (`ultralytics/`, `sams/`) | **ComfyUI-Impact-Pack** (+ **Impact-Subpack** for the detector provider) | ❌ add |
| "Seam Fix Mode" / "Half Tile + intersections" upscaling (older sheets) | **ComfyUI_UltimateSDUpscale** | ❌ add |
| Background removal for clean sprites (`RMBG Resolution`) | **ComfyUI-RMBG** / **BiRefNet** node (see #40) | ❌ add |
| SeedVR2 upscaling (newer/QWEN pipeline) | **SeedVR2** node (see #55) | ❌ add (only if using QWEN/v3) |
| Pose preprocessing / OpenPose | `comfyui_controlnet_aux` | ✅ already in install script |
| QWEN clone/clothes workflows | Qwen-Image-Edit nodes (see #57) | ❌ add (only if using QWEN) |

- [ ] Add each pack needed for the chosen pipeline to `scripts/install_comfyui.sh`
      via `install_node` (SDXL path needs Impact Pack + Subpack + RMBG +
      UltimateSDUpscale; QWEN path adds SeedVR2 + Qwen-Image-Edit).
- [ ] Pin Impact Pack and ComfyUI to a known-good pair (§4.5 #48/#53).
- [ ] Re-run the smoke test (§2.5) and watch the console for "missing node"
      errors when loading each `VN_Step*` workflow.

---

## 4.5 Known upstream issues → local fixes (set up proactively)

Triaged the VNCCS issue tracker (2026-05-26). Confirmed the node-dep picture in
§4: the SDXL/Illustrious pipeline (our path) uses **Impact Pack** (FaceDetailer
+ ultralytics/SAM); older sheets use **Ultimate SD Upscale**; the newer/QWEN
pipeline adds **BiRefNet/RMBG** background-removal and a **SeedVR2** upscaler.
Four things to handle before the first run:

**1. Pin ComfyUI + Impact Pack — don't run bleeding-edge.**
- **#48 (open)** — `CharacterSheetCropper` crashes `'NoneType' not subscriptable`
  at `sheet_crop.py:31` after the ComfyUI ≥0.15.1 mask-API change. Hits the core
  sprite-sheet crop on day one. *Fix:* pin ComfyUI below the break **or** patch
  `sheet_crop.py` to guard `mask is None` before indexing.
- **#53 (closed)** — clean reinstall → Ultimate SD Upscale "12 vs 16 channels" +
  FaceDetailer `Tensor has no attribute 'copy'` = Impact Pack / ComfyUI version
  skew. *Fix:* install a matching Impact Pack version; record both commits in INDEX.

**2. Pre-fix workflow model fields + Windows paths (Linux install).**
- **#49 / #37 (closed)** — workflows hardcode `ckpt_name:
  Illustrious\ILFlatMix.safetensors` (Windows `\`). *Fix:* edit each `VN_Step*`
  workflow's `ckpt_name` to your actual Illustrious file, forward slashes.
- **#43 (open)** — QWEN Step1 ships placeholder model fields ("Green"). *Fix:*
  set real checkpoint/upscaler dropdowns after import.
- **#50 (open)** — `EmotionGeneratorV2.load_character_sheet()` → `[Errno 22]
  Invalid argument` = backslash/path issue. *Fix:* keep all sheet/output paths
  POSIX — relevant since we drive headless (§5.5).

**3. Verify the heavy node deps actually load.**
- **#40 (open)** BiRefNet `has no attribute '__file__'` (RMBG weights load);
  **#55 (open)** SeedVR2 "meta tensors" load failure — both version/weights
  mismatches, not VRAM. *Fix:* pre-download known-good BiRefNet + SeedVR2
  weights into the nodes' expected dirs; confirm clean import.

**4. Use SDXL-arch models only.**
- **#60 (open)** SDXL ControlNet `ValueError: y is None` = wrong-arch ControlNet.
  *Fix:* use `AnytestV4` / `IllustriousXL_openpose` from §3a (not SD1.5 ones).
- **#58 (open)** HF `MIUProject/VNCCS` vs `…/VNCCS_V2` LoRA confusion. *Fix:* for
  SDXL/Illustrious use the V1 set (`vn_character_sheet_v4`, `EmotionCoreV2`); the
  `V2` LoRAs are QWEN-only.

VRAM glitches (**#54/#59**, open) are low-risk at 24 GB, but #59 (assembled-sheet
glitch) can still bite — if sheets glitch, drop RMBG resolution to 1024 and lower
the SeedVR2 target res. Pure feature-requests (#31/#33/#36/#42/#44/#45/#51/#52/#56)
need no action.

- [ ] Pin a known-good ComfyUI + Impact Pack pair; record commits in `INDEX.md`.
- [ ] Patch/guard `sheet_crop.py:31` if staying on newer ComfyUI (#48).
- [ ] Sweep imported `VN_Step*` workflows for `\` paths + placeholder model names.

---

## 5. Caveats & open questions

1. **UI vs API (the headline).** Steps 1–5 are interactive. They cannot be
   driven by `run_workflow`/MCP or `storyboard.py` as-is. Treat VNCCS as a
   browser tool. *Possible* future automation: the per-character `config.json`
   that VNCCS writes under `VN_CharacterCreatorSuit/<NAME>/` could be templated,
   and the non-interactive `VN_Step4_SpritesGenerator` *might* be convertible to
   API format — needs investigation, out of scope for first integration.
2. **HF tree verified** (2026-05-26). Two surprises vs. the README: the QWEN
   path is `loras/qwen/VNCCS/` (lowercase), and the `ultralytics/` face
   detectors were **deleted** from the HF repo — source them from
   `Bingsu/adetailer` or via Impact-Subpack auto-download (§3b).
3. **QWEN folder** turned out to be a fixed set of 5 named LoRAs (§3a), so it's
   hand-listed like everything else — no `hf_folder` handler needed.
4. **Transitive nodes.** Impact Pack / UltimateSDUpscale / RMBG are inferred
   (§4). Don't ship the install-script change until confirmed against VNCCS
   source, or the smoke test will hit "missing node" walls.
5. **`ultralytics`/`sams` path resolution.** Confirm these honor
   `extra_model_paths.yaml`; some Impact-Pack versions read a hardcoded
   `ComfyUI/models/...`. Symlink if needed.
6. **`timm`** is in VNCCS `pyproject.toml` but not `requirements.txt` — install
   it explicitly (§2.1).
7. **Hardcoded repo root.** `scripts/install_comfyui.sh:4` pins
   `REPO_ROOT=/media/menser/fauna/image_gen`. Edits there are fine, but the
   path is environment-specific — don't "fix" it as part of this work.

---

## 5.5 Headless automation — feasible, with tweaks

Verdict from reading the node source (`main`; `cleanup`/`CharacterStudio`
behave the same): **partially headless out of the box, fully scriptable after
two tweaks.** Almost every node is pure compute — a server-coupling grep shows
only `emotion_generator_v2` touches `PromptServer`, and only for *optional*,
read-only UI helper routes the node itself never calls.

### Per-stage breakdown

| Stage | Node | Headless via `/prompt`? |
|---|---|---|
| 1 Base character | `CharacterCreator` | ✅ compute runs — **but** the character folder/config must already exist (see blocker) |
| 2 Clothing sets | `CharacterAssetSelector` | ✅ writes costume config server-side; character must exist; costume must be in the enum or pass `new_costume_name` |
| 3 Emotions | `EmotionGenerator` / `_v2` | ✅ `generate_emotions()` is pure compute; v2's `/vnccs/get_*` routes are UI-only, not called by the node |
| 4 Sprites | `SpriteGenerator` | ✅ fully headless — disk crop; input `character` only |
| 5 LoRA dataset | `DatasetGenerator` | ✅ fully headless — inputs `character`, `game_name` |
| Poses | `pose_generator` + `web/pose_editor*.js` | ⚠️ compute works, but pose data normally comes from the 3D JS editor — supply joint JSON directly or drop a preset in `presets/poses/` |

### The one blocker

`CharacterCreator.create_character()` operates on the `existing_character`
dropdown (built by scanning disk) and calls `ensure_character_structure(...)`.
It does **not** use the `new_character_name` input. The folder +
`<NAME>_config.json` are created by the front-end "Create New Character" button
→ `GET /vnccs/create?name=<NAME>` (registered in `__init__.py`). That route does
**not** fire when you POST a graph to `/prompt`.

### Tweaks to make stages 1–5 scriptable

1. **Pre-seed the character** (pick one), then queue the graph:
   - hit the route already live on the running server:
     `GET http://127.0.0.1:8188/vnccs/create?name=<NAME>` — provisions folder +
     config; **or**
   - write `output/VN_CharacterCreatorSuit/<NAME>/<NAME>_config.json` + the
     `Sheets/Faces/Sprites/Naked/neutral` tree yourself (mirror
     `ensure_character_structure` + the `character_info` dict in
     `character_creator.py`).
2. **(cleaner) Patch `create_character`** to honor `new_character_name`
   (`character_name = new_character_name or existing_character`) so stage 1
   self-provisions inside the graph and the route dependency disappears. ~1-line
   change — keep it as a tracked local patch; re-apply on upstream update.
3. **Re-export every `VN_Step*` workflow to API format** (ComfyUI → Save (API
   Format)) before placing in `workflows/`. API-graph inputs to wire as this
   repo's `PARAM_*` placeholders:
   - CharacterCreator: `existing_character` (name),
     `sex/age/race/eyes/hair/face/body/skin_color/nsfw/seed/negative_prompt`
   - selector: `character`, `costume` (+ garment strings)
   - emotions: `character`, `emotions` (comma list)
   - sprites / dataset: `character` (+ `game_name`)
4. **Costumes** need no node tweak, but pass `new_costume_name` or pre-create via
   `/vnccs/create_costume` — an unknown costume silently falls back to `"Naked"`.

### Recommended integration shape

A thin `scripts/vnccs.py` driver modeled on `scripts/storyboard.py`: read a
character spec (YAML), `GET /vnccs/create`, then queue the API-format
`VN_Step1..4` graphs in order via `/prompt`, and build the usual local HTML
gallery (per `BROWSER_DISPLAY.md`) of the resulting sheet/sprites. This keeps
VNCCS on the same HTTP-API/no-MCP path as the storyboard driver and sidesteps
MCP's UI-format crash entirely.

- [ ] Re-export the chosen `VN_Step*` workflows to API format → `workflows/`.
- [ ] Apply tweak #1 (route call) or #2 (node patch); commit the patch.
- [ ] (optional) Write `scripts/vnccs.py` headless driver.

---

## 6. Acceptance criteria

- [ ] `scripts/install_comfyui.sh` clones VNCCS **and** every confirmed
      transitive node pack; `timm` installed.
- [ ] `configs/comfyui/extra_model_paths.yaml` exposes `ultralytics/` + `sams/`,
      copied to the live `comfyui/` install.
- [ ] `models.yaml` has a `vnccs` section (14 files incl. the 5 QWEN LoRAs);
      `install_models.py --only vnccs` downloads them; §3b detectors sourced.
- [ ] Fresh ComfyUI start loads VNCCS with zero import/missing-node errors.
- [ ] `VN_Step1_CharSheetGenerator` produces a sheet under
      `comfyui/output/VN_CharacterCreatorSuit/<NAME>/Sheets/`.
- [ ] `CLAUDE.md`, `INDEX.md`, `README.md` updated; VNCCS documented
      (browser-first; headless path per §5.5).
- [ ] Branch chosen per §1.5 (default `main`); ComfyUI + Impact Pack pinned and
      the §4.5 issue fixes applied/verified.
</content>
</invoke>
