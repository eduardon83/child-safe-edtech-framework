import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import worker from "../src/worker.js";
import { makeHash } from "../src/auth.js";
import { textFields, applyEdits } from "../src/yamledit.js";
import { segments, applySegmentEdits } from "../src/htmledit.js";
import { SITES, TEXT_KEYS, ruleFor } from "../src/sites.js";
import { mockGitHub } from "./mock-github.mjs";

const RULES = `# Rules
version: 0.1.0
rules:
  - id: CORE-ABC-01
    title: Say what the product is for
    level: MUST
    requirement: >
      The product has one written purpose. The same text is used
      in the store and on the website.
    detection:
      type: manifest
      message: "not editable"
    notes:
      - "Portugal: ask the authority: CNPD."
`;
const PAGE = `<section><h1>Title {version}</h1><p>Intro text with <a href="x/">a link</a>.</p>
<button>Click me</button><label>Name</label><p><a href="a/">Only a link</a></p>
<script>const s = "<p>not text</p>";</script><ul><li>One useful item here</li><li>Two</li></ul></section>`;

async function setup() {
  const dir = mkdtempSync(join(tmpdir(), "admin-"));
  for (const id of ["csef", "hdsf"]) {
    mkdirSync(join(dir, id, "framework"), { recursive: true });
    mkdirSync(join(dir, id, "tooling"), { recursive: true });
    writeFileSync(join(dir, id, "framework", "rules.yaml"), RULES);
    writeFileSync(join(dir, id, "framework", "00-introduction.md"), "# Intro\n\nHello.\n");
    writeFileSync(join(dir, id, "framework", "legislation.md"), "# Generated\n");
    writeFileSync(join(dir, id, "tooling", "home.template.html"), PAGE);
    writeFileSync(join(dir, id, "tooling", "build.py"), "print('code')\n");
  }
  const log = [];
  const env = {
    GITHUB_TOKEN: "t",
    SESSION_SECRET: "x".repeat(40),
    EDITORS: JSON.stringify([{ email: "ed@example.org", name: "Ed", hash: await makeHash("correct horse battery") }]),
    FETCH: mockGitHub({ [SITES.csef.repo]: join(dir, "csef"), [SITES.hdsf.repo]: join(dir, "hdsf") }, log),
  };
  const base = "https://admin.example.org";
  let cookie = "";
  const call = async (method, path, data, extra = {}) => {
    const r = await worker.fetch(new Request(base + path, {
      method,
      headers: { Origin: base, Cookie: cookie, ...(data ? { "Content-Type": "application/json" } : {}), ...extra },
      body: data ? JSON.stringify(data) : undefined,
    }), env);
    const set = r.headers.get("Set-Cookie");
    if (set) cookie = set.split(";")[0];
    return { status: r.status, body: await r.json() };
  };
  return { dir, env, log, call };
}

test("sign in is required and wrong passwords are refused", async () => {
  const { call } = await setup();
  assert.equal((await call("GET", "/api/me")).status, 401);
  assert.equal((await call("POST", "/api/login", { email: "ed@example.org", password: "wrong" })).status, 401);
  assert.equal((await call("POST", "/api/login", { email: "nobody@example.org", password: "correct horse battery" })).status, 401);
  const ok = await call("POST", "/api/login", { email: "ED@example.org ", password: "correct horse battery" });
  assert.equal(ok.status, 200);
  assert.equal((await call("GET", "/api/me")).body.email, "ed@example.org");
  await call("POST", "/api/logout", {});
  assert.equal((await call("GET", "/api/me")).status, 401);
});

test("posts from another origin are refused", async () => {
  const { call } = await setup();
  const r = await call("POST", "/api/login", { email: "ed@example.org", password: "correct horse battery" }, { Origin: "https://evil.example" });
  assert.equal(r.status, 403);
});

test("a forged or expired session is refused", async () => {
  const { env } = await setup();
  const r = await worker.fetch(new Request("https://a.example/api/me", { headers: { Cookie: "__Host-sfe_admin=eyJlIjoiZWRAZXhhbXBsZS5vcmciLCJ4Ijo5OTk5OTk5OTk5fQ.AAAA" } }), env);
  assert.equal(r.status, 401);
});

test("only information files are listed and generated files are left out", async () => {
  const { call } = await setup();
  await call("POST", "/api/login", { email: "ed@example.org", password: "correct horse battery" });
  const files = (await call("GET", "/api/files?site=hdsf")).body.files.map((f) => f.path).sort();
  assert.deepEqual(files, ["framework/00-introduction.md", "framework/rules.yaml", "tooling/home.template.html"]);
  assert.equal((await call("GET", "/api/file?site=hdsf&path=tooling/build.py")).status, 403);
  assert.equal((await call("GET", "/api/file?site=hdsf&path=framework/legislation.md")).status, 403);
  assert.equal((await call("GET", "/api/file?site=hdsf&path=../secret")).status, 403);
});

