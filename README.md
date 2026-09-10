# image_gen

![banner](assets/banner.png)

A production-grade local AI image and video generation stack running on a single RTX 3090. Covers the full range from quick SDXL sketches to state-of-the-art Flux edits, impressionist LoRA styling, and 14B-parameter video generation — all callable by a Claude Code agent via MCP without touching a UI.

> **⚠️ The full model library is 320GB on disk.** Run `python3 scripts/install_models.py --check` to see a per-section breakdown before committing. Use `--skip wan` to skip the WAN 2.2 video models and save ~110GB.

**GPU:** RTX 3090 (24GB) &nbsp;|&nbsp; **ComfyUI:** `localhost:8188` &nbsp;|&nbsp; **MCP:** `localhost:9000`

---

## Why

> *"Drama is life with the dull bits cut out."*
> — Alfred Hitchcock

Image generation used to mean knowing your tools cold: which model handles which subject, what LoRA weight to dial in, which sampler converges cleanest at which step count. That knowledge was the bottleneck between an idea and a finished image. It shouldn't be.

This repo is built around the idea that the agent carries that knowledge. `CLAUDE.md` gives any Claude Code instance a complete map of the stack. `INDEX.md` is an auto-synced inventory of every installed model — trigger words, weights, sources, capabilities. The MCP server exposes every workflow as a callable tool. The agent reads, reasons, and executes. You supply the vision.

> *"I'm not funny. What I am is brave."*
> — Lucille Ball

Manual prompt engineering had its moment. The era of describing what you want and letting the machine figure out the rest is not coming — it's here.

---

## How

> *"Too much of a good thing can be wonderful."*
> — Mae West

1. **Start the stack:** `imggen`
2. **Open Claude Code** in this repo — `.mcp.json` auto-connects to the MCP server
3. **Describe what you want** — style, subject, mood, references, constraints
4. The agent reads `INDEX.md`, picks the right model and workflow, calls the MCP tools, and generates
5. Give feedback in plain language; it iterates

For anything deeper — downloading a new LoRA, wiring a custom workflow, batch-generating variations with consistent style — it can do that too. The full capability inventory is in [`INDEX.md`](INDEX.md) and the agent operating instructions are in [`CLAUDE.md`](CLAUDE.md).

> *"If you obey all the rules, you miss all the fun."*
> — Katharine Hepburn

---

## Setup

**Prerequisites:** HuggingFace token at `~/.cache/huggingface/token` (needed for Flux.1-dev), CivitAI API key in `$CIVITAI_API_KEY`.

**Linux / macOS:**
```bash
git clone https://github.com/kleer001/image_gen.git && cd image_gen && bash scripts/install_comfyui.sh && bash scripts/install_comfyui_mcp.sh && python3 scripts/install_models.py
```

**Windows — open PowerShell as Administrator, then paste into the WSL terminal it opens:**
```powershell
wsl --install
```
```bash
git clone https://github.com/kleer001/image_gen.git && cd image_gen && bash scripts/install_comfyui.sh && bash scripts/install_comfyui_mcp.sh && python3 scripts/install_models.py
```

Clones and wires up ComfyUI + the MCP server, then pulls the full model library (~320GB). Once done, `imggen` starts everything.

<details>
<summary><strong>Manual setup (step by step)</strong></summary>

#### 1. Clone the repo

```bash
git clone https://github.com/kleer001/image_gen.git
cd image_gen
```

#### 2. Install ComfyUI and custom nodes

```bash
bash scripts/install_comfyui.sh
```

Creates a venv, installs PyTorch (CUDA on Linux/Windows, MPS on macOS), installs ComfyUI requirements, and clones all required custom nodes (AnimateDiff, VideoHelperSuite, HunyuanVideoWrapper, WanVideoWrapper, XLabs Flux ControlNet, ControlNet-Aux, Frame-Interpolation, StoryDiffusion, KJNodes).

#### 3. Install the MCP server

```bash
bash scripts/install_comfyui_mcp.sh
```

Clones comfyui-mcp-server, creates its venv, and installs dependencies.

#### 4. Download models

```bash
python3 scripts/install_models.py              # full library (~200GB)
python3 scripts/install_models.py --check      # preview what's missing + disk needed
python3 scripts/install_models.py --skip wan   # skip WAN 2.2 (saves 110GB)
```

Downloads checkpoints, Flux models, video models, LoRAs, ControlNets, VAEs, and upscalers from HuggingFace and CivitAI. Resumes interrupted downloads automatically.

</details>

## Running

```bash
imggen          # start ComfyUI + MCP server, open browser
imggen stop     # kill both
imggen status   # check what's running

# A1111 (independent)
cd automatic1111 && ./webui.sh
```


## GitHub Backup

Only configs, scripts, workflows, and this README are pushed.
Models and outputs stay local only.

## License

The code, workflows, and documentation here are [MIT](LICENSE) — use them however you like.

The models this stack downloads are **not** covered by that. They carry their own terms, and some are restrictive: Flux.1-dev is non-commercial, and MiniMax H3 is unavailable in several territories. Check the license on any weights you pull before building something commercial on them.

Reference images, plates, and shot lists are not distributed with the repo. Supply your own — the examples name the files they expect.
