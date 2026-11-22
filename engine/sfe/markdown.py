"""A small, dependency-free Markdown renderer for framework guides.

Headings, paragraphs, ordered and bullet lists (with indented continuation lines), pipe tables, fenced code,
standalone images, blockquotes, inline code, bold, italics and links. Relative links to repository files become
links to the framework's repository. Deterministic, so generated pages can be checked in CI.
Lifted from CSEF tooling/mdpage.py.
"""
from __future__ import annotations

import html
import re


def slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", t).lower()).strip("-")


def _resolve(href: str, base_dir: str, links: dict, repo: str) -> str:
    if re.match(r"^(https?:|mailto:|#)", href):
        return href
    path, _, frag = href.partition("#")
    parts = []
    for p in (base_dir.rstrip("/") + "/" + path).split("/"):
        if p in ("", "."):
            continue
        if p == "..":
            if parts:
                parts.pop()
        else:
            parts.append(p)
    full = "/".join(parts)
    if full in links:
        return links[full] + (f"#{frag}" if frag else "")
    return (repo + "/tree/main/" if path.endswith("/") else repo + "/blob/main/") + full + ("/" if path.endswith("/") else "") + (f"#{frag}" if frag else "")


def inline(t: str, base_dir: str, links: dict, repo: str = "", host: str = "") -> str:
    codes = []

    def keep(m):
        codes.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    t = re.sub(r"`([^`]+)`", keep, t)
    t = html.escape(t, quote=False)

    def link(m):
        href = _resolve(html.unescape(m.group(2)), base_dir, links, repo)
        ext = href.startswith("http") and not (host and host in href)
        return f'<a href="{html.escape(href)}"' + (' rel="noopener"' if ext else "") + f">{m.group(1)}</a>"

    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", t)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], t)


def render(md: str, base_dir: str = "framework", links: dict | None = None, images: dict | None = None,
           repo: str = "", host: str = "") -> tuple[str, str, list]:
    """Returns (title, body html, [(id, h2 text)])."""
    links, images = links or {}, images or {}
    lines = md.splitlines()
    out, toc, title = [], [], ""
    i = 0
    il = lambda s: inline(s, base_dir, links, repo, host)  # noqa: E731
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("```"):
            lang = ln[3:].strip()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(f'<pre><code{f" class=language-{html.escape(lang)}" if lang else ""}>{html.escape(chr(10).join(buf))}</code></pre>')
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lvl, text = len(m.group(1)), m.group(2).strip()
            if lvl == 1 and not title:
                title = re.sub(r"[`*]", "", text)
                out.append(f"<h1>{il(text)}</h1>")
            else:
                hid = slug(text)
                if lvl == 2:
                    toc.append((hid, re.sub(r"[`*]", "", text)))
                out.append(f'<h{lvl} id="{hid}">{il(text)}</h{lvl}>')
            i += 1
            continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", ln)
        if m:
            src = images.get(m.group(2), _resolve(m.group(2), base_dir, links, repo))
            out.append(f'<figure><img src="{html.escape(src)}" alt="{html.escape(m.group(1))}"></figure>')
            i += 1
            continue
        if ln.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.match(r"^:?-+:?$", c) for c in r)]
            th = "".join(f"<th>{il(c)}</th>" for c in head) if any(head) else ""
            trs = "".join("<tr>" + "".join(f"<td>{il(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append('<div class="tbl"><table>' + (f"<thead><tr>{th}</tr></thead>" if th else "") + f"<tbody>{trs}</tbody></table></div>")
            continue
        m = re.match(r"^(\s*)(\d+\.|[-*])\s+(.*)$", ln)
        if m:
            ordered = m.group(2)[0].isdigit()
            items = []
            while i < len(lines):
                mm = re.match(r"^(\s*)(\d+\.|[-*])\s+(.*)$", lines[i])
                if mm and (mm.group(2)[0].isdigit()) == ordered and len(mm.group(1)) == len(m.group(1)):
                    items.append([mm.group(3)])
                    i += 1
                elif items and lines[i].startswith("   ") and lines[i].strip():
                    items[-1].append(lines[i].strip())
                    i += 1
                else:
                    break
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{il(' '.join(x))}</li>" for x in items) + f"</{tag}>")
            continue
        if ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append(f"<blockquote><p>{il(' '.join(buf))}</p></blockquote>")
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4}\s|```|\||!\[|\s*(\d+\.|[-*])\s|>)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{il(' '.join(buf))}</p>")
    return title, "\n".join(out), toc
