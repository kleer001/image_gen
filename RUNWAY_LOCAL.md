# Local Runway: options

Goal: reproduce Runway's UI and abilities on the local stack. The backend already
exists here (ComfyUI + WAN / HunyuanVideo). The missing part is the UI layer.

## What Runway does

Gen-4 text/image-to-video, video-to-video, motion brush, inpaint / erase, Act-One
(face performance transfer), lip-sync, frame interpolation, upscale, camera control,
plus a multi-shot timeline and an asset library. One web studio holds all of it.

## Closest local projects

No project is a pixel-clone of Runway. Each one below covers part of it.

| Project | What it gives | Fit vs Runway | Notes |
|---|---|---|---|
| NodeTool | One canvas for image/video/audio/text; masks, inpaint, outpaint, relight, upscale, layers; local or bring-your-own-key | Closest creative workspace; node/canvas, not a timeline | AGPL-3.0, desktop or self-host, talks to local ComfyUI |
| ComfyStudio (Electron) | Timeline editor + asset browser + stock search over ComfyUI | Closest to Runway's timeline UI | listed in awesome-alternative-uis-for-comfyui |
| Inline Studio | AI filmmaking on a node canvas, versioned non-destructive renders | Film-project shape, not a timeline | free desktop |
| The Halleen Machine | AI-video workflow with structured timelines and batch | Pipeline / timeline manager | — |
| Open Generative AI | All-in-one image/video studio, 600+ models | Broad studio, cloud-model-first | MIT, self-host |
| SwarmUI | Polished web frontend over ComfyUI | Best-maintained ComfyUI frontend; image-centric | active |

## The gap

Runway's signature UI verbs — motion brush, Act-One, click-to-erase — have no
turnkey local UI. The underlying capability exists as ComfyUI nodes (pose / depth
ControlNet, inpaint, WAN VACE). Each verb needs a workflow built behind it.

A faithful local clone = one shell (NodeTool or ComfyStudio) + the missing verbs
built as ComfyUI workflows behind it.

## How Runway itself drives generation

Runway's own advanced workflow ("A Game of HORSE", official tutorial) runs on two
pieces that map onto this repo's MCP-plus-driver pattern:

- **Runway MCP** (`runway.com/mcp`) — no API key; the agent calls the API, polls,
  and downloads. Models: Seedance 2.5, Kling 3.0, Gen-4.5, Veo 3.1, GPT Image 2,
  Gen-4, Nano Banana Pro.
- **Official skills** (`github.com/runwayml/skills`, `npx skills add runwayml/skills`)
  — `rw-generate-video/image/audio` plus dev-platform skills incl.
  `runway-dev-characters` and `runway-dev-workflows`.

The tutorial's seven steps: story → character sheets (Runway Agent + Nano Banana) →
wardrobe → location + the **Burst method** (generate one Seedance 2.5 clip for exact
scene continuity, then extract frames as coverage) → character voice → prompt build
via a Claude skill → edit.

### The enhancer skill

Runway's own Claude skill (`runway-sd-enhancer-skill.md`, fetched from the source
URL below) turns a raw idea into a structured Seedance 2.5 prompt: asset-binding
block, one-sentence summary, gap-free integer-second timeline, camera / action
direction, style lock, native audio. Two paths (SEQUENTIAL, VARIATIONS), a 30s
split rule (`N = ceil(total / 30)`, continuity blocks repeated verbatim),
LOCKED-vs-UNLOCKED task classes, and a final self-check.

Its structured-prompt contract is model-agnostic. This repo's local adaptation is
the `shot-enhancer` skill, which writes shot lists for `storyboard.py` / WAN I2V /
H3 instead of Seedance. The Burst method is the same idea as this repo's "render a
video, extract frames" step (`scripts/extract_frames.py`).

That skill file and the video transcript are third-party content, so they are not
tracked in this repo. A local working copy lives under `runway_ref/` (gitignored);
fetch it from the source URL below.

## Sources

- https://github.com/light-and-ray/awesome-alternative-uis-for-comfyui
- https://nodetool.ai/alternatives/runway
- https://github.com/anil-matcha/open-generative-ai
- https://magichour.ai/blog/open-source-alternatives-to-runwayml
- https://runway.com/prompts/a-game-of-horse (skill + prompts)
- https://runway.com/mcp
- https://github.com/runwayml/skills
