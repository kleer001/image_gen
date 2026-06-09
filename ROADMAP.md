# ROADMAP — buildable next steps

Forward-looking backlog for taking this stack from "image gen + scaffolded video"
to the full render → identity-lock → finish pipeline the Seedance-style workflow
implies, built entirely on local OSS. This is the *what could be built* list;
`TODO.md` is the separate *confirm-on-rig* checklist for things already scaffolded.

Priority key: **P1** unblocks the core video pipeline · **P2** rounds out the
Seedance-parity feature set · **P3** polish / hygiene.

---

## Video pipeline completion

- [ ] **P1 — Promote the two scaffolds.** Once validated per `TODO.md`, move
      `scaffolds/wan_vace_r2v.json` and `scaffolds/video_post_upscale_interp.json`
      into `workflows/`, restart so the MCP registers them, repoint each driver's
      `WORKFLOW_FILE`, and strip the `_scaffold` keys.
- [ ] **P1 — Render-through-finish.** Add a `--post` flag (or a thin meta-driver)
      so `video_shot.py` / `video_vace.py` can hand their output clips straight to
      `video_post.py` — one command from start frame to upscaled/interpolated clip.
- [ ] **P2 — Audio / lip-sync.** The dialogue scenes ("that's a lot of jacket…")
      need speech-driven video. Three paths: (a) **Ovi** (installed) — one-pass
      video+native voice, but the voice isn't cloneable; (b) **voice_loom** (sister
      repo, `omnivoice` voice-clone TTS) → audio-driven lip-sync (**EchoMimicV3**
      lightest, or Sonic) on a character frame, for a consistent per-character cloned
      voice; (c) catalog `Wan-AI/Wan2.2-S2V-14B` (reuses WAN VAE + UMT5) as the
      integrated start-frame+audio option. Reference: radar digest.
- [ ] **P2 — LTX-2.3 fast-draft engine.** Add LTX-2.3 (fp8/distilled) as a
      low-latency T2V/I2V path for blocking shot timing before committing slow WAN
      renders — and it carries synchronized audio. Catalog + workflow + driver.
- [ ] **P3 — First-last-frame (WAN FLF2V).** Controlled shot transitions by
      pinning both endpoints (a node exists in the WAN ecosystem). Good for match
      cuts and loops.
- [ ] **P3 — Long shots (FramePack).** For clips beyond WAN's ~5s window without
      OOM. Catalog + workflow.

## Character / identity tooling (the front half of the workflow)

- [x] **P1 — Character reference-sheet generator.** Done via FLUX.2 Klein 9B
      (`scripts/flux2_character_sheet.py`, isolated `:8189` instance): a t2i seed on
      neutral-gray + soft key, then reference-locked edits for a front/profile/back/
      face turnaround — emits the `reference:` image the video drivers consume.
      Identity-lock is Klein reference-edit, not Kontext.
- [ ] **P2 — Outfit swap.** A Kontext recipe/workflow for "put outfit X onto
      character Y" (the video's outfit-swap skill), with a note to carry tattoos/
      markings explicitly in the prompt.
- [x] **P2 — Install skin-realism LoRAs.** Done: `aidmaRealisticSkin` ("No plastic")
      and `PortraitEngine-v2.0-Flux` installed + cataloged. Fills the realism gap
      (style-heavy LoRA library had no skin detailer). Note: these target **Flux.1-dev**
      workflows — the FLUX.2 Klein character sheet doesn't load Flux.1 LoRAs.
- [ ] **P2 — Multi-plate scene composition (needs VACE).** Once VACE is live, a
      driver that takes character + outfit + location plates and composes a scene —
      the open analog to Seedance's `@image1..@imageN` conditioning.

## Prompt / skill layer (the actual "skills" from the video)

- [ ] **P2 — Shot-prompt skill.** A Claude skill (or prompt-template module) that
      emits WAN/VACE-formatted shot prompts with the camera + atmospheric-depth +
      handheld conventions baked in — the local analog of the creator's "skills".
      Include a camera vocabulary (Dutch angle, operator shake, push-in, dolly) and
      reference-tagging.
- [ ] **P3 — Storyboard → video bridge.** Take an approved storyboard sheet and
      auto-generate the matching video shot list (panels become start frames /
      references), so the storyboard and video drivers chain.

## Camera control

- [ ] **P3 — Handheld/operator-shake for WAN.** The stack's camera-motion LoRAs are
      SD1.5+AnimateDiff only; WAN has none. Capture a reusable prompt fragment, and
      track whether a WAN motion-control LoRA / node lands (radar).

## Delivery / review UX

- [ ] **P2 — Unify the HTML galleries.** `storyboard.py`, `video_shot.py`, and
      `video_post.py` each hand-roll a near-identical gallery. Extract one shared
      `gallery.py` helper (grid + figure/caption + serve + open-in-browser); the
      three drivers already duplicate `free_port` / `serve` / `open_in_browser` too.
      Real DRY win and one place to improve review UX.
- [ ] **P3 — Post-chain before/after.** Side-by-side source vs. upscaled+interpolated
      in the gallery; add download links and per-clip re-roll.
- [ ] **P3 — Audio in the gallery.** S2V/LTX outputs carry audio; the `<video>`
      tags are currently `muted`. Add an unmuted/with-audio mode for those drivers.

## Catalog / infra hygiene

- [ ] **P2 — Fill the VACE size.** `models.yaml` has the VACE fp8 entry at `size: 0`
      (placeholder). Set the real byte size once downloaded; confirm the fp8
      single-file path doesn't need `merge_wan_shards.py`.
- [ ] **P3 — Refresh INDEX.md.** Dated `2026-05-08`; add VACE / LTX / S2V once
      installed (the sync hook appends unindexed files, but video models want
      hand-written VRAM/wrapper notes).
- [ ] **P3 — Dedupe FilmNoir LoRA.** `INDEX.md` flags `ClassicNeoFilmNoir-Flux` and
      `FilmNoir-v1-Flux` as the same model (same CivitAI versionId). Remove one.
- [ ] **P3 — Storyboard example.** `examples/` only has video shot lists; add a
      `storyboard.example.yaml` to match (format currently lives only in the
      `storyboard.py` docstring).
- [x] **P3 — Periodic radar cadence.** Done: `UPDATE.html` is the Claude-facing
      update-sweep runbook (extends the radar to cover **workflows** too); a
      `SessionStart` hook (`scripts/check_sweep_due.py`) nudges when the newest
      `radar/` digest is > 7 days old, and `scripts/update_sweep.sh` drives an
      unattended weekly `claude -p` run via cron.

## Validation (once the stack is up)

- [ ] **P1 — End-to-end smoke.** With `imggen` running, push one 1-shot render
      through each driver (`video_shot.py`, then the promoted VACE and post drivers)
      to confirm the live path, not just the Python logic (which is unit-smoke-tested).
