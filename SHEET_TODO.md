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

**Conclusion:** integrate VNCCS as a **browser workflow at `localhost:8188`**,
not as MCP tools. The deliverable (the character sheet / sprite set) is
produced through the ComfyUI canvas using the bundled `VN_Step*` workflows.
Do **not** drop VNCCS's `VN_Step*.json` files into `workflows/` — they are
UI-format and will break MCP auto-registration. Keep them in the custom-node
dir where VNCCS ships them.

See §5 for what *could* later be automated (and what can't).

---

## 1. How it fits the existing architecture

| Concern | This repo today | VNCCS need | Action |
|---|---|---|---|
| Base model | Illustrious-XL-v0.1 (SDXL) already installed | "Any Illustrious-based SDXL" | ✅ none — reuse existing checkpoint |
| Model dir | shared `models/` via `configs/comfyui/extra_model_paths.yaml` | adds `ultralytics/`, `sams/` categories | ⚠️ add two new path keys (§2.2) |
| Custom nodes | cloned explicitly in `scripts/install_comfyui.sh` | VNCCS + several transitive node deps | ⚠️ add to install script (§2.1) |
| Model fetch | `models.yaml` → `scripts/install_models.py` | 14 files on VNCCS HF (~7.4 GB) + 3 face detectors elsewhere | ⚠️ add entries (§2.3, §3) |
| Automation | MCP + HTTP API, API-format workflows | interactive UI nodes | ❌ stays manual/browser (§0) |
| VRAM | RTX 3090 24 GB | tuned for 8 GB (RMBG ≤1408) | ✅ comfortable headroom |
| Output | `outputs/` + `comfyui/output/` (gitignored) | `comfyui/output/VN_CharacterCreatorSuit/<NAME>/{Sheets,Sprites,Lora}` | ✅ none — already gitignored |

VNCCS is SDXL/Illustrious-based, so it does **not** contend with the Flux /
HunyuanVideo / WAN VRAM budget — it's in the same family as the existing
`sdxl_basic` / `controlnet_pose` workflows.

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
      `## Storyboards` explaining it's a **browser workflow, not MCP** (§0),
      the 5-stage pipeline, and the output path. Cross-reference: identity
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

VNCCS itself is one node pack, but its workflows reference functionality from
other packs (hence the README's "Install missing custom nodes" step). Evidence
from the README + node names, with likely owning pack:

| Capability seen in VNCCS | Likely required node pack | Already installed here? |
|---|---|---|
| Face Detailer + `UltralyticsDetectorProvider` + `SAMLoader` (`ultralytics/`, `sams/`) | **ComfyUI-Impact-Pack** (+ Impact-Subpack for the detector provider) | ❌ add |
| "Seam Fix Mode", "Half Tile + intersections" upscaling | **ComfyUI_UltimateSDUpscale** | ❌ add |
| "RMBG Resolution" background removal for clean sprites | a background-removal node (e.g. **ComfyUI-RMBG** / `BRIA RMBG`) | ❌ add (confirm which) |
| Pose preprocessing / OpenPose | `comfyui_controlnet_aux` | ✅ already in install script |

- [ ] Clone the VNCCS repo locally and grep its `nodes/*.py` imports and the
      `VN_Step*.json` workflow `class_type` values to produce the **definitive**
      dependency list — the table above is inferred, not confirmed.
- [ ] Add each confirmed pack to `scripts/install_comfyui.sh` via `install_node`.
- [ ] Re-run the smoke test (§2.5) and watch the console for "missing node"
      errors when loading each `VN_Step*` workflow.

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
- [ ] `CLAUDE.md`, `INDEX.md`, `README.md` updated; VNCCS documented as a
      browser workflow (not MCP).
</content>
</invoke>
