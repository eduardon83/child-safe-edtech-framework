"use strict";
// Text admin for CSEF and HDSF. Talks to the Worker under /api/.
const $ = (s) => document.querySelector(s);
const state = { me: null, site: null, files: [], file: null, changes: new Map(), shown: 40, preview: false };

const LABELS = {
  title: "Title", requirement: "What to do", rationale: "Why", improvement: "How to improve", status: "Status",
  notes: "Note", note: "Note", summary: "Summary", description: "Description", desc: "Description", help: "Help text",
  intro: "Introduction", text: "Text", target: "Target", why: "Why", look_for: "What to look for", ideas: "Ideas",
  question: "Question", meaning: "Meaning", asks: "What it asks", aspect: "Aspect", csef_note: "CSEF note",
  watch: "What to watch", effect: "Effect", hero_title: "Page title", lead_new: "Lead (new pack)",
  lead_edit: "Lead (edit pack)", lead_tail: "Lead (end)",
};
const TAGS = { p: "Paragraph", h1: "Main heading", h2: "Heading", h3: "Subheading", h4: "Small heading", h5: "Small heading", h6: "Small heading",
  li: "List item", dt: "Term", dd: "Definition", figcaption: "Caption", blockquote: "Quote", td: "Table cell", th: "Table heading", caption: "Table caption" };

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function call(method, path, data) {
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: data ? { "Content-Type": "application/json" } : {},
    body: data ? JSON.stringify(data) : undefined,
  });
  let out = {};
  try { out = await res.json(); } catch { /* empty */ }
  if (res.status === 401 && path !== "/api/login") { showLogin(); throw new Error("Please sign in."); }
  if (!res.ok) throw Object.assign(new Error(out.error || `Error ${res.status}`), { status: res.status });
  return out;
}

function toast(html, bad = false, ms = 9000) {
  const t = $("#toast");
  t.innerHTML = html;
  t.className = "toast" + (bad ? " bad" : "");
  t.hidden = false;
  clearTimeout(toast.timer);
  if (ms) toast.timer = setTimeout(() => { t.hidden = true; }, ms);
}

// Writing checks from STYLE.md. They warn and never block.
function warnings(text) {
  const w = [];
  if (/—/.test(text)) w.push("Has an em dash. Use a full stop, a comma or a colon.");
  if (/\s–\s/.test(text)) w.push("Has an en dash used as a dash. Use a full stop, a comma or a colon.");
  if (/\S {2,}\S/.test(text)) w.push("Has a double space.");
  const long = String(text).replace(/<[^>]+>/g, "").split(/(?<=[.!?])\s+/).filter((s) => s.split(/\s+/).length > 30);
  if (long.length) w.push(`${long.length} sentence${long.length > 1 ? "s" : ""} over 30 words. Shorter is easier to read.`);
  return w;
}

function grow(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight + 2, 640) + "px";
}

// ------------------------------------------------------------------ login
function showLogin() {
  state.me = null;
  $("#app").hidden = true;
  $("#savebar").hidden = true;
  $("#logout").hidden = true;
  $("#who").textContent = "";
  $("#sites").innerHTML = "";
  $("#login").hidden = false;
  $("#login-form [name=email]").focus();
}

$("#login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target;
  $("#login-error").textContent = "";
  f.querySelector("button").disabled = true;
  try {
    await call("POST", "/api/login", { email: f.email.value, password: f.password.value });
    f.password.value = "";
    await start();
  } catch (e) {
    $("#login-error").textContent = e.message;
  } finally {
    f.querySelector("button").disabled = false;
  }
});

$("#logout").addEventListener("click", async () => {
  if (!leaveOk()) return;
  await call("POST", "/api/logout", {}).catch(() => {});
  state.changes.clear();
  showLogin();
});

// ------------------------------------------------------------------ navigation
function leaveOk() {
  return state.changes.size === 0 || confirm("You have changes that are not saved. Leave without saving?");
}

window.addEventListener("beforeunload", (ev) => {
  if (state.changes.size) { ev.preventDefault(); ev.returnValue = ""; }
});

function parseHash() {
  const h = decodeURIComponent(location.hash.slice(1));
  const i = h.indexOf("/");
  return i < 0 ? { site: h || null, path: null } : { site: h.slice(0, i), path: h.slice(i + 1) };
}

