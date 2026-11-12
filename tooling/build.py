#!/usr/bin/env python3
"""Validate the CSES rule catalogue and regenerate derived files.

  python3 tooling/build.py            validate + regenerate
  python3 tooling/build.py --check    validate + fail if generated files are out of date (CI)
  python3 tooling/build.py --zip DIR  also package the skill as DIR/cses-review.zip

Generated (never edit by hand):
  standard/catalogue/*.md      rule catalogue per profile, age bands and packs
  self-assessment/*.md         checklists per profile, grouped by compliance level
  tooling/semgrep/cses.yml     Semgrep rules from the regex patterns
  docs/index.html, docs/pack-builder/index.html   GitHub Pages site and Pack Builder
  skill/cses-review/standard/  copies of rules.yaml and sources.yaml
  skill/cses-review/packs/     copies of the packs
  skill/cses-review/scripts/scan.py
  skill/cses-review/templates/   copies of the product templates

Licence: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
import scan  # noqa: E402

LEVEL_NAMES = scan.LEVEL_NAMES
SOURCE_TYPES = {"law", "law-pending", "proposal", "guidance", "standard", "literature", "news", "policy"}
TIER_MIN_TYPES = {
    1: {"law", "law-pending", "policy"},
    2: {"law", "law-pending", "proposal", "guidance", "standard", "policy"},
    3: SOURCE_TYPES,
}
REQUIRED = ["id", "title", "level", "tier", "profiles", "age_bands", "requirement", "rationale",
            "improvement", "effort", "sources", "detection"]
FEATURES = {"accounts", "multiplayer", "chat", "ugc", "social", "notifications", "streaks",
            "leaderboards", "purchases", "assessment", "ai_generative", "ai_assessment",
            "ai_adaptive", "recommender"}
ID_RE = re.compile(r"^(CORE|A|B|C|AGE|[A-Z]{2,8})-[A-Z0-9]{2,4}-\d{2}$")

errors: list[str] = []


def err(msg):
    errors.append(msg)


# --------------------------------------------------------------------------- validation
def validate_rule(r, sources, origin):
    rid = r.get("id", "?")
    for k in REQUIRED:
        if k not in r:
            err(f"{origin} {rid}: missing field '{k}'")
    if not ID_RE.match(rid):
        err(f"{origin} {rid}: id does not match PREFIX-AREA-NN")
    if r.get("level") not in ("MUST", "SHOULD"):
        err(f"{origin} {rid}: level must be MUST or SHOULD")
    if r.get("tier") not in (1, 2, 3):
        err(f"{origin} {rid}: tier must be 1, 2 or 3")
    if not set(r.get("profiles", [])) <= scan.PROFILES:
        err(f"{origin} {rid}: unknown profile in {r.get('profiles')}")
    bands = r.get("age_bands", [])
    if bands != ["all"] and not set(bands) <= set(scan.BANDS):
        err(f"{origin} {rid}: unknown age band in {bands}")
    if not set(r.get("features", []) or []) <= FEATURES:
        err(f"{origin} {rid}: unknown feature in {r.get('features')}")
    if r.get("effort") not in ("low", "medium", "high"):
        err(f"{origin} {rid}: effort must be low, medium or high")
    types = set()
    for sid in r.get("sources", []):
        if sid not in sources:
            err(f"{origin} {rid}: unknown source '{sid}'")
        else:
            types.add(sources[sid].get("type"))
    tier = r.get("tier")
    if tier in TIER_MIN_TYPES and types and not (types & TIER_MIN_TYPES[tier]):
        err(f"{origin} {rid}: tier {tier} needs at least one source of type {sorted(TIER_MIN_TYPES[tier])}")
    det = r.get("detection") or {}
    if det.get("method") not in ("static", "manifest", "manual", "mixed"):
        err(f"{origin} {rid}: detection.method invalid")
    for p in det.get("patterns", []) or []:
        validate_pattern(p, f"{origin} {rid}")


def validate_pattern(p, where):
    t = p.get("type")
    if t == "regex":
        try:
            scan.compile_pattern(p)
        except re.error as e:
            err(f"{where}: bad regex: {e}")
    elif t == "dependency":
        if not p.get("names"):
            err(f"{where}: dependency pattern without names")
    elif t == "repo":
        if p.get("check") not in scan.REPO_CHECKS:
            err(f"{where}: unknown repo check {p.get('check')}")
    elif t == "manifest":
        if p.get("check") not in scan.MANIFEST_CHECKS:
            err(f"{where}: unknown manifest check {p.get('check')}")
    else:
        err(f"{where}: unknown pattern type {t}")
    if p.get("confidence", "medium") not in ("high", "medium"):
        err(f"{where}: confidence must be high or medium")


def validate_sources(sources, origin):
    for sid, s in sources.items():
        for k in ("title", "type", "jurisdiction", "status", "verified"):
            if k not in s:
                err(f"{origin} source {sid}: missing '{k}'")
        if s.get("type") not in SOURCE_TYPES:
            err(f"{origin} source {sid}: unknown type {s.get('type')}")


def validate_pack_file(pf: Path):
    """Validate one pack (country, sector or company). Returns (doc, merged standard) or None."""
    s2 = scan.load_standard(ROOT)
    doc = scan.load_yaml(pf)
    if "pack" not in doc or "id" not in doc["pack"]:
        err(f"pack {pf.name}: missing pack.id")
        return None
    pid = doc["pack"]["id"]
    if not re.match(r"^[a-z][a-z0-9_-]{1,7}$", pid):
        err(f"pack {pf.name}: pack.id must be 2 to 8 lowercase letters or digits")
    try:
        scan.apply_pack(s2, pf)
    except (ValueError, KeyError) as e:
        err(f"pack {pf.name}: {e}")
        return None
    validate_sources({s["id"]: s for s in doc.get("sources", []) or []}, f"pack {pid}")
    touched = [r["id"] for r in doc.get("rules", []) or []]
    for rid in touched:
        if not rid.startswith(pid.upper() + "-"):
            err(f"pack {pid}: rule {rid} must start with {pid.upper()}-")
    touched += [a["rule"] for a in doc.get("amend", []) or []]
    touched += [rid for rid in s2.rules if rid.startswith(pid.upper() + "-POL-")]
    for rid in dict.fromkeys(touched):
        if rid in s2.rules:
            validate_rule(s2.rules[rid], s2.sources, f"pack {pid}")
    for a in doc.get("amend", []) or []:
        for p in a.get("add_patterns", []) or []:
            validate_pattern(p, f"pack {pid} amend {a['rule']}")
    pol = doc.get("policy") or {}
    unknown = set(pol) - {"minimum_level", "no_go", "forbid_dependencies", "forbid_phrases", "forbid_patterns",
                          "require_decision_for_features", "review_every_days", "require_agent_instructions"}
    if unknown:
        err(f"pack {pid}: unknown policy keys {sorted(unknown)}")
    if not set(pol.get("require_decision_for_features") or []) <= FEATURES:
        err(f"pack {pid}: unknown feature in require_decision_for_features")
    return doc, s2


def load_and_validate():
    std = scan.load_standard(ROOT)
    ids = [r["id"] for r in scan.load_yaml(ROOT / "standard" / "rules.yaml")["rules"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        err(f"duplicate rule ids: {sorted(dupes)}")
    validate_sources(std.sources, "standard")
    for r in std.rules.values():
        validate_rule(r, std.sources, "standard")
    topics = scan.load_yaml(ROOT / "standard" / "coc-topics.yaml")
    for rid in std.rules:
        if rid not in topics.get("rules", {}):
            err(f"coc-topics.yaml: rule {rid} has no entry (add terms, or skip: true)")
    for rid, t in topics.get("rules", {}).items():
        if rid not in std.rules:
            err(f"coc-topics.yaml: unknown rule {rid}")
        for g in (t or {}).get("terms", []) + [[x] for x in (t or {}).get("conflict", []) or []]:
            for term in g:
                if isinstance(term, bool):
                    err(f"coc-topics.yaml: {rid} has a YAML boolean (quote words like \"no\", \"yes\", \"on\", \"off\")")
        for rx in (t or {}).get("conflict_regex", []) or []:
            try:
                re.compile(rx)
            except re.error as ex:
                err(f"coc-topics.yaml: {rid} bad conflict_regex: {ex}")

    packs = {}
    for pf in sorted((ROOT / "packs").glob("*.yaml")):
        if pf.name.startswith("_"):
            continue
        res = validate_pack_file(pf)
        if res:
            packs[res[0]["pack"]["id"]] = res
    return std, packs


# --------------------------------------------------------------------------- generation
LANDING = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Child-Safe EdTech Standard</title>
<style>
:root{--bg:#f7f7f4;--ink:#1d2321;--muted:#5d6763;--accent:#1f6f5c;--panel:#fff;--line:#dcdfd9}
@media (prefers-color-scheme:dark){:root{--bg:#121514;--ink:#e8ebe9;--muted:#a2aba7;--accent:#5cc3a6;--panel:#1b1f1e;--line:#2e3432}}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:760px;margin:0 auto;padding:40px 16px}
h1{font-size:1.9rem;margin:0 0 6px}p.lead{color:var(--muted);margin:0 0 28px}
a{color:var(--accent)}.cards{display:grid;gap:12px}
.card{display:block;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;text-decoration:none;color:var(--ink)}
.card strong{color:var(--accent)}.card span{display:block;color:var(--muted);font-size:.95rem}
</style></head><body><main>
<h1>Child-Safe EdTech Standard</h1>
<p class="lead">An open standard and toolkit for software children use for learning. CSES v{version}, {rules} rules, draft for public comment.</p>
<div class="cards">
<a class="card" href="pack-builder/"><strong>Pack Builder</strong><span>Define your organisation's minimum level, no-gos and rules, and publish your pack to GitHub.</span></a>
<a class="card" href="https://github.com/eduardon83/child-safe-edtech-standards"><strong>Repository</strong><span>The standard, the scanner, the Claude skill and the GitHub Action.</span></a>
<a class="card" href="https://github.com/eduardon83/child-safe-edtech-standards/blob/main/standard/catalogue/index.md"><strong>Rule catalogue</strong><span>Every rule with requirement, rationale, improvement and sources.</span></a>
<a class="card" href="https://github.com/eduardon83/child-safe-edtech-standards/issues"><strong>Give feedback</strong><span>Open an issue: false positives, rule wording, sources, country packs.</span></a>
</div>
<p class="lead" style="margin-top:28px;font-size:.9rem">Not legal advice or a certification. Standard content CC BY 4.0, code Apache 2.0.</p>
</main></body></html>
"""

