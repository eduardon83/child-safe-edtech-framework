#!/usr/bin/env python3
"""Serious-game quality pre-check.

Maps three inputs to the 22 serious-game quality criteria in framework/serious-games/criteria.yaml:
  1. CSEF scan results (findings.json, or a fresh scan of the repo),
  2. Compass results (compass.json, optional), and
  3. the team's own statements with evidence (serious_game.claims in csef.yaml).

The output is a pre-check for a quality label, not the label. Usage:

  python3 tooling/precheck.py --repo path/to/product [--findings dist/findings.json] [--compass compass.json]
                              [--out-dir dist/precheck] [--formats md,html,json] [--fail-on missing]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scan  # noqa: E402
import brand  # noqa: E402

TOOL = "csef-precheck"
GROUPS = {"serious": "Serious part", "game": "Game part", "balance": "Balance between serious and game part"}
STATUS = {"ready": "Ready", "partial": "Partial", "missing": "Missing", "issue": "CSEF issue"}
STATUS_ORDER = ["issue", "missing", "partial", "ready"]
COVERAGE = {"covered": "CSEF checks it", "partial": "CSEF checks part of it", "declaration": "Team statement needed",
            "tension": "CSEF sets limits for children"}
DISCLAIMER = ("This pre-check maps CSEF results and the team's own statements to the serious-game quality criteria of "
              "Caserman et al. (2020). It is not a quality label, and no labelling body issued or endorsed it.")
URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)


def default_root() -> Path:
    return scan.default_root()


def load_criteria(root: Path) -> dict:
    return scan.load_yaml(root / "framework" / "serious-games" / "criteria.yaml")


# --------------------------------------------------------------------------- inputs
def scan_dict(repo: Path, root: Path, manifest: dict, level: int | None) -> dict:
    """Run a CSEF scan and return the same structure as findings.json."""
    std = scan.load_standard(root)
    for p in scan.resolve_packs(repo, root, manifest, []):
        scan.apply_pack(std, p)
    lvl = max(level or int(manifest.get("compliance_level", 1)), std.minimum_level)
    res = scan.scan(repo, std, manifest, lvl)
    return json.loads(json.dumps(scan.to_json(std, manifest, res, scan.build_improvements(std, res)), default=str))


def rule_states(findings: dict) -> dict:
    """rule id -> ok | review | issue, for rules in scope. NEXT (next level) findings do not count."""
    states = {rid: "ok" for rid in findings.get("rules", {})}
    rank = {"ok": 0, "review": 1, "issue": 2}

    def bump(rid, st):
        if rid in states and rank[st] > rank[states[rid]]:
            states[rid] = st
    for f in findings.get("findings", []):
        sev = f.get("severity")
        if sev == "BLOCK":
            bump(f["rule_id"], "issue")
        elif sev in ("REVIEW", "WARN"):
            bump(f["rule_id"], "review")
    for h in findings.get("human_checks", []):
        if not h.get("next_level"):
            bump(h["rule_id"], "review")
    return states


def compass_levels(compass: dict | None) -> dict | None:
    if compass is None:
        return None
    return {t["id"]: int(t.get("level") or 0) for t in compass.get("targets", [])}


def claims_of(manifest: dict) -> dict:
    sg = manifest.get("serious_game") or {}
    raw = sg.get("claims") or {}
    if isinstance(raw, list):
        raw = {c.get("id"): c for c in raw if isinstance(c, dict)}
    out = {}
    for cid, c in raw.items():
        if isinstance(c, str):
            c = {"statement": c}
        ev = c.get("evidence") or []
        out[str(cid)] = {"statement": (c.get("statement") or "").strip(),
                         "evidence": [ev] if isinstance(ev, str) else list(ev)}
    return out


def evidence_found(repo: Path, ref: str) -> bool | None:
    """True or False for a local path; None for a URL (not checked offline)."""
    if URL_RE.match(ref):
        return None
    return (repo / ref.split("#", 1)[0]).exists()


# --------------------------------------------------------------------------- assessment
def assess(repo: Path, root: Path, manifest: dict, findings: dict, compass: dict | None) -> dict:
    crit = load_criteria(root)
    states = rule_states(findings)
    levels = compass_levels(compass)
    claims = claims_of(manifest)
    titles = {rid: r.get("title", "") for rid, r in findings.get("rules", {}).items()}
    target_titles = {t["id"]: t.get("title", "") for t in (compass or {}).get("targets", [])}
    out = []
    for c in crit["criteria"]:
        reasons_missing, reasons_partial, issues = [], [], []
        rules = []
        for rid in c.get("rules") or []:
            rid = scan.ALIASES.get(rid, rid)
            if rid not in states:
                continue
            st = states[rid]
            rules.append({"id": rid, "title": titles.get(rid, ""), "status": st})
            if st == "issue":
                issues.append(rid)
            elif st == "review":
                reasons_partial.append(f"{rid} needs review in the CSEF report")
        if issues:
            reasons_missing.insert(0, "CSEF blocking finding: " + ", ".join(issues))
        comp = []
        for tid, need in (c.get("compass") or {}).items():
            got = None if levels is None else levels.get(tid, 0)
            comp.append({"id": tid, "title": target_titles.get(tid, ""), "level": got, "needed": need})
            if got is not None and got < need:
                reasons_missing.append(f"Compass {tid} at level {got}, needs {need}")
        if comp and levels is None:
            reasons_partial.append("Compass not run (" + ", ".join(t["id"] for t in comp) + ")")
        claim = claims.get(c["id"])
        cl = None
        if claim:
            ev = [{"ref": e, "found": evidence_found(repo, e)} for e in claim["evidence"]]
            cl = {"statement": claim["statement"], "evidence": ev}
            if c.get("declare") and not claim["statement"]:
                reasons_missing.append("statement missing")
            if c.get("declare") and not ev:
                reasons_partial.append("statement has no evidence")
            for e in ev:
                if e["found"] is False:
                    reasons_partial.append(f"evidence not found: {e['ref']}")
        elif c.get("declare"):
            reasons_missing.append(f"statement with evidence missing (serious_game.claims.{c['id']})")
        if not rules and not comp and not c.get("declare") and not claim:
            reasons_partial.append("no CSEF rule in scope; add a statement with evidence")
        status = "issue" if issues else "missing" if reasons_missing else "partial" if reasons_partial else "ready"
        out.append({**{k: c.get(k) for k in ("id", "group", "aspect", "asks", "coverage", "csef_note")},
                    "status": status, "reasons": reasons_missing + reasons_partial,
                    "rules": rules, "compass": comp, "claim": cl, "evidence_kinds": c.get("evidence") or []})
    summary = {s: sum(1 for x in out if x["status"] == s) for s in STATUS_ORDER}
    blocking = sum(1 for f in findings.get("findings", []) if f.get("severity") == "BLOCK")
    review = sum(1 for f in findings.get("findings", []) if f.get("severity") in ("REVIEW", "WARN"))
    return {
        "format": 1,
        "tool": {"name": TOOL, "version": scan.TOOL_VERSION},
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "product": manifest.get("product"),
        "characterizing_goal": (manifest.get("serious_game") or {}).get("characterizing_goal"),
        "basis": {"criteria_version": crit.get("version"), "source": crit.get("basis"),
                  "reference": "Caserman P. et al. (2020). Quality criteria for serious games: serious part, game part, "
                               "and balance. JMIR Serious Games 8(3):e19037. doi:10.2196/19037"},
        "disclaimer": DISCLAIMER,
        "scan": {"tool": findings.get("tool"), "level": findings.get("level"), "blocking": blocking, "review": review,
                 "generated": findings.get("generated")},
        "compass_run": compass is not None,
        "summary": summary,
        "criteria": out,
    }


# --------------------------------------------------------------------------- output
def render_md(m: dict) -> str:
    s = m["summary"]
    L = [f"# Serious-game quality pre-check: {m['product'] or 'product'}", "",
         f"*{m['disclaimer']}*", "",
         f"Generated {m['generated']} by {m['tool']['name']} {m['tool']['version']}. "
         f"Criteria: {m['basis']['reference']}", ""]
    if m.get("characterizing_goal"):
        L += [f"**Characterizing goal.** {m['characterizing_goal']}", ""]
    sc = m["scan"]
    L += [f"**Summary.** {s['ready']} ready, {s['partial']} partial, {s['missing']} missing, {s['issue']} with a CSEF issue "
          f"(of {len(m['criteria'])}). CSEF scan at level {sc['level']}: {sc['blocking']} blocking, {sc['review']} to review."
          + ("" if m["compass_run"] else " Compass not run."), ""]
    for g, gname in GROUPS.items():
        L += [f"## {gname}", "", "| Criterion | Status | CSEF coverage | What is missing |", "|---|---|---|---|"]
        for c in [x for x in m["criteria"] if x["group"] == g]:
            why = "; ".join(c["reasons"]) or "nothing"
            L.append(f"| {c['id']} {c['aspect']} | {STATUS[c['status']]} | {COVERAGE[c['coverage']]} | {why} |")
        L.append("")
    L += ["## Details", ""]
    for c in m["criteria"]:
        L += [f"### {c['id']} {c['aspect']} · {STATUS[c['status']]}", "", c["asks"], ""]
        if c.get("csef_note"):
            L += [f"*For children, CSEF applies:* {c['csef_note']}", ""]
        if c["rules"]:
            L.append("CSEF rules: " + ", ".join(f"{r['id']} ({r['status']})" for r in c["rules"]))
        if c["compass"]:
            L.append("Compass: " + ", ".join(f"{t['id']} (level {'not run' if t['level'] is None else t['level']}, "
                                             f"needs {t['needed']})" for t in c["compass"]))
        if c["claim"]:
            L.append(f"Statement: {c['claim']['statement'] or '(empty)'}")
            for e in c["claim"]["evidence"]:
                mark = {True: "found", False: "NOT FOUND", None: "link"}[e["found"]]
                L.append(f"- Evidence: {e['ref']} ({mark})")
        elif c["evidence_kinds"]:
            L.append("Evidence that fits: " + ", ".join(c["evidence_kinds"]))
        L.append("")
    return "\n".join(L).rstrip() + "\n"


def render_html(m: dict) -> str:
    e = html.escape
    pill = {"ready": "teal", "partial": "sun", "missing": "coral", "issue": "coral"}
    s = m["summary"]
    rows = []
    for g, gname in GROUPS.items():
        rows.append(f'<h2>{e(gname)}</h2><table><thead><tr><th>Criterion</th><th>Status</th><th>CSEF coverage</th>'
                    f'<th>What is missing</th></tr></thead><tbody>')
        for c in [x for x in m["criteria"] if x["group"] == g]:
            note = f'<div class="note">For children: {e(c["csef_note"])}</div>' if c.get("csef_note") else ""
            rows.append(f'<tr><td><strong>{e(c["id"])}</strong> {e(c["aspect"])}<div class="asks">{e(c["asks"])}</div>{note}</td>'
                        f'<td><span class="pill {pill[c["status"]]}">{STATUS[c["status"]]}</span></td>'
                        f'<td>{e(COVERAGE[c["coverage"]])}</td><td>{e("; ".join(c["reasons"]) or "Nothing")}</td></tr>')
        rows.append("</tbody></table>")
    goal = f'<p><strong>Characterizing goal.</strong> {e(m["characterizing_goal"])}</p>' if m.get("characterizing_goal") else ""
    css = brand.tokens_css() + brand.BASE_CSS + """
