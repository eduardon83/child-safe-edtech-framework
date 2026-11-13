#!/usr/bin/env python3
"""CSEF scanner: pre-compliance checks for software used by children.

Reads a product manifest (csef.yaml), selects the rules of the Child-Safe EdTech
Standard that apply (profiles, age bands, compliance level, packs), runs static
and manifest checks, and writes:

  report.md         pre-compliance report with findings, human checks and sources
  improvements.md   prioritised list of improvements, including next-level items
  findings.json     machine-readable results
  findings.sarif    for GitHub code scanning

This is a pre-compliance aid. It cannot establish legal compliance.

Usage:
  python3 scan.py --repo PATH [--manifest FILE] [--level 1|2|3] [--pack FILE ...]
                  [--out-dir DIR] [--format text|json|none] [--fail-on block|review|warn|never]
                  [--export html,pdf,docx]   (dashboard.html, report.pdf, report.docx via tooling/export.py)

Licence: Apache-2.0
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("CSEF scanner needs PyYAML: pip install pyyaml")

TOOL_NAME = "csef-scan"
TOOL_VERSION = "0.8.0"

PROFILES = {"core", "A", "B", "C"}
BANDS = ["B1", "B2", "B3", "B4", "B5"]
BAND_AGES = {"B1": "3-5", "B2": "6-9", "B3": "10-12", "B4": "13-15", "B5": "16-17"}
LEVEL_NAMES = {1: "Legal baseline", 2: "Forward-compliant", 3: "Best practice"}
SEVERITY_ORDER = ["BLOCK", "REVIEW", "WARN", "HUMAN", "NEXT", "WAIVED"]
EFFORT_ORDER = {"low": 0, "medium": 1, "high": 2}
# csef.* first; the cses.* names from v0.5 and earlier are still accepted.
MANIFEST_NAMES = ["csef.yaml", "csef.yml", ".csef/manifest.yaml", ".csef/csef.yaml",
                  "cses.yaml", "cses.yml", ".cses/manifest.yaml", ".cses/cses.yaml"]

SOURCE_EXT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".html", ".htm", ".css", ".scss", ".less",
    ".py", ".java", ".kt", ".kts", ".swift", ".m", ".dart", ".cs", ".go", ".rb", ".php",
    ".sql", ".json", ".yaml", ".yml", ".xml", ".plist", ".gd", ".lua", ".gradle", ".strings",
    ".po", ".arb", ".properties", ".toml", ".env",
    ".prefab", ".asset", ".unity", ".asmdef", ".tscn", ".tres", ".godot",          # Unity and Godot text assets
    ".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".scala", ".ex", ".exs", ".m", ".mm", ".rules",
}
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".nuxt", "out", "coverage", "vendor",
    "Pods", ".gradle", ".idea", ".vscode", "__pycache__", ".venv", "venv", "env", "Library",
    "Temp", "csef-report", "cses-report", ".csef", ".cses", "Logs", "obj", "UserSettings", "Build", "Builds", ".godot", "target",
}
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Podfile.lock",
    "pubspec.lock", "composer.lock", "Cargo.lock",
}
MAX_FILE_BYTES = 1_000_000
EEA_REGION = re.compile(
    r"(^eu\b|\beu-|-eu\b|europe|\beea\b|frankfurt|ireland|dublin|paris|stockholm|milan|madrid|"
    r"lisbon|lisboa|amsterdam|warsaw|vienna|brussels|helsinki|copenhagen|oslo|"
    r"^(at|be|bg|hr|cy|cz|dk|ee|fi|fr|de|gr|hu|ie|it|lv|lt|lu|mt|nl|pl|pt|ro|sk|si|es|se|is|li|no)$)",
    re.I,
)

MANIFEST_CHECKS = [
    "manifest_missing", "kids_act_scope_missing", "dpia_missing", "third_party_without_dpa",
    "gdpr_role_missing", "transfer_outside_eea", "retention_missing", "monetisation_for_minors",
    "ai_without_inventory", "high_risk_without_risk_file", "security_policy_missing",
    "decision_records", "review_stale",
]


# --------------------------------------------------------------------------- data
@dataclass
class Finding:
    rule_id: str
    severity: str
    message: str
    path: str | None = None
    line: int | None = None
    evidence: str | None = None
    note: str | None = None
    confidence: str | None = None
    raw: str | None = None          # severity the finding would have at Level 3 (for per-level views)


@dataclass
class Standard:
    version: str
    rules: dict
    sources: dict
    packs: list = field(default_factory=list)
    parameters: dict = field(default_factory=dict)
    minimum_level: int = 1
    minimum_level_by: str = ""


# --------------------------------------------------------------------------- loading
def default_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_standard(root: Path) -> Standard:
    rules_doc = load_yaml(root / "framework" / "rules.yaml")
    sources_doc = load_yaml(root / "framework" / "sources.yaml")
    rules = {}
    for r in rules_doc.get("rules", []):
        r = dict(r)
        r.setdefault("notes", [])
        r.setdefault("origin", "CSEF")
        rules[r["id"]] = r
    sources = {s["id"]: dict(s, origin="CSEF") for s in sources_doc.get("sources", [])}
    return Standard(version=str(rules_doc.get("version", "?")), rules=rules, sources=sources)


def apply_pack(std: Standard, pack_path: Path) -> None:
    doc = load_yaml(pack_path)
    meta = doc.get("pack", {})
    pid = meta.get("id", pack_path.stem)
    for s in doc.get("sources", []) or []:
        if s["id"] in std.sources:
            raise ValueError(f"Pack {pid}: source id {s['id']} already exists")
        std.sources[s["id"]] = dict(s, origin=f"pack:{pid}")
    for r in doc.get("rules", []) or []:
        if r["id"] in std.rules:
            raise ValueError(f"Pack {pid}: rule id {r['id']} already exists")
        r = dict(r)
        r.setdefault("notes", [])
        r["origin"] = f"pack:{pid}"
        std.rules[r["id"]] = r
    for a in doc.get("amend", []) or []:
        rid = a["rule"]
        if rid not in std.rules:
            raise ValueError(f"Pack {pid}: amend targets unknown rule {rid}")
        rule = std.rules[rid]
        for sid in a.get("add_sources", []) or []:
            if sid not in rule["sources"]:
                rule["sources"] = list(rule["sources"]) + [sid]
        if a.get("note"):
            rule["notes"] = list(rule["notes"]) + [f"[{pid.upper()}] {a['note']}"]
        if "level" in a:
            if a["level"] == "MUST":
                rule["level"] = "MUST"
            elif rule["level"] == "MUST":
                raise ValueError(f"Pack {pid}: cannot weaken {rid} to {a['level']}")
        if "tier" in a:
            new_tier = int(a["tier"])
            if new_tier > int(rule["tier"]):
                raise ValueError(f"Pack {pid}: cannot raise tier of {rid} (that would weaken it)")
            rule["tier"] = new_tier
        if a.get("add_patterns"):
            det = dict(rule.get("detection", {"method": "static"}))
            det["patterns"] = list(det.get("patterns", []) or []) + list(a["add_patterns"])
            if det.get("method") == "manual":
                det["method"] = "mixed"
            rule["detection"] = det
    apply_policy(std, doc, pid, meta)
    std.parameters.update({f"{pid}.{k}": v for k, v in (doc.get("parameters") or {}).items()})
    std.packs.append({"id": pid, "title": meta.get("title", pid), "path": str(pack_path),
                      "version": meta.get("version", "?"), "status": meta.get("status", "")})


def _policy_rule(rid, title, requirement, rationale, improvement, sources, patterns, method="static", effort="low"):
    return {
        "id": rid, "title": title, "level": "MUST", "tier": 1, "profiles": ["core"], "age_bands": ["all"],
        "requirement": requirement, "rationale": rationale, "improvement": improvement, "effort": effort,
        "sources": sources, "detection": {"method": method, "patterns": patterns},
        "notes": [], "no_go": True,
    }


def apply_policy(std: Standard, doc: dict, pid: str, meta: dict) -> None:
    """Organisation policy: minimum level, no-gos, forbidden dependencies and phrases, required records.

    Policy rules are 'always on' (tier 1) and 'no-go' (MUST findings block at any confidence).
    They cite an auto-created source of type 'policy' so reports show they are the organisation's choice, not law.
    """
    if "policy" not in doc:
        return
    policy = doc.get("policy") or {}
    pfx = pid.upper()
    title = meta.get("title", pid)
    src_id = f"{pfx}-POLICY"
    if src_id not in std.sources:
        std.sources[src_id] = {
            "id": src_id, "title": f"{title} (organisation policy)", "type": "policy",
            "jurisdiction": meta.get("jurisdiction", "ORG"),
            "status": f"Organisation policy v{meta.get('version', '?')}. Binding for this organisation's products, not law",
            "url": meta.get("url"), "verified": str(meta.get("date", dt.date.today().isoformat())), "origin": f"pack:{pid}",
        }
    ml = policy.get("minimum_level")
    if ml:
        ml = int(ml)
        if ml not in (1, 2, 3):
            raise ValueError(f"Pack {pid}: minimum_level must be 1, 2 or 3")
        if ml > std.minimum_level:
            std.minimum_level, std.minimum_level_by = ml, title
    for rid in policy.get("no_go", []) or []:
        if rid not in std.rules:
            raise ValueError(f"Pack {pid}: no_go targets unknown rule {rid}")
        r = std.rules[rid]
        r["level"], r["tier"], r["no_go"] = "MUST", 1, True
        if src_id not in r["sources"]:
            r["sources"] = list(r["sources"]) + [src_id]
        r["notes"] = list(r["notes"]) + [f"[{pfx}] No-go for {title}: blocks at every compliance level."]
    n = 0
    def nid():
        nonlocal n
        n += 1
        rid = f"{pfx}-POL-{n:02d}"
        if rid in std.rules:
            raise ValueError(f"Pack {pid}: {rid} already exists; do not use the POL area for hand-written rules")
        return rid
    deps = policy.get("forbid_dependencies") or []
    if deps:
        rid = nid()
        std.rules[rid] = _policy_rule(rid, f"Dependencies forbidden by {title}",
            f"These packages are not used in {title} products: {', '.join(deps)}.",
            f"Organisation decision recorded in the {title} policy.",
            "Remove the dependency or obtain a waiver from the policy owner.", [src_id],
            [{"type": "dependency", "confidence": "high", "names": list(deps)}])
    phrases = policy.get("forbid_phrases") or []
    if phrases:
        rid = nid()
        rx = "(" + "|".join(re.escape(str(x)) for x in phrases) + ")"
        std.rules[rid] = _policy_rule(rid, f"Copy forbidden by {title}",
            f"Child-facing copy does not contain: {'; '.join(phrases)}.",
            f"Organisation decision recorded in the {title} policy (pressure, guilt or scarcity language).",
            "Rewrite the copy in neutral, informational terms.", [src_id],
            [{"type": "regex", "confidence": "high", "flags": "i", "pattern": rx}])
    for item in policy.get("forbid_patterns") or []:
        rid = nid()
        std.rules[rid] = _policy_rule(rid, item.get("title", f"Pattern forbidden by {title}"),
            item.get("requirement", f"Code does not match: {item['pattern']}"),
            item.get("rationale", f"Organisation decision recorded in the {title} policy."),
            item.get("improvement", "Remove the construct or obtain a waiver."), [src_id],
            [{"type": "regex", "confidence": "high", "flags": item.get("flags", ""), "pattern": item["pattern"],
              **({"globs": item["globs"]} if item.get("globs") else {})}])
    feats = policy.get("require_decision_for_features") or []
    if feats:
        rid = nid()
        std.rules[rid] = _policy_rule(rid, f"Decision record for sensitive features ({title})",
            f"Each of these features, when declared, has a decision record linked under `decisions:` in csef.yaml: {', '.join(feats)}.",
            "Sensitive features need a documented decision with a named approver before release.",
            "Write a decision record (templates/waiver.md format) and link it in csef.yaml `decisions: {feature: path}`.", [src_id],
            [{"type": "manifest", "check": "decision_records", "confidence": "high", "features": list(feats)}], method="manifest")
    days = policy.get("review_every_days")
    if days:
        rid = nid()
        std.rules[rid] = _policy_rule(rid, f"Manifest reviewed every {days} days ({title})",
            f"`last_review` in csef.yaml is no older than {days} days.",
            "Keeps the declared features, third parties and level in line with the product.",
            "Review csef.yaml with the product owner and update `last_review`.", [src_id],
            [{"type": "manifest", "check": "review_stale", "confidence": "high", "days": int(days)}], method="manifest")
    if policy.get("require_agent_instructions"):
        rid = nid()
        std.rules[rid] = _policy_rule(rid, f"AI coding agents receive the child-safety rules ({title})",
            "The repository gives AI coding agents the CSEF rules (CLAUDE.md, AGENTS.md, .cursorrules or similar mentioning CSEF).",
            "Agents write much of the code; they must know the red lines too.",
            "Copy templates/agent-instructions.md into CLAUDE.md or AGENTS.md.", [src_id],
            [{"type": "repo", "check": "agent_instructions_missing", "confidence": "high"}])


def find_manifest(repo: Path, explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_absolute() else (repo / p)
    for name in MANIFEST_NAMES:
        if (repo / name).exists():
            return repo / name
    return None


# --------------------------------------------------------------------------- selection
def bands_of(rule) -> set:
    b = rule.get("age_bands", ["all"])
    return set(BANDS) if "all" in b else set(b)


def rule_in_scope(rule, profiles: set, bands: set) -> bool:
    rp = set(rule.get("profiles", ["core"]))
    if "core" not in rp and not (rp & profiles):
        return False
    return bool(bands_of(rule) & bands)


def features_declared(rule, manifest: dict | None) -> bool:
    req = rule.get("features")
    if not req or manifest is None:
        return True
    declared = set(manifest.get("features") or [])
    return bool(declared & set(req))


# --------------------------------------------------------------------------- static checks
def iter_files(repo: Path):
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES or fn in MANIFEST_NAMES:
                continue
            p = Path(dirpath) / fn
            if p.suffix.lower() not in SOURCE_EXT and fn not in ("Podfile",):
                continue
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield p


def read_text(p: Path):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


IGNORE_RE = re.compile(r"cse[fs]-ignore:\s*([A-Z0-9, -]+?)(?:\s+(?:--|because|reason:)\s*(.*))?$", re.I)


def inline_ignored(lines, idx, rule_id) -> str | None:
    for j in (idx, idx - 1):
        if 0 <= j < len(lines):
            m = IGNORE_RE.search(lines[j])
            if m and rule_id in [x.strip() for x in m.group(1).split(",")]:
                return (m.group(2) or "no reason given").strip()
    return None


def compile_pattern(p):
    flags = re.I if "i" in str(p.get("flags", "")) else 0
    return re.compile(p["pattern"], flags | re.M)


def regex_findings(rule, pat, files_cache, repo: Path):
    rx = compile_pattern(pat)
    globs = pat.get("globs")
    out = []
    for rel, lines, text in files_cache:
        if globs and not any(fnmatch.fnmatch(Path(rel).name, g) or fnmatch.fnmatch(rel, g) for g in globs):
            continue
        if not rx.search(text):
            continue
        for i, line in enumerate(lines):
            if rx.search(line):
                out.append((rel, i + 1, line.strip()[:160], inline_ignored(lines, i, rule["id"])))
                if len(out) > 25:
                    return out
    return out


def collect_dependencies(repo: Path):
    deps = {}  # name -> file
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = str(p.relative_to(repo))
            try:
                if fn == "package.json":
                    data = json.loads(p.read_text(encoding="utf-8"))
                    for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                        for name in (data.get(k) or {}):
                            deps.setdefault(name, rel)
                elif fn.startswith("requirements") and fn.endswith(".txt"):
                    for ln in p.read_text(encoding="utf-8").splitlines():
                        m = re.match(r"\s*([A-Za-z0-9_.\-]+)", ln)
                        if m and not ln.strip().startswith("#"):
                            deps.setdefault(m.group(1).lower(), rel)
                elif fn == "pyproject.toml":
                    for m in re.finditer(r'^\s*"?([A-Za-z0-9_.\-]+)\s*(?:[<>=~!\[]|"|\s*=)', p.read_text(encoding="utf-8"), re.M):
                        deps.setdefault(m.group(1).lower(), rel)
                elif fn == "Podfile":
                    for m in re.finditer(r"pod\s+['\"]([^'\"/]+)", p.read_text(encoding="utf-8")):
                        deps.setdefault(m.group(1), rel)
                elif fn.endswith((".gradle", ".gradle.kts")):
                    for m in re.finditer(r"['\"]([a-zA-Z0-9_.\-]+:[a-zA-Z0-9_.\-]+)(?::[^'\"]*)?['\"]", p.read_text(encoding="utf-8")):
                        deps.setdefault(m.group(1), rel)
                elif fn == "manifest.json" and p.parent.name == "Packages":  # Unity Package Manager
                    data = json.loads(p.read_text(encoding="utf-8"))
                    for name in (data.get("dependencies") or {}):
                        deps.setdefault(name, rel)
                elif fn.endswith("Dependencies.xml"):  # Unity External Dependency Manager (Android and iOS SDKs)
                    t = p.read_text(encoding="utf-8")
                    for m in re.finditer(r'androidPackage\s+spec="([^":]+:[^":]+)', t):
                        deps.setdefault(m.group(1), rel)
                    for m in re.finditer(r'iosPod\s+name="([^"]+)"', t):
                        deps.setdefault(m.group(1), rel)
                elif fn == "pom.xml":
                    t = p.read_text(encoding="utf-8")
                    for m in re.finditer(r"<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>", t):
                        deps.setdefault(f"{m.group(1).strip()}:{m.group(2).strip()}", rel)
                elif fn.endswith((".csproj", ".fsproj")) or fn in ("packages.config", "Directory.Packages.props"):
                    for m in re.finditer(r'(?:PackageReference|PackageVersion|package)\s+(?:Include|id)="([^"]+)"', p.read_text(encoding="utf-8"), re.I):
                        deps.setdefault(m.group(1), rel)
                elif fn == "go.mod":
                    for m in re.finditer(r"^\s*(?:require\s+)?([\w.\-]+\.[\w.\-/]+)\s+v[\d.]+", p.read_text(encoding="utf-8"), re.M):
                        deps.setdefault(m.group(1), rel)
                elif fn == "Cargo.toml":
                    t = p.read_text(encoding="utf-8")
                    sec = re.search(r"^\[dependencies\]([\s\S]*?)(^\[|\Z)", t, re.M)
                    for m in re.finditer(r"^\s*([A-Za-z0-9_\-]+)\s*=", sec.group(1) if sec else "", re.M):
                        deps.setdefault(m.group(1), rel)
                elif fn == "composer.json":
                    data = json.loads(p.read_text(encoding="utf-8"))
                    for k in ("require", "require-dev"):
                        for name in (data.get(k) or {}):
                            deps.setdefault(name, rel)
                elif fn == "Gemfile":
                    for m in re.finditer(r"^\s*gem\s+['\"]([^'\"]+)", p.read_text(encoding="utf-8"), re.M):
                        deps.setdefault(m.group(1), rel)
                elif fn == "Package.swift":
                    for m in re.finditer(r'\.package\s*\(\s*(?:name:\s*"[^"]*",\s*)?url:\s*"[^"]*/([^/"]+?)(?:\.git)?"', p.read_text(encoding="utf-8")):
                        deps.setdefault(m.group(1), rel)
                elif fn == "pubspec.yaml":
                    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                    for k in ("dependencies", "dev_dependencies"):
                        for name in (data.get(k) or {}):
                            deps.setdefault(name, rel)
            except (OSError, ValueError, yaml.YAMLError):
                continue
    return deps


def dependency_findings(pat, deps):
    names = pat.get("names", [])
    lower = {k.lower(): (k, v) for k, v in deps.items()}
    hits = []
    for n in names:
        if n.lower() in lower:
            k, f = lower[n.lower()]
            hits.append((f, k))
    return hits


# --------------------------------------------------------------------------- manifest checks
def path_exists(repo: Path, value) -> bool:
    if not value:
        return False
    v = str(value)
    if v.startswith(("http://", "https://")):
        return True
    return (repo / v).exists()


def manifest_check(name: str, manifest: dict | None, repo: Path, bands: set, pat: dict | None = None):
    """Return a list of messages (empty list = check passes)."""
    if name == "manifest_missing":
        return ["No CSEF manifest (csef.yaml) found. All profiles and age bands were assumed."] if manifest is None else []
    if manifest is None:
        return []
    m = manifest
    features = set(m.get("features") or [])
    ai = m.get("ai") or {}
    if name == "kids_act_scope_missing":
        v = (m.get("legal_scope") or {}).get("kids_act")
        return [] if v and v != "unknown" else ["`legal_scope.kids_act` is missing or 'unknown'."]
    if name == "dpia_missing":
        processes_more = bool(features - {"accounts"}) or bool(m.get("third_parties"))
        if not processes_more:
            return []
        return [] if path_exists(repo, m.get("dpia")) else ["No DPIA referenced, or the referenced file does not exist."]
    if name == "third_party_without_dpa":
        return [f"Third party '{t.get('name', '?')}' has no signed processor agreement (dpa_signed is not true)."
                for t in (m.get("third_parties") or []) if t.get("dpa_signed") is not True]
    if name == "gdpr_role_missing":
        return [] if m.get("gdpr_role") in ("controller", "processor", "joint") else ["`gdpr_role` is missing (controller, processor or joint)."]
    if name == "transfer_outside_eea":
        msgs = []
        for t in m.get("third_parties") or []:
            region = str(t.get("region") or "")
            if not region:
                msgs.append(f"Third party '{t.get('name', '?')}' has no hosting region declared.")
            elif not EEA_REGION.search(region) and not t.get("transfer_mechanism"):
                msgs.append(f"Third party '{t.get('name', '?')}' is hosted in '{region}' without a declared transfer mechanism.")
        return msgs
    if name == "retention_missing":
        return [] if m.get("retention") else ["No retention periods declared (`retention`)."]
    if name == "monetisation_for_minors":
        mon = m.get("monetisation", "none")
        minors = bool(bands & set(BANDS))
        if minors and mon in ("in_app_purchases", "ads", "virtual_currency"):
            return [f"Monetisation '{mon}' declared for a product used by minors."]
        return []
    if name == "ai_without_inventory":
        if features & {"ai_generative", "ai_assessment", "ai_adaptive"}:
            return [] if path_exists(repo, ai.get("inventory")) else ["AI features declared but no AI inventory file found (`ai.inventory`)."]
        return []
    if name == "high_risk_without_risk_file":
        risky = ai.get("act_class") == "high_risk_annex_iii" or bool(features & {"ai_assessment", "ai_adaptive"})
        if risky and not path_exists(repo, ai.get("risk_file")):
            return ["AI that evaluates, adapts or places learners, but no AI risk file found (`ai.risk_file`)."]
        return []
    if name == "decision_records":
        decisions = m.get("decisions") or {}
        return [f"Feature '{f}' is declared but has no decision record linked under `decisions:`."
                for f in (pat or {}).get("features", []) if f in features and not path_exists(repo, decisions.get(f))]
    if name == "review_stale":
        days = int((pat or {}).get("days", 180))
        lr = m.get("last_review")
        if not lr:
            return ["`last_review` is missing."]
        try:
            age = (dt.date.today() - dt.date.fromisoformat(str(lr))).days
        except ValueError:
            return [f"`last_review` is not a date: {lr}"]
        return [f"`last_review` is {age} days old (limit {days})."] if age > days else []
    if name == "security_policy_missing":
        candidates = [m.get("security_policy"), "SECURITY.md", ".github/SECURITY.md", ".well-known/security.txt", "public/.well-known/security.txt"]
        return [] if any(path_exists(repo, c) for c in candidates) else ["No SECURITY.md or security.txt found."]
    raise ValueError(f"Unknown manifest check: {name}")


# --------------------------------------------------------------------------- repository checks
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comms  # noqa: E402

REPO_CHECKS = ["reduced_motion_missing", "reward_layers", "agent_instructions_missing"] + comms.CHECKS
AGENT_FILES = ["CLAUDE.md", "AGENTS.md", ".cursorrules", ".github/copilot-instructions.md", ".windsurfrules", ".lovable/knowledge.md"]
ANIMATION_RX = re.compile(r"(@keyframes|framer-motion|from ['\"]motion/react|gsap|lottie|Animated\.(timing|spring|loop)|anime\.js|animation\s*:\s*[a-z])", re.I)
REDUCED_RX = re.compile(r"(prefers-reduced-motion|useReducedMotion|isReduceMotionEnabled|reduceMotion|reducedMotion|AccessibilityInfo)", re.I)
REWARD_LAYERS = {
    "points / XP / score": r"\b(xp|exp_?points|experience_?points|addPoints|awardPoints|score\s*\+=|pointsEarned)\b",
    "coins / gems / currency": r"\b(coins?|gems?|diamonds?|moedas|currency)\b",
    "badges / achievements / trophies": r"\b(badges?|achievements?|trophies|trophy|medals?|conquistas)\b",
    "streaks": r"\b(streaks?|sequ[eê]ncia)\b",
    "levels / level-up": r"\b(levelUp|level_up|onLevelUp|nextLevel|subirN[ií]vel)\b",
    "leaderboards / rankings": r"\b(leaderboards?|rankings?|classifica[cç][aã]o)\b",
    "unlockables": r"\b(unlock(ed|ables?)?|desbloque\w*)\b",
    "celebrations": r"\b(confetti|fireworks|celebrat\w*|celebra[cç][aã]o)\b",
}


def repo_check(name, files_cache, repo=None, inv=None, manifest=None):
    """Return list of (path, line, message) for repository-wide checks."""
    if name in comms.CHECKS:
        return comms.check(name, inv, manifest) if inv else []
    if name == "agent_instructions_missing":
        for f in AGENT_FILES:
            p = repo / f if repo else None
            if p and p.exists() and re.search(r"CSEF|CSES|child-safety rules", p.read_text(encoding="utf-8", errors="ignore"), re.I):
                return []
        return [(None, None, "No AI agent instructions mentioning CSEF found (CLAUDE.md, AGENTS.md, .cursorrules, ...).")]
    if name == "reduced_motion_missing":
        first = None
        for rel, lines, text in files_cache:
            if REDUCED_RX.search(text):
                return []
            if first is None and ANIMATION_RX.search(text):
                for i, ln in enumerate(lines):
                    if ANIMATION_RX.search(ln):
                        first = (rel, i + 1)
                        break
        if first:
            return [(first[0], first[1], "Animations found but no reduced-motion handling anywhere in the codebase.")]
        return []
    if name == "reward_layers":
        found = {}
        for label, rx in REWARD_LAYERS.items():
            c = re.compile(rx, re.I)
            for rel, lines, text in files_cache:
                if not rel.endswith((".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".dart", ".cs", ".gd", ".lua", ".py", ".swift", ".kt", ".json")):
                    continue
                if c.search(text):
                    found[label] = rel
                    break
        if len(found) >= 4:
            return [(None, None, f"Reward pile-up signal: {len(found)} reward layers found in code ({', '.join(found)}). "
                                 "Check which are given for learning and which for showing up.")]
        return []
    raise ValueError(f"Unknown repository check: {name}")


# --------------------------------------------------------------------------- severity
def severity_for(rule, confidence: str, level: int) -> str:
    if int(rule["tier"]) > level:
        return "NEXT"
    if rule["level"] == "MUST":
        return "BLOCK" if (confidence == "high" or rule.get("no_go")) else "REVIEW"
    return "WARN"


def active_waiver(waivers, rule_id, path, today):
    for w in waivers:
        if w.get("rule") != rule_id or not w.get("approved_by"):
            continue
        if w.get("path") and path and not fnmatch.fnmatch(path, w["path"]):
            continue
        exp = w.get("expires")
        if exp and str(exp) < today:
            continue
        return w
    return None


# --------------------------------------------------------------------------- scan
def _with_raw(findings, std):
    for f in findings:
        f.raw = "WAIVED" if f.severity == "WAIVED" else severity_for(std.rules[f.rule_id], f.confidence or "medium", 3)
    return findings


def scan(repo: Path, std: Standard, manifest: dict | None, level: int):
    profiles = set(manifest.get("profiles") or []) if manifest else {"A", "B", "C"}
    bands = set(manifest.get("age_bands") or []) if manifest else set(BANDS)
    waivers = (manifest or {}).get("waivers") or []
    today = dt.date.today().isoformat()

    in_scope = {rid: r for rid, r in std.rules.items() if rule_in_scope(r, profiles, bands)}

    files_cache = []
    for p in iter_files(repo):
        text = read_text(p)
        if text is None:
            continue
        files_cache.append((str(p.relative_to(repo)), text.splitlines(), text))
    deps = collect_dependencies(repo)
    inv = comms.inventory(files_cache, deps)

    findings: list[Finding] = []
    checked_static = set()

    for rid, rule in in_scope.items():
        det = rule.get("detection") or {}
        declared = features_declared(rule, manifest)
        for pat in det.get("patterns", []) or []:
            conf = pat.get("confidence", "medium")
            sev = severity_for(rule, conf, level)
            undeclared = None if declared else "Feature not declared in the manifest but found in code."
            if pat["type"] == "regex":
                checked_static.add(rid)
                for rel, ln, snippet, ignored in regex_findings(rule, pat, files_cache, repo):
                    w = active_waiver(waivers, rid, rel, today)
                    if ignored is not None or w:
                        findings.append(Finding(rid, "WAIVED", rule["title"], rel, ln, snippet,
                                                note=f"Waived: {ignored if ignored is not None else w.get('reason', '')}"
                                                     + (f" (approved by {w['approved_by']})" if w else " (inline)")))
                        continue
                    findings.append(Finding(rid, sev, rule["title"], rel, ln, snippet, note=undeclared, confidence=conf))
            elif pat["type"] == "dependency":
                checked_static.add(rid)
                for f, name in dependency_findings(pat, deps):
                    w = active_waiver(waivers, rid, f, today)
                    if w:
                        findings.append(Finding(rid, "WAIVED", rule["title"], f, None, f"dependency: {name}",
                                                note=f"Waived: {w.get('reason', '')} (approved by {w['approved_by']})"))
                        continue
                    findings.append(Finding(rid, sev, rule["title"], f, None, f"dependency: {name}", note=undeclared, confidence=conf))
            elif pat["type"] == "repo":
                checked_static.add(rid)
                for rel, ln, msg in repo_check(pat["check"], files_cache, repo, inv, manifest):
                    w = active_waiver(waivers, rid, rel, today)
                    if w:
                        findings.append(Finding(rid, "WAIVED", rule["title"], rel, ln, msg,
                                                note=f"Waived: {w.get('reason', '')} (approved by {w['approved_by']})"))
                        continue
                    findings.append(Finding(rid, sev, rule["title"], rel, ln, msg, confidence=conf))
            elif pat["type"] == "manifest":
                if not declared and rule.get("features"):
                    continue
                checked_static.add(rid)
                for msg in manifest_check(pat["check"], manifest, repo, bands, pat):
                    w = active_waiver(waivers, rid, None, today)
                    if w:
                        findings.append(Finding(rid, "WAIVED", rule["title"], "csef.yaml", None, msg,
                                                note=f"Waived: {w.get('reason', '')} (approved by {w['approved_by']})"))
                        continue
                    findings.append(Finding(rid, sev, rule["title"], "csef.yaml", None, msg, confidence=conf))

    # human checks: manual or mixed rules in scope whose feature applies
    human = []
    for rid, rule in in_scope.items():
        method = (rule.get("detection") or {}).get("method", "manual")
        if method in ("manual", "mixed") and features_declared(rule, manifest):
            hit = any(f.rule_id == rid and f.severity not in ("WAIVED",) for f in findings)
            human.append({"rule_id": rid, "next_level": int(rule["tier"]) > level, "has_static_hit": hit})

    return {
        "profiles": sorted(profiles), "bands": sorted(bands), "level": level,
        "rules_in_scope": sorted(in_scope), "findings": _with_raw(findings, std), "human_checks": human,
        "communications": inv,
    }


# --------------------------------------------------------------------------- reporting helpers
def cited_sources(std: Standard, rule_ids):
    seen = []
    for rid in rule_ids:
        for sid in std.rules[rid].get("sources", []):
            if sid not in seen:
                seen.append(sid)
    return seen


def src_label(std, sid):
    s = std.sources.get(sid)
    return f"[{sid}]" if s else f"[{sid}?]"


def esc(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def group_findings(findings):
    groups = {}
    for f in findings:
        groups.setdefault((f.rule_id, f.severity), []).append(f)
    return groups


def kids_act_line(manifest):
    v = ((manifest or {}).get("legal_scope") or {}).get("kids_act", "not declared")
    return v


def render_report(repo, std, manifest, result, manifest_path) -> str:
    level = result["level"]
    findings = result["findings"]
    counts = {s: 0 for s in SEVERITY_ORDER}
    for (rid, sev), items in group_findings(findings).items():
        counts[sev] += 1
    human_now = [h for h in result["human_checks"] if not h["next_level"]]
    product = (manifest or {}).get("product", repo.name)
    lines = []
    a = lines.append
    a(f"# CSEF pre-compliance report: {product}")
    a("")
    a(f"Generated {dt.date.today().isoformat()} by {TOOL_NAME} {TOOL_VERSION}, Child-Safe EdTech Framework v{std.version}.")
    a("")
    a("> **This is a pre-compliance report, not a legal opinion or certification.** Static analysis finds")
    a("> technical signals in code and configuration. It cannot see contracts, legal bases, real user")
    a("> experience or how the product is operated. Items under *Human checks* need a person to confirm.")
    a("")
    a("## Scope")
    a("")
    a("| | |")
    a("|---|---|")
    a(f"| Compliance level | **Level {level}: {LEVEL_NAMES[level]}** |")
    prof_names = {"A": "A Educational game", "B": "B Game-based application", "C": "C Gamified application"}
    a(f"| Profiles | Core + {', '.join(prof_names.get(p, p) for p in result['profiles']) or 'none'} |")
    a(f"| Age bands | {', '.join(f'{b} ({BAND_AGES[b]})' for b in result['bands'])} |")
    a(f"| Manifest | {manifest_path if manifest_path else 'not found (all profiles and bands assumed)'} |")
    a(f"| EU KIDS Act scope (declared) | {kids_act_line(manifest)} |")
    if std.minimum_level > 1:
        a(f"| Minimum level | Level {std.minimum_level}, set by {std.minimum_level_by} |")
    nogos = sorted(rid for rid in result["rules_in_scope"] if std.rules[rid].get("no_go"))
    if nogos:
        a(f"| No-go rules | {len(nogos)} (block at any confidence) |")
    a(f"| Packs loaded | {', '.join(p['title'] + ' v' + p['version'] for p in std.packs) or 'none'} |")
    a(f"| Rules in scope | {len(result['rules_in_scope'])} |")
    a("")
    if std.parameters:
        a("**Pack parameters:** " + "; ".join(f"{k} = {v}" for k, v in std.parameters.items()))
        a("")
    a("## Summary")
    a("")
    verdict = ("Blocking issues found. Fix or formally waive them before release."
               if counts["BLOCK"] else
               "No blocking issues found by automated checks at this level. Complete the review items and human checks before describing the results.")
    a(f"**{verdict}**")
    a("")
    a("| Severity | Rules affected | Meaning |")
    a("|---|---|---|")
    a(f"| BLOCK | {counts['BLOCK']} | Clear breach of a MUST rule at the chosen level |")
    a(f"| REVIEW | {counts['REVIEW']} | Likely breach of a MUST rule; a person must confirm |")
    a(f"| WARN | {counts['WARN']} | SHOULD rule not met |")
    a(f"| HUMAN | {len(human_now)} | Cannot be checked in code; needs a person |")
    a(f"| NEXT | {counts['NEXT']} | Signals against rules of a higher level (see improvements) |")
    a(f"| WAIVED | {counts['WAIVED']} | Accepted with a recorded reason |")
    a("")

    a("## Findings")
    a("")
    groups = group_findings(findings)
    for sev in ["BLOCK", "REVIEW", "WARN"]:
        items = [(rid, fs) for (rid, s), fs in groups.items() if s == sev]
        if not items:
            continue
        a(f"### {sev}")
        a("")
        for rid, fs in sorted(items):
            rule = std.rules[rid]
            a(f"#### {rid}: {rule['title']}")
            a("")
            a(f"*{rule['level']}, tier {rule['tier']} ({LEVEL_NAMES[int(rule['tier'])]}).* {rule['requirement'].strip()}")
            a("")
            for f in fs[:10]:
                loc = f"`{f.path}{':' + str(f.line) if f.line else ''}`" if f.path else ""
                ev = f" `{esc(f.evidence)}`" if f.evidence and f.path != "csef.yaml" else (f" {f.evidence}" if f.evidence else "")
                extra = f" *{f.note}*" if f.note else ""
                a(f"- {loc}{ev}{extra}")
            if len(fs) > 10:
                a(f"- ... and {len(fs) - 10} more locations (see findings.json)")
            a("")
            a(f"**Why:** {rule['rationale'].strip()}")
            for n in rule.get("notes", []):
                a(f"  \n**National note:** {n}")
            a("")
            a(f"**Sources:** {', '.join(src_label(std, s) for s in rule.get('sources', []))}")
            a("")
    if not any(s in ("BLOCK", "REVIEW", "WARN") for (_, s) in groups):
        a("No automated findings at this level.")
        a("")

    a("## Communications inventory")
    a("")
    a("Channels found in code and the safeguards around them (rules CORE-CHT-*, CORE-SAF-05, AGE-B2-01).")
    a("")
    lines.extend(comms.markdown(result["communications"]))
    a("## Human checks")
    a("")
    a("These rules apply to the product but need a person to verify. Tick them in the self-assessment checklist.")
    a("")
    a("| Rule | Level | What to confirm | Sources |")
    a("|---|---|---|---|")
    for h in sorted(human_now, key=lambda h: h["rule_id"]):
        r = std.rules[h["rule_id"]]
        a(f"| {h['rule_id']} | {r['level']} / tier {r['tier']} | {esc(r['requirement'].strip())} | {', '.join(src_label(std, s) for s in r.get('sources', []))} |")
    a("")

    waived = [f for f in findings if f.severity == "WAIVED"]
    if waived:
        a("## Waivers applied")
        a("")
        for f in waived:
            a(f"- {f.rule_id} at `{f.path}{':' + str(f.line) if f.line else ''}`: {f.note}")
        a("")

    used_rules = {f.rule_id for f in findings if f.severity != "NEXT"} | {h["rule_id"] for h in human_now}
    a("## Sources")
    a("")
    a("Status as recorded in the source registry. Check the `verified` date before relying on it.")
    a("")
    for sid in cited_sources(std, sorted(used_rules)):
        s = std.sources.get(sid)
        if not s:
            a(f"- **[{sid}]** (missing from registry)")
            continue
        url = f" <{s['url']}>" if s.get("url") else ""
        a(f"- **[{sid}]** {s['title']}. *{s.get('type', '')}, {s.get('jurisdiction', '')}.* {s.get('status', '')}. Verified {s.get('verified', '?')}.{url}")
    a("")
    return "\n".join(lines)


def priority_key(item):
    return (SEVERITY_ORDER.index(item["severity"]), EFFORT_ORDER.get(item["effort"], 1), item["rule_id"])


def build_improvements(std, result):
    level = result["level"]
    items = {}
    for f in result["findings"]:
        if f.severity == "WAIVED":
            continue
        key = f.rule_id
        rule = std.rules[key]
        it = items.setdefault(key, {
            "rule_id": key, "title": rule["title"], "severity": f.severity, "tier": int(rule["tier"]),
            "level": rule["level"], "effort": rule.get("effort", "medium"),
            "action": rule.get("improvement", "").strip(), "why": rule["rationale"].strip(),
            "locations": [], "sources": rule.get("sources", []), "notes": rule.get("notes", []),
        })
        if SEVERITY_ORDER.index(f.severity) < SEVERITY_ORDER.index(it["severity"]):
            it["severity"] = f.severity
        if f.path:
            it["locations"].append(f"{f.path}{':' + str(f.line) if f.line else ''}")
    for h in result["human_checks"]:
        rid = h["rule_id"]
        if rid in items:
            continue
        rule = std.rules[rid]
        items[rid] = {
            "rule_id": rid, "title": rule["title"], "severity": "NEXT" if h["next_level"] else "HUMAN",
            "tier": int(rule["tier"]), "level": rule["level"], "effort": rule.get("effort", "medium"),
            "action": rule.get("improvement", "").strip(), "why": rule["rationale"].strip(),
            "locations": [], "sources": rule.get("sources", []), "notes": rule.get("notes", []),
        }
    return sorted(items.values(), key=priority_key)


def render_improvements(std, manifest, result, improvements) -> str:
    level = result["level"]
    product = (manifest or {}).get("product", "product")
    lines = []
    a = lines.append
    a(f"# Improvement plan: {product}")
    a("")
    a(f"Compliance level chosen: **Level {level}: {LEVEL_NAMES[level]}**. Generated {dt.date.today().isoformat()} by {TOOL_NAME} {TOOL_VERSION}.")
    a("")
    a("Ordered by severity, then by effort (quick wins first). Items marked *verify* come from human checks:")
    a("they may already be done; confirm and tick them in the self-assessment.")
    a("")
    sections = [
        ("BLOCK", "Fix before release"),
        ("REVIEW", "Confirm and fix"),
        ("WARN", "Recommended at this level"),
        ("HUMAN", "Verify (cannot be checked in code)"),
        ("NEXT", "To reach the next level"),
    ]
    n = 0
    for sev, title in sections:
        group = [i for i in improvements if i["severity"] == sev]
        if not group:
            continue
        a(f"## {title}")
        a("")
        if sev == "NEXT":
            for t in range(level + 1, 4):
                sub = [i for i in group if i["tier"] == t]
                if not sub:
                    continue
                a(f"### Level {t}: {LEVEL_NAMES[t]}")
                a("")
                for i in sub:
                    n += 1
                    lines.extend(render_item(std, n, i, verify=False))
            continue
        for i in group:
            n += 1
            lines.extend(render_item(std, n, i, verify=(sev == "HUMAN")))
    if n == 0:
        a("Nothing to improve at this level. Consider raising the compliance level.")
    a("")
    a("## Sources")
    a("")
    for sid in cited_sources(std, [i["rule_id"] for i in improvements]):
        s = std.sources.get(sid)
        if s:
            a(f"- **[{sid}]** {s['title']}. {s.get('status', '')}. {s.get('url', '')}")
    a("")
    return "\n".join(lines)


def render_item(std, n, i, verify):
    out = []
    tag = " *(verify)*" if verify else ""
    out.append(f"**{n}. {i['action']}**{tag}")
    out.append("")
    out.append(f"- Rule: {i['rule_id']} {i['title']} ({i['level']}, tier {i['tier']}), effort: {i['effort']}")
    out.append(f"- Why: {i['why']}")
    if i["locations"]:
        locs = ", ".join(f"`{x}`" for x in i["locations"][:6])
        more = f" and {len(i['locations']) - 6} more" if len(i["locations"]) > 6 else ""
        out.append(f"- Where: {locs}{more}")
    for note in i["notes"]:
        out.append(f"- National note: {note}")
    out.append(f"- Sources: {', '.join(src_label(std, s) for s in i['sources'])}")
    out.append("")
    return out


RULE_EXPORT_FIELDS = ["id", "title", "level", "tier", "profiles", "age_bands", "features", "requirement",
                      "rationale", "improvement", "effort", "sources", "notes", "origin", "no_go"]
MANIFEST_EXPORT_FIELDS = ["product", "description", "context", "gdpr_role", "legal_scope", "features", "jurisdictions",
                          "monetisation", "distribution", "compliance_level", "last_review"]


def to_json(std, manifest, result, improvements):
    m = manifest or {}
    return {
        "format": 2,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION, "standard_version": std.version},
        "minimum_level": std.minimum_level, "minimum_level_by": std.minimum_level_by,
        "manifest": {k: m.get(k) for k in MANIFEST_EXPORT_FIELDS if k in m} if manifest else None,
        "rules": {rid: {k: std.rules[rid].get(k) for k in RULE_EXPORT_FIELDS if k in std.rules[rid]}
                  for rid in result["rules_in_scope"]},
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "product": (manifest or {}).get("product"),
        "level": result["level"], "profiles": result["profiles"], "age_bands": result["bands"],
        "packs": std.packs, "parameters": std.parameters,
        "findings": [f.__dict__ for f in result["findings"]],
        "human_checks": result["human_checks"],
        "improvements": improvements,
        "communications": result.get("communications"),
        "sources": {sid: std.sources[sid] for sid in cited_sources(std, result["rules_in_scope"]) if sid in std.sources},
    }


def to_sarif(std, result):
    sev_map = {"BLOCK": "error", "REVIEW": "warning", "WARN": "note", "NEXT": "note"}
    used = sorted({f.rule_id for f in result["findings"] if f.severity in sev_map})
    rules = []
    for rid in used:
        r = std.rules[rid]
        src = [std.sources[s].get("url") for s in r.get("sources", []) if s in std.sources and std.sources[s].get("url")]
        rules.append({
            "id": rid, "name": rid,
            "shortDescription": {"text": r["title"]},
            "fullDescription": {"text": r["requirement"].strip()},
            "help": {"text": f"{r.get('improvement', '').strip()} Sources: {', '.join(r.get('sources', []))}"},
            "helpUri": src[0] if src else None,
            "properties": {"tier": r["tier"], "level": r["level"]},
        })
    results = []
    for f in result["findings"]:
        if f.severity not in sev_map:
            continue
        loc = {"physicalLocation": {"artifactLocation": {"uri": f.path or "csef.yaml"}}}
        if f.line:
            loc["physicalLocation"]["region"] = {"startLine": f.line}
        results.append({
            "ruleId": f.rule_id, "level": sev_map[f.severity],
            "message": {"text": f"[{f.severity}] {f.message}" + (f": {f.evidence}" if f.evidence else "")},
            "locations": [loc],
        })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": TOOL_NAME, "version": TOOL_VERSION,
                                      "informationUri": "https://github.com/eduardon83/child-safe-edtech-framework", "rules": rules}},
                  "results": results}],
    }


# --------------------------------------------------------------------------- main
def resolve_packs(repo: Path, root: Path, manifest: dict | None, extra: list[str]) -> list[Path]:
    paths = []
    for j in (manifest or {}).get("jurisdictions") or []:
        code = str(j).lower()
        if code == "eu":
            continue
        p = root / "packs" / f"{code}.yaml"
        if p.exists():
            paths.append(p)
        else:
            print(f"csef: no pack for jurisdiction {j} (looked for {p}). Consider contributing one.", file=sys.stderr)
    for rel in ((manifest or {}).get("packs") or []) + list(extra or []):
        p = Path(rel)
        if not p.is_absolute():
            p = (repo / p) if (repo / p).exists() else (root / p)
        if not p.exists():
            raise FileNotFoundError(f"Pack not found: {rel}")
        if p not in paths:
            paths.append(p)
    return paths


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CSEF pre-compliance scanner")
    ap.add_argument("--repo", default=".", help="repository to scan")
    ap.add_argument("--manifest", help="path to csef.yaml (default: auto-detect)")
    ap.add_argument("--framework-root", "--standard-root", dest="standard_root", default=None, help="folder containing framework/ and packs/")
    ap.add_argument("--level", type=int, choices=[1, 2, 3], help="override compliance level")
    ap.add_argument("--pack", action="append", default=[], help="extra pack file (repeatable)")
    ap.add_argument("--out-dir", default=None, help="write report.md, improvements.md, findings.json, findings.sarif here")
    ap.add_argument("--format", choices=["text", "json", "none"], default="text", help="stdout format")
    ap.add_argument("--fail-on", choices=["block", "review", "warn", "never"], default="block")
    ap.add_argument("--export", default="", help="also export: comma-separated html,pdf,docx (needs --out-dir)")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    root = Path(args.standard_root).resolve() if args.standard_root else Path(os.environ.get("CSEF_FRAMEWORK_ROOT") or os.environ.get("CSES_STANDARD_ROOT") or default_root())
    std = load_standard(root)

    mpath = find_manifest(repo, args.manifest)
    manifest = load_yaml(mpath) if mpath and mpath.exists() else None
    if args.manifest and manifest is None:
        print(f"csef: manifest {args.manifest} not found", file=sys.stderr)
        return 2
    for p in resolve_packs(repo, root, manifest, args.pack):
        apply_pack(std, p)

    level = args.level or int((manifest or {}).get("compliance_level", 1))
    if level < std.minimum_level:
        print(f"csef: level raised from {level} to {std.minimum_level}, the minimum set by {std.minimum_level_by}", file=sys.stderr)
        level = std.minimum_level
    result = scan(repo, std, manifest, level)
    improvements = build_improvements(std, result)

    if args.out_dir:
        out = Path(args.out_dir).resolve()  # relative to the current directory, like any CLI
        out.mkdir(parents=True, exist_ok=True)
        rel_manifest = str(mpath.relative_to(repo)) if mpath and manifest is not None and mpath.is_relative_to(repo) else (str(mpath) if manifest else None)
        (out / "report.md").write_text(render_report(repo, std, manifest, result, rel_manifest), encoding="utf-8")
        (out / "improvements.md").write_text(render_improvements(std, manifest, result, improvements), encoding="utf-8")
        (out / "findings.json").write_text(json.dumps(to_json(std, manifest, result, improvements), indent=2, default=str), encoding="utf-8")
        (out / "findings.sarif").write_text(json.dumps(to_sarif(std, result), indent=2), encoding="utf-8")
        if args.export:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import export as csef_export
            try:
                written = csef_export.export(out / "findings.json", [f.strip() for f in args.export.split(",") if f.strip()], out)
                if args.format == "text":
                    print("exported: " + ", ".join(str(Path(v).name) for k, v in written.items() if k != "pdf_engine"))
            except RuntimeError as ex:
                print(f"csef export: {ex}", file=sys.stderr)

    counts = {s: len({f.rule_id for f in result["findings"] if f.severity == s}) for s in SEVERITY_ORDER}
    if args.format == "json":
        print(json.dumps(to_json(std, manifest, result, improvements), indent=2, default=str))
    elif args.format == "text":
        print(f"CSEF {std.version} | level {level} ({LEVEL_NAMES[level]}) | profiles core+{','.join(result['profiles'])} | bands {','.join(result['bands'])}")
        print("rules affected: " + ", ".join(f"{s} {counts[s]}" for s in SEVERITY_ORDER if s != "HUMAN")
              + f", HUMAN {len([h for h in result['human_checks'] if not h['next_level']])}")
        for f in sorted(result["findings"], key=lambda f: (SEVERITY_ORDER.index(f.severity), f.rule_id)):
            if f.severity in ("BLOCK", "REVIEW", "WARN"):
                loc = f"{f.path}:{f.line}" if f.line else (f.path or "")
                print(f"  {f.severity:6} {f.rule_id:12} {loc}  {f.evidence or f.message}")
        if args.out_dir:
            print(f"report written to {args.out_dir}/")

    threshold = {"block": ["BLOCK"], "review": ["BLOCK", "REVIEW"], "warn": ["BLOCK", "REVIEW", "WARN"], "never": []}[args.fail_on]
    return 1 if any(counts[s] for s in threshold) else 0


if __name__ == "__main__":
    sys.exit(main())
