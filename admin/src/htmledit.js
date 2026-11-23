// Edit information text in an HTML page template.
// Editable: paragraphs, headings, list items, table cells, captions and notes.
// Not editable: buttons, form labels, options, summaries, scripts, styles and anything with a button role.
const TEXT_TAGS = "p|h1|h2|h3|h4|h5|h6|li|dt|dd|figcaption|blockquote|td|th|caption";
const SEGMENT = new RegExp(`<(${TEXT_TAGS})(\\s[^>]*)?>([\\s\\S]*?)</\\1\\s*>`, "gi");
const MASKED = ["script", "style", "button", "label", "select", "option", "summary", "template", "svg", "textarea", "noscript"];
const NESTED_BLOCK = /<\/?(p|div|ul|ol|li|dl|dt|dd|section|article|aside|table|thead|tbody|tr|td|th|h[1-6]|form|fieldset|button|input|select|textarea|label|script|style|svg|nav|header|footer|main|details|summary|figure|blockquote|iframe|img|video|audio|canvas|object)\b/i;
const BUTTONISH = /\b(btn|button|cta|tab|chip|toggle)\b|role\s*=\s*["']?(button|tab|menuitem)/i;
const INLINE_OK = new Set(["a", "code", "strong", "em", "b", "i", "br", "abbr", "kbd", "span", "sup", "sub", "small", "mark", "q", "cite", "time", "var", "wbr"]);

function fail(message, status = 400) {
  const e = new Error(message);
  e.status = status;
  throw e;
}

function mask(src) {
  let out = src.replace(/<!--[\s\S]*?-->/g, (m) => " ".repeat(m.length));
  for (const tag of MASKED) {
    const re = new RegExp(`<${tag}\\b[\\s\\S]*?</${tag}\\s*>`, "gi");
    out = out.replace(re, (m) => " ".repeat(m.length));
  }
  return out;
}

function plain(html) {
  return html.replace(/<[^>]*>/g, "").replace(/\{[a-z_0-9]+\}/gi, "").replace(/&[a-z#0-9]+;/gi, " ").trim();
}

// [{index, tag, start, end, html}] where start and end are the positions of the inner HTML.
export function segments(src) {
  const masked = mask(src);
  const out = [];
  SEGMENT.lastIndex = 0;
  let m;
  while ((m = SEGMENT.exec(masked))) {
    const openLen = m[0].indexOf(">") + 1;
    const start = m.index + openLen;
    const end = start + m[3].length;
    const inner = src.slice(start, end);
    if (NESTED_BLOCK.test(inner)) {
      SEGMENT.lastIndex = m.index + openLen;
      continue;
    }
    if (BUTTONISH.test(m[2] || "") || !/[A-Za-zÀ-ÿ]{2}/.test(plain(inner))) continue;
    // A block made only of links is navigation, which works like a set of buttons.
    if (!/[A-Za-zÀ-ÿ]{2}/.test(plain(inner.replace(/<a\b[\s\S]*?<\/a\s*>/gi, "")))) continue;
    // Short list items, terms and table headers are labels, like the text on a button.
    if (/^(li|dt|th)$/i.test(m[1]) && plain(inner).split(/\s+/).length <= 2) continue;
    out.push({ index: out.length, tag: m[1].toLowerCase(), start, end, html: inner });
  }
  return out;
}

function placeholders(html) {
  return (html.match(/\{[a-z_0-9]+\}/gi) || []).sort().join(" ");
}

export function checkInline(html, old) {
  if (/<\s*\/?\s*(script|style|iframe|object|embed|form|input|button|img|svg)\b/i.test(html)) fail("Only text and simple inline tags (links, bold, italics, code) are allowed.");
  if (/\son[a-z]+\s*=/i.test(html) || /javascript\s*:/i.test(html) || /\sstyle\s*=/i.test(html)) fail("Scripts and inline styles are not allowed.");
  const stack = [];
  for (const t of html.matchAll(/<(\/?)([a-z0-9]+)\b[^>]*?(\/?)>/gi)) {
    const name = t[2].toLowerCase();
    if (!INLINE_OK.has(name)) fail(`The tag <${name}> is not allowed here.`);
    if (name === "br" || name === "wbr" || t[3]) continue;
    if (t[1]) {
      if (stack.pop() !== name) fail(`The tag </${name}> does not match an opening tag.`);
    } else stack.push(name);
  }
  if (stack.length) fail(`The tag <${stack[stack.length - 1]}> is not closed.`);
  if (/<|>/.test(html.replace(/<\/?[a-z0-9]+\b[^<>]*>/gi, ""))) fail("Write < and > as &lt; and &gt;.");
  if (placeholders(html) !== placeholders(old)) fail("Keep the {placeholders} exactly as they were. The build fills them in.");
}

// edits: [{index, old, html}]. "old" must match the current text, so a stale page cannot overwrite newer text.
export function applySegmentEdits(src, edits) {
  if (!Array.isArray(edits) || edits.length === 0) fail("Nothing to save.");
  const segs = segments(src);
  const reps = [];
  for (const e of edits) {
    const s = segs[e.index];
    if (!s || typeof e.html !== "string") fail("Bad edit.");
    if (s.html !== e.old) fail("This text changed since you opened it. Reload and try again.", 409);
    const html = e.html.replace(/\r\n?/g, "\n");
    if (html === s.html) continue;
    if (!plain(html)) fail("A text block cannot be empty.");
    checkInline(html, s.html);
    reps.push({ start: s.start, end: s.end, html });
  }
  reps.sort((a, b) => b.start - a.start);
  let out = src;
  for (const r of reps) out = out.slice(0, r.start) + r.html + out.slice(r.end);
  if (segments(out).length !== segs.length) fail("The change would alter the page structure. Nothing was saved.", 422);
  return out;
}
