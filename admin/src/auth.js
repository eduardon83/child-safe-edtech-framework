// Email and password login, with a signed session cookie.
// Passwords are never stored: EDITORS holds PBKDF2-SHA256 hashes made with tools/add-editor.mjs.
const enc = new TextEncoder();
const dec = new TextDecoder();
export const ITERATIONS = 100000; // the most Cloudflare Workers allow for PBKDF2
const SESSION_HOURS = 12;
const DUMMY = "pbkdf2_sha256$100000$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";

export function b64u(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function fromB64u(s) {
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

function same(a, b) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a[i] ^ b[i];
  return d === 0;
}

export async function derive(password, salt, iterations = ITERATIONS) {
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations }, key, 256);
  return new Uint8Array(bits);
}

export async function makeHash(password) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  return `pbkdf2_sha256$${ITERATIONS}$${b64u(salt)}$${b64u(await derive(password, salt))}`;
}

export function editors(env) {
  let list;
  try {
    list = JSON.parse(env.EDITORS || "[]");
  } catch {
    throw Object.assign(new Error("EDITORS is not valid JSON."), { status: 500 });
  }
  return (Array.isArray(list) ? list : []).filter((e) => e && typeof e.email === "string" && typeof e.hash === "string")
    .map((e) => ({ email: e.email.trim().toLowerCase(), name: e.name || e.email, hash: e.hash }));
}

export async function checkPassword(env, email, password) {
  const ed = editors(env).find((e) => e.email === String(email || "").trim().toLowerCase());
  const [scheme, iter, salt, hash] = (ed ? ed.hash : DUMMY).split("$");
  if (scheme !== "pbkdf2_sha256") return null;
  const got = await derive(String(password || ""), fromB64u(salt), Math.min(Number(iter) || ITERATIONS, ITERATIONS));
  return same(got, fromB64u(hash)) && ed ? ed : null;
}

async function hmacKey(env) {
  if (!env.SESSION_SECRET || env.SESSION_SECRET.length < 32) {
    throw Object.assign(new Error("SESSION_SECRET is missing or shorter than 32 characters."), { status: 500 });
  }
  return crypto.subtle.importKey("raw", enc.encode(env.SESSION_SECRET), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

export function cookieName(env) {
  return env.DEV === "1" ? "sfe_admin" : "__Host-sfe_admin";
}

export async function sessionCookie(env, editor) {
  const payload = b64u(enc.encode(JSON.stringify({ e: editor.email, x: Math.floor(Date.now() / 1000) + SESSION_HOURS * 3600 })));
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", await hmacKey(env), enc.encode(payload)));
  const secure = env.DEV === "1" ? "" : "; Secure";
  return `${cookieName(env)}=${payload}.${b64u(sig)}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${SESSION_HOURS * 3600}${secure}`;
}

export function clearCookie(env) {
  const secure = env.DEV === "1" ? "" : "; Secure";
  return `${cookieName(env)}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0${secure}`;
}

// The editor for this request, or null.
export async function currentEditor(request, env) {
  const cookie = request.headers.get("Cookie") || "";
  const m = cookie.match(new RegExp("(?:^|;\\s*)" + cookieName(env).replace(/[$]/g, "\\$") + "=([^;]+)"));
  if (!m) return null;
  const [payload, sig] = m[1].split(".");
  if (!payload || !sig) return null;
  let ok = false;
  try {
    ok = await crypto.subtle.verify("HMAC", await hmacKey(env), fromB64u(sig), enc.encode(payload));
  } catch {
    return null;
  }
  if (!ok) return null;
  let data;
  try {
    data = JSON.parse(dec.decode(fromB64u(payload)));
  } catch {
    return null;
  }
  if (!data || data.x < Date.now() / 1000) return null;
  // Removing someone from EDITORS ends their sessions at once.
  return editors(env).find((e) => e.email === data.e) || null;
}

// Slow down password guessing. Uses the Cloudflare rate limit binding when it is set up, and memory otherwise.
const attempts = new Map();
export async function loginAllowed(env, key) {
  if (env.LOGIN_LIMITER && typeof env.LOGIN_LIMITER.limit === "function") {
    const { success } = await env.LOGIN_LIMITER.limit({ key });
    return success;
  }
  const now = Date.now();
  const a = attempts.get(key);
  return !(a && a.n >= 5 && now - a.t < 15 * 60 * 1000);
}

export function loginFailed(key) {
  const now = Date.now();
  const a = attempts.get(key);
  if (!a || now - a.t > 15 * 60 * 1000) attempts.set(key, { n: 1, t: now });
  else a.n += 1;
  if (attempts.size > 5000) attempts.clear();
}

export function loginSucceeded(key) {
  attempts.delete(key);
}
