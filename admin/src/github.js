// Read and write files in the framework repositories through the GitHub API.
const API = "https://api.github.com";
const enc = new TextEncoder();
const dec = new TextDecoder();

function fail(message, status) {
  throw Object.assign(new Error(message), { status });
}

async function gh(env, path, init = {}) {
  if (!env.GITHUB_TOKEN) fail("GITHUB_TOKEN is not set.", 500);
  const res = await (env.FETCH || fetch)(API + path, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "kendir-framework-admin",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
    },
  });
  if (res.status === 409) fail("Someone saved this file in the meantime. Reload it and make your change again.", 409);
  if (res.status === 401 || res.status === 403) fail("GitHub refused the request. Check that GITHUB_TOKEN is valid and can write to the repository.", 502);
  if (res.status === 404) fail("Not found on GitHub.", 404);
  if (!res.ok) fail(`GitHub error ${res.status}.`, 502);
  return res.json();
}

const enc64 = (text) => {
  const bytes = enc.encode(text);
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
};
const dec64 = (b64) => dec.decode(Uint8Array.from(atob(b64.replace(/\s/g, "")), (c) => c.charCodeAt(0)));
const quote = (path) => path.split("/").map(encodeURIComponent).join("/");

export async function listFiles(env, site) {
  const tree = await gh(env, `/repos/${site.repo}/git/trees/${encodeURIComponent(site.branch)}?recursive=1`);
  return tree.tree.filter((t) => t.type === "blob").map((t) => t.path);
}

export async function getFile(env, site, path) {
  const f = await gh(env, `/repos/${site.repo}/contents/${quote(path)}?ref=${encodeURIComponent(site.branch)}`);
  if (Array.isArray(f) || f.type !== "file") fail("Not a file.", 400);
  if (f.encoding !== "base64") fail("This file is too large to edit here.", 413);
  return { sha: f.sha, text: dec64(f.content) };
}

export async function putFile(env, site, path, text, sha, message, editor) {
  const body = {
    message,
    content: enc64(text),
    sha,
    branch: site.branch,
    author: { name: editor.name, email: editor.email },
  };
  const r = await gh(env, `/repos/${site.repo}/contents/${quote(path)}`, { method: "PUT", body: JSON.stringify(body) });
  return { sha: r.content.sha, commit: r.commit.sha, url: r.commit.html_url };
}

// The latest runs of the workflow that rebuilds the site. Needs "Actions: read" on the token; empty otherwise.
export async function rebuildRuns(env, site) {
  try {
    const r = await gh(env, `/repos/${site.repo}/actions/workflows/rebuild-after-edit.yml/runs?per_page=5&branch=${encodeURIComponent(site.branch)}`);
    return r.workflow_runs.map((w) => ({ status: w.status, conclusion: w.conclusion, title: w.display_title, url: w.html_url, at: w.created_at }));
  } catch {
    return [];
  }
}