test("rule texts are editable, levels and checks are not", async () => {
  const { call, dir, log } = await setup();
  await call("POST", "/api/login", { email: "ed@example.org", password: "correct horse battery" });
  const f = (await call("GET", "/api/file?site=csef&path=framework/rules.yaml")).body;
  assert.deepEqual(f.fields.map((x) => x.key), ["title", "requirement", "notes 1"]);
  assert.equal((await call("POST", "/api/save?site=csef&path=framework/rules.yaml", { sha: f.sha, edits: [{ path: ["rules", 0, "level"], value: "MAY" }] })).status, 403);
  assert.equal((await call("POST", "/api/save?site=csef&path=framework/rules.yaml", { sha: f.sha, edits: [{ path: ["rules", 0, "detection", "message"], value: "x" }] })).status, 403);
  const r = await call("POST", "/api/save?site=csef&path=framework/rules.yaml", { sha: f.sha, message: "Shorter title", edits: [{ path: ["rules", 0, "title"], value: "Write down: the purpose" }] });
  assert.equal(r.status, 200, JSON.stringify(r.body));
  const text = readFileSync(join(dir, "csef", "framework", "rules.yaml"), "utf8");
  assert.equal(text, RULES.replace("title: Say what the product is for", 'title: "Write down: the purpose"'));
  assert.match(log[0].message, /^admin: Shorter title/);
  assert.deepEqual(log[0].author, { name: "Ed", email: "ed@example.org" });
  // The old version can no longer be saved over the new one.
  const stale = await call("POST", "/api/save?site=csef&path=framework/rules.yaml", { sha: f.sha, edits: [{ path: ["rules", 0, "title"], value: "Other" }] });
  assert.equal(stale.status, 409);
});

test("page text: paragraphs and headings only, placeholders kept", async () => {
  const { call } = await setup();
  await call("POST", "/api/login", { email: "ed@example.org", password: "correct horse battery" });
  const f = (await call("GET", "/api/file?site=hdsf&path=tooling/home.template.html")).body;
  assert.deepEqual(f.segments.map((s) => s.tag), ["h1", "p", "li"]);
  const save = (edits) => call("POST", "/api/save?site=hdsf&path=tooling/home.template.html", { sha: f.sha, edits });
  assert.equal((await save([{ index: 0, old: f.segments[0].html, html: "Title" }])).status, 400);
  assert.equal((await save([{ index: 1, old: f.segments[1].html, html: "<img src=x onerror=alert(1)>" }])).status, 400);
  assert.equal((await save([{ index: 1, old: "something else", html: "New" }])).status, 409);
  const ok = await save([{ index: 1, old: f.segments[1].html, html: "New intro with <strong>bold</strong> text." }]);
  assert.equal(ok.status, 200, JSON.stringify(ok.body));
  assert.equal(ok.body.segments[1].html, "New intro with <strong>bold</strong> text.");
});

test("markdown guides are saved as written", async () => {
  const { call, dir } = await setup();
  await call("POST", "/api/login", { email: "ed@example.org", password: "correct horse battery" });
  const f = (await call("GET", "/api/file?site=hdsf&path=framework/00-introduction.md")).body;
  const r = await call("POST", "/api/save?site=hdsf&path=framework/00-introduction.md", { sha: f.sha, content: "# Intro\r\n\r\nHello again." });
  assert.equal(r.status, 200);
  assert.equal(readFileSync(join(dir, "hdsf", "framework", "00-introduction.md"), "utf8"), "# Intro\n\nHello again.\n");
});

test("YAML edits keep every other line as it was", () => {
  const out = applyEdits(RULES, [{ path: ["rules", 0, "requirement"], value: "One purpose.\n\nA second paragraph." }], TEXT_KEYS);
  const before = RULES.split("\n");
  const after = out.split("\n");
  assert.equal(after.slice(0, 6).join("\n"), before.slice(0, 6).join("\n"));
  assert.equal(after.slice(-6).join("\n"), before.slice(-6).join("\n"));
  assert.equal(textFields(out, TEXT_KEYS)[1].value, "One purpose.\n\nA second paragraph.\n");
});

test("HTML segments skip buttons, labels, scripts and link-only blocks", () => {
  const s = segments(PAGE);
  assert.ok(s.every((x) => !/Click me|Name|not text|Only a link/.test(x.html)));
  assert.throws(() => applySegmentEdits(PAGE, [{ index: 1, old: s[1].html, html: "<b>open" }]));
});

test("the real repositories can be listed", () => {
  for (const site of Object.values(SITES)) {
    assert.ok(ruleFor(site, "framework/rules.yaml"));
    assert.equal(ruleFor(site, "tooling/build.py"), null);
    assert.equal(ruleFor(site, "packs/_template.yaml"), null);
  }
});

test("health shows which settings exist, and an empty EDITORS is reported", async () => {
  const { env } = await setup();
  const h = await (await worker.fetch(new Request("https://a.example/api/health"), env)).json();
  assert.deepEqual(h, { GITHUB_TOKEN: true, SESSION_SECRET: true, EDITORS: "1 editor" });
  const none = await (await worker.fetch(new Request("https://a.example/api/health"), { ...env, EDITORS: undefined })).json();
  assert.match(none.EDITORS, /^missing/);
  const empty = { ...env, EDITORS: "[]" };
  const r = await worker.fetch(new Request("https://a.example/api/login", { method: "POST", headers: { Origin: "https://a.example", "Content-Type": "application/json" }, body: JSON.stringify({ email: "a@b.c", password: "x" }) }), empty);
  assert.equal(r.status, 503);
});

test("common paste slips in EDITORS still work", async () => {
  const { parseEditors } = await import("../src/auth.js");
  const one = { email: "a@b.c", hash: "h" };
  assert.equal(parseEditors(JSON.stringify([one])).length, 1);
  assert.equal(parseEditors(JSON.stringify(one)).length, 1);
  assert.equal(parseEditors(JSON.stringify(JSON.stringify([one]))).length, 1);
  assert.equal(parseEditors("  \n" + JSON.stringify([one]) + "\n").length, 1);
  assert.throws(() => parseEditors("pbkdf2_sha256$1$a$b"));
});
