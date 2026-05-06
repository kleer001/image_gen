#!/usr/bin/env python3
"""Convert ComfyUI UI-format workflow JSON to API format.

Reads /object_info from a running ComfyUI to resolve widget order per class.
Drops Note nodes; folds PrimitiveNode literals into their consumers.

Usage: python3 scripts/ui_to_api.py <file.json> [<file.json> ...]
       Writes API JSON to stdout if one arg, else overwrites each file in place.
"""
import json
import sys
import urllib.request
from pathlib import Path

OBJECT_INFO_URL = "http://127.0.0.1:8188/object_info"


def fetch_object_info():
    with urllib.request.urlopen(OBJECT_INFO_URL, timeout=15) as r:
        return json.load(r)


def is_ui_format(doc):
    return isinstance(doc, dict) and "nodes" in doc and "links" in doc


_WIDGET_PRIMS = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}
_MISSING = object()


def is_widget_typed(spec):
    if not isinstance(spec, list) or not spec:
        return False
    t = spec[0]
    if isinstance(t, list):
        return True
    return t in _WIDGET_PRIMS


def widget_default(spec):
    if not isinstance(spec, list) or not spec:
        return _MISSING
    t = spec[0]
    opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
    if "default" in opts:
        return opts["default"]
    if isinstance(t, list) and t:
        return t[0]
    if t == "BOOLEAN":
        return False
    return _MISSING


def convert(ui, oi):
    nodes = ui["nodes"]
    links = ui.get("links", []) or []

    # 1. PrimitiveNode literal map: link_id -> literal value
    prim_links = {}
    prim_node_ids = set()
    for n in nodes:
        if n["type"] != "PrimitiveNode":
            continue
        prim_node_ids.add(n["id"])
        wv = n.get("widgets_values") or []
        literal = wv[0] if wv else None
        for out in n.get("outputs", []) or []:
            for lid in out.get("links") or []:
                prim_links[lid] = literal

    # 2. Link map: link_id -> (from_node_id, from_slot), excluding PrimitiveNode sources
    link_map = {}
    for ln in links:
        # [link_id, from_node, from_slot, to_node, to_slot, type]
        lid, from_node, from_slot = ln[0], ln[1], ln[2]
        if from_node in prim_node_ids:
            continue
        link_map[lid] = (from_node, from_slot)

    api = {}
    for n in nodes:
        ntype = n["type"]
        if ntype in ("Note", "PrimitiveNode"):
            continue
        nid = str(n["id"])
        spec = oi.get(ntype)
        if spec is None:
            raise RuntimeError(f"node id {nid}: class {ntype!r} not in /object_info")

        node_inputs = n.get("inputs", []) or []
        excluded = {inp["name"] for inp in node_inputs}

        out_inputs = {}

        # Link inputs (and PrimitiveNode-driven widget inputs, which appear here as links)
        for inp in node_inputs:
            link_id = inp.get("link")
            if link_id is None:
                continue
            name = inp["name"]
            if link_id in prim_links:
                out_inputs[name] = prim_links[link_id]
            elif link_id in link_map:
                from_node, from_slot = link_map[link_id]
                out_inputs[name] = [str(from_node), from_slot]
            else:
                raise RuntimeError(
                    f"node {nid} ({ntype}) input {name!r}: dangling link id {link_id}"
                )

        # Widget inputs from widgets_values, in input_order, skipping excluded names
        widgets_values = n.get("widgets_values")
        input_order = spec.get("input_order", {}) or {}
        order = list(input_order.get("required", [])) + list(input_order.get("optional", []))
        input_specs = spec.get("input", {}) or {}
        req_specs = input_specs.get("required", {}) or {}
        opt_specs = input_specs.get("optional", {}) or {}

        if isinstance(widgets_values, dict):
            # Dict form: keyed directly by widget name (e.g. VHS_VideoCombine)
            for name in order:
                if name in excluded:
                    continue
                ispec = req_specs.get(name) or opt_specs.get(name)
                if not is_widget_typed(ispec):
                    continue
                if name in widgets_values:
                    out_inputs[name] = widgets_values[name]
                else:
                    dflt = widget_default(ispec)
                    if dflt is not _MISSING:
                        out_inputs[name] = dflt
        else:
            widgets_values = widgets_values or []
            wi = 0
            for name in order:
                ispec = req_specs.get(name) or opt_specs.get(name)
                if not is_widget_typed(ispec):
                    continue
                # Advance index for every widget-typed slot, even when linked,
                # because ComfyUI retains the value in widgets_values after a
                # widget is converted to an input.
                if wi < len(widgets_values):
                    value = widgets_values[wi]
                    wi += 1
                else:
                    value = _MISSING
                if name not in excluded:
                    if value is _MISSING:
                        dflt = widget_default(ispec)
                        if dflt is not _MISSING:
                            out_inputs[name] = dflt
                    else:
                        out_inputs[name] = value
                schema_cag = (
                    isinstance(ispec, list)
                    and len(ispec) > 1
                    and isinstance(ispec[1], dict)
                    and ispec[1].get("control_after_generate")
                )
                # ComfyUI's UI also injects a control_after_generate slot for any
                # input named 'seed'/'noise_seed'/'rand_seed' even when the schema
                # doesn't flag it (e.g. HyVideoSampler.seed, WanVideoSampler.seed).
                name_cag = name in ("seed", "noise_seed", "rand_seed")
                # CAG slot follows seed-like widgets in widgets_values. Older
                # ComfyUI exports stored a string ('fixed'/'increment'/...),
                # newer ones may store a boolean toggle. Skip unconditionally.
                if (schema_cag or name_cag) and wi < len(widgets_values):
                    wi += 1

        api[nid] = {"class_type": ntype, "inputs": out_inputs}

    return api


def main(argv):
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    paths = [Path(p) for p in argv[1:]]
    oi = fetch_object_info()
    if len(paths) == 1:
        ui = json.loads(paths[0].read_text())
        if not is_ui_format(ui):
            raise RuntimeError(f"{paths[0]}: not UI format (missing 'nodes'/'links')")
        api = convert(ui, oi)
        json.dump(api, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    for p in paths:
        ui = json.loads(p.read_text())
        if not is_ui_format(ui):
            print(f"SKIP (already API or unknown): {p}", file=sys.stderr)
            continue
        api = convert(ui, oi)
        p.write_text(json.dumps(api, indent=2) + "\n")
        print(f"OK  {p}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)