let lastHash = location.hash;
window.addEventListener("hashchange", () => {
  if (!state.me) return;
  if (!leaveOk()) { history.replaceState(null, "", lastHash); return; }
  lastHash = location.hash;
  route();
});

async function start() {
  state.me = await call("GET", "/api/me");
  $("#login").hidden = true;
  $("#app").hidden = false;
  $("#logout").hidden = false;
  $("#who").textContent = state.me.email;
  if (!parseHash().site) history.replaceState(null, "", "#" + state.me.sites[0].id);
  lastHash = location.hash;
  await route();
}

async function route() {
  const { site, path } = parseHash();
  const s = state.me.sites.find((x) => x.id === site) || state.me.sites[0];
  $("#sites").innerHTML = state.me.sites.map((x) =>
    `<a href="#${x.id}" title="${esc(x.title)}"${x.id === s.id ? ' aria-current="page"' : ""}>${esc(x.name)}</a>`).join("");
  if (!state.site || state.site.id !== s.id) {
    state.site = s;
    state.files = [];
    $("#file-list").innerHTML = '<p class="muted">Loading…</p>';
    try {
      state.files = (await call("GET", `/api/files?site=${s.id}`)).files;
    } catch (e) {
      $("#file-list").innerHTML = `<p class="error">${esc(e.message)}</p>`;
      return;
    }
  }
  renderFiles();
  if (path) await openFile(path);
  else {
    state.file = null;
    state.changes.clear();
    updateBar();
    $("#editor").innerHTML = `<div class="empty"><h2>${esc(s.title)}</h2><p>Pick a file on the left. The live site is <a href="${esc(s.site)}" target="_blank" rel="noopener">${esc(s.site.replace("https://", ""))}</a>.</p>
      <p>Each save is a commit to <code>${esc(s.repo)}</code>. A GitHub workflow then rebuilds the site, usually in 2 to 4 minutes. To undo, revert the commit on GitHub.</p></div>`;
  }
}

function renderFiles() {
  const q = $("#file-filter").value.trim().toLowerCase();
  const groups = {};
  for (const f of state.files) {
    if (q && !f.path.toLowerCase().includes(q)) continue;
    (groups[f.group] = groups[f.group] || []).push(f);
  }
  const current = parseHash().path;
  $("#file-list").innerHTML = Object.entries(groups).map(([g, fs]) => `<h3>${esc(g)}</h3>` + fs.map((f) =>
    `<a href="#${state.site.id}/${esc(f.path)}"${f.path === current ? ' aria-current="page"' : ""}>${esc(f.name || f.path.split("/").pop())}<br><small class="muted">${esc(f.path)}</small></a>`).join("")).join("")
    || '<p class="muted">No files match.</p>';
}
$("#file-filter").addEventListener("input", renderFiles);

// ------------------------------------------------------------------ editing
async function openFile(path) {
  state.changes.clear();
  state.shown = 40;
  state.preview = false;
  updateBar();
  $("#editor").innerHTML = '<p class="muted">Loading…</p>';
  try {
    state.file = await call("GET", `/api/file?site=${state.site.id}&path=${encodeURIComponent(path)}`);
  } catch (e) {
    state.file = null;
    $("#editor").innerHTML = `<p class="error">${esc(e.message)}</p>`;
    return;
  }
  renderEditor();
}

function header() {
  const f = state.file;
  const live = state.site.site;
  const known = state.files.find((x) => x.path === f.path);
  return `<div class="head"><h2>${esc(known ? known.name : f.path.split("/").pop())}</h2><span class="muted">${esc(f.path)}</span>
    <a href="${esc(f.history)}" target="_blank" rel="noopener">History and undo</a>
    <a href="${esc(live)}" target="_blank" rel="noopener">Open the site</a></div>`;
}

function renderEditor() {
  const f = state.file;
  if (f.kind === "markdown") return renderMarkdown();
  const items = f.kind === "yaml"
    ? f.fields.map((x) => ({ id: JSON.stringify(x.path), label: LABELS[x.key.split(" ")[0]] ? LABELS[x.key.split(" ")[0]] + (x.key.includes(" ") ? " " + x.key.split(" ")[1] : "") : x.key, group: x.group || "General", value: x.value }))
    : f.segments.map((x) => ({ id: String(x.index), label: TAGS[x.tag] || x.tag, group: null, value: x.html }));
  state.items = items;
  $("#editor").innerHTML = header() + `<div class="tools"><input id="field-filter" type="search" placeholder="${f.kind === "yaml" ? "Find by id or text" : "Find text"}" aria-label="Find"><span id="count" class="muted"></span></div><div id="fields"></div>`;
  $("#field-filter").addEventListener("input", () => { state.shown = 40; renderFields(); });
  renderFields();
}

