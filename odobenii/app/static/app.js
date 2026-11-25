/* Odobenii's page.  Every picture is drawn by the local server; this page picks and shows. */
"use strict";
const $ = id => document.getElementById(id);
const TOKEN = document.querySelector('meta[name="odobenii-token"]')?.content || "";
const store = {
  get(k, d) { try { const v = localStorage.getItem("hpv:" + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
  put(k, v) { try { localStorage.setItem("hpv:" + k, JSON.stringify(v)); } catch (e) { /* private window: not kept */ } },
};
const LOOK0 = { cs: "lab", emph: "balanced", k: 4, tone: true, unpainted: true, cap: true, hatch: true };
const UI = {
  tab: store.get("tab", "photos"), view: store.get("view", "boost"), cmp: store.get("cmp", ""), flip: store.get("flip", false),
  look: Object.assign({}, LOOK0, store.get("look", {})), tool: null, drag: null, leaving: false, imgKey: "", stripSeq: 0,
};
const VIEWS = ["original", "boost", "stretch", "expected", "departs"];
const VIEW_NAMES = { original: "The photograph", boost: "Boost", stretch: "Stretch", expected: "Expected unpainted ×4", departs: "Where colour departs" };
const SPACE_NAMES = { lab: "CIELAB", density: "Density" };
const EMPH_NAMES = { balanced: "balanced", redgreen: "red–green", yellowblue: "yellow–blue" };
const STRIP_HUES = ["pink-red", "orange", "yellow", "green", "blue", "purple"];
let ST = null;

// -- talking to the server ------------------------------------------------------------------------------------------
function apiGet(url) { return fetch(url, { headers: { "X-Odobenii-Token": TOKEN } }); }
async function api(method, url, body) {
  const opt = { method, headers: { "X-Odobenii-Token": TOKEN } };
  if (body instanceof FormData) opt.body = body;
  else if (body !== undefined) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  let r;
  try { r = await fetch(url, opt); } catch (e) { throw new Error("The visualiser's server is not answering. Is it still running?"); }
  let d = {};
  try { d = await r.json(); } catch (e) { /* not JSON */ }
  if (!r.ok || !d.ok) throw new Error(d.error || `${r.status} ${r.statusText}`);
  if (d.state) applyState(d.state);
  return d;
}
function status(msg, kind = "") { const el = $("status"); el.textContent = msg; el.className = "status " + kind; }
const PROG = { n: 0, poll: null };
function progressStart() { if (PROG.n++ === 0) { PROG.poll = setInterval(pollProgress, 350); } }
function progressEnd() { PROG.n = Math.max(0, PROG.n - 1); if (!PROG.n) { clearInterval(PROG.poll); PROG.poll = null; $("progress").hidden = true; } }
async function pollProgress() {
  try {
    const d = await (await apiGet("/api/progress")).json();
    const p = d.progress || {};
    $("progress").hidden = !p.busy;
    if (p.busy) { $("pFill").style.width = `${Math.round(100 * (p.frac || 0))}%`; $("pLabel").textContent = p.label || ""; $("pTime").textContent = `${Math.round(p.seconds || 0)} s`; }
    if (d.batch) renderBatch(d.batch);
  } catch (e) { /* the next poll tries again */ }
}
async function guarded(label, fn) {
  status(label + "…"); progressStart();
  try { await fn(); status(""); } catch (e) { status(e.message || String(e), "bad"); }
  finally { progressEnd(); }
}

// -- state ----------------------------------------------------------------------------------------------------------
function applyState(st) {
  const before = ST && ST.image ? `${ST.image.path}|${ST.image.size}` : "";
  ST = st;
  const now = st.image ? `${st.image.path}|${st.image.size}` : "";
  renderFiles(); renderInfo(); renderBoxes(); renderSettings(); renderExport(); renderBatch(st.batch);
  $("empty").hidden = !!st.image;
  $("btnExport").disabled = !st.image;
  if (now !== before) {
    V.iw = st.image ? st.image.size[0] : 0; V.ih = st.image ? st.image.size[1] : 0;
    V.pic = null; V2.pic = null; fitView();
  }
  scheduleFetch(0);
  refreshStrip();
}
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function renderFiles() {
  const host = $("files"), sel = ST.image ? ST.image.path : "";
  const item = f => `<button type="button" class="photo${f.path === sel ? " sel" : ""}" data-path="${esc(f.path)}"><span class="fn" title="${esc(f.path)}">${esc(f.name)}</span><span class="mb">${f.mb} MB</span></button>`;
  let html = "";
  if (ST.files.length) html += `<div class="group">${esc(ST.folder)}</div>` + ST.files.map(item).join("");
  if (ST.added.length) html += `<div class="group">Added to the session</div>` + ST.added.map(item).join("");
  host.innerHTML = html;
  $("filesHint").hidden = !!(ST.files.length || ST.added.length);
  $("filesHint").textContent = ST.folder ? "No photographs this tool reads in that folder (TIFF, PNG, JPEG, WebP, BMP)." : "Open a folder, or add files.";
  if (document.activeElement !== $("folder") && !$("folder").value) $("folder").value = ST.folder || "";
}
function renderInfo() {
  const im = ST.image;
  $("infoStep").hidden = !im;
  if (!im) return;
  $("imgInfo").innerHTML = `<b>${esc(im.name)}</b>, ${im.size[0]} × ${im.size[1]} px, ${im.bits}-bit. ${esc(im.colour)}`;
  const warn = [];
  if (im.grey_file) warn.push("This file holds no colour (greyscale): it cannot show paint.");
  if (im.no_votes) warn.push("No tones could be judged here: the photograph is all too dark, too light or clipped.");
  $("imgWarn").hidden = !warn.length; $("imgWarn").textContent = warn.join(" ");
  $("guessHint").hidden = !im.guessing;
  $("stCrop").textContent = im.crop ? "drawn" : "the whole frame";
  const used = (im.boxes || []).filter(b => b.used).length, all = (im.boxes || []).length;
  $("stBox").textContent = all ? `${used} of ${all} used` : "none";
}
function renderBoxes() {
  const host = $("boxList"), im = ST.image;
  if (!im || !(im.boxes || []).length) { host.innerHTML = ""; return; }
  host.innerHTML = im.boxes.map((b, i) => `<div class="bx${b.used ? "" : " unused"}"><span class="tag">B${i + 1}</span><span class="note">${esc(b.note)}</span><button type="button" class="small" data-rm="${i}" aria-label="Remove box B${i + 1}">✕</button></div>`).join("");
}
function renderSettings() {
  const s = ST.settings;
  if (!$("project").hidden && document.activeElement && $("project").contains(document.activeElement)) return;
  $("defSpace").value = s.default_space; $("nearBlack").value = s.near_black; $("nearWhite").value = s.near_white;
  $("t0").value = s.T0; $("anaEdge").value = s.analysis_edge;
  $("sessionRoot").textContent = ST.session; $("ver").textContent = ST.version;
}
function renderExport() {
  if (!$("exFolder").value) $("exFolder").value = ST.export_folder || "";
  if (!$("bIn").value && ST.folder) $("bIn").value = ST.folder;
}
function renderBatch(b) {
  if (!b) return;
  $("btnBatch").disabled = b.running; $("btnBatchCancel").disabled = !b.running;
  const el = $("bOutMsg");
  if (b.running) { el.className = "out"; el.textContent = `Drawing ${b.current || "…"} (${b.done} of ${b.total})`; watchBatch(); }
  else if (b.finished) {
    el.className = "out " + (b.errors.length ? "bad" : "ok");
    el.innerHTML = `${b.cancelled ? "Cancelled" : "Done"}: ${b.done} of ${b.total} photographs, pictures in <span class="mono">${esc(b.out)}</span>.` +
      (b.errors.length ? `<br>${b.errors.map(esc).join("<br>")}` : "");
  }
}
let batchTimer = null;
function watchBatch() {
  if (batchTimer) return;
  batchTimer = setInterval(async () => {
    try {
      const d = await (await apiGet("/api/progress")).json();
      renderBatch(d.batch);
      if (!d.batch.running) { clearInterval(batchTimer); batchTimer = null; }
    } catch (e) { clearInterval(batchTimer); batchTimer = null; }
  }, 1000);
}

// -- tabs, views and the look ----------------------------------------------------------------------------------------
function setTab(t) {
  UI.tab = t; store.put("tab", t);
  document.querySelectorAll("#flow button").forEach(b => b.classList.toggle("on", b.dataset.tab === t));
  document.querySelectorAll("[data-pane]").forEach(p => { p.hidden = p.dataset.pane !== t; });
  if (t === "check") refreshStrip();
}
function describe(view) {
  const L = UI.look;
  if (view === "boost") return `Boost ×${L.k}`;
  if (view !== "stretch") return VIEW_NAMES[view] || "";
  const off = [!L.tone && "tone kept", !L.unpainted && "all pixels", !L.cap && "no cap"].filter(Boolean);
  return `Stretch ×${L.k} · ${SPACE_NAMES[L.cs]} · ${EMPH_NAMES[L.emph]}${off.length ? ` · guards off: ${off.join(", ")}` : ""}`;
}
function setView(v) {
  if (!VIEWS.includes(v)) return;
  if (v === UI.cmp && !UI.flip) { UI.cmp = UI.view; store.put("cmp", UI.cmp); $("cmpSel").value = UI.cmp; }
  UI.view = v; store.put("view", v);
  renderViewbar(); labelViews(); refreshStrip(); scheduleFetch(0);
}
function renderViewbar() {
  document.querySelectorAll("#viewbar button").forEach(b => b.classList.toggle("on", b.dataset.view === UI.view));
  $("viewDesc").textContent = describe(UI.view);
  $("visLabel").textContent = UI.view === "departs" || UI.cmp === "departs" ? "Visualisation only — not a measurement. Blank does not mean unpainted." : "Visualisation only — not a measurement";
}
function renderLook() {
  const L = UI.look;
  document.querySelectorAll("#segSpace button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.v === L.cs)));
  document.querySelectorAll("#segEmph button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.v === L.emph)));
  $("k").value = L.k; $("kOut").textContent = `×${L.k}`;
  $("gTone").checked = L.tone; $("gUnp").checked = L.unpainted; $("gCap").checked = L.cap; $("hatch").checked = L.hatch;
  $("btnGuards").textContent = L.tone || L.unpainted || L.cap ? "All off (a plain stretch, to compare)" : "All on (the guarded stretch)";
}
let lookTimer = null;
function lookChanged() {
  store.put("look", UI.look); renderLook(); renderViewbar(); labelViews();
  clearTimeout(lookTimer); lookTimer = setTimeout(() => { scheduleFetch(0); refreshStrip(); }, 60);
}
function lookParams(view) {
  const L = UI.look;
  return { view, cs: L.cs, emph: L.emph, k: L.k, tone: L.tone ? 1 : 0, unpainted: L.unpainted ? 1 : 0, cap: L.cap ? 1 : 0, hatch: L.hatch ? 1 : 0 };
}
async function refreshStrip() {
  if (!ST || !ST.image || UI.tab !== "check") return;
  const seq = ++UI.stripSeq;
  const q = new URLSearchParams({ ...lookParams(UI.view), screen: VIEW_SPACE });
  try {
    const r = await apiGet(`/api/strip?${q}`);
    if (!r.ok || seq !== UI.stripSeq) return;
    const url = URL.createObjectURL(await r.blob());
    const img = $("strip"), old = img.dataset.url;
    img.src = url; img.dataset.url = url;
    if (old) URL.revokeObjectURL(old);
  } catch (e) { /* the strip is redrawn with the next change */ }
}
function buildStripLabels() {
  $("stripHues").style.gridTemplateRows = `repeat(${STRIP_HUES.length}, 1fr)`;
  $("stripHues").innerHTML = STRIP_HUES.map(h => `<span>${h}</span>`).join("");
  $("stripTones").innerHTML = "<span>darker</span><span>tone</span><span>lighter</span>";
}

// -- the image well --------------------------------------------------------------------------------------------------
const cv = $("cv"), cv2 = $("cv2");
let VIEW_SPACE = window.matchMedia && window.matchMedia("(color-gamut: p3)").matches ? "p3" : "srgb";
const V = { iw: 0, ih: 0, s: 1, ox: 0, oy: 0, pic: null, rect: null, seq: 0, timer: null, fitted: false, atFit: true };
const V2 = { pic: null, rect: null, seq: 0 };
const CTX = new Map();
function ctx2d(c) {
  if (!CTX.has(c)) {
    let g = null;
    try { g = c.getContext("2d", VIEW_SPACE === "p3" ? { colorSpace: "display-p3" } : {}); } catch (e) { g = null; }
    if (!g) g = c.getContext("2d");
    const attrs = g.getContextAttributes ? g.getContextAttributes() : {};
    if (VIEW_SPACE === "p3" && attrs.colorSpace !== "display-p3") VIEW_SPACE = "srgb";
    CTX.set(c, g);
  }
  return CTX.get(c);
}
function canvasSize() { const r = cv.getBoundingClientRect(); return [r.width, r.height]; }
function fitView() {
  const [cw, ch] = canvasSize();
  if (!V.iw || !cw) return;
  V.s = Math.min(cw / V.iw, ch / V.ih) * 0.98;
  V.ox = (cw - V.iw * V.s) / 2; V.oy = (ch - V.ih * V.s) / 2; V.fitted = V.atFit = true;
  showZoom(); draw(); scheduleFetch(0);
}
function showZoom() { $("zoomOut").textContent = V.iw ? `${(V.s * 100).toFixed(V.s < 0.1 ? 1 : 0)}%` : ""; }
const toImg = (cx, cy) => [(cx - V.ox) / V.s, (cy - V.oy) / V.s];
function zoomAt(cx, cy, f) {
  const ns = Math.max(0.01, Math.min(40, V.s * f));
  const [u, v] = toImg(cx, cy);
  V.s = ns; V.ox = cx - u * ns; V.oy = cy - v * ns; V.atFit = false;
  showZoom(); draw(); scheduleFetch();
}
function scheduleFetch(delay = 110) { clearTimeout(V.timer); V.timer = setTimeout(fetchPics, delay); }
function visibleRect() {
  const [cw, ch] = canvasSize();
  const x0 = Math.max(0, Math.floor(-V.ox / V.s)), y0 = Math.max(0, Math.floor(-V.oy / V.s));
  const x1 = Math.min(V.iw, Math.ceil((cw - V.ox) / V.s)), y1 = Math.min(V.ih, Math.ceil((ch - V.oy) / V.s));
  return x1 > x0 && y1 > y0 ? [x0, y0, x1, y1] : null;
}
async function fetchOne(view, target) {
  const r = visibleRect(); if (!r) return;
  const [x0, y0, x1, y1] = r, dpr = Math.min(2, window.devicePixelRatio || 1);
  const ow = Math.max(1, Math.min(4096, Math.round((x1 - x0) * V.s * dpr))), oh = Math.max(1, Math.min(4096, Math.round((y1 - y0) * V.s * dpr)));
  const seq = ++target.seq;
  const q = new URLSearchParams({ x: x0, y: y0, w: x1 - x0, h: y1 - y0, ow, oh, screen: VIEW_SPACE, ...lookParams(view) });
  const resp = await apiGet(`/api/view?${q}`);
  if (!resp.ok) { const d = await resp.json().catch(() => ({})); if (seq === target.seq) status(d.error || "The picture could not be drawn.", "bad"); return; }
  const bmp = await createImageBitmap(await resp.blob());
  if (seq !== target.seq) return;
  target.pic = bmp; target.rect = r; draw();
}
async function fetchPics() {
  if (UI.leaving || !ST || !ST.image) { draw(); return; }
  $("busy").hidden = false;
  const second = UI.cmp && !UI.flip ? fetchOne(UI.cmp, V2) : Promise.resolve();
  try { await Promise.all([fetchOne(UI.view, V), second]); }
  catch (e) { if (!UI.leaving) console.error(e); }
  finally { $("busy").hidden = true; }
}
function sizeCanvas(c) {
  const r = c.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1);
  if (c.width !== Math.round(r.width * dpr) || c.height !== Math.round(r.height * dpr)) { c.width = Math.round(r.width * dpr); c.height = Math.round(r.height * dpr); }
  const g = ctx2d(c); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, r.width, r.height);
  return g;
}
function paint(c, T) {
  const g = sizeCanvas(c);
  if (!ST || !ST.image) return g;
  if (T.pic && T.rect) {
    const [x0, y0, x1, y1] = T.rect;
    g.imageSmoothingEnabled = V.s < 1;
    g.drawImage(T.pic, V.ox + x0 * V.s, V.oy + y0 * V.s, (x1 - x0) * V.s, (y1 - y0) * V.s);
  }
  g.strokeStyle = "rgba(255,255,255,0.12)"; g.lineWidth = 1; g.strokeRect(V.ox, V.oy, V.iw * V.s, V.ih * V.s);
  overlay(g);
  return g;
}
function draw() { paint(cv, V); if (!cv2.hidden) paint(cv2, V2); }
function cssVar(n, d) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d; }
function overlay(g) {
  const im = ST.image, c1 = cssVar("--overlay", "#ffd166"), c2 = cssVar("--overlay-2", "#6fe3ff"), cb = cssVar("--overlay-bad", "#ff7a70");
  g.font = `11px ${getComputedStyle(document.body).fontFamily}`;
  const rect = (b, col, label, dash) => {
    const x = V.ox + b[0] * V.s, y = V.oy + b[1] * V.s, w = b[2] * V.s, h = b[3] * V.s;
    g.setLineDash(dash ? [5, 4] : []);
    g.strokeStyle = "rgba(0,0,0,0.6)"; g.lineWidth = 3; g.strokeRect(x, y, w, h);
    g.strokeStyle = col; g.lineWidth = 1.3; g.strokeRect(x, y, w, h);
    g.setLineDash([]);
    if (label) { g.lineWidth = 3; g.strokeStyle = "rgba(0,0,0,0.85)"; g.strokeText(label, x + 2, y - 4); g.fillStyle = col; g.fillText(label, x + 2, y - 4); }
  };
  if (im.crop) rect(im.crop, c2, "Print area", true);
  (im.boxes || []).forEach((b, i) => rect(b.box, b.used ? c1 : cb, `B${i + 1}${b.used ? "" : " (not used)"}`, !b.used));
  if (UI.drag && UI.drag.rect) rect(UI.drag.rect, UI.tool === "crop" ? c2 : c1, UI.tool === "crop" ? "Print area" : "Unpainted box", true);
}
function labelViews() {
  const on = !!UI.cmp;
  $("lab1").hidden = !on; $("lab2").hidden = !on || UI.flip;
  if (!on) return;
  $("lab1").textContent = describe(UI.view) + (UI.flip ? `  ·  F: ${describe(UI.cmp)}` : "");
  $("lab2").textContent = describe(UI.cmp);
}
function setCompare(v) {
  UI.cmp = VIEWS.includes(v) && v !== UI.view ? v : ""; store.put("cmp", UI.cmp);
  $("cmpSel").value = UI.cmp; $("zFlip").disabled = !UI.cmp;
  layoutWell(); labelViews(); renderViewbar(); scheduleFetch(0);
}
function layoutWell() {
  const split = !!UI.cmp && !UI.flip;
  const [cw, ch] = canvasSize(), c = V.iw && cw ? toImg(cw / 2, ch / 2) : null;
  $("well").classList.toggle("split", split); cv2.hidden = !split;
  const [cw2, ch2] = canvasSize();
  if (!c || V.atFit) { fitView(); return; }
  V.ox = cw2 / 2 - c[0] * V.s; V.oy = ch2 / 2 - c[1] * V.s; draw();
}
function flip() {
  if (!UI.cmp) return;
  const a = UI.view; UI.view = UI.cmp; UI.cmp = a; store.put("view", UI.view); store.put("cmp", UI.cmp);
  $("cmpSel").value = UI.cmp;
  [V.pic, V2.pic] = [V2.pic, V.pic]; [V.rect, V2.rect] = [V2.rect, V.rect];
  renderViewbar(); labelViews(); refreshStrip(); draw(); scheduleFetch(0);
}

// pointer: pan, or drag a box with a tool
function onDown(e) {
  if (!ST || !ST.image) return;
  const c = e.currentTarget, r = c.getBoundingClientRect();
  c.setPointerCapture(e.pointerId);
  const p = [e.clientX - r.left, e.clientY - r.top];
  if (UI.tool) { const [u, v] = toImg(...p); UI.drag = { kind: "box", u0: u, v0: v, rect: null }; }
  else { UI.drag = { kind: "pan", x: e.clientX, y: e.clientY, ox: V.ox, oy: V.oy }; c.classList.add("panning"); }
}
function onMove(e) {
  const d = UI.drag; if (!d) return;
  const r = e.currentTarget.getBoundingClientRect();
  if (d.kind === "pan") { V.ox = d.ox + e.clientX - d.x; V.oy = d.oy + e.clientY - d.y; V.atFit = false; draw(); scheduleFetch(); return; }
  const [u, v] = toImg(e.clientX - r.left, e.clientY - r.top);
  const x0 = Math.max(0, Math.min(d.u0, u)), y0 = Math.max(0, Math.min(d.v0, v));
  const x1 = Math.min(V.iw, Math.max(d.u0, u)), y1 = Math.min(V.ih, Math.max(d.v0, v));
  d.rect = [x0, y0, x1 - x0, y1 - y0]; draw();
}
async function onUp(e) {
  const d = UI.drag; UI.drag = null; e.currentTarget.classList.remove("panning");
  if (!d || d.kind !== "box") return;
  draw();
  if (!d.rect || d.rect[2] * V.s < 6 || d.rect[3] * V.s < 6) { status("Drag a larger box.", "warn"); return; }
  const box = d.rect.map(v => Math.round(v));
  if (UI.tool === "crop") await guarded("Refitting inside the print area", () => api("POST", "/api/crop", { box }));
  else {
    const boxes = (ST.image.boxes || []).map(b => b.box).concat([box]);
    if (boxes.length > 12) { status("At most 12 boxes.", "warn"); return; }
    await guarded("Checking the box and refitting", () => api("POST", "/api/boxes", { boxes }));
  }
}
function setTool(t) {
  UI.tool = UI.tool === t ? null : t;
  document.querySelectorAll("[data-tool]").forEach(b => b.classList.toggle("on", b.dataset.tool === UI.tool));
  [cv, cv2].forEach(c => c.classList.toggle("picking", !!UI.tool));
  $("toolHint").textContent = UI.tool === "crop" ? "Drag around the print itself: the reference is fitted from inside it only."
    : UI.tool === "box" ? "Drag over an area you have examined on the object and know is unpainted. Esc to stop."
    : "Pick a tool, then drag on the picture. Scroll to zoom, drag to pan, double-click to fit.";
}

// -- wiring ----------------------------------------------------------------------------------------------------------
function wire() {
  document.querySelectorAll("#flow button").forEach(b => b.addEventListener("click", () => setTab(b.dataset.tab)));
  document.querySelectorAll("#viewbar button").forEach(b => b.addEventListener("click", () => setView(b.dataset.view)));
  $("btnFolder").addEventListener("click", () => guarded("Listing the folder", () => api("POST", "/api/folder", { path: $("folder").value.trim() })));
  $("folder").addEventListener("keydown", e => { if (e.key === "Enter") $("btnFolder").click(); });
  $("addFiles").addEventListener("change", async e => {
    const files = [...e.target.files]; e.target.value = "";
    if (!files.length) return;
    const fd = new FormData(); files.forEach(f => fd.append("file", f, f.name));
    await guarded(`Adding ${files.length} file${files.length > 1 ? "s" : ""}`, () => api("POST", "/api/upload", fd));
  });
  $("files").addEventListener("click", e => {
    const b = e.target.closest(".photo"); if (!b) return;
    guarded("Reading and fitting the reference", () => api("POST", "/api/open", { path: b.dataset.path }));
  });
  document.querySelectorAll("#segSpace button").forEach(b => b.addEventListener("click", () => { UI.look.cs = b.dataset.v; if (UI.view !== "stretch") setView("stretch"); lookChanged(); }));
  document.querySelectorAll("#segEmph button").forEach(b => b.addEventListener("click", () => { UI.look.emph = b.dataset.v; if (UI.view !== "stretch") setView("stretch"); lookChanged(); }));
  $("k").addEventListener("input", () => { UI.look.k = +$("k").value; lookChanged(); });
  [["gTone", "tone"], ["gUnp", "unpainted"], ["gCap", "cap"], ["hatch", "hatch"]].forEach(([id, key]) =>
    $(id).addEventListener("change", () => { UI.look[key] = $(id).checked; lookChanged(); }));
  $("btnGuards").addEventListener("click", () => {
    const on = !(UI.look.tone || UI.look.unpainted || UI.look.cap);
    UI.look.tone = UI.look.unpainted = UI.look.cap = on; if (UI.view !== "stretch") setView("stretch"); lookChanged();
  });
  document.querySelectorAll("[data-tool]").forEach(b => b.addEventListener("click", () => setTool(b.dataset.tool)));
  $("btnCropClear").addEventListener("click", () => ST && ST.image && guarded("Refitting on the whole frame", () => api("POST", "/api/crop", { box: null })));
  $("btnBoxClear").addEventListener("click", () => ST && ST.image && guarded("Refitting without boxes", () => api("POST", "/api/boxes", { boxes: [] })));
  $("boxList").addEventListener("click", e => {
    const b = e.target.closest("[data-rm]"); if (!b) return;
    const boxes = ST.image.boxes.map(x => x.box).filter((_, i) => i !== +b.dataset.rm);
    guarded("Refitting", () => api("POST", "/api/boxes", { boxes }));
  });
  $("btnShowExpected").addEventListener("click", () => setView("expected"));
  $("btnCompareExpected").addEventListener("click", () => { setView("expected"); setCompare("boost"); });
  $("cmpSel").addEventListener("change", () => setCompare($("cmpSel").value));
  $("flipMode").checked = !!UI.flip;
  $("flipMode").addEventListener("change", () => { UI.flip = $("flipMode").checked; store.put("flip", UI.flip); layoutWell(); labelViews(); scheduleFetch(0); });
  $("zFlip").addEventListener("click", flip);
  $("zWide").addEventListener("click", () => { const w = !document.body.classList.contains("wide"); document.body.classList.toggle("wide", w); $("zWide").setAttribute("aria-pressed", String(w)); requestAnimationFrame(() => (V.atFit ? fitView() : (draw(), scheduleFetch(0)))); });
  $("zFull").addEventListener("click", () => { const s = $("stage"); if (document.fullscreenElement) document.exitFullscreen(); else if (s.requestFullscreen) s.requestFullscreen(); });
  document.addEventListener("fullscreenchange", () => requestAnimationFrame(() => (V.atFit ? fitView() : (draw(), scheduleFetch(0)))));
  $("zFit").addEventListener("click", fitView);
  $("z11").addEventListener("click", () => { const [cw, ch] = canvasSize(); const dpr = Math.min(2, window.devicePixelRatio || 1); zoomAt(cw / 2, ch / 2, (1 / dpr) / V.s); });
  [cv, cv2].forEach(c => {
    c.addEventListener("pointerdown", onDown); c.addEventListener("pointermove", onMove); c.addEventListener("pointerup", onUp);
    c.addEventListener("pointercancel", () => { UI.drag = null; draw(); });
    c.addEventListener("wheel", e => { e.preventDefault(); const r = c.getBoundingClientRect(); zoomAt(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0015)); }, { passive: false });
    c.addEventListener("dblclick", fitView);
  });
  window.addEventListener("resize", () => { if (V.atFit) fitView(); else { draw(); scheduleFetch(); } });
  document.addEventListener("keydown", e => {
    if (e.target.closest("input, select, textarea") || e.ctrlKey || e.metaKey || e.altKey) return;
    const n = "12345".indexOf(e.key);
    if (n >= 0) { setView(VIEWS[n]); e.preventDefault(); }
    else if (e.key === "f" || e.key === "F") flip();
    else if (e.key === "w" || e.key === "W") $("zWide").click();
    else if (e.key === "Escape" && UI.tool) setTool(UI.tool);
  });
  $("btnSettings").addEventListener("click", () => { const h = !$("project").hidden; $("project").hidden = h; $("btnSettings").setAttribute("aria-expanded", String(!h)); });
  $("btnSaveSettings").addEventListener("click", () => guarded("Applying the settings", () => api("POST", "/api/settings", {
    default_space: $("defSpace").value, near_black: +$("nearBlack").value, near_white: +$("nearWhite").value,
    T0: +$("t0").value, analysis_edge: +$("anaEdge").value })));
  $("btnExport").addEventListener("click", () => guarded("Exporting", async () => {
    const d = await api("POST", "/api/export", { look: lookParams(UI.view), folder: $("exFolder").value.trim(), edge: $("exEdge").value });
    $("exOut").className = "out ok"; $("exOut").innerHTML = `Written: <span class="mono">${esc(d.data.path)}</span>`;
  }));
  $("btnBatch").addEventListener("click", () => guarded("Starting the batch run", async () => {
    const looks = [...document.querySelectorAll("[data-b]")].filter(i => i.checked).map(i => lookParams(i.dataset.b));
    await api("POST", "/api/batch", { folder_in: $("bIn").value.trim(), folder_out: $("bOut").value.trim(), looks, edge: $("bEdge").value });
    watchBatch();
  }));
  $("btnBatchCancel").addEventListener("click", () => guarded("Cancelling after this photograph", () => api("POST", "/api/batch/cancel")));
  $("btnStop").addEventListener("click", () => $("stopDlg").showModal());
  $("stopCancel").addEventListener("click", () => $("stopDlg").close());
  $("stopGo").addEventListener("click", async () => {
    $("stopDlg").close();
    try { await api("POST", "/api/shutdown"); UI.leaving = true; document.body.classList.add("stopped"); $("stopped").hidden = false; }
    catch (e) { status(e.message, "bad"); }
  });
}

async function start() {
  buildStripLabels(); wire(); renderLook(); setTab(UI.tab); renderViewbar();
  $("cmpSel").value = UI.cmp; $("zFlip").disabled = !UI.cmp; layoutWell(); labelViews();
  try { const d = await (await apiGet("/api/state")).json(); if (d.ok) applyState(d.state); else status(d.error || "The state could not be read.", "bad"); }
  catch (e) { status("The visualiser's server is not answering. Is it still running?", "bad"); }
}
start();
