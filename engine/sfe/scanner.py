"""A generic scanner: which rules apply to a product, what the code and the manifest show, and the report.

A framework supplies its rules, its manifest checks (name -> function) and its config. Severities:

  BLOCK   a MUST rule with a high-confidence finding
  REVIEW  a MUST rule with a medium-confidence finding
  WARN    a SHOULD rule with a finding
  HUMAN   a rule in scope that only a person can check (detection: manual, or no finding to show either way)
  WAIVED  a finding covered by an inline ignore comment or a dated waiver in the manifest
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import Config
from .patterns import Ignore, collect_dependencies, dependency_findings, iter_files, read_text, regex_findings

SEVERITY_ORDER = ["BLOCK", "REVIEW", "WARN", "HUMAN", "WAIVED"]


@dataclass
class Finding:
    rule: str
    severity: str
    title: str
    strength: str
    tier: int
    where: str = ""
    detail: str = ""
    improvement: str = ""
    sources: list = field(default_factory=list)
    waived: str = ""


def expand_features(cfg: Config, features) -> set:
    out = set()
    for f in features or []:
        out |= set(cfg.feature_groups.get(f, [f]))
    return out


def in_scope(cfg: Config, rule, manifest: dict | None, level: int) -> bool:
    if rule["tier"] > level:
        return False
    m = manifest or {}
    profiles = set(m.get("profiles") or ["core"]) | {"core"}
    if not set(rule["profiles"]) & profiles:
        return False
    dims = rule.get(cfg.dimension_key, ["all"])
    declared = set(m.get(cfg.dimension_key) or [])
    if dims != ["all"] and declared and not set(dims) & declared:
        return False
    feats = set(rule.get("features") or [])
    if feats and not feats & expand_features(cfg, m.get("features")):
        return False
    return True


def _waiver(manifest, rule_id, today):
    for w in (manifest or {}).get("waivers", []) or []:
        if w.get("rule") == rule_id:
            until = w.get("until")
            if until and str(until) < today.isoformat():
                continue
            return f"waiver: {w.get('reason', 'no reason given')}" + (f" (until {until})" if until else "")
    return None


def run(cfg: Config, repo: Path, rules: list, manifest: dict | None, level: int = 1, *, manifest_checks: dict,
        ignore: Ignore | None = None, description_only: bool = False, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    repo = Path(repo)
    files_cache = []
    deps = {}
    if not description_only:
        for p in iter_files(repo, cfg.manifest_names):
            t = read_text(p)
            if t is not None:
                files_cache.append((str(p.relative_to(repo)), t.splitlines(), t))
        deps = collect_dependencies(repo)
    findings: list[Finding] = []
    in_scope_ids = []
    for r in sorted(rules, key=lambda r: r["id"]):
        if not in_scope(cfg, r, manifest, level):
            continue
        in_scope_ids.append(r["id"])
        base = dict(rule=r["id"], title=r["title"], strength=r["level"], tier=r["tier"],
                    improvement=r["improvement"].strip(), sources=list(r["sources"]))
        hit = False
        det = r.get("detection") or {}
        for p in det.get("patterns", []) or []:
            conf = p.get("confidence", "medium")
            sev = "WARN" if r["level"] == "SHOULD" else ("BLOCK" if conf == "high" else "REVIEW")
            if p["type"] == "regex" and not description_only:
                for rel, line, text, ign in regex_findings(r, p, files_cache, repo, ignore):
                    hit = True
                    w = ign and f"inline: {ign}"
                    findings.append(Finding(severity="WAIVED" if w else sev, where=f"{rel}:{line}", detail=text, waived=w or "", **base))
            elif p["type"] == "dependency" and not description_only:
                for f, name in dependency_findings(p, deps):
                    hit = True
                    findings.append(Finding(severity=sev, where=f, detail=f"dependency {name}", **base))
            elif p["type"] == "manifest":
                fn = manifest_checks[p["check"]]
                for msg in fn(manifest, repo, p) or []:
                    hit = True
                    findings.append(Finding(severity=sev, where="manifest", detail=msg, **base))
        if not hit and det.get("method") in ("manual", "mixed"):
            findings.append(Finding(severity="HUMAN", detail=det.get("human", "Check by hand and keep the evidence."), **base))
    for f in findings:
        if f.severity in ("BLOCK", "REVIEW", "WARN"):
            w = _waiver(manifest, f.rule, today)
            if w:
                f.severity, f.waived = "WAIVED", w
    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f.severity), f.rule, f.where))
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITY_ORDER}
    return {"level": level, "rules_in_scope": in_scope_ids, "findings": findings, "counts": counts,
            "date": today.isoformat(), "description_only": description_only}


def verdict(result) -> str:
    c = result["counts"]
    if c["BLOCK"]:
        return "Not ready: fix the BLOCK items first."
    if c["REVIEW"] or c["WARN"]:
        return "Review needed: no blocking finding, but items need a decision."
    return "No automated finding. The HUMAN items still need a person and evidence."


def render_markdown(cfg: Config, result, sources: dict, product: str = "") -> str:
    c = result["counts"]
    lines = [f"# {cfg.short} report{': ' + product if product else ''}", "",
             f"Level {result['level']} ({cfg.levels[result['level']]}) · {len(result['rules_in_scope'])} rules in scope · {result['date']}"
             + (" · description only (code not read)" if result["description_only"] else ""), "",
             f"**{verdict(result)}**", "",
             "| " + " | ".join(SEVERITY_ORDER) + " |", "|" + "---|" * len(SEVERITY_ORDER),
             "| " + " | ".join(str(c[s]) for s in SEVERITY_ORDER) + " |", ""]
    for sev in SEVERITY_ORDER:
        items = [f for f in result["findings"] if f.severity == sev]
        if not items:
            continue
        lines += [f"## {sev}", ""]
        last = None
        for f in items:
            if f.rule != last:
                if last is not None:
                    lines.append("")
                srcs = ", ".join(f"[{s}]({sources[s]['url']})" if sources.get(s, {}).get("url") else s for s in f.sources)
                lines += [f"### {f.rule}: {f.title} ({f.strength}, level {f.tier})", "", f"How to improve: {f.improvement}", "",
                          f"Sources: {srcs}", ""]
                last = f.rule
            loc = f"`{f.where}` " if f.where else ""
            lines.append(f"- {loc}{f.detail}" + (f" ({f.waived})" if f.waived else ""))
        lines.append("")
    lines += ["---", "", f"{cfg.name} ({cfg.short}). Automated checks find signs, not proof. "
              "This report is not legal or regulatory advice.", ""]
    return "\n".join(lines)


def to_json(cfg: Config, result, product: str = "") -> str:
    d = dict(result)
    d["findings"] = [asdict(f) for f in result["findings"]]
    d["framework"] = cfg.short
    d["product"] = product
    d["verdict"] = verdict(result)
    return json.dumps(d, indent=2, ensure_ascii=False) + "\n"


def to_sarif(cfg: Config, result, rules_by_id: dict) -> str:
    level = {"BLOCK": "error", "REVIEW": "warning", "WARN": "note"}
    res = []
    for f in result["findings"]:
        if f.severity not in level:
            continue
        loc = {}
        if ":" in f.where and f.where != "manifest":
            path, _, line = f.where.rpartition(":")
            loc = {"locations": [{"physicalLocation": {"artifactLocation": {"uri": path}, "region": {"startLine": int(line)}}}]}
        res.append({"ruleId": f.rule, "level": level[f.severity], "message": {"text": f"{f.title}. {f.detail}"}, **loc})
    used = sorted({f.rule for f in result["findings"]})
    sarif = {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
             "runs": [{"tool": {"driver": {"name": cfg.short, "informationUri": cfg.site or cfg.repo,
                                           "rules": [{"id": i, "shortDescription": {"text": rules_by_id[i]["title"]}} for i in used]}},
                       "results": res}]}
    return json.dumps(sarif, indent=2, ensure_ascii=False) + "\n"
