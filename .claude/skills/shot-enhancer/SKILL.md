---
name: shot-enhancer
description: Turn a raw video idea, scene description, or shot note into a finished shot-list YAML for this repo's local drivers — storyboard.py (Flux + Kontext panels), video_shot.py (WAN 2.2 image-to-video), or h3_ref2v.py / h3_t2v.py (MiniMax H3 video + native audio). The local analogue of Runway's Seedance prompt enhancer, retargeted to the models this stack actually runs, with a model-agnostic craft layer and an anti-slop gate. Output is a valid shot list only. Use when the user wants to make a short film, movie, or multi-shot video and needs the shots written; asks to enhance, expand, or "make a real prompt / shot list" from an idea; asks for a storyboard, a WAN clip, an H3 clip with voice, or coverage for a scene; or names a driver (storyboard, video_shot, wan, h3).
---

# shot-enhancer — local shot-list writer

Input: a user idea at any level of detail, plus an optional target driver, optional
reference images, an optional project bible, and an optional duration.
Output: a shot-list YAML for one driver, and nothing else.

This skill writes shot lists. It does not render and it does not talk about its work.

The local models are not Seedance 2.5. Do not carry Seedance's contract across —
WAN takes one start frame and one continuous motion, not a 30-second timestamped
timeline; only H3 makes audio.

## How to write a shot list

1. **Load `craft.md` first.** It is the model-agnostic layer — bible, concrete
   instructions, focus, finishing, stills-first, performance. It gates everything.
2. **Route** to a driver (below) and write to that driver's format.
3. **For any performance or action beat,** get the observable beats from the
   `direct-performance` skill and paste them in as the shot's action; do not write
   the mood word yourself.
4. **Run `slop-gate.md`** against the finished list. Fix every hit, then re-read the
   gate. Emit only when it is clear.

## Output contract — non-negotiable

- The response is the YAML shot list and nothing else. No preamble, no fences, no
  explanation, no sign-off.
- The YAML must parse and must match the target driver's format below, so the driver
  runs it unedited.
- **Never write the cinematic style suffix into a prompt.** Every driver appends its
  own `DEFAULT_STYLE_SUFFIX` at render time. Writing it again double-applies it.
  Set `style_suffix:` only to override, or `""` to disable.
- No duration or resolution text inside prompts — those live in the top-level YAML
  keys (`num_frames`, `fps`, `width`, `height`, `seconds`).
- Never ask a clarifying question. Commit to one direction and write.

## Routing

When the user names a driver, use it. Otherwise:

| The idea is… | Driver | Format |
|---|---|---|
| Still panels / coverage / a storyboard / a character sheet in scene | `storyboard.py` | STORYBOARD |
| Motion from a start frame, no dialogue needed | `video_shot.py` | WAN-I2V |
| A talking shot, a voice line, or sound matters | `h3_ref2v.py` / `h3_t2v.py` | H3 |

The Runway "Burst method" maps to STORYBOARD (generate coverage) plus a video driver
(animate a chosen frame). The operator picks which frames feed the video step with
`scripts/extract_frames.py`.

## STORYBOARD (storyboard.py — Flux + Flux Kontext)

Panels 2..N are in-context edits of the reference (or of panel 1), so identity
holds. Panel 1 sets the aspect; later panels snap to Kontext buckets off the
reference aspect. Set `width`/`height` to the target aspect and the sheet follows
(1024×576 ≈ 16:9).

```yaml
reference: ./refs/<name>.png   # optional; omit to seed panel 1 from the first prompt
lora: film-storyboard.safetensors
lora_weight: 0.85
guidance: 2.5
steps: 24
seed: 42
width: 1024
height: 576
shots:
  - "wide establishing shot, <subject> in <place>, <action>"
  - prompt: "close-up, <detail>"
    seed: 9999
```

- One panel = one moment. Vary shot size and angle panel to panel; that is coverage.
- LoRA triggers: `film-storyboard.safetensors` has none; `Storyboarding-v2-Flux`
  wants `storyboarding`; `StoryboardSketch-Flux` wants `Storyboard sketch`. Add the
  trigger into each prompt only for a LoRA that needs one.

## WAN-I2V (video_shot.py — WAN 2.2 image-to-video)

> WAN 14B is the hardware red flag in CLAUDE.md — the driver's preflight gate handles
> safety. Write the shot list; do not run it.

WAN carries identity and scene from the **start frame only**. Each shot needs an
`image:` (a rendered frame — a storyboard panel or a character-sheet crop) and a
`prompt:` describing **one continuous motion**, about 5 seconds. No dialogue, no
audio, no timeline.

```yaml
num_frames: 81          # ~5s at 16fps
fps: 16
width: 832              # divisible by 32
height: 480
seed: 42
shots:
  - image: ./plates/<frame>.png
    prompt: "<one motion: a gesture, a look, a slow camera move>"
  - image: ./plates/<frame>.png
    prompt: "<one motion>"
    num_frames: 121     # a longer beat
```

- One action and one camera move per shot. A second beat drifts.
- For a longer story, write several shots, each off its own start frame, in order.
- Do not set `negative_prompt` unless the user asks — the default is tuned.

## H3 (h3_ref2v.py with refs, or h3_t2v.py for text only)

MiniMax H3 makes the clip and its soundtrack in one pass — the only local path to
voice and sound. Clips are short (~3–5s; the frame count snaps to a 17k+5 grid).
References are addressed positionally as `<Picture 1>`, `<Picture 2>` … in supply
order (up to 9); references drift, so restate identity in words too.

```yaml
title: <name>
seconds: 5
width: 608
height: 352
seed: 7
steps: 4
ref_image_size: match
references:                 # order sets <Picture 1>, <Picture 2>, ...
  - refs/<subject>.png
shots:
  - label: <beat>
    prompt: "<Picture 1>, <who they are in words>, says \"<dialogue verbatim>\", <sound>"
```

- Quote dialogue verbatim; place the speaker with it.
- Cite each `<Picture i>` and describe what must stay fixed (face, wardrobe, build).
- For a voice-capture shot, state "no music, only the voice and ambience."
- For text-to-clip with sound and no reference, target `h3_t2v.py`: a single prompt
  string carries subject, action, and any spoken line.

## Intake and self-check

Intake tiers: **BARE** — invent subject, action, coverage. **SPARSE** — honor the
anchors, invent the rest. **DETAILED** — serve the vision, quote dialogue verbatim,
fill only technical gaps. Commit; never hedge.

Before sending:

1. `craft.md` applied; the project bible (if any) locked, only deltas described.
2. One driver chosen; the YAML matches that format exactly and parses.
3. No style suffix written into any prompt.
4. Performance/action beats came from `direct-performance`, not a mood word.
5. `slop-gate.md` read against the list; every hit fixed.
6. Output is the shot list alone — no commentary, no fences.

## Worked examples

One rooftop scene written for all three targets:

- `examples/enhancer_storyboard.example.yaml` — coverage panels
- `examples/enhancer_wan_i2v.example.yaml` — one-motion clips off chosen frames
- `examples/enhancer_h3_voice.example.yaml` — a spoken line with sound
