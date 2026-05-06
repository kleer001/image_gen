# Showing generated images to the user

When image_gen produces a batch (gallery, comparison grid, A/B test), open an HTML page in the user's browser. Browser sandboxing makes naive `file://` paths unreliable, so follow this checklist.

## 1. Always serve over local HTTP, not `file://`

`file://` fails in three ways: flatpak/snap browsers rewrite paths via portals (the address bar won't match what you told the user), `fetch()`/modules/CORS often break, and images outside the HTML's directory may be blocked. A local HTTP server sidesteps all of this and works on every browser tier.

```bash
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SERVE_DIR" &
SERVER_PID=$!
```

Probe `$PORT` first — increment from e.g. 8765 until free. Bind `127.0.0.1` only (don't expose to LAN).

## 2. Stage assets inside `$SERVE_DIR`

The browser can only fetch files under `$SERVE_DIR`:

- Copy or **symlink** the PNGs into `$SERVE_DIR` (symlinks for large files).
- Use basename-only `<img src="foo.png">` — never absolute paths.
- `$SERVE_DIR` should be `mktemp -d` (or `/tmp/<name>_gallery/` for stable paths). Never serve `$HOME` or repo roots — anything under it is readable by any localhost client.

## 3. Open the URL

```bash
# Linux                xdg-open "http://localhost:$PORT/index.html"
# macOS                open "http://localhost:$PORT/index.html"
# Windows              cmd.exe /c start "" "http://localhost:$PORT/index.html"
# WSL → host browser   explorer.exe "http://localhost:$PORT/index.html"
```

**Headless / SSH:** detect with `[ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]` (or `$SSH_CONNECTION` set without a forwarded display). Don't try to open — print the URL and tell the user to forward the port: `ssh -L $PORT:localhost:$PORT user@host`.

## 4. HTML conventions

- Light background by default (don't blindly follow `prefers-color-scheme`).
- Each image full-width, captioned with prompt, seed, model, LoRA info — that's what the user compares on.
- No external CDN assets (fonts, frameworks). Page must work offline.
- Footer with served path + kill command, so cleanup is obvious.

## 5. Clean up

When the user is done:
- `kill $SERVER_PID`
- Remove `$SERVE_DIR` if it was a `mktemp -d`
- Don't auto-delete the source PNGs

## 6. Tell the user exactly one URL

Print **only** `http://localhost:$PORT/...`. Don't also mention the filesystem path — it invites confusion when the address bar shows a portal-rewritten path. One source of truth.
