"""Report exports: an interactive HTML dashboard, PDF and Word, from a scanner result.

Input is the JSON written by sfe.scanner.to_json, plus optional extra sections (for example a document review):

  sections = [{"title": str, "intro": str, "items": [{"status": "ok|gap|review|info", "title": str,
               "detail": str, "rule": str (optional), "evidence": str (optional)}]}]

HTML needs nothing. PDF needs Chrome or Chromium (set CHROME=/path) or WeasyPrint. Word needs python-docx.
Licence: Apache-2.0
"""
from __future__ import annotations

import html
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import Config

SEVS = ["BLOCK", "REVIEW", "WARN", "HUMAN", "WAIVED"]
SEV_TEXT = {"BLOCK": "Fix before launch", "REVIEW": "Needs a decision", "WARN": "Recommended fix",
            "HUMAN": "A person must check", "WAIVED": "Waived with a reason"}
SEV_COLOUR = {"BLOCK": "#b42318", "REVIEW": "#b54708", "WARN": "#8a6d00", "HUMAN": "#365a7a", "WAIVED": "#5f6b73"}
STATUS_TEXT = {"ok": "Found", "gap": "Missing", "review": "Check", "info": "Note"}
STATUS_COLOUR = {"ok": "#127a3f", "gap": "#b42318", "review": "#b54708", "info": "#365a7a"}


def build_model(cfg: Config, result: dict, rules_by_id: dict, sources: dict, sections: list | None = None) -> dict:
    groups = []
    for sev in SEVS:
        by_rule = {}
        for f in result.get("findings", []):
            if f["severity"] != sev:
                continue
            g = by_rule.setdefault(f["rule"], {"rule": f["rule"], "title": f["title"], "strength": f["strength"],
                                                "tier": f["tier"], "improvement": f["improvement"], "sources": f["sources"],
                                                "profiles": rules_by_id.get(f["rule"], {}).get("profiles", []),
                                                "why": str(rules_by_id.get(f["rule"], {}).get("rationale", "")).strip(),
                                                "items": []})
            g["items"].append({"where": f.get("where", ""), "detail": f.get("detail", ""), "waived": f.get("waived", "")})
        if by_rule:
            groups.append({"severity": sev, "rules": sorted(by_rule.values(), key=lambda g: g["rule"])})
    used = sorted({s for g in groups for r in g["rules"] for s in r["sources"]})
    return {"framework": cfg.short, "name": cfg.name, "site": cfg.site, "product": result.get("product") or "",
            "date": result.get("date", ""), "level": result.get("level", 1), "level_name": cfg.levels.get(result.get("level", 1), ""),
            "levels": cfg.levels, "verdict": result.get("verdict", ""), "counts": result.get("counts", {}),
            "in_scope": len(result.get("rules_in_scope", [])), "description_only": result.get("description_only", False),
            "groups": groups, "sections": sections or [], "packs": result.get("packs", []), "parameters": result.get("parameters", {}),
            "sources": [{"id": s, "title": sources.get(s, {}).get("title", s), "url": sources.get(s, {}).get("url", ""),
                         "status": sources.get(s, {}).get("status", "")} for s in used]}


