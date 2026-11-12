#!/usr/bin/env python3
"""CSEF code-of-conduct comparison.

Compares a code of conduct (an industry code, a company code, a draft code under the EU KIDS Act) with:
  1. the structural expectations for codes of conduct in the EU KIDS Act proposal (Art. 17, Art. 23, Recital 39);
  2. the CSEF rules in scope (profiles, age bands, level, packs).

For each rule it reports: covered, partial (topic mentioned, or only weak commitment), missing, or
possible conflict (the code permits something the rule forbids). This is a first pass based on wording;
every result needs a person (or the csef-review skill) to confirm meaning.

  python3 tooling/coc.py --input code.pdf [--name "Example Code"] [--level 1|2|3] [--profiles A,C]
                         [--bands B2,B3] [--pack file.yaml] [--out-dir csef-coc] [--formats md,html,json]

Input: .txt, .md, .html, .pdf (pdftotext or pypdf) or .docx (python-docx).

Licence: Apache-2.0
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as htmllib
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan  # noqa: E402

TOOL = "csef-coc"
STRONG = r"\b(must|shall|will|never|do not|does not|are not|is not|may not|cannot|can not|prohibit\w*|ban(s|ned)?|required?|commit\w*|ensure\w*|undertake\w*|guarantee\w*|not permitted|not allowed)\b"
WEAK = r"\b(should|encourag\w*|endeavou?r\w*|aim(s)? to|where possible|where appropriate|where feasible|strive\w*|consider\w*|recommend\w*|seek to|best efforts|as far as possible|voluntar\w*)\b"
PERMISSIVE = r"\b(may|can|could|is permitted|are permitted|permitted|allowed|acceptable|optional|at (their|its) discretion|provided that|as long as|subject to|is possible)\b"
NEGATION = r"\b(not|never|no|nor|prohibit\w*|ban(s|ned)?|avoid\w*|without|refrain\w*|cannot|must not|may not|shall not|exclude\w*|forbid\w*)\b"
STATUS_ORDER = ["conflict", "missing", "partial", "covered", "not_applicable"]
STATUS_LABEL = {"conflict": "Possible conflict", "missing": "Missing", "partial": "Partial", "covered": "Covered", "not_applicable": "Not expected in a code"}
STATUS_SEV = {"conflict": "BLOCK", "missing": "REVIEW", "partial": "WARN", "covered": "OK", "not_applicable": "NEXT"}


# --------------------------------------------------------------------------- text
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("’", "'").replace("‘", "'")
    s = re.sub(r"[-_/]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def read_input(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in (".txt", ".md", ".markdown"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if suf in (".html", ".htm"):
        t = path.read_text(encoding="utf-8", errors="ignore")
        t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
        t = re.sub(r"(?i)<br\s*/?>|</(p|li|h\d|div|tr)>", "\n", t)
        return htmllib.unescape(re.sub(r"<[^>]+>", " ", t))
    if suf == ".pdf":
        if shutil.which("pdftotext"):
            r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
            if r.returncode == 0:
                return r.stdout
        try:
            from pypdf import PdfReader  # type: ignore
            return "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
        except ImportError:
            raise RuntimeError("Reading PDF needs pdftotext (poppler) or `pip install pypdf`.")
    if suf == ".docx":
        try:
            from docx import Document  # type: ignore
        except ImportError:
            raise RuntimeError("Reading .docx needs `pip install python-docx`.")
        d = Document(str(path))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    raise RuntimeError(f"Unsupported input type: {suf} (use .txt, .md, .html, .pdf or .docx)")


def clauses(text: str):
    """Split into clauses: paragraphs and list items, keeping the nearest heading."""
    out, heading, buf = [], "", []

    def flush():
        if buf:
            t = " ".join(x.strip() for x in buf).strip()
            if len(t) > 15:
                out.append({"id": f"C{len(out) + 1}", "heading": heading, "text": t})
            buf.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if re.match(r"^(#{1,6}\s|article\s+\d+|section\s+\d+|part\s+[ivx\d]+|chapter\s+\d+)", line, re.I) or (
                len(line) < 80 and line.isupper() and len(line.split()) <= 10):
            flush()
            heading = line.lstrip("# ").strip()
            continue
        if re.match(r"^([-*•]|\(?[a-z0-9]{1,3}[.)])\s+", line, re.I):
            flush()
        buf.append(line)
    flush()
    return out


def term_rx(term: str):
    t = norm(str(term)).strip()
    end = r"(?![a-z0-9])" if len(t) <= 3 else ""
    return re.compile(r"(?<![a-z0-9])" + re.escape(t) + end)


def sentences(t: str):
    return [x for x in re.split(r"(?<=[.;:!?])\s+", t) if x.strip()]


# --------------------------------------------------------------------------- matching
GENERIC = {"not", "never", "no", "prohibit", "ban", "avoid", "disable", "hide", "limit", "warning", "option", "setting",
           "settings", "control", "review", "design", "support", "tool", "secure", "standard", "requirement", "guideline",
           "content", "data", "children", "minors", "learning", "default", "defaults", "rights", "request", "regular"}


def match_terms(groups, cls, need=None):
    """Best clause (or pair of adjacent clauses) by number of term groups matched.

    Groups made only of generic words (not, never, settings...) count only alongside a topic group,
    so a clause saying "will not use timers" does not match every 'no X' rule."""
    compiled = [[term_rx(t) for t in g] for g in groups]
    generic = [all(norm(str(t)).strip() in GENERIC for t in g) for g in groups]
    need = need or min(2, len(groups))
    best = None
    for i, c in enumerate(cls):
        window = c["n"] + (" " + cls[i + 1]["n"] if i + 1 < len(cls) else "")
        hits_c = [any(r.search(c["n"]) for r in g) for g in compiled]
        hits_w = [any(r.search(window) for r in g) for g in compiled]
        topical_c = any(h and not gen for h, gen in zip(hits_c, generic))
        topical_w = any(h and not gen for h, gen in zip(hits_w, generic))
        score_c = sum(hits_c) if topical_c else 0
        score_w = sum(hits_w) if topical_w else 0
        cand = (score_c, 1, [c]) if score_c >= score_w else (score_w, 0, [c] + ([cls[i + 1]] if i + 1 < len(cls) else []))
        if best is None or (cand[0], cand[1]) > (best[0], best[1]):
            best = cand
    if not best or best[0] == 0:
        return {"score": 0, "need": need, "groups": len(groups), "clauses": []}
    return {"score": best[0], "need": need, "groups": len(groups), "clauses": best[2]}


def strength(text_n: str) -> str:
    if re.search(STRONG, text_n):
        return "strong"
    if re.search(WEAK, text_n):
        return "weak"
    return "neutral"


def find_conflicts(topic, cls):
    out = []
    subj = [term_rx(t) for t in topic.get("conflict", []) or []]
    rxs = [re.compile(p, re.I) for p in topic.get("conflict_regex", []) or []]
    for c in cls:
        for s in sentences(c["n"]):
            hit = None
            for p in rxs:
                if p.search(s) and not re.search(r"\b(not|never|no)\b[^.]{0,20}" + p.pattern, s):
                    hit = s
                    break
            if not hit and subj and any(r.search(s) for r in subj) and re.search(PERMISSIVE, s) and not re.search(NEGATION, s):
                hit = s
            if hit:
                out.append({"clause": c["id"], "heading": c["heading"], "sentence": hit})
                break
    return out[:3]


def assess(groups, cls, need=None, topic=None):
    m = match_terms(groups, cls, need)
    conflicts = find_conflicts(topic or {}, cls)
    if conflicts:
        status = "conflict"
    elif m["score"] == 0:
        status = "missing"
    elif m["score"] >= m["need"] and strength(" ".join(c["n"] for c in m["clauses"])) == "strong":
        status = "covered"
    else:
        status = "partial"
    why = ""
    if status == "partial":
        if m["score"] < m["need"]:
            why = f"topic mentioned ({m['score']} of {m['need']} required aspects)"
        else:
            st = strength(" ".join(c["n"] for c in m["clauses"]))
            why = "only a weak commitment (should, encourage, where possible)" if st == "weak" else "no clear commitment (must, shall, will, never)"
    return {"status": status, "why": why, "score": m["score"], "need": m["need"],
            "clauses": [{"id": c["id"], "heading": c["heading"], "text": c["text"][:400]} for c in m["clauses"]],
            "conflicts": [{"clause": x["clause"], "heading": x["heading"], "sentence": x["sentence"][:300]} for x in conflicts]}


# --------------------------------------------------------------------------- run
def compare(text: str, std, topics: dict, level: int, profiles: set, bands: set, name: str) -> dict:
    cls = clauses(text)
    for c in cls:
        c["n"] = norm(c["text"])
    structure = []
    for s in topics.get("structure", []):
        res = assess(s["terms"], cls, s.get("need"))
        if res["status"] == "conflict":
            res["status"] = "partial"
        structure.append({"id": s["id"], "title": s["title"], "basis": s["basis"], **res})
    results = []
    for rid, r in sorted(std.rules.items()):
        if not scan.rule_in_scope(r, profiles, bands):
            continue
        topic = topics["rules"].get(rid)
        if topic is None:
            title_words = [w for w in re.findall(r"[a-z]{5,}", norm(r["title"])) if w not in {"every", "never", "their", "about", "children", "child"}]
            topic = {"terms": [[w] for w in title_words[:3]]} if title_words else {"skip": True}
        base = {"rule_id": rid, "title": r["title"], "level": r["level"], "tier": int(r["tier"]),
                "in_level": int(r["tier"]) <= level, "sources": r.get("sources", []), "improvement": r.get("improvement", ""),
                "requirement": " ".join(r["requirement"].split())}
        if topic.get("skip"):
            results.append({**base, "status": "not_applicable", "why": "engineering practice not usually set in a code of conduct",
                            "score": 0, "need": 0, "clauses": [], "conflicts": []})
            continue
        results.append({**base, **assess(topic["terms"], cls, topic.get("need"), topic)})
    counts = {k: sum(1 for x in results if x["status"] == k and x["in_level"]) for k in STATUS_ORDER}
    scounts = {k: sum(1 for x in structure if x["status"] == k) for k in ("covered", "partial", "missing")}
    used = sorted({sid for x in results if x["in_level"] and x["status"] != "not_applicable" for sid in x["sources"]})
    return {
        "format": 1, "tool": {"name": TOOL, "version": scan.TOOL_VERSION, "standard_version": std.version},
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "code": {"name": name, "clauses": len(cls), "words": len(text.split())},
        "scope": {"level": level, "profiles": sorted(profiles), "age_bands": sorted(bands), "packs": std.packs},
        "structure": structure, "structure_counts": scounts, "rules": results, "counts": counts,
        "sources": {sid: std.sources[sid] for sid in used if sid in std.sources},
        "clause_index": [{"id": c["id"], "heading": c["heading"], "text": c["text"]} for c in cls],
    }


# --------------------------------------------------------------------------- output
def render_md(res: dict) -> str:
    L = []
    a = L.append
    lv = res["scope"]["level"]
    a(f"# Code of conduct comparison: {res['code']['name']}")
    a("")
    a(f"Generated {res['generated'][:10]} by {TOOL} {res['tool']['version']} against the Child-Safe EdTech Framework v{res['tool']['standard_version']}, "
      f"Level {lv} ({scan.LEVEL_NAMES[lv]}), profiles core + {', '.join(res['scope']['profiles'])}, age bands {', '.join(res['scope']['age_bands'])}.")
    a("")
    a("> **First-pass comparison based on wording, not legal advice.** 'Covered' means the code uses the right terms with a clear "
      "commitment; it does not prove the commitment is adequate. 'Possible conflict' means a sentence appears to permit what a rule "
      "forbids. Confirm every result by reading the clauses cited. Under the EU KIDS Act proposal (Recital 39), adhering to a code does "
      "not in itself presume legal compliance.")
    a("")
    c = res["counts"]
    a("## Summary")
    a("")
    a(f"The code has {res['code']['clauses']} clauses ({res['code']['words']} words).")
    a("")
    a("| Result | Rules at this level |")
    a("|---|---|")
    for k in STATUS_ORDER:
        a(f"| {STATUS_LABEL[k]} | {c[k]} |")
    a("")
    a("## Structure of the code (EU KIDS Act Art. 17, Art. 23, Recital 39)")
    a("")
    a("| Criterion | Basis | Result | Where |")
    a("|---|---|---|---|")
    for s in res["structure"]:
        where = ", ".join(x["id"] for x in s["clauses"]) or "-"
        a(f"| {s['title']} | {s['basis']} | {STATUS_LABEL[s['status']]}{(' (' + s['why'] + ')') if s['why'] else ''} | {where} |")
    a("")
    groups = [("conflict", "Possible conflicts"), ("missing", "Missing from the code"), ("partial", "Partly covered"), ("covered", "Covered")]
    for k, title in groups:
        items = [x for x in res["rules"] if x["status"] == k and x["in_level"]]
        if not items:
            continue
        a(f"## {title} ({len(items)})")
        a("")
        for x in items:
            a(f"### {x['rule_id']}: {x['title']}")
            a("")
            a(f"*{x['level']}, Level {x['tier']} ({scan.LEVEL_NAMES[x['tier']]}).* {x['requirement']}")
            a("")
            for cf in x["conflicts"]:
                a(f"- **Possible conflict in {cf['clause']}**{(' (' + cf['heading'] + ')') if cf['heading'] else ''}: \"{cf['sentence']}\"")
            if x["why"]:
                a(f"- Assessment: {x['why']}.")
            for cl in x["clauses"][:2]:
                a(f"- Closest clause {cl['id']}{(' (' + cl['heading'] + ')') if cl['heading'] else ''}: \"{cl['text'][:240]}{'...' if len(cl['text']) > 240 else ''}\"")
            if k in ("conflict", "missing", "partial"):
                a(f"- Suggested addition to the code: {x['improvement']}")
            a(f"- Sources: {', '.join(x['sources'])}")
            a("")
    nxt = [x for x in res["rules"] if not x["in_level"] and x["status"] in ("missing", "partial", "conflict")]
    if nxt:
        a(f"## Above the chosen level ({len(nxt)})")
        a("")
        a("Rules of higher levels the code does not fully cover. Useful if the code aims higher.")
        a("")
        for x in nxt:
            a(f"- **{x['rule_id']}** {x['title']} (Level {x['tier']}): {STATUS_LABEL[x['status']].lower()}")
        a("")
    na = [x for x in res["rules"] if x["status"] == "not_applicable"]
    if na:
        a("## Not expected in a code of conduct")
        a("")
        a(", ".join(f"{x['rule_id']}" for x in na) + ". These are engineering practices checked in code by the scanner.")
        a("")
    a("## Sources")
    a("")
    for sid, s in res["sources"].items():
        a(f"- **[{sid}]** {s['title']}. {s.get('status', '')}. {s.get('url') or ''}")
    a("")
    return "\n".join(L)


def render_html(res: dict) -> str:
    import export  # reuse dashboard styles
    e = htmllib.escape
    sev = lambda k: f"--c:var(--{STATUS_SEV[k]});--cb:var(--{STATUS_SEV[k]}-bg)"  # noqa: E731
    lv = res["scope"]["level"]
    o = []
    a = o.append
    a(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
      f'<title>Code of conduct comparison: {e(res["code"]["name"])}</title><style>{export.CSS}</style></head><body><div class="wrap">')
    a(f'<h1>Code of conduct comparison</h1><p class="sub"><strong>{e(res["code"]["name"])}</strong> · {res["code"]["clauses"]} clauses · '
      f'Level {lv} ({e(scan.LEVEL_NAMES[lv])}) · core + {e(", ".join(res["scope"]["profiles"]))} · bands {e(", ".join(res["scope"]["age_bands"]))} · '
      f'CSEF v{e(res["tool"]["standard_version"])}</p>')
    a('<p class="disclaimer"><strong>First-pass comparison based on wording, not legal advice.</strong> Confirm every result by reading the '
      'clauses cited. Under the EU KIDS Act proposal (Recital 39), adhering to a code does not in itself presume legal compliance.</p>')
    a('<section class="panel"><h2>Summary</h2><div class="tiles" style="grid-template-columns:repeat(4,minmax(0,1fr))">')
    for k in ("conflict", "missing", "partial", "covered"):
        a(f'<div class="tile" style="{sev(k)};background:var(--cb);border-color:var(--c)"><b style="color:var(--c)">{res["counts"][k]}</b>'
          f'<span><strong>{e(STATUS_LABEL[k])}</strong></span></div>')
    a('</div></section>')
    a('<section class="panel"><h2>Structure of the code</h2><p class="muted small">What the EU KIDS Act proposal expects codes of conduct to contain (Art. 17, Art. 23, Recital 39).</p>'
      '<table><thead><tr><th>Criterion</th><th>Basis</th><th>Result</th><th>Where</th></tr></thead><tbody>')
    for s in res["structure"]:
        a(f'<tr><td><strong>{e(s["title"])}</strong></td><td class="small">{e(s["basis"])}</td>'
          f'<td><span class="sev" style="{sev(s["status"])}">{e(STATUS_LABEL[s["status"]])}</span>'
          + (f'<div class="small muted">{e(s["why"])}</div>' if s["why"] else "")
          + f'</td><td class="small">{e(", ".join(x["id"] for x in s["clauses"]) or "-")}</td></tr>')
    a('</tbody></table></section>')
    a('<section class="panel"><h2>Rules</h2><div class="filters">')
    for k in ("conflict", "missing", "partial", "covered", "not_applicable"):
        chk = " checked" if k != "not_applicable" else ""
        a(f'<label class="fchip" style="{sev(k)}"><input type="checkbox" data-sev-filter value="{k}"{chk}> {e(STATUS_LABEL[k])}</label>')
    a(f'<select id="flevel" aria-label="Up to level"><option value="{lv}">Chosen level</option><option value="3">All levels</option></select>'
      '<input id="q" type="search" placeholder="Search rule or clause" aria-label="Search"><span id="fcount" class="small muted"></span></div>')
    for x in sorted(res["rules"], key=lambda x: (STATUS_ORDER.index(x["status"]), x["rule_id"])):
        k = x["status"]
        a(f'<details class="card" data-sev="{k}" data-tier="{x["tier"]}" style="{sev(k)}"><summary>'
          f'<span class="sev">{e(STATUS_LABEL[k])}</span><span class="rid">{e(x["rule_id"])}</span><strong>{e(x["title"])}</strong>'
          f'<span class="lv" style="--c:var(--L{x["tier"]})">L{x["tier"]} {e(x["level"])}</span></summary><div class="body">'
          f'<p>{e(x["requirement"])}</p>')
        for cf in x["conflicts"]:
            a(f'<p class="note" style="background:var(--BLOCK-bg)"><strong>Possible conflict in {e(cf["clause"])}:</strong> "{e(cf["sentence"])}"</p>')
        if x["why"]:
            a(f'<p class="small"><strong>Assessment.</strong> {e(x["why"])}.</p>')
        for cl in x["clauses"][:2]:
            a(f'<p class="small"><strong>{e(cl["id"])}</strong>{(" · " + e(cl["heading"])) if cl["heading"] else ""}: "{e(cl["text"][:300])}"</p>')
        if k in ("conflict", "missing", "partial"):
            a(f'<p><strong>Suggested addition to the code.</strong> {e(x["improvement"])}</p>')
        a(f'<p class="small muted">Sources: {e(", ".join(x["sources"]))}</p></div></details>')
    a('</section><section class="panel"><h2>Sources</h2><table><tbody>')
    for sid, s in res["sources"].items():
        t = f'<a href="{e(s["url"])}">{e(s["title"])}</a>' if s.get("url") else e(s["title"])
        a(f'<tr><td class="rid">{e(sid)}</td><td>{t}</td><td class="small">{e(s.get("status", ""))}</td></tr>')
    a('</tbody></table></section></div>')
    a('''<script>(function(){const q=document.getElementById('q'),lv=document.getElementById('flevel');
function f(){const sev=new Set([...document.querySelectorAll('[data-sev-filter]:checked')].map(x=>x.value));const t=(q.value||'').toLowerCase(),m=parseInt(lv.value,10);let n=0;
document.querySelectorAll('details.card').forEach(c=>{const ok=sev.has(c.dataset.sev)&&parseInt(c.dataset.tier,10)<=m&&(!t||c.textContent.toLowerCase().includes(t));c.classList.toggle('hidden',!ok);if(ok)n++;});
document.getElementById('fcount').textContent=n+' shown';}
document.querySelectorAll('[data-sev-filter]').forEach(x=>x.addEventListener('change',f));q.addEventListener('input',f);lv.addEventListener('change',f);f();})();</script>''')
    a('</body></html>')
    return "".join(o)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compare a code of conduct with the Child-Safe EdTech Framework")
    ap.add_argument("--input", required=True, help=".txt, .md, .html, .pdf or .docx")
    ap.add_argument("--name", help="name of the code (default: file name)")
    ap.add_argument("--level", type=int, choices=[1, 2, 3], default=3, help="compare up to this level (default 3: everything)")
    ap.add_argument("--profiles", default="A,B,C", help="comma-separated profiles in scope (default A,B,C)")
    ap.add_argument("--bands", default="B1,B2,B3,B4,B5", help="comma-separated age bands in scope")
    ap.add_argument("--pack", action="append", default=[], help="extra pack (country, sector or company)")
    ap.add_argument("--framework-root", "--standard-root", dest="standard_root", default=None)
    ap.add_argument("--out-dir", default="csef-coc")
    ap.add_argument("--formats", default="md,html,json")
    args = ap.parse_args(argv)

    root = Path(args.standard_root).resolve() if args.standard_root else scan.default_root()
    std = scan.load_standard(root)
    for p in args.pack:
        scan.apply_pack(std, Path(p))
    topics = yaml.safe_load((root / "framework" / "coc-topics.yaml").read_text(encoding="utf-8"))
    src = Path(args.input)
    try:
        text = read_input(src)
    except RuntimeError as ex:
        print(f"csef coc: {ex}", file=sys.stderr)
        return 1
    res = compare(text, std, topics, args.level, set(args.profiles.split(",")), set(args.bands.split(",")), args.name or src.stem)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fm = [f.strip() for f in args.formats.split(",")]
    if "md" in fm:
        (out / "coc-comparison.md").write_text(render_md(res), encoding="utf-8")
    if "html" in fm:
        (out / "coc-comparison.html").write_text(render_html(res), encoding="utf-8")
    if "json" in fm:
        (out / "coc-comparison.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    c = res["counts"]
    print(f"{res['code']['name']}: {res['code']['clauses']} clauses | conflict {c['conflict']}, missing {c['missing']}, "
          f"partial {c['partial']}, covered {c['covered']} | structure: {res['structure_counts']} | written to {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
