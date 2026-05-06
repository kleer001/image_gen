# API Usage (no MCP required)

ComfyUI exposes an HTTP API on port `8188`. Any process on this machine — another repo's script, a shell pipeline, a different Claude Code session — can submit workflows directly. Use this when you don't want to (or can't) load the MCP server.

**MCP vs direct API:**
- **MCP** — only available when Claude Code starts in a directory whose `.mcp.json` lists the server. Loaded once per session.
- **Direct API** — works from anywhere as long as `imggen` is running. No session coupling.

## Prerequisites

```bash
imggen status       # confirm ComfyUI is on :8188
imggen              # if not, start it (~30s)
```

The MCP server (port 9000) is **not** required for this path.

## Endpoints

| Verb | Path | Purpose |
|------|------|---------|
| POST | `/prompt` | Queue a workflow. Body: `{"prompt": <workflow-dict>}`. Returns `{"prompt_id": "..."}`. |
| GET  | `/history/{prompt_id}` | Poll for completion. When done, returns `{prompt_id: {outputs: {...}, status: {...}}}`. |
| GET  | `/view?filename=...&subfolder=...&type=output` | Download a generated asset. |
| GET  | `/queue` | Inspect queue. |
| POST | `/queue` with `{"delete": [prompt_id]}` | Cancel. |

## Workflow JSONs

Files in `workflows/` are ComfyUI **API-format** dicts keyed by node ID. Two ways to customize them:

**1. Mutate in place (current default).** Workflows ship with baked-in prompts/seeds/dims. Load the JSON, change the field, POST.

**2. PARAM placeholders.** If a node input is a string like `"PARAM_PROMPT"` or `"PARAM_INT_STEPS"`, substitute before submitting. Convention (matches the MCP server):

| Placeholder | Type | Example field name after stripping |
|---|---|---|
| `PARAM_PROMPT` | str | `prompt` |
| `PARAM_INT_<NAME>` | int | `<name>` (lowercased) |
| `PARAM_FLOAT_<NAME>` | float | `<name>` |
| `PARAM_BOOL_<NAME>` | bool | `<name>` |
| `PARAM_STR_<NAME>` | str | `<name>` |

Bare `PARAM_<name>` (no type token) defaults to `str`. The same placeholder may appear on multiple nodes/inputs — substitute all of them.

## Curl recipe

```bash
# 1. Edit a workflow with jq (set the prompt on node "6")
WF=$(jq '.["6"].inputs.text = "a fox in a snowy forest, cinematic"' \
        workflows/flux_txt2img.json)

# 2. Queue it
PROMPT_ID=$(curl -s -X POST http://127.0.0.1:8188/prompt \
  -H 'Content-Type: application/json' \
  -d "{\"prompt\": ${WF}}" | jq -r .prompt_id)
echo "queued: $PROMPT_ID"

# 3. Poll until outputs appear
while :; do
  OUT=$(curl -s "http://127.0.0.1:8188/history/${PROMPT_ID}" | jq ".\"${PROMPT_ID}\".outputs // empty")
  [ -n "$OUT" ] && [ "$OUT" != "null" ] && break
  sleep 1
done

# 4. Pull the first image filename and download it
echo "$OUT" | jq -r '.. | .images? // empty | .[0] | "\(.filename) \(.subfolder) \(.type)"' \
  | read FN SUB TYPE
curl -sG "http://127.0.0.1:8188/view" \
  --data-urlencode "filename=${FN}" \
  --data-urlencode "subfolder=${SUB}" \
  --data-urlencode "type=${TYPE}" \
  -o "/tmp/${FN}"
echo "saved /tmp/${FN}"
```

## Python recipe (stdlib + requests)

```python
import json, time, requests, re
from pathlib import Path

BASE = "http://127.0.0.1:8188"
WORKFLOWS = Path("/media/menser/fauna/image_gen/workflows")

def _coerce(token: str, value):
    t = token.upper()
    if t == "INT":   return int(value)
    if t == "FLOAT": return float(value)
    if t == "BOOL":  return bool(value)
    return str(value)

def _substitute(workflow: dict, overrides: dict) -> dict:
    """Replace PARAM_* placeholders in-place. Mirrors the MCP server."""
    for node in workflow.values():
        if not isinstance(node, dict): continue
        inputs = node.get("inputs", {})
        for k, v in list(inputs.items()):
            if not (isinstance(v, str) and v.startswith("PARAM_")):
                continue
            token = v[len("PARAM_"):]
            type_hint = "STR"
            if "_" in token:
                head, rest = token.split("_", 1)
                if head.upper() in {"STR","STRING","TEXT","INT","FLOAT","BOOL"}:
                    type_hint, token = head, rest
            name = re.sub(r"[^a-z0-9]+", "_", token.lower()).strip("_")
            if name in overrides:
                inputs[k] = _coerce(type_hint, overrides[name])
    return workflow

def run(workflow_id: str, overrides: dict | None = None, timeout: int = 600) -> Path:
    wf = json.loads((WORKFLOWS / f"{workflow_id}.json").read_text())
    if overrides:
        _substitute(wf, overrides)
    pid = requests.post(f"{BASE}/prompt", json={"prompt": wf}, timeout=30).json()["prompt_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        h = requests.get(f"{BASE}/history/{pid}", timeout=10).json().get(pid)
        if h and h.get("outputs"):
            for node_out in h["outputs"].values():
                for key in ("images", "gifs", "videos", "audio", "files"):
                    items = node_out.get(key)
                    if items:
                        a = items[0]
                        r = requests.get(f"{BASE}/view", params={
                            "filename": a["filename"],
                            "subfolder": a.get("subfolder", ""),
                            "type": a.get("type", "output"),
                        }, timeout=30)
                        out = Path("/tmp") / a["filename"]
                        out.write_bytes(r.content)
                        return out
        time.sleep(1)
    raise TimeoutError(f"workflow {pid} did not finish in {timeout}s")

if __name__ == "__main__":
    print(run("flux_txt2img", {"prompt": "a fox in a snowy forest"}))
```

Drop this in any repo. The only runtime dependency is `requests`. No MCP, no `.mcp.json` entry needed.

## Choosing the right path

- **Other Claude Code projects** — add `.mcp.json` (MCP) **or** call the HTTP API from a script. The HTTP API doesn't burn an MCP slot at session start.
- **Cron jobs, CI, non-Claude tooling** — direct API only. MCP isn't reachable from outside Claude Code.
- **One-off shell experiments** — curl recipe above.
