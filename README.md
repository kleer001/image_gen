# image_gen

![banner](assets/banner.png)

Local image and video generation on one 24GB GPU, driven by a Claude Code agent.

Runs Flux.1, SDXL/Illustrious, Kontext, FLUX.2 Klein, Ideogram 4, and 14B-parameter video
(WAN 2.2, HunyuanVideo, MiniMax H3) across five pinned ComfyUI environments that share a single
model directory. You describe what you want; the agent picks the model, the LoRA, and the
workflow, and runs it. Everything also works from plain HTTP if you'd rather not use an agent.

**GPU:** RTX 3090 (24GB) &nbsp;|&nbsp; **ComfyUI:** `localhost:8188` &nbsp;|&nbsp; **MCP:** `localhost:9000`

> **⚠️ The full model library is over 400GB on disk.** Run `python3 scripts/install_models.py --check`
> for a per-section breakdown before committing. `--skip wan` drops the WAN 2.2 video models and
> saves ~120GB.

---

## Usage

Start the stack:

```console
$ ./scripts/imggen.sh
[imggen] Starting ComfyUI...
         http://localhost:8188  (ready)
[imggen] Starting MCP server...
         http://localhost:9000/mcp  (ready)
```

Open Claude Code in this directory — `.mcp.json` connects it to the MCP server — and ask for
what you want. The agent reads `INDEX.md` to see which models and LoRAs are actually on disk,
picks one, and runs the matching workflow:

> *Six-panel storyboard: a wanderer crossing a salt flat at dusk, same character in every panel.*

Or drive it directly, no agent involved:

```bash
python3 scripts/storyboard.py examples/storyboard.example.yaml
```

Renders each panel through the ComfyUI HTTP API, locks identity across panels with Flux Kontext,
builds an HTML contact sheet, and opens it in your browser. The same pattern covers video
(`video_shot.py`), reference-to-video (`h3_ref2v.py`), and character sheets
(`flux2_character_sheet.py`).

`./scripts/imggen.sh stop` and `status` do what they say. For a bare `imggen` command, alias it:

```bash
alias imggen='/path/to/image_gen/scripts/imggen.sh'
```

## Install

**Prerequisites:** an NVIDIA GPU with 24GB (the quantization choices throughout assume Ampere /
`sm_86`), a HuggingFace token at `~/.cache/huggingface/token` for the gated Flux.1-dev repo, and
a CivitAI key in `$CIVITAI_API_KEY` for the LoRAs.

```bash
git clone https://github.com/kleer001/image_gen.git
cd image_gen
bash scripts/install_comfyui.sh      # ComfyUI + venv + the nine custom nodes
bash scripts/install_comfyui_mcp.sh  # the MCP server
python3 scripts/install_models.py    # the model library — see the warning above
```

`install_models.py` resumes interrupted downloads, and `--check`, `--only <section>` and
`--skip <section>` let you take it in pieces.

The other environments are optional and independent — `install_comfyui_flux2.sh` (FLUX.2 Klein),
`install_comfyui_v26.sh` (Krea 2, Bernini-R), `install_comfyui_h3.sh` (MiniMax H3 video+audio),
and `install_a1111.sh` (standalone SDXL webui on `:7860`). Each pins its own ComfyUI version so
a bump for one model family can't break the others. See [`ENVIRONMENTS.md`](ENVIRONMENTS.md).

## Status

Released as **v0.1.0** — it runs daily on the machine it was built for, and this is the first
time anyone else can clone it. Expect the rough edges of a first release. Reference images and
plates are not distributed; supply your own at the paths the examples name, per the
reference-image section of [`CLAUDE.md`](CLAUDE.md).

## Why

> *"Drama is life with the dull bits cut out."*
> — Alfred Hitchcock

Image generation used to mean knowing your tools cold: which model handles which subject, what
LoRA weight to dial in, which sampler converges cleanest at which step count. That knowledge was
the bottleneck between an idea and a finished image. It shouldn't be.

This repo is built so the agent carries that knowledge. `CLAUDE.md` is a complete map of the
stack. `INDEX.md` is an auto-synced inventory of every installed model — trigger words, weights,
sources. The MCP server exposes every workflow as a callable tool. The agent reads, reasons, and
executes. You supply the vision.

> *"I'm not funny. What I am is brave."*
> — Lucille Ball

The hard-won part isn't the wiring, it's what the wiring taught: which quantizations survive on
`sm_86`, why MiniMax H3 needs cu130 while everything else runs cu121, how much VRAM WAN 2.2 needs
before it takes the whole machine down, and why a character sheet shot on white gives you plastic
skin in every scene you composite it into. That's all written down here.

> *"If you obey all the rules, you miss all the fun."*
> — Katharine Hepburn

## Docs

| | |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Agent operating instructions — the full map of the stack |
| [`INDEX.md`](INDEX.md) | Installed models, trigger words, LoRA weights (auto-synced) |
| [`ENVIRONMENTS.md`](ENVIRONMENTS.md) | The five generator environments and how to add one |
| [`API_USAGE.md`](API_USAGE.md) | Driving ComfyUI over plain HTTP, no MCP |
| [`models/MODELS.md`](models/MODELS.md) | Download catalog with sources and install notes |
| [`radar/`](radar/) | Dated sweeps of the open-weights landscape |

## License

The code, workflows, and documentation here are [MIT](LICENSE) — use them however you like.

The models this stack downloads are **not** covered by that. They carry their own terms, and some
are restrictive: Flux.1-dev is non-commercial, and MiniMax H3 is unavailable in several
territories. Check the license on any weights you pull before building something commercial.
