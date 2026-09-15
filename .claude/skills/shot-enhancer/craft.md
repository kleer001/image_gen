# Craft — the model-agnostic layer

Load this before writing any shot list. These rules hold for every driver; the
per-driver format sits on top of them. They are what separates a directed frame
from AI slop.

## Obey the bible

If the project has a bible (a director's / world / character reference, see
`examples/bible.example.md`), it is the source of truth. Lock everything it
establishes — terrain, materials, lighting, palette, identity anchors, lens
grammar. A prompt then describes only the **deltas and the missing information**,
never the whole world again. No bible yet: write the shot, and note in one line
what a bible would pin so the operator can start one.

## Concrete, not vague

Replace every style word with a visible instruction the result can be checked
against.

- Not "cinematic light" → name the source, direction, and falloff: "bright foggy
  afternoon daylight through the doorway; the doorway-facing surfaces are brighter,
  the surfaces facing into the room fall into deep shadow with a fast falloff."
- Not "nice colors" → a named palette: "muted cool blue-gray, a slight gray-violet
  cast in the shadows."
- Not "detailed" → named materials: "aged wood, aged iron, grime, damp surfaces."

Every clause should describe a relationship you can see in the output and correct.

## Change what is rendered, not how much is there

Direct the transformation of the objects already established. Do not ask for more
objects or more detail everywhere — that is how a frame turns to noise. Name the
focal subject and let the rest fall off: "the face and upper body are the focal
subject; the foreground, the doorway, and the deeper room fall out of focus." The
subject is the clearest part of the frame, not unnaturally razor-sharp.

## Restrained finishing

After light and materials are right, add finishing as a thin top layer, never as a
substitute for them: subtle grain, mild sensor noise, slight lens softness, a
little chromatic aberration. Restraint is the point — heavy finishing reads as a
filter, not a lens.

## Stills first

A video model mostly re-animates what the still already decided, and fixing a still
is cheaper than re-rolling a clip. Get the frame right first — with the storyboard
and Kontext-edit path — then animate it. A weak start frame cannot be rescued by a
motion prompt.

## Show, do not tell; hold identity

Write what is visible and audible, not the abstract state behind it. For anything a
character feels or does, do not write the mood word — break it into observable
behavior with the `direct-performance` skill, then paste those beats in as the
action. Hold identity anchors word-for-word across shots; a paraphrase is a drift.

## Skin

Render characters on a solid neutral-gray background under a soft directional key
light, never pure white — white kicks light back into the face, blows out the edges,
and bakes in the plastic look that then fights every scene the character is
composited into.
