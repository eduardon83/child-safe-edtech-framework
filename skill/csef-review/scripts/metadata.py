#!/usr/bin/env python3
"""Product metadata export and label package.

One `metadata` block in csef.yaml, plus what CSEF already knows about the product, exported as:
  sg-mdf-json   Serious Games Metadata Format (DIN SPEC 91380), Core (Level 1), with the learning-games profile
  sg-mdf-xml    the same, as XML
  lrmi          schema.org LearningResource (LRMI) JSON-LD, for any learning product

DIN SPEC 91380 defines the format as a grammar and tables, with no official JSON or XML schema. The JSON and
XML here are CSEF's serialisation of that grammar: element names and nesting follow the DIN SPEC (English
names), and every file says so. Allowed values for the selection lists are in Annex A of the DIN SPEC (free
download, https://doi.org/10.31030/2853739); CSEF does not copy them and accepts free text.

  python3 tooling/metadata.py --repo path/to/product [--formats sg-mdf-json,sg-mdf-xml,lrmi] [--out-dir dist/metadata]
  python3 tooling/metadata.py --repo path/to/product --package [--findings findings.json] [--compass compass.json]

--package writes a label package: metadata, CSEF findings, the serious-game pre-check, an evidence index and a
MANIFEST.json with SHA-256 hashes, zipped. It holds no learner data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scan  # noqa: E402
import precheck  # noqa: E402

TOOL = "csef-metadata"
SERIALISATION = {
    "name": "CSEF serialisation of SG-MDF",
    "version": "1",
    "note": ("DIN SPEC 91380:2018-06 defines SG-MDF as a grammar with no official JSON or XML schema. Element names and "
             "nesting follow the DIN SPEC. This file is not published or endorsed by DIN."),
}
SGMDF_FORMAT = {"metadataFormatID": "SG-MDF", "metadataFormatName": "SG-MDF",
                "metadataFormatVersion": "DIN SPEC 91380:2018-06", "metadataFormatReleaseDate": "2018-06"}

# SG-MDF Core (Level 1): DIN reference and path in the serialisation. "[]" means every list item.
CORE = [
    ("1.1.1", "gameInfo.titleInfo.gameID"), ("1.1.2", "gameInfo.titleInfo.title"),
    ("1.2.1", "gameInfo.characterizingGoal.primaryGoal"), ("1.2.3", "gameInfo.characterizingGoal.goalDescription"),
    ("1.3", "gameInfo.abstract"), ("1.4.1", "gameInfo.keywordInfo[].keyword"), ("1.5", "gameInfo.gameGenre"),
    ("1.6", "gameInfo.gameMode"), ("1.7.1", "gameInfo.previewInfo[].previewObject"),
    ("1.7.2", "gameInfo.previewInfo[].previewObjectType"), ("1.8", "gameInfo.playTime"),
    ("1.9.1", "gameInfo.releaseInfo[].releaseVersion"), ("1.9.2", "gameInfo.releaseInfo[].releaseDate"),
    ("1.9.3", "gameInfo.releaseInfo[].releaseStatus"),
    ("2.1.1", "useInfo.applicationFields[].applicationField"), ("2.2.1", "useInfo.targetUserGroups[].targetUserGroup"),
    ("2.3.1", "useInfo.ageRestrictions[].ageRestriction"), ("2.5", "useInfo.language"),
    ("2.8", "useInfo.dataRecordingTransfer"),
    ("3.1", "distributionInfo[].distributionChannel"), ("3.3", "distributionInfo[].priceInfo"),
    ("3.4", "distributionInfo[].withCosts"),
    ("4.1.1", "technicalInfo.platformInfo[].platform"), ("4.1.2", "technicalInfo.platformInfo[].requirementInfo"),
    ("5.1.1", "involvedPartyInfo.involvedParty[].involvedPartyName"),
    ("5.1.2", "involvedPartyInfo.involvedParty[].partyRoleCode"),
    ("7.1", "metadataInfo.metadataLanguage"), ("7.2", "metadataInfo.metadataCharacterSet"),
    ("7.3.1", "metadataInfo.metadataFormat.metadataFormatID"), ("7.3.2", "metadataInfo.metadataFormat.metadataFormatName"),
    ("7.3.3", "metadataInfo.metadataFormat.metadataFormatVersion"),
    ("7.3.4", "metadataInfo.metadataFormat.metadataFormatReleaseDate"),
]
# Learning-games profile (Level 3): required when the `learning` block is used.
LEARNING_REQUIRED = [("2.L2", "useInfo.educational.learningResourceType"), ("2.L5", "useInfo.educational.context"),
                     ("2.L12", "useInfo.educational.priorKnowledge")]
LIMITS = {"gameInfo.abstract": 2000, "useInfo.dataRecordingTransfer": 2000}
PURCHASES = {
    "none": "No purchases inside the product.",
    "adult_licence": "No purchases inside the product; licences are bought by adults (school or family).",
    "subscription_adult": "No purchases inside the product; subscriptions are bought by adults.",
    "in_app_purchases": "In-app purchases, adult-facing only (CSEF CORE-COM-04).",
    "virtual_currency": "Virtual currency bought with money, adult-facing only (CSEF CORE-COM-04, A-ECO-03).",
    "ads": "Contains advertising.",
}
CONTEXT_GROUPS = {"school": ["intermediaries - teacher"], "home": ["intermediaries - parents, legal guardians"],
                  "mixed": ["intermediaries - teacher", "intermediaries - parents, legal guardians"]}
ROLE_TEXT = {"processor": "processor (the school or family decides what happens to the data)",
             "controller": "controller", "joint": "joint controller"}
PLAY_MODE = [("coop", "https://schema.org/CoOp"), ("cooperative", "https://schema.org/CoOp"),
             ("multi", "https://schema.org/MultiPlayer"), ("single", "https://schema.org/SinglePlayer")]


def _list(v):
    if v is None or v == "":
        return []
    return list(v) if isinstance(v, (list, tuple)) else [v]


def _s(v):
    return "" if v is None else (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else str(v))


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:100] or "product"


def age_range(bands) -> tuple[int, int] | None:
    ages = [scan.BAND_AGES[b] for b in bands if b in scan.BAND_AGES]
    if not ages:
        return None
    nums = [int(x) for a in ages for x in a.split("-")]
    return min(nums), max(nums)


def goal_text(g) -> str:
    if isinstance(g, dict):
        return " - ".join(_s(g[k]) for k in ("subject", "adverb", "verb") if g.get(k))
    return _s(g)


# --------------------------------------------------------------------------- data statement (SG-MDF 2.8)
def data_statement(m: dict, md: dict) -> str:
    feats = set(scan.expand_features(m.get("features") or []))
    parts = ["Personal data recorded: yes, user accounts." if "accounts" in feats
             else "User accounts: none declared."]
    tps = m.get("third_parties") or []
    if tps:
        items = []
        for t in tps:
            where = t.get("jurisdiction") or t.get("region")
            items.append(f"{t.get('name')} ({t.get('purpose')}{', ' + where if where else ''})")
        parts.append("Processed by third parties: " + "; ".join(items) + ".")
    else:
        parts.append("Third parties: none declared.")
    if m.get("gdpr_role"):
        parts.append("Provider's GDPR role: " + ROLE_TEXT.get(m["gdpr_role"], m["gdpr_role"]) + ".")
    ret = m.get("retention") or []
    if ret:
        parts.append("Retention: " + "; ".join(f"{r.get('category')} for {r.get('period')}" for r in ret) + ".")
    ai = sorted(f for f in feats if f.startswith("ai_"))
    if ai:
        parts.append("AI features: " + ", ".join(ai) + " (AI inventory kept, CSEF CORE-AI-04).")
    if md.get("privacy_notice"):
        parts.append(f"Privacy notice: {md['privacy_notice']}.")
    parts.append(f"Declared in csef.yaml; checked with CSEF {scan.TOOL_VERSION}.")
    return " ".join(parts)


# --------------------------------------------------------------------------- SG-MDF
def build_sgmdf(m: dict, scan_summary: dict | None = None) -> tuple[dict, list[str]]:
    md = m.get("metadata") or {}
    notes = []
    feats = set(scan.expand_features(m.get("features") or []))
    profiles = set(m.get("profiles") or [])

    primary = md.get("primary_goal") or ("Educational Game" if "A" in profiles else None)
    if primary and not md.get("primary_goal"):
        notes.append("primaryGoal set to 'Educational Game' from profile A; set metadata.primary_goal to change it.")
    goals = [goal_text(g) for g in _list(md.get("goal_descriptions"))]
    modes = _list(md.get("game_mode"))
    if not modes and not ({"multiplayer"} & feats):
        modes = ["single player"]
        notes.append("gameMode set to 'single player' because no multiplayer feature is declared.")

    groups = []
    rng = age_range(m.get("age_bands") or [])
    if rng:
        groups.append(f"players - pupils, ages {rng[0]} to {rng[1]}")
    groups += CONTEXT_GROUPS.get(m.get("context"), [])
    groups += [g for g in _list(md.get("target_groups")) if g not in groups]

    price_note = PURCHASES.get(m.get("monetisation") or "none", "")
    dist = []
    for d in _list(md.get("distribution")):
        pi = _s(d.get("price_info"))
        dist.append({k: v for k, v in {
            "distributionChannel": _s(d.get("channel")),
            "distributionDescription": _s(d.get("url") or d.get("description")),
            "priceInfo": (pi.rstrip(".") + ". " + price_note).strip() if pi else "",
            "withCosts": _s(d.get("with_costs")),
        }.items() if v or k in ("priceInfo", "withCosts", "distributionChannel")})
    if not dist:
        for d in m.get("distribution") or []:
            dist.append({"distributionChannel": _s(d.get("channel")), "priceInfo": "", "withCosts": ""})
        if dist:
            notes.append("distributionChannel taken from csef.yaml distribution; add metadata.distribution with "
                         "price_info and with_costs.")

    quality = [{"qualityAspect": _s(q.get("aspect")), "qualityAspectType": _s(q.get("type"))}
               for q in _list(md.get("quality"))]
    oe = ((m.get("data_collection") or {}).get("open_evidence") or {})
    if oe.get("url"):
        quality.append({"qualityAspect": f"Open evidence feed from play (csef-evidence-0.1, group figures only): {oe['url']}",
                        "qualityAspectType": "evaluation"})
    if scan_summary:
        quality.append({"qualityAspect": f"CSEF {scan_summary['version']} scan at level {scan_summary['level']} on "
                                         f"{scan_summary['date']}: {scan_summary['blocking']} blocking findings, "
                                         f"{scan_summary['review']} to review.", "qualityAspectType": "testing"})

    use = {
        "applicationFields": [{"applicationField": f} for f in (_list(md.get("application_field")) or ["education"])],
        "targetUserGroups": [{"targetUserGroup": g} for g in groups],
        "ageRestrictions": [{"ageRestriction": _s(a)} for a in _list(md.get("age_rating"))],
        "language": [_s(x) for x in _list(md.get("languages"))],
        "dataRecordingTransfer": data_statement(m, md),
    }
    for src, key in (("usability", "usability"), ("requirements", "requirements")):
        if md.get(src):
            use[key] = _s(md[src])
    lr = md.get("learning")
    if lr:
        edu = {
            "interactionType": _s(lr.get("interaction_type")),
            "learningResourceType": [_s(x) for x in _list(lr.get("resource_type"))],
            "interactivityLevel": _s(lr.get("interactivity_level")),
            "context": [_s(x) for x in (_list(lr.get("context")) or _list(m.get("context")))],
            "difficultyLevel": [_s(x) for x in _list(lr.get("difficulty"))],
            "typicalLearningTime": _s(lr.get("typical_learning_time")),
            "replayability": _s(lr.get("replayability")),
            "progressIndicators": [_s(x) for x in _list(lr.get("progress_indicators"))],
            "teachingConcept": _s(lr.get("teaching_concept")),
            "curriculum": _s(lr.get("curriculum")),
            "priorKnowledge": _s(lr.get("prior_knowledge")),
            "applicationScenarios": _s(lr.get("application_scenarios")),
        }
        use["educational"] = {k: v for k, v in edu.items() if v or k in ("learningResourceType", "context", "priorKnowledge")}
    if md.get("privacy_notice") is None and "accounts" in feats:
        notes.append("DIN SPEC guidance: when personal data is recorded or shared, link the privacy notice "
                     "(metadata.privacy_notice).")

    rel = _list(md.get("release"))
    doc = {
        "gameInfo": {
            "titleInfo": {k: v for k, v in {"gameID": _s(md.get("game_id") or slug(m.get("product"))),
                                            "title": _s(md.get("title") or m.get("product")),
                                            "subTitle": _s(md.get("subtitle"))}.items() if v or k != "subTitle"},
            "characterizingGoal": {"primaryGoal": _s(primary),
                                   **({"additionalGoal": _list(md.get("additional_goals"))} if md.get("additional_goals") else {}),
                                   "goalDescription": goals},
            "abstract": _s(md.get("abstract") or m.get("description")),
            "keywordInfo": [{"keyword": _s(k)} for k in _list(md.get("keywords"))],
            "gameGenre": [_s(g) for g in _list(md.get("genre"))],
            "gameMode": [_s(x) for x in modes],
            "previewInfo": [{"previewObject": _s(p.get("url")), "previewObjectType": _s(p.get("type"))}
                            for p in _list(md.get("previews"))],
            "playTime": _s(md.get("play_time")),
            "releaseInfo": [{"releaseVersion": _s(r.get("version")), "releaseDate": _s(r.get("date")),
                             "releaseStatus": _s(r.get("status"))} for r in rel],
        },
        "useInfo": use,
        "distributionInfo": dist,
        "technicalInfo": {"platformInfo": [{k: v for k, v in {
            "platform": _s(p.get("platform")), "requirementInfo": _s(p.get("requirements")),
            "furtherDevices": _s(p.get("devices")), "installation": _s(p.get("installation"))}.items()
            if v or k in ("platform", "requirementInfo")} for p in _list(md.get("platforms"))]},
        "involvedPartyInfo": {"involvedParty": [{k: v for k, v in {
            "involvedPartyName": _s(p.get("name")), "partyRoleCode": _s(p.get("role")),
            "involvedPartyReference": _s(p.get("url")), "partyInfo": _s(p.get("info"))}.items()
            if v or k in ("involvedPartyName", "partyRoleCode", "involvedPartyReference")}
            for p in _list(md.get("parties"))]},
        **({"qualityInfo": {"qualityFeature": quality}} if quality else {}),
        "metadataInfo": {"metadataLanguage": _s(md.get("metadata_language") or "en"),
                         "metadataCharacterSet": "UTF-8 (Unicode, ISO/IEC 10646)",
                         "metadataFormat": dict(SGMDF_FORMAT)},
    }
    return doc, notes


def _values(doc, path):
    cur = [doc]
    for part in path.split("."):
        many = part.endswith("[]")
        key = part[:-2] if many else part
        nxt = []
        for c in cur:
            v = c.get(key) if isinstance(c, dict) else None
            if v is None:
                continue
            if many or isinstance(v, list):
                nxt.extend(v if isinstance(v, list) else [v])
            else:
                nxt.append(v)
        cur = nxt
    return cur


def validate_sgmdf(doc: dict) -> list[dict]:
    """Missing or too long fields, with the DIN reference."""
    problems = []
    checks = CORE + (LEARNING_REQUIRED if "educational" in doc.get("useInfo", {}) else [])
    for ref, path in checks:
        vals = _values(doc, path)
        container = path.rsplit(".", 1)[0]
        if not vals or any(v in ("", None, []) for v in vals) or (
                "[]" in container and not _values(doc, container.replace("[]", ""))):
            problems.append({"ref": ref, "field": path.replace("[]", ""), "problem": "missing"})
    for path, n in LIMITS.items():
        for v in _values(doc, path):
            if len(v) > n:
                problems.append({"ref": "", "field": path, "problem": f"longer than {n} characters"})
    return problems


def sgmdf_json(doc: dict) -> str:
    return json.dumps({"serialisation": SERIALISATION, "SG-MD": doc}, indent=2, ensure_ascii=False) + "\n"


def _xml(parent, key, value):
    if isinstance(value, list):
        for v in value:
            _xml(parent, key, v)
    elif isinstance(value, dict):
        el = ET.SubElement(parent, key)
        for k, v in value.items():
            _xml(el, k, v)
    else:
        ET.SubElement(parent, key).text = _s(value)


def sgmdf_xml(doc: dict) -> str:
    root = ET.Element("SG-MD", {"serialisation": f"csef-{SERIALISATION['version']}"})
    for k, v in doc.items():
        _xml(root, k, v)
    ET.indent(root)
    body = ET.tostring(root, encoding="unicode")
    note = SERIALISATION["note"].replace("--", "-")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<!-- {SERIALISATION["name"]}. {note} -->\n{body}\n'


# --------------------------------------------------------------------------- LRMI / schema.org
def build_lrmi(m: dict, doc: dict) -> dict:
    md = m.get("metadata") or {}
    gi, ui = doc["gameInfo"], doc["useInfo"]
    is_game = bool(md.get("is_game", "A" in set(m.get("profiles") or [])))
    out = {"@context": "https://schema.org",
           "@type": ["LearningResource", "VideoGame" if is_game else "SoftwareApplication"],
           "identifier": gi["titleInfo"]["gameID"], "name": gi["titleInfo"]["title"], "description": gi["abstract"]}
    kw = [k["keyword"] for k in gi["keywordInfo"]]
    if kw:
        out["keywords"] = ", ".join(kw)
    if ui["language"]:
        out["inLanguage"] = ui["language"]
    rng = age_range(m.get("age_bands") or [])
    if rng:
        out["typicalAgeRange"] = f"{rng[0]}-{rng[1]}"
    roles = ["student"] + (["teacher"] if m.get("context") in ("school", "mixed") else []) + \
            (["parent"] if m.get("context") in ("home", "mixed") else [])
    out["audience"] = [{"@type": "EducationalAudience", "educationalRole": r} for r in roles]
    goal = (m.get("serious_game") or {}).get("characterizing_goal") or md.get("teaches")
    teaches = _list(goal) or list(gi["characterizingGoal"]["goalDescription"])
    if teaches:
        out["teaches"] = teaches
    edu = ui.get("educational") or {}
    if edu.get("learningResourceType"):
        out["learningResourceType"] = edu["learningResourceType"]
    if edu.get("applicationScenarios"):
        out["educationalUse"] = edu["applicationScenarios"]
    if edu.get("curriculum"):
        out["educationalAlignment"] = [{"@type": "AlignmentObject", "alignmentType": "educationalFramework",
                                        "targetName": edu["curriculum"]}]
    if edu.get("priorKnowledge"):
        out["competencyRequired"] = edu["priorKnowledge"]
    if edu.get("typicalLearningTime"):
        out["timeRequired"] = edu["typicalLearningTime"]
    rating = [a["ageRestriction"] for a in ui["ageRestrictions"]]
    if rating:
        out["contentRating"] = rating[0]
    if gi["releaseInfo"]:
        out["version"] = gi["releaseInfo"][0]["releaseVersion"]
        out["datePublished"] = gi["releaseInfo"][0]["releaseDate"]
    costs = {d.get("withCosts", "").lower() for d in doc["distributionInfo"]}
    if costs and costs <= {"no", "free"}:
        out["isAccessibleForFree"] = True
    elif costs & {"yes"}:
        out["isAccessibleForFree"] = False
    urls = [d["distributionDescription"] for d in doc["distributionInfo"]
            if precheck.URL_RE.match(d.get("distributionDescription", ""))]
    if urls:
        out["url"] = urls[0]
    imgs = [p["previewObject"] for p in gi["previewInfo"] if p["previewObject"]]
    if imgs:
        out["image"] = imgs[0]
    for p in doc["involvedPartyInfo"]["involvedParty"]:
        org = {"@type": "Organization", "name": p["involvedPartyName"]}
        if p.get("involvedPartyReference"):
            org["url"] = p["involvedPartyReference"]
        role = p["partyRoleCode"].lower()
        key = "publisher" if "publish" in role else "author" if "develop" in role else "contributor"
        out.setdefault(key, []).append(org)
    plats = [p["platform"] for p in doc["technicalInfo"]["platformInfo"] if p["platform"]]
    if plats:
        out["gamePlatform" if is_game else "operatingSystem"] = plats
    if is_game:
        modes = []
        for gm in gi["gameMode"]:
            for k, v in PLAY_MODE:
                if k in gm.lower() and v not in modes:
                    modes.append(v)
                    break
        if modes:
            out["playMode"] = modes
    else:
        out["applicationCategory"] = "EducationalApplication"
    if md.get("privacy_notice"):
        out["usageInfo"] = md["privacy_notice"]
    return out


# --------------------------------------------------------------------------- package
def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def evidence_index(repo: Path, m: dict, pre: dict | None) -> list[dict]:
    rows = []
    for c in (pre or {}).get("criteria", []):
        for e in (c.get("claim") or {}).get("evidence", []):
            rows.append({"criterion": c["id"], "ref": e["ref"], "found": e["found"]})
    for q in _list((m.get("metadata") or {}).get("quality")):
        if q.get("url"):
            rows.append({"criterion": "quality", "ref": q["url"], "found": None})
    return rows


README = """CSEF label package
==================