function renderFields() {
  const q = $("#field-filter").value.trim().toLowerCase();
  const items = state.items.filter((x) => !q || (x.group || "").toLowerCase().includes(q) || x.value.toLowerCase().includes(q));
  // Group consecutive items (one rule, one source) into one card.
  const cards = [];
  for (const it of items) {
    const last = cards[cards.length - 1];
    if (last && it.group && last.group === it.group) last.items.push(it);
    else cards.push({ group: it.group, items: [it] });
  }
  $("#count").textContent = `${items.length} text${items.length === 1 ? "" : "s"}`;
  const shown = cards.slice(0, state.shown);
  $("#fields").innerHTML = shown.map((c) => `<div class="group">${c.group ? `<h4>${esc(c.group)}</h4>` : ""}${c.items.map(fieldHtml).join("")}</div>`).join("")
    + (cards.length > shown.length ? `<p class="more"><button class="ghost" id="more">Show more (${cards.length - shown.length} left)</button></p>` : "");
  $("#fields").querySelectorAll("textarea").forEach((ta) => {
    grow(ta);
    ta.addEventListener("input", () => onEdit(ta));
  });
  const more = $("#more");
  if (more) more.addEventListener("click", () => { state.shown += 40; renderFields(); });
}

function fieldHtml(it) {
  const value = state.changes.has(it.id) ? state.changes.get(it.id) : it.value;
  const w = warnings(value);
  return `<label class="field${state.changes.has(it.id) ? " changed" : ""}"><span>${esc(it.label)}</span>
    <textarea data-id="${esc(it.id)}" rows="2" spellcheck="true">${esc(value)}</textarea>
    ${w.length ? `<span class="warn">${w.map(esc).join(" ")}</span>` : ""}</label>`;
}

function onEdit(ta) {
  const it = state.items.find((x) => x.id === ta.dataset.id);
  const field = ta.closest(".field");
  if (ta.value.replace(/\s+$/, "") === it.value.replace(/\s+$/, "")) state.changes.delete(it.id);
  else state.changes.set(it.id, ta.value);
  field.classList.toggle("changed", state.changes.has(it.id));
  let warn = field.querySelector(".warn");
  const w = warnings(ta.value);
  if (w.length && !warn) { warn = document.createElement("span"); warn.className = "warn"; field.appendChild(warn); }
  if (warn) { warn.textContent = w.join(" "); warn.hidden = !w.length; }
  grow(ta);
  updateBar();
}

function renderMarkdown() {
  const f = state.file;
  const value = state.changes.has("md") ? state.changes.get("md") : f.content;
  $("#editor").innerHTML = header() + `<div class="tools"><button class="ghost" id="toggle">${state.preview ? "Edit" : "Preview"}</button>
    <span class="muted">Markdown: <code># Heading</code>, <code>**bold**</code>, <code>[link](https://…)</code>, <code>- list item</code>.</span></div>
    <div id="mdwarn"></div>` + (state.preview ? `<div class="preview">${markdown(value)}</div>` : `<textarea class="md" id="md" spellcheck="true">${esc(value)}</textarea>`);
  $("#toggle").addEventListener("click", () => { state.preview = !state.preview; renderMarkdown(); });
  const ta = $("#md");
  const warn = () => {
    const w = warnings(ta ? ta.value : value);
    $("#mdwarn").innerHTML = w.length ? `<p class="field"><span class="warn">${w.map(esc).join(" ")}</span></p>` : "";
  };
  warn();
  if (ta) ta.addEventListener("input", () => {
    if (ta.value === f.content) state.changes.delete("md"); else state.changes.set("md", ta.value);
    warn();
    updateBar();
  });
}

