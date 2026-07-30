(() => {
  "use strict";
  const DATA = JSON.parse(document.getElementById("scan-data").textContent);
  let CONFIG = { theme: "living", onlineIcons: false };
  try {
    const raw = document.getElementById("scan-config").textContent.trim();
    if (raw && !raw.includes("__SCAN_CONFIG__")) CONFIG = { ...CONFIG, ...JSON.parse(raw) };
  } catch (_) { /* keep defaults */ }

  // ---------- view preferences that survive a reload ----------
  // Keyed PER DOCUMENT on purpose: every local atlas shares the single file://
  // origin, so one global key would make a map you were sent inherit your
  // settings — including switching favicon fetching on without a fresh opt-in.
  // The rendered config is the default; a stored value exists only once the
  // user has actually touched that control, so `--theme print` still holds for
  // a fresh embed. Writes happen on explicit toggles only.
  const PREF_KEY = "atlas:prefs:" + ((DATA.project || {}).name || "untitled");
  let PREFS = {};
  try { PREFS = JSON.parse(localStorage.getItem(PREF_KEY) || "{}") || {}; } catch (_) { PREFS = {}; }
  function savePref(key, value) {
    PREFS[key] = value;
    // storage can be unavailable (Safari on file://, private mode, quota) —
    // the viewer keeps working, it just stops remembering
    try { localStorage.setItem(PREF_KEY, JSON.stringify(PREFS)); } catch (_) { /* not persisted */ }
  }

  // Key order = display order (stat pills): lane flow left-to-right,
  // services before the AI kinds — the map is about the codebase first.
  const KINDS = {
    entry:    { label: "Entry",    color: "var(--entry)" },
    cron:     { label: "Cron",     color: "var(--cron)" },
    service:  { label: "Service",  color: "var(--service)" },
    agent:    { label: "Agent",    color: "var(--agent)" },
    model:    { label: "Model",    color: "var(--model)" },
    tool:     { label: "Tool",     color: "var(--tool)" },
    store:    { label: "Store",    color: "var(--store)" },
    external: { label: "External", color: "var(--external)" },
  };
  const kindOf = n => KINDS[n.kind] || KINDS.external;

  // One tiny SVG shape per kind (bolt, clock, gear, spark, chip, wrench,
  // cylinder, globe) — inlined, so icons cost zero network requests.
  const GLYPHS = {
    entry:    '<path d="M9.8 1 3.6 9h3.3L6 15l6.4-8H9.1L9.8 1z"/>',
    cron:     '<circle class="s" cx="8" cy="8" r="5.7"/><path class="s" d="M8 4.6V8l2.4 1.5"/>',
    service:  '<circle class="s" cx="8" cy="8" r="2.6"/><path class="s" d="M8 1.6v2.1M8 12.3v2.1M1.6 8h2.1M12.3 8h2.1M3.5 3.5 5 5M11 11l1.5 1.5M12.5 3.5 11 5M5 11l-1.5 1.5"/>',
    agent:    '<path d="M8 1.2 9.7 6.3 14.8 8 9.7 9.7 8 14.8 6.3 9.7 1.2 8 6.3 6.3 8 1.2z"/>',
    model:    '<rect class="s" x="4.2" y="4.2" width="7.6" height="7.6" rx="1.4"/><path class="s" d="M6.2 4.2V1.8M9.8 4.2V1.8M6.2 14.2v-2.4M9.8 14.2v-2.4M4.2 6.2H1.8M4.2 9.8H1.8M14.2 6.2h-2.4M14.2 9.8h-2.4"/>',
    tool:     '<path d="M14.2 4.5a4.4 4.4 0 0 1-5.7 5.2l-4.3 4.4a1.7 1.7 0 0 1-2.4-2.4l4.4-4.3a4.4 4.4 0 0 1 5.2-5.7L8.9 4.2l2.9 2.9 2.4-2.6z"/>',
    store:    '<ellipse class="s" cx="8" cy="3.8" rx="5.4" ry="2.1"/><path class="s" d="M2.6 3.8v8.4c0 1.2 2.4 2.1 5.4 2.1s5.4-.9 5.4-2.1V3.8"/><path class="s" d="M2.6 8c0 1.2 2.4 2.1 5.4 2.1S13.4 9.2 13.4 8"/>',
    external: '<circle class="s" cx="8" cy="8" r="5.7"/><path class="s" d="M2.3 8h11.4M8 2.3c2 2.6 2 8.8 0 11.4-2-2.6-2-8.8 0-11.4z"/>',
  };
  const glyphSvg = (k, style) => {
    const key = KINDS[k] ? k : "external";
    return `<svg class="kind-glyph" viewBox="0 0 16 16" aria-hidden="true"${style ? ` style="${style}"` : ""}>${GLYPHS[key]}</svg>`;
  };

  // Per-theme color tables (keyed by data-theme). Canvas + inline styles read
  // the ACTIVE theme's palette, not fixed hex, so a theme switch fully recolors.
  const THEME_PALETTES = {
    living: {
      entry: "#2BE59A", cron: "#F0C64B", agent: "#4D8DFF", model: "#B27BFF",
      tool: "#33D6E8", service: "#7E86FF", store: "#FF7A5E", external: "#8797B3",
      accent: "#4DE3FF", mmViewport: "#4DE3FF",
      mmEdge: "rgba(140,166,204,.30)", mmScrim: "rgba(4,6,12,.58)",
    },
    print: {
      entry: "#1E8A5B", cron: "#A87A16", agent: "#2456C4", model: "#7C3AC0",
      tool: "#0F8A9C", service: "#4C51B8", store: "#C2492F", external: "#6E7686",
      accent: "#B4552D", mmViewport: "#B4552D",
      mmEdge: "rgba(23,21,26,.20)", mmScrim: "rgba(246,242,234,.64)",
    },
  };
  const wantTheme = PREFS.theme || CONFIG.theme;
  let curTheme = THEME_PALETTES[wantTheme] ? wantTheme : "living";
  let PAL = THEME_PALETTES[curTheme];
  const kindKey = n => (KINDS[n.kind] ? n.kind : "external");
  const kindHex = k => PAL[KINDS[k] ? k : "external"];
  document.documentElement.dataset.theme = curTheme;

  const LANES = [
    { kinds: ["entry", "cron"],      label: "Entry points" },
    { kinds: ["service", "agent"],   label: "Services & agents" },
    { kinds: ["model", "tool"],      label: "Models & tools" },
    { kinds: ["store", "external"],  label: "Data & external" },
  ];

  // Favicons are OPT-IN. By default (onlineIcons off) only letter tiles render
  // and NOT A SINGLE network request is made. When the user flips the Icons
  // toggle on, every icon is rebuilt in place and favicons are fetched from
  // google.com; flipping it back off rebuilds the letter tiles. The choice is
  // remembered FOR THIS MAP ONLY (see PREF_KEY) — a different atlas still opens
  // offline until it is switched on there too.
  let onlineIcons = "icons" in PREFS ? !!PREFS.icons : !!CONFIG.onlineIcons;
  const iconSlots = [];
  function buildIconNode(slot) {
    const wrap = document.createElement("span");
    wrap.className = "letter-icon " + (slot.cls || "");
    const seed = slot.domain || slot.label || "?";
    const hue = [...seed].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 360, 7);
    wrap.style.background = `hsl(${hue} 45% 38%)`;
    wrap.textContent = (slot.label || slot.domain || "?").trim().charAt(0).toUpperCase();
    if (onlineIcons && slot.domain) {
      const img = document.createElement("img");
      img.className = slot.cls || "favicon";
      img.alt = "";
      img.src = `https://www.google.com/s2/favicons?domain=${encodeURIComponent(slot.domain)}&sz=64`;
      img.addEventListener("load", () => {
        if (slot.el && slot.el.isConnected) { slot.el.replaceWith(img); slot.el = img; }
      });
    }
    return wrap;
  }
  function iconEl(domain, label, cls) {
    const slot = { domain, label, cls, el: null };
    slot.el = buildIconNode(slot);
    iconSlots.push(slot);
    return slot.el;
  }
  function rebuildIcons() {
    for (const slot of iconSlots) {
      const fresh = buildIconNode(slot);
      if (slot.el && slot.el.isConnected) slot.el.replaceWith(fresh);
      slot.el = fresh;
    }
  }

  // ---------- header ----------
  const proj = DATA.project || {};
  document.title = (proj.name || "Atlas") + " — Atlas";
  document.getElementById("proj-name").textContent = proj.name || "Atlas";
  if (proj.iconDomain) {
    document.getElementById("title-row").prepend(iconEl(proj.iconDomain, proj.name, "proj-icon"));
  }
  document.getElementById("proj-tagline").textContent = proj.tagline || "";
  document.getElementById("tb-date").textContent = proj.date || "—";

  // Header content is DERIVED from the graph — the hand-written stats/top*
  // fields in the JSON are ignored so the header can never disagree with the map.
  const graphNodes = DATA.graph?.nodes || [];
  const topLevel = graphNodes.filter(n => !n.parent);

  const statsEl = document.getElementById("stats");
  const PLURAL = { entry: "entries", cron: "crons", agent: "agents", model: "models",
                   tool: "tools", service: "services", store: "stores", external: "externals" };
  // Counts cover EVERY node, children included — the pill answers "how many
  // tools does this system have", not "how many boxes are drawn collapsed".
  for (const kind of Object.keys(KINDS)) {
    const count = graphNodes.filter(n => (KINDS[n.kind] ? n.kind : "external") === kind).length;
    if (!count) continue;
    const d = document.createElement("button");
    d.className = "stat";
    d.dataset.kindfilter = kind;
    d.title = `Show only ${PLURAL[kind]} (click again to clear)`;
    d.innerHTML = glyphSvg(kind, `color:var(--${kind});width:10px;height:10px;align-self:center`) +
                  `<b>${count}</b><span>${count === 1 ? kind : PLURAL[kind]}</span>`;
    d.addEventListener("click", () => setKindFilter(kind));
    statsEl.appendChild(d);
  }

  const chipsEl = document.getElementById("chips");
  const models = graphNodes.filter(n => n.kind === "model");
  const seenDomains = new Set();
  const integrations = graphNodes.filter(n =>
    (n.kind === "external" || n.kind === "store") && n.domain &&
    !seenDomains.has(n.domain) && seenDomains.add(n.domain));
  // Integrations lead; models follow — AI is one facet of the map, not the headline.
  for (const [label, items] of [["Integrations", integrations], ["Models", models]]) {
    if (!items.length) continue;
    const g = document.createElement("div");
    g.className = "chip-group";
    g.innerHTML = `<span class="chip-label">${label}</span>`;
    for (const it of items) {
      const c = document.createElement("button");
      c.className = "chip";
      c.title = `Jump to ${it.label || it.id}`;
      c.appendChild(iconEl(it.domain, it.label, "favicon"));
      c.appendChild(document.createTextNode(it.label || it.id));
      c.addEventListener("click", () => jumpToNode(it.id));
      g.appendChild(c);
    }
    chipsEl.appendChild(g);
  }

  if (chipsEl.querySelector(".chip-group")) statsEl.classList.add("divide");

  chipsEl.addEventListener("wheel", ev => {
    if (Math.abs(ev.deltaY) > Math.abs(ev.deltaX)) {
      chipsEl.scrollLeft += ev.deltaY;
      ev.preventDefault();
    }
  }, { passive: false });

  // NOTE: there is no separate legend. The header stat pills already carry the
  // glyph, the colour, the kind name and the count, and they are the kind
  // filter — a second legend in the toolbar was the same control twice.

  // ---------- graph model ----------
  const allNodes = (DATA.graph?.nodes || []).map(n => ({ ...n }));
  const byId = new Map(allNodes.map(n => [n.id, n]));
  for (const n of allNodes) if (n.parent && !byId.has(n.parent)) delete n.parent;
  const childrenOf = new Map();
  for (const n of allNodes) {
    if (!n.parent) continue;
    if (!childrenOf.has(n.parent)) childrenOf.set(n.parent, []);
    childrenOf.get(n.parent).push(n);
  }
  const isContainer = id => childrenOf.has(id);
  const rawEdges = (DATA.graph?.edges || []).filter(e => byId.has(e.from) && byId.has(e.to));

  const expanded = new Set();
  let focusRootId = null;

  // A collapsed ancestor swallows its descendants: edges re-route to it.
  function effectiveId(id) {
    const chain = [];
    let cur = byId.get(id);
    while (cur) { chain.unshift(cur); cur = cur.parent ? byId.get(cur.parent) : null; }
    for (let i = 0; i < chain.length - 1; i++) {
      if (!expanded.has(chain[i].id)) return chain[i].id;
    }
    return id;
  }
  function baseVisible() {
    return allNodes.filter(n => {
      let p = n.parent;
      while (p) {
        if (!expanded.has(p)) return false;
        p = byId.get(p).parent;
      }
      return true;
    });
  }
  // Layout unit: an expanded container stacks with its children; else the user group.
  function layoutGroup(n) {
    if (n.parent && expanded.has(n.parent)) return "__c:" + n.parent;
    if (isContainer(n.id) && expanded.has(n.id)) return "__c:" + n.id;
    return n.group ? "__g:" + n.group : null;
  }

  const NODE_W = 196, ROW_GAP = 26, COL_GAP = 150, GROUP_PAD = 16;
  const MAX_PER_COL = 7, SUBCOL_GAP = 30;
  document.documentElement.style.setProperty("--node-w", NODE_W + "px");

  const viewport = document.getElementById("viewport");
  const world = document.getElementById("world");
  const nodesEl = document.getElementById("nodes");
  const groupsEl = document.getElementById("groups");
  const svg = document.getElementById("edges");
  const SVGNS = "http://www.w3.org/2000/svg";
  const detail = document.getElementById("detail");
  const minimap = document.getElementById("minimap");
  const mmCtx = minimap.getContext("2d");

  let tx = 0, ty = 0, scale = 1;
  let selectedId = null;
  let nodeCache = new Map();          // id -> el, persistent across renders
  let edgeEls = [], groupBoxEls = [], adjacency = new Map();
  let curNodes = [], curEdges = [], curPos = new Map();
  let maxX = 0, maxY = 0;

  const zoomReadout = document.getElementById("zoom-reset");
  const apply = () => {
    world.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
    zoomReadout.textContent = Math.round(scale * 100) + "%";
    drawMinimap();
  };

  function toggle(id) {
    if (expanded.has(id)) {
      expanded.delete(id);
      for (const c of childrenOf.get(id) || []) expanded.delete(c.id);
    } else expanded.add(id);
    render(true);
  }
  function setFocus(id) {
    focusRootId = id;
    document.getElementById("show-all").style.display = "";
    render(false);
  }
  function exitFocus() {
    focusRootId = null;
    document.getElementById("show-all").style.display = "none";
    render(false);
  }

  function buildEffectiveEdges(visIds) {
    const merged = new Map();
    for (const e of rawEdges) {
      const from = effectiveId(e.from), to = effectiveId(e.to);
      if (from === to || !visIds.has(from) || !visIds.has(to)) continue;
      const key = from + "→" + to;
      const prev = merged.get(key);
      if (!prev) merged.set(key, { from, to, kind: e.kind, label: e.label, count: 1 });
      else {
        prev.count++;
        if (!prev.label && e.label) prev.label = e.label;
        if (!prev.kind && e.kind) prev.kind = e.kind;
      }
    }
    return [...merged.values()].map(e =>
      e.count > 1 && !e.label ? { ...e, label: "×" + e.count } : e);
  }

  function render(keepView) {
    clearSelection();

    curNodes = baseVisible();
    let visIds = new Set(curNodes.map(n => n.id));
    curEdges = buildEffectiveEdges(visIds);

    // focus mode: restrict to the flow through the focus root (recomputed so
    // expanding a focused container keeps its children in view)
    if (focusRootId) {
      const root = effectiveId(focusRootId);
      if (!visIds.has(root)) exitFocus();
      else {
        // The focus root's flow includes its visible descendants (their edges ARE
        // the container's flow once expanded). Trace downstream + upstream from
        // each — directional closures, NOT a bidirectional flood fill (that would
        // keep the whole component).
        const family = [root];
        const collectKids = id => {
          if (!expanded.has(id)) return;
          for (const c of childrenOf.get(id) || []) {
            family.push(c.id);
            collectKids(c.id);
          }
        };
        collectKids(root);
        const keep = new Set(family);
        for (const start of family) {
          for (const dir of ["out", "in"]) {
            const stack = [start];
            const seen = new Set([start]);
            while (stack.length) {
              const cur = stack.pop();
              for (const e of curEdges) {
                const next = dir === "out"
                  ? (e.from === cur ? e.to : null)
                  : (e.to === cur ? e.from : null);
                if (next && !seen.has(next)) {
                  seen.add(next);
                  keep.add(next);
                  stack.push(next);
                }
              }
            }
          }
        }
        // keep parent cards of kept children so container stacks stay intact
        for (const id of [...keep]) {
          let p = byId.get(id)?.parent;
          while (p && visIds.has(p)) { keep.add(p); p = byId.get(p).parent; }
        }
        curNodes = curNodes.filter(n => keep.has(n.id));
        visIds = new Set(curNodes.map(n => n.id));
        curEdges = curEdges.filter(e => visIds.has(e.from) && visIds.has(e.to));
      }
    }

    // ----- semantic lanes: horizontal position IS information -----
    // entry/cron → agent/service → model/tool → store/external, left to right
    const laneOf = n => {
      const idx = LANES.findIndex(l => l.kinds.includes(n.kind));
      return idx === -1 ? LANES.length - 1 : idx;
    };
    const rank = new Map(curNodes.map(n => [n.id, laneOf(n)]));
    const units = new Map();
    for (const n of curNodes) {
      const g = layoutGroup(n);
      if (!g) continue;
      if (!units.has(g)) units.set(g, []);
      units.get(g).push(n);
    }
    // a unit stays in one lane: containers pull children to the container's
    // lane; user groups take the median member lane
    for (const [g, members] of units) {
      let lane;
      if (g.startsWith("__c:")) {
        const c = byId.get(g.slice(4));
        lane = laneOf(c);
      } else {
        const ranks = members.map(m => rank.get(m.id)).sort((a, b) => a - b);
        lane = ranks[Math.floor(ranks.length / 2)];
      }
      members.forEach(m => rank.set(m.id, lane));
    }

    const layers = new Map();
    for (const n of curNodes) {
      const r = rank.get(n.id);
      if (!layers.has(r)) layers.set(r, []);
      layers.get(r).push(n);
    }
    const layerRanks = [...layers.keys()].sort((a, b) => a - b);

    // ----- barycenter ordering; layout units stay contiguous, container card first -----
    const order = new Map();
    layerRanks.forEach(r => layers.get(r).forEach((n, i) => order.set(n.id, i)));
    const inEdges = new Map(), outEdges = new Map();
    for (const e of curEdges) {
      (inEdges.get(e.to) || inEdges.set(e.to, []).get(e.to)).push(e.from);
      (outEdges.get(e.from) || outEdges.set(e.from, []).get(e.from)).push(e.to);
    }
    for (let sweep = 0; sweep < 4; sweep++) {
      const forward = sweep % 2 === 0;
      for (const r of (forward ? layerRanks : [...layerRanks].reverse())) {
        const layer = layers.get(r);
        const bary = n => {
          const ns = ((forward ? inEdges : outEdges).get(n.id) || []).map(id => order.get(id) ?? 0);
          return ns.length ? ns.reduce((a, b) => a + b, 0) / ns.length : (order.get(n.id) ?? 0);
        };
        // kinds stay grouped inside a lane (crons together, stores before
        // externals); barycenter only orders within a kind
        const repKindIdx = n => {
          const g = layoutGroup(n);
          const k = g && g.startsWith("__c:") ? byId.get(g.slice(4)).kind : n.kind;
          const lane = LANES[rank.get(n.id)] || LANES[LANES.length - 1];
          const i = lane.kinds.indexOf(k);
          return i === -1 ? lane.kinds.length : i;
        };
        layer.sort((a, b) => {
          const ga = layoutGroup(a), gb = layoutGroup(b);
          if (ga && ga === gb) return 0;
          return repKindIdx(a) - repKindIdx(b)
            || bary(a) - bary(b)
            || String(a.id).localeCompare(String(b.id));
        });
        const buckets = [], bucketOf = new Map();
        for (const n of layer) {
          const g = layoutGroup(n);
          if (g && bucketOf.has(g)) bucketOf.get(g).push(n);
          else {
            const arr = [n];
            if (g) bucketOf.set(g, arr);
            buckets.push(arr);
          }
        }
        for (const b of buckets) b.sort((a, c) => (isContainer(c.id) ? 1 : 0) - (isContainer(a.id) ? 1 : 0));
        const packed = buckets.flat();
        layers.set(r, packed);
        packed.forEach((n, i) => order.set(n.id, i));
      }
    }

    // ----- sync node cards (persistent elements animate to new positions) -----
    for (const [id, el] of nodeCache) {
      if (!visIds.has(id)) { el.remove(); nodeCache.delete(id); }
    }
    const entering = new Set();
    for (const n of curNodes) {
      let el = nodeCache.get(n.id);
      if (!el) {
        el = buildCard(n);
        el.classList.add("entering", "no-anim");
        nodesEl.appendChild(el);
        nodeCache.set(n.id, el);
        entering.add(n.id);
      }
      const btn = el.querySelector(".expander");
      if (btn) {
        btn.textContent = expanded.has(n.id) ? "−" : "+" + childrenOf.get(n.id).length;
        btn.title = expanded.has(n.id) ? "Collapse" : "Expand " + childrenOf.get(n.id).length + " components";
      }
    }

    // ----- position: tall layers wrap into sub-columns; units never split -----
    const pos = new Map();
    maxX = 0; maxY = 0;
    const layerSubcols = layerRanks.map(r => {
      const layer = layers.get(r);
      const buckets = [], bucketOf = new Map();
      for (const n of layer) {
        const g = layoutGroup(n);
        if (g && bucketOf.has(g)) bucketOf.get(g).push(n);
        else {
          const arr = [n];
          if (g) bucketOf.set(g, arr);
          buckets.push(arr);
        }
      }
      const numSub = Math.ceil(layer.length / MAX_PER_COL);
      const perSub = Math.ceil(layer.length / numSub);
      const subcols = [[]];
      let count = 0;
      for (const b of buckets) {
        if (count > 0 && count + b.length > perSub && subcols.length < numSub) {
          subcols.push([]);
          count = 0;
        }
        subcols[subcols.length - 1].push(...b);
        count += b.length;
      }
      return subcols;
    });

    const padded = (list, cb) => {
      let prevG = null;
      for (const n of list) {
        const g = layoutGroup(n);
        if (g !== prevG && prevG !== null) cb(10, null);
        if (g && g !== prevG) cb(GROUP_PAD, null);
        cb(0, n);
        const last = !list.slice(list.indexOf(n) + 1).some(m => layoutGroup(m) === g);
        cb(nodeCache.get(n.id).offsetHeight + ROW_GAP, null);
        if (g && last) cb(GROUP_PAD, null);
        prevG = g;
      }
    };
    const subcolHeight = list => {
      let h = 0;
      padded(list, d => { h += d; });
      return Math.max(0, h - ROW_GAP);
    };
    const tallest = Math.max(0, ...layerSubcols.flat().map(subcolHeight));

    const LANE_HEAD_H = 48;
    const laneSpans = [];
    let cursorX = 0;
    layerSubcols.forEach((subcols, li) => {
      const x0 = cursorX;
      subcols.forEach((list, si) => {
        const x = cursorX + si * (NODE_W + SUBCOL_GAP);
        let y = (tallest - subcolHeight(list)) / 2 + LANE_HEAD_H;
        padded(list, (d, n) => {
          if (n) pos.set(n.id, { x, y, w: NODE_W, h: nodeCache.get(n.id).offsetHeight });
          y += d;
          maxY = Math.max(maxY, y);
        });
      });
      cursorX += subcols.length * (NODE_W + SUBCOL_GAP) - SUBCOL_GAP + COL_GAP;
      maxX = Math.max(maxX, cursorX - COL_GAP);
      laneSpans.push({ rank: layerRanks[li], x0, x1: cursorX - COL_GAP });
    });

    const lanesEl = document.getElementById("lanes");
    lanesEl.textContent = "";
    for (const span of laneSpans) {
      const head = document.createElement("div");
      head.className = "lane-head";
      head.style.cssText = `left:${span.x0}px;top:0;width:${span.x1 - span.x0}px`;
      head.textContent = LANES[span.rank]?.label || "";
      lanesEl.appendChild(head);
    }
    curPos = pos;

    for (const [id, p] of pos) {
      const el = nodeCache.get(id);
      el.style.left = p.x + "px";
      el.style.top = p.y + "px";
    }
    // entering nodes appear in place (no glide from 0,0), then fade in
    requestAnimationFrame(() => requestAnimationFrame(() => {
      for (const id of entering) {
        const el = nodeCache.get(id);
        if (el) el.classList.remove("entering", "no-anim");
      }
    }));

    // ----- unit boxes (user groups + expanded containers) -----
    groupsEl.textContent = "";
    groupBoxEls = [];
    for (const [g, members] of units) {
      const ps = members.map(m => pos.get(m.id)).filter(Boolean);
      if (!ps.length || (ps.length < 2 && !g.startsWith("__c:"))) continue;
      const x0 = Math.min(...ps.map(p => p.x)) - GROUP_PAD;
      const y0 = Math.min(...ps.map(p => p.y)) - GROUP_PAD - 4;
      const x1 = Math.max(...ps.map(p => p.x + p.w)) + GROUP_PAD;
      const y1 = Math.max(...ps.map(p => p.y + p.h)) + GROUP_PAD;
      const box = document.createElement("div");
      const isC = g.startsWith("__c:");
      box.className = "group-box" + (isC ? " container-box" : "");
      box.style.cssText = `left:${x0}px;top:${y0}px;width:${x1 - x0}px;height:${y1 - y0}px`;
      const label = document.createElement("span");
      label.className = "group-label";
      if (isC) {
        const cid = g.slice(4);
        label.textContent = "▾ " + (byId.get(cid).label || cid);
        label.title = "Collapse";
        label.addEventListener("click", () => toggle(cid));
      } else {
        label.textContent = g.slice(4);
      }
      box.appendChild(label);
      groupsEl.appendChild(box);
      groupBoxEls.push(box);
    }

    // ----- edges with fanned anchors (no rope knots at hub nodes) -----
    svg.textContent = "";
    edgeEls = [];
    svg.setAttribute("width", maxX + 200);
    svg.setAttribute("height", maxY + 200);
    // spread attachment points along each node side, ordered by the other end's y
    const ports = new Map(); // "id:side" -> [{i, otherY}]
    const anchor = [];
    curEdges.forEach((e, i) => {
      const a = pos.get(e.from), b = pos.get(e.to);
      const backward = b.x <= a.x;
      const sideA = backward ? "left" : "right";
      const sideB = backward ? "right" : "left";
      for (const [id, side, otherY] of [[e.from, sideA, b.y + b.h / 2], [e.to, sideB, a.y + a.h / 2]]) {
        const key = id + ":" + side;
        if (!ports.has(key)) ports.set(key, []);
        ports.get(key).push({ i, otherY });
      }
      anchor[i] = { backward };
    });
    for (const [key, list] of ports) {
      const [id] = key.split(":");
      const p = pos.get(id);
      list.sort((u, v) => u.otherY - v.otherY);
      list.forEach((entry, idx) => {
        const y = p.y + p.h * (idx + 1) / (list.length + 1);
        const side = key.endsWith(":left") ? "left" : "right";
        const x = side === "left" ? p.x : p.x + p.w;
        const a = anchor[entry.i];
        const isFrom = curEdges[entry.i].from === id && (a.backward ? side === "left" : side === "right");
        if (isFrom) { a.x1 = x; a.y1 = y; } else { a.x2 = x; a.y2 = y; }
      });
    }
    curEdges.forEach((e, i) => {
      const { x1, y1, x2, y2, backward } = anchor[i];
      if (x1 == null || x2 == null) return;
      const dx = Math.max(50, Math.abs(x2 - x1) * .45) * (backward ? -1 : 1);
      const g = document.createElementNS(SVGNS, "g");
      g.classList.add("edge");
      const path = document.createElementNS(SVGNS, "path");
      path.setAttribute("class", "edge-path");
      path.setAttribute("d", `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`);
      g.appendChild(path);
      const arrow = document.createElementNS(SVGNS, "path");
      arrow.setAttribute("class", "edge-arrow");
      arrow.setAttribute("d", backward
        ? `M ${x2} ${y2} L ${x2 + 8} ${y2 - 4.5} L ${x2 + 8} ${y2 + 4.5} Z`
        : `M ${x2} ${y2} L ${x2 - 8} ${y2 - 4.5} L ${x2 - 8} ${y2 + 4.5} Z`);
      g.appendChild(arrow);
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      if (e.label) {
        const t = document.createElementNS(SVGNS, "text");
        t.setAttribute("class", "edge-label");
        t.setAttribute("x", mx); t.setAttribute("y", my - 5);
        t.setAttribute("text-anchor", "middle");
        t.textContent = e.label;
        g.appendChild(t);
        requestAnimationFrame(() => {
          const bb = t.getBBox();
          const bg = document.createElementNS(SVGNS, "rect");
          bg.setAttribute("class", "edge-label-bg");
          bg.setAttribute("x", bb.x - 5); bg.setAttribute("y", bb.y - 2);
          bg.setAttribute("width", bb.width + 10); bg.setAttribute("height", bb.height + 4);
          bg.setAttribute("rx", 5);
          g.insertBefore(bg, t);
        });
      }
      if (e.kind) {
        const t = document.createElementNS(SVGNS, "text");
        t.setAttribute("class", "edge-kind");
        t.setAttribute("x", mx); t.setAttribute("y", my + 12);
        t.setAttribute("text-anchor", "middle");
        t.textContent = e.kind;
        g.appendChild(t);
      }
      svg.appendChild(g);
      edgeEls.push({ e, g });
    });

    adjacency = new Map(curNodes.map(n => [n.id, { out: [], in: [] }]));
    edgeEls.forEach(({ e }, i) => { adjacency.get(e.from).out.push(i); adjacency.get(e.to).in.push(i); });

    // motion re-binds to the freshly-built edge paths (no stale DOM refs)
    onLayoutChanged();

    document.getElementById("tb-sheet").textContent = focusRootId
      ? "Focus — " + (byId.get(focusRootId)?.label || focusRootId)
      : "Overview";
    document.getElementById("tb-nodes").innerHTML =
      `<b>${curNodes.length}</b> shown / ${allNodes.length}`;

    applySearch();
    applyKindFilter();
    sizeMinimap();                 // the map's aspect drives the minimap's
    if (!keepView) fit(0.45); else apply();
  }

  function buildCard(n) {
    const el = document.createElement("div");
    el.className = "node" + (isContainer(n.id) ? " container-card" : "");
    el.dataset.id = n.id;
    el.dataset.kind = KINDS[n.kind] ? n.kind : "external";
    const k = kindOf(n);
    el.style.setProperty("--kind-color", k.color);
    const kindRow = document.createElement("div");
    kindRow.className = "kind-row";
    kindRow.innerHTML = glyphSvg(kindKey(n)) + `<span class="kind-tag">${k.label}</span>`;
    if (isContainer(n.id)) {
      const btn = document.createElement("button");
      btn.className = "expander";
      btn.addEventListener("click", ev => { ev.stopPropagation(); toggle(n.id); });
      kindRow.appendChild(btn);
    }
    el.appendChild(kindRow);
    const labelRow = document.createElement("div");
    labelRow.className = "label-row";
    if (n.domain) labelRow.appendChild(iconEl(n.domain, n.label, "node-icon"));
    const lab = document.createElement("span");
    lab.className = "label";
    lab.textContent = n.label || n.id;
    labelRow.appendChild(lab);
    el.appendChild(labelRow);
    if (n.sub) {
      const sub = document.createElement("div");
      sub.className = "sub";
      sub.textContent = n.sub;
      el.appendChild(sub);
    }
    el.addEventListener("pointerenter", () => { if (!selectedId) highlight(n.id); });
    el.addEventListener("pointerleave", () => { if (!selectedId) highlight(null); });
    el.addEventListener("click", ev => {
      ev.stopPropagation();
      if (selectedId === n.id) { clearSelection(); return; }
      if (selectedId) nodeCache.get(selectedId)?.classList.remove("selected");
      selectedId = n.id;
      el.classList.add("selected");
      highlight(n.id);
      showDetail(n.id, el);
    });
    el.addEventListener("dblclick", ev => { ev.stopPropagation(); setFocus(n.id); });
    return el;
  }

  // ---------- flow tracing ----------
  function traceFrom(id) {
    const nodeSet = new Set([id]);
    const edgeSet = new Set();
    const walk = (start, dir) => {
      const stack = [start];
      while (stack.length) {
        const cur = stack.pop();
        for (const ei of adjacency.get(cur)?.[dir] || []) {
          if (edgeSet.has(ei)) continue;
          edgeSet.add(ei);
          const next = dir === "out" ? edgeEls[ei].e.to : edgeEls[ei].e.from;
          if (!nodeSet.has(next)) { nodeSet.add(next); stack.push(next); }
        }
      }
    };
    walk(id, "out");
    walk(id, "in");
    return { nodeSet, edgeSet };
  }
  // ---------- kind filter (clickable header stat pills) ----------
  let kindFilter = null;
  function kindFilterMatches(id) {
    const n = byId.get(id);
    if (!n) return false;
    if (kindKey(n) === kindFilter) return true;
    // a collapsed container stands in for its children
    return isContainer(id) && !expanded.has(id) &&
      (childrenOf.get(id) || []).some(c => kindKey(c) === kindFilter);
  }
  function applyKindFilter() {
    document.querySelectorAll("[data-kindfilter]").forEach(el =>
      el.classList.toggle("active", el.dataset.kindfilter === kindFilter));
    if (!kindFilter) {
      nodeCache.forEach(el => el.classList.remove("dim"));
      edgeEls.forEach(({ g }) => g.classList.remove("dim"));
      return;
    }
    const keep = new Set();
    nodeCache.forEach((el, id) => { if (kindFilterMatches(id)) keep.add(id); });
    nodeCache.forEach((el, id) => el.classList.toggle("dim", !keep.has(id)));
    // keep an edge lit if it touches a kept node — shows what the kind connects to
    edgeEls.forEach(({ e, g }) => g.classList.toggle("dim", !keep.has(e.from) && !keep.has(e.to)));
  }
  function setKindFilter(kind) {
    stopTour();
    kindFilter = kindFilter === kind ? null : kind;
    applyKindFilter();
  }

  // jump the camera to a node (chip click); resolves hidden children to
  // their collapsed container, and leaves focus mode if it hides the target
  function jumpToNode(id) {
    stopTour();
    let vid = effectiveId(id);
    if (!nodeCache.has(vid)) { exitFocus(); vid = effectiveId(id); }
    const p = curPos.get(vid), el = nodeCache.get(vid);
    if (!p || !el) return;
    const S = Math.max(0.8, Math.min(1.2, scale));
    tweenCamera(innerWidth / 2 - (p.x + p.w / 2) * S,
                innerHeight / 2 - (p.y + p.h / 2) * S, S, 450);
    if (selectedId) nodeCache.get(selectedId)?.classList.remove("selected");
    selectedId = vid;
    el.classList.add("selected");
    highlight(vid);
    setTimeout(() => { if (selectedId === vid) showDetail(vid, el); }, 480);
  }

  function highlight(id) {
    if (!id) {
      nodeCache.forEach(el => el.classList.remove("hl", "dim"));
      edgeEls.forEach(({ g }) => g.classList.remove("hl", "dim"));
      groupBoxEls.forEach(el => el.classList.remove("dim"));
      applyKindFilter();
      return;
    }
    const { nodeSet, edgeSet } = traceFrom(id);
    nodeCache.forEach((el, nid) => {
      el.classList.toggle("hl", nodeSet.has(nid) && nid !== id);
      el.classList.toggle("dim", !nodeSet.has(nid));
    });
    edgeEls.forEach(({ g }, i) => {
      g.classList.toggle("hl", edgeSet.has(i));
      g.classList.toggle("dim", !edgeSet.has(i));
    });
  }

  // ---------- detail popover ----------
  function showDetail(id, el) {
    const n = byId.get(id);
    const k = kindOf(n);
    const hex = kindHex(kindKey(n));
    const dGlyph = document.getElementById("d-glyph");
    dGlyph.innerHTML = glyphSvg(kindKey(n));
    dGlyph.style.color = hex;
    document.getElementById("d-kind").textContent = k.label;
    document.getElementById("d-kind").style.color = hex;
    document.getElementById("d-label").textContent = n.label || n.id;
    const dd = document.getElementById("d-detail");
    dd.textContent = n.detail || n.sub || "";
    dd.style.display = dd.textContent ? "" : "none";
    const dc = document.getElementById("d-contains");
    const kids = childrenOf.get(id);
    if (kids) {
      const names = kids.slice(0, 10).map(c => c.label || c.id).join(" · ");
      dc.textContent = `Contains ${kids.length}: ${names}${kids.length > 10 ? ` +${kids.length - 10} more` : ""}`;
    }
    dc.style.display = kids ? "" : "none";
    const src = document.getElementById("d-src");
    src.textContent = n.sourceRef || "";
    src.style.display = n.sourceRef ? "" : "none";
    const tg = document.getElementById("d-toggle");
    if (kids) {
      tg.style.display = "";
      tg.textContent = expanded.has(id) ? "Collapse" : "Expand";
      tg.onclick = () => toggle(id);
    } else tg.style.display = "none";
    document.getElementById("d-focus").onclick = () => setFocus(id);
    document.getElementById("d-discuss").onclick = () => openSheet(id);
    const r = el.getBoundingClientRect();
    detail.style.display = "block";
    const dw = 290, dh = detail.offsetHeight;
    let left = Math.min(innerWidth - dw - 12, Math.max(12, r.left));
    let top = r.bottom + 10;
    if (top + dh > innerHeight - 12) top = Math.max(12, r.top - dh - 10);
    detail.style.left = left + "px";
    detail.style.top = top + "px";
  }
  function clearSelection() {
    if (selectedId) nodeCache.get(selectedId)?.classList.remove("selected");
    selectedId = null;
    detail.style.display = "none";
    highlight(null);
  }
  detail.querySelector(".close").addEventListener("click", clearSelection);
  viewport.addEventListener("click", ev => { if (!ev.target.closest(".node")) clearSelection(); });
  addEventListener("keydown", ev => {
    if (ev.key === "Escape") {
      if (!shortcutsEl.hidden) setShortcuts(false);
      else if (!sheet.hidden) closeSheet();
      else if (tourActive) stopTour();
      else if (selectedId) clearSelection();
      else if (kindFilter) { kindFilter = null; applyKindFilter(); }
      else if (focusRootId) exitFocus();
      return;
    }
    // single-letter shortcuts must not fire while typing in the search box
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (ev.target?.closest?.("input, select, textarea")) return;
    if (ev.key === "m" || ev.key === "M") setMinimap(!mmCollapsed);
  });

  // ---------- prompt sheet: hand a node or a flow to a coding agent ----------
  // Built from the RAW graph, not the drawn one: a collapsed container should
  // still report the connections its children really have.
  const rawAdj = new Map(allNodes.map(n => [n.id, { out: [], in: [] }]));
  rawEdges.forEach((e, i) => { rawAdj.get(e.from).out.push(i); rawAdj.get(e.to).in.push(i); });

  const sheet = document.getElementById("promptsheet");
  const psText = document.getElementById("ps-text");
  const psStatus = document.getElementById("ps-status");
  let psNodeId = null, psScope = "node";

  const pName = id => byId.get(id)?.label || id;
  const pKind = id => { const n = byId.get(id); return n ? kindKey(n) : "unknown"; };
  const pRef = id => byId.get(id)?.sourceRef;
  function pNode(id) {
    const n = byId.get(id); if (!n) return id;
    let s = `${pName(id)} (${pKind(id)})`;
    if (n.sub) s += ` — ${n.sub}`;
    if (n.sourceRef) s += `  [${n.sourceRef}]`;
    return s;
  }
  // A neighbour without its path just sends the agent grepping, so name and
  // locate every endpoint the reader has not already been given.
  const pPeer = id => `${pName(id)} (${pKind(id)})` + (pRef(id) ? ` [${pRef(id)}]` : "");
  function pEdge(e, selfId) {
    const arrow = `--${e.kind || "connects"}-->`;
    const s = selfId
      ? (e.from === selfId ? `this ${arrow} ${pPeer(e.to)}`
                           : `${pPeer(e.from)} ${arrow} this`)
      : `${pName(e.from)} ${arrow} ${pName(e.to)}`;
    return s + (e.label ? `   "${e.label}"` : "");
  }

  // Paths are what make this actionable, so say what they are relative to.
  function promptFooter() {
    let s = "Paths in [brackets] are relative to the repo root. This map is a\n" +
            "generated high-level summary, so treat them as starting points and\n" +
            "confirm against the real code before acting.";
    if (CONFIG.atlasPath) s += `\nThe full machine-readable map is at ${CONFIG.atlasPath}.`;
    return s + "\n\nMY QUESTION: ";
  }

  function promptHeader() {
    const p = DATA.project || {};
    let s = `Codebase atlas context for ${p.name || "this repository"}`;
    if (p.tagline) s += ` — ${p.tagline}`;
    return s + ".\n";
  }

  // A container's real wiring lives on its children, so the subtree is the unit.
  function subtreeOf(id) {
    const set = new Set([id]), stack = [id];
    while (stack.length) {
      for (const c of childrenOf.get(stack.pop()) || []) {
        if (!set.has(c.id)) { set.add(c.id); stack.push(c.id); }
      }
    }
    return set;
  }

  function buildNodePrompt(id) {
    const n = byId.get(id);
    const L = [promptHeader(), "COMPONENT", `  ${pNode(id)}`];
    if (n.detail) L.push(`  ${n.detail}`);
    if (n.parent) L.push(`  inside: ${pPeer(n.parent)}`);
    if (n.group) L.push(`  group: ${n.group}`);
    const kids = childrenOf.get(id) || [];
    if (kids.length) {
      L.push(`  contains (${kids.length}):`);
      for (const c of kids) L.push(`    - ${pNode(c.id)}`);
    }

    const sub = subtreeOf(id);
    const ins = [], outs = [], internal = [];
    rawEdges.forEach((e, i) => {
      const f = sub.has(e.from), t = sub.has(e.to);
      if (f && t) { if (e.from !== e.to) internal.push(i); }
      else if (f) outs.push(i);
      else if (t) ins.push(i);
    });
    // The inner endpoint is either the node itself or one of its children,
    // which the "contains" list above has already located.
    const side = (e, id2) => (id2 === id ? "this" : `${pName(id2)} (inside this)`);
    const line = (i, dir) => {
      const e = rawEdges[i], arrow = `--${e.kind || "connects"}-->`;
      const s = dir === "out"
        ? `${side(e, e.from)} ${arrow} ${pPeer(e.to)}`
        : `${pPeer(e.from)} ${arrow} ${side(e, e.to)}`;
      return s + (e.label ? `   "${e.label}"` : "");
    };

    L.push("", "CONNECTIONS");
    if (!ins.length && !outs.length && !internal.length) L.push("  (none recorded in the atlas)");
    if (ins.length) {
      L.push(`  incoming (${ins.length}):`);
      for (const i of ins) L.push(`    - ${line(i, "in")}`);
    }
    if (outs.length) {
      L.push(`  outgoing (${outs.length}):`);
      for (const i of outs) L.push(`    - ${line(i, "out")}`);
    }
    if (internal.length) {
      L.push(`  internal (${internal.length}):`);
      for (const i of internal) L.push(`    - ${pEdge(rawEdges[i], null)}`);
    }
    L.push("", promptFooter());
    return L.join("\n");
  }

  function buildFlowPrompt(id) {
    const seed = subtreeOf(id);           // start from the node AND its contents
    const nodeSet = new Set(seed), edgeSet = new Set();
    const walk = (start, dir) => {
      const stack = [start];
      while (stack.length) {
        const cur = stack.pop();
        for (const ei of rawAdj.get(cur)?.[dir] || []) {
          if (edgeSet.has(ei)) continue;
          edgeSet.add(ei);
          const next = dir === "out" ? rawEdges[ei].to : rawEdges[ei].from;
          if (!nodeSet.has(next)) { nodeSet.add(next); stack.push(next); }
        }
      }
    };
    for (const s of seed) { walk(s, "out"); walk(s, "in"); }
    const L = [promptHeader(),
      `FLOW through ${pName(id)} — ${nodeSet.size} components, ${edgeSet.size} connections.`,
      "", "COMPONENTS"];
    for (const nid of nodeSet) L.push(`  - ${pNode(nid)}${nid === id ? "   <- the one I clicked" : ""}`);
    L.push("", "CONNECTIONS");
    for (const ei of edgeSet) L.push(`  - ${pEdge(rawEdges[ei], null)}`);
    L.push("", promptFooter());
    return L.join("\n");
  }

  function renderSheet() {
    psText.value = psScope === "flow" ? buildFlowPrompt(psNodeId) : buildNodePrompt(psNodeId);
    sheet.querySelectorAll(".ps-scope button")
      .forEach(b => b.classList.toggle("on", b.dataset.scope === psScope));
    // land the caret on the empty question line
    psText.focus();
    psText.setSelectionRange(psText.value.length, psText.value.length);
    psText.scrollTop = psText.scrollHeight;
  }
  function openSheet(id) {
    psNodeId = id;
    psScope = "node";
    document.getElementById("ps-title").textContent = pName(id);
    psStatus.textContent = "Type your question at the end, then copy.";
    psStatus.classList.remove("ok");
    sheet.hidden = false;
    renderSheet();
  }
  function closeSheet() { sheet.hidden = true; psNodeId = null; }

  sheet.querySelector(".ps-close").addEventListener("click", closeSheet);
  sheet.querySelectorAll(".ps-scope button").forEach(b =>
    b.addEventListener("click", () => { psScope = b.dataset.scope; renderSheet(); }));

  document.getElementById("ps-copy").addEventListener("click", async () => {
    const text = psText.value;
    let ok = false;
    // navigator.clipboard needs a secure context; file:// qualifies in Chrome
    // but not everywhere, so fall back and finally just leave it selected.
    try { await navigator.clipboard.writeText(text); ok = true; } catch (err) { /* fall through */ }
    if (!ok) {
      psText.focus(); psText.select();
      try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
    }
    psStatus.textContent = ok ? "Copied — paste it to your agent." : "Selected: press ⌘C / Ctrl+C to copy.";
    psStatus.classList.toggle("ok", ok);
  });

  // ---------- minimap ----------
  const titleblock = document.getElementById("titleblock");
  const mmToggle = document.getElementById("mm-toggle");
  const mmWrap = document.getElementById("mm-wrap");
  // Restored before the first paint, so a map left collapsed opens collapsed
  // rather than playing the collapse animation on load.
  let mmCollapsed = !!PREFS.mmCollapsed;
  if (mmCollapsed) {
    titleblock.classList.add("mm-collapsed");
    mmToggle.setAttribute("aria-expanded", "false");
    mmToggle.title = "Expand minimap (M)";
  }
  const MM_PAD = 7;                    // breathing room around the drawing
  let mmW = 216, mmH = 96;             // CSS pixels; the canvas backing store is DPR-scaled

  // The canvas takes the SHAPE OF THE MAP, not a fixed box: a wide lane layout
  // gets a short wide minimap instead of a tall one with dead bands above and
  // below the drawing. Clamped so it never dominates or disappears.
  function sizeMinimap() {
    const cssW = minimap.clientWidth || mmW;
    const b = mmBounds();
    const aspect = b ? b.w / b.h : 1.9;
    const cssH = Math.round(cssW / Math.min(4.2, Math.max(1.05, aspect)));
    mmW = cssW;
    mmH = Math.max(64, Math.min(148, cssH));
    // DPR-scaled backing store — the old fixed 216x128 canvas was resampled and
    // soft on every retina display.
    const dpr = Math.min(2, devicePixelRatio || 1);
    const bw = Math.round(mmW * dpr), bh = Math.round(mmH * dpr);
    minimap.style.height = mmH + "px";
    if (minimap.width !== bw || minimap.height !== bh) {
      minimap.width = bw;
      minimap.height = bh;
    }
    mmCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // set even while collapsed (the .mm-collapsed rule still wins) so expanding
    // animates to the right height instead of the fallback and then snapping
    titleblock.style.setProperty("--mm-h", mmH + "px");
    drawMinimap();
  }

  function setMinimap(collapsed) {
    mmCollapsed = collapsed;
    titleblock.classList.toggle("mm-collapsed", collapsed);
    mmToggle.setAttribute("aria-expanded", String(!collapsed));
    mmToggle.title = (collapsed ? "Expand" : "Collapse") + " minimap (M)";
    if (!collapsed) sizeMinimap();
    savePref("mmCollapsed", collapsed);
  }
  mmToggle.addEventListener("click", () => setMinimap(!mmCollapsed));

  // Tight bounds of what is actually drawn. maxX/maxY are layout cursors, not
  // the real extent, so fitting to them left empty bands inside the canvas.
  function mmBounds() {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of curPos.values()) {
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y);
      x1 = Math.max(x1, p.x + p.w); y1 = Math.max(y1, p.y + p.h);
    }
    return isFinite(x0) ? { x0, y0, w: Math.max(1, x1 - x0), h: Math.max(1, y1 - y0) } : null;
  }
  // world → minimap transform, shared by the painter and the pointer handler
  function mmFit() {
    const b = mmBounds();
    if (!b) return null;
    const s = Math.min((mmW - MM_PAD * 2) / b.w, (mmH - MM_PAD * 2) / b.h);
    return { s, ox: (mmW - b.w * s) / 2 - b.x0 * s, oy: (mmH - b.h * s) / 2 - b.y0 * s };
  }

  function drawMinimap() {
    if (mmCollapsed) return;           // nothing visible to paint
    mmCtx.clearRect(0, 0, mmW, mmH);
    const f = mmFit();
    if (!f) return;
    const { s, ox, oy } = f;

    // edges first, as one hairline path — without them the minimap is a bar
    // chart; with them it reads as the same graph, shrunk
    mmCtx.strokeStyle = PAL.mmEdge;
    mmCtx.lineWidth = .5;
    mmCtx.beginPath();
    for (const e of curEdges) {
      const a = curPos.get(e.from), b = curPos.get(e.to);
      if (!a || !b) continue;
      mmCtx.moveTo(ox + (a.x + a.w / 2) * s, oy + (a.y + a.h / 2) * s);
      mmCtx.lineTo(ox + (b.x + b.w / 2) * s, oy + (b.y + b.h / 2) * s);
    }
    mmCtx.stroke();

    mmCtx.globalAlpha = .92;
    for (const [id, p] of curPos) {
      mmCtx.fillStyle = kindHex(kindKey(byId.get(id)));
      mmCtx.fillRect(ox + p.x * s, oy + p.y * s, Math.max(2, p.w * s), Math.max(2, p.h * s));
    }
    mmCtx.globalAlpha = 1;

    // Viewport shown as a hole in a scrim rather than a floating rectangle:
    // off-screen map dims, so "where am I" is legible at a glance, and the
    // marker can never wander off the canvas when zoomed out.
    const x0 = Math.max(0, ox + (-tx / scale) * s);
    const y0 = Math.max(0, oy + (-ty / scale) * s);
    const x1 = Math.min(mmW, ox + (-tx / scale + innerWidth / scale) * s);
    const y1 = Math.min(mmH, oy + (-ty / scale + innerHeight / scale) * s);
    mmCtx.fillStyle = PAL.mmScrim;
    if (x1 <= x0 || y1 <= y0) { mmCtx.fillRect(0, 0, mmW, mmH); return; }  // map fully off-screen
    mmCtx.fillRect(0, 0, mmW, y0);
    mmCtx.fillRect(0, y1, mmW, mmH - y1);
    mmCtx.fillRect(0, y0, x0, y1 - y0);
    mmCtx.fillRect(x1, y0, mmW - x1, y1 - y0);
    mmCtx.strokeStyle = PAL.mmViewport;
    mmCtx.globalAlpha = .75;
    mmCtx.lineWidth = 1;
    mmCtx.strokeRect(Math.round(x0) + .5, Math.round(y0) + .5,
                     Math.max(1, Math.round(x1 - x0) - 1), Math.max(1, Math.round(y1 - y0) - 1));
    mmCtx.globalAlpha = 1;
  }

  // click to jump, and hold to scrub the camera around the map
  let mmDragging = false;
  function mmPanTo(ev) {
    const f = mmFit();
    if (!f) return;
    const rect = minimap.getBoundingClientRect();
    const wx = (ev.clientX - rect.left - f.ox) / f.s, wy = (ev.clientY - rect.top - f.oy) / f.s;
    tx = innerWidth / 2 - wx * scale;
    ty = innerHeight / 2 - wy * scale;
    apply();
  }
  minimap.addEventListener("pointerdown", ev => {
    if (mmCollapsed) return;
    mmDragging = true;
    minimap.classList.add("dragging");
    minimap.setPointerCapture(ev.pointerId);
    mmPanTo(ev);
  });
  minimap.addEventListener("pointermove", ev => { if (mmDragging) mmPanTo(ev); });
  const mmRelease = () => { mmDragging = false; minimap.classList.remove("dragging"); };
  minimap.addEventListener("pointerup", mmRelease);
  minimap.addEventListener("pointercancel", mmRelease);

  // ---------- pan & zoom ----------
  function fit(minScale) {
    const headerH = document.querySelector("header").offsetHeight + 10;
    const reserveRight = 250; // title block corner stays clear
    const availW = innerWidth - 40 - reserveRight;
    const availH = innerHeight - headerH - 80;
    scale = Math.min(1, availW / (maxX || 1), availH / (maxY || 1));
    if (minScale && scale < minScale) scale = minScale;
    tx = 30 + Math.max(0, (availW - maxX * scale) / 2);
    ty = headerH + Math.max(10, (availH - maxY * scale) / 2);
    if (maxY * scale > availH) ty = headerH;
    apply();
  }
  function zoomBy(factor) {
    const cx = innerWidth / 2, cy = innerHeight / 2;
    const ns = Math.min(2.5, Math.max(.1, scale * factor));
    tx = cx - (cx - tx) * (ns / scale);
    ty = cy - (cy - ty) * (ns / scale);
    scale = ns;
    apply();
  }
  let panning = false, px = 0, py = 0;
  viewport.addEventListener("pointerdown", ev => {
    if (ev.target.closest(".node")) return;
    panning = true; px = ev.clientX; py = ev.clientY;
    viewport.classList.add("panning");
    viewport.setPointerCapture(ev.pointerId);
  });
  viewport.addEventListener("pointermove", ev => {
    if (!panning) return;
    tx += ev.clientX - px; ty += ev.clientY - py;
    px = ev.clientX; py = ev.clientY;
    apply();
  });
  viewport.addEventListener("pointerup", () => { panning = false; viewport.classList.remove("panning"); });
  viewport.addEventListener("wheel", ev => {
    ev.preventDefault();
    if (ev.ctrlKey || Math.abs(ev.deltaY) > Math.abs(ev.deltaX)) {
      const factor = Math.exp(-ev.deltaY * (ev.ctrlKey ? .01 : .0015));
      const ns = Math.min(2.5, Math.max(.1, scale * factor));
      tx = ev.clientX - (ev.clientX - tx) * (ns / scale);
      ty = ev.clientY - (ev.clientY - ty) * (ns / scale);
      scale = ns;
    } else {
      tx -= ev.deltaX;
    }
    apply();
  }, { passive: false });
  document.getElementById("fit").addEventListener("click", () => fit());
  document.getElementById("zoom-in").addEventListener("click", () => zoomBy(1.3));
  document.getElementById("zoom-out").addEventListener("click", () => zoomBy(1 / 1.3));
  // the readout is the control: click it to go back to 1:1 about the centre
  zoomReadout.addEventListener("click", () => zoomBy(1 / scale));
  addEventListener("resize", () => { sizeMinimap(); apply(); });
  document.getElementById("expand-all").addEventListener("click", () => {
    childrenOf.forEach((_, id) => expanded.add(id));
    render(false);
  });
  document.getElementById("collapse-all").addEventListener("click", () => {
    expanded.clear();
    render(false);
  });
  document.getElementById("show-all").addEventListener("click", exitFocus);

  // ---------- gestures & shortcuts popover ----------
  // The old always-on hint paragraph sat over the map and wrapped to three
  // lines next to the toolbar. Same content, on demand, out of the way.
  const helpBtn = document.getElementById("help");
  const shortcutsEl = document.getElementById("shortcuts");
  function setShortcuts(open) {
    shortcutsEl.hidden = !open;
    helpBtn.classList.toggle("active", open);
    helpBtn.setAttribute("aria-expanded", String(open));
  }
  helpBtn.addEventListener("click", ev => { ev.stopPropagation(); setShortcuts(shortcutsEl.hidden); });
  document.addEventListener("pointerdown", ev => {
    if (!shortcutsEl.hidden && !ev.target.closest("#shortcuts, #help")) setShortcuts(false);
  });

  // ---------- search (matches hidden children too, marks their container) ----------
  const search = document.getElementById("search");
  function applySearch() {
    const q = search.value.trim().toLowerCase();
    nodeCache.forEach(el => el.classList.remove("dim", "match"));
    if (!q) return;
    const hits = new Set();
    for (const n of allNodes) {
      const hay = `${n.label || ""} ${n.sub || ""} ${n.id} ${n.kind} ${n.group || ""} ${n.detail || ""}`.toLowerCase();
      if (hay.includes(q)) hits.add(effectiveId(n.id));
    }
    nodeCache.forEach((el, id) => {
      el.classList.toggle("match", hits.has(id));
      el.classList.toggle("dim", !hits.has(id));
    });
  }
  search.addEventListener("input", applySearch);

  // ---------- theme switching ----------
  const themeSelect = document.getElementById("theme-select");
  function setTheme(name) {
    if (!THEME_PALETTES[name]) return;
    curTheme = name;
    PAL = THEME_PALETTES[name];
    document.documentElement.dataset.theme = name;
    // the select IS the theme readout — no second copy in the title block
    themeSelect.value = name;
    if (selectedId) { const el = nodeCache.get(selectedId); if (el) showDetail(selectedId, el); }
    updateMotionAvailability();
    drawMinimap();
  }
  themeSelect.addEventListener("change", () => {
    stopTour();
    setTheme(themeSelect.value);
    savePref("theme", curTheme);
  });

  // ---------- icons (opt-in favicons) ----------
  const iconsBtn = document.getElementById("icons");
  function refreshIconsBtn() { iconsBtn.classList.toggle("active", onlineIcons); }
  iconsBtn.addEventListener("click", () => {
    onlineIcons = !onlineIcons;
    refreshIconsBtn();
    rebuildIcons();
    savePref("icons", onlineIcons);
  });

  // ---------- motion: flow particles + entry pulse ----------
  const motionBtn = document.getElementById("motion");
  const prefersReduced = matchMedia("(prefers-reduced-motion: reduce)");
  let motionOn = false;
  const SVGNS_ = SVGNS;
  let particlesG = null, particles = [], particleRAF = null, lastTs = 0;

  const motionAllowed = () => curTheme !== "print" && !prefersReduced.matches;
  const motionRunning = () => motionOn && motionAllowed() && !document.hidden;

  function edgeParticleColor(kind) {
    if (kind === "writes") return "var(--store)";   // warm
    if (kind === "reads") return "var(--tool)";      // cool
    // An enqueued hand-off is where the flow stops being synchronous, which is
    // the first thing you want to know when the far end never ran.
    if (kind === "enqueues") return "var(--cron)";   // amber, like scheduled work
    return "var(--accent)";                          // calls / triggers / default
  }
  function rebuildParticles() {
    particles = [];
    particlesG = document.createElementNS(SVGNS_, "g");
    particlesG.setAttribute("id", "particles");
    svg.appendChild(particlesG);
    if (!edgeEls.length || edgeEls.length > 150) return;   // skip entirely above 150 edges
    const idxs = edgeEls.map((_, i) => i).sort((a, b) => {
      const ha = edgeEls[a].g.classList.contains("hl") ? 0 : 1;
      const hb = edgeEls[b].g.classList.contains("hl") ? 0 : 1;
      return ha - hb || a - b;                              // traced/focused first, then by index
    });
    const chosen = idxs.slice(0, Math.min(60, edgeEls.length));  // hard cap 60, ≤1 per edge
    for (const i of chosen) {
      const c = document.createElementNS(SVGNS_, "circle");
      c.setAttribute("r", "2.6");
      c.setAttribute("class", "particle");
      c.style.fill = edgeParticleColor(edgeEls[i].e.kind);
      particlesG.appendChild(c);
      particles.push({ edgeIdx: i, circle: c, t: Math.random(), speed: 0.10 + Math.random() * 0.06 });
    }
  }
  function stepParticles(ts) {
    const dt = lastTs ? Math.min(0.05, (ts - lastTs) / 1000) : 0.016;
    lastTs = ts;
    for (const p of particles) {
      const eg = edgeEls[p.edgeIdx];
      const path = eg && eg.g.querySelector(".edge-path");
      if (!path) { p.circle.style.opacity = 0; continue; }
      let total = 0;
      try { total = path.getTotalLength(); } catch (_) { total = 0; }
      if (!total) { p.circle.style.opacity = 0; continue; }
      p.t += p.speed * dt; if (p.t > 1) p.t -= 1;
      const pt = path.getPointAtLength(p.t * total);
      p.circle.setAttribute("cx", pt.x);
      p.circle.setAttribute("cy", pt.y);
      const cls = eg.g.classList;
      p.circle.style.opacity = cls.contains("dim") ? 0 : cls.contains("hl") ? 0.95 : 0.30;
    }
    particleRAF = requestAnimationFrame(stepParticles);
  }
  function startParticles() {
    if (!particles.length) return;
    if (particleRAF == null) { lastTs = 0; particleRAF = requestAnimationFrame(stepParticles); }
  }
  function stopParticles() {
    if (particleRAF != null) { cancelAnimationFrame(particleRAF); particleRAF = null; }
    particles.forEach(p => p.circle.style.opacity = 0);
  }
  function applyMotion() {
    const run = motionRunning();
    document.documentElement.classList.toggle("motion-on", run);
    if (run) startParticles(); else stopParticles();
  }
  function updateMotionAvailability() {
    if (!motionAllowed()) { motionOn = false; motionBtn.disabled = true; }
    else {
      motionBtn.disabled = false;
      // Motion is force-cleared whenever it becomes unavailable (Print theme,
      // reduced-motion). Re-read the preference when it becomes available
      // again, so a round trip through Print does not silently lose it.
      motionOn = PREFS.motion !== false;
    }
    motionBtn.classList.toggle("active", motionOn);
    applyMotion();
  }
  function onLayoutChanged() {
    rebuildParticles();
    applyMotion();
  }
  // Saved here and NOT in updateMotionAvailability(): that one force-clears
  // motionOn whenever motion is unavailable (print theme, reduced-motion), so
  // persisting from there would let one look at the print theme permanently
  // disable motion.
  motionBtn.addEventListener("click", () => {
    if (!motionAllowed()) return;
    motionOn = !motionOn;
    motionBtn.classList.toggle("active", motionOn);
    applyMotion();
    savePref("motion", motionOn);
  });
  document.addEventListener("visibilitychange", applyMotion);
  prefersReduced.addEventListener?.("change", updateMotionAvailability);

  // ---------- guided tour ----------
  const playBtn = document.getElementById("play");
  let tourActive = false, tourTimers = [], camRAF = null;

  function tourSequence() {
    let seq = topLevel.filter(n => n.kind === "entry" || n.kind === "cron");
    if (!seq.length) {
      const hasIn = new Set(rawEdges.map(e => e.to));
      seq = topLevel.filter(n => !hasIn.has(n.id));
    }
    // order by current layout position when available (left-to-right, top-down)
    return seq.slice().sort((a, b) => {
      const pa = curPos.get(a.id), pb = curPos.get(b.id);
      if (pa && pb) return pa.x - pb.x || pa.y - pb.y;
      return 0;
    });
  }
  function tweenCamera(TX, TY, S, ms) {
    if (camRAF) cancelAnimationFrame(camRAF);
    const sx = tx, sy = ty, ss = scale, t0 = performance.now();
    const ease = u => 1 - Math.pow(1 - u, 3);
    const frame = now => {
      const u = Math.min(1, (now - t0) / ms), e = ease(u);
      tx = sx + (TX - sx) * e; ty = sy + (TY - sy) * e; scale = ss + (S - ss) * e;
      apply();
      if (u < 1) camRAF = requestAnimationFrame(frame); else camRAF = null;
    };
    camRAF = requestAnimationFrame(frame);
  }
  function scheduleHops(rootId, done) {
    const root = effectiveId(rootId);
    const layers = [];                       // edge indices grouped by BFS depth
    const seenN = new Set([root]);
    const usedE = new Set();
    let frontier = [root];
    while (frontier.length) {
      const nextFrontier = [], layerEdges = [];
      for (const cur of frontier) {
        for (const ei of adjacency.get(cur)?.out || []) {
          if (usedE.has(ei)) continue;
          usedE.add(ei);
          layerEdges.push(ei);
          const to = edgeEls[ei].e.to;
          if (!seenN.has(to)) { seenN.add(to); nextFrontier.push(to); }
        }
      }
      if (layerEdges.length) layers.push(layerEdges);
      frontier = nextFrontier;
    }
    const TOTAL = 3500;
    edgeEls.forEach(({ g }) => g.classList.remove("hl"));
    nodeCache.forEach(el => el.classList.remove("hl"));
    if (!layers.length) { tourTimers.push(setTimeout(done, TOTAL)); return; }
    const per = TOTAL / layers.length;       // hops spread evenly across the 3.5s window
    layers.forEach((layerEdges, d) => {
      tourTimers.push(setTimeout(() => {
        if (!tourActive) return;
        for (const ei of layerEdges) {
          edgeEls[ei].g.classList.add("hl");
          nodeCache.get(edgeEls[ei].e.to)?.classList.add("hl");
        }
        rebuildParticles(); applyMotion();
      }, d * per));
    });
    tourTimers.push(setTimeout(done, TOTAL));
  }
  function runTourStop(seq, i) {
    if (!tourActive) return;
    if (i >= seq.length) { stopTour(); return; }
    const node = seq[i];
    const prev = { tx, ty, scale };
    setFocus(node.id);                       // renders + fits (sets tx/ty/scale to target)
    const target = { tx, ty, scale };
    tx = prev.tx; ty = prev.ty; scale = prev.scale;
    tweenCamera(target.tx, target.ty, target.scale, 700);
    scheduleHops(node.id, () => runTourStop(seq, i + 1));
  }
  function startTour() {
    const seq = tourSequence();
    if (!seq.length) return;
    if (kindFilter) { kindFilter = null; applyKindFilter(); }
    tourActive = true;
    playBtn.classList.add("active");
    runTourStop(seq, 0);
  }
  function stopTour() {
    if (!tourActive) return;
    tourActive = false;
    tourTimers.forEach(clearTimeout); tourTimers = [];
    if (camRAF) { cancelAnimationFrame(camRAF); camRAF = null; }
    playBtn.classList.remove("active");
    exitFocus();                             // restore the overview
  }
  playBtn.addEventListener("click", () => { if (tourActive) stopTour(); else startTour(); });
  // any manual interaction (except pressing Play) stops the tour
  ["pointerdown", "wheel"].forEach(t => document.addEventListener(t, ev => {
    if (tourActive && !ev.target.closest("#play")) stopTour();
  }, true));

  // ---------- boot ----------
  setTheme(curTheme);
  refreshIconsBtn();
  // motion defaults ON in living, unless this map was left with it switched off
  motionOn = motionAllowed() && PREFS.motion !== false;
  updateMotionAvailability();

  render(false);

  // hide Play when the scan has no valid tour sequence
  if (!tourSequence().length) playBtn.style.display = "none";
})();
