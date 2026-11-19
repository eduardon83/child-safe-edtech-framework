#!/usr/bin/env python3
"""Build the example reports for the website (docs/examples/).

Runs every CSEF tool on the fictional example products in examples/ and copies the outputs that people
want to see before they start: dashboards, PDF and Word reports, the Compass, the code-of-conduct
comparison, the company policy kit, the serious-game pre-check, metadata and a label package. Writes
docs/examples/index.html to list them by audience.

Run it before each release (PDF needs Chrome or Chromium):

  python3 tooling/examples.py

The outputs carry the date they were made, so build.py --check does not compare them.
"""
from __future__ import annotations

import datetime as dt
import html
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import brand  # noqa: E402
import scan  # noqa: E402

OUT = ROOT / "docs" / "examples"
PY = sys.executable


def run(*args):
    r = subprocess.run([PY, *map(str, args)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode not in (0, 1):
        raise SystemExit(f"examples: {' '.join(map(str, args))} failed\n{r.stderr[-2000:]}")
    return r


def copy(src: Path, rel: str) -> str:
    dst = OUT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    return rel


def build(tmp: Path) -> dict:
    made = {}
    # Developers: a product with problems, and one that passes.
    run("tooling/scan.py", "--repo", "examples/noncompliant-game", "--out-dir", tmp / "bad", "--format", "none",
        "--export", "html,pdf,docx")
    run("tooling/scan.py", "--repo", "examples/compliant-game", "--out-dir", tmp / "good", "--format", "none",
        "--export", "html")
    made["bad_html"] = copy(tmp / "bad" / "dashboard.html", "developers/word-quest/dashboard.html")
    if (tmp / "bad" / "report.pdf").exists():
        made["bad_pdf"] = copy(tmp / "bad" / "report.pdf", "developers/word-quest/report.pdf")
    made["bad_docx"] = copy(tmp / "bad" / "report.docx", "developers/word-quest/report.docx")
    made["good_html"] = copy(tmp / "good" / "dashboard.html", "developers/garden-of-numbers/dashboard.html")
    # Companies: the policy kit.
    run("tooling/policy.py", "--answers", "examples/policy/answers.json", "--batch", "--out-dir", tmp / "policy",
        "--formats", "md,html,pdf,docx", "--no-skill")
    for name in ("staff-policy", "boundaries-report"):
        made[f"{name}_html"] = copy(tmp / "policy" / f"{name}.html", f"companies/{name}.html")
        if (tmp / "policy" / f"{name}.pdf").exists():
            made[f"{name}_pdf"] = copy(tmp / "policy" / f"{name}.pdf", f"companies/{name}.pdf")
    made["pack"] = copy(tmp / "policy" / "acme.yaml", "companies/company-pack.yaml")
    # Designers and educators: the Literacy Compass.
    run("tooling/compass.py", "--input", "examples/compass/fact-quest", "--manifest",
        "examples/compass/fact-quest/csef.yaml", "--csef-findings", tmp / "bad" / "findings.json",
        "--out-dir", tmp / "compass", "--formats", "html")
    made["compass"] = copy(tmp / "compass" / "compass.html", "designers/compass.html")
    # Industry bodies: code-of-conduct comparison.
    run("tooling/coc.py", "--input", "examples/codes-of-conduct/example-code.md", "--level", "2", "--out-dir",
        tmp / "coc", "--formats", "html")
    made["coc"] = copy(tmp / "coc" / "coc-comparison.html", "industry/coc-comparison.html")
    # Label teams: pre-check, metadata and a package.
    run("tooling/precheck.py", "--repo", "examples/compliant-game", "--out-dir", tmp / "pre", "--formats", "html")
    made["precheck"] = copy(tmp / "pre" / "precheck.html", "labels/precheck.html")
    run("tooling/metadata.py", "--repo", "examples/compliant-game", "--out-dir", tmp / "md")
    for f in ("sg-mdf.json", "sg-mdf.xml", "lrmi.jsonld"):
        made[f] = copy(tmp / "md" / f, f"labels/{f}")
    run("tooling/metadata.py", "--repo", "examples/compliant-game", "--package", "--out-dir", tmp / "pkg")
    z = sorted((tmp / "pkg").glob("*.zip"))[-1]
    made["package"] = copy(z, "labels/label-package-garden-of-numbers.zip")
    # Researchers: the event file check, the open evidence feed and its check (fictional data).
    ev, cat = "examples/evidence-feed/events.tsv", "examples/compliant-game/docs/event-catalogue.yaml"
    run("tooling/evidence.py", "check-events", "--events", ev, "--catalogue", cat, "--out-dir", tmp / "ev", "--formats", "html")
    made["events"] = copy(tmp / "ev" / "events-check.html", "researchers/events-check.html")
    shutil.make_archive(str(tmp / "feed"), "zip", ROOT / "examples" / "evidence-feed", "feed")
    made["feed"] = copy(tmp / "feed.zip", "researchers/garden-of-numbers-evidence-feed.zip")
    run("tooling/evidence.py", "check-feed", "--feed", tmp / "feed.zip", "--out-dir", tmp / "fc", "--formats", "html")
    made["feedcheck"] = copy(tmp / "fc" / "feed-check.html", "researchers/feed-check.html")
    return made


def size(rel: str) -> str:
    n = (OUT / rel).stat().st_size
    return f"{n / 1_000_000:.1f} MB" if n >= 1_000_000 else f"{max(1, round(n / 1000))} KB"


def link(made: dict, key: str, label: str) -> str:
    if key not in made:
        return ""
    rel = made[key]
    ext = rel.rsplit(".", 1)[-1].upper().replace("JSONLD", "JSON-LD")
    return (f'<a class="file" href="{html.escape(rel)}"><span class="fmt">{ext}</span>{html.escape(label)}'
            f'<span class="sz">{size(rel)}</span></a>')


def page(made: dict) -> str:
    groups = [
        ("developers", "For developers", "teal",
         "The scanner's output for two fictional games. Word Quest breaks many rules on purpose; Garden of Numbers passes.",
         [("Word Quest: a product with problems", "Findings by severity, the improvement plan, communications and sources.",
           [("bad_html", "Interactive dashboard"), ("bad_pdf", "Report"), ("bad_docx", "Report")]),
          ("Garden of Numbers: a product that passes", "What a clean result looks like at level 3.",
           [("good_html", "Interactive dashboard")])]),
        ("companies", "For companies", "indigo",
         "The policy kit from the questionnaire, for a fictional company (Acme).",
         [("Staff policy", "Your boundaries in plain language, for everyone who builds the product.",
           [("staff-policy_html", "Staff policy"), ("staff-policy_pdf", "Staff policy")]),
          ("Boundaries report", "Each answer matched with the law and recommendations, for legal counsel.",
           [("boundaries-report_html", "Boundaries report"), ("boundaries-report_pdf", "Boundaries report")]),
          ("Company pack", "The guardrails file the scanner checks in every project.",
           [("pack", "Company pack")])]),
        ("designers", "For designers and educators", "sky",
         "The Literacy Compass for Fact Quest, a fictional detective game for ages 10 to 15.",
         [("Literacy Compass", "What the game teaches about digital, media and AI literacy, with an evidence level per target.",
           [("compass", "Compass report")])]),
        ("industry", "For industry bodies", "sun",
         "A fictional code of conduct, written with gaps and conflicts on purpose.",
         [("Code-of-conduct comparison", "Covered, partial, missing or in conflict, with the clauses cited.",
           [("coc", "Comparison")])]),
        ("researchers", "For researchers and data teams", "sky",
         "Garden of Numbers logs play in the Open Game Data format for a study. Fictional data: 60 pupils in 6 classes.",
         [("Event file check", "The event file against the child-safe profile and the game's event catalogue.",
           [("events", "Event file check")]),
          ("Open evidence feed", "Group figures per level, with at least 10 players and 3 classes behind each.",
           [("feed", "Evidence feed"), ("feedcheck", "Feed check")])]),
        ("labels", "For teams preparing a label", "lilac",
         "Garden of Numbers, prepared for a serious-game quality label.",
         [("Serious-game pre-check", "22 quality criteria: ready, partial, missing or CSEF issue.",
           [("precheck", "Pre-check")]),
          ("Metadata", "The product description in SG-MDF (DIN SPEC 91380) and schema.org LearningResource.",
           [("sg-mdf.json", "SG-MDF"), ("sg-mdf.xml", "SG-MDF"), ("lrmi.jsonld", "schema.org")]),
          ("Label package", "Metadata, findings, pre-check, evidence index and hashes, in one zip.",
           [("package", "Label package")])]),
    ]
    blocks = []
    for gid, title, color, intro, items in groups:
        cards = []
        for t, d, links in items:
            ls = "".join(link(made, k, lab) for k, lab in links)
            cards.append(f'<div class="card"><h3>{html.escape(t)}</h3><p>{html.escape(d)}</p><div class="files">{ls}</div></div>')
        blocks.append(f'<section id="{gid}" class="grp" style="--g:var(--c-{color})"><h2>{html.escape(title)}</h2>'
                      f'<p class="intro">{html.escape(intro)}</p><div class="cards">{"".join(cards)}</div></section>')
    css = brand.tokens_css() + brand.BASE_CSS + """
*{box-sizing:border-box}body{margin:0;background:var(--c-paper);color:var(--c-ink);font:17px/1.6 var(--font)}
a{color:var(--c-indigo-t)}.in{max-width:1120px;margin:0 auto;padding:0 20px}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:18px 20px}
.top .csef-brand{margin:0}.top nav{display:flex;gap:4px 20px;flex-wrap:wrap}
.top nav a{color:var(--c-ink);text-decoration:none;font-weight:500;padding:10px 0}
h1{font-size:clamp(2.2rem,5vw,3.2rem);line-height:1.05;margin:24px 0 12px}
.lead{font-size:1.15rem;color:var(--c-ink2);max-width:62ch;margin:0 0 20px}
.jump{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.jump a{display:inline-flex;align-items:center;min-height:44px;padding:0 16px;border-radius:999px;background:var(--c-panel);
border:1px solid var(--c-line);color:var(--c-ink);text-decoration:none;font-weight:500}
.grp{padding:36px 0;border-top:1px solid var(--c-line)}.grp h2{font-size:1.8rem;margin:0 0 6px;display:flex;align-items:center;gap:12px}
.grp h2:before{content:"";width:14px;height:14px;border-radius:4px;background:var(--g)}
.intro{color:var(--c-ink2);margin:0 0 18px;max-width:70ch}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.card{background:var(--c-panel);border:1px solid var(--c-line);border-radius:16px;padding:20px}
.card h3{margin:0 0 6px;font-size:1.2rem}.card p{margin:0 0 14px;color:var(--c-ink2);font-size:.96rem}
.files{display:flex;flex-direction:column;gap:8px}
.file{display:flex;align-items:center;gap:10px;min-height:44px;padding:8px 12px;border-radius:10px;background:var(--c-paper);
color:var(--c-ink);text-decoration:none;font-weight:500}.file:hover{background:var(--c-code)}
.fmt{flex:none;min-width:58px;text-align:center;padding:2px 8px;border-radius:6px;background:var(--c-ink);color:var(--c-paper);
font-size:.75rem;font-weight:700;letter-spacing:.03em}.sz{margin-left:auto;color:var(--c-ink2);font-size:.85rem;font-weight:400}
.note{background:var(--c-sun-bg);border-radius:12px;padding:12px 16px;font-size:.95rem;margin:8px 0 24px}
footer{margin-top:40px;padding:28px 0;border-top:1px solid var(--c-line);color:var(--c-ink2);font-size:.9rem}
"""
    today = dt.date.today().isoformat()
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>Example reports · CSEF</title><meta name="description" content="What CSEF produces, on fictional example products: '
            f'dashboards, PDF reports, policy kit, Literacy Compass, code-of-conduct comparison, serious-game pre-check and label package.">'
            f'{brand.head("../favicon.svg")}<style>{css}</style></head><body><div class="csef-stripe"></div>'
            f'<header class="top"><a href="../" aria-label="CSEF home" style="text-decoration:none">{brand.logo("lockup", 40)}</a>'
            f'<nav aria-label="Main"><a href="../">Home</a><a href="../questionnaire/">Questionnaire</a><a href="../pack-builder/">Pack Builder</a>'
            f'<a href="https://github.com/eduardon83/child-safe-edtech-framework">GitHub</a></nav></header>'
            f'<main class="in"><h1>Example reports</h1><p class="lead">See what you get before you start. Every file here was made by the '
            f'CSEF tools from fictional example products in the repository.</p>'
            f'<nav class="jump" aria-label="Audiences"><a href="#developers">Developers</a><a href="#companies">Companies</a>'
            f'<a href="#designers">Designers and educators</a><a href="#industry">Industry bodies</a><a href="#labels">Label teams</a><a href="#researchers">Researchers</a></nav>'
            f'<p class="note">Made with CSEF {scan.TOOL_VERSION} on {today}. Fictional products, no real data. A pre-compliance check, '
            f'not legal advice and not a certification.</p>{"".join(blocks)}</main>'
            f'<footer><div class="in">Child-Safe EdTech Framework (CSEF), maintained by Kendir Studios with the EdTech community. '
            f'Framework content CC BY 4.0 · code Apache 2.0</div></footer></body></html>\n')


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as t:
        made = build(Path(t))
    (OUT / "index.html").write_text(page(made), encoding="utf-8")
    missing = [k for k in ("bad_pdf", "staff-policy_pdf", "boundaries-report_pdf") if k not in made]
    print(f"examples: {len(made)} files in {OUT.relative_to(ROOT)}"
          + (f" (no PDF for {', '.join(missing)}: install Chrome or Chromium)" if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