HEADER = "<!-- GENERATED by tooling/build.py from standard/rules.yaml. Do not edit by hand. -->\n\n"


def bands_txt(r):
    b = r.get("age_bands", ["all"])
    return "all" if b == ["all"] else ", ".join(f"{x} ({scan.BAND_AGES[x]})" for x in b)


def src_links(r, sources):
    out = []
    for sid in r.get("sources", []):
        s = sources.get(sid, {})
        out.append(f"[{sid}]({s['url']})" if s.get("url") else sid)
    return ", ".join(out)


def rule_block(r, sources):
    lines = [f"### {r['id']}: {r['title']}", ""]
    lines.append(f"**{r['level']}** · Level {r['tier']} ({LEVEL_NAMES[r['tier']]}) · Age bands: {bands_txt(r)}"
                 + (f" · Features: {', '.join(r['features'])}" if r.get("features") else "")
                 + f" · Detection: {(r.get('detection') or {}).get('method', 'manual')} · Effort: {r.get('effort')}")
    lines += ["", f"**Requirement.** {r['requirement'].strip()}", "",
              f"**Why.** {r['rationale'].strip()}", "",
              f"**How to improve.** {r['improvement'].strip()}", ""]
    for n in r.get("notes", []):
        lines += [f"**National note.** {n}", ""]
    lines += [f"**Sources.** {src_links(r, sources)}", ""]
    return lines


