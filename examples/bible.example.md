# Project bible — <film title>

The project bible is **data**, not code: the single reference that keeps a film
consistent across every shot. The `shot-enhancer` craft layer locks everything this
file establishes and lets each prompt describe only the deltas. Build it from real
references — real places, objects, clothing — so the world has a source outside the
model's average.

This is a template. Copy it per film, keep it with the operator's own material
(under `refs/`, which is gitignored), and fill every section from real references.
Delete the guidance lines as you go.

## Logline

One or two sentences: who, where, what they want, what stands in the way.

## World

The rules the whole film obeys.

- **Terrain / setting** — the real place it draws on, and the specific traits taken
  from it (e.g. Hadrian's Wall → exposed dark rock, shallow soil, short ridge grass,
  denser vegetation in the sheltered valley).
- **Materials** — the named materials that recur: aged wood, aged iron, grime, damp.
- **Lighting** — the light the world is under, as checkable relationships: source,
  direction, which surfaces are brighter, how fast it falls off.
- **Palette** — named colors, including the shadow cast (e.g. muted cool blue-gray,
  slight gray-violet in shadow).
- **Weather / time of day** — the default, and any per-act change.

## Locations

One handbook block per location: terrain, vegetation, materials, lighting, and the
fixed elements that must read the same every time the location appears.

## Characters

One block per character.

- **Identity anchors** — 15–20 specific physical attributes (face, hair, build, age,
  distinguishing marks). These are held word-for-word across shots.
- **Wardrobe** — the default look, plus a separate entry per beat where it changes.
- **Voice** — timbre, accent, pace, and how the voice moves under stress.
- **Reference sheet** — the character-sheet image the drivers condition on
  (`flux2_character_sheet.py`), on neutral gray under a soft key.

## Look

- **Lens grammar** — default shot sizes, the moves the film uses, the moves it avoids.
- **Focus** — how depth of field is used; who is usually the focal subject.
- **Finishing** — the restrained grain / sensor noise / lens softness the film wears.
- **Sound policy** — when there is music and when there is not.

## Continuity anchors

The short strings repeated verbatim to stop drift: identity strings per character,
the established light direction, screen direction across a cut.
