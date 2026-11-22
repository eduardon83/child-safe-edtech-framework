#!/usr/bin/env python3
"""Validate the CSEF rule catalogue and regenerate derived files.

  python3 tooling/build.py            validate + regenerate
  python3 tooling/build.py --check    validate + fail if generated files are out of date (CI)
  python3 tooling/build.py --zip DIR  also package the skill as DIR/csef-review.zip

Generated (never edit by hand):
  framework/catalogue/*.md      rule catalogue per profile, age bands and packs
  self-assessment/*.md         checklists per profile, grouped by compliance level
  tooling/semgrep/csef.yml     Semgrep rules from the regex patterns
  docs/index.html, docs/pack-builder/index.html   GitHub Pages site and Pack Builder
  docs/questionnaire/index.html                    static policy questionnaire (answers download)
  skill/csef-review/framework/  copies of rules.yaml and sources.yaml
  skill/csef-review/packs/     copies of the packs
  skill/csef-review/scripts/scan.py
  skill/csef-review/templates/   copies of the product templates
  framework/compass/catalogue.md Literacy Compass target catalogue
  skill/csef-review/framework/compass/, skill/csef-review/scripts/compass.py

Licence: Apache-2.0
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
import scan  # noqa: E402

sys.path.insert(0, str(ROOT / "engine"))
from sfe import catalogue as sfe_catalogue  # noqa: E402
from sfe import config as sfe_config  # noqa: E402

CFG = sfe_config.load(ROOT / "framework" / "framework.yaml")

LEVEL_NAMES = scan.LEVEL_NAMES
SOURCE_TYPES = CFG.source_types
TIER_MIN_TYPES = CFG.tier_min_types
REQUIRED = CFG.required_fields
FEATURES = CFG.features
FEATURE_NAMES = FEATURES | set(scan.FEATURE_GROUPS)
ID_RE = CFG.id_re

errors: list[str] = []


def err(msg):
    errors.append(msg)


# --------------------------------------------------------------------------- validation
def validate_rule(r, sources, origin):
    sfe_catalogue.validate_rule(CFG, r, sources, origin, err, scan.REPO_CHECKS, scan.MANIFEST_CHECKS)


def validate_pattern(p, where):
    sfe_catalogue.validate_pattern(p, where, err, scan.REPO_CHECKS, scan.MANIFEST_CHECKS)


def validate_sources(sources, origin):
    sfe_catalogue.validate_sources(CFG, sources, origin, err)


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


COMPASS_SCOPES = {"claimed", "universal", "feature"}
COMPASS_REQUIRED = ["id", "axis", "title", "scope", "age_bands", "target", "why", "improvement", "sources", "terms"]


def packs_for_compass():
    return sorted((ROOT / "packs").glob("*.yaml"))


def validate_compass(std, pack_files):
    """Literacy Compass: targets, axes, sources, features and the crosswalk."""
    import compass as cmp
    s2 = scan.load_standard(ROOT)
    for pf in pack_files:
        if not pf.name.startswith("_"):
            scan.apply_pack(s2, pf)
    try:
        c = cmp.load_compass(ROOT, [pf for pf in pack_files if not pf.name.startswith("_")], s2)
    except (ValueError, KeyError) as ex:
        err(f"compass: {ex}")
        return None
    raw = scan.load_yaml(ROOT / "framework" / "compass" / "targets.yaml")
    ids = [x["id"] for x in raw["targets"]]
    for d in {i for i in ids if ids.count(i) > 1}:
        err(f"compass: duplicate target id {d}")
    axes = {a["id"]: a for a in c["axes"]}
    for a in c["axes"]:
        if a.get("lens") not in ("learner", "design"):
            err(f"compass axis {a['id']}: lens must be learner or design")
        for sid in a.get("sources", []):
            if sid not in std.sources:
                err(f"compass axis {a['id']}: unknown source {sid}")
    for t in c["targets"].values():
        tid = t.get("id", "?")
        for k in COMPASS_REQUIRED:
            if k not in t:
                err(f"compass {tid}: missing field '{k}'")
        if not re.match(r"^([A-Z]{2,8}-)?[A-Z]{2,4}-\d{2}$", tid):
            err(f"compass {tid}: id must be AXIS-NN (packs: PACK-AXIS-NN)")
        if t.get("axis") not in axes:
            err(f"compass {tid}: unknown axis {t.get('axis')}")
        elif t.get("origin", "CSEF") == "CSEF" and not tid.startswith(str(t["axis"]) + "-"):
            err(f"compass {tid}: id does not match axis {t['axis']}")
        elif t.get("origin", "CSEF") != "CSEF" and not tid.startswith(t["origin"].split(":")[1].upper() + "-"):
            err(f"compass {tid}: pack targets must start with the pack id")
        if t.get("scope") not in COMPASS_SCOPES:
            err(f"compass {tid}: scope must be one of {sorted(COMPASS_SCOPES)}")
        if t.get("scope") == "feature" and not t.get("features"):
            err(f"compass {tid}: feature scope needs features")
        if not set(t.get("features") or []) <= FEATURE_NAMES:
            err(f"compass {tid}: unknown feature in {t.get('features')}")
        for rid in t.get("builds_on") or []:
            if rid not in std.rules:
                err(f"compass {tid}: builds_on unknown rule {rid}")
        bands = t.get("age_bands", [])
        if bands != ["all"] and not set(bands) <= set(scan.BANDS):
            err(f"compass {tid}: unknown age band in {bands}")
        if not t.get("sources"):
            err(f"compass {tid}: needs at least one source")
        for g in (t.get("terms") or []) + [[x] for x in t.get("conflict") or []]:
            for term in g:
                if not isinstance(term, str):
                    err(f"compass {tid}: non-text term {term!r} (quote words like \"no\", \"yes\", \"on\", \"off\")")
    cw = c["crosswalk"]
    for key, m in list(cw.get("axes", {}).items()) + list(cw.get("targets", {}).items()):
        if key not in axes and key not in c["targets"]:
            err(f"compass crosswalk: unknown axis or target {key}")
        for fw, items in (m or {}).items():
            if fw not in cw["frameworks"]:
                err(f"compass crosswalk {key}: unknown framework {fw}")
            elif not {str(x) for x in items} <= {str(k) for k in cw["frameworks"][fw]["items"]}:
                err(f"compass crosswalk {key}: unknown item in {fw}: {items}")
    for fw in cw["frameworks"]:
        if fw not in std.sources:
            err(f"compass crosswalk: framework {fw} is not in sources.yaml")
    return c


# --------------------------------------------------------------------------- legislation.md and research.md
# Hand-written text stays; the build refreshes each entry's id line, status and citing rules from
# sources.yaml, rebuilds the at-a-glance table and adds a stub entry for any new source.
LEG_SECTION = {"law": "## Law in force", "law-pending": "## Adopted, applying later",
               "proposal": "## EU proposals (in negotiation)", "policy": "## Policy context",
               "standard": "## Technical standards"}
LEG_LAST = "## Open discussions and watch list"
RES_LAST = "## Gaps and research wanted"


def _citations(std, s2, compass, pack_files):
    rules, targets = {}, {}
    for rid, r in s2.rules.items():
        base = set(std.rules[rid]["sources"]) if rid in std.rules else None
        for sid in r.get("sources", []):
            amended = base is not None and sid not in base
            rules.setdefault(sid, []).append(f"{rid} (PT amendment)" if amended and sid.startswith("PT-") else
                                             f"{rid} (pack amendment)" if amended else rid)
    base_targets = scan.load_yaml(ROOT / "framework" / "compass" / "targets.yaml")["targets"]
    base_src = {t["id"]: set(t.get("sources", [])) for t in base_targets}
    for tid, t in compass["targets"].items():
        for sid in t.get("sources", []):
            extra = tid in base_src and sid not in base_src[tid]
            targets.setdefault(sid, []).append(f"{tid} (pack)" if extra else tid)
    return rules, targets


def _leg_section(sid, s):
    origin = s.get("origin", "CSEF")
    if origin.startswith("pack:"):
        return "## National: Portugal (pack, draft)" if origin == "pack:pt" else f"## National: {s.get('jurisdiction')} (pack)"
    if s["type"] == "guidance":
        return "## EU guidance and recommendations" if s.get("jurisdiction") == "EU" else "## International guidance and frameworks"
    return LEG_SECTION.get(s["type"], "## Policy context")


def _insert_in_section(text, heading, entry, last):
    if heading + "\n" not in text:
        text = text.replace(last + "\n", heading + "\n\n" + last + "\n", 1)
    start = text.index(heading + "\n") + len(heading) + 1
    nxt = text.find("\n## ", start)
    nxt = len(text) if nxt < 0 else nxt + 1
    return text[:nxt] + entry + text[nxt:]


def _refresh_entries(text, sources, rules_c, targets_c, bullet):
    def fmt(xs):
        return ", ".join(f"`{x}`" for x in xs)
    pre = "- " if bullet else ""
    blocks = re.split(r"(?=^### )", text, flags=re.M)
    for i, b in enumerate(blocks):
        m = re.search(r"^\*Id `([^`]+)` · .*\*$", b, re.M)
        if not m or m.group(1) not in sources:
            continue
        sid, s = m.group(1), sources[m.group(1)]
        idline = (f"*Id `{sid}` · verified {s.get('verified')}*" if bullet else
                  f"*Id `{sid}` · {s['type']} · {s.get('jurisdiction')} · verified {s.get('verified')}*")
        b = b.replace(m.group(0), idline)
        if not bullet:
            b = re.sub(r"^\*\*Status\.\*\* .*$", lambda _: f"**Status.** {s['status'].rstrip('.')}.", b, count=1, flags=re.M)
        b = re.sub(r"^%s\*\*(Rules|Compass targets) citing it\.\*\* .*\n(\n)?" % re.escape(pre), "", b, flags=re.M)
        lines = [f"{pre}**Rules citing it.** {fmt(rules_c[sid]) if rules_c.get(sid) else 'none (context)'}"]
        if targets_c.get(sid):
            lines.append(f"{pre}**Compass targets citing it.** {fmt(targets_c[sid])}")
        link = re.search(r"^%s\*\*Link\.\*\*" % re.escape(pre), b, re.M)
        sep = "\n" if bullet else "\n\n"
        ins = sep.join(lines) + sep
        b = b[:link.start()] + ins + b[link.start():] if link else b.rstrip("\n") + sep + ins
        blocks[i] = b
    return "".join(blocks)


def source_pages(std, s2, compass, pack_files):
    rules_c, targets_c = _citations(std, s2, compass, pack_files)
    srcs = s2.sources
    leg = (ROOT / "framework" / "legislation.md").read_text(encoding="utf-8")
    res = (ROOT / "framework" / "research.md").read_text(encoding="utf-8")
    have = set(re.findall(r"^\*Id `([^`]+)`", leg, re.M)) | set(re.findall(r"^\*Id `([^`]+)`", res, re.M))
    for sid, s in srcs.items():
        if sid in have:
            continue
        link = f"[{s.get('url')}]({s.get('url')})" if s.get("url") else "-"
        if s["type"] == "literature":
            entry = (f"### {s['title']}\n\n*Id `{sid}` · verified {s.get('verified')}*\n\n- **Key finding.** {s['status']}\n"
                     f"- **Link.** {link}\n\n")
            res = res.replace(RES_LAST + "\n", entry + RES_LAST + "\n", 1)
        else:
            summary = (" ".join(s["summary"].split()) + "\n\n") if s.get("summary") else ""
            entry = (f"### {s['title']}\n\n*Id `{sid}` · {s['type']} · {s.get('jurisdiction')} · verified {s.get('verified')}*\n\n"
                     f"{summary}**Status.** {s['status'].rstrip('.')}.\n\n**Link.** {link}\n\n")
            leg = _insert_in_section(leg, _leg_section(sid, s), entry, LEG_LAST)
    leg = re.sub(r"\n{3,}", "\n\n", _refresh_entries(leg, srcs, rules_c, targets_c, bullet=False))
    res = re.sub(r"\n{3,}", "\n\n", _refresh_entries(res, srcs, rules_c, {}, bullet=True))

    order = re.findall(r"^\*Id `([^`]+)`", leg, re.M)
    rows = ["| Source | Type | Status | CSEF rules | Compass targets |", "|---|---|---|---|---|"]
    for sid in order:
        s = srcs[sid]
        first = re.split(r"(?<=[a-z0-9)])[.;]\s(?=[A-Z])", s["status"])[0].rstrip(".;")
        rows.append(f"| **{sid}** {s['title']} | {s['type']} | {first} | {len(rules_c.get(sid, []))} | {len(targets_c.get(sid, []))} |")
    leg = re.sub(r"(## At a glance\n\n)\| Source \| Type \|.*?\n(?=\n)", lambda m: m.group(1) + "\n".join(rows) + "\n",
                 leg, count=1, flags=re.S)
    latest = max(str(s.get("verified")) for s in srcs.values() if s["type"] != "literature")
    d = dt.date.fromisoformat(latest)
    leg = re.sub(r"> Status as of \*\*[^*]+\*\*\.", f"> Status as of **{d.day} {d.strftime('%B')} {d.year}**.", leg, count=1)
    return leg, res


def compass_catalogue(std, c) -> str:
    L = ["<!-- GENERATED by tooling/build.py from framework/compass/targets.yaml. Do not edit by hand. -->", "",
         "# Literacy Compass: target catalogue", "",
         f"Compass v{c['version']}: {len(c['targets'])} targets on {len(c['axes'])} axes. See [04-literacy-compass.md](../04-literacy-compass.md) "
         "for how the Compass works.", "",
         "Evidence ladder: " + ", ".join(f"{k} {v['name']}" for k, v in c["levels"].items()) + ".", "",
         "| Axis | Lens | Question |", "|---|---|---|"]
    for a in c["axes"]:
        L.append(f"| **{a['id']}** {a['title']} | {a['lens']} | {a['question']} |")
    for a in c["axes"]:
        L += ["", f"## {a['id']}: {a['title']}", "", f"*{a['question']}*", ""]
        for t in [x for x in c["targets"].values() if x["axis"] == a["id"]]:
            scope = t["scope"] + (f" ({', '.join(t['features'])})" if t["scope"] == "feature" else "")
            refs = "; ".join(f"{k} {', '.join(map(str, v))}" for k, v in (t.get("refs") or {}).items() if v) or "-"
            L += [f"### {t['id']} {t['title']}", "",
                  f"- **Scope:** {scope}. **Age bands:** {', '.join(t.get('age_bands', ['all']))}."
                  + (f" **Natural fit for:** {', '.join(t['features'])}." if t["scope"] == "claimed" and t.get("features") else ""),
                  f"- **Target:** {' '.join(t['target'].split())}",
                  f"- **Why:** {' '.join(t['why'].split())}",
                  f"- **Look for:** {' '.join(t.get('look_for', '').split())}",
                  f"- **Improvement:** {' '.join(t['improvement'].split())}",
                  f"- **Ideas:** {'; '.join(t.get('ideas') or []) or '-'}",
                  f"- **Framework references:** {refs}",
                  *([f"- **Builds on rules:** {', '.join(t['builds_on'])}. The rule requires the feature; this target asks whether it also teaches."]
                    if t.get("builds_on") else []),
                  "- **Sources:** " + ", ".join(f"[{sid}]({std.sources[sid].get('url', '')})" if std.sources.get(sid, {}).get('url') else sid
                                                for sid in t["sources"])]
            if t.get("conflict"):
                L.append("- **Hidden-curriculum phrases:** " + ", ".join(f"\"{x}\"" for x in t["conflict"]))
            L.append("")
    return "\n".join(L)


def validate_serious_games(std):
    """framework/serious-games/criteria.yaml: ids, groups and links to rules and Compass targets."""
    doc = scan.load_yaml(ROOT / "framework" / "serious-games" / "criteria.yaml") or {}
    targets = {t["id"] for t in scan.load_yaml(ROOT / "framework" / "compass" / "targets.yaml")["targets"]}
    if doc.get("basis") not in std.sources:
        err(f"serious-games criteria: basis {doc.get('basis')} is not a source")
    seen = set()
    for c in doc.get("criteria", []):
        cid = c.get("id", "?")
        if not re.fullmatch(r"SG-\d{2}", cid) or cid in seen:
            err(f"serious-games criteria: bad or duplicate id {cid}")
        seen.add(cid)
        if c.get("group") not in ("serious", "game", "balance"):
            err(f"serious-games {cid}: group must be serious, game or balance")
        if c.get("coverage") not in ("covered", "partial", "declaration", "tension"):
            err(f"serious-games {cid}: unknown coverage {c.get('coverage')}")
        if c.get("coverage") == "tension" and not c.get("csef_note"):
            err(f"serious-games {cid}: a tension needs a csef_note")
        for rid in c.get("rules") or []:
            if rid not in std.rules:
                err(f"serious-games {cid}: unknown rule {rid}")
        for tid, lvl in (c.get("compass") or {}).items():
            if tid not in targets:
                err(f"serious-games {cid}: unknown Compass target {tid}")
            if lvl not in (1, 2, 3, 4):
                err(f"serious-games {cid}: Compass level for {tid} must be 1 to 4")
        if not (c.get("rules") or c.get("compass") or c.get("declare")):
            err(f"serious-games {cid}: needs rules, compass targets or declare: true")


def validate_site():
    """Every local link on the website points to a file in docs/ (example reports come from tooling/examples.py)."""
    for name, base in (("landing.template.html", ROOT / "docs"), ("submit.template.html", ROOT / "docs" / "submit"),
                       ("workbench.template.html", ROOT / "docs" / "workbench")):
        text = (ROOT / "tooling" / name).read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            if re.match(r"^(https?:|mailto:|#|\{|\$\{)", href):
                continue
            target = (base / href.split("#", 1)[0]).resolve()
            if href.endswith("/") or target.is_dir():
                target = target / "index.html"
            generated = target in (ROOT / "docs" / "index.html", ROOT / "docs" / "submit" / "index.html",
                                   ROOT / "docs" / "workbench" / "index.html", ROOT / "docs" / "learning-data" / "index.html")
            if not target.exists() and not generated:
                err(f"{name}: link {href} has no file in docs/ (run tooling/examples.py for example reports)")


WORKBENCH_WHEELS = ["python_docx-1.1.2-py3-none-any.whl", "pypdf-5.1.0-py3-none-any.whl"]


def validate_workbench():
    for w in WORKBENCH_WHEELS:
        if not (ROOT / "docs" / "workbench" / "vendor" / w).exists():
            err(f"docs/workbench/vendor/{w} is missing (the Workbench reads Word and PDF with it)")


def load_and_validate():
    std = scan.load_standard(ROOT)
    ids = [r["id"] for r in scan.load_yaml(ROOT / "framework" / "rules.yaml")["rules"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        err(f"duplicate rule ids: {sorted(dupes)}")
    for x in scan.load_yaml(ROOT / "framework" / "rules.yaml").get("retired", []) or []:
        if x["id"] in std.rules:
            err(f"retired rule {x['id']} is still defined")
        if x.get("replaced_by") not in std.rules:
            err(f"retired rule {x['id']}: replaced_by {x.get('replaced_by')} is not a rule")
    validate_sources(std.sources, "standard")
    for r in std.rules.values():
        validate_rule(r, std.sources, "standard")
    topics = scan.load_yaml(ROOT / "framework" / "coc-topics.yaml")
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

    validate_compass(std, packs_for_compass())
    validate_serious_games(std)
    validate_site()
    validate_workbench()

    pack_rule_ids = {r["id"] for pf in (ROOT / "packs").glob("*.yaml") for r in scan.load_yaml(pf).get("rules", []) or []}
    guide = (ROOT / "skill" / "csef-review" / "references" / "review-guide.md").read_text(encoding="utf-8")
    for rid in sorted(set(re.findall(r"\b(?:CORE|A|B|C|AGE|PT)-[A-Z0-9]{2,4}-\d{2}\b", guide))):
        if rid not in std.rules and rid not in pack_rule_ids:
            err(f"review-guide.md: unknown or retired rule {rid}")

    qdoc = scan.load_yaml(ROOT / "framework" / "questionnaire.yaml")
    seen = set()
    for s in qdoc.get("sections", []):
        for qq in (s.get("questions") or []) + [x for g in s.get("groups") or [] for x in g["questions"]]:
            if qq["id"] in seen:
                err(f"questionnaire.yaml: duplicate question id {qq['id']}")
            seen.add(qq["id"])
            for rid in qq.get("rules", []) or []:
                if rid not in std.rules:
                    err(f"questionnaire.yaml: {qq['id']} refers to unknown rule {rid}")
            if "rules" in qq and not (qq.get("never") and qq.get("level")):
                err(f"questionnaire.yaml: boundary {qq['id']} needs 'never' and 'level' text")
            if not set(qq.get("features", []) or []) <= FEATURE_NAMES:
                err(f"questionnaire.yaml: {qq['id']} has an unknown feature")
    for x in qdoc.get("always", []):
        for rid in x["rules"]:
            if rid not in std.rules:
                err(f"questionnaire.yaml: always item refers to unknown rule {rid}")
    for k, v in qdoc.get("phrase_sets", {}).items():
        if any(not isinstance(ph, str) for ph in v["phrases"]):
            err(f"questionnaire.yaml: phrase set {k} has a non-text entry (quote it)")

    import policy
    pq = policy.Q(ROOT)
    for code in pq.i18n:
        for m in pq.i18n_missing(code):
            err(f"framework/i18n/{code}.yaml: missing translation {m}")

    packs = {}
    for pf in sorted((ROOT / "packs").glob("*.yaml")):
        if pf.name.startswith("_"):
            continue
        res = validate_pack_file(pf)
        if res:
            packs[res[0]["pack"]["id"]] = res
    return std, packs


# --------------------------------------------------------------------------- generation
HEADER = sfe_catalogue.header(CFG)


def bands_txt(r):
    return sfe_catalogue.dimension_txt(CFG, r)


src_links = sfe_catalogue.src_links
anchor = sfe_catalogue.anchor


def rule_block(r, sources):
    return sfe_catalogue.rule_block(CFG, r, sources)


def catalogue_page(title, intro, rules, sources):
    return sfe_catalogue.catalogue_page(CFG, title, intro, rules, sources)


def checklist_page(title, rules):
    return sfe_catalogue.checklist_page(CFG, title, rules)


def semgrep_yaml(rules):
    return sfe_catalogue.semgrep_yaml(CFG, rules)


def generate(std, packs) -> dict[Path, str]:
    files: dict[Path, str] = {}
    rules = sorted(std.rules.values(), key=lambda r: r["id"])
    core = [r for r in rules if r["profiles"] == ["core"] and not r["id"].startswith("AGE-")]
    by_prof = {p: [r for r in rules if p in r["profiles"]] for p in ("A", "B", "C")}
    age = [r for r in rules if r["id"].startswith("AGE-")]
    cat = ROOT / "framework" / "catalogue"
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
           f"CSEF v{std.version}: {len(rules)} rules. Level 1 = {LEVEL_NAMES[1]}, 2 = {LEVEL_NAMES[2]}, 3 = {LEVEL_NAMES[3]}.", "",
           "| Level | MUST | SHOULD |", "|---|---|---|"]
    for t in (1, 2, 3):
        idx.append(f"| {t} {LEVEL_NAMES[t]} | {sum(1 for r in rules if r['tier'] == t and r['level'] == 'MUST')} | {sum(1 for r in rules if r['tier'] == t and r['level'] == 'SHOULD')} |")
    idx += ["", "| ID | Title | Profiles | Strength | Level | Age bands |", "|---|---|---|---|---|---|"]
    for r in rules:
        idx.append(f"| {r['id']} | {r['title']} | {', '.join(r['profiles'])} | {r['level']} | {r['tier']} | {bands_txt(r)} |")
    retired = scan.load_yaml(ROOT / "framework" / "rules.yaml").get("retired", []) or []
    if retired:
        idx += ["", "## Retired rules", "",
                "Merged into other rules. Packs, waivers and `csef-ignore` comments that use an old id keep working.", "",
                "| Old ID | Replaced by | Since |", "|---|---|---|"]
        idx += [f"| {x['id']} | {x['replaced_by']} | {x.get('since', '')} |" for x in retired]
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
        lines += ["", "## Amendments to framework rules", ""]
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

    files[ROOT / "tooling" / "semgrep" / "csef.yml"] = semgrep_yaml(rules)

    cat_json = json.dumps({
        "version": std.version,
        "features": sorted(FEATURES),
        "rules": [{"id": r["id"], "title": r["title"], "level": r["level"], "tier": r["tier"],
                   "profiles": r["profiles"], "requirement": " ".join(r["requirement"].split())} for r in rules],
    }, ensure_ascii=False).replace("</", "<\\/")
    tpl = (ROOT / "tooling" / "pack-builder.template.html").read_text(encoding="utf-8")
    import brand
    tpl = (tpl.replace("<!--BRAND_HEAD-->", brand.head("../favicon.svg"))
              .replace("/*BRAND_CSS*/", brand.tokens_css() + brand.BASE_CSS)
              .replace("<!--BRAND_LOGO-->", '<a href="../" aria-label="CSEF home" style="display:inline-block">'
                       + brand.logo("lockup", 40) + "</a>"))
    files[ROOT / "docs" / "pack-builder" / "index.html"] = tpl.replace("/*CATALOGUE*/null", cat_json)
    import policy
    files[ROOT / "docs" / "questionnaire" / "index.html"] = policy.render_form(policy.Q(ROOT), None, False, home="../")
    files[ROOT / "docs" / "questionnaire" / "csef-bundle.json"] = policy.web_bundle(ROOT)
    def site_page(name, favicon):
        return ((ROOT / "tooling" / name).read_text(encoding="utf-8")
                .replace("{version}", std.version).replace("{rules}", str(len(rules)))
                .replace("{sources}", str(len(std.sources)))
                .replace("{head}", brand.head(favicon))
                .replace("{brand_css}", brand.tokens_css() + brand.BASE_CSS)
                .replace("{logo}", brand.logo("lockup", 44)))
    files[ROOT / "docs" / "index.html"] = site_page("landing.template.html", "favicon.svg")
    files[ROOT / "docs" / "submit" / "index.html"] = site_page("submit.template.html", "../favicon.svg")
    # Guides published as pages of the website (Markdown in framework/ is the source).
    import mdpage
    files[ROOT / "docs" / "learning-data" / "index.html"] = mdpage.page(
        (ROOT / "framework" / "08-learning-data.md").read_text(encoding="utf-8"), version=std.version,
        source_path="framework/08-learning-data.md",
        description="Collect learning data from games safely, and publish only group figures: the CSEF Learning Data guide.",
        images={"data/tiers.svg": "tiers.svg"})
    import workbench
    files[ROOT / "docs" / "workbench" / "index.html"] = site_page("workbench.template.html", "../favicon.svg")
    files[ROOT / "docs" / "workbench" / "csef-bundle.json"] = workbench.web_bundle(ROOT)
    files[ROOT / "docs" / "workbench" / "example.json"] = workbench.example_bundle(ROOT)
    files[ROOT / "docs" / "learning-data" / "tiers.svg"] = (ROOT / "framework" / "data" / "tiers.svg").read_text(encoding="utf-8")

    import compass as cmp
    s2 = scan.load_standard(ROOT)
    pfs = [pf for pf in packs_for_compass() if not pf.name.startswith("_")]
    for pf in pfs:
        scan.apply_pack(s2, pf)
    files[ROOT / "framework" / "compass" / "catalogue.md"] = compass_catalogue(s2, cmp.load_compass(ROOT, [], s2))
    leg, res = source_pages(std, s2, cmp.load_compass(ROOT, pfs, s2), pfs)
    files[ROOT / "framework" / "legislation.md"] = leg
    files[ROOT / "framework" / "research.md"] = res

    sk = ROOT / "skill" / "csef-review"
    for name in ("targets.yaml", "crosswalk.yaml"):
        files[sk / "framework" / "compass" / name] = (ROOT / "framework" / "compass" / name).read_text(encoding="utf-8")
    files[sk / "framework" / "rules.yaml"] = (ROOT / "framework" / "rules.yaml").read_text(encoding="utf-8")
    files[sk / "framework" / "sources.yaml"] = (ROOT / "framework" / "sources.yaml").read_text(encoding="utf-8")
    for pf in sorted((ROOT / "packs").glob("*.yaml")):
        files[sk / "packs" / pf.name] = pf.read_text(encoding="utf-8")
    files[sk / "scripts" / "scan.py"] = (ROOT / "tooling" / "scan.py").read_text(encoding="utf-8")
    for name in ("csef-lockup-on-light.svg", "csef-mark-on-light.svg"):
        files[sk / "brand" / "svg" / name] = (ROOT / "brand" / "svg" / name).read_text(encoding="utf-8")
    files[sk / "brand" / "web" / "favicon.svg"] = (ROOT / "brand" / "web" / "favicon.svg").read_text(encoding="utf-8")
    files[sk / "framework" / "serious-games" / "criteria.yaml"] = (ROOT / "framework" / "serious-games" / "criteria.yaml").read_text(encoding="utf-8")
    for name in ("profile.yaml", "evidence-ontology.yaml"):
        files[sk / "framework" / "data" / name] = (ROOT / "framework" / "data" / name).read_text(encoding="utf-8")
    for t in ("export.py", "comms.py", "coc.py", "policy.py", "brand.py", "compass.py", "precheck.py", "metadata.py",
              "evidence.py", "workbench.py"):
        files[sk / "scripts" / t] = (ROOT / "tooling" / t).read_text(encoding="utf-8")
    for t in ("coc-topics.yaml", "questionnaire.yaml"):
        files[sk / "framework" / t] = (ROOT / "framework" / t).read_text(encoding="utf-8")
    for t in ("csef.yaml", "dpia-starter.md", "ai-risk-file.md", "waiver.md", "agent-instructions.md", "survey-register.md", "bullying-procedure.md",
              "event-catalogue.yaml"):
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
        z = out / "csef-review.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted((ROOT / "skill" / "csef-review").rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    zf.write(f, Path("csef-review") / f.relative_to(ROOT / "skill" / "csef-review"))
        print(f"Skill packaged: {z}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
