#!/usr/bin/env node
// Add or update an editor in editors.json (kept on your computer only, never committed).
// Then send the file to Cloudflare:  npx wrangler secret put EDITORS < editors.json
//
//   node tools/add-editor.mjs                 asks for email, name and password
//   node tools/add-editor.mjs --free-plan     lighter hash that fits the 10 ms CPU limit of Workers Free
//   node tools/add-editor.mjs --remove EMAIL  removes an editor
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { createInterface } from "node:readline";
import { derive, b64u } from "../src/auth.js";

const FILE = new URL("../editors.json", import.meta.url);
const args = process.argv.slice(2);
const iterations = args.includes("--free-plan") ? 40000 : 100000;
const list = existsSync(FILE) ? JSON.parse(readFileSync(FILE, "utf8")) : [];

function save(next) {
  writeFileSync(FILE, JSON.stringify(next, null, 2) + "\n", { mode: 0o600 });
  console.log(`\neditors.json now has ${next.length} editor${next.length === 1 ? "" : "s"}.`);
  console.log("Send it to Cloudflare with:\n  npx wrangler secret put EDITORS < editors.json\n");
}

const r = args.indexOf("--remove");
if (r >= 0) {
  const email = String(args[r + 1] || "").toLowerCase();
  save(list.filter((e) => e.email.toLowerCase() !== email));
  process.exit(0);
}

const rl = createInterface({ input: process.stdin, output: process.stdout, terminal: true });
const ask = (q, hidden = false) => new Promise((res) => {
  rl.question(q, (a) => { if (hidden) process.stdout.write("\n"); res(a); });
  if (hidden) rl._writeToOutput = (s) => { if (s.startsWith(q)) rl.output.write(q); };
});

const email = (await ask("Email: ")).trim().toLowerCase();
const name = (await ask("Name (shown in commits): ")).trim() || email;
const restore = rl._writeToOutput;
const password = await ask("Password (at least 12 characters): ", true);
const again = await ask("Password again: ", true);
rl._writeToOutput = restore;
rl.close();

if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { console.error("That email does not look right."); process.exit(1); }
if (password.length < 12) { console.error("Use at least 12 characters. A short sentence works well."); process.exit(1); }
if (password !== again) { console.error("The passwords are not the same."); process.exit(1); }

const salt = crypto.getRandomValues(new Uint8Array(16));
const hash = `pbkdf2_sha256$${iterations}$${b64u(salt)}$${b64u(await derive(password, salt, iterations))}`;
save([...list.filter((e) => e.email.toLowerCase() !== email), { email, name, hash }]);
