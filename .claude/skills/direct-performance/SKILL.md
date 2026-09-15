---
name: direct-performance
description: Direct a believable performance or action beat for AI video and stills — turn an emotional state or a fight move into observable behavior with timing, sound, and physical reaction, instead of a mood word that produces generic, exaggerated acting. Covers moving performance (an emotional arc over time), action choreography, and a single expressive still (one frozen beat). The output is a compact beat description that drops into a shot prompt (hand it to the shot-enhancer skill to wrap into a WAN, H3, or storyboard shot list). Use when the user wants the acting to feel real or "not exaggerated", asks to direct or block a performance, to decompose an emotion into behavior, to choreograph an action or fight beat with exact timing, or to get an expressive face in a still.
---

# direct-performance — behavior, not mood words

A model asked for "she looks sad" returns the international sign of sadness — a
downturned mouth, maybe a tear — and it reads as slop. A director never accepts
that. The fix is not better rendering; it is direction. Translate the intent into
observable behavior, timing, sound, and physical reaction the model can render and
you can check.

Output: the direction text only — a compact block ready to paste as a shot prompt's
action. No commentary. Hand it to `shot-enhancer` to place into a driver's YAML.

Pick the mode from the request.

## PERFORMANCE — an emotional beat over time (WAN / H3)

**1. Establish first.** State the character's personality, their circumstance, what
they want in this moment, what they are suppressing, and where their attention
actually is. A beat plays a motivation, not a label.

**2. Name the exact state, not the category.** Not "sad." Cold, exhausted, grieving,
and still trying to keep the song going — a specific mix. That mix changes every
choice below.

**3. Stage the emotional arc.** A believable performance moves; a stiff one holds one
face. Direct the whole shape, not the final expression:

> **Trigger → Resistance → Leakage → Release → Aftermath**

What starts the feeling, how the character tries to hide it, which involuntary
reactions escape, the peak, and what is left after. Skipping to the final state is
the most common tell.

**4. Render each stage in four channels:**

- **Behavior** — what they do, in order. Small actions, not a summary.
- **Timing** — pauses, hesitations, a gaze that lands half a second late.
- **Sound** — breath, a caught word, a restrained sob, the voice thinning. This
  channel is why H3 carries a spoken performance; WAN cannot.
- **Body** — hands, shoulders, a tremor, a grip tightening.

Keep it restrained. Micro-expressions that flicker and get controlled read as real;
melodrama reads as AI.

**Camera for a performance.** Give the face the frame: an eye-level close-up or
medium close-up, and **one restrained move** — a very slow push-in or a slight
handheld drift — so the camera does not compete with the performance.

**Micro-behavior library** (name the visible change, not the emotion):

- **Holding back tears** — lips press together, the jaw tightens, one swallow, a
  small unsteady breath; control breaks only after moisture gathers on the lower lid.
- **Embarrassment** — the gaze drops, the shoulders draw inward, the fingers tighten
  on whatever they hold.
- **Suppressed anger** — the jaw clenches, the lips flatten, breathing goes controlled
  and nasal, the shoulders stay rigid.

**Worked beat.** State: cold, exhausted, grieving, still trying to sing.

> She sings only a few words at a time. Her breath interrupts the phrase and she
> stops. A tiny restrained sob slips out. She takes a very small inhale and tries
> again. Her fingers tremble on the amulet; she tightens her grip slightly, and a
> shiver travels through her shoulder.

## STILL — one expressive frame (storyboard / start frame)

A still cannot play the arc; it holds one instant. So choose the single most legible
beat — usually the **leakage** or the **controlled peak** — and describe that frozen
physical state exactly. Read the moment off the arc above, then freeze it.

- Describe the state as caught mid-motion, not posed: a breath held partway, a look
  landing, a muscle mid-tension.
- Favor asymmetry and restraint — a one-sided mouth, a single tightened brow, a moist
  lower lid — over a full symmetric expression, which reads as a stock emoji.
- Same framing rule: eye-level close-up or medium close-up so the small changes have
  the pixels to show.

For **exact** still control beyond the prompt, the LivePortrait Expression Editor
(scaffolded; see TODO.md) dials brows, eyes, pupils, mouth, and smile on a rendered
face, and `kontext_edit.py` can edit an expression in context. Prefer a subtle dial
over an expression LoRA, which tends to push toward exaggerated, acted faces.

**Worked still.** State: suppressed anger, the controlled peak.

> Eye-level close-up, caught mid-breath: the jaw is clenched, the lips flattened to a
> hard line, one brow slightly lower than the other, the nostrils just flared on a
> held nasal breath. The eyes are fixed and still. Nothing moves; everything is held.

## ACTION — a physical or fight beat (WAN)

Break each move into **contact → force → reaction → next move**, and give the beat a
**time window**. If the intent is speed, name the count and fit the beats inside it:
"three strikes in one second" means three described strikes, each with its target and
the response, all inside that second — not a blur.

**Worked beat.** Intent: he is extremely fast, three strikes in one second.

> Within one second: a straight punch lands on the guard's forearm, snapping it
> aside; a second strike drives into the ribs and folds him forward; a rising third
> catches the jaw and throws his head back. Each contact is distinct, the body
> reacting to each before the next lands.

## Which driver carries a performance

- **H3** (`h3_ref2v.py`) — voice and body together, ~5s. Choose it for a spoken or
  vocal performance.
- **WAN** (`video_shot.py`) — body and motion from a start frame, ~5s, no sound.
  Choose it for a silent physical beat or an action move.
- **Storyboard / start frame** (`storyboard.py`) — a single expressive still (STILL
  mode), which then becomes a WAN start frame under the stills-first rule.

Write the beats the same way for each; the shot-enhancer skill fits them to the
target's format and length.