// A small Markdown preview. The site build is the real renderer.
function markdown(src) {
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, t, u) => /^(https?:|\/|#|\.|[a-z0-9-]+\/)/i.test(u) ? `<a href="${u}">${t}</a>` : t);
  const out = [];
  let list = null, para = [], code = null;
  const flush = () => {
    if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para = []; }
    if (list) { out.push(`<${list.tag}>${list.items.map((i) => `<li>${inline(i)}</li>`).join("")}</${list.tag}>`); list = null; }
  };
  for (const line of src.split("\n")) {
    if (code !== null) {
      if (/^```/.test(line)) { out.push(`<pre><code>${esc(code.join("\n"))}</code></pre>`); code = null; } else code.push(line);
      continue;
    }
    if (/^```/.test(line)) { flush(); code = []; continue; }
    let m;
    if ((m = line.match(/^(#{1,6})\s+(.*)/))) { flush(); out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); continue; }
    if ((m = line.match(/^\s*([-*]|\d+\.)\s+(.*)/))) {
      if (para.length) flush();
      const tag = /\d/.test(m[1]) ? "ol" : "ul";
      if (!list || list.tag !== tag) { flush(); list = { tag, items: [] }; }
      list.items.push(m[2]);
      continue;
    }
    if (!line.trim()) { flush(); continue; }
    if (list && /^\s+/.test(line)) { list.items[list.items.length - 1] += " " + line.trim(); continue; }
    if (list) flush();
    para.push(line.trim());
  }
  flush();
  return out.join("\n");
}

// ------------------------------------------------------------------ saving
function updateBar() {
  const n = state.changes.size;
  $("#savebar").hidden = n === 0;
  $("#changes").textContent = state.file && state.file.kind === "markdown" ? "The file has changes" : `${n} change${n === 1 ? "" : "s"}`;
}

$("#discard").addEventListener("click", () => {
  if (!confirm("Discard your changes to this file?")) return;
  state.changes.clear();
  updateBar();
  renderEditor();
});

$("#save").addEventListener("click", async () => {
  const f = state.file;
  if (!f || !state.changes.size) return;
  const btn = $("#save");
  btn.disabled = true;
  btn.textContent = "Saving…";
  const payload = { sha: f.sha, message: $("#message").value };
  if (f.kind === "markdown") payload.content = state.changes.get("md");
  else if (f.kind === "yaml") payload.edits = [...state.changes].map(([id, value]) => ({ path: JSON.parse(id), value }));
  else payload.edits = [...state.changes].map(([id, html]) => ({ index: Number(id), old: f.segments[Number(id)].html, html }));
  try {
    const r = await call("POST", `/api/save?site=${state.site.id}&path=${encodeURIComponent(f.path)}`, payload);
    state.changes.clear();
    $("#message").value = "";
    Object.assign(state.file, r);
    if (r.content !== undefined) state.file.content = r.content;
    updateBar();
    renderEditor();
    if (r.unchanged) toast("Nothing changed, so nothing was saved.");
    else {
      toast(`<strong>Saved.</strong> The site updates in a few minutes. <a href="${esc(r.url)}" target="_blank" rel="noopener">See the commit</a>.<br><span id="rebuild" class="muted">Waiting for the rebuild…</span>`, false, 0);
      watchRebuild(r.commit);
    }
  } catch (e) {
    toast(esc(e.message) + (e.status === 409 ? ' <button class="ghost" id="reload">Reload the file</button>' : ""), true, 0);
    const reload = $("#reload");
    if (reload) reload.addEventListener("click", () => { $("#toast").hidden = true; state.changes.clear(); openFile(f.path); });
  } finally {
    btn.disabled = false;
    btn.textContent = "Save and publish";
  }
});

async function watchRebuild(commit) {
  for (let i = 0; i < 24; i++) {
    await new Promise((r) => setTimeout(r, 10000));
    const el = $("#rebuild");
    if (!el) return;
    let runs = [];
    try { runs = (await call("GET", `/api/status?site=${state.site.id}`)).runs; } catch { return; }
    const run = runs[0];
    if (!run) { el.textContent = "Rebuild status is not available. Check the Actions tab on GitHub."; return; }
    if (run.status !== "completed") { el.innerHTML = `Rebuilding the site… <a href="${esc(run.url)}" target="_blank" rel="noopener">follow it</a>`; continue; }
    el.innerHTML = run.conclusion === "success"
      ? `The site is rebuilt. GitHub Pages publishes it within a minute or two.`
      : `<span class="error">The rebuild failed.</span> <a href="${esc(run.url)}" target="_blank" rel="noopener">See why</a>. Your text is saved; fix it here and save again.`;
    setTimeout(() => { $("#toast").hidden = true; }, 15000);
    return;
  }
}

// ------------------------------------------------------------------ boot
start().catch((e) => { if (e.message !== "Please sign in.") showLogin(); });