# --------------------------------------------------------------------------- HTML
CSS = """:root{--ink:#14232c;--muted:#51626c;--line:#d9e1e5;--paper:#f7f9fa;--card:#fff;--accent:ACCENT}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{background:var(--card);border-bottom:4px solid var(--accent);padding:22px 28px}header h1{margin:0 0 4px;font-size:1.55rem}
.meta{color:var(--muted);font-size:.9rem}.wrap{max-width:1100px;margin:0 auto;padding:20px 28px 60px}
.verdict{font-weight:700;font-size:1.05rem;margin:14px 0 0}
.counts{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:18px 0}
.count{background:var(--card);border:1px solid var(--line);border-top:4px solid var(--c);border-radius:8px;padding:10px 12px}
.count b{display:block;font-size:1.6rem;line-height:1.1}.count span{font-size:.82rem;color:var(--muted)}
.bar{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:8px 0 18px}
.bar label{font-size:.9rem}.bar input[type=search]{flex:1;min-width:180px;padding:6px 9px;border:1px solid var(--line);border-radius:6px;font:inherit}
.bar button{font:inherit;padding:6px 12px;border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer}
h2{margin:30px 0 10px;font-size:1.2rem}.rule{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--c);border-radius:8px;padding:12px 16px;margin:10px 0}
.rule h3{margin:0 0 4px;font-size:1rem}.tag{display:inline-block;font-size:.75rem;font-weight:700;color:#fff;background:var(--c);border-radius:4px;padding:1px 7px;margin-right:6px}
.rule p{margin:6px 0}.rule ul{margin:6px 0 2px;padding-left:20px}.rule code{background:#eef2f4;padding:0 4px;border-radius:3px;font-size:.88em}
details summary{cursor:pointer;color:var(--muted);font-size:.88rem}.src a{color:var(--ink)}
.item{display:flex;gap:10px;align-items:flex-start;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:8px 0}
.st{flex:0 0 auto;font-size:.75rem;font-weight:700;color:#fff;border-radius:4px;padding:2px 8px;margin-top:2px}
.note{background:#fff8ec;border:1px solid #f0d9b5;border-radius:8px;padding:10px 14px;font-size:.9rem;margin-top:30px}
.hidden{display:none}footer{color:var(--muted);font-size:.85rem;margin-top:30px}
@media print{.bar,button{display:none}body{background:#fff}.rule,.item,.count{break-inside:avoid}details{display:block}details>summary{display:none}}
@media (max-width:700px){.counts{grid-template-columns:repeat(2,1fr)}}
"""

JS = """const q=document.getElementById('q'),boxes=[...document.querySelectorAll('[data-sevf]')],lv=document.getElementById('lv');
function apply(){const on=new Set(boxes.filter(b=>b.checked).map(b=>b.value)),t=(q.value||'').toLowerCase(),L=+lv.value;
document.querySelectorAll('.rule').forEach(r=>{const ok=on.has(r.dataset.sev)&&(+r.dataset.tier<=L)&&(!t||r.textContent.toLowerCase().includes(t));r.classList.toggle('hidden',!ok)});
document.querySelectorAll('section[data-sev]').forEach(s=>s.classList.toggle('hidden',!s.querySelector('.rule:not(.hidden)')));}
[q,lv,...boxes].forEach(e=>e.addEventListener('input',apply));document.getElementById('pr').addEventListener('click',()=>window.print());"""


def _e(s):
    return html.escape(str(s or ""))


