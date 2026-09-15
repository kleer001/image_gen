# Slop gate — run before emitting

A shot list is not finished until it passes this gate. Read each row against the
shot list you wrote. For every hit, apply the fix and rewrite the shot, then read
the gate again. The gate is mechanical: it does not judge taste, it catches the
tells that read as AI-generated.

| Code | Tell | Cause | Cheapest fix |
|---|---|---|---|
| S1 | Plastic, glossy skin | Character rendered on white; blown highlights | Neutral-gray background, soft directional key, no blown highlights (craft: Skin) |
| S2 | Generic "cinematic" look | Vague style words | Replace with visible light / palette / material instructions (craft: Concrete) |
| S3 | Exaggerated, generic emotion | A mood word instead of behavior | Break the state into behavior + timing + sound + body via `direct-performance` |
| S4 | Busy, noisy frame | Asking for more objects / detail everywhere | Name one focal subject; let the rest fall off; re-render existing objects (craft: Change what is rendered) |
| S5 | Character drifts between shots | Identity restated loosely | Hold identity anchors word-for-word; WAN carries them through the start frame, H3 through `<Picture i>` restated in words |
| S6 | Motion wanders or over-cuts (WAN) | More than one beat in a WAN prompt, or a timeline | One continuous motion per WAN shot; WAN does not read timestamps |
| S7 | Razor-sharp, video-game clean | No lens character | Add restrained grain, sensor noise, mild lens softness, slight chromatic aberration — thin, after light and materials (craft: Restrained finishing) |
| S8 | Camera ignores the direction | The move is only described in words | Try the prompt first; escalate to a driving plate (AnimateDiff camera LoRA, or a hand-rendered move) used as reference — see the 3D-camera note in PRODUCTION_WORKFLOW.md |
| S9 | Voice fights the music (H3) | Music left unspecified | For a voice-capture shot, state "no music, only the voice and ambience" |
| S10 | World looks different each scene | No bible, or the bible ignored | Lock the bible; describe only deltas (craft: Obey the bible) |
| S11 | Double-applied cinematic haze | Style suffix written into the prompt | Remove it — the driver appends its own suffix at render time |

When every row is clear, the shot list may be emitted.
