---
name: model-radar
description: Sweep the open-weights image/video generation landscape — new base models, LoRAs for installed model families, and ComfyUI custom nodes/tools — filtered to what fits this deployment's GPU and excluding what's already installed. Produces a dated markdown digest under radar/. Report only; never downloads, installs, or edits the catalog. Use when the user invokes /model-radar or asks for a what's-new sweep of image/video models for the image_gen stack.
---

# Model Radar

Survey the current open-weights image- and video-generation landscape, compare it against what this stack already has, and write a dated digest of what is new and worth considering. **Report only — never download, install, start `imggen`, or edit `models.yaml` / `INDEX.md`.**

> **Full procedure & current-state-digestion checklist: [`UPDATE.html`](../../../UPDATE.html) at the repo root.** That page is the authoritative, extended runbook (it also covers the **Workflows** category and the local-vs-remote state-digestion caveats). The steps below mirror it; if they ever diverge, UPDATE.html wins.

This is a sovereign/local rig. Judge "state of the art" only among **open-weights models runnable locally**, not closed APIs (Midjourney, Sora, Veo, Kling) — those are out of scope by design.

## Hardware ceiling

Target GPU ceiling: **24 GB VRAM (RTX 3090)**. A model only counts as installable if it fits in 24 GB, including via quantization (GGUF / fp8) — flag when a model fits *only* quantized and note the quality/speed cost. If `nvidia-smi` is available, detect the actual VRAM and use that instead of the written ceiling.

## Steps

1. **Establish the window.** List `radar/`. The newest existing digest's date is the "since" boundary — report what is new since then. If `radar/` has no dated digests, use roughly the last 14 days.
2. **Read installed state.** Parse `INDEX.md` (authoritative on-disk inventory) and `models.yaml` (installable catalog) to build (a) the set of installed model/LoRA filenames and (b) the base model families currently in use — derive these families from `INDEX.md` itself, do not assume a fixed list. Anything already present must not be re-reported as "new."
3. **Sweep these categories** with web search — several focused queries each:
   - **Image base models** — new or updated open-weights foundations and notable checkpoints.
   - **Video models** — new or updated open-weights video generators.
   - **LoRAs** — notable new LoRAs for the base families this stack uses (step 2b).
   - **Workflows (ComfyUI & elsewhere)** — new SOTA *pipelines* for what the stack does or wants (txt2img, Kontext/in-context edit, ControlNet, storyboard, i2v/t2v, upscale + frame-interp). Sources: ComfyUI example workflows, CivitAI (Workflows filter), OpenArt, comfyworkflows.com, GitHub. Prefer API-format graphs; note node deps and 24 GB fit.
   - **ComfyUI nodes / tools** — significant new custom nodes, pipelines, or quantization tooling relevant to the installed models.
4. **Filter:** drop anything already installed (step 2a) and anything that cannot fit the VRAM ceiling even quantized.
5. **Rank** by relevance: does it fill a known gap, upgrade an installed model, or unlock a new capability? Demote incremental point releases.
6. **Verify skeptically.** Many "best of" rankings are vendor or SEO blogs. Prefer primary sources (HuggingFace / CivitAI model cards, release notes). Mark any claim resting only on a vendor blog as *unverified*.
7. **Write the digest** to `radar/<YYYY-MM-DD>.md` using the template below, then print a summary of at most 5 lines.

## Digest template

```markdown
# Model Radar — <YYYY-MM-DD>
Window: since <prev-date>. GPU ceiling: <N> GB.

## Image base models
- **<name>** (<params>, <license>) — <what changed / why it matters>. Fits 24 GB: <yes | quantized only | no>. Source: <url>. Verdict: <skip | watch | try>.

## Video models
- ...

## LoRAs (for installed families)
- **<name>** — <family>, trigger `<...>`. Source: <url>. Verdict: <...>.

## Workflows
- **<name>** — <capability it improves>; format <ComfyUI API / other>, deps <node(s)>. Fits stack: <yes | needs node X>. Source: <url>. Verdict: <skip | watch | try>.

## ComfyUI nodes / tools
- **<name>** — <what it adds>. Source: <url>.

## Bottom line
<2-3 sentences: anything worth acting on, or "nothing material this window.">
```

## Guardrails

- Report only. Never download, never edit `INDEX.md` / `models.yaml`, never start the stack.
- Cite a source URL for every entry.
- If a sweep category turns up nothing new, say so explicitly rather than padding.
- Keep it scannable — a handful of high-signal entries beats an exhaustive dump.
