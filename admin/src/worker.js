// Text admin for CSEF and HDSF, as a Cloudflare Worker.
// The page in public/ is served as static assets. This file answers /api/*.
// Every save is a commit to main. A GitHub workflow in each repository then rebuilds the site.
import { SITES, TEXT_KEYS, NAMES, ruleFor } from "./sites.js";
import { textFields, applyEdits } from "./yamledit.js";
import { segments, applySegmentEdits } from "./htmledit.js";
import * as auth from "./auth.js";
import * as github from "./github.js";

const MAX_TEXT = 900 * 1024;

function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", ...headers },
  });
}

function fail(message, status = 400) {
  throw Object.assign(new Error(message), { status });
}

function siteOf(id) {
  const site = Object.prototype.hasOwnProperty.call(SITES, id) ? SITES[id] : null;
  if (!site) fail("Unknown site.", 404);
  return site;
}

function sameOrigin(request, url) {
  const origin = request.headers.get("Origin");
  return origin === url.origin;
}

async function body(request) {
  const type = request.headers.get("Content-Type") || "";
  if (!type.startsWith("application/json")) fail("Send JSON.", 415);
  const text = await request.text();
  if (text.length > MAX_TEXT * 1.2) fail("Too large.", 413);
  try {
    return JSON.parse(text);
  } catch {
    fail("Bad JSON.");
  }
}

function describe(path, rule, text) {
  if (rule.kind === "markdown") return { content: text };
  if (rule.kind === "yaml") return { fields: textFields(text, TEXT_KEYS) };
  return { segments: segments(text).map(({ index, tag, html }) => ({ index, tag, html })) };
}

function oneLine(s, max = 72) {
  return String(s || "").replace(/\s+/g, " ").trim().slice(0, max);
}

async function api(request, env, url) {
  const route = `${request.method} ${url.pathname.replace(/\/+$/, "")}`;
  const ip = request.headers.get("CF-Connecting-IP") || "local";

  if (request.method === "POST" && !sameOrigin(request, url)) fail("Wrong origin.", 403);

  // Which settings are in place, never their values. Helps when sign-in fails after setup.
  if (route === "GET /api/health") {
    let editors = 0, editorsError = null;
    try { editors = auth.editors(env).length; } catch (e) { editorsError = e.message; }
    return json({
      GITHUB_TOKEN: Boolean(env.GITHUB_TOKEN),
      SESSION_SECRET: Boolean(env.SESSION_SECRET && env.SESSION_SECRET.length >= 32),
      EDITORS: editorsError || (editors ? `${editors} editor${editors === 1 ? "" : "s"}`
        : env.EDITORS === undefined ? "missing: this deployment has no EDITORS setting" : "set, but it holds no editor with an email and a hash"),
    });
  }

  if (route === "POST /api/login") {
    const { email, password } = await body(request);
    const key = `${ip}|${String(email || "").toLowerCase()}`;
    if (!(await auth.loginAllowed(env, key))) fail("Too many attempts. Wait 15 minutes and try again.", 429);
    if (auth.editors(env).length === 0) fail("No editors are set up yet. Add the EDITORS secret in Cloudflare, then deploy.", 503);
    const editor = await auth.checkPassword(env, email, password);
    if (!editor) {
      auth.loginFailed(key);
      fail("Wrong email or password.", 401);
    }
    auth.loginSucceeded(key);
    return json({ email: editor.email, name: editor.name }, 200, { "Set-Cookie": await auth.sessionCookie(env, editor) });
  }
  if (route === "POST /api/logout") return json({ ok: true }, 200, { "Set-Cookie": auth.clearCookie(env) });

  const editor = await auth.currentEditor(request, env);
  if (!editor) fail("Please sign in.", 401);

  if (route === "GET /api/me") {
    const sites = Object.entries(SITES).map(([id, s]) => ({ id, name: s.name, title: s.title, site: s.site, repo: s.repo }));
    return json({ email: editor.email, name: editor.name, sites });
  }

  const site = siteOf(url.searchParams.get("site") || "");

  if (route === "GET /api/files") {
    const files = (await github.listFiles(env, site))
      .map((path) => ({ path, rule: ruleFor(site, path) }))
      .filter((f) => f.rule)
      .map(({ path, rule }) => ({ path, name: NAMES[path] || path.split("/").pop(), kind: rule.kind, group: rule.group }));
    return json({ files });
  }

  if (route === "GET /api/status") return json({ runs: await github.rebuildRuns(env, site) });

  const path = url.searchParams.get("path");
  const rule = ruleFor(site, path);
  if (!rule) fail("This file cannot be edited here.", 403);

  if (route === "GET /api/file") {
    const { sha, text } = await github.getFile(env, site, path);
    return json({ path, sha, kind: rule.kind, group: rule.group, history: `https://github.com/${site.repo}/commits/${site.branch}/${path}`, ...describe(path, rule, text) });
  }

  if (route === "POST /api/save") {
    const data = await body(request);
    if (typeof data.sha !== "string") fail("Missing file version.");
    const { sha, text } = await github.getFile(env, site, path);
    if (sha !== data.sha) fail("Someone saved this file after you opened it. Reload it and make your change again.", 409);
    let next;
    if (rule.kind === "markdown") {
      if (typeof data.content !== "string" || !data.content.trim()) fail("The text cannot be empty.");
      next = data.content.replace(/\r\n?/g, "\n").replace(/\s*$/, "\n");
    } else if (rule.kind === "yaml") {
      next = applyEdits(text, data.edits, TEXT_KEYS);
    } else {
      next = applySegmentEdits(text, data.edits);
    }
    if (next.length > MAX_TEXT) fail("The file would be too large.", 413);
    if (next === text) return json({ unchanged: true, sha });
    const summary = oneLine(data.message) || `edit ${path}`;
    const message = `admin: ${summary}\n\nEdited by ${editor.name} <${editor.email}> in the text admin.\nFile: ${path}`;
    const saved = await github.putFile(env, site, path, next, sha, message, editor);
    return json({ ...saved, ...describe(path, rule, next) });
  }

  fail("Not found.", 404);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/api/")) {
      return env.ASSETS ? env.ASSETS.fetch(request) : new Response("Not found", { status: 404 });
    }
    try {
      return await api(request, env, url);
    } catch (e) {
      const status = e.status || 500;
      if (status >= 500) console.error(e);
      return json({ error: status >= 500 && !e.status ? "Something went wrong. Nothing was saved." : e.message }, status);
    }
  },
};