def render_html(model: dict, accent: str = "#0f6e6e", for_print: bool = False) -> str:
    c = model["counts"]
    cards = "".join(f'<div class="count" style="--c:{SEV_COLOUR[s]}"><b>{c.get(s, 0)}</b><span>{s}: {SEV_TEXT[s]}</span></div>' for s in SEVS)
    bar = ""
    if not for_print:
        sevs = "".join(f'<label><input type="checkbox" data-sevf value="{s}" checked> {s}</label>' for s in SEVS)
        lvls = "".join(f'<option value="{k}"{" selected" if k == model["level"] else ""}>Up to level {k}: {_e(v)}</option>' for k, v in model["levels"].items())
        bar = (f'<div class="bar" role="search"><input id="q" type="search" placeholder="Search rules, files, words" aria-label="Search">'
               f'{sevs}<select id="lv" aria-label="Level">{lvls}</select><button id="pr" type="button">Print or save as PDF</button></div>')
    srcs = {s["id"]: s for s in model["sources"]}
    body = []
    for g in model["groups"]:
        sev = g["severity"]
        rs = []
        for r in g["rules"]:
            items = "".join(f'<li>{"<code>" + _e(i["where"]) + "</code> " if i["where"] else ""}{_e(i["detail"])}'
                            f'{" <em>(" + _e(i["waived"]) + ")</em>" if i["waived"] else ""}</li>' for i in r["items"])
            links = ", ".join(f'<a href="{_e(srcs[s]["url"])}">{_e(s)}</a>' if srcs.get(s, {}).get("url") else _e(s) for s in r["sources"])
            why = f'<details><summary>Why this rule</summary><p>{_e(r["why"])}</p></details>' if r["why"] else ""
            rs.append(f'<article class="rule" style="--c:{SEV_COLOUR[sev]}" data-sev="{sev}" data-tier="{r["tier"]}">'
                      f'<h3><span class="tag">{sev}</span>{_e(r["rule"])}: {_e(r["title"])}</h3>'
                      f'<div class="meta">{_e(r["strength"])} · level {r["tier"]} ({_e(model["levels"].get(r["tier"], ""))}) · profiles {_e(", ".join(r["profiles"]))}</div>'
                      f'<p><b>How to improve.</b> {_e(r["improvement"])}</p>{why}<ul>{items}</ul>'
                      f'<p class="src meta">Sources: {links}</p></article>')
        body.append(f'<section data-sev="{sev}"><h2>{sev}: {SEV_TEXT[sev]}</h2>{"".join(rs)}</section>')
    for sec in model["sections"]:
        its = "".join(f'<div class="item"><span class="st" style="background:{STATUS_COLOUR.get(i.get("status"), "#365a7a")}">'
                      f'{_e(STATUS_TEXT.get(i.get("status"), i.get("status")))}</span><div><b>{_e(i.get("title"))}</b>'
                      f'{" <span class=meta>(" + _e(i["rule"]) + ")</span>" if i.get("rule") else ""}'
                      f'<div>{_e(i.get("detail"))}</div>{"<div class=meta>" + _e(i["evidence"]) + "</div>" if i.get("evidence") else ""}</div></div>'
                      for i in sec.get("items", []))
        body.append(f'<section class="extra"><h2>{_e(sec["title"])}</h2><p class="meta">{_e(sec.get("intro", ""))}</p>{its}</section>')
    src_list = "".join(f'<li><b>{_e(s["id"])}</b>: {_e(s["title"])}{" (" + _e(s["status"][:160]) + ")" if s["status"] else ""}'
                       f'{" <a href=" + chr(34) + _e(s["url"]) + chr(34) + ">link</a>" if s["url"] else ""}</li>' for s in model["sources"])
    mode = " · description only (code not read)" if model["description_only"] else ""
    packs = ""
    if model.get("packs"):
        packs = "<div class=\"meta\">Packs: " + ", ".join(_e(f"{p['title']} v{p['version']}") for p in model["packs"]) + "</div>"
    if model.get("parameters"):
        packs += "<div class=\"meta\">" + " · ".join(f"{_e(k)}: {_e(v)}" for k, v in model["parameters"].items()) + "</div>"
    return ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{_e(model['framework'])} report{': ' + _e(model['product']) if model['product'] else ''}</title>"
            f"<style>{CSS.replace('ACCENT', accent)}</style></head><body>"
            f"<header><h1>{_e(model['framework'])} report{': ' + _e(model['product']) if model['product'] else ''}</h1>"
            f"<div class=\"meta\">{_e(model['name'])} · level {model['level']} ({_e(model['level_name'])}) · {model['in_scope']} rules in scope · {_e(model['date'])}{mode}</div>"
            f"{packs}<p class=\"verdict\">{_e(model['verdict'])}</p></header><main class=\"wrap\"><div class=\"counts\">{cards}</div>{bar}"
            f"{''.join(body)}<h2>Sources cited</h2><ul class=\"src\">{src_list}</ul>"
            "<p class=\"note\">Automated checks find signs. A person confirms them. A clean report does not mean the product is compliant. "
            "This report is not legal or regulatory advice.</p>"
            f"<footer>Generated with {_e(model['name'])} ({_e(model['framework'])}). {_e(model['site'])}</footer></main>"
            + ("" if for_print else f"<script>{JS}</script>") + "</body></html>\n")


# --------------------------------------------------------------------------- PDF
def find_chrome():
    env = os.environ.get("CHROME")
    if env and Path(env).exists():
        return env
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        p = shutil.which(n)
        if p:
            return p
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if Path(p).exists():
            return p
    return None


def render_pdf(html_text: str, pdf_path: Path) -> str:
    chrome = find_chrome()
    if chrome:
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "report.html"
            src.write_text(html_text, encoding="utf-8")
            subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={pdf_path}", src.as_uri()], check=True, capture_output=True, timeout=120)
        return "chrome"
    try:
        import weasyprint  # type: ignore
        weasyprint.HTML(string=html_text).write_pdf(str(pdf_path))
        return "weasyprint"
    except ImportError:
        raise RuntimeError("PDF export needs Chrome or Chromium (set CHROME=/path) or `pip install weasyprint`.")


