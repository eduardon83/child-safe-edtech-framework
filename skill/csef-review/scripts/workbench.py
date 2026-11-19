#!/usr/bin/env python3
"""CSEF Workbench: run the tools that do not read code, on a product description and its documents.

This is the engine behind https://csef.kendirstudios.pt/workbench/, where designers, decision makers and
researchers add their files in the browser and the tools run there (Pyodide), with nothing uploaded. It can also
run on a computer, for testing or for a team without the website:

  python3 tooling/workbench.py --work my-product --tools describe,compass,precheck,package --out-dir csef-workbench

Work folder: csef.yaml at the top; documents anywhere below it (paths in csef.yaml such as docs/dpia.md are
resolved from the top). Optional inputs: --coc (a code of conduct), --events and --catalogue (an OGD event file
and its catalogue), --feed (a feed folder or zip).

Tools:
  describe   description check: csef.yaml and the files it links, without code (scan.py --description-only)
  compass    Literacy Compass on the documents
  precheck   serious-game pre-check (uses describe and compass when they ran)
  package    metadata export and label package
  coc        code-of-conduct comparison
  events     event file check against the child-safe profile and the catalogue
  feed       build an open evidence feed from the event file (thresholds applied)
  feedcheck  check an evidence feed before publishing or showing it

Licence: Apache-2.0
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import traceback
import zipfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import scan  # noqa: E402

TOOLS = ["describe", "compass", "precheck", "package", "coc", "events", "feed", "feedcheck"]
TITLES = {
    "describe": "Description check", "compass": "Literacy Compass", "precheck": "Serious-game pre-check",
    "package": "Label package", "coc": "Code-of-conduct comparison", "events": "Event file check",
    "feed": "Open evidence feed", "feedcheck": "Evidence feed check",
}
DOC_EXT = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf", ".docx", ".json", ".po", ".csv", ".arb", ".strings"}
FEATURES = ["accounts", "multiplayer", "chat", "ugc", "social", "notifications", "streaks", "leaderboards", "purchases",
            "assessment", "ai_generative", "ai_assessment", "ai_adaptive", "recommender", "survey"]


# --------------------------------------------------------------------------- product description form
def manifest_to_form(text: str) -> dict:
    """The fields of csef.yaml the Workbench form shows. Unknown keys stay in the YAML untouched."""
    m = yaml.safe_load(text or "") or {}
    dist = (m.get("distribution") or [{}])[0] or {}
    dc = m.get("data_collection") or {}
    oe = dc.get("open_evidence") or {}
    md = m.get("metadata") or {}
    return {
        "product": m.get("product", ""), "description": m.get("description", ""),
        "profiles": m.get("profiles") or [], "age_bands": m.get("age_bands") or [],
        "compliance_level": int(m.get("compliance_level") or 2),
        "jurisdictions": ", ".join(str(j) for j in (m.get("jurisdictions") or ["EU"])),
        "context": m.get("context", "school"), "channel": dist.get("channel", "school"),
        "operated_by": dist.get("operated_by", "school"),
        "kids_act": (m.get("legal_scope") or {}).get("kids_act", "unknown"),
        "gdpr_role": m.get("gdpr_role", ""), "features": scan.expand_features(m.get("features") or []),
        "monetisation": m.get("monetisation", "none"),
        "ai_act_class": (m.get("ai") or {}).get("act_class", "none"),
        "logs_events": str(dc.get("event_standard", "")) if dc else "",
        "event_catalogue": dc.get("event_catalogue", ""),
        "purposes": dc.get("purposes") or [],
        "open_evidence": bool(oe), "collected_under": oe.get("collected_under", ""),
        "keywords": ", ".join(md.get("keywords") or []),
        "languages": ", ".join(md.get("languages") or []),
    }


def form_to_manifest(text: str, f: dict) -> str:
    """Write the form values into csef.yaml, keeping every other key."""
    m = yaml.safe_load(text or "") or {}
    m.setdefault("cses_version", "0.1")

    def put(key, val):
        if val in (None, "", []):
            m.pop(key, None)
        else:
            m[key] = val

    put("product", (f.get("product") or "").strip())
    put("description", (f.get("description") or "").strip())
    put("profiles", [p for p in ("A", "B", "C") if p in (f.get("profiles") or [])])
    put("age_bands", [b for b in scan.BANDS if b in (f.get("age_bands") or [])])
    m["compliance_level"] = int(f.get("compliance_level") or 2)
    put("jurisdictions", [j.strip().upper() for j in str(f.get("jurisdictions") or "").replace(";", ",").split(",") if j.strip()])
    put("context", f.get("context"))
    if f.get("channel"):
        dist = m.get("distribution") or [{}]
        dist[0] = dict(dist[0] or {}, channel=f["channel"], operated_by=f.get("operated_by") or "school")
        m["distribution"] = dist
    ls = m.get("legal_scope") or {}
    ls["kids_act"] = f.get("kids_act") or "unknown"
    ls.setdefault("dsa_online_platform", False)
    m["legal_scope"] = ls
    put("gdpr_role", f.get("gdpr_role"))
    put("features", [x for x in FEATURES if x in (f.get("features") or [])])
    put("monetisation", f.get("monetisation") or "none")
    ai = m.get("ai") or {}
    ai["act_class"] = f.get("ai_act_class") or "none"
    ai.setdefault("inventory", None)
    m["ai"] = ai
    les = f.get("logs_events")
    if les:
        dc = m.get("data_collection") or {}
        dc["event_standard"] = les
        if les != "none":
            if f.get("event_catalogue"):
                dc["event_catalogue"] = f["event_catalogue"]
            dc["purposes"] = [p for p in ("operation", "improvement", "evaluation", "research") if p in (f.get("purposes") or [])] or ["operation"]
            dc.setdefault("player_id", {"kind": "random", "scope": "product", "renews": "school_year"})
            dc.setdefault("cross_product_linking", False)
            dc.setdefault("detectors", "population_only")
            if "research" in dc["purposes"]:
                dc.setdefault("research", {"study_branch": "study", "agreement": None, "ethics_approval": None,
                                           "key_holder": "studio", "default_on": False})
            if f.get("open_evidence"):
                oe = dc.get("open_evidence") or {}
                oe["ontology"] = "csef-evidence-0.1"
                if f.get("collected_under"):
                    oe["collected_under"] = f["collected_under"]
                oe.setdefault("min_players", 10)
                oe.setdefault("min_classes", 3)
                dc["open_evidence"] = oe
            else:
                dc.pop("open_evidence", None)
        m["data_collection"] = dc
    md = m.get("metadata") or {}
    kw = [k.strip() for k in str(f.get("keywords") or "").split(",") if k.strip()]
    lg = [k.strip() for k in str(f.get("languages") or "").split(",") if k.strip()]
    if kw:
        md["keywords"] = kw
    if lg:
        md["languages"] = lg
    if md:
        m["metadata"] = md
    order = ["cses_version", "product", "description", "profiles", "age_bands", "compliance_level", "jurisdictions",
             "context", "distribution", "legal_scope", "gdpr_role", "features"]
    out = {k: m[k] for k in order if k in m}
    out.update({k: v for k, v in m.items() if k not in out})
    return ("# CSEF product manifest, written with the CSEF Workbench. See templates/csef.yaml for every field.\n"
            + yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=110))


def check_form(text: str) -> list[str]:
    """Plain-language gaps before running."""
    try:
        m = yaml.safe_load(text or "") or {}
    except yaml.YAMLError as ex:
        return [f"csef.yaml cannot be read: {ex}"]
    if not isinstance(m, dict):
        return ["csef.yaml must describe one product (a set of key: value lines)."]
    gaps = []
    if not m.get("product"):
        gaps.append("Give the product a name.")
    if not m.get("profiles"):
        gaps.append("Pick at least one kind of product (educational game, game-based software or gamified app).")
    if not m.get("age_bands"):
        gaps.append("Pick the age groups that use the product.")
    return gaps


# --------------------------------------------------------------------------- running the tools
def _call(fn, argv) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            code = fn(argv)
        except SystemExit as ex:
            code = ex.code if isinstance(ex.code, int) else 2
            if ex.code and not isinstance(ex.code, int):
                print(ex.code)
    return int(code or 0), buf.getvalue().strip()


def _docs(work: Path, exclude: set) -> list[Path]:
    out = []
    for p in sorted(work.rglob("*")):
        if p.is_file() and p.suffix.lower() in DOC_EXT and p.resolve() not in exclude and p.name != "csef.yaml":
            out.append(p)
    return out


def _files(d: Path) -> list[dict]:
    kinds = {".html": "html", ".zip": "zip", ".json": "json", ".md": "md", ".docx": "docx", ".tsv": "tsv",
             ".xml": "xml", ".jsonld": "json", ".sarif": "json", ".pdf": "pdf"}
    order = {"html": 0, "zip": 1, "docx": 2, "pdf": 3}
    fs = [{"path": str(p), "name": p.name, "kind": kinds.get(p.suffix.lower(), "file")}
          for p in sorted(d.rglob("*")) if p.is_file()] if d.exists() else []
    return sorted(fs, key=lambda x: (order.get(x["kind"], 9), x["name"]))


def run(work: str | Path, tools: list[str], out: str | Path, opts: dict | None = None) -> dict:
    """Run the selected tools. opts: level, coc, events, catalogue, feed, game, maker, collected_under, approval,
    instrument, countries, languages. Returns {"results": [...], "zip": path}."""
    import coc
    import compass
    import evidence
    import metadata
    import precheck
    opts = opts or {}
    work, out = Path(work), Path(out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    manifest_path = work / "csef.yaml"
    m = scan.load_yaml(manifest_path) if manifest_path.exists() else {}
    level = str(opts.get("level") or (m or {}).get("compliance_level") or 2)
    special = {Path(p).resolve() for p in (opts.get("coc"), opts.get("events"), opts.get("catalogue"), opts.get("feed")) if p}
    results = []
    findings = out / "describe" / "findings.json"
    compass_json = out / "compass" / "compass.json"
    has_docx = _has_docx()

    def add(tool, code, log, ok=None, note=""):
        d = out / tool
        try:
            summary = summarise(tool, d) if not note else ""
        except Exception:  # a summary is a convenience; never fail on it
            summary = ""
        results.append({"tool": tool, "title": TITLES[tool], "code": code, "ok": (code == 0) if ok is None else ok,
                        "log": log[-3000:], "note": note, "summary": summary, "files": _files(d)})

    for tool in [t for t in TOOLS if t in tools]:
        d = out / tool
        try:
            if tool == "describe":
                if not manifest_path.exists():
                    add(tool, 2, "", False, "Describe the product first (step 1).")
                    continue
                code, log = _call(scan.main, ["--repo", str(work), "--out-dir", str(d), "--format", "text", "--level", level,
                                              "--description-only", "--fail-on", "never",
                                              "--export", "html,docx" if has_docx else "html"])
                for junk in ("findings.sarif",):
                    (d / junk).unlink(missing_ok=True)
                add(tool, code, log)
            elif tool == "compass":
                docs = _docs(work, special)
                if not docs:
                    add(tool, 2, "", False, "Add documents first: design documents, teacher guides or in-product texts.")
                    continue
                argv = ["--out-dir", str(d)] + [x for p in docs for x in ("--input", str(p))]
                if manifest_path.exists():
                    argv += ["--manifest", str(manifest_path)]
                if findings.exists():
                    argv += ["--csef-findings", str(findings)]
                code, log = _call(compass.main, argv)
                add(tool, code, log)
            elif tool == "precheck":
                if not manifest_path.exists():
                    add(tool, 2, "", False, "Describe the product first (step 1).")
                    continue
                argv = ["--repo", str(work), "--out-dir", str(d), "--level", level]
                if findings.exists():
                    argv += ["--findings", str(findings)]
                if compass_json.exists():
                    argv += ["--compass", str(compass_json)]
                code, log = _call(precheck.main, argv)
                add(tool, code, log)
            elif tool == "package":
                if not manifest_path.exists():
                    add(tool, 2, "", False, "Describe the product first (step 1).")
                    continue
                argv = ["--repo", str(work), "--out-dir", str(d), "--package", "--level", level]
                if findings.exists():
                    argv += ["--findings", str(findings)]
                if compass_json.exists():
                    argv += ["--compass", str(compass_json)]
                code, log = _call(metadata.main, argv)
                add(tool, code, log, ok=True)
            elif tool == "coc":
                if not opts.get("coc"):
                    add(tool, 2, "", False, "Add the code of conduct to compare.")
                    continue
                argv = ["--input", str(opts["coc"]), "--out-dir", str(d), "--level", level]
                if m.get("profiles"):
                    argv += ["--profiles", ",".join(m["profiles"])]
                if m.get("age_bands"):
                    argv += ["--bands", ",".join(m["age_bands"])]
                code, log = _call(coc.main, argv)
                add(tool, code, log)
            elif tool in ("events", "feed"):
                cat = opts.get("catalogue") or ((m.get("data_collection") or {}).get("event_catalogue") and
                                                str(work / m["data_collection"]["event_catalogue"]))
                if not opts.get("events") or not cat or not Path(cat).exists():
                    add(tool, 2, "", False, "Add an event file (OGD format, .tsv) and its event catalogue (.yaml).")
                    continue
                if tool == "events":
                    code, log = _call(evidence.main, ["check-events", "--events", str(opts["events"]), "--catalogue", str(cat),
                                                      "--out-dir", str(d)])
                    add(tool, code, log)
                else:
                    md = m.get("metadata") or {}
                    maker = next((p.get("name") for p in md.get("parties") or [] if p.get("role") == "developer"), None)
                    oe = (m.get("data_collection") or {}).get("open_evidence") or {}
                    argv = ["build-feed", "--events", str(opts["events"]), "--catalogue", str(cat), "--out-dir", str(d / "feed"),
                            "--zip", "--collected-under", opts.get("collected_under") or oe.get("collected_under") or "processor_for_school",
                            "--game", opts.get("game") or m.get("product") or "Game"]
                    for k, v in (("--maker", opts.get("maker") or maker), ("--approval", opts.get("approval") or
                                 ((m.get("data_collection") or {}).get("research") or {}).get("ethics_approval")),
                                 ("--instrument", opts.get("instrument")), ("--countries", opts.get("countries")),
                                 ("--languages", opts.get("languages") or ",".join(md.get("languages") or []))):
                        if v:
                            argv += [k, str(v)]
                    code, log = _call(evidence.main, argv)
                    if (d / "feed").exists():
                        res = evidence.check_feed(evidence.read_feed(d / "feed"))
                        evidence.write_report(res, d, "feed-check", ("html",))
                    add(tool, code, log)
            elif tool == "feedcheck":
                if not opts.get("feed"):
                    add(tool, 2, "", False, "Add an evidence feed (a .zip, or its files).")
                    continue
                code, log = _call(evidence.main, ["check-feed", "--feed", str(opts["feed"]), "--out-dir", str(d)])
                add(tool, code, log)
        except Exception:  # keep going: one tool failing must not stop the others
            add(tool, 3, traceback.format_exc(), False, "This tool stopped with an error. The details are in the log.")
    z = out.parent / f"{out.name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        if manifest_path.exists():
            zf.write(manifest_path, "csef-results/csef.yaml")
        for p in sorted(out.rglob("*")):
            if p.is_file():
                zf.write(p, f"csef-results/{p.relative_to(out)}")
    return {"results": results, "zip": str(z)}


def _n(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def summarise(tool: str, d: Path) -> str:
    """One plain sentence per tool, read from its JSON output."""
    def js(name):
        p = d / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    if tool == "describe":
        f = js("findings.json") or {}
        sev = {}
        for x in f.get("findings", []):
            sev.setdefault(x["severity"], set()).add(x["rule_id"])
        hum = sum(1 for h in f.get("human_checks", []) if not h.get("next_level"))
        code = len(f.get("code_rules_not_checked") or [])
        return (f"{_n(len(sev.get('BLOCK', ())), 'rule')} to fix first, {len(sev.get('REVIEW', ()))} to review, "
                f"{_n(len(sev.get('WARN', ())), 'recommendation')}, {_n(hum, 'human check')}. "
                f"{_n(code, 'rule is', 'rules are')} checked in code: share the report with your developers.")
    if tool == "compass":
        c = js("compass.json") or {}
        ins = [x for x in c.get("targets", []) if x.get("status") == "in_scope"]
        return (f"{len(ins)} targets in scope, {sum(1 for x in ins if x.get('level', 0) >= 2)} at Designed or above. "
                f"{_n(len(c.get('claim_findings', [])), 'claim')} to support, {_n(len(c.get('conflicts', [])), 'possible conflict')}. "
                "A profile, never a score.")
    if tool == "precheck":
        s = (js("precheck.json") or {}).get("summary", {})
        return (f"{s.get('ready', 0)} criteria ready, {s.get('partial', 0)} partial, {s.get('missing', 0)} missing, "
                f"{_n(s.get('issue', 0), 'CSEF issue')}. Preparation, not a label.")
    if tool == "package":
        z = next(d.glob("*.zip"), None)
        return "Label package ready: metadata, checks and evidence index, with a hash for every file." if z else ""
    if tool == "coc":
        c = (js("coc-comparison.json") or {}).get("counts", {})
        return (f"{c.get('covered', 0)} rules covered, {c.get('partial', 0)} partial, {c.get('missing', 0)} missing, "
                f"{_n(c.get('conflict', 0), 'possible conflict')} for a person to review.")
    if tool == "events":
        r = js("events-check.json") or {}
        return (f"{r.get('events', 0)} events from {r.get('players', 0)} player codes in {r.get('classes', 0)} classes: "
                f"{_n(r.get('counts', {}).get('BLOCK', 0), 'blocking issue')}, {r.get('counts', {}).get('REVIEW', 0)} to review.")
    if tool == "feed":
        meta = json.loads((d / "feed" / "META.json").read_text(encoding="utf-8")) if (d / "feed" / "META.json").exists() else {}
        rows = max(0, len((d / "feed" / "population.tsv").read_text(encoding="utf-8").splitlines()) - 1) if (d / "feed" / "population.tsv").exists() else 0
        return (f"{_n(rows, 'row')} of group figures from {meta.get('player_count', 0)} players in {meta.get('class_count', 0)} classes; "
                f"{_n(meta.get('suppressed_cells', 0), 'small cell')} removed. Check it, then publish feed.zip.")
    if tool == "feedcheck":
        r = js("feed-check.json") or {}
        c = r.get("counts", {})
        return ("Ready to publish." if r.get("ok") else "Not ready to publish.") + \
            f" {_n(c.get('BLOCK', 0), 'blocking issue')}, {c.get('REVIEW', 0)} to review."
    return ""


def _has_docx() -> bool:
    try:
        import docx  # noqa: F401
        return True
    except ImportError:
        return False


# --------------------------------------------------------------------------- browser bundle
BUNDLE_TOOLS = ["scan.py", "comms.py", "brand.py", "export.py", "compass.py", "coc.py", "precheck.py", "metadata.py",
                "evidence.py", "workbench.py"]
BUNDLE_FILES = ["framework/rules.yaml", "framework/sources.yaml", "framework/coc-topics.yaml",
                "framework/compass/targets.yaml", "framework/compass/crosswalk.yaml",
                "framework/serious-games/criteria.yaml", "framework/data/profile.yaml",
                "framework/data/evidence-ontology.yaml", "templates/csef.yaml", "templates/event-catalogue.yaml",
                "brand/svg/csef-lockup-on-light.svg", "brand/svg/csef-mark-on-light.svg", "brand/web/favicon.svg"]
EXAMPLE_FILES = {  # the "Try the example" button: fictional Garden of Numbers
    "csef.yaml": "examples/compliant-game/csef.yaml",
    "docs/design-document.md": "examples/compliant-game/docs/design-document.md",
    "docs/playtest-summary.md": "examples/compliant-game/docs/playtest-summary.md",
    "docs/dpia.md": "examples/compliant-game/docs/dpia.md",
    "docs/event-catalogue.yaml": "examples/compliant-game/docs/event-catalogue.yaml",
    "docs/research/agreement.md": "examples/compliant-game/docs/research/agreement.md",
    "SECURITY.md": "examples/compliant-game/SECURITY.md",
    "data/events.tsv": "examples/evidence-feed/events.tsv",
    "coc/example-code.md": "examples/codes-of-conduct/example-code.md",
}


def web_bundle(root: Path = ROOT) -> str:
    files = {f"tooling/{t}": (root / "tooling" / t).read_text(encoding="utf-8") for t in BUNDLE_TOOLS}
    files.update({f: (root / f).read_text(encoding="utf-8") for f in BUNDLE_FILES})
    for pf in sorted((root / "packs").glob("*.yaml")):
        files[f"packs/{pf.name}"] = pf.read_text(encoding="utf-8")
    version = scan.load_yaml(root / "framework" / "rules.yaml").get("version", "?")
    return json.dumps({"version": str(version), "files": files}, ensure_ascii=False) + "\n"


def example_bundle(root: Path = ROOT) -> str:
    return json.dumps({k: (root / v).read_text(encoding="utf-8") for k, v in EXAMPLE_FILES.items()}, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CSEF Workbench: the tools that do not read code, on a product description and documents.")
    ap.add_argument("--work", required=True, help="folder with csef.yaml and the documents")
    ap.add_argument("--tools", default="describe,compass,precheck,package", help=f"comma-separated: {', '.join(TOOLS)}")
    ap.add_argument("--out-dir", default="csef-workbench")
    ap.add_argument("--level", type=int, choices=[1, 2, 3])
    ap.add_argument("--coc")
    ap.add_argument("--events")
    ap.add_argument("--catalogue")
    ap.add_argument("--feed")
    ap.add_argument("--collected-under", choices=["processor_for_school", "own_study"])
    a = ap.parse_args(argv)
    res = run(a.work, [t.strip() for t in a.tools.split(",")], a.out_dir,
              {"level": a.level, "coc": a.coc, "events": a.events, "catalogue": a.catalogue, "feed": a.feed,
               "collected_under": a.collected_under})
    for r in res["results"]:
        print(f"{'ok ' if r['ok'] else '-- '} {r['title']}: {r['note'] or (r['log'].splitlines() or [''])[-1][:160]}")
    print(f"all results: {res['zip']}")
    return 0 if all(r["ok"] for r in res["results"]) else 1


if __name__ == "__main__":
    sys.exit(main())
