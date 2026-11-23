// Run the admin on http://localhost:8787 against copies of the repositories, with a fake GitHub.
//   node test/dev-server.mjs /path/to/csef-copy /path/to/hdsf-copy
// Sign in with admin@example.org and "correct horse battery".
import { createServer } from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { join, extname } from "node:path";
import worker from "../src/worker.js";
import { makeHash } from "../src/auth.js";
import { mockGitHub } from "./mock-github.mjs";

const [csef, hdsf] = process.argv.slice(2);
const port = Number(process.env.PORT || 8787);
const env = {
  DEV: "1",
  GITHUB_TOKEN: "test",
  SESSION_SECRET: "a-local-test-secret-that-is-long-enough",
  EDITORS: JSON.stringify([{ email: "admin@example.org", name: "Test Editor", hash: await makeHash("correct horse battery") }]),
  FETCH: mockGitHub({ "eduardon83/child-safe-edtech-framework": csef, "eduardon83/digital-health-safety-framework": hdsf }),
};
const PUBLIC = new URL("../public/", import.meta.url).pathname;
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css" };
const headers = Object.fromEntries(readFileSync(join(PUBLIC, "_headers"), "utf8").split("\n").filter((l) => /^\s+\S+:/.test(l)).map((l) => l.trim().split(/:\s(.+)/).slice(0, 2)));

createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${port}`);
  if (url.pathname.startsWith("/api/")) {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const request = new Request(url, { method: req.method, headers: req.headers, body: ["GET", "HEAD"].includes(req.method) ? undefined : Buffer.concat(chunks) });
    const r = await worker.fetch(request, env);
    res.writeHead(r.status, Object.fromEntries(r.headers));
    res.end(Buffer.from(await r.arrayBuffer()));
    return;
  }
  const file = join(PUBLIC, url.pathname === "/" ? "index.html" : url.pathname.slice(1));
  if (!file.startsWith(PUBLIC) || !existsSync(file) || file.endsWith("_headers")) { res.writeHead(404); res.end("Not found"); return; }
  res.writeHead(200, { "Content-Type": TYPES[extname(file)] || "application/octet-stream", ...headers });
  res.end(readFileSync(file));
}).listen(port, () => console.log(`Admin on http://localhost:${port}`));
