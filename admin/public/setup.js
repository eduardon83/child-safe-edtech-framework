"use strict";
// Makes the SESSION_SECRET and EDITORS values in the browser. Nothing leaves this page.
const $ = (s) => document.querySelector(s);
const b64u = (bytes) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

$("#secret").value = b64u(crypto.getRandomValues(new Uint8Array(48)));

async function hash(password, iterations) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = new Uint8Array(await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations }, key, 256));
  return `pbkdf2_sha256$${iterations}$${b64u(salt)}$${b64u(bits)}`;
}

$("#editor-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("#error").textContent = "";
  const email = $("#email").value.trim().toLowerCase();
  const name = $("#name").value.trim() || email;
  const password = $("#password").value;
  let list = [];
  try {
    const current = $("#current").value.trim();
    list = current ? JSON.parse(current) : [];
    if (!Array.isArray(list)) throw new Error();
  } catch {
    $("#error").textContent = "The current EDITORS value is not valid. Paste it exactly as you saved it.";
    return;
  }
  if (password.length < 12) { $("#error").textContent = "Use at least 12 characters. A short sentence works well."; return; }
  if (password !== $("#again").value) { $("#error").textContent = "The passwords are not the same."; return; }
  const entry = { email, name, hash: await hash(password, $("#free").checked ? 40000 : 100000) };
  list = [...list.filter((e) => String(e.email).toLowerCase() !== email), entry];
  $("#editors").value = JSON.stringify(list);
  $("#password").value = "";
  $("#again").value = "";
  $("#result").hidden = false;
});

document.addEventListener("click", async (ev) => {
  const id = ev.target.dataset && ev.target.dataset.copy;
  if (!id) return;
  const el = $("#" + id);
  el.select();
  try { await navigator.clipboard.writeText(el.value); } catch { document.execCommand("copy"); }
  ev.target.textContent = "Copied";
  setTimeout(() => { ev.target.textContent = "Copy"; }, 1500);
});

$("#check").addEventListener("click", async () => {
  const out = $("#health");
  out.innerHTML = "<li>Checking…</li>";
  try {
    const h = await (await fetch("/api/health", { cache: "no-store" })).json();
    const line = (name, v) => `<li><code>${name}</code>: ${v === true ? "set" : v === false ? "<strong class=\"error\">missing</strong>" : String(v).replace(/[<&]/g, "")}</li>`;
    out.innerHTML = line("GITHUB_TOKEN", h.GITHUB_TOKEN) + line("SESSION_SECRET", h.SESSION_SECRET) + line("EDITORS", h.EDITORS);
  } catch {
    out.innerHTML = "<li class=\"error\">The check did not answer. The admin may still be deploying.</li>";
  }
});
