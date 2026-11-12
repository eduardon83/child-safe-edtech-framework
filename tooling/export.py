#!/usr/bin/env python3
"""CSEF export: turn a scan (findings.json) into a reviewer-friendly dashboard and documents.

  python3 tooling/export.py --input csef-report/findings.json --formats html,pdf,docx [--out-dir DIR]

Outputs (in --out-dir, default: the folder of the input):
  dashboard.html   interactive, self-contained dashboard (levels, age bands, filters, checklists)
  report.pdf       print version of the dashboard (needs Chrome/Chromium, or WeasyPrint)
  report.docx      Word document for legal counsel and clients (needs python-docx)

Licence: Apache-2.0
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LEVEL_NAMES = {1: "Legal baseline", 2: "Forward-compliant", 3: "Best practice"}
LEVEL_DESC = {
    1: "Binding law in force, or law with a fixed application date.",
    2: "Adds adopted EU proposals and official benchmarks (EU KIDS Act, DFA, DSA Art. 28 guidelines).",
    3: "Adds research and expert recommendations.",
}
BANDS = [("B1", "3-5"), ("B2", "6-9"), ("B3", "10-12"), ("B4", "13-15"), ("B5", "16-17")]
SEV = {
    "BLOCK": ("Blocking", "Clear breach of a MUST rule. Fix or formally waive before release."),
    "REVIEW": ("Review", "Likely breach of a MUST rule. A person must confirm."),
    "WARN": ("Warning", "A SHOULD rule is not met."),
    "HUMAN": ("Human check", "Applies, but cannot be verified in code."),
    "NEXT": ("Next level", "Signal against a rule above the chosen level."),
    "WAIVED": ("Waived", "Accepted gap with reason, approver and expiry."),
}
SEV_ORDER = ["BLOCK", "REVIEW", "WARN", "HUMAN", "NEXT", "WAIVED"]
STATUS = {
    "blocked": ("Blocked", "BLOCK"),
    "review": ("Needs review", "REVIEW"),
    "warn": ("Warnings only", "WARN"),
    "human": ("Human checks pending", "HUMAN"),
    "clear": ("No automated issues", "OK"),
}
TYPE_LABEL = {"law": "Law", "law-pending": "Law (applies later)", "proposal": "Proposal", "guidance": "Guidance",
              "standard": "Standard", "literature": "Research", "news": "News", "policy": "Organisation policy"}

e = html.escape


# --------------------------------------------------------------------------- model
def build_model(d: dict) -> dict:
    if d.get("format", 1) < 2:
        raise SystemExit("findings.json is from an older scanner. Re-run tooling/scan.py (v0.3.0 or later).")
    rules = d["rules"]
    level = d["level"]
    findings = d["findings"]
    active = [f for f in findings if f.get("raw") != "WAIVED"]
    human = d["human_checks"]

    def tier(rid):
        return int(rules[rid]["tier"])

    levels = []
    for L in (1, 2, 3):
        in_l = [r for r in rules.values() if int(r["tier"]) <= L]
        iss = [f for f in active if tier(f["rule_id"]) <= L]
        by = {s: sorted({f["rule_id"] for f in iss if f["raw"] == s}) for s in ("BLOCK", "REVIEW", "WARN")}
        hum = [h["rule_id"] for h in human if tier(h["rule_id"]) <= L and not h["has_static_hit"]]
        with_issue = set().union(*by.values())
        if by["BLOCK"]:
            st = "blocked"
        elif by["REVIEW"]:
            st = "review"
        elif by["WARN"]:
            st = "warn"
        elif hum:
            st = "human"
        else:
            st = "clear"
        levels.append({"level": L, "rules": len(in_l), "block": by["BLOCK"], "review": by["REVIEW"], "warn": by["WARN"],
                       "human": hum, "clean": len(in_l) - len(with_issue), "status": st,
                       "chosen": L == level, "minimum": L == d.get("minimum_level", 1) and d.get("minimum_level", 1) > 1})

    bands = []
    for b, ages in BANDS:
        specific = [r["id"] for r in rules.values() if r.get("age_bands") != ["all"] and b in r.get("age_bands", [])]
        applying = {r["id"] for r in rules.values() if r.get("age_bands") == ["all"] or b in r.get("age_bands", [])}
        iss = sorted({f["rule_id"] for f in active if f["rule_id"] in applying and f["severity"] in ("BLOCK", "REVIEW", "WARN")})
        bands.append({"band": b, "ages": ages, "declared": b in d["age_bands"], "specific": specific, "issues": iss})

    groups = {}
    for f in findings:
        g = groups.setdefault(f["rule_id"], {"rule_id": f["rule_id"], "severity": f["severity"], "raw": f["raw"], "items": []})
        if SEV_ORDER.index(f["severity"]) < SEV_ORDER.index(g["severity"]):
            g["severity"] = f["severity"]
        g["items"].append(f)
    fgroups = sorted(groups.values(), key=lambda g: (SEV_ORDER.index(g["severity"]), g["rule_id"]))

    counts = {s: len([g for g in fgroups if g["severity"] == s]) for s in SEV_ORDER}
    counts["HUMAN"] = len([h for h in human if not h["next_level"] and not h["has_static_hit"]])

    m = d.get("manifest") or {}
    counsel = []
    ks = (m.get("legal_scope") or {}).get("kids_act")
    counsel.append(("EU KIDS Act scope", f"Declared: {ks or 'not declared'}. Confirm per distribution channel whether the "
                    "education exemption (Art. 2(4)(c)) applies, or whether the product is an online game, AI companion or chatbot in scope."))
    counsel.append(("GDPR role and legal basis", f"Declared role: {m.get('gdpr_role') or 'not declared'}. Confirm controller/processor "
                    "split per deployment, the legal basis for each purpose, and the national age of digital consent where consent is used."))
    if m.get("jurisdictions"):
        counsel.append(("National law", f"Jurisdictions declared: {', '.join(map(str, m['jurisdictions']))}. Check national rules not yet covered by a pack."))
    lvl1 = sorted({h["rule_id"] for h in human if tier(h["rule_id"]) == 1 and rules[h["rule_id"]]["level"] == "MUST"}
                  | {f["rule_id"] for f in active if tier(f["rule_id"]) == 1 and f["raw"] in ("BLOCK", "REVIEW")})
    proposals = sorted({sid for r in rules.values() for sid in r.get("sources", [])
                        if d["sources"].get(sid, {}).get("type") in ("proposal", "law-pending")})
    waived = [f for f in findings if f["severity"] == "WAIVED"]

    return {"d": d, "rules": rules, "level": level, "levels": levels, "bands": bands, "fgroups": fgroups,
            "counts": counts, "counsel": counsel, "lvl1": lvl1, "proposals": proposals, "waived": waived,
            "verdict": levels[level - 1]["status"], "manifest": m}


# --------------------------------------------------------------------------- html
CSS = """
:root{--bg:#f6f6f3;--panel:#fff;--ink:#1c2220;--muted:#5b6561;--line:#dde0da;--code:#f0f1ed;
--BLOCK:#b42318;--BLOCK-bg:#fdecea;--REVIEW:#b45309;--REVIEW-bg:#fff1e0;--WARN:#8a6d00;--WARN-bg:#fff8d6;
--HUMAN:#1d4ed8;--HUMAN-bg:#e8efff;--NEXT:#5f6b7a;--NEXT-bg:#eef0f3;--WAIVED:#3f7a52;--WAIVED-bg:#e6f3ea;--OK:#1f7a4d;--OK-bg:#e3f4ea;
--L1:#0f5c4d;--L1-bg:#e1f1ec;--L2:#3949ab;--L2-bg:#e8eafb;--L3:#7b3fa0;--L3-bg:#f3e8fa;
--B1:#d9480f;--B2:#c08400;--B3:#2b8a3e;--B4:#1971c2;--B5:#7048e8;
--font:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#111413;--panel:#1a1e1d;--ink:#e7eae8;--muted:#a1aaa6;--line:#2c3331;--code:#222826;
--BLOCK:#ff8a7a;--BLOCK-bg:#3b1c19;--REVIEW:#ffb36b;--REVIEW-bg:#3a2715;--WARN:#f2d15c;--WARN-bg:#35300f;--HUMAN:#8fb1ff;--HUMAN-bg:#1c2640;
--NEXT:#aab4c0;--NEXT-bg:#252a30;--WAIVED:#8fd1a5;--WAIVED-bg:#1c2e23;--OK:#7ad6a3;--OK-bg:#18301f;
--L1:#6fd2b9;--L1-bg:#16302a;--L2:#9fa8ff;--L2-bg:#1f2342;--L3:#d7a6f5;--L3-bg:#2e1f39;
--B1:#ff8c5a;--B2:#f2c14e;--B3:#69db7c;--B4:#74c0fc;--B5:#b197fc}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15.5px/1.5 var(--font)}
a{color:var(--L2)}.wrap{max-width:1200px;margin:0 auto;padding:20px 16px 48px}
h1{font-size:1.65rem;margin:0}h2{font-size:1.2rem;margin:0 0 4px}h3{font-size:1rem;margin:0}
.sub{color:var(--muted);margin:2px 0 0}.muted{color:var(--muted)}.small{font-size:.86rem}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-top:16px}
.disclaimer{border-left:4px solid var(--REVIEW);background:var(--REVIEW-bg);padding:10px 14px;border-radius:8px;margin-top:14px;font-size:.92rem}
.top{display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:flex-end}
.btns{display:flex;gap:8px;flex-wrap:wrap}
button{font:inherit;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:8px;padding:6px 12px;cursor:pointer}
button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid var(--L2);outline-offset:2px}
.verdict{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,2fr);gap:16px;align-items:stretch}
@media(max-width:820px){.verdict{grid-template-columns:1fr}}
.vbox{border-radius:12px;padding:16px;display:flex;flex-direction:column;justify-content:center}
.vbox .big{font-size:1.45rem;font-weight:700}
.tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
@media(max-width:520px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
.tile{border-radius:10px;padding:10px 12px;border:1px solid var(--line)}
.tile b{font-size:1.5rem;display:block;line-height:1.1}.tile span{font-size:.85rem}
.ladder{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:10px}
@media(max-width:820px){.ladder{grid-template-columns:1fr}}
.lvl{border:1px solid var(--line);border-top:6px solid var(--c);border-radius:12px;padding:14px;background:var(--panel);position:relative}
.lvl.chosen{box-shadow:0 0 0 2px var(--c) inset}
.lvl .name{color:var(--c);font-weight:700}
.tag{display:inline-block;font-size:.75rem;border-radius:999px;padding:1px 8px;font-weight:600;border:1px solid currentColor}
.pill{display:inline-flex;align-items:center;gap:6px;font-weight:600;font-size:.88rem;border-radius:999px;padding:3px 10px;color:var(--c);background:var(--cb)}
.dot{width:9px;height:9px;border-radius:50%;background:currentColor;display:inline-block}
.bar{height:8px;border-radius:99px;background:var(--code);overflow:hidden;margin:10px 0 4px}.bar>i{display:block;height:100%;background:var(--c)}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;margin-top:8px;font-size:.82rem;text-align:center}
.stats div b{display:block;font-size:1.05rem}
.bands{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:10px}
@media(max-width:820px){.bands{grid-template-columns:repeat(2,minmax(0,1fr))}}
.band{border-radius:12px;padding:12px;border:1px solid var(--line);border-left:6px solid var(--c);opacity:.62}
.band.on{opacity:1;background:var(--panel)}.band .bn{font-weight:700;color:var(--c)}
.scope{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 24px;margin-top:8px}
@media(max-width:640px){.scope{grid-template-columns:1fr}}
.scope div{padding:6px 0;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:12px}
.scope div span:last-child{text-align:right;font-weight:600}
.filters{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
.filters input[type=search]{flex:1 1 220px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit}
.filters select{padding:7px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit}
.fchip{display:inline-flex;gap:6px;align-items:center;border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:.86rem;cursor:pointer;color:var(--c)}
.fchip:has(input:checked){background:var(--cb);border-color:var(--c)}
details.card{border:1px solid var(--line);border-left:5px solid var(--c);border-radius:10px;margin:8px 0;background:var(--panel)}
details.card>summary{list-style:none;cursor:pointer;padding:10px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
details.card>summary::-webkit-details-marker{display:none}
.card .body{padding:0 14px 12px}
.rid{font-family:var(--mono);font-size:.82rem;color:var(--muted)}
.sev{font-size:.75rem;font-weight:700;border-radius:6px;padding:2px 8px;color:var(--c);background:var(--cb);border:1px solid var(--c)}
.lv{font-size:.75rem;font-weight:600;border-radius:6px;padding:1px 7px;color:var(--c);border:1px solid var(--c)}
code,.loc{font-family:var(--mono);font-size:.82rem;background:var(--code);border-radius:5px;padding:1px 5px;overflow-wrap:anywhere}
ul.locs{margin:6px 0;padding-left:18px}ul.locs li{margin:2px 0}
.src a{margin-right:8px}.note{background:var(--HUMAN-bg);border-radius:6px;padding:6px 10px;margin:6px 0;font-size:.9rem}
table{width:100%;border-collapse:collapse;font-size:.92rem}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.82rem;color:var(--muted);font-weight:600}
.check td:first-child{width:32px}.check input[type=checkbox]{width:18px;height:18px}
.check input[type=text]{width:100%;border:1px solid var(--line);border-radius:6px;padding:5px 8px;background:var(--bg);color:var(--ink);font:inherit;font-size:.88rem}
.imp{border-left:4px solid var(--c);padding:6px 12px;margin:10px 0;background:var(--panel)}
.typ{font-size:.72rem;border-radius:6px;padding:1px 6px;border:1px solid var(--line);white-space:nowrap}
.hidden{display:none !important}
@media(max-width:700px){table{display:block;overflow-x:auto}.check input[type=text]{min-width:140px}}
section.panel{min-width:0;overflow-wrap:break-word}
.scope div span:first-child{flex:0 0 auto}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:.85rem;margin-top:8px}
nav.toc{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:12px;font-size:.92rem}
@page{size:A4;margin:12mm}
@media print{body{background:#fff;font-size:10.5px}.btns,.filters,nav.toc{display:none !important}
details.card,.lvl,.band,.tile,tr,.imp{break-inside:avoid}.panel{border:1px solid #ccc;padding:12px;margin-top:10px}.wrap{padding:0;max-width:none}a{color:#000}
.verdict{grid-template-columns:1fr 2fr !important}.tiles{grid-template-columns:repeat(3,1fr) !important}
.ladder{grid-template-columns:repeat(3,1fr) !important}.bands{grid-template-columns:repeat(5,1fr) !important}
.scope{grid-template-columns:1fr 1fr !important}table{display:table !important}h1{font-size:1.4rem}.stats{font-size:.68rem;overflow-wrap:normal}.band{overflow-wrap:normal}
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

JS = r"""
(function(){
  const key = 'csef-dash-' + (document.body.dataset.product || 'product');
  function load(){ try { return JSON.parse(localStorage.getItem(key) || '{}'); } catch(e){ return {}; } }
  function save(v){ try { localStorage.setItem(key, JSON.stringify(v)); } catch(e){} }
  const st = load();
  document.querySelectorAll('[data-check]').forEach(cb => {
    const id = cb.dataset.check; cb.checked = !!(st[id] && st[id].ok);
    const note = document.querySelector('[data-note="'+id+'"]'); if (note && st[id]) note.value = st[id].note || '';
    const upd = () => { st[id] = {ok: cb.checked, note: note ? note.value : ''}; save(st); progress(); };
    cb.addEventListener('change', upd); if (note) note.addEventListener('input', upd);
  });
  function progress(){
    const all = document.querySelectorAll('[data-check]'), done = [...all].filter(x => x.checked).length;
    const el = document.getElementById('hc-progress'); if (el) el.textContent = done + ' of ' + all.length + ' confirmed';
  }
  progress();
  const q = document.getElementById('q'), lv = document.getElementById('flevel');
  function filter(){
    const sev = new Set([...document.querySelectorAll('[data-sev-filter]:checked')].map(x => x.value));
    const term = (q.value || '').toLowerCase(), maxL = parseInt(lv.value || '3', 10);
    let shown = 0;
    document.querySelectorAll('details.card[data-sev]').forEach(c => {
      const ok = sev.has(c.dataset.sev) && parseInt(c.dataset.tier,10) <= maxL && (!term || c.textContent.toLowerCase().includes(term));
      c.classList.toggle('hidden', !ok); if (ok) shown++;
    });
    document.getElementById('fcount').textContent = shown + ' shown';
  }
  document.querySelectorAll('[data-sev-filter]').forEach(x => x.addEventListener('change', filter));
  q.addEventListener('input', filter); lv.addEventListener('change', filter); filter();
  document.getElementById('expand').addEventListener('click', () => document.querySelectorAll('details.card').forEach(d => d.open = true));
  document.getElementById('collapse').addEventListener('click', () => document.querySelectorAll('details.card').forEach(d => d.open = false));
  document.getElementById('print').addEventListener('click', () => { document.querySelectorAll('details.card').forEach(d => d.open = true); window.print(); });
  document.getElementById('dlchecks').addEventListener('click', () => {
    const rows = [['rule','confirmed','note']];
    document.querySelectorAll('[data-check]').forEach(cb => { const n = document.querySelector('[data-note="'+cb.dataset.check+'"]');
      rows.push([cb.dataset.check, cb.checked ? 'yes' : 'no', (n ? n.value : '').replace(/"/g,'""')]); });
    const csv = rows.map(r => r.map(v => '"' + v + '"').join(',')).join('\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
    a.download = 'csef-human-checks.csv'; document.body.appendChild(a); a.click(); a.remove();
  });
  window.addEventListener('beforeprint', () => document.querySelectorAll('details.card').forEach(d => d.open = true));
})();
"""


def sev_vars(s):
    return f"--c:var(--{s});--cb:var(--{s}-bg)"


def lvl_vars(L):
    return f"--c:var(--L{L});--cb:var(--L{L}-bg)"


def src_links(model, sids):
    out = []
    for sid in sids:
        s = model["d"]["sources"].get(sid, {})
        label = e(sid)
        typ = TYPE_LABEL.get(s.get("type", ""), s.get("type", ""))
        if s.get("url"):
            out.append(f'<a href="{e(s["url"])}" title="{e(s.get("title", ""))}">{label}</a> <span class="muted small">({e(typ)})</span>')
        else:
            out.append(f'<span title="{e(s.get("title", ""))}">{label}</span> <span class="muted small">({e(typ)})</span>')
    return " ".join(out)


def render_html(model: dict, for_print: bool = False) -> str:
    d, rules, level = model["d"], model["rules"], model["level"]
    m = model["manifest"]
    product = d.get("product") or "Product"
    gen = d.get("generated", "")[:10]
    st_label, st_sev = STATUS[model["verdict"]]
    out = []
    a = out.append
    op = " open" if for_print else ""
    a(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
      f'<title>CSEF dashboard: {e(product)}</title><style>{CSS}</style></head>'
      f'<body data-product="{e(product)}"><div class="wrap">')
    a('<div class="top"><div>')
    a(f'<h1>CSEF pre-compliance dashboard</h1><p class="sub"><strong>{e(product)}</strong> · scanned {e(gen)} · '
      f'Child-Safe EdTech Framework v{e(d["tool"]["standard_version"])} · {e(d["tool"]["name"])} {e(d["tool"]["version"])}</p></div>')
    if not for_print:
        a('<div class="btns"><button id="expand" type="button">Expand all</button><button id="collapse" type="button">Collapse all</button>'
          '<button id="print" type="button">Print / PDF</button></div>')
    a('</div>')
    a('<p class="disclaimer"><strong>Pre-compliance report, not legal advice or certification.</strong> Automated checks find technical '
      'signals in code and configuration. They cannot see contracts, legal bases or how the product is operated. Use this dashboard to '
      'prepare a review with your DPO and legal counsel.</p>')
    if not for_print:
        a('<nav class="toc" aria-label="Sections"><a href="#levels">Levels</a><a href="#bands">Age bands</a><a href="#scope">Scope</a>'
          '<a href="#comms">Communications</a><a href="#findings">Findings</a><a href="#human">Human checks</a><a href="#plan">Improvement plan</a>'
          '<a href="#counsel">For legal counsel</a><a href="#sources">Sources</a></nav>')

    # verdict
    c = model["counts"]
    a('<section class="panel"><div class="verdict">')
    a(f'<div class="vbox" style="{sev_vars(st_sev)};background:var(--cb);border:1px solid var(--c)">'
      f'<span class="small muted">At your chosen level</span>'
      f'<span class="big" style="color:var(--c)">{e(st_label)}</span>'
      f'<span>Level {level}: {e(LEVEL_NAMES[level])}'
      + (f' · minimum set by {e(d.get("minimum_level_by", ""))}' if d.get("minimum_level", 1) > 1 else "") + '</span></div>')
    a('<div class="tiles">')
    for s in ("BLOCK", "REVIEW", "WARN", "HUMAN", "NEXT", "WAIVED"):
        a(f'<div class="tile" style="{sev_vars(s)};background:var(--cb);border-color:var(--c)"><b style="color:var(--c)">{c.get(s, 0)}</b>'
          f'<span><strong>{e(SEV[s][0])}</strong> · {e(SEV[s][1])}</span></div>')
    a('</div></div></section>')

    # levels
    a('<section class="panel" id="levels"><h2>Where you stand at each level</h2>'
      '<p class="muted small">Each level includes the ones below it. Signals for higher levels never fail your build; they show what it takes to go further.</p>'
      '<div class="ladder">')
    for lv in model["levels"]:
        L = lv["level"]
        sl, ss = STATUS[lv["status"]]
        pct = round(100 * lv["clean"] / lv["rules"]) if lv["rules"] else 100
        tags = ""
        if lv["chosen"]:
            tags += ' <span class="tag" style="color:var(--c)">Chosen</span>'
        if lv["minimum"]:
            tags += ' <span class="tag" style="color:var(--c)">Policy minimum</span>'
        a(f'<div class="lvl{" chosen" if lv["chosen"] else ""}" style="{lvl_vars(L)}">'
          f'<div class="name">Level {L}: {e(LEVEL_NAMES[L])}{tags}</div>'
          f'<p class="muted small" style="margin:4px 0 8px">{e(LEVEL_DESC[L])}</p>'
          f'<span class="pill" style="{sev_vars(ss)}"><span class="dot"></span>{e(sl)}</span>'
          f'<div class="bar" style="{lvl_vars(L)}"><i style="width:{pct}%"></i></div>'
          f'<span class="small muted">{lv["clean"]} of {lv["rules"]} rules with no automated issue</span>'
          f'<div class="stats">'
          f'<div style="color:var(--BLOCK)"><b>{len(lv["block"])}</b>blocking</div>'
          f'<div style="color:var(--REVIEW)"><b>{len(lv["review"])}</b>review</div>'
          f'<div style="color:var(--WARN)"><b>{len(lv["warn"])}</b>warnings</div>'
          f'<div style="color:var(--HUMAN)"><b>{len(lv["human"])}</b>human</div></div></div>')
    a('</div></section>')

    # bands
    a('<section class="panel" id="bands"><h2>Age bands</h2>'
      '<p class="muted small">Highlighted bands are declared in the product manifest. Each band lists rules written specifically for it, and open issues on rules that apply to it.</p>'
      '<div class="bands">')
    for i, b in enumerate(model["bands"], 1):
        a(f'<div class="band{" on" if b["declared"] else ""}" style="--c:var(--{b["band"]})">'
          f'<div class="bn">{b["band"]} · ages {b["ages"]}</div>'
          f'<div class="small">{"Declared" if b["declared"] else "Not declared"}</div>'
          f'<div class="small muted">{len(b["specific"])} band-specific rule(s)</div>'
          f'<div class="small">{len(b["issues"]) if b["declared"] else "–"} open issue(s)</div></div>')
    a('</div></section>')

    # scope
    def val(x):
        if x is None or x == [] or x == {}:
            return "not declared"
        if isinstance(x, list):
            return ", ".join(map(str, x))
        if isinstance(x, dict):
            return ", ".join(f"{k}: {v}" for k, v in x.items())
        return str(x)
    prof = {"A": "A Educational game", "B": "B Game-based application", "C": "C Gamified application"}
    rows = [
        ("Profiles", "Core + " + (", ".join(prof.get(p, p) for p in d["profiles"]) or "none")),
        ("Age bands", ", ".join(f"{b} ({dict(BANDS)[b]})" for b in d["age_bands"])),
        ("Context of use", val(m.get("context"))),
        ("GDPR role", val(m.get("gdpr_role"))),
        ("EU KIDS Act scope", val((m.get("legal_scope") or {}).get("kids_act"))),
        ("Jurisdictions", val(m.get("jurisdictions"))),
        ("Features declared", val(m.get("features"))),
        ("Monetisation", val(m.get("monetisation"))),
        ("Packs", ", ".join(f'{p["title"]} v{p["version"]}' for p in d.get("packs", [])) or "none"),
        ("Manifest last reviewed", val(m.get("last_review"))),
    ]
    a('<section class="panel" id="scope"><h2>Scope</h2><div class="scope">')
    for k, v in rows:
        a(f'<div><span class="muted">{e(k)}</span><span>{e(v)}</span></div>')
    a('</div>')
    if d.get("parameters"):
        a('<p class="small muted" style="margin-top:10px">Pack parameters: ' + e("; ".join(f"{k} = {v}" for k, v in d["parameters"].items())) + '</p>')
    a('</section>')

    # communications
    inv = d.get("communications") or {}
    a('<section class="panel" id="comms"><h2>Communications</h2>'
      '<p class="muted small">Ways children can communicate, found in code, and the safeguards around them. A safeguard not found may '
      'still be configured in a service dashboard or a backend outside the repository: confirm by hand.</p>')
    if not inv.get("has_communication"):
        a('<p>No communication channels found in code. If the product has chat, multiplayer or comments through a service configured '
          'elsewhere, declare it in csef.yaml.</p>')
    else:
        a('<table><thead><tr><th>Channel</th><th>Kind</th><th>Evidence</th></tr></thead><tbody>')
        for c in inv["channels"]:
            a(f'<tr><td><strong>{e(c["name"])}</strong></td><td>{e(c["kind"])}</td><td>'
              + " ".join(f'<span class="loc">{e(x)}</span>' for x in c["evidence"][:3]) + '</td></tr>')
        a('</tbody></table><h3 style="margin-top:14px">Safeguards</h3><div class="tiles" style="margin-top:8px">')
        for k, v in inv["safeguards"].items():
            ok = bool(v["evidence"])
            sv = "OK" if ok else "REVIEW"
            a(f'<div class="tile" style="{sev_vars(sv)};background:var(--cb);border-color:var(--c)">'
              f'<b style="color:var(--c);font-size:1rem">{"Found" if ok else "Not found"}</b><span><strong>{e(v["label"])}</strong>'
              + (f'<br><span class="loc">{e(v["evidence"][0])}</span>' if ok else "") + '</span></div>')
        a('</div>')
        risks = [v for v in inv["risks"].values() if v["evidence"]]
        if risks:
            a('<h3 style="margin-top:14px">Risk signals</h3><table><tbody>')
            for v in risks:
                a(f'<tr><td style="color:var(--BLOCK)"><strong>{e(v["label"])}</strong></td><td>'
                  + " ".join(f'<span class="loc">{e(x)}</span>' for x in v["evidence"][:3]) + '</td></tr>')
            a('</tbody></table>')
    a('</section>')

    # findings
    a('<section class="panel" id="findings"><h2>Findings</h2><p class="muted small">Grouped by rule. Open a card for locations, the reason and the sources.</p>')
    if not for_print:
        a('<div class="filters" role="group" aria-label="Filter findings">')
        for s in ("BLOCK", "REVIEW", "WARN", "NEXT", "WAIVED"):
            chk = "" if s in ("WAIVED",) else " checked"
            a(f'<label class="fchip" style="{sev_vars(s)}"><input type="checkbox" data-sev-filter value="{s}"{chk}> {e(SEV[s][0])}</label>')
        a('<select id="flevel" aria-label="Up to level"><option value="3">All levels</option><option value="1">Level 1 only</option>'
          '<option value="2">Levels 1 and 2</option></select>'
          '<input id="q" type="search" placeholder="Search rule, file or text" aria-label="Search findings"><span id="fcount" class="small muted"></span></div>')
    if not model["fgroups"]:
        a('<p>No automated findings.</p>')
    for g in model["fgroups"]:
        r = rules[g["rule_id"]]
        s = g["severity"]
        a(f'<details class="card" data-sev="{s}" data-tier="{r["tier"]}" style="{sev_vars(s)}"{op}><summary>'
          f'<span class="sev">{e(SEV[s][0])}</span><span class="rid">{e(r["id"])}</span><strong>{e(r["title"])}</strong>'
          f'<span class="lv" style="{lvl_vars(int(r["tier"]))}">L{r["tier"]} {e(r["level"])}</span>'
          + (' <span class="lv" style="--c:var(--BLOCK)">No-go</span>' if r.get("no_go") else "")
          + f'<span class="small muted">{len(g["items"])} location(s)</span></summary><div class="body">')
        a(f'<p>{e(" ".join(r["requirement"].split()))}</p><ul class="locs">')
        for f in g["items"][:15]:
            loc = f'{f["path"]}{":" + str(f["line"]) if f.get("line") else ""}' if f.get("path") else "repository"
            ev = f' <code>{e(f["evidence"])}</code>' if f.get("evidence") else ""
            nt = f' <em class="muted">{e(f["note"])}</em>' if f.get("note") else ""
            a(f'<li><span class="loc">{e(loc)}</span>{ev}{nt}</li>')
        if len(g["items"]) > 15:
            a(f'<li class="muted">and {len(g["items"]) - 15} more</li>')
        a('</ul>')
        a(f'<p><strong>Why.</strong> {e(" ".join(r["rationale"].split()))}</p>')
        a(f'<p><strong>How to improve.</strong> {e(" ".join(r.get("improvement", "").split()))}</p>')
        for n in r.get("notes", []):
            a(f'<p class="note">{e(n)}</p>')
        a(f'<p class="src small"><strong>Sources.</strong> {src_links(model, r.get("sources", []))}</p></div></details>')
    a('</section>')

    # human checks
    hum = [h for h in d["human_checks"] if not h["next_level"]]
    a('<section class="panel" id="human"><h2>Human checks</h2>'
      '<p class="muted small">These rules apply but cannot be verified in code. Tick each one you can evidence and note where the evidence is.'
      + ('' if for_print else ' Your ticks are saved in this browser only. <button id="dlchecks" type="button">Download as CSV</button> <span id="hc-progress" class="small"></span>')
      + '</p><table class="check"><thead><tr><th></th><th>Rule</th><th>What to confirm</th><th>Evidence / note</th></tr></thead><tbody>')
    for h in sorted(hum, key=lambda h: (rules[h["rule_id"]]["tier"], h["rule_id"])):
        r = rules[h["rule_id"]]
        a(f'<tr><td><input type="checkbox" data-check="{e(r["id"])}" aria-label="Confirmed {e(r["id"])}"></td>'
          f'<td><span class="rid">{e(r["id"])}</span><br><strong>{e(r["title"])}</strong><br>'
          f'<span class="lv" style="{lvl_vars(int(r["tier"]))}">L{r["tier"]} {e(r["level"])}</span></td>'
          f'<td>{e(" ".join(r["requirement"].split()))}<div class="src small">{src_links(model, r.get("sources", []))}</div></td>'
          f'<td><input type="text" data-note="{e(r["id"])}" aria-label="Evidence for {e(r["id"])}" placeholder="Link or note"></td></tr>')
    a('</tbody></table></section>')

    # plan
    a('<section class="panel" id="plan"><h2>Improvement plan</h2><p class="muted small">Ordered by severity, then effort (quick wins first).</p>')
    titles = {"BLOCK": "Fix before release", "REVIEW": "Confirm and fix", "WARN": "Recommended at this level",
              "HUMAN": "Verify (cannot be checked in code)", "NEXT": "To reach the next level"}
    n = 0
    for s in ("BLOCK", "REVIEW", "WARN", "HUMAN", "NEXT"):
        items = [i for i in d["improvements"] if i["severity"] == s]
        if not items:
            continue
        a(f'<h3 style="margin-top:14px;color:var(--{s})">{e(titles[s])} ({len(items)})</h3>')
        for i in items:
            n += 1
            locs = ", ".join(i["locations"][:4]) + (f" and {len(i['locations']) - 4} more" if len(i["locations"]) > 4 else "")
            a(f'<div class="imp" style="{sev_vars(s)}"><strong>{n}. {e(i["action"])}</strong><br>'
              f'<span class="small"><span class="rid">{e(i["rule_id"])}</span> {e(i["title"])} · '
              f'<span class="lv" style="{lvl_vars(int(i["tier"]))}">L{i["tier"]}</span> · effort {e(i["effort"])}'
              + (f' · <span class="loc">{e(locs)}</span>' if locs else "") + '</span></div>')
    a('</section>')

    # counsel
    a('<section class="panel" id="counsel"><h2>For legal counsel</h2>'
      '<p class="muted small">Points where a legal judgement is needed before release. Bring this section, the scope and the human checks to the review.</p>'
      '<table><thead><tr><th>Topic</th><th>Question</th></tr></thead><tbody>')
    for t, qtxt in model["counsel"]:
        a(f'<tr><td><strong>{e(t)}</strong></td><td>{e(qtxt)}</td></tr>')
    a('</tbody></table>')
    if model["lvl1"]:
        a('<h3 style="margin-top:14px">Level 1 (legal) rules needing confirmation</h3><table><thead><tr><th>Rule</th><th>Requirement</th><th>Legal sources</th></tr></thead><tbody>')
        for rid in model["lvl1"]:
            r = rules[rid]
            legal = [s for s in r.get("sources", []) if d["sources"].get(s, {}).get("type") in ("law", "law-pending", "policy")]
            a(f'<tr><td><span class="rid">{e(rid)}</span><br>{e(r["title"])}</td><td>{e(" ".join(r["requirement"].split()))}</td>'
              f'<td class="src">{src_links(model, legal)}</td></tr>')
        a('</tbody></table>')
    if model["proposals"]:
        a('<h3 style="margin-top:14px">Proposals and pending law this review relies on</h3><ul>')
        for sid in model["proposals"]:
            s = d["sources"][sid]
            a(f'<li><strong>{e(sid)}</strong> {e(s["title"])}. <em>{e(s.get("status", ""))}</em></li>')
        a('</ul>')
    if model["waived"]:
        a('<h3 style="margin-top:14px">Waivers in force</h3><ul>')
        for f in model["waived"]:
            a(f'<li><span class="rid">{e(f["rule_id"])}</span> {e(f.get("path") or "")}: {e(f.get("note") or "")}</li>')
        a('</ul>')
    a('</section>')

    # sources
    a('<section class="panel" id="sources"><h2>Sources</h2><p class="muted small">Every source cited by the rules in scope, with its status and the date it was last verified.</p>'
      '<table><thead><tr><th>Id</th><th>Source</th><th>Type</th><th>Status</th><th>Verified</th></tr></thead><tbody>')
    order = ["law", "law-pending", "proposal", "guidance", "standard", "policy", "literature", "news"]
    for sid, s in sorted(d["sources"].items(), key=lambda kv: (order.index(kv[1].get("type")) if kv[1].get("type") in order else 99, kv[0])):
        title = f'<a href="{e(s["url"])}">{e(s["title"])}</a>' if s.get("url") else e(s["title"])
        a(f'<tr><td class="rid">{e(sid)}</td><td>{title}</td><td><span class="typ">{e(TYPE_LABEL.get(s.get("type"), s.get("type", "")))}</span></td>'
          f'<td class="small">{e(s.get("status", ""))}</td><td class="small">{e(str(s.get("verified", "")))}</td></tr>')
    a('</tbody></table></section>')
    a(f'<p class="small muted" style="margin-top:18px">Generated {e(dt.date.today().isoformat())} from findings.json. '
      'Child-Safe EdTech Framework: standard content CC BY 4.0, code Apache 2.0.</p></div>')
    if not for_print:
        a(f'<script>{JS}</script>')
    a('</body></html>')
    return "".join(out)


# --------------------------------------------------------------------------- pdf
def find_chrome():
    for c in [os.environ.get("CHROME"), "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "msedge"]:
        if c and (shutil.which(c) or Path(c).exists()):
            return shutil.which(c) or c
    return None


def render_pdf(html_text: str, pdf_path: Path) -> str:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "print.html"
        src.write_text(html_text, encoding="utf-8")
        chrome = find_chrome()
        if chrome:
            cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                   f"--user-data-dir={td}/profile", f"--print-to-pdf={pdf_path}", src.as_uri()]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and pdf_path.exists():
                return "chrome"
        try:
            import weasyprint  # type: ignore
            weasyprint.HTML(string=html_text).write_pdf(str(pdf_path))
            return "weasyprint"
        except ImportError:
            pass
    raise RuntimeError("PDF export needs Chrome/Chromium (set CHROME=/path) or `pip install weasyprint`.")


# --------------------------------------------------------------------------- docx
HEX = {"BLOCK": "FDECEA", "REVIEW": "FFF1E0", "WARN": "FFF8D6", "HUMAN": "E8EFFF", "NEXT": "EEF0F3", "WAIVED": "E6F3EA",
       "OK": "E3F4EA", 1: "E1F1EC", 2: "E8EAFB", 3: "F3E8FA"}
INK = {"BLOCK": "B42318", "REVIEW": "B45309", "WARN": "8A6D00", "HUMAN": "1D4ED8", "NEXT": "5F6B7A", "WAIVED": "3F7A52",
       "OK": "1F7A4D", 1: "0F5C4D", 2: "3949AB", 3: "7B3FA0"}


def render_docx(model: dict, path: Path) -> None:
    try:
        from docx import Document
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Pt, RGBColor, Cm
    except ImportError:
        raise RuntimeError("DOCX export needs python-docx: pip install python-docx")

    d, rules, level = model["d"], model["rules"], model["level"]
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    for name, size in (("Title", 22), ("Heading 1", 15), ("Heading 2", 12.5)):
        doc.styles[name].font.name = "Calibri"
        doc.styles[name].font.size = Pt(size)

    def shade(cell, hexcol):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hexcol)
        tcPr.append(shd)

    def colored(par, text, key, bold=True):
        run = par.add_run(text)
        run.bold = bold
        run.font.color.rgb = RGBColor.from_string(INK[key])
        return run

    def table(headers, widths=None):
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]
            c.text = ""
            r = c.paragraphs[0].add_run(h)
            r.bold = True
            r.font.size = Pt(9.5)
            shade(c, "EDEFEA")
        if widths:
            t.autofit = False
            tblPr = t._tbl.tblPr
            for tag in ("w:tblW", "w:tblLayout"):
                for old in tblPr.findall(qn(tag)):
                    tblPr.remove(old)
            tw = OxmlElement("w:tblW")
            tw.set(qn("w:w"), str(int(sum(widths) * 567)))
            tw.set(qn("w:type"), "dxa")
            tblPr.append(tw)
            lay = OxmlElement("w:tblLayout")
            lay.set(qn("w:type"), "fixed")
            tblPr.append(lay)
            for i, w in enumerate(widths):
                t.columns[i].width = Cm(w)
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        return t

    def add_row(t, values, widths=None, fill=None):
        cells = t.add_row().cells
        for i, v in enumerate(values):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            if isinstance(v, tuple):
                colored(p, v[0], v[1])
            else:
                run = p.add_run(str(v))
                run.font.size = Pt(9.5)
            if widths:
                cells[i].width = Cm(widths[i])
        if fill:
            shade(cells[0], fill)
        return cells

    product = d.get("product") or "Product"
    doc.add_paragraph(f"CSEF pre-compliance report: {product}", style="Title")
    p = doc.add_paragraph()
    p.add_run(f"Scanned {d.get('generated', '')[:10]} · Child-Safe EdTech Framework v{d['tool']['standard_version']} · "
              f"{d['tool']['name']} {d['tool']['version']}").italic = True
    p = doc.add_paragraph()
    p.add_run("Pre-compliance report, not legal advice or certification. ").bold = True
    p.add_run("Automated checks find technical signals in code and configuration. They cannot see contracts, legal bases or how "
              "the product is operated. Use this document to prepare a review with your DPO and legal counsel.")

    sl, ss = STATUS[model["verdict"]]
    doc.add_heading("Summary", level=1)
    p = doc.add_paragraph("At the chosen level (Level %d, %s): " % (level, LEVEL_NAMES[level]))
    colored(p, sl, ss)
    if d.get("minimum_level", 1) > 1:
        doc.add_paragraph(f"Minimum level {d['minimum_level']} set by {d.get('minimum_level_by', '')}.")
    t = table(["Severity", "Rules", "Meaning"], [3, 1.6, 12])
    for s in ("BLOCK", "REVIEW", "WARN", "HUMAN", "NEXT", "WAIVED"):
        add_row(t, [(SEV[s][0], s), model["counts"].get(s, 0), SEV[s][1]], [3, 1.6, 12], HEX[s])

    doc.add_heading("Where you stand at each level", level=1)
    t = table(["Level", "Status", "Rules", "Blocking", "Review", "Warnings", "Human"], [4.6, 3.4, 1.5, 1.7, 1.6, 1.8, 1.6])
    for lv in model["levels"]:
        L = lv["level"]
        st_l, st_s = STATUS[lv["status"]]
        name = f"Level {L}: {LEVEL_NAMES[L]}" + (" (chosen)" if lv["chosen"] else "")
        add_row(t, [(name, L), (st_l, st_s), lv["rules"], len(lv["block"]), len(lv["review"]), len(lv["warn"]), len(lv["human"])],
                [4.6, 3.4, 1.5, 1.7, 1.6, 1.8, 1.6], HEX[L])

    doc.add_heading("Age bands", level=1)
    t = table(["Band", "Ages", "Declared", "Band-specific rules", "Open issues"], [2, 2, 2.4, 4, 3])
    for b in model["bands"]:
        add_row(t, [b["band"], b["ages"], "Yes" if b["declared"] else "No", len(b["specific"]),
                    len(b["issues"]) if b["declared"] else "-"], [2, 2, 2.4, 4, 3])

    m = model["manifest"]
    doc.add_heading("Scope", level=1)
    prof = {"A": "A Educational game", "B": "B Game-based application", "C": "C Gamified application"}
    t = table(["Item", "Value"], [5, 11.5])
    for k, v in [("Profiles", "Core + " + ", ".join(prof.get(x, x) for x in d["profiles"])),
                 ("Age bands", ", ".join(d["age_bands"])), ("Context", m.get("context") or "not declared"),
                 ("GDPR role", m.get("gdpr_role") or "not declared"),
                 ("EU KIDS Act scope", (m.get("legal_scope") or {}).get("kids_act") or "not declared"),
                 ("Jurisdictions", ", ".join(map(str, m.get("jurisdictions") or [])) or "not declared"),
                 ("Features", ", ".join(m.get("features") or []) or "not declared"),
                 ("Packs", ", ".join(f"{x['title']} v{x['version']}" for x in d.get("packs", [])) or "none")]:
        add_row(t, [k, v], [5, 11.5])

    inv = d.get("communications") or {}
    doc.add_heading("Communications", level=1)
    if not inv.get("has_communication"):
        doc.add_paragraph("No communication channels found in code.")
    else:
        t = table(["Channel", "Kind", "Evidence"], [4, 3.5, 9])
        for c in inv["channels"]:
            add_row(t, [c["name"], c["kind"], ", ".join(c["evidence"][:3])], [4, 3.5, 9])
        doc.add_paragraph("")
        t = table(["Safeguard", "Found in code", "Evidence"], [6, 3, 7.5])
        for v in inv["safeguards"].values():
            ok = bool(v["evidence"])
            add_row(t, [v["label"], ("Found", "OK") if ok else ("Not found", "REVIEW"), ", ".join(v["evidence"][:2])], [6, 3, 7.5])
        risks = [v for v in inv["risks"].values() if v["evidence"]]
        if risks:
            doc.add_paragraph("")
            t = table(["Risk signal", "Evidence"], [6, 10.5])
            for v in risks:
                add_row(t, [(v["label"], "BLOCK"), ", ".join(v["evidence"][:3])], [6, 10.5])
        doc.add_paragraph("A safeguard not found may still be configured in a service dashboard or a backend outside the repository. Confirm by hand.").italic = True

    doc.add_heading("Findings", level=1)
    if not model["fgroups"]:
        doc.add_paragraph("No automated findings.")
    for g in model["fgroups"]:
        r = rules[g["rule_id"]]
        s = g["severity"]
        h = doc.add_paragraph(style="Heading 2")
        colored(h, f"[{SEV[s][0]}] ", s)
        h.add_run(f"{r['id']}: {r['title']}")
        doc.add_paragraph(f"{r['level']}, Level {r['tier']} ({LEVEL_NAMES[int(r['tier'])]})" + (". No-go." if r.get("no_go") else ".")).italic = True
        doc.add_paragraph(" ".join(r["requirement"].split()))
        for f in g["items"][:10]:
            loc = f'{f["path"]}{":" + str(f["line"]) if f.get("line") else ""}' if f.get("path") else "repository"
            doc.add_paragraph(f"{loc}  {f.get('evidence') or ''}", style="List Bullet")
        if len(g["items"]) > 10:
            doc.add_paragraph(f"and {len(g['items']) - 10} more locations", style="List Bullet")
        p = doc.add_paragraph()
        p.add_run("Why. ").bold = True
        p.add_run(" ".join(r["rationale"].split()))
        p = doc.add_paragraph()
        p.add_run("How to improve. ").bold = True
        p.add_run(" ".join(r.get("improvement", "").split()))
        for nte in r.get("notes", []):
            doc.add_paragraph(nte).italic = True
        p = doc.add_paragraph()
        p.add_run("Sources. ").bold = True
        p.add_run(", ".join(r.get("sources", [])))

    doc.add_heading("Human checks", level=1)
    doc.add_paragraph("These rules apply but cannot be verified in code. Record the evidence and who confirmed it.")
    t = table(["Rule", "What to confirm", "Confirmed by / evidence"], [4.2, 8.3, 4])
    for hc in sorted([h for h in d["human_checks"] if not h["next_level"]], key=lambda h: (rules[h["rule_id"]]["tier"], h["rule_id"])):
        r = rules[hc["rule_id"]]
        add_row(t, [f"{r['id']} (L{r['tier']} {r['level']})\n{r['title']}", " ".join(r["requirement"].split()), ""], [4.2, 8.3, 4], HEX[int(r["tier"])])

    doc.add_heading("Improvement plan", level=1)
    titles = {"BLOCK": "Fix before release", "REVIEW": "Confirm and fix", "WARN": "Recommended at this level",
              "HUMAN": "Verify (cannot be checked in code)", "NEXT": "To reach the next level"}
    for s in ("BLOCK", "REVIEW", "WARN", "HUMAN", "NEXT"):
        items = [i for i in d["improvements"] if i["severity"] == s]
        if not items:
            continue
        h = doc.add_paragraph(style="Heading 2")
        colored(h, f"{titles[s]} ({len(items)})", s)
        for i in items:
            p = doc.add_paragraph(style="List Number")
            p.add_run(i["action"]).bold = True
            p.add_run(f"  {i['rule_id']}, Level {i['tier']}, effort {i['effort']}.")

    doc.add_heading("For legal counsel", level=1)
    t = table(["Topic", "Question"], [4, 12.5])
    for k, v in model["counsel"]:
        add_row(t, [k, v], [4, 12.5])
    if model["lvl1"]:
        doc.add_heading("Level 1 (legal) rules needing confirmation", level=2)
        t = table(["Rule", "Requirement", "Legal sources"], [4, 9, 3.5])
        for rid in model["lvl1"]:
            r = rules[rid]
            legal = [s for s in r.get("sources", []) if d["sources"].get(s, {}).get("type") in ("law", "law-pending", "policy")]
            add_row(t, [f"{rid}\n{r['title']}", " ".join(r["requirement"].split()), ", ".join(legal)], [4, 9, 3.5])
    if model["proposals"]:
        doc.add_heading("Proposals and pending law relied on", level=2)
        for sid in model["proposals"]:
            s = d["sources"][sid]
            doc.add_paragraph(f"{sid}: {s['title']}. {s.get('status', '')}", style="List Bullet")

    doc.add_heading("Sources", level=1)
    order = ["law", "law-pending", "proposal", "guidance", "standard", "policy", "literature", "news"]
    for sid, s in sorted(d["sources"].items(), key=lambda kv: (order.index(kv[1].get("type")) if kv[1].get("type") in order else 99, kv[0])):
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"[{sid}] ").bold = True
        p.add_run(f"{s['title']}. {TYPE_LABEL.get(s.get('type'), s.get('type', ''))}. {s.get('status', '')}. "
                  f"Verified {s.get('verified', '')}." + (f" {s['url']}" if s.get("url") else ""))
    doc.save(str(path))


