// Star rating + notes widget, injected into every gallery figure that holds a
// video. Keyed "<gallery dir>/<clip filename>" so one flat ratings.json covers
// every gallery. Autosaves on change; there is no save button by design.
(function () {
  const STARS = [
    { value: 1, label: "yuck" },
    { value: 2, label: "yeah, maybe" },
    { value: 3, label: "excellent" },
  ];
  const SAVE_DEBOUNCE_MS = 600;

  const css = `
    /* The gallery stylesheet sets video{display:block}, and an author rule beats
       the user-agent [hidden] rule whatever the specificity — so hiding by
       attribute needs this to actually take effect. */
    [hidden] { display: none !important; }
    .rev { border-top: 1px solid #333; padding: .6em .8em; display: flex;
           flex-direction: column; gap: .5em; }
    .rev-row { display: flex; align-items: center; gap: .6em; }
    .rev-stars { display: flex; gap: .15em; }
    .rev-star { cursor: pointer; font-size: 21px; line-height: 1; color: #4a4a52;
                background: none; border: 0; padding: 0 1px; transition: color .12s; }
    .rev-star:hover, .rev-star.on { color: #f0c040; }
    .rev-star:focus-visible { outline: 2px solid #6aa9ff; outline-offset: 2px; }
    .rev-verdict { font-size: 12px; color: #999; min-width: 8ch; }
    .rev-hide { margin-left: auto; font-size: 11px; color: #8fb4e8; background: none;
                border: 1px solid #3a3a44; border-radius: 4px; padding: .2em .55em;
                cursor: pointer; white-space: nowrap; }
    figure.collapsed { min-width: 380px; }
    figure.collapsed .rev { border-top: 0; }
    .rev-title { font-size: 12.5px; color: #ddd; overflow: hidden;
                 text-overflow: ellipsis; white-space: nowrap; max-width: 34ch; }
    .rev-hide:hover { border-color: #6aa9ff; }
    .rev-clear { font-size: 11px; color: #777; background: none;
                 border: 0; cursor: pointer; text-decoration: underline; }
    .rev textarea { width: 100%; box-sizing: border-box; min-height: 3.2em;
                    resize: vertical; background: #101014; color: #ddd;
                    border: 1px solid #333; border-radius: 4px; padding: .45em .55em;
                    font: 12.5px/1.45 -apple-system, system-ui, sans-serif; }
    .rev textarea:focus { outline: none; border-color: #6aa9ff; }
    .rev-state { font-size: 11px; height: 1.2em; color: #6a6a72; }
    .rev-state.saved { color: #5fa85f; }
    .rev-state.error { color: #d06a6a; }
    .info { border-top: 1px solid #2c2c33; padding: .55em .8em; font-size: 12px;
            color: #b8b8c0; }
    .info summary { cursor: pointer; color: #8fb4e8; list-style: none; outline: none; }
    .info summary::-webkit-details-marker { display: none; }
    .info summary::before { content: "▸ "; }
    .info[open] summary::before { content: "▾ "; }
    .info dl { margin: .6em 0 0; display: grid; grid-template-columns: max-content 1fr;
               gap: .3em .8em; }
    .info dt { color: #7d7d88; white-space: nowrap; }
    .info dd { margin: 0; }
    .info .q-caveat dt, .info .q-caveat dd { color: #d8a05a; }
    .info .q-measured dt, .info .q-measured dd { color: #7fb87f; }
    #rev-summary { position: fixed; right: 12px; bottom: 12px; background: #1a1a1f;
                   border: 1px solid #444; border-radius: 6px; padding: .5em .8em;
                   font: 12px -apple-system, system-ui, sans-serif; color: #ccc;
                   z-index: 50; }
  `;
  document.head.appendChild(document.createElement("style")).textContent = css;

  // Gallery dir is the last path segment before the file, e.g. /loras/index.html.
  const parts = location.pathname.split("/").filter(Boolean);
  const galleryDir = parts.length > 1 ? parts[parts.length - 2] : "";
  const keyFor = (src) => `${galleryDir}/${decodeURIComponent(src.split("/").pop())}`;

  const HIDDEN_PREFIX = "h3rev:hidden:";

  function readHidden(key) {
    try {
      return localStorage.getItem(HIDDEN_PREFIX + key) === "1";
    } catch (err) {
      return false;
    }
  }

  function writeHidden(key, hidden) {
    try {
      if (hidden) localStorage.setItem(HIDDEN_PREFIX + key, "1");
      else localStorage.removeItem(HIDDEN_PREFIX + key);
    } catch (err) {
      /* private window, or site data blocked; the toggle still works for this view */
    }
  }

  const pending = new Map();
  let timer = null;

  function queueSave(key, entry, stateEl) {
    pending.set(key, { ...(pending.get(key) || {}), ...entry });
    stateEl.textContent = "saving…";
    stateEl.className = "rev-state";
    clearTimeout(timer);
    timer = setTimeout(flush, SAVE_DEBOUNCE_MS);
  }

  async function flush() {
    if (!pending.size) return;
    const payload = Object.fromEntries(pending);
    pending.clear();
    try {
      const res = await fetch("/api/ratings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(res.status);
      document.querySelectorAll(".rev-state").forEach((el) => {
        if (el.textContent === "saving…") {
          el.textContent = "saved";
          el.className = "rev-state saved";
        }
      });
    } catch (err) {
      document.querySelectorAll(".rev-state").forEach((el) => {
        if (el.textContent === "saving…") {
          el.textContent = "save failed — is the review server still running?";
          el.className = "rev-state error";
        }
      });
    }
    updateSummary();
  }

  // Don't lose an in-flight edit when the tab closes mid-debounce.
  window.addEventListener("beforeunload", () => {
    if (!pending.size) return;
    navigator.sendBeacon("/api/ratings",
      new Blob([JSON.stringify(Object.fromEntries(pending))], { type: "application/json" }));
  });

  const widgets = [];

  function buildWidget(figure, key, saved, video) {
    const wrap = document.createElement("div");
    wrap.className = "rev";

    const row = document.createElement("div");
    row.className = "rev-row";
    const starBox = document.createElement("div");
    starBox.className = "rev-stars";
    const verdict = document.createElement("span");
    verdict.className = "rev-verdict";
    const hide = document.createElement("button");
    hide.className = "rev-hide";
    hide.type = "button";

    const clear = document.createElement("button");
    clear.className = "rev-clear";
    clear.textContent = "clear";
    clear.type = "button";

    // Collapsing hides the whole panel — clip, caption, info card and notes —
    // leaving the title, the stars and this button, so a long page can be
    // scanned by verdict alone.
    const caption = figure.querySelector("figcaption");
    const info = figure.querySelector(".info");

    // The caption's first line is the clip's label; keep it as the collapsed
    // title so a shut panel still says which clip it is.
    // textContent would flatten the whole caption, since <br> contributes no
    // newline — walk the child nodes and stop at the first line break instead.
    function firstCaptionLine(el) {
      if (!el) return "";
      let out = "";
      for (const node of el.childNodes) {
        if (node.nodeName === "BR") break;
        out += node.textContent;
      }
      return out.trim();
    }

    const title = document.createElement("span");
    title.className = "rev-title";
    title.textContent = firstCaptionLine(caption);

    // Default is open; only an explicitly stored choice collapses a clip.
    let hidden = readHidden(key);

    function paintHide() {
      video.hidden = hidden;
      if (caption) caption.hidden = hidden;
      if (info) info.hidden = hidden;
      notes.hidden = hidden;
      state.hidden = hidden;
      title.hidden = !hidden;
      figure.classList.toggle("collapsed", hidden);
      hide.textContent = hidden ? "show" : "hide";
      hide.setAttribute("aria-expanded", String(!hidden));
    }

    hide.addEventListener("click", () => {
      hidden = !hidden;
      if (hidden && !video.paused) video.pause();
      writeHidden(key, hidden);
      paintHide();
    });

    const state = document.createElement("div");
    state.className = "rev-state";

    const notes = document.createElement("textarea");
    notes.placeholder = "notes…";
    notes.value = saved.notes || "";

    let rating = saved.rating || 0;
    const buttons = STARS.map((s) => {
      const b = document.createElement("button");
      b.className = "rev-star";
      b.type = "button";
      b.textContent = "★";
      b.title = `${s.value} — ${s.label}`;
      b.setAttribute("aria-label", b.title);
      b.addEventListener("click", () => setRating(s.value));
      starBox.appendChild(b);
      return b;
    });

    function paint() {
      buttons.forEach((b, i) => b.classList.toggle("on", i < rating));
      const hit = STARS.find((s) => s.value === rating);
      verdict.textContent = hit ? `${rating} — ${hit.label}` : "unrated";
    }

    function setRating(value) {
      rating = rating === value ? 0 : value;
      paint();
      queueSave(key, { rating }, state);
      updateSummary();
    }

    notes.addEventListener("input", () => queueSave(key, { notes: notes.value }, state));
    clear.addEventListener("click", () => {
      rating = 0;
      notes.value = "";
      paint();
      queueSave(key, { rating: 0, notes: "" }, state);
      updateSummary();
    });

    row.append(starBox, verdict, title, hide, clear);
    wrap.append(row, notes, state);
    figure.appendChild(wrap);
    paint();
    paintHide();
    widgets.push({ get rating() { return rating; } });
  }

  function updateSummary() {
    const box = document.getElementById("rev-summary");
    if (!box) return;
    const rated = widgets.filter((w) => w.rating > 0).length;
    box.textContent = `${rated} / ${widgets.length} rated on this page`;
  }

  const FIELDS = [
    ["made_for", "Made for"],
    ["age", "Age"],
    ["liked", "Liked for"],
    ["disliked", "Disliked for"],
    ["bad_for", "Bad for"],
    ["better", "Gets better with"],
    ["else", "Also"],
    ["measured", "Measured here"],
    ["caveat", "Caveat"],
  ];

  function buildInfo(figure, cardIds, cards) {
    const present = cardIds.map((id) => cards[id]).filter(Boolean);
    if (!present.length) return;
    const box = document.createElement("details");
    box.className = "info";
    const sum = document.createElement("summary");
    sum.textContent = present.map((c) => c.title).join("  +  ");
    box.appendChild(sum);
    present.forEach((card) => {
      const dl = document.createElement("dl");
      FIELDS.forEach(([key, label]) => {
        if (!card[key]) return;
        const dt = document.createElement("dt");
        const dd = document.createElement("dd");
        dt.textContent = label;
        dd.textContent = card[key];
        if (key === "caveat" || key === "measured") {
          dt.className = dd.className = `q-${key}`;
        }
        dl.append(dt, dd);
      });
      if (present.length > 1) {
        const h = document.createElement("div");
        h.style.cssText = "margin-top:.7em;color:#8fb4e8";
        h.textContent = card.title;
        box.appendChild(h);
      }
      box.appendChild(dl);
    });
    figure.appendChild(box);
  }

  async function init() {
    let saved = {};
    let cards = {};
    let cardMap = {};
    try {
      saved = await (await fetch("/api/ratings")).json();
    } catch (err) {
      /* first run, or the server has no ratings yet */
    }
    try {
      [cards, cardMap] = await Promise.all([
        fetch("/info_cards.json").then((r) => r.json()),
        fetch("/card_map.json").then((r) => r.json()),
      ]);
    } catch (err) {
      /* info cards are optional */
    }
    document.querySelectorAll("figure").forEach((fig) => {
      const video = fig.querySelector("video");
      if (!video) return;
      const key = keyFor(video.getAttribute("src"));
      buildInfo(fig, cardMap[key] || [], cards);
      buildWidget(fig, key, saved[key] || {}, video);
    });
    if (widgets.length) {
      const box = document.createElement("div");
      box.id = "rev-summary";
      document.body.appendChild(box);
      updateSummary();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