def catalogue_page(title, intro, rules, sources):
    lines = [HEADER + f"# {title}", "", intro, "",
             "| ID | Rule | Strength | Level | Detection |", "|---|---|---|---|---|"]
    for r in rules:
        lines.append(f"| [{r['id']}](#{anchor(r)}) | {r['title']} | {r['level']} | {r['tier']} | {(r.get('detection') or {}).get('method')} |")
    lines.append("")
    for r in rules:
        lines += rule_block(r, sources)
    return "\n".join(lines)


def anchor(r):
    return re.sub(r"[^a-z0-9 -]", "", f"{r['id']}: {r['title']}".lower()).replace(" ", "-")


def checklist_page(title, rules):
    lines = [HEADER + f"# Self-assessment: {title}", "",
             "Tick each item you can evidence. Keep the evidence (link, file, screenshot) next to the tick.",
             "Pick your target level: complete every item of that level and of the levels below it.", "",
             "Product: ____________________  Date: __________  Assessor: ____________________", ""]
    for t in (1, 2, 3):
        sub = [r for r in rules if r["tier"] == t]
        if not sub:
            continue
        lines += [f"## Level {t}: {LEVEL_NAMES[t]}", ""]
        for r in sub:
            lines.append(f"- [ ] **{r['id']}** ({r['level']}) {r['title']}. {r['requirement'].strip()}  ")
            lines.append(f"      Evidence: ")
        lines.append("")
    return "\n".join(lines)