# --------------------------------------------------------------------------- cli
def export(input_path: Path, formats: list[str], out_dir: Path | None = None) -> dict:
    d = json.loads(Path(input_path).read_text(encoding="utf-8"))
    model = build_model(d)
    out = Path(out_dir) if out_dir else Path(input_path).parent
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    if "html" in formats:
        p = out / "dashboard.html"
        p.write_text(render_html(model), encoding="utf-8")
        written["html"] = p
    if "pdf" in formats:
        p = out / "report.pdf"
        engine = render_pdf(render_html(model, for_print=True), p)
        written["pdf"] = p
        written["pdf_engine"] = engine
    if "docx" in formats:
        p = out / "report.docx"
        render_docx(model, p)
        written["docx"] = p
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export a CSEF scan to an interactive HTML dashboard, PDF and Word")
    ap.add_argument("--input", default="csef-report/findings.json", help="findings.json written by tooling/scan.py")
    ap.add_argument("--formats", default="html", help="comma-separated: html,pdf,docx")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)
    formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    bad = set(formats) - {"html", "pdf", "docx"}
    if bad:
        print(f"Unknown format(s): {', '.join(sorted(bad))}", file=sys.stderr)
        return 2
    try:
        written = export(Path(args.input), formats, Path(args.out_dir) if args.out_dir else None)
    except (RuntimeError, FileNotFoundError) as ex:
        print(f"csef export: {ex}", file=sys.stderr)
        return 1
    for k, v in written.items():
        if k != "pdf_engine":
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