Prepared with the Child-Safe EdTech Framework (CSEF). It describes one product for a label or catalogue.

metadata/sg-mdf.json, sg-mdf.xml  Serious Games Metadata Format (DIN SPEC 91380), CSEF serialisation
metadata/lrmi.jsonld              schema.org LearningResource description
csef/findings.json                CSEF scan results (child safety, privacy, commercial practices, design)
precheck/                         serious-game quality pre-check (criteria of Caserman et al. 2020)
evidence/index.json               evidence the team cites, with links or file paths
MANIFEST.json                     list of files with SHA-256 hashes

The pre-check is not a label. No labelling body issued or endorsed this package. It holds no learner data.
"""


def build_package(repo: Path, root: Path, out_dir: Path, findings_path=None, compass_path=None,
                  include_evidence=False, level=None) -> tuple[Path, dict]:
    mpath = scan.find_manifest(repo, None)
    m = scan.load_yaml(mpath) or {}
    pre, findings = precheck.run(repo, root, None, findings_path, compass_path, level)
    summ = {"version": (findings.get("tool") or {}).get("version", scan.TOOL_VERSION), "level": findings.get("level"),
            "date": (findings.get("generated") or "")[:10], "blocking": pre["scan"]["blocking"],
            "review": pre["scan"]["review"]}
    doc, notes = build_sgmdf(m, summ)
    problems = validate_sgmdf(doc)
    gid = doc["gameInfo"]["titleInfo"]["gameID"]
    stamp = dt.date.today().isoformat()
    work = out_dir / f"csef-label-package-{gid}-{stamp}"
    if work.exists():
        shutil.rmtree(work)
    (work / "metadata").mkdir(parents=True)
    (work / "metadata" / "sg-mdf.json").write_text(sgmdf_json(doc), encoding="utf-8")
    (work / "metadata" / "sg-mdf.xml").write_text(sgmdf_xml(doc), encoding="utf-8")
    (work / "metadata" / "lrmi.jsonld").write_text(json.dumps(build_lrmi(m, doc), indent=2, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")
    (work / "csef").mkdir()
    (work / "csef" / "findings.json").write_text(json.dumps(findings, indent=2, ensure_ascii=False, default=str),
                                                 encoding="utf-8")
    precheck.write_outputs(pre, work / "precheck", ["json", "md", "html"])
    if compass_path:
        shutil.copy(compass_path, work / "csef" / "compass.json")
    ev = evidence_index(repo, m, pre)
    (work / "evidence").mkdir()
    if include_evidence:
        for e in ev:
            if e["found"]:
                src = repo / e["ref"].split("#", 1)[0]
                dst = work / "evidence" / "files" / e["ref"].split("#", 1)[0]
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_file():
                    shutil.copy(src, dst)
    (work / "evidence" / "index.json").write_text(json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8")
    (work / "README.txt").write_text(README, encoding="utf-8")
    files = sorted(p for p in work.rglob("*") if p.is_file())
    manifest = {
        "package_format": 1, "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "tool": {"name": TOOL, "version": scan.TOOL_VERSION}, "product": m.get("product"), "gameID": gid,
        "sgmdf_core_complete": not problems, "sgmdf_problems": problems, "notes": notes,
        "precheck_summary": pre["summary"], "disclaimer": precheck.DISCLAIMER,
        "files": [{"path": str(p.relative_to(work)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in files],
    }
    (work / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    zpath = out_dir / f"{work.name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(work.rglob("*")):
            if p.is_file():
                z.write(p, f"{work.name}/{p.relative_to(work)}")
    return zpath, manifest


# --------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export product metadata (SG-MDF, LRMI) and build a label package.")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--manifest")
    ap.add_argument("--framework-root", default=None)
    ap.add_argument("--out-dir", default="dist/metadata")
    ap.add_argument("--formats", default="sg-mdf-json,sg-mdf-xml,lrmi")
    ap.add_argument("--package", action="store_true", help="build a label package zip")
    ap.add_argument("--findings", help="findings.json from scan.py (default: run a scan)")
    ap.add_argument("--compass", help="compass.json from compass.py (optional)")
    ap.add_argument("--include-evidence", action="store_true", help="copy local evidence files into the package")
    ap.add_argument("--level", type=int, choices=[1, 2, 3])
    ap.add_argument("--strict", action="store_true", help="exit 1 if SG-MDF Core fields are missing")
    a = ap.parse_args(argv)
    repo = Path(a.repo)
    root = Path(a.framework_root) if a.framework_root else scan.default_root()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if a.package:
        z, man = build_package(repo, root, out, a.findings, a.compass, a.include_evidence, a.level)
        problems = man["sgmdf_problems"]
        print(f"{TOOL}: package {z} ({len(man['files'])} files). SG-MDF Core "
              + ("complete." if not problems else f"missing {len(problems)} field(s)."))
    else:
        mpath = scan.find_manifest(repo, a.manifest)
        if not mpath or not mpath.exists():
            print(f"{TOOL}: no csef.yaml found in {repo}", file=sys.stderr)
            return 2
        m = scan.load_yaml(mpath) or {}
        doc, notes = build_sgmdf(m)
        problems = validate_sgmdf(doc)
        fm = {f.strip() for f in a.formats.split(",")}
        written = []
        if "sg-mdf-json" in fm:
            (out / "sg-mdf.json").write_text(sgmdf_json(doc), encoding="utf-8"); written.append("sg-mdf.json")
        if "sg-mdf-xml" in fm:
            (out / "sg-mdf.xml").write_text(sgmdf_xml(doc), encoding="utf-8"); written.append("sg-mdf.xml")
        if "lrmi" in fm:
            (out / "lrmi.jsonld").write_text(json.dumps(build_lrmi(m, doc), indent=2, ensure_ascii=False) + "\n",
                                             encoding="utf-8"); written.append("lrmi.jsonld")
        for n in notes:
            print(f"  note: {n}")
        print(f"{TOOL}: wrote {', '.join(written)} to {out}. SG-MDF Core "
              + ("complete." if not problems else f"missing {len(problems)} field(s)."))
    for p in problems:
        print(f"  {p['ref'] or '-':6} {p['field']}: {p['problem']}")
    return 1 if (a.strict and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