def semgrep_yaml(rules):
    out = []
    for r in rules:
        for i, p in enumerate((r.get("detection") or {}).get("patterns", []) or []):
            if p["type"] != "regex":
                continue
            rx = p["pattern"]
            if "i" in str(p.get("flags", "")):
                rx = "(?i)" + rx
            sev = "ERROR" if (r["level"] == "MUST" and p.get("confidence") == "high") else "WARNING" if r["level"] == "MUST" else "INFO"
            entry = {
                "id": f"{r['id']}-{i + 1}".lower(),
                "message": f"{r['id']} ({r['level']}, level {r['tier']}): {r['title']}. {r['improvement'].strip()}",
                "severity": sev,
                "languages": ["generic"],
                "pattern-regex": rx,
                "metadata": {"cses_rule": r["id"], "tier": r["tier"], "sources": r["sources"]},
            }
            if p.get("globs"):
                entry["paths"] = {"include": p["globs"]}
            out.append(entry)
    return "# GENERATED by tooling/build.py. Do not edit by hand.\n" + yaml.safe_dump({"rules": out}, sort_keys=False, allow_unicode=True, width=200)


def generate(std, packs) -> dict[Path, str]:
    files: dict[Path, str] = {}
    rules = sorted(std.rules.values(), key=lambda r: r["id"])
    core = [r for r in rules if r["profiles"] == ["core"] and not r["id"].startswith("AGE-")]
    by_prof = {p: [r for r in rules if p in r["profiles"]] for p in ("A", "B", "C")}
    age = [r for r in rules if r["id"].startswith("AGE-")]
    cat = ROOT / "standard" / "catalogue"
    intros = {
        "core": "Rules that apply to every product used by minors, whatever its profile.",
        "A": "Profile A: educational games. Read together with the core rules.",
        "B": "Profile B: game-based applications and software. Read together with the core rules.",
        "C": "Profile C: gamified applications. Read together with the core rules.",
        "age": "Age-band modifiers. They add or tighten rules for specific age bands.",
    }
    files[cat / "core.md"] = catalogue_page("Core rules", intros["core"], core, std.sources)
    files[cat / "profile-a.md"] = catalogue_page("Profile A: educational games", intros["A"], by_prof["A"], std.sources)
    files[cat / "profile-b.md"] = catalogue_page("Profile B: game-based applications", intros["B"], by_prof["B"], std.sources)
    files[cat / "profile-c.md"] = catalogue_page("Profile C: gamified applications", intros["C"], by_prof["C"], std.sources)
    files[cat / "age-bands.md"] = catalogue_page("Age-band modifiers", intros["age"], age, std.sources)

    idx = [HEADER + "# Rule catalogue", "",
           f"CSES v{std.version}: {len(rules)} rules. Level 1 = {LEVEL_NAMES[1]}, 2 = {LEVEL_NAMES[2]}, 3 = {LEVEL_NAMES[3]}.", "",
           "| Level | MUST | SHOULD |", "|---|---|---|"]
    for t in (1, 2, 3):
        idx.append(f"| {t} {LEVEL_NAMES[t]} | {sum(1 for r in rules if r['tier'] == t and r['level'] == 'MUST')} | {sum(1 for r in rules if r['tier'] == t and r['level'] == 'SHOULD')} |")
    idx += ["", "| ID | Title | Profiles | Strength | Level | Age bands |", "|---|---|---|---|---|---|"]
    for r in rules:
        idx.append(f"| {r['id']} | {r['title']} | {', '.join(r['profiles'])} | {r['level']} | {r['tier']} | {bands_txt(r)} |")
    idx += ["", "Packs: " + (", ".join(f"[{pid}](pack-{pid}.md)" for pid in sorted(packs)) or "none"), ""]
    files[cat / "index.md"] = "\n".join(idx)

    for pid, (doc, s2) in packs.items():
        prules = [s2.rules[r["id"]] for r in doc.get("rules", []) or []]
        lines = [HEADER + f"# Pack: {doc['pack'].get('title', pid)}", "",
                 f"Jurisdiction: {doc['pack'].get('jurisdiction')}. Version {doc['pack'].get('version')}. {doc['pack'].get('status', '')}", ""]
        if doc.get("parameters"):
            lines += ["## Parameters", ""] + [f"- {k}: {v}" for k, v in doc["parameters"].items()] + [""]
        lines += ["## Sources added", ""]
        for s in doc.get("sources", []) or []:
            lines.append(f"- **{s['id']}** {s['title']}. {s.get('status', '')}. {s.get('url', '')}")
        lines += ["", "## Amendments to standard rules", ""]
        for a in doc.get("amend", []) or []:
            bits = []
            if a.get("add_sources"):
                bits.append("adds sources " + ", ".join(a["add_sources"]))
            if "tier" in a:
                bits.append(f"sets level {a['tier']}")
            if a.get("level"):
                bits.append(f"sets {a['level']}")
            if a.get("add_patterns"):
                bits.append(f"adds {len(a['add_patterns'])} detection pattern(s)")
            lines.append(f"- **{a['rule']}**: {'; '.join(bits)}. {a.get('note', '')}")
        lines += ["", "## Rules added", ""]
        for r in prules:
            lines += rule_block(r, s2.sources)
        files[cat / f"pack-{pid}.md"] = "\n".join(lines)

    sa = ROOT / "self-assessment"
    files[sa / "core.md"] = checklist_page("Core (all products)", core)
    files[sa / "profile-a.md"] = checklist_page("Profile A, educational games (use with core.md)", [r for r in by_prof["A"] if r["profiles"] != ["core"]])
    files[sa / "profile-b.md"] = checklist_page("Profile B, game-based applications (use with core.md)", [r for r in by_prof["B"] if r["profiles"] != ["core"]])
    files[sa / "profile-c.md"] = checklist_page("Profile C, gamified applications (use with core.md)", [r for r in by_prof["C"] if r["profiles"] != ["core"]])
    files[sa / "age-bands.md"] = checklist_page("Age-band modifiers (use with core.md)", age)

    files[ROOT / "tooling" / "semgrep" / "cses.yml"] = semgrep_yaml(rules)

    cat_json = json.dumps({
        "version": std.version,
        "features": sorted(FEATURES),
        "rules": [{"id": r["id"], "title": r["title"], "level": r["level"], "tier": r["tier"],
                   "profiles": r["profiles"], "requirement": " ".join(r["requirement"].split())} for r in rules],
    }, ensure_ascii=False).replace("</", "<\\/")
    tpl = (ROOT / "tooling" / "pack-builder.template.html").read_text(encoding="utf-8")
    files[ROOT / "docs" / "pack-builder" / "index.html"] = tpl.replace("/*CATALOGUE*/null", cat_json)
    files[ROOT / "docs" / "index.html"] = LANDING.replace("{version}", std.version).replace("{rules}", str(len(rules)))

    sk = ROOT / "skill" / "cses-review"
    files[sk / "standard" / "rules.yaml"] = (ROOT / "standard" / "rules.yaml").read_text(encoding="utf-8")
    files[sk / "standard" / "sources.yaml"] = (ROOT / "standard" / "sources.yaml").read_text(encoding="utf-8")
    for pf in sorted((ROOT / "packs").glob("*.yaml")):
        files[sk / "packs" / pf.name] = pf.read_text(encoding="utf-8")
    files[sk / "scripts" / "scan.py"] = (ROOT / "tooling" / "scan.py").read_text(encoding="utf-8")
    for t in ("export.py", "comms.py", "coc.py"):
        files[sk / "scripts" / t] = (ROOT / "tooling" / t).read_text(encoding="utf-8")
    files[sk / "standard" / "coc-topics.yaml"] = (ROOT / "standard" / "coc-topics.yaml").read_text(encoding="utf-8")
    for t in ("cses.yaml", "dpia-starter.md", "ai-risk-file.md", "waiver.md", "agent-instructions.md"):
        files[sk / "templates" / t] = (ROOT / "templates" / t).read_text(encoding="utf-8")
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--zip", metavar="DIR")
    ap.add_argument("--validate-pack", metavar="FILE", help="validate a single pack file (e.g. your company pack) and exit")
    args = ap.parse_args()

    if args.validate_pack:
        res = validate_pack_file(Path(args.validate_pack))
        if errors or not res:
            print("Pack validation failed:")
            for e in errors:
                print("  -", e)
            return 1
        doc, s2 = res
        pol = doc.get("policy") or {}
        print(f"OK: pack '{doc['pack']['id']}' valid. {len(doc.get('rules') or [])} rule(s), "
              f"{len(doc.get('amend') or [])} amendment(s), {len(pol.get('no_go') or [])} no-go(s), "
              f"minimum level {pol.get('minimum_level', 1)}.")
        return 0

    std, packs = load_and_validate()
    if errors:
        print("Validation failed:")
        for e in errors:
            print("  -", e)
        return 1
    files = generate(std, packs)
    stale = [p for p, c in files.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    if args.check:
        if stale:
            print("Generated files are out of date. Run: python3 tooling/build.py")
            for p in stale:
                print("  -", p.relative_to(ROOT))
            return 1
        print(f"OK: {len(std.rules)} rules, {len(std.sources)} sources, {len(packs)} pack(s); generated files up to date.")
        return 0
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(files[p], encoding="utf-8")
    print(f"OK: {len(std.rules)} rules, {len(std.sources)} sources, {len(packs)} pack(s); {len(stale)} file(s) regenerated.")
    if args.zip:
        out = Path(args.zip)
        out.mkdir(parents=True, exist_ok=True)
        z = out / "cses-review.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted((ROOT / "skill" / "cses-review").rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    zf.write(f, Path("cses-review") / f.relative_to(ROOT / "skill" / "cses-review"))
        print(f"Skill packaged: {z}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
