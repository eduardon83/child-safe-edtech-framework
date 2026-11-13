"""CSEF brand for every HTML output: colours, fonts, logo, favicon.

The logo SVGs in brand/svg are turned into one inline SVG whose colours follow CSS variables, so the same
markup works in light mode, dark mode and print without extra files. Outputs stay self-contained: fonts come
from Google Fonts when online and fall back to system fonts offline.
"""
from __future__ import annotations

import base64
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
TAGLINE = "Build safe things for kids. Together."

# Colours from brand/tokens/csef-colors.css. Text versions are darkened where a brand colour is used as
# small text on Paper, to keep WCAG AA contrast.
LIGHT = {
    "paper": "#F6F3EC", "ink": "#17233F", "ink2": "#4A5468", "panel": "#FFFFFF", "line": "#E2DDD1", "code": "#EEEAE0",
    "teal": "#1F8A7A", "indigo": "#4A5FC1", "sky": "#5DA9DD", "lilac": "#9A7AD0", "coral": "#E2674A", "sun": "#F2B441",
    "teal-t": "#16695D", "indigo-t": "#3B4DA6", "lilac-t": "#6F51A8", "sky-t": "#2B6F9E", "coral-t": "#B3452B", "sun-t": "#8A5C00",
    "teal-bg": "#E0F0EC", "indigo-bg": "#E6E9F8", "lilac-bg": "#EFE8F8", "sky-bg": "#E3F0F9", "coral-bg": "#FBE7E1", "sun-bg": "#FDF1D8",
}
DARK = {
    "paper": "#17233F", "ink": "#F6F3EC", "ink2": "#B8C0D0", "panel": "#1F2C4C", "line": "#33405F", "code": "#26345A",
    "teal": "#3FBFA8", "indigo": "#8A9BEA", "sky": "#5DA9DD", "lilac": "#B59BE6", "coral": "#E2674A", "sun": "#F2B441",
    "teal-t": "#5FD3BD", "indigo-t": "#A9B6F2", "lilac-t": "#CBB5F0", "sky-t": "#8CC6EC", "coral-t": "#F2967F", "sun-t": "#F6C969",
    "teal-bg": "#173E43", "indigo-bg": "#262F5E", "lilac-bg": "#33295A", "sky-bg": "#1C3A5A", "coral-bg": "#45263A", "sun-bg": "#413A30",
}
LOGO_LIGHT = {"#17233F": "ink", "#4A5468": "ink2", "#1F8A7A": "teal", "#4A5FC1": "indigo", "#9A7AD0": "lilac"}

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;700'
         '&display=swap" rel="stylesheet">')
FONT_BODY = '"Inter",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif'
FONT_DISPLAY = '"Space Grotesk","Inter",system-ui,-apple-system,"Segoe UI",sans-serif'


def _vars(d: dict) -> str:
    return ";".join(f"--c-{k}:{v}" for k, v in d.items())


def tokens_css() -> str:
    """--c-* variables for light and dark mode, honouring data-theme overrides."""
    return (f":root{{{_vars(LIGHT)};--font:{FONT_BODY};--font-display:{FONT_DISPLAY}}}"
            f"@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{{_vars(DARK)}}}}}"
            f":root[data-theme=dark]{{{_vars(DARK)}}}"
            "@media print{:root,:root[data-theme=dark]{" + _vars(LIGHT) + "}}")


BASE_CSS = """
h1,h2,h3,.display{font-family:var(--font-display);letter-spacing:-.01em}
.csef-stripe{height:6px;background:linear-gradient(90deg,var(--c-teal) 0 25%,var(--c-indigo) 25% 50%,var(--c-sky) 50% 75%,var(--c-lilac) 75%)}
.csef-brand{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 18px}
.csef-brand svg{display:block;height:var(--logo-h,40px);width:auto;max-width:100%}
.csef-brand .tag{font-family:var(--font-display);font-weight:500;color:var(--c-ink2);font-size:.95rem}
@media print{body{background:#fff!important}.csef-stripe{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


@lru_cache(maxsize=None)
def _svg(name: str) -> str:
    p = BRAND / "svg" / f"{name}.svg"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _themable(svg: str) -> str:
    """Replace the light-mode colours with CSS variables (fallback: the original colour)."""
    def tag(m):
        t = m.group(0)
        styles = []
        for attr in ("fill", "stroke"):
            mm = re.search(rf'\s{attr}="(#[0-9A-Fa-f]{{6}})"', t)
            if mm and mm.group(1).upper() in LOGO_LIGHT:
                styles.append(f"{attr}:var(--c-{LOGO_LIGHT[mm.group(1).upper()]},{mm.group(1)})")
                t = t.replace(mm.group(0), "")
        if styles:
            t = t[:-1].rstrip("/").rstrip() + f' style="{";".join(styles)}"' + ("/>" if t.endswith("/>") else ">")
        return t
    svg = re.sub(r"<(?:path|rect|circle|g)\b[^>]*>", tag, svg)
    return re.sub(r'\s(width|height)="[^"]*"', "", svg, count=2)


def logo(kind: str = "lockup", height: int = 40, tagline: bool = False) -> str:
    """Inline logo that follows light/dark mode. kind: lockup, lockup-compact, mark, mark-small."""
    svg = _svg(f"csef-{kind}-on-light")
    if not svg:
        return '<div class="csef-brand"><strong class="display">CSEF</strong></div>'
    tag = f'<span class="tag">{TAGLINE}</span>' if tagline else ""
    return f'<div class="csef-brand" style="--logo-h:{height}px">{_themable(svg)}{tag}</div>'


@lru_cache(maxsize=None)
def favicon_data_uri() -> str:
    p = BRAND / "web" / "favicon.svg"
    if not p.exists():
        return ""
    return "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()


def head(favicon: str | None = None) -> str:
    """Fonts and favicon for <head>. favicon=None embeds it (self-contained files)."""
    fav = favicon or favicon_data_uri()
    return FONTS + (f'<link rel="icon" href="{fav}" type="image/svg+xml">' if fav else "")


def png(name: str) -> Path | None:
    p = BRAND / "png" / f"{name}.png"
    return p if p.exists() else None


def style_docx(doc) -> None:
    """Brand colours for Word headings."""
    from docx.shared import RGBColor
    for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        try:
            doc.styles[name].font.color.rgb = RGBColor(0x17, 0x23, 0x3F)
        except KeyError:
            pass