body{margin:0;background:var(--c-paper);color:var(--c-ink);font-family:var(--font);line-height:1.5}
main{max-width:1040px;margin:0 auto;padding:28px 20px 60px}
.disclaimer{background:var(--c-sun-bg);border-left:4px solid var(--c-sun);padding:10px 14px;border-radius:6px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}
.card{background:var(--c-panel);border:1px solid var(--c-line);border-radius:10px;padding:12px 14px}
.card b{display:block;font-family:var(--font-display);font-size:1.8rem}
table{width:100%;border-collapse:collapse;background:var(--c-panel);border:1px solid var(--c-line);border-radius:10px;margin:8px 0 20px}
th,td{text-align:left;vertical-align:top;padding:10px 12px;border-bottom:1px solid var(--c-line);font-size:.93rem}
th{font-weight:600;color:var(--c-ink2)}
.asks{color:var(--c-ink2);font-size:.86rem;margin-top:4px}.note{font-size:.84rem;margin-top:6px;color:var(--c-indigo-t)}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.82rem;font-weight:600;white-space:nowrap}
.pill.teal{background:var(--c-teal-bg);color:var(--c-teal-t)}.pill.sun{background:var(--c-sun-bg);color:var(--c-sun-t)}
.pill.coral{background:var(--c-coral-bg);color:var(--c-coral-t)}
@media (max-width:700px){.cards{grid-template-columns:repeat(2,1fr)}}
"""
    sc = m["scan"]
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Serious-game pre-check: {e(m["product"] or "")}</title>{brand.head()}<style>{css}</style></head><body>'
            f'<div class="csef-stripe"></div><main>{brand.logo("lockup", 36)}'
            f'<h1>Serious-game quality pre-check</h1><p><strong>{e(m["product"] or "")}</strong> · generated {e(m["generated"])}</p>'
            f'<p class="disclaimer">{e(m["disclaimer"])}</p>{goal}'
            f'<div class="cards"><div class="card"><b>{s["ready"]}</b>Ready</div><div class="card"><b>{s["partial"]}</b>Partial</div>'
            f'<div class="card"><b>{s["missing"]}</b>Missing</div><div class="card"><b>{s["issue"]}</b>CSEF issue</div></div>'
            f'<p>CSEF scan at level {sc["level"]}: {sc["blocking"]} blocking, {sc["review"]} to review.'
            f'{"" if m["compass_run"] else " Compass not run."}</p>'
            + "".join(rows) +
            f'<p class="asks">Criteria: {e(m["basis"]["reference"])}</p></main></body></html>')


def write_outputs(m: dict, out: Path, formats: list[str]) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    if "json" in formats:
        p = out / "precheck.json"; p.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8"); paths.append(p)
    if "md" in formats:
        p = out / "precheck.md"; p.write_text(render_md(m), encoding="utf-8"); paths.append(p)
    if "html" in formats:
        p = out / "precheck.html"; p.write_text(render_html(m), encoding="utf-8"); paths.append(p)
    return paths


def run(repo: Path, root: Path, manifest_path: str | None = None, findings_path: str | None = None,
        compass_path: str | None = None, level: int | None = None) -> tuple[dict, dict]:
    mpath = scan.find_manifest(repo, manifest_path)
    if not mpath or not mpath.exists():
        raise SystemExit(f"{TOOL}: no csef.yaml found in {repo}")
    manifest = scan.load_yaml(mpath) or {}
    scan.load_standard(root)  # fills scan.ALIASES
    findings = (json.loads(Path(findings_path).read_text(encoding="utf-8")) if findings_path
                else scan_dict(repo, root, manifest, level))
    compass = json.loads(Path(compass_path).read_text(encoding="utf-8")) if compass_path else None
    return assess(repo, root, manifest, findings, compass), findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Serious-game quality pre-check (not a label).")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--manifest")
    ap.add_argument("--findings", help="findings.json from scan.py (default: run a scan)")
    ap.add_argument("--compass", help="compass.json from compass.py (optional)")
    ap.add_argument("--level", type=int, choices=[1, 2, 3])
    ap.add_argument("--framework-root", default=None)
    ap.add_argument("--out-dir", default="dist/precheck")
    ap.add_argument("--formats", default="md,html,json")
    ap.add_argument("--fail-on", choices=["none", "issue", "missing"], default="none")
    a = ap.parse_args(argv)
    root = Path(a.framework_root) if a.framework_root else default_root()
    m, _ = run(Path(a.repo), root, a.manifest, a.findings, a.compass, a.level)
    paths = write_outputs(m, Path(a.out_dir), [f.strip() for f in a.formats.split(",")])
    s = m["summary"]
    print(f"{TOOL}: {s['ready']} ready, {s['partial']} partial, {s['missing']} missing, {s['issue']} CSEF issue. "
          + ", ".join(str(p) for p in paths))
    if a.fail_on == "issue" and s["issue"]:
        return 1
    if a.fail_on == "missing" and (s["issue"] or s["missing"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
