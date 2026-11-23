// A tiny stand-in for the GitHub API, backed by folders on disk. For tests and local runs only.
import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";

const blobSha = (buf) => createHash("sha1").update(`blob ${buf.length}\0`).update(buf).digest("hex");

function walk(dir, base = "") {
  const out = [];
  for (const name of readdirSync(dir)) {
    if ([".git", "node_modules", "docs", "dist", "__pycache__", ".pytest_cache"].includes(name)) continue;
    const p = join(dir, name);
    const rel = base ? `${base}/${name}` : name;
    if (statSync(p).isDirectory()) out.push(...walk(p, rel));
    else out.push(rel);
  }
  return out;
}

export function mockGitHub(roots, log = []) {
  const reply = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
  return async (url, init = {}) => {
    const u = new URL(url);
    const m = u.pathname.match(/^\/repos\/([^/]+\/[^/]+)\/(.*)$/);
    if (!m || !roots[m[1]]) return reply({ message: "Not Found" }, 404);
    const root = roots[m[1]];
    const rest = m[2];
    if (!/^Bearer \S+/.test(init.headers?.Authorization || "")) return reply({}, 401);
    if (rest.startsWith("git/trees/")) return reply({ tree: walk(root).map((path) => ({ path, type: "blob" })) });
    if (rest.startsWith("actions/workflows/")) return reply({ workflow_runs: [{ status: "completed", conclusion: "success", display_title: "admin: test", html_url: "https://example.org/run", created_at: new Date().toISOString() }] });
    if (rest.startsWith("contents/")) {
      const path = decodeURIComponent(rest.slice("contents/".length));
      const file = join(root, path);
      if ((init.method || "GET") === "GET") {
        if (!existsSync(file)) return reply({ message: "Not Found" }, 404);
        const buf = readFileSync(file);
        return reply({ type: "file", encoding: "base64", sha: blobSha(buf), content: buf.toString("base64") });
      }
      if (init.method === "PUT") {
        const body = JSON.parse(init.body);
        const current = existsSync(file) ? blobSha(readFileSync(file)) : null;
        if (body.sha !== current) return reply({ message: "sha does not match" }, 409);
        const buf = Buffer.from(body.content, "base64");
        writeFileSync(file, buf);
        log.push({ repo: m[1], path, message: body.message, author: body.author });
        return reply({ content: { sha: blobSha(buf) }, commit: { sha: "c0ffee" + log.length, html_url: `https://github.com/${m[1]}/commit/c0ffee${log.length}` } });
      }
    }
    return reply({ message: "Not Found" }, 404);
  };
}
