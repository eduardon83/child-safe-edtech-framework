// Edit text values in a YAML file without touching anything else.
// Only the source span of each changed value is replaced, so comments, order and layout stay.
// After the change the file is parsed again and compared: only the edited values may differ.
import { parseDocument, isMap, isSeq, isScalar } from "yaml";

const SKIP = new Set(["detection", "patterns", "forbid_patterns", "forbid_phrases", "forbid_dependencies"]);

function fail(message, status = 400) {
  const e = new Error(message);
  e.status = status;
  throw e;
}

function parse(src) {
  const doc = parseDocument(src);
  if (doc.errors.length) fail("The file is not valid YAML: " + doc.errors[0].message, 422);
  return doc;
}

function keyOf(pair) {
  return isScalar(pair.key) && pair.key.value !== null ? pair.key.value : null;
}

function itemLabel(map) {
  if (!isMap(map)) return null;
  const id = map.get("id");
  const title = map.get("title");
  if (typeof id === "string" && typeof title === "string") return `${id} · ${title}`;
  if (typeof id === "string") return id;
  return null;
}

// List every editable text value: [{path, key, value, group, multiline}]
export function textFields(src, keyRe) {
  const doc = parse(src);
  const out = [];
  const walk = (node, path, group) => {
    if (isMap(node)) {
      const label = itemLabel(node) || group;
      for (const pair of node.items) {
        const key = keyOf(pair);
        if (key === null || SKIP.has(String(key))) continue;
        const v = pair.value;
        const p = [...path, key];
        if (isScalar(v) && typeof v.value === "string" && keyRe.test(String(key))) {
          out.push({ path: p, key, value: v.value, group: label });
        } else if (isSeq(v) && keyRe.test(String(key)) && v.items.every((x) => isScalar(x) && typeof x.value === "string")) {
          v.items.forEach((x, i) => out.push({ path: [...p, i], key: `${key} ${i + 1}`, value: x.value, group: label }));
        } else if (isMap(v) || isSeq(v)) {
          walk(v, p, label || (path.length === 0 ? key : group));
        }
      }
    } else if (isSeq(node)) {
      node.items.forEach((x, i) => walk(x, [...path, i], group));
    }
  };
  walk(doc.contents, [], null);
  return out;
}

function allowedPath(path, keyRe) {
  const last = path[path.length - 1];
  const key = typeof last === "number" ? path[path.length - 2] : last;
  return typeof key === "string" && keyRe.test(key) && !path.some((k) => SKIP.has(k));
}

