"""Render a CSEF guide (Markdown) as a page of the website, in the CSEF brand.

A small, dependency-free renderer for the Markdown the guides use: headings, paragraphs, ordered and bullet lists
(with indented continuation lines), pipe tables, fenced code, standalone images, inline code, bold, italics and
links. Relative links to repository files become GitHub links; images can be mapped to copies next to the page.
Deterministic, so build.py --check can compare the output.

Licence: Apache-2.0
"""
from __future__ import annotations

import html
import re

import brand

REPO = "https://github.com/eduardon83/child-safe-edtech-framework/blob/main/"
TREE = "https://github.com/eduardon83/child-safe-edtech-framework/tree/main/"


import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "engine"))
from sfe import markdown as _md  # noqa: E402

_REPO = REPO.rsplit("/blob/", 1)[0]
slug = _md.slug


def inline(t: str, base_dir: str, links: dict) -> str:
    return _md.inline(t, base_dir, links, _REPO, "csef.kendirstudios.pt")


def render(md: str, base_dir: str = "framework", links: dict | None = None, images: dict | None = None) -> tuple[str, str, list]:
    """Returns (title, body html, [(id, h2 text)])."""
    return _md.render(md, base_dir, links, images, _REPO, "csef.kendirstudios.pt")


CSS = """*{box-sizing:border-box}body{margin:0;background:var(--c-paper);color:var(--c-ink);font:17px/1.65 var(--font)}
a{color:var(--c-indigo-t)}a:focus-visible{outline:3px solid var(--c-indigo);outline-offset:2px}
.in{max-width:1180px;margin:0 auto;padding:0 24px}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px 24px;flex-wrap:wrap;padding-top:16px;padding-bottom:16px}
.top .csef-brand{margin:0}.top nav{display:flex;gap:4px 20px;flex-wrap:wrap}.top nav a{color:var(--c-ink);text-decoration:none;font-weight:500;padding:10px 0}
.layout{display:grid;grid-template-columns:240px minmax(0,1fr);gap:48px;padding-top:24px;padding-bottom:72px}
.toc{position:sticky;top:16px;align-self:start;font-size:.93rem}.toc p{margin:0 0 8px;font-weight:600;color:var(--c-ink2)}
.toc ol{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:2px}.toc a{display:block;padding:6px 10px;border-radius:8px;color:var(--c-ink);text-decoration:none}
.toc a:hover{background:var(--c-panel)}
article{max-width:820px}article h1{font-size:clamp(2rem,4.4vw,3rem);line-height:1.08;margin:0 0 18px}
article h2{font-size:1.7rem;line-height:1.2;margin:48px 0 12px;scroll-margin-top:12px}article h3{font-size:1.25rem;margin:30px 0 8px}
article p,article li{max-width:72ch}article li{margin:0 0 6px}
.tbl{overflow-x:auto;margin:14px 0 22px}table{border-collapse:collapse;width:100%;background:var(--c-panel);border:1px solid var(--c-line);font-size:.92rem}
th,td{text-align:left;vertical-align:top;padding:9px 12px;border-bottom:1px solid var(--c-line)}th{color:var(--c-ink2);font-weight:600}
code{font:.88em ui-monospace,"SF Mono",Menlo,monospace;background:var(--c-code);padding:1px 5px;border-radius:5px}
pre{margin:14px 0 22px;padding:18px 20px;border-radius:14px;background:#17233F;color:#F6F3EC;font:13.5px/1.65 ui-monospace,"SF Mono",Menlo,monospace;overflow-x:auto}
pre code{background:none;padding:0;color:inherit}
figure{margin:18px 0 24px}figure img{display:block;width:100%;height:auto;border-radius:14px;border:1px solid var(--c-line)}
.meta{display:flex;flex-wrap:wrap;gap:8px 16px;margin:0 0 28px;color:var(--c-ink2);font-size:.92rem}
.pill{display:inline-block;padding:4px 12px;border-radius:999px;background:var(--c-indigo-bg);color:var(--c-indigo-t);font-weight:600;font-size:.82rem}
footer{border-top:1px solid var(--c-line);background:var(--c-panel);padding:28px 0;color:var(--c-ink2);font-size:.92rem}
@media (max-width:900px){.layout{grid-template-columns:1fr}.toc{position:static}}
@media print{.toc,.top nav,footer{display:none}.layout{display:block}}"""


def page(md: str, *, version: str, source_path: str, home: str = "../", description: str = "", links: dict | None = None,
         images: dict | None = None) -> str:
    title, body, toc = render(md, source_path.rsplit("/", 1)[0], links, images)
    e = html.escape
    toc_html = "".join(f'<li><a href="#{hid}">{e(t)}</a></li>' for hid, t in toc)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{e(title)} · CSEF</title><meta name=\"description\" content=\"{e(description)}\">"
            f'{brand.head(home + "favicon.svg")}<style>{brand.tokens_css()}{brand.BASE_CSS}{CSS}</style></head>'
            f'<body><div class="csef-stripe"></div><header class="in top"><a href="{home}" aria-label="CSEF home" style="text-decoration:none">'
            f'{brand.logo("lockup", 40)}</a><nav aria-label="Main"><a href="{home}workbench/">Workbench</a><a href="{home}examples/">Examples</a>'
            f'<a href="{home}#rules">Guides</a><a href="https://github.com/eduardon83/child-safe-edtech-framework">GitHub</a></nav></header>'
            f'<div class="in layout"><nav class="toc" aria-label="On this page"><p>On this page</p><ol>{toc_html}</ol></nav>'
            f'<article><p class="meta"><span class="pill">CSEF v{e(version)} guide</span>'
            f'<a href="{REPO}{e(source_path)}">Source on GitHub</a><span>CC BY 4.0</span></p>{body}</article></div>'
            f'<footer><div class="in">Child-Safe EdTech Framework (CSEF) v{e(version)}, maintained by Kendir Studios with the EdTech community. '
            f"Pre-compliance guidance, not legal advice. Framework content CC BY 4.0 · code Apache 2.0.</div></footer></body></html>\n")
