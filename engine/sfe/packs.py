"""Packs: country, sector, literature and company packs that extend a framework without forking it.

A pack is a YAML file with any of: pack (metadata), parameters, sources, rules, amend, policy.

  - sources: added to the registry; ids may not clash.
  - rules: new rules, prefixed with the pack id in upper case (PT-LNG-01).
  - amend: make an existing rule stricter only: add_sources, note, level SHOULD -> MUST, tier to a lower number,
    add_patterns. A pack can never weaken or remove a rule.
  - policy (company packs): minimum_level, no_go, forbid_dependencies, forbid_phrases, forbid_patterns,
    require_decision_for_features, review_every_days. Creates <ID>-POL-nn rules citing a <ID>-POLICY source.
  - parameters: values shown in reports (digital consent age, authorities, helplines).

Lifted from CSEF tooling/scan.py (apply_pack, apply_policy) and made framework-neutral. Licence: Apache-2.0
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import Config

AMEND_KEYS = {"rule", "add_sources", "note", "level", "tier", "add_patterns"}
POLICY_KEYS = {"minimum_level", "no_go", "forbid_dependencies", "forbid_phrases", "forbid_patterns",
               "require_decision_for_features", "review_every_days", "require_agent_instructions"}


@dataclass
class Merged:
    rules: dict
    sources: dict
    minimum_level: int = 1
    minimum_level_by: str = ""
    parameters: dict = field(default_factory=dict)
    packs: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def merged(rules: list, sources: dict) -> Merged:
    rs = {}
    for r in rules:
        r = dict(r)
        r.setdefault("notes", [])
        r.setdefault("origin", "framework")
        rs[r["id"]] = r
    return Merged(rules=rs, sources={k: dict(v) for k, v in sources.items()})


def load(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def apply(cfg: Config, m: Merged, doc: dict, path: str = "", manifest_checks=()) -> None:
    meta = doc.get("pack") or {}
    pid = str(meta.get("id") or Path(path).stem)
    pfx = pid.upper()
    for s in doc.get("sources", []) or []:
        if s["id"] in m.sources:
            raise ValueError(f"Pack {pid}: source id {s['id']} already exists")
        m.sources[s["id"]] = dict(s, origin=f"pack:{pid}")
    for r in doc.get("rules", []) or []:
        if r["id"] in m.rules:
            raise ValueError(f"Pack {pid}: rule id {r['id']} already exists")
        if not r["id"].startswith(pfx + "-"):
            raise ValueError(f"Pack {pid}: rule {r['id']} must start with {pfx}-")
        m.rules[r["id"]] = dict(r, notes=list(r.get("notes", []) or []), origin=f"pack:{pid}")
    for a in doc.get("amend", []) or []:
        rid = a.get("rule")
        if rid not in m.rules:
            raise ValueError(f"Pack {pid}: amend targets unknown rule {rid}")
        extra = set(a) - AMEND_KEYS
        if extra:
            raise ValueError(f"Pack {pid}: amend of {rid} has unknown keys {sorted(extra)}")
        r = m.rules[rid]
        for sid in a.get("add_sources", []) or []:
            if sid not in m.sources:
                raise ValueError(f"Pack {pid}: amend of {rid} cites unknown source {sid}")
            if sid not in r["sources"]:
                r["sources"] = list(r["sources"]) + [sid]
        if a.get("note"):
            r["notes"] = list(r["notes"]) + [f"[{pfx}] {a['note']}"]
        if "level" in a:
            if a["level"] == "MUST":
                r["level"] = "MUST"
            elif r["level"] == "MUST":
                raise ValueError(f"Pack {pid}: cannot weaken {rid} to {a['level']}")
        if "tier" in a:
            t = int(a["tier"])
            if t > int(r["tier"]):
                raise ValueError(f"Pack {pid}: cannot move {rid} to a higher (less binding) level")
            r["tier"] = t
        if a.get("add_patterns"):
            det = dict(r.get("detection") or {"method": "static"})
            det["patterns"] = list(det.get("patterns", []) or []) + list(a["add_patterns"])
            if det.get("method") == "manual":
                det["method"] = "mixed"
            r["detection"] = det
    _policy(cfg, m, doc, pid, meta, set(manifest_checks))
    m.parameters.update({f"{pid}.{k}": v for k, v in (doc.get("parameters") or {}).items()})
    m.packs.append({"id": pid, "title": meta.get("title", pid), "path": str(path), "version": str(meta.get("version", "?")),
                    "status": meta.get("status", ""), "jurisdiction": meta.get("jurisdiction", "")})


def _policy_rule(cfg, rid, title, requirement, rationale, improvement, sources, patterns, method="static"):
    return {"id": rid, "title": title, "level": "MUST", "tier": 1, "profiles": ["core"], cfg.dimension_key: ["all"],
            "requirement": requirement, "rationale": rationale, "improvement": improvement, "effort": "low",
            "sources": sources, "detection": {"method": method, "patterns": patterns}, "notes": [], "no_go": True}


def _policy(cfg: Config, m: Merged, doc: dict, pid: str, meta: dict, manifest_checks: set) -> None:
    if "policy" not in doc:
        return
    pol = doc.get("policy") or {}
    extra = set(pol) - POLICY_KEYS
    if extra:
        raise ValueError(f"Pack {pid}: unknown policy keys {sorted(extra)}")
    pfx, title = pid.upper(), meta.get("title", pid)
    src = f"{pfx}-POLICY"
    m.sources.setdefault(src, {
        "id": src, "title": f"{title} (organisation policy)", "type": "policy", "jurisdiction": meta.get("jurisdiction", "ORG"),
        "status": f"Organisation policy v{meta.get('version', '?')}. Binding for this organisation's products, not law",
        "url": meta.get("url"), "verified": str(meta.get("date", dt.date.today().isoformat())), "origin": f"pack:{pid}"})
    ml = pol.get("minimum_level")
    if ml:
        ml = int(ml)
        if ml not in (1, 2, 3):
            raise ValueError(f"Pack {pid}: minimum_level must be 1, 2 or 3")
        if ml > m.minimum_level:
            m.minimum_level, m.minimum_level_by = ml, title
    for rid in pol.get("no_go", []) or []:
        if rid not in m.rules:
            raise ValueError(f"Pack {pid}: no_go targets unknown rule {rid}")
        r = m.rules[rid]
        r["level"], r["tier"], r["no_go"] = "MUST", 1, True
        if src not in r["sources"]:
            r["sources"] = list(r["sources"]) + [src]
        r["notes"] = list(r["notes"]) + [f"[{pfx}] No-go for {title}: blocks at every level."]
    n = 0

    def nid():
        nonlocal n
        n += 1
        rid = f"{pfx}-POL-{n:02d}"
        if rid in m.rules:
            raise ValueError(f"Pack {pid}: {rid} already exists; the POL area is reserved for policy rules")
        return rid

    deps = pol.get("forbid_dependencies") or []
    if deps:
        rid = nid()
        m.rules[rid] = _policy_rule(cfg, rid, f"Packages not used at {title}", f"These packages are not used in {title} products: {', '.join(deps)}.",
                                    f"Decision recorded in the {title} policy.", "Remove the package or get a waiver from the policy owner.",
                                    [src], [{"type": "dependency", "confidence": "high", "names": list(deps)}])
    phrases = pol.get("forbid_phrases") or []
    if phrases:
        rid = nid()
        rx = "(" + "|".join(re.escape(str(x)) for x in phrases) + ")"
        m.rules[rid] = _policy_rule(cfg, rid, f"Wording not used at {title}", f"Text shown to people does not contain: {'; '.join(map(str, phrases))}.",
                                    f"Decision recorded in the {title} policy (pressure, guilt or scarcity wording).",
                                    "Rewrite the text in neutral, informative words.", [src],
                                    [{"type": "regex", "confidence": "high", "flags": "i", "pattern": rx}])
    for item in pol.get("forbid_patterns") or []:
        rid = nid()
        m.rules[rid] = _policy_rule(cfg, rid, item.get("title", f"Pattern not used at {title}"),
                                    item.get("requirement", f"Code does not match: {item['pattern']}"),
                                    item.get("rationale", f"Decision recorded in the {title} policy."),
                                    item.get("improvement", "Remove the construct or get a waiver."), [src],
                                    [{"type": "regex", "confidence": "high", "flags": item.get("flags", ""), "pattern": item["pattern"],
                                      **({"globs": item["globs"]} if item.get("globs") else {})}])
    feats = pol.get("require_decision_for_features") or []
    if feats:
        if "decision_records" in manifest_checks:
            rid = nid()
            m.rules[rid] = _policy_rule(cfg, rid, f"Decision records for sensitive features ({title})",
                                        f"Each of these features, when declared, has a decision record linked under `decisions:` in the manifest: {', '.join(feats)}.",
                                        "Sensitive features need a recorded decision with a named approver before release.",
                                        "Write a decision record and link it under `decisions: {feature: path}`.", [src],
                                        [{"type": "manifest", "check": "decision_records", "confidence": "high", "features": list(feats)}], "manifest")
        else:
            m.warnings.append(f"Pack {pid}: require_decision_for_features is not supported by {cfg.short}")
    days = pol.get("review_every_days")
    if days:
        if "review_stale" in manifest_checks:
            rid = nid()
            m.rules[rid] = _policy_rule(cfg, rid, f"Manifest reviewed every {days} days ({title})",
                                        f"The manifest's last review is no older than {days} days.",
                                        "Keeps the declared features, data flows and level in line with the product.",
                                        "Review the manifest with the product owner and update the review date.", [src],
                                        [{"type": "manifest", "check": "review_stale", "confidence": "high", "days": int(days)}], "manifest")
        else:
            m.warnings.append(f"Pack {pid}: review_every_days is not supported by {cfg.short}")
    if pol.get("require_agent_instructions"):
        m.warnings.append(f"Pack {pid}: require_agent_instructions is handled by {cfg.short}'s own scanner, if at all")


def validate(cfg: Config, doc: dict, base_rules: list, base_sources: dict, err, manifest_checks=(), repo_checks=()) -> None:
    """Validate a pack on its own and merged with the framework. Reports problems through err(msg)."""
    from .catalogue import validate_rule
    meta = doc.get("pack") or {}
    pid = str(meta.get("id") or "?")
    if not re.fullmatch(r"[a-z0-9]{2,8}", pid):
        err(f"pack id '{pid}' must be 2 to 8 lowercase letters or digits")
    m = merged(base_rules, base_sources)
    try:
        apply(cfg, m, doc, pid, manifest_checks)
    except (ValueError, KeyError) as e:
        err(f"pack {pid}: {e}")
        return
    for r in doc.get("rules", []) or []:
        validate_rule(cfg, m.rules[r["id"]], m.sources, f"pack {pid}", err, repo_checks, manifest_checks)
    for s in doc.get("sources", []) or []:
        for k in cfg.source_required:
            if k not in s:
                err(f"pack {pid} source {s.get('id')}: missing '{k}'")