# --------------------------------------------------------------------------- Word
def render_docx(model: dict, path: Path, accent: str = "#0f6e6e") -> None:
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
    except ImportError:
        raise RuntimeError("Word export needs python-docx: pip install python-docx")
    rgb = lambda h: RGBColor.from_string(h.lstrip("#").upper())  # noqa: E731
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(11)
    doc.add_heading(f"{model['framework']} report{': ' + model['product'] if model['product'] else ''}", 0)
    doc.add_paragraph(f"{model['name']} · level {model['level']} ({model['level_name']}) · {model['in_scope']} rules in scope · {model['date']}"
                      + (" · description only" if model["description_only"] else ""))
    if model.get("packs"):
        doc.add_paragraph("Packs: " + ", ".join(f"{p['title']} v{p['version']}" for p in model["packs"]))
    if model.get("parameters"):
        doc.add_paragraph(" · ".join(f"{k}: {v}" for k, v in model["parameters"].items()))
    p = doc.add_paragraph()
    p.add_run(model["verdict"]).bold = True
    t = doc.add_table(rows=2, cols=len(SEVS))
    t.style = "Table Grid"
    for i, s in enumerate(SEVS):
        t.cell(0, i).text = s
        t.cell(1, i).text = str(model["counts"].get(s, 0))
        for run in t.cell(0, i).paragraphs[0].runs:
            run.bold = True
            run.font.color.rgb = rgb(SEV_COLOUR[s])
    srcs = {s["id"]: s for s in model["sources"]}
    for g in model["groups"]:
        doc.add_heading(f"{g['severity']}: {SEV_TEXT[g['severity']]}", 1)
        for r in g["rules"]:
            h = doc.add_heading(f"{r['rule']}: {r['title']}", 2)
            for run in h.runs:
                run.font.color.rgb = rgb(SEV_COLOUR[g["severity"]])
            doc.add_paragraph(f"{r['strength']} · level {r['tier']} · profiles {', '.join(r['profiles'])}").runs[0].italic = True
            q = doc.add_paragraph()
            q.add_run("How to improve. ").bold = True
            q.add_run(r["improvement"])
            if r["why"]:
                q = doc.add_paragraph()
                q.add_run("Why. ").bold = True
                q.add_run(r["why"])
            for i in r["items"]:
                doc.add_paragraph((f"{i['where']}: " if i["where"] else "") + i["detail"] + (f" ({i['waived']})" if i["waived"] else ""),
                                  style="List Bullet")
            doc.add_paragraph("Sources: " + ", ".join(f"{s} ({srcs[s]['url']})" if srcs.get(s, {}).get("url") else s for s in r["sources"]))
    for sec in model["sections"]:
        doc.add_heading(sec["title"], 1)
        if sec.get("intro"):
            doc.add_paragraph(sec["intro"])
        for i in sec.get("items", []):
            q = doc.add_paragraph(style="List Bullet")
            r1 = q.add_run(f"{STATUS_TEXT.get(i.get('status'), i.get('status'))}: ")
            r1.bold = True
            r1.font.color.rgb = rgb(STATUS_COLOUR.get(i.get("status"), "#365a7a"))
            q.add_run(f"{i.get('title', '')}" + (f" ({i['rule']})" if i.get("rule") else "") + f". {i.get('detail', '')}")
            if i.get("evidence"):
                q.add_run(f" {i['evidence']}").italic = True
    doc.add_heading("Sources cited", 1)
    for s in model["sources"]:
        doc.add_paragraph(f"{s['id']}: {s['title']}" + (f" {s['url']}" if s["url"] else ""), style="List Bullet")
    doc.add_paragraph("Automated checks find signs. A person confirms them. A clean report does not mean the product is compliant. "
                      "This report is not legal or regulatory advice.").runs[0].italic = True
    doc.save(str(path))


def export(cfg: Config, result: dict, rules_by_id: dict, sources: dict, formats, out_dir: Path,
           sections: list | None = None, accent: str = "#0f6e6e", stem: str = "report") -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = build_model(cfg, result, rules_by_id, sources, sections)
    written = {}
    if "html" in formats:
        p = out_dir / f"{stem}.html"
        p.write_text(render_html(model, accent), encoding="utf-8")
        written["html"] = p
    if "pdf" in formats:
        p = out_dir / f"{stem}.pdf"
        render_pdf(render_html(model, accent, for_print=True), p)
        written["pdf"] = p
    if "docx" in formats:
        p = out_dir / f"{stem}.docx"
        render_docx(model, p, accent)
        written["docx"] = p
    if "json" in formats:
        p = out_dir / f"{stem}-model.json"
        p.write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
        written["json"] = p
    return written
