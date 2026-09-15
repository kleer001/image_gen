# showcase/

Self-contained pages that show a capability of this stack working, built from real
render outputs.

## liveportrait.html

The LivePortrait validation page: the retargeting clip (a driving performance
transferred onto one portrait) and the four dialed expression stills, each with its
exact ExpressionEditor parameters. Assets are embedded, so the file opens on its own
with no server and no external files.

- **Live page:** https://claude.ai/artifact/P9Hq12UyhBJGKN6FuzDVxF
- **Built by:** `build_showcase.py`, from the validation renders in `comfyui/output`.

Rebuild after new renders:

```
comfyui/.venv/bin/python showcase/build_showcase.py
```

The render outputs live under `comfyui/output` (gitignored). If they have been
cleared, re-run the LivePortrait drivers first — see the LivePortrait section of
`../TODO.md` and `../PRODUCTION_WORKFLOW.md`.