const PLAIN_BAD_START = /^[-?:,[\]{}#&*!|>'"%@`\s]/;
const PLAIN_SPECIAL = /^(true|false|yes|no|on|off|null|~|[-+]?[\d.][\d._:eE+-]*|\.inf|\.nan)$/i;

function plainSafe(v) {
  return v.length > 0 && !v.includes("\n") && !PLAIN_BAD_START.test(v) && !PLAIN_SPECIAL.test(v) &&
    !/: |:$| #|\s$|\t/.test(v);
}

// Indentation for block content that replaces the value starting at pos.
function blockIndent(src, pos) {
  const start = src.lastIndexOf("\n", pos - 1) + 1;
  let lead = 0;
  while (src[start + lead] === " ") lead++;
  let rest = src.slice(start + lead, pos);
  while (rest.startsWith("- ")) {
    lead += 2;
    rest = rest.slice(2).replace(/^ +/, (s) => { lead += s.length; return ""; });
  }
  return rest === "" ? lead : lead + 2;
}

function wrap(line, width) {
  if (line.length <= width || /\s\s/.test(line)) return [line];
  const out = [];
  let rest = line;
  while (rest.length > width) {
    let cut = rest.lastIndexOf(" ", width);
    if (cut <= 0) cut = rest.indexOf(" ", width);
    if (cut <= 0) break;
    out.push(rest.slice(0, cut));
    rest = rest.slice(cut + 1);
  }
  out.push(rest);
  return out;
}

function blockScalar(value, indent, folded, endsLine) {
  const pad = " ".repeat(indent);
  const trail = value.match(/\n*$/)[0].length;
  const chomp = trail === 0 ? "-" : trail === 1 ? "" : "+";
  const body = value.replace(/\n+$/, "");
  const lines = body.split("\n");
  if (folded && lines.some((l) => /^\s/.test(l) || /\s$/.test(l))) folded = false;
  let content;
  if (folded) {
    const parts = [];
    lines.forEach((l, i) => {
      if (i > 0) parts.push("");
      parts.push(...(l === "" ? [] : wrap(l, Math.max(40, 116 - indent))));
    });
    content = parts;
  } else {
    content = lines;
  }
  const text = (folded ? ">" : "|") + chomp + "\n" + content.map((l) => (l === "" ? "" : pad + l)).join("\n");
  const extra = trail > 1 ? "\n".repeat(trail - 1) : "";
  return text + (endsLine ? "\n" + extra : "");
}

function serialize(src, node, value, safe) {
  const [start, end] = node.range;
  const type = node.type;
  if (safe) return JSON.stringify(value);
  if (type === "BLOCK_FOLDED" || type === "BLOCK_LITERAL") {
    const headerEnd = src.indexOf("\n", start);
    const first = src.slice(headerEnd + 1).match(/^(?:[ \t]*\n)*( *)/);
    const indent = first && first[1].length > 0 ? first[1].length : blockIndent(src, start);
    return blockScalar(value, indent, type === "BLOCK_FOLDED", src[end - 1] === "\n");
  }
  if (value.includes("\n")) return blockScalar(value, blockIndent(src, start), false, false);
  if (type === "PLAIN" && plainSafe(value)) return value;
  if (type === "QUOTE_SINGLE") return "'" + value.replace(/'/g, "''") + "'";
  return JSON.stringify(value);
}

function setIn(obj, path, value) {
  let o = obj;
  for (let i = 0; i < path.length - 1; i++) o = o[path[i]];
  o[path[path.length - 1]] = value;
}

function sameJSON(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

// edits: [{path: [...], value: "new text"}]. Returns the new file text.
export function applyEdits(src, edits, keyRe) {
  if (!Array.isArray(edits) || edits.length === 0) fail("Nothing to save.");
  const doc = parse(src);
  const expected = doc.toJS();
  const nodes = [];
  for (const e of edits) {
    if (!Array.isArray(e.path) || typeof e.value !== "string") fail("Bad edit.");
    if (!allowedPath(e.path, keyRe)) fail(`"${e.path.join(".")}" is not information text and cannot be edited here.`, 403);
    const node = doc.getIn(e.path, true);
    if (!isScalar(node) || typeof node.value !== "string") fail(`"${e.path.join(".")}" is not a text value.`);
    // Keep the line endings the value had, so a trimmed textarea does not change the YAML style.
    e.value = e.value.replace(/\r\n?/g, "\n").replace(/\s+$/, "") + node.value.match(/\n*$/)[0];
    if (node.value === e.value) continue;
    if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(e.value)) fail("The text has control characters.");
    setIn(expected, e.path, e.value);
    nodes.push({ node, value: e.value });
  }
  if (nodes.length === 0) return src;
  for (const safe of [false, true]) {
    const reps = nodes.map(({ node, value }) => ({ start: node.range[0], end: node.range[1], text: serialize(src, node, value, safe) }))
      .sort((a, b) => b.start - a.start);
    let out = src;
    for (const r of reps) out = out.slice(0, r.start) + r.text + out.slice(r.end);
    const check = parseDocument(out);
    if (!check.errors.length && sameJSON(check.toJS(), expected)) return out;
  }
  fail("The change could not be written safely. Nothing was saved.", 422);
}
