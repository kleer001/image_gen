# Production workflow: consistent characters, voices, scenes

The local version of Runway's "Game of HORSE" workflow (see `RUNWAY_LOCAL.md` for
where it comes from). It chains the drivers this repo already has into one path:
build a character, lock it across shots, give it a voice, and cut the result.

Each step names the local tool and its real limit. The `shot-enhancer` skill writes
the shot-list YAML that the video steps consume, the `direct-performance` skill
writes the acting and action beats, and both obey the project bible.

## 0 — The bible

Before the shots, build the film's reference — its world, locations, characters, and
look — from real places, objects, and clothing. `examples/bible.example.md` is the
template. This is the single source of truth for consistency: the `shot-enhancer`
craft layer locks everything the bible establishes and lets each prompt describe
only the deltas. Keep it under `refs/` with the operator's own material.

## 1 — Story

Model-agnostic. Build on cause and effect: one action triggers the next. Give a
character a want, put an obstacle in the way, show it rather than explain it, end
changed from the start, and cut anything that serves none of those.

## 2 — Character and character sheet

Iterate the character with Flux text-to-image (`flux_txt2img_run.py`) or Illustrious
for stylised work. Render on a **solid neutral-gray background** under soft
directional key light — white blows out face edges and bakes in plastic skin (see
the character-sheet craft in `CLAUDE.md`).

Then build the sheet:

```bash
scripts/flux2_character_sheet.py "a wiry man in his 40s, shaved head, leather jacket"
```

This emits front / side-profile / back / face-close-up with identity locked by
reference edit. That sheet is the reference the later steps consume. Build one per
main character.

## 3 — Wardrobe

Edit the sheet for each wardrobe look with Flux Kontext:

```bash
scripts/kontext_edit.py "change the jacket to a red mascot costume" --ref <sheet.png>
```

Keep one sheet per look, so a beat that changes costume has its own reference.

## 4 — Location and the Burst method

Render location candidates with Flux text-to-image. Then the **Burst method**:
generate one short clip and pull the frames you like as coverage, rather than
iterating stills. One generation fixes continuity because every frame is from the
same pass.

Generate the clip with the video driver:

```bash
scripts/video_shot.py shots.yaml     # WAN 2.2 I2V — animates a start frame
```

or, when the beat needs sound, `scripts/h3_t2v.py`.

Pull the frames you like into `plates/` with the frame extractor:

```bash
scripts/extract_frames.py clip.mp4 --browse                 # labelled contact sheet, find a frame/second
scripts/extract_frames.py clip.mp4 --at 2.5 --prefix lantern  # save that frame to plates/
```

`--browse` opens a contact sheet where each thumbnail shows its frame index and
timestamp; `--at` (seconds) or `--frame` (index) then saves the exact picks as
`plates/<prefix>_NN.png`, ready as start frames for step 6.

## 5 — Character voice

MiniMax H3 is the only local path that generates sound. It makes the clip and its
soundtrack in one pass, so a voice comes from a video generation, not a standalone
text-to-speech step.

```bash
scripts/h3_ref2v.py voice.yaml       # <Picture i> references + a spoken line
```

Use a scene frame as a reference, prompt the character to say a plain sentence, and
name no music, so the output carries the voice alone. Keep or swap the voice by
re-rolling the seed or the reference.

## 6 — The performance and the shot prompt

Direct the acting before you render it. For any beat a character feels or does, the
`direct-performance` skill breaks the state into observable behavior, timing, sound,
and body — the fix for the exaggerated, generic performance that reads as AI. It
also choreographs action beats into contact → force → reaction with a time window.

Then turn the beat into a shot list with the `shot-enhancer` skill. It loads its
craft layer first, obeys the bible, writes YAML for whichever driver fits, and runs
an anti-slop gate before emitting. Run two variations per beat, so the edit has
coverage to choose from.

The agent drafts the prompts; you review the YAML before rendering, and correct it.
The prompt is a draft to direct, not a result to accept.

**Camera you cannot get by prompting.** When a shot needs an exact move the prompt
will not deliver, the prompt alone is the wrong tool. The local escalation is a
driving plate: an AnimateDiff camera-motion LoRA (zoom / pan / tilt, in
`models/animatediff_motion_lora/`), or a hand-rendered move, used as a motion
reference. There is no local 3D-stage equivalent to Flick's; this is the gap. See
gate row S8.

## 7 — Edit

Assemble the clips end to end in any editor. Keep the parts that flow, cut the parts
that break, and build toward the story from step 1. This step is outside the repo.

## The chain, at a glance

```
bible  →  story  →  character (Flux)  →  sheet (flux2_character_sheet)
       →  wardrobe (kontext_edit)  →  location (Flux) + Burst (video_shot / h3_t2v → frames)
       →  voice (h3_ref2v)  →  performance (direct-performance)  →  shot list (shot-enhancer)
       →  render (video_shot / h3)  →  edit
```

## What does not carry over from Runway

- **Seedance 2.5's 30-second timestamped timeline** — WAN animates one ~5s motion
  from a start frame and does not read timestamps. Sequence by rendering several
  shots, each off its own frame, not by one long timeline prompt.
- **Native audio on the main video model** — only H3 makes sound locally, and H3
  clips are short. Voice and motion may come from two different generations.
- **A single reference-to-video call with many `@image` refs** — H3's `<Picture i>`
  path is the closest (up to 9 refs); WAN carries identity through the start frame
  only. WAN 2.1 VACE is the catalogued migration target for true multi-image
  conditioning (see `models.yaml`), not yet installed.
