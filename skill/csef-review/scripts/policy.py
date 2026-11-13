#!/usr/bin/env python3
"""CSEF policy questionnaire: turn an organisation's boundaries into guardrails.

Asks what the organisation will and will not do, matches each answer with the law and with
recommendations, and writes a policy kit:

  <id>.yaml                    company pack (the guardrails the scanner applies)
  answers.json                 the answers; run again with them to change anything
  boundaries-report.*          what you chose, what the law already requires, what is recommended
  staff-policy.*               the policy in plain language, for everyone in the organisation
  agent-instructions.md        the rules for AI coding agents (CLAUDE.md, AGENTS.md, Cursor)
  csef-check.yml               GitHub Actions workflow with your pack
  csef-review.zip              the Claude review skill
  README.md                    how to use the kit in your projects

Everything runs locally. Nothing is sent anywhere.

Usage:
  python3 tooling/policy.py                         questions in the terminal
  python3 tooling/policy.py --web                   questions in a local web page (http://127.0.0.1:8765)
  python3 tooling/policy.py --answers csef-policy/answers.json --batch
                                                    regenerate from saved answers, no questions
Options: --out-dir DIR (default csef-policy), --formats md,html,pdf,docx, --port N, --no-skill
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand  # noqa: E402
import scan  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("CSEF policy needs PyYAML: pip install pyyaml")

TOOL = "csef-policy"
PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"
REPO_URL = "https://github.com/eduardon83/child-safe-edtech-framework"
ROOT = scan.default_root()
LEVEL_NAMES = {1: "Legal baseline", 2: "Forward-compliant", 3: "Best practice"}
TIER_LABEL = {1: "Law", 2: "Coming", 3: "Recommended"}
TIER_LONG = {1: "Required by law today", 2: "Proposals and official benchmarks (EU KIDS Act proposal, DSA guidelines)",
             3: "Research and expert recommendations"}
CHOICE_LABEL = {"never": "Never (red line)", "approval": "Only with written approval", "level": "Follow our level"}
BAND_AGES = {"B1": "3 to 5", "B2": "6 to 9", "B3": "10 to 12", "B4": "13 to 15", "B5": "16 to 17"}
PROFILE_NAMES = {"A": "Educational games", "B": "Game-based applications and software", "C": "Gamified applications"}

# Interface text of the web form. Translations live in framework/i18n/<code>.yaml (same keys).
UI_EN = {
    "lang_label": "Language", "about": "About CSEF", "hero_title": "Set your child-safety boundaries",
    "lead_new": "Answer the questions. Your guardrails file, reports and staff policy are generated from them.",
    "lead_edit": "Editing version {v}. Change any answer and generate again.",
    "lead_tail": "It takes about 15 minutes. You do not need to be a developer.",
    "get1_t": "Staff policy", "get1_d": "Plain language, for everyone in your organisation.",
    "get2_t": "Boundaries report", "get2_d": "Each answer matched with the law, for management and legal counsel.",
    "get3_t": "Guardrails file", "get3_d": "Your rules, checked automatically in every project.",
    "get4_t": "For developers", "get4_d": "Instructions for AI coding tools and a ready CI check.",
    "privacy_local": "Everything runs on this computer. Nothing is sent anywhere.",
    "privacy_web": "Your answers stay in this browser. Nothing is sent anywhere. The kit is made on your device.",
    "output_note": "", "mt_note": "",
    "steps": "Steps", "so_far": "Your answers so far", "c_red": "Red lines", "c_amber": "Only with approval",
    "c_covered": "Covered by law or level", "c_gap": "Recommended, not adopted", "c_na": "Not applicable",
    "generate": "Generate the policy kit", "save": "Save answers.json", "load": "Load answers.json",
    "legend_law": "required today", "legend_coming": "EU KIDS Act proposal, official guidelines (Level 2)",
    "legend_rec": "research and experts (Level 3)", "tier1": "Law", "tier2": "Coming", "tier3": "Recommended",
    "ch_never": "Never (red line)", "ch_approval": "Only with written approval", "ch_level": "Follow our level",
    "rules": "Rules",
    "foot": "Child-Safe EdTech Framework (CSEF) v{v}. Build safe things for kids. Together. A framework, not a standard. Not legal advice.",
    "hint_red_law": "Required by law already. A red line also blocks weak signals.",
    "hint_red_req": "Red line. Also required at your level.",
    "hint_red_above": "Red line beyond the law and your level.",
    "hint_amber_req": "These rules already apply at your level. Approval documents how you comply; it cannot switch them off.",
    "hint_amber": "Allowed only with a written decision record.",
    "hint_cov_law": "Covered by the law.", "hint_cov": "Covered by your level.",
    "hint_gap": "Not adopted. Recommended at Level {n}.",
    "loaded": "Answers loaded", "loaded_v": " (version {v})", "loaded_tail": ". Change what you need, then generate again.",
    "bad_file": "That file is not an answers.json.",
    "st_engine": "Loading the policy engine. The first time takes up to a minute.",
    "st_rules": "Loading the CSEF rules...", "st_gen": "Generating your kit...", "fix": "Please fix:",
    "ready": "Version {v} is ready.", "dl_kit": "Download the kit (.zip)", "open_policy": "Open the staff policy",
    "open_report": "Open the boundaries report",
    "pdf_tip": "To get a PDF, open a document and print it to PDF. The zip has Word versions too.",
    "changes": "Changes since the last version:", "check_first": "Check these first:",
    "gen_fail": "The kit could not be generated in this browser. Save your answers and try again later, or use the command line tool.",
    "served_written": "written to", "served_changes": "Changes:",
    "served_unreach": "Could not reach the local tool. Is it still running?",
}


# --------------------------------------------------------------------------- loading

class Q:
    """Questionnaire plus the framework it refers to."""

    def __init__(self, root: Path = ROOT):
        self.root = root
        self.doc = scan.load_yaml(root / "framework" / "questionnaire.yaml")
        self.std = scan.load_standard(root)
        self.packs = []
        for p in sorted((root / "packs").glob("*.yaml")):
            if p.name.startswith("_"):
                continue
            meta = (scan.load_yaml(p) or {}).get("pack", {})
            self.packs.append({"value": str(meta.get("jurisdiction", p.stem)).upper(),
                               "label": meta.get("title", p.stem), "file": p.name})
        self.i18n = {}
        docs = [scan.load_yaml(f) or {} for f in (root / "framework" / "i18n").glob("*.yaml")]
        for doc in sorted(docs, key=lambda d: (d.get("order", 99), d.get("code", ""))):
            self.i18n[doc["code"]] = doc
        self.questions = {}
        self.boundaries = []
        for s in self.doc["sections"]:
            for q in s.get("questions", []) or []:
                self.questions[q["id"]] = dict(q, section=s["id"])
            for g in s.get("groups", []) or []:
                for q in g["questions"]:
                    b = dict(q, type="boundary", group=g["title"], group_id=g.get("id", g["title"]), section=s["id"])
                    b["tier"] = min(int(self.std.rules[r]["tier"]) for r in b["rules"])
                    self.questions[b["id"]] = b
                    self.boundaries.append(b)

    def options(self, q):
        if q.get("options_from") == "packs":
            return [{"value": "EU", "label": "European Union (always applies)"}] + [
                {"value": p["value"], "label": p["label"]} for p in self.packs]
        if q.get("options_from") in ("dependency_sets", "phrase_sets"):
            sets = self.doc[q["options_from"]]
            return [{"value": k, "label": v["label"]} for k, v in sets.items()]
        if q["type"] == "boundary":
            opts = [{"value": "never", "label": CHOICE_LABEL["never"]}]
            if q.get("approval"):
                opts.append({"value": "approval", "label": CHOICE_LABEL["approval"]})
            opts.append({"value": "level", "label": CHOICE_LABEL["level"]})
            return opts
        return q.get("options", [])

    def default(self, q):
        if q["type"] == "boundary":
            return "level"
        if q["type"] in ("multi", "list"):
            if q.get("options_from") == "packs":
                return ["EU"]
            return list(q.get("default", []) or [])
        return q.get("default", "")

    def visible(self, q, answers) -> bool:
        if q["type"] != "boundary":
            return True
        feats = set(answers.get("features") or [])
        profs = set(answers.get("profiles") or [])
        if q.get("features") and not (feats & set(q["features"])):
            return False
        if q.get("profiles") and not (profs & set(q["profiles"])):
            return False
        return True

    def schema(self) -> dict:
        """What the web form needs: questions, options, translations and interface text."""
        secs = []
        for s in self.doc["sections"]:
            sec = {"id": s["id"], "title": s["title"], "intro": " ".join(str(s.get("intro", "")).split()),
                   "questions": [], "groups": []}
            for q in s.get("questions", []) or []:
                opts = [dict(o, desc=" ".join(str(o.get("desc", "")).split())) if o.get("desc") else o
                        for o in self.options(q)]
                sec["questions"].append(dict(q, help=" ".join(str(q.get("help", "")).split()), options=opts,
                                             default=self.default(q)))
            for g in s.get("groups", []) or []:
                sec["groups"].append({"id": g.get("id", g["title"]), "title": g["title"],
                                      "intro": " ".join(str(g.get("intro", "")).split()), "questions": [
                    {"id": b["id"], "type": "boundary", "label": b["label"], "tier": b["tier"],
                     "help": " ".join(str(b.get("help", "")).split()),
                     "features": b.get("features", []), "profiles": b.get("profiles", []),
                     "options": self.options(b), "default": "level", "rules": b["rules"]}
                    for b in (self.questions[x["id"]] for x in g["questions"])]})
            secs.append(sec)
        langs = [{"code": "en", "name": "English", "mt": False}] + [
            {"code": c, "name": d.get("language", c), "mt": bool(d.get("machine_translated"))}
            for c, d in self.i18n.items()]
        return {"sections": secs, "framework_version": self.std.version, "tiers": TIER_LABEL, "ui": UI_EN,
                "languages": langs, "i18n": {c: {k: d.get(k, {}) for k in ("ui", "sections", "groups", "questions")}
                                             for c, d in self.i18n.items()}}

    def i18n_missing(self, code: str) -> list[str]:
        """Texts of the form that a translation does not cover."""
        d, miss = self.i18n.get(code, {}), []
        for k in UI_EN:
            if k not in (d.get("ui") or {}) and UI_EN[k]:
                miss.append(f"ui.{k}")
        for s in self.doc["sections"]:
            if "title" not in (d.get("sections") or {}).get(s["id"], {}):
                miss.append(f"sections.{s['id']}")
            for g in s.get("groups", []) or []:
                gt = (d.get("groups") or {}).get(g.get("id"), {})
                if "title" not in gt or (g.get("intro") and "intro" not in gt):
                    miss.append(f"groups.{g.get('id')}")
        for qid, q in self.questions.items():
            qt = (d.get("questions") or {}).get(qid, {})
            if "label" not in qt:
                miss.append(f"questions.{qid}.label")
            if q.get("help") and "help" not in qt:
                miss.append(f"questions.{qid}.help")
            if q["type"] != "boundary" and not q.get("options_from") or q.get("options_from") in ("dependency_sets",):
                for o in self.options(q):
                    ot = (qt.get("options") or {}).get(str(o["value"]), {})
                    if "label" not in ot or (o.get("desc") and "desc" not in ot):
                        miss.append(f"questions.{qid}.options.{o['value']}")
        return miss


def normalise(q: Q, raw: dict) -> tuple[dict, list[str]]:
    """Fill defaults, coerce types, validate. Returns (answers, errors)."""
    a, errs = {}, []
    if raw.get("org_name") and not raw.get("pack_id"):
        guess = re.sub(r"[^a-z]", "", str(raw["org_name"]).lower())[:8]
        raw = dict(raw, pack_id=guess if len(guess) >= 2 else "")
    for qid, qq in q.questions.items():
        v = raw.get(qid, q.default(qq))
        t = qq["type"]
        if t in ("multi", "list"):
            if isinstance(v, str):
                v = [x.strip() for x in re.split(r"[\n,]" if t == "multi" else r"\n", v) if x.strip()]
            v = [str(x).strip() for x in (v or []) if str(x).strip()]
        else:
            v = "" if v is None else str(v).strip()
        vals = {o["value"] for o in q.options(qq)}
        if t in ("single", "boundary") and v and v not in vals:
            errs.append(f"{qq['label']}: '{v}' is not one of {sorted(vals)}")
        if t == "multi" and vals:
            bad = [x for x in v if x not in vals]
            if bad:
                errs.append(f"{qq['label']}: unknown option(s) {bad}")
        if qq.get("required") and not v:
            errs.append(f"{qq['label']}: required")
        if qq.get("pattern") and v and not re.match(qq["pattern"], v):
            errs.append(f"{qq['label']}: '{v}' does not match {qq['pattern']}")
        a[qid] = v
    if "none" in a.get("features", []):
        a["features"] = []
    if "EU" not in a.get("jurisdictions", []):
        a["jurisdictions"] = ["EU"] + a.get("jurisdictions", [])
    return a, errs


# --------------------------------------------------------------------------- matching

def assess(q: Q, a: dict) -> dict:
    """Match each boundary with the law and the chosen level."""
    level = int(a["minimum_level"] or 1)
    items, warnings, notes, approval_req = [], [], [], []
    for b in q.boundaries:
        vis = q.visible(b, a)
        choice = a.get(b["id"], "level") if vis else None
        tier = b["tier"]
        required = tier <= level
        if not vis:
            result, key = "Not applicable: you do not use the features this is about", "na"
        elif choice == "never":
            key = "red"
            result = ("Red line. The law already requires it; you also block it on weak signals" if tier == 1 else
                      "Red line above the law" if not required else "Red line. Also required at your level")
        elif choice == "approval":
            key = "amber"
            if required:
                result = "Approval adds a written check. The rules for your level still apply"
                approval_req.append(b["label"])
            else:
                result = "Allowed with written approval"
        else:
            key = "covered" if required else "gap"
            result = ("Covered: the law applies" if tier == 1 else "Covered by your level") if required else \
                f"Not adopted. Recommended at Level {tier}"
        srcs = []
        for r in b["rules"]:
            for s in q.std.rules[r]["sources"]:
                if s not in srcs:
                    srcs.append(s)
        items.append(dict(b, visible=vis, choice=choice, result=result, key=key, sources=srcs, required=required))

    if approval_req:
        notes.append("For these, approval adds a written check, but the framework rules already apply at your level "
                     "and approval cannot switch them off: " + "; ".join(approval_req) + ".")
    bands, feats, buyers = set(a["age_bands"]), set(a["features"]), a.get("buyers")
    if level == 1 and bands & {"B1", "B2"}:
        warnings.append("Your products are used by children under 10, but you chose Level 1. Many protections for "
                        "young children (protective defaults, preset messages, adult in control for ages 3 to 5) are "
                        "Level 2. We recommend Level 2.")
    if "B1" in bands and "ai_generative" in feats and a.get("genai") != "never":
        warnings.append("Children aged 3 to 5 may talk to generative AI. Make sure an adult is always in control "
                        "(AGE-B1-01) and consider making direct AI conversation a red line for this age.")
    if "B2" in bands and "chat" in feats and a.get("chat") != "never" and level < 2:
        notes.append("Under 10, the framework expects preset messages only (AGE-B2-01, Level 2).")
    if buyers in ("families", "both"):
        notes.append("The EU KIDS Act proposal exempts services operated by or on behalf of schools (Art. 2(4)(c)). "
                     "Products sold to families are not covered by that exemption.")
    if buyers == "other":
        notes.append("Your products are free, publicly funded, sponsored or paid for in another way. That does not change "
                     "the protections: the EU KIDS Act proposal covers games whether they are free, paid or mixed "
                     "(Recital 12). Its education exemption (Art. 2(4)(c)) depends on who operates the service (schools "
                     "or others on their behalf), not on who pays. Ask legal counsel if it may apply.")
    if buyers in ("schools", "both"):
        notes.append("Even when the education exemption of the EU KIDS Act proposal applies, GDPR, the DSA and the "
                     "AI Act still apply. CSEF applies the same protections in every channel. Ask legal counsel "
                     "whether the exemption covers your product.")
    for j in a["jurisdictions"]:
        if j != "EU" and j not in {p["value"] for p in q.packs}:
            notes.append(f"There is no CSEF pack for {j} yet. National rules there are not checked.")
    counts = {k: sum(1 for i in items if i["key"] == k) for k in ("red", "amber", "covered", "gap", "na")}
    counts["above_law"] = sum(1 for i in items if i["key"] == "red" and i["tier"] > 1)
    return {"items": items, "warnings": warnings, "notes": notes, "counts": counts, "level": level}


def build_pack(q: Q, a: dict, res: dict, version: str, today: str) -> tuple[dict, dict]:
    """Return (pack document, comments by rule id for no_go)."""
    pid, pfx = a["pack_id"], a["pack_id"].upper()
    org = a["org_name"]
    no_go, comments = [], {}
    for i in res["items"]:
        if i["key"] == "red":
            for r in i["rules"]:
                if r not in no_go:
                    no_go.append(r)
                    comments[r] = i["label"]
    deps = []
    for k in a["forbid_sets"]:
        deps += q.doc["dependency_sets"][k]["packages"]
    deps += a["forbid_extra"]
    phrases = []
    for k in a["phrase_sets"]:
        phrases += q.doc["phrase_sets"][k]["phrases"]
    phrases += a["phrase_extra"]
    feats = []
    for i in res["items"]:
        if i["key"] == "amber":
            for f in i.get("features", []):
                if f in a["features"] and f not in feats:
                    feats.append(f)
    policy = {"minimum_level": res["level"]}
    if no_go:
        policy["no_go"] = no_go
    if deps:
        policy["forbid_dependencies"] = list(dict.fromkeys(deps))
    if phrases:
        policy["forbid_phrases"] = list(dict.fromkeys(phrases))
    if feats:
        policy["require_decision_for_features"] = feats
    policy["review_every_days"] = int(a["review_every_days"] or 180)
    policy["require_agent_instructions"] = a["agent_instructions"] == "yes"
    doc = {
        "pack": {"id": pid, "title": f"{org} child-safety policy", "jurisdiction": "ORG", "version": version,
                 "date": today, "maintainer": f"{org}: {a['owner']}",
                 "status": f"In force for: {a['scope']}", "url": None,
                 "generated_by": f"{TOOL} {scan.TOOL_VERSION} from answers.json"},
        "parameters": {"owner": a["owner"], "waiver_approvers": a["approvers"],
                       "waiver_max_days": int(a["waiver_days"] or 90), "contact": a["contact"], "scope": a["scope"],
                       "profiles": a["profiles"], "age_bands": a["age_bands"], "features": a["features"],
                       "jurisdictions": a["jurisdictions"]},
        "policy": policy,
    }
    rules = []
    for n, text in enumerate(a["own_rules"], 1):
        rules.append({"id": f"{pfx}-OWN-{n:02d}", "title": text[:90], "level": "MUST", "tier": 1, "profiles": ["core"],
                      "age_bands": ["all"], "requirement": text,
                      "rationale": f"{org} red line, set in the CSEF questionnaire.",
                      "improvement": f"Check in every review. If a product needs an exception, ask {a['approvers']}.",
                      "effort": "low", "sources": [f"{pfx}-POLICY"], "detection": {"method": "manual"}})
    if rules:
        doc["rules"] = rules
    return doc, comments


def pack_yaml(doc: dict, comments: dict, a: dict) -> str:
    pid = doc["pack"]["id"]
    head = [f"# CSEF company pack: {a['org_name']}",
            "# Generated by the CSEF policy questionnaire (tooling/policy.py). To change it, run the",
            "# questionnaire again with answers.json rather than editing this file by hand.",
            "#",
            "# Use in a product repository:",
            f"#   1. Copy this file to .csef/packs/{pid}.yaml",
            f"#   2. In csef.yaml:  jurisdictions: [{', '.join(a['jurisdictions'])}]",
            f"#                     packs: [.csef/packs/{pid}.yaml]",
            "#   3. Run the scanner, the GitHub Action or the csef-review skill as usual.",
            "#", f"# Validate: python3 tooling/build.py --validate-pack {pid}.yaml", ""]
    body = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=110)
    out = []
    for line in body.splitlines():
        m = re.match(r"^  - ([A-Z]+-[A-Z0-9]+-\d{2})$", line)
        if m and m.group(1) in comments:
            line = f"{line:<20}# {comments[m.group(1)]}"
        out.append(line)
    return "\n".join(head + out) + "\n"


def validate_pack(path: Path) -> list[str]:
    try:
        import build
    except ImportError:  # inside the Claude skill, where build.py is not bundled
        try:
            scan.apply_pack(scan.load_standard(ROOT), path)
            return []
        except (ValueError, KeyError) as ex:
            return [str(ex)]
    build.errors.clear()
    res = build.validate_pack_file(path)
    errs = list(build.errors)
    if not res and not errs:
        errs.append("pack could not be loaded")
    return errs


def diff_answers(q: Q, old: dict, new: dict) -> list[str]:
    out = []
    for qid, qq in q.questions.items():
        o, n = old.get(qid), new.get(qid)
        if qq["type"] == "boundary":
            o = o if o is not None else "level"
        if o == n or (not o and not n):
            continue
        label = qq["label"]
        if qq["type"] in ("multi", "list"):
            o, n = set(o or []), set(n or [])
            parts = []
            if n - o:
                parts.append("added " + ", ".join(sorted(n - o)))
            if o - n:
                parts.append("removed " + ", ".join(sorted(o - n)))
            out.append(f"{label}: {'; '.join(parts)}")
        elif qq["type"] == "boundary":
            out.append(f"{label}: {CHOICE_LABEL.get(o, o)} → {CHOICE_LABEL.get(n, n)}")
        else:
            names = {x["value"]: x["label"] for x in q.options(qq)}
            out.append(f"{label}: {names.get(o, o or 'empty')} → {names.get(n, n or 'empty')}")
    return out


def bump(version: str) -> str:
    try:
        major, minor, _ = (int(x) for x in version.split("."))
        return f"{major}.{minor + 1}.0"
    except Exception:
        return "1.0.0"


# --------------------------------------------------------------------------- documents
# A document is a list of blocks: ("h1"|"h2"|"h3"|"p"|"note"|"warn", text), ("ul", [text]),
# ("table", headers, rows, keys). **bold** is supported in text.

KEY_COL = {"red": ("#FBE7E1", "#B3452B"), "amber": ("#FDF1D8", "#8A5C00"), "covered": ("#E0F0EC", "#16695D"),
           "gap": ("#EEEAE0", "#4A5468"), "na": ("#F6F3EC", "#4A5468"),
           1: ("#E0F0EC", "#16695D"), 2: ("#E6E9F8", "#3B4DA6"), 3: ("#EFE8F8", "#6F51A8")}
KEY_CLASS = {"red": "coral", "amber": "sun", "covered": "teal", "gap": "neutral", "na": "faint", 1: "teal", 2: "indigo", 3: "lilac"}


def to_md(blocks) -> str:
    out = []
    for b in blocks:
        k = b[0]
        if k in ("h1", "h2", "h3"):
            out += ["#" * int(k[1]) + " " + b[1], ""]
        elif k == "p":
            out += [b[1], ""]
        elif k in ("note", "warn"):
            out += ["> " + ("**Warning.** " if k == "warn" else "") + b[1], ""]
        elif k == "ul":
            out += [f"- {x}" for x in b[1]] + [""]
        elif k == "table":
            out += ["| " + " | ".join(b[1]) + " |", "|" + "---|" * len(b[1])]
            out += ["| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |" for r in b[2]]
            out += [""]
    return "\n".join(out)


def _inline(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return re.sub(r"(https?://[^\s<)]+)", r'<a href="\1">\1</a>', t)


HTML_CSS = brand.tokens_css() + brand.BASE_CSS + """
*{box-sizing:border-box}body{margin:0;background:var(--c-paper);color:var(--c-ink);font:16px/1.6 var(--font)}
main{max-width:920px;margin:0 auto;padding:28px 16px 64px}h1{font-size:2rem;line-height:1.15;margin:0 0 8px}
h2{font-size:1.35rem;margin:40px 0 12px;padding-top:14px;border-top:1px solid var(--c-line)}h3{font-size:1.08rem;margin:24px 0 8px}
p,li{overflow-wrap:anywhere}a{color:var(--c-teal-t)}code{font-size:.9em;background:var(--c-code);padding:1px 5px;border-radius:5px}
.note,.warn{border-left:4px solid var(--c-teal);background:var(--c-panel);padding:12px 16px;margin:12px 0;border-radius:0 10px 10px 0}
.warn{border-color:var(--c-sun);background:var(--c-sun-bg)}
.tw{overflow-x:auto;margin:10px 0 18px;border:1px solid var(--c-line);border-radius:12px;background:var(--c-panel)}
table{border-collapse:collapse;width:100%;font-size:.92rem}th,td{padding:9px 11px;text-align:left;vertical-align:top;border-bottom:1px solid var(--c-line)}
th{font-size:.76rem;text-transform:uppercase;letter-spacing:.05em;color:var(--c-ink2);font-weight:600}tr:last-child td{border-bottom:0}
td:first-child{min-width:150px;width:30%}
.pill{display:inline-block;padding:2px 9px;border-radius:8px;font-size:.82rem;font-weight:600;line-height:1.4}
.k-coral{background:var(--c-coral-bg);color:var(--c-coral-t)}.k-sun{background:var(--c-sun-bg);color:var(--c-sun-t)}
.k-teal{background:var(--c-teal-bg);color:var(--c-teal-t)}.k-indigo{background:var(--c-indigo-bg);color:var(--c-indigo-t)}
.k-lilac{background:var(--c-lilac-bg);color:var(--c-lilac-t)}.k-neutral{background:var(--c-code);color:var(--c-ink2)}
.k-faint{background:transparent;color:var(--c-ink2);font-weight:500}
.meta{color:var(--c-ink2);margin:0 0 14px}ul{padding-left:22px}li{margin:5px 0}
footer{margin-top:48px;padding-top:14px;border-top:1px solid var(--c-line);color:var(--c-ink2);font-size:.85rem}
@media print{body{font-size:10.5pt}main{max-width:none;padding:0}h2{break-after:avoid}tr{break-inside:avoid}
.tw{overflow:visible}@page{size:A4;margin:14mm 14mm 16mm}}
"""


def to_html(blocks, title: str) -> str:
    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
           f'content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>{brand.head()}'
           f'<style>{HTML_CSS}</style></head><body><div class="csef-stripe"></div><main>{brand.logo("lockup", 44)}']
    for b in blocks:
        k = b[0]
        if k in ("h1", "h2", "h3"):
            out.append(f"<{k}>{_inline(b[1])}</{k}>")
        elif k == "p":
            out.append(f"<p>{_inline(b[1])}</p>")
        elif k in ("note", "warn"):
            out.append(f'<div class="{k}">{"<strong>Warning.</strong> " if k == "warn" else ""}{_inline(b[1])}</div>')
        elif k == "ul":
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in b[1]) + "</ul>")
        elif k == "table":
            keys = b[3] if len(b) > 3 else [None] * len(b[2])
            rows = []
            for r, key in zip(b[2], keys):
                cells = []
                kk, cols = (key if isinstance(key, tuple) else (key, [len(r) - 1])) if key else (None, [])
                for ci, c in enumerate(r):
                    txt = _inline(str(c))
                    if kk is not None and ci in cols:
                        txt = f'<span class="pill k-{KEY_CLASS.get(kk, "neutral")}">{txt}</span>'
                    cells.append(f"<td>{txt}</td>")
                rows.append("<tr>" + "".join(cells) + "</tr>")
            out.append('<div class="tw"><table><thead><tr>' + "".join(f"<th>{html.escape(h)}</th>" for h in b[1]) +
                       "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")
    out.append(f'<footer>Child-Safe EdTech Framework (CSEF). {brand.TAGLINE} A framework, not a standard. '
               'Not legal advice.</footer></main></body></html>')
    return "\n".join(out)


def to_docx(blocks, path: Path, title: str) -> None:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    d = Document()
    d.core_properties.title = title
    brand.style_docx(d)
    logo_png = brand.png("csef-lockup-on-light")
    if logo_png:
        from docx.shared import Cm
        d.add_picture(str(logo_png), width=Cm(5.5))
    st = d.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(10.5)

    def runs(par, text, size=None):
        for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
            if part:
                r = par.add_run(part.replace("`", ""))
                r.bold = bool(i % 2)
                if size:
                    r.font.size = Pt(size)

    def shade(cell, hexcol):
        tcPr = cell._tc.get_or_add_tcPr()
        s = OxmlElement("w:shd")
        s.set(qn("w:val"), "clear"), s.set(qn("w:color"), "auto"), s.set(qn("w:fill"), hexcol.lstrip("#"))
        tcPr.append(s)

    for b in blocks:
        k = b[0]
        if k in ("h1", "h2", "h3"):
            d.add_heading(b[1].replace("**", ""), level=int(k[1]))
        elif k == "p":
            runs(d.add_paragraph(), b[1])
        elif k in ("note", "warn"):
            p = d.add_paragraph()
            if k == "warn":
                r = p.add_run("Warning. ")
                r.bold, r.font.color.rgb = True, RGBColor(0xB4, 0x53, 0x09)
            runs(p, b[1])
            p.paragraph_format.left_indent = Pt(12)
        elif k == "ul":
            for x in b[1]:
                runs(d.add_paragraph(style="List Bullet"), x)
        elif k == "table":
            headers, rows = b[1], b[2]
            keys = b[3] if len(b) > 3 else [None] * len(rows)
            t = d.add_table(rows=1, cols=len(headers))
            t.style, t.alignment = "Table Grid", WD_TABLE_ALIGNMENT.LEFT
            for i, h in enumerate(headers):
                c = t.rows[0].cells[i]
                c.text = ""
                runs(c.paragraphs[0], f"**{h}**", 9)
                shade(c, "#EEF0F3")
            for r, key in zip(rows, keys):
                cells = t.add_row().cells
                for i, v in enumerate(r):
                    cells[i].text = ""
                    runs(cells[i].paragraphs[0], str(v), 9)
                if key:
                    kk, cols = key if isinstance(key, tuple) else (key, [len(r) - 1])
                    for ci in cols:
                        shade(cells[ci], KEY_COL.get(kk, ("#FFFFFF",))[0])
            d.add_paragraph()
    d.save(str(path))


def write_doc(blocks, out: Path, stem: str, title: str, formats) -> list[Path]:
    written = []
    if "md" in formats:
        p = out / f"{stem}.md"
        p.write_text(to_md(blocks), encoding="utf-8")
        written.append(p)
    h = to_html(blocks, title)
    if "html" in formats:
        p = out / f"{stem}.html"
        p.write_text(h, encoding="utf-8")
        written.append(p)
    if "pdf" in formats:
        import export
        p = out / f"{stem}.pdf"
        try:
            export.render_pdf(h, p)
            written.append(p)
        except Exception as ex:  # noqa: BLE001
            print(f"{TOOL}: PDF skipped ({ex})", file=sys.stderr)
    if "docx" in formats:
        p = out / f"{stem}.docx"
        try:
            to_docx(blocks, p, title)
            written.append(p)
        except ImportError:
            print(f"{TOOL}: Word skipped (pip install python-docx)", file=sys.stderr)
    return written


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def fill(text: str, a: dict) -> str:
    return text.replace("{org}", a["org_name"]).replace("{approvers}", a["approvers"])


def src_line(q: Q, sid: str) -> str:
    s = q.std.sources.get(sid, {})
    url = s.get("url")
    return f"**{sid}** {s.get('title', sid)}" + (f" ({s.get('status')})" if s.get("status") else "") + (f": {url}" if url else "")


def boundaries_report(q: Q, a: dict, res: dict, pack: dict, changes: list[str], prev_version: str | None) -> list:
    level, c = res["level"], res["counts"]
    pid = a["pack_id"]
    B = [("h1", f"{a['org_name']}: child-safety boundaries report"),
         ("p", f"Policy version **{pack['pack']['version']}** · {pack['pack']['date']} · CSEF {q.std.version} · "
               f"generated by {TOOL} {scan.TOOL_VERSION}"),
         ("note", "This report shows what you chose, what the law already requires and what is recommended. It is a "
                  "self-assessment of your intentions, not legal advice and not a certification. Ask your DPO and legal "
                  "counsel to review it."),
         ("h2", "Summary"),
         ("table", ["", ""], [
             ["Organisation", a["org_name"]], ["Policy owner", a["owner"]], ["Exceptions approved by", a["approvers"]],
             ["Scope", a["scope"]], ["Minimum level", f"Level {level}, {LEVEL_NAMES[level]}"],
             ["Products", ", ".join(PROFILE_NAMES[p] for p in a["profiles"])],
             ["Ages", ", ".join(BAND_AGES[x] for x in a["age_bands"])],
             ["Countries", ", ".join(a["jurisdictions"])],
             ["Features", ", ".join(a["features"]) or "none declared"]]),
         ("table", ["Result", "Count"], [
             ["Red lines", c["red"]], ["of which go beyond the law and your level", c["above_law"]],
             ["Allowed only with written approval", c["amber"]], ["Covered by the law or your level", c["covered"]],
             ["Recommended but not adopted", c["gap"]], ["Not applicable", c["na"]]],
          [("red", [1]), ("red", [1]), ("amber", [1]), ("covered", [1]), ("gap", [1]), ("na", [1])])]
    if res["warnings"]:
        B.append(("h2", "Check these first"))
        B += [("warn", w) for w in res["warnings"]]
    if res["notes"]:
        B.append(("h2", "Notes"))
        B.append(("ul", res["notes"]))
    if changes:
        B += [("h2", f"Changes since version {prev_version}"), ("ul", changes)]

    B += [("h2", "Your boundaries"),
          ("p", "Legal status: **Law** = required today; **Coming** = EU KIDS Act proposal and official guidelines "
                "(Level 2); **Recommended** = research and experts (Level 3).")]
    for g in dict.fromkeys(i["group"] for i in res["items"]):
        rows, keys = [], []
        for i in (x for x in res["items"] if x["group"] == g):
            rows.append([i["label"], CHOICE_LABEL.get(i["choice"], "Not asked"), TIER_LABEL[i["tier"]],
                         ", ".join(i["rules"]), i["result"]])
            keys.append(i["key"])
        B += [("h3", g), ("table", ["Practice", "Your answer", "Legal status", "Rules", "Result"], rows, keys)]

    law = [i for i in res["items"] if i["visible"] and i["tier"] == 1]
    above = [i for i in res["items"] if i["key"] == "red" and i["tier"] > 1]
    gaps = [i for i in res["items"] if i["key"] == "gap"]
    amber = [i for i in res["items"] if i["key"] == "amber"]
    B += [("h2", "Legal and recommended, side by side"),
          ("h3", "Required by law, whatever you answer"),
          ("p", "These apply at every level. Your answer only decides whether the scanner also blocks weak signals."),
          ("ul", [f"**{i['label']}** ({', '.join(i['rules'])}): {q.std.rules[i['rules'][0]]['title']}" for i in law]
           or ["None in scope."]),
          ("h3", "Your choices beyond the law"),
          ("ul", [f"**{i['label']}**: {TIER_LABEL[i['tier']].lower()}, adopted as a red line" for i in above]
           or ["None. Consider which recommended practices you want as red lines."]),
          ("h3", "Allowed with written approval"),
          ("ul", [f"**{i['label']}**: needs a decision record approved by {a['approvers']}"
                  + (" (the rules still apply at your level)" if i["required"] else "") for i in amber] or ["None."]),
          ("h3", "Recommended, not adopted")]
    if gaps:
        B.append(("p", "These practices are recommended above your minimum level. A product can still choose a higher "
                       "level. This is what adopting each one would take:"))
        B.append(("table", ["Practice", "Level", "What it would take"],
                  [[i["label"], f"{i['tier']} ({TIER_LABEL[i['tier']]})",
                    " ".join(q.std.rules[r]["improvement"].strip() for r in i["rules"][:2])] for i in gaps],
                  [(i["tier"], [1]) for i in gaps]))
    else:
        B.append(("ul", ["None. Every recommendation in scope is covered by your level or a red line."]))

    pol = pack["policy"]
    B += [("h2", "What the guardrails file contains"),
          ("p", f"`{pid}.yaml` is what the scanner applies to every product that lists it in `csef.yaml`."),
          ("table", ["Setting", "Value"], [
              ["Minimum level", pol["minimum_level"]],
              ["Red lines (no_go)", len(pol.get("no_go", []))],
              ["Forbidden packages", len(pol.get("forbid_dependencies", []))],
              ["Forbidden phrases", len(pol.get("forbid_phrases", []))],
              ["Features needing a decision record", ", ".join(pol.get("require_decision_for_features", [])) or "none"],
              ["Manifest review", f"every {pol['review_every_days']} days"],
              ["AI agent instructions required", "yes" if pol["require_agent_instructions"] else "no"],
              ["Own rules (checked by people)", len(pack.get("rules", []))]])]
    if pack.get("rules"):
        B.append(("ul", [f"**{r['id']}** {r['requirement']}" for r in pack["rules"]]))

    srcs = []
    for i in res["items"]:
        if i["visible"]:
            srcs += [s for s in i["sources"] if s not in srcs]
    B += [("h2", "Sources"), ("ul", [src_line(q, s) for s in srcs]),
          ("p", "Proposals are not law. Status as recorded in `framework/sources.yaml`.")]
    return B


def staff_policy(q: Q, a: dict, res: dict, pack: dict) -> list:
    level = res["level"]
    org, pid = a["org_name"], a["pack_id"]
    items = [i for i in res["items"] if i["visible"]]
    never = [fill(i["never"], a) for i in items if i["key"] == "red"]
    law_level = [fill(i["level"], a) for i in items if i["key"] == "covered"]
    approval = [fill(i["approval"], a) for i in items if i["key"] == "amber"]
    feats = set(a["features"])
    always = [x["text"] for x in q.doc["always"]
              if x["level"] <= level and (not x.get("features") or feats & set(x["features"]))]
    pol = pack["policy"]
    B = [("h1", f"{org}: how we keep children safe in our products"),
         ("p", f"Version {pack['pack']['version']} · {pack['pack']['date']} · Owner: {a['owner']} · "
               f"Questions: {a['contact']}"),
         ("h2", "Why we have these rules"),
         ("p", f"This policy covers: {a['scope']}. Children use these products, and children need more protection than adults. "
               "The law says so, and so do we. These rules apply to everyone: design, development, content, "
               "sales and support. They also apply to suppliers and to AI tools that write code for us."),
         ("p", f"Our minimum level is **Level {level}, {LEVEL_NAMES[level]}**. "
               + {1: "We follow what the law requires today.",
                  2: "We follow the law and what is coming soon, such as the EU KIDS Act proposal.",
                  3: "We follow the law, what is coming, and what research recommends."}[level]),
         ("h2", "We never do this"),
         ("p", "These are our red lines. No deadline and no client request changes them."),
         ("ul", never or ["We have no extra red lines. The law and our level still apply."])]
    if law_level:
        B += [("h2", "The law and our level also say"), ("ul", law_level)]
    if approval:
        B += [("h2", "Only with written approval"),
              ("p", f"Ask before you design these. {cap(a['approvers'])} must approve in writing. "
                    "Write a short decision record: what, why, which safeguards, who approved, until when."),
              ("ul", approval)]
    B += [("h2", "We always do this"), ("ul", always)]
    if a["own_rules"]:
        B += [("h2", "Our own rules"), ("ul", a["own_rules"])]
    if pol.get("forbid_dependencies") or pol.get("forbid_phrases"):
        B.append(("h2", "Tools and words we never use"))
        if pol.get("forbid_dependencies"):
            names = [q.doc["dependency_sets"][k]["label"] for k in a["forbid_sets"]] + a["forbid_extra"]
            B += [("p", "These kinds of packages are never added to a product:"), ("ul", names)]
        if pol.get("forbid_phrases"):
            ex = pol["forbid_phrases"][:6]
            B += [("p", "We never write pressure or guilt messages for children. For example:"),
                  ("ul", [f"\"{x}\"" for x in ex] + [f"and {len(pol['forbid_phrases']) - len(ex)} more in "
                                                      f"`{pid}.yaml`"] if len(pol["forbid_phrases"]) > len(ex) else
                   [f"\"{x}\"" for x in ex])]
    B += [("h2", "Before you build something new"),
          ("ul", ["Check it against the lists above.",
                  "If it needs approval, ask first. Do not start building.",
                  "If you are not sure, ask. Asking is always right.",
                  "Run the check on your project before every release."]),
          ("h2", "How to check your project"),
          ("ul", [f"Put `{pid}.yaml` in your repository at `.csef/packs/{pid}.yaml`.",
                  f"List it in `csef.yaml` under `packs:`. Fill in the product's ages and features there.",
                  "Run `python3 tooling/scan.py --repo . --export html` or use the GitHub Action `csef-check.yml`.",
                  "Open `dashboard.html`. Red items block a release. Orange items need a person to look.",
                  "With Claude, use the `csef-review` skill: \"Run a CSEF review of this repository.\""]
           + (["Add `agent-instructions.md` to `CLAUDE.md` or `AGENTS.md`. AI tools must know our rules."]
              if pol["require_agent_instructions"] else [])
           + [f"Review `csef.yaml` at least every {pol['review_every_days']} days."]),
          ("h2", "Exceptions"),
          ("p", f"Sometimes a rule cannot be met yet. Then you need a waiver. Only {a['approvers']} can give one. "
                f"A waiver says why, what we do meanwhile, and when it ends. It lasts {a['waiver_days']} days at most. "
                "Red lines that are the law never get a waiver."),
          ("h2", "If something goes wrong"),
          ("p", f"Tell {a['contact']} at once. This includes a data leak, a child at risk, or a feature that breaks "
                "these rules. Do not wait. Do not fix it alone in silence."),
          ("h2", "When this policy changes"),
          ("p", f"The policy owner ({a['owner']}) reviews it when the law changes and at least once a year. Each change gets a "
                "new version number. The latest version is the one that counts.")]
    return B


def agent_md(q: Q, a: dict, res: dict, pack: dict) -> str:
    items = [i for i in res["items"] if i["visible"]]
    pol = pack["policy"]
    L = ["# Child-safety rules for AI coding agents", "",
         f"Paste this block into `CLAUDE.md`, `AGENTS.md`, Cursor rules or Lovable project knowledge in every "
         f"{a['org_name']} repository.", "", "```markdown",
         f"## Child-safety rules ({a['org_name']}, CSEF, mandatory)", "",
         f"Users of this product are children. Before changing code, read csef.yaml (ages, features, level) and "
         f".csef/packs/{a['pack_id']}.yaml. Minimum level: {res['level']} ({LEVEL_NAMES[res['level']]}).", "",
         "Never add, even if asked:"]
    L += [f"- {fill(i['never'], a)}" for i in items if i["key"] == "red"]
    L += [f"- {r}" for r in a["own_rules"]]
    if pol.get("forbid_dependencies"):
        L.append(f"- these packages: {', '.join(pol['forbid_dependencies'])}")
    amber = [i for i in items if i["key"] == "amber"]
    if amber:
        L += ["", f"Stop and ask a person (approval by {a['approvers']}) before adding:"]
        L += [f"- {i['label'].lower()}" for i in amber]
    if pol.get("forbid_phrases"):
        L += ["", "Never write child-facing text with pressure, guilt or scarcity, such as: "
              + "; ".join(f'"{x}"' for x in pol["forbid_phrases"][:8]) + "."]
    L += ["", "If a request conflicts with these rules, say so and propose a safe alternative.",
          "Run the CSEF scan before proposing a release.", "```", ""]
    return "\n".join(L)


def workflow_yml(a: dict) -> str:
    pid = a["pack_id"]
    return f"""# CSEF check with the {a['org_name']} pack. Copy to .github/workflows/csef-check.yml
# and keep the pack at .csef/packs/{pid}.yaml in the repository.
name: CSEF check
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
  security-events: write
jobs:
  csef:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: eduardon83/child-safe-edtech-framework@v{scan.TOOL_VERSION}
        with:
          packs: .csef/packs/{pid}.yaml
          fail-on: block
          export: html
"""


def kit_readme(a: dict, pack: dict, files: list[str]) -> str:
    pid = a["pack_id"]
    rows = [("staff-policy", "staff-policy.*", "Everyone", "The policy in plain language. Share it with all staff and suppliers."),
            ("boundaries-report", "boundaries-report.*", "Management, DPO, legal counsel",
             "Your answers, matched with the law and recommendations."),
            (f"{pid}.yaml", f"{pid}.yaml", "Product teams", "The guardrails file the scanner applies."),
            ("agent-instructions.md", "agent-instructions.md", "Developers",
             "Rules to paste into CLAUDE.md, AGENTS.md or Cursor rules."),
            ("csef-check.yml", "csef-check.yml", "Developers", "GitHub Actions workflow that runs the check with your pack."),
            ("csef-review.zip", "csef-review.zip", "Anyone using Claude", "The Claude skill for reviews."),
            ("answers.json", "answers.json", "Policy owner", "Your answers. Use them to change the policy later.")]
    table = "\n".join(f"| `{shown}` | {who} | {what} |" for key, shown, who, what in rows
                      if any(f == key or f.startswith(key + ".") for f in files))
    return f"""# {a['org_name']} child-safety policy kit

Version {pack['pack']['version']}, {pack['pack']['date']}. Made with the CSEF policy questionnaire.

## What is here

| File | For whom | What it is |
|---|---|---|
{table}

## Use it in a project

1. Copy `{pid}.yaml` to `.csef/packs/{pid}.yaml` in the product repository.
2. Copy `templates/csef.yaml` from the CSEF repository to the product root. Fill in ages and features.
   Add `packs: [.csef/packs/{pid}.yaml]` and `jurisdictions: [{', '.join(a['jurisdictions'])}]`.
3. Copy `csef-check.yml` to `.github/workflows/`.
4. Paste `agent-instructions.md` into the repository's `CLAUDE.md` or `AGENTS.md`.
5. Run locally: `python3 tooling/scan.py --repo /path/to/product --export html`.

## Change the policy

Run the questionnaire again with your answers. Everything is regenerated, the version goes up, and the
report lists what changed.

- In the browser: open https://csef.kendirstudios.pt/questionnaire/, choose **Load answers.json**, change
  what you need and generate the kit again.
- With the CSEF repository: `python3 tooling/policy.py --web --answers {pid}-policy/answers.json --out-dir {pid}-policy`

PDF: open the `.html` files in a browser and print to PDF, or use the Word files.

The scanner, the GitHub Action and the Claude skill are at https://github.com/eduardon83/child-safe-edtech-framework.

Not legal advice and not a certification. The Child-Safe EdTech Framework (CSEF) is a framework, not a standard.
"""


def skill_zip(dest: Path) -> Path | None:
    sk = ROOT / "skill" / "csef-review"
    if not sk.exists():
        return None
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(sk.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                zf.write(f, Path("csef-review") / f.relative_to(sk))
    return dest


# --------------------------------------------------------------------------- generate

def generate(q: Q, raw: dict, out: Path, formats=("md", "html", "pdf", "docx"), previous: dict | None = None,
             with_skill: bool = True, today: str | None = None) -> dict:
    a, errs = normalise(q, raw)
    if errs:
        return {"ok": False, "errors": errs}
    today = today or dt.date.today().isoformat()
    prev_answers = (previous or {}).get("answers")
    prev_version = (previous or {}).get("pack_version")
    changes = diff_answers(q, normalise(q, prev_answers)[0], a) if prev_answers else []
    if prev_version:
        version = bump(prev_version) if changes else prev_version
    else:
        version = "1.0.0"
    res = assess(q, a)
    pack, comments = build_pack(q, a, res, version, today)
    out.mkdir(parents=True, exist_ok=True)
    pid = a["pack_id"]
    pack_path = out / f"{pid}.yaml"
    pack_path.write_text(pack_yaml(pack, comments, a), encoding="utf-8")
    perr = validate_pack(pack_path)
    if perr:
        return {"ok": False, "errors": [f"generated pack failed validation: {e}" for e in perr]}
    history = list((previous or {}).get("history", []))
    if not prev_version or changes:
        history.append({"version": version, "date": today, "changes": changes or ["First version"]})
    (out / "answers.json").write_text(json.dumps({
        "questionnaire_version": q.doc.get("version", 1), "framework_version": q.std.version,
        "tool": f"{TOOL} {scan.TOOL_VERSION}", "pack_version": version, "date": today,
        "answers": a, "history": history}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written = [pack_path, out / "answers.json"]
    written += write_doc(boundaries_report(q, a, res, pack, changes, prev_version), out, "boundaries-report",
                         f"{a['org_name']}: boundaries report", formats)
    written += write_doc(staff_policy(q, a, res, pack), out, "staff-policy",
                         f"{a['org_name']}: child-safety policy", formats)
    (out / "agent-instructions.md").write_text(agent_md(q, a, res, pack), encoding="utf-8")
    (out / "csef-check.yml").write_text(workflow_yml(a), encoding="utf-8")
    written += [out / "agent-instructions.md", out / "csef-check.yml"]
    if with_skill:
        z = skill_zip(out / "csef-review.zip")
        if z:
            written.append(z)
    names = [p.name for p in written] + ["README.md"]
    (out / "README.md").write_text(kit_readme(a, pack, names), encoding="utf-8")
    written.append(out / "README.md")
    return {"ok": True, "version": version, "changes": changes, "counts": res["counts"],
            "warnings": res["warnings"], "files": [p.name for p in written], "out_dir": str(out), "pack_id": pid}


WEB_BUNDLE_FILES = ["tooling/policy.py", "tooling/scan.py", "tooling/comms.py", "tooling/brand.py",
                    "framework/rules.yaml", "framework/sources.yaml", "framework/questionnaire.yaml",
                    "brand/svg/csef-lockup-on-light.svg", "brand/svg/csef-mark-on-light.svg", "brand/web/favicon.svg"]
WEB_BUNDLE_BINARY = ["brand/png/csef-lockup-on-light.png"]


def web_bundle(root: Path = ROOT) -> str:
    """Everything the in-browser questionnaire needs to run generate() in Pyodide, as one JSON file."""
    import base64
    files = {f: (root / f).read_text(encoding="utf-8") for f in WEB_BUNDLE_FILES}
    for pf in sorted((root / "packs").glob("*.yaml")):
        files[f"packs/{pf.name}"] = pf.read_text(encoding="utf-8")
    for pf in sorted((root / "framework" / "i18n").glob("*.yaml")):
        files[f"framework/i18n/{pf.name}"] = pf.read_text(encoding="utf-8")
    binary = {f: base64.b64encode((root / f).read_bytes()).decode() for f in WEB_BUNDLE_BINARY if (root / f).exists()}
    version = scan.load_yaml(root / "framework" / "rules.yaml").get("version", "?")
    return json.dumps({"version": str(version), "files": files, "binary": binary}, ensure_ascii=False) + "\n"


def zip_kit(out: Path, dest: Path, folder: str) -> Path:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(out.iterdir()):
            if f.is_file():
                zf.write(f, f"{folder}/{f.name}")
    return dest


def load_previous(path: Path | None) -> dict | None:
    if path and path.exists():
        doc = json.loads(path.read_text(encoding="utf-8"))
        if "answers" not in doc:  # a bare answers dict
            doc = {"answers": doc}
        return doc
    return None


# --------------------------------------------------------------------------- terminal

def ask_terminal(q: Q, prev: dict) -> dict:  # pragma: no cover (interactive)
    a = dict(prev)

    def prompt(text):
        try:
            return input(text)
        except EOFError:
            return ""

    print("\nCSEF policy questionnaire. Press Enter to keep the value in [brackets].\n")
    for s in q.doc["sections"]:
        print(f"\n== {s['title']} ==")
        if s.get("intro"):
            print(s["intro"].strip())
        qs = [q.questions[x["id"]] for x in s.get("questions", []) or []]
        for g in s.get("groups", []) or []:
            qs += [dict(q.questions[x["id"]], _group=g["title"]) for x in g["questions"]]
        last_group = None
        for qq in qs:
            if not q.visible(qq, a):
                continue
            if qq.get("_group") and qq["_group"] != last_group:
                last_group = qq["_group"]
                print(f"\n-- {last_group} --")
            cur = a.get(qq["id"], q.default(qq))
            opts = q.options(qq)
            t = qq["type"]
            extra = f"  [{TIER_LABEL[qq['tier']]}]" if t == "boundary" else ""
            print(f"\n{qq['label']}{extra}")
            if qq.get("help"):
                print(f"  {qq['help']}")
            if t in ("single", "boundary", "multi"):
                for n, o in enumerate(opts, 1):
                    mark = "*" if (o["value"] in cur if t == "multi" else o["value"] == cur) else " "
                    print(f"  {n}.{mark} {o['label']}")
                while True:
                    shown = ",".join(str(n) for n, o in enumerate(opts, 1) if (o["value"] in cur if t == "multi"
                                                                                else o["value"] == cur))
                    r = prompt(f"  {'Numbers, comma separated' if t == 'multi' else 'Number'} [{shown}]: ").strip()
                    if not r:
                        break
                    try:
                        picks = [opts[int(x) - 1]["value"] for x in r.replace(" ", "").split(",") if x]
                    except (ValueError, IndexError):
                        print("  Please type the number(s) shown.")
                        continue
                    cur = picks if t == "multi" else picks[0]
                    break
            elif t == "list":
                if cur:
                    print("  Current: " + "; ".join(cur))
                r = prompt("  One per line, empty line to finish, '-' to clear. ")
                if r.strip() == "-":
                    cur = []
                elif r.strip():
                    lines = [r.strip()]
                    while True:
                        more = prompt("  ").strip()
                        if not more:
                            break
                        lines.append(more)
                    cur = lines
            else:
                r = prompt(f"  [{cur}]: ").strip()
                if r:
                    cur = r
            a[qq["id"]] = cur
    return a


# --------------------------------------------------------------------------- web

FORM_CSS = brand.tokens_css() + brand.BASE_CSS + """
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:16px}
body{margin:0;background:var(--c-paper);color:var(--c-ink);font:16px/1.55 var(--font)}
a{color:var(--c-teal-t)}
.top{max-width:1120px;margin:0 auto;padding:18px 16px 0;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.top .csef-brand{margin:0}.top nav a{font-weight:500;text-decoration:none;color:var(--c-ink2);margin-left:16px;font-size:.95rem}
.top nav a:hover{color:var(--c-ink)}
.hero{max-width:1120px;margin:0 auto;padding:36px 16px 8px}
.hero h1{font-size:clamp(2rem,4.5vw,3rem);line-height:1.08;margin:0 0 12px;max-width:16ch}
.hero .lead{font-size:1.12rem;color:var(--c-ink2);max-width:62ch;margin:0 0 22px}
.gets{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 10px}
@media (max-width:860px){.gets{grid-template-columns:repeat(2,minmax(0,1fr))}}
.get{background:var(--c-panel);border:1px solid var(--c-line);border-radius:14px;padding:14px 14px 12px;border-top:5px solid var(--r)}
.get strong{display:block;font-family:var(--font-display);font-size:1.02rem;margin-bottom:2px}.get span{font-size:.9rem;color:var(--c-ink2)}
.privacy{display:inline-flex;gap:8px;align-items:center;font-size:.92rem;color:var(--c-ink2);margin:12px 0 0}
.privacy::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--c-teal);flex:none}
.wrap{max-width:1120px;margin:0 auto;padding:24px 16px 80px;display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:28px}
@media (max-width:900px){.wrap{grid-template-columns:minmax(0,1fr)}aside{position:static!important}.steps-panel{display:none}}
section{background:var(--c-panel);border:1px solid var(--c-line);border-radius:18px;padding:22px 22px 10px;margin:0 0 20px;min-width:0}
section h2{margin:0 0 4px;font-size:1.4rem;display:flex;align-items:center;gap:12px}
.num{display:inline-grid;place-items:center;width:32px;height:32px;border-radius:9px;background:var(--r,var(--c-teal));color:var(--nt,#fff);
font-size:1rem;flex:none}
section>.intro{color:var(--c-ink2);margin:6px 0 12px;max-width:68ch}
h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.07em;color:var(--c-ink2);margin:22px 0 4px;font-family:var(--font)}
.q{padding:14px 0;border-top:1px solid var(--c-line)}h3+.q{border-top:0}
.q>label,.q>.lab{display:block;font-weight:600;margin-bottom:8px}.help{font-size:.88rem;color:var(--c-ink2);margin:-4px 0 8px}
input[type=text],textarea{width:100%;font:inherit;padding:10px 12px;border:1px solid var(--c-line);border-radius:10px;background:var(--c-paper);color:var(--c-ink)}
input[type=text]:focus,textarea:focus{outline:2px solid var(--c-teal);outline-offset:1px;border-color:transparent}
textarea{min-height:80px}.opts{display:flex;flex-wrap:wrap;gap:8px}
.opt{display:flex;gap:9px;align-items:flex-start;border:1.5px solid var(--c-line);border-radius:11px;padding:8px 12px;cursor:pointer;background:var(--c-paper);min-width:0}
.opt input{margin-top:4px;accent-color:var(--c-teal)}.opt:has(input:checked){border-color:var(--c-teal);background:var(--c-teal-bg)}
.opt:has(input:focus-visible){outline:2px solid var(--c-teal);outline-offset:2px}
.col .opts{flex-direction:column}
.b .opt:has(input[value=never]:checked){background:var(--c-coral-bg);border-color:var(--c-coral)}
.b .opt:has(input[value=never]) input{accent-color:var(--c-coral)}
.b .opt:has(input[value=approval]:checked){background:var(--c-sun-bg);border-color:var(--c-sun)}
.b .opt:has(input[value=approval]) input{accent-color:#B07A0A}
.tier{display:inline-block;font-size:.72rem;font-weight:600;padding:2px 9px;border-radius:999px;margin-left:8px;vertical-align:2px;letter-spacing:.02em}
.tier1{background:var(--c-teal-bg);color:var(--c-teal-t)}.tier2{background:var(--c-indigo-bg);color:var(--c-indigo-t)}.tier3{background:var(--c-lilac-bg);color:var(--c-lilac-t)}
.hint{font-size:.86rem;margin-top:7px;color:var(--c-ink2)}.hint.warn{color:var(--c-sun-t)}
.hidden{display:none}aside{position:sticky;top:16px;align-self:start}
.panel{background:var(--c-panel);border:1px solid var(--c-line);border-radius:18px;padding:18px;margin-bottom:14px}
.panel h2{font-size:1.05rem;margin:0 0 10px}
.steps{list-style:none;margin:0;padding:0;counter-reset:s}.steps li{margin:2px 0}
.steps a{display:flex;gap:10px;align-items:center;text-decoration:none;color:var(--c-ink);padding:5px 6px;border-radius:8px;font-size:.95rem}
.steps a:hover{background:var(--c-code)}.steps i{width:10px;height:10px;border-radius:3px;background:var(--r);flex:none}
.stat{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px dashed var(--c-line)}
.stat:last-of-type{border-bottom:0}.stat b{font-variant-numeric:tabular-nums;font-family:var(--font-display);font-size:1.1rem}
.stat span{display:flex;align-items:center;gap:8px}.stat span::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--d)}
button,.btn{font:inherit;font-weight:600;border:0;border-radius:12px;padding:12px 14px;cursor:pointer;width:100%;margin-top:10px;
background:var(--c-ink);color:var(--c-paper);text-decoration:none;display:block;text-align:center}
button:hover{filter:brightness(1.12)}
button.sec,.btn.sec{background:transparent;color:var(--c-ink);border:1.5px solid var(--c-line)}
#result{margin-top:12px;font-size:.92rem}#result .btn{margin-top:8px}#result .small{font-size:.84rem;color:var(--c-ink2)}
.busy{display:flex;gap:10px;align-items:center}.busy::before{content:"";width:14px;height:14px;border-radius:50%;border:2px solid var(--c-line);border-top-color:var(--c-teal);animation:spin .8s linear infinite;flex:none}
@keyframes spin{to{transform:rotate(360deg)}}@media (prefers-reduced-motion:reduce){.busy::before{animation:none}}
button:disabled{opacity:.6;cursor:wait}#result ul{padding-left:18px;margin:6px 0}#result .err{color:var(--c-coral-t)}
.legend{font-size:.84rem;color:var(--c-ink2)}.legend>span{display:block;margin:6px 0}.legend .tier{margin:0 6px 0 0}
.foot{color:var(--c-ink2);font-size:.85rem;margin-top:24px}
.langs{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 18px;font-size:.92rem;color:var(--c-ink2)}
.seg{display:inline-flex;background:var(--c-panel);border:1px solid var(--c-line);border-radius:20px;padding:3px;gap:2px;flex-wrap:wrap}
.seg button{width:auto;margin:0;padding:6px 14px;border-radius:999px;background:transparent;color:var(--c-ink);font-weight:500;font-size:.92rem}
.seg button[aria-pressed=true]{background:var(--c-ink);color:var(--c-paper);font-weight:600}
.opt .ol{display:block}.desc{display:block;font-size:.84rem;color:var(--c-ink2);margin-top:3px;line-height:1.45}
.col .opt{width:100%}.opt.excl{border-style:dashed}
.gintro{font-size:.9rem;color:var(--c-ink2);background:var(--c-code);border-radius:10px;padding:10px 12px;margin:4px 0 6px}
.outnote{font-size:.9rem;color:var(--c-ink2);margin:6px 0 0}
"""

FORM_JS = r"""
const S = JSON.parse(document.getElementById('schema').textContent);
const PREV = JSON.parse(document.getElementById('prev').textContent);
const SERVED = document.body.dataset.served === '1';
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LANGS = S.languages;
let LANG = 'en';
try {
  const alias = x => ({no: 'nb', nn: 'nb'})[x] || x;
  const pick = [new URLSearchParams(location.search).get('lang'), localStorage.getItem('csef-lang'), (navigator.language || '').slice(0, 2)].map(x => x && alias(x));
  LANG = pick.find(x => x && LANGS.some(l => l.code === x)) || 'en';
} catch (e) {}
const TR = () => S.i18n[LANG] || {};
function T(k, vars){ let s = (TR().ui || {})[k]; if (s == null) s = S.ui[k]; if (s == null) s = k;
  for (const [a, b] of Object.entries(vars || {})) s = s.split('{' + a + '}').join(b); return s; }
function QT(q, f){ const x = ((TR().questions || {})[q.id] || {})[f]; return (x != null && x !== '') ? x : q[f]; }
function OT(q, o, f){ if (q.type === 'boundary' && f === 'label') return T('ch_' + o.value);
  const x = ((((TR().questions || {})[q.id] || {}).options || {})[o.value] || {})[f]; return x || o[f]; }
function ST(s, f){ const x = ((TR().sections || {})[s.id] || {})[f]; return x != null ? x : s[f]; }
function GT(g, f){ const x = ((TR().groups || {})[g.id] || {})[f]; return x || g[f]; }
const TIER = k => T('tier' + k);
let A = Object.assign({}, PREV.answers || {});
let PREVDOC = PREV.answers ? PREV : null;
function val(q){ return (q.id in A) ? A[q.id] : (q.type === 'text' ? QT(q, 'default') : q.default); }
const ROLE = ['var(--c-teal)','var(--c-indigo)','var(--c-sky)','var(--c-lilac)','var(--c-coral)','var(--c-sun)'];
function chrome(){
  document.documentElement.lang = LANG;
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = T(el.dataset.i18n, {v: el.dataset.v || ''}); });
  const ver = PREVDOC && PREVDOC.pack_version;
  $('#lead').textContent = (ver ? T('lead_edit', {v: ver}) : T('lead_new')) + ' ' + T('lead_tail');
  const mt = (LANGS.find(l => l.code === LANG) || {}).mt;
  const note = [mt ? T('mt_note') : '', T('output_note')].filter(Boolean).join(' '); $('#outnote').textContent = note; $('#outnote').hidden = !note;
  $('#langs').innerHTML = LANGS.map(l => `<button type="button" lang="${l.code}" aria-pressed="${l.code === LANG}" data-code="${l.code}">${esc(l.name)}</button>`).join('');
  $('#steps').innerHTML = S.sections.map((s, i) => `<li><a href="#s-${s.id}"><i style="--r:${ROLE[i % ROLE.length]}"></i>${esc(ST(s, 'title'))}</a></li>`).join('');
}
function setLang(code){
  LANG = code;
  try { localStorage.setItem('csef-lang', code); const u = new URL(location.href); u.searchParams.set('lang', code); history.replaceState(null, '', u); } catch (e) {}
  chrome(); render();
}
document.addEventListener('click', e => { const b = e.target.closest('#langs button'); if (b) setLang(b.dataset.code); });
function render(){
  const f = $('#form'); f.innerHTML = '';
  S.sections.forEach((s, i) => {
    const sec = document.createElement('section'); sec.id = 's-' + s.id;
    const intro = ST(s, 'intro');
    sec.innerHTML = `<h2><span class="num" style="--r:${ROLE[i % ROLE.length]};${[2, 5].includes(i % ROLE.length) ? '--nt:#17233F' : ''}">${i + 1}</span>${esc(ST(s, 'title'))}</h2>` + (intro ? `<p class="intro">${esc(intro)}</p>` : '');
    s.questions.forEach(q => sec.appendChild(field(q)));
    s.groups.forEach(g => { const h = document.createElement('h3'); h.textContent = GT(g, 'title'); sec.appendChild(h);
      const gi = GT(g, 'intro'); if (gi) { const p = document.createElement('p'); p.className = 'gintro'; p.textContent = gi; sec.appendChild(p); }
      g.questions.forEach(q => sec.appendChild(field(q))); });
    f.appendChild(sec);
  });
  update();
}
function field(q){
  const hasDesc = (q.options || []).some(o => o.desc);
  const d = document.createElement('div'); d.className = 'q' + (q.type === 'boundary' ? ' b' : '') +
    (((q.options || []).some(o => OT(q, o, 'label').length > 40) || hasDesc) && q.type !== 'boundary' ? ' col' : ''); d.dataset.id = q.id;
  const v = val(q); const name = 'f-' + q.id; const help = QT(q, 'help');
  const helpH = help ? `<p class="help">${esc(help)}</p>` : '';
  let h = '';
  if (q.type === 'text') h = `<label for="${name}">${esc(QT(q, 'label'))}</label>` + helpH + `<input type="text" id="${name}" value="${esc(v || '')}">`;
  else if (q.type === 'list') h = `<label for="${name}">${esc(QT(q, 'label'))}</label>` + helpH + `<textarea id="${name}">${esc((v || []).join('\n'))}</textarea>`;
  else {
    const multi = q.type === 'multi';
    const tier = q.tier ? `<span class="tier tier${q.tier}" title="${esc(T('rules'))}: ${esc(q.rules.join(', '))}">${esc(TIER(q.tier))}</span>` : '';
    h = `<div class="lab" id="${name}-l">${esc(QT(q, 'label'))}${tier}</div>` + helpH +
      `<div class="opts" role="${multi ? 'group' : 'radiogroup'}" aria-labelledby="${name}-l">` +
      q.options.map(o => { const desc = OT(q, o, 'desc');
        return `<label class="opt${desc ? ' has-desc' : ''}${o.value === q.exclusive ? ' excl' : ''}"><input type="${multi ? 'checkbox' : 'radio'}" name="${name}" value="${esc(o.value)}"
        ${(multi ? (v || []).includes(o.value) : v === o.value) ? 'checked' : ''}><span><span class="ol">${esc(OT(q, o, 'label'))}</span>${desc ? `<small class="desc">${esc(desc)}</small>` : ''}</span></label>`; }).join('') + '</div>' +
      (q.type === 'boundary' ? '<div class="hint"></div>' : '');
  }
  d.innerHTML = h;
  d.addEventListener('input', () => { read(q, d); update(); });
  d.addEventListener('change', e => {
    if (q.exclusive && e.target.type === 'checkbox' && e.target.checked) {
      d.querySelectorAll('input[type=checkbox]').forEach(i => {
        if (e.target.value === q.exclusive ? i !== e.target : i.value === q.exclusive) i.checked = false; });
    }
    read(q, d); update(); });
  return d;
}
function read(q, d){
  if (q.type === 'text') A[q.id] = d.querySelector('input').value.trim();
  else if (q.type === 'list') A[q.id] = d.querySelector('textarea').value.split('\n').map(x => x.trim()).filter(Boolean);
  else if (q.type === 'multi') A[q.id] = [...d.querySelectorAll('input:checked')].map(i => i.value);
  else { const c = d.querySelector('input:checked'); A[q.id] = c ? c.value : ''; }
  if (q.id === 'org_name' && !PREV.answers?.pack_id) {
    const p = document.querySelector('[data-id=pack_id] input');
    if (p && !p.dataset.touched) { p.value = A.org_name.toLowerCase().replace(/[^a-z]/g, '').slice(0, 8); A.pack_id = p.value; }
  }
  if (q.id === 'pack_id') d.querySelector('input').dataset.touched = '1';
}
function all(){ const qs = []; S.sections.forEach(s => { qs.push(...s.questions); s.groups.forEach(g => qs.push(...g.questions)); }); return qs; }
function update(){
  const feats = val({id:'features', default:[]}) || [], profs = val({id:'profiles', default:[]}) || [];
  const level = parseInt(val({id:'minimum_level', default:'2'}) || '1', 10);
  const c = {red:0, amber:0, covered:0, gap:0, na:0};
  all().filter(q => q.type === 'boundary').forEach(q => {
    const el = document.querySelector(`[data-id="${q.id}"]`);
    const vis = (!q.features.length || q.features.some(f => feats.includes(f))) && (!q.profiles.length || q.profiles.some(p => profs.includes(p)));
    el.classList.toggle('hidden', !vis);
    if (!vis) { c.na++; return; }
    const ch = val(q); const req = q.tier <= level; const hint = el.querySelector('.hint'); hint.classList.remove('warn');
    if (ch === 'never') { c.red++; hint.textContent = q.tier === 1 ? T('hint_red_law') : (req ? T('hint_red_req') : T('hint_red_above')); }
    else if (ch === 'approval') { c.amber++; hint.textContent = req ? T('hint_amber_req') : T('hint_amber'); if (req) hint.classList.add('warn'); }
    else if (req) { c.covered++; hint.textContent = q.tier === 1 ? T('hint_cov_law') : T('hint_cov'); }
    else { c.gap++; hint.textContent = T('hint_gap', {n: q.tier}); }
  });
  for (const k in c) { const e = document.getElementById('c-' + k); if (e) e.textContent = c[k]; }
}
function payload(){ const out = {}; all().forEach(q => out[q.id] = val(q)); return out; }
function download(name, text, type){ const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], {type}));
  a.download = name; document.body.appendChild(a); a.click(); a.remove(); }
$('#dl').addEventListener('click', () => download('answers.json', JSON.stringify(Object.assign({}, PREVDOC || {}, {answers: payload()}), null, 2), 'application/json'));
$('#load').addEventListener('change', e => { const f = e.target.files[0]; if (!f) return; f.text().then(t => {
  try { const d = JSON.parse(t); A = Object.assign({}, d.answers || d); PREVDOC = d.answers ? d : {answers: d}; chrome(); render();
    $('#result').innerHTML = '<p>' + esc(T('loaded') + (PREVDOC.pack_version ? T('loaded_v', {v: PREVDOC.pack_version}) : '') + T('loaded_tail')) + '</p>'; }
  catch (x) { $('#result').innerHTML = `<p class="err">${esc(T('bad_file'))}</p>`; } }); });
const PYODIDE = document.body.dataset.pyodide || '';
let PY = null;
async function engine(status){
  if (PY) return PY;
  status(T('st_engine'));
  const { loadPyodide } = await import(PYODIDE + 'pyodide.mjs');
  const py = await loadPyodide({ indexURL: PYODIDE });
  await py.loadPackage(['pyyaml', 'lxml', 'typing-extensions', 'micropip']);
  status(T('st_rules'));
  const b = await (await fetch('csef-bundle.json', {cache: 'no-cache'})).json();
  for (const [path, text] of Object.entries(b.files)) { const full = '/csef/' + path;
    py.FS.mkdirTree(full.slice(0, full.lastIndexOf('/'))); py.FS.writeFile(full, text); }
  for (const [path, b64] of Object.entries(b.binary || {})) { const full = '/csef/' + path;
    py.FS.mkdirTree(full.slice(0, full.lastIndexOf('/'))); py.FS.writeFile(full, Uint8Array.from(atob(b64), c => c.charCodeAt(0))); }
  py.globals.set('DOCX_WHEEL', new URL('vendor/python_docx-1.1.2-py3-none-any.whl', location.href).href);
  try { await py.runPythonAsync('import micropip\nawait micropip.install(DOCX_WHEEL, deps=False)'); }
  catch (x) { console.warn('Word export unavailable', x); }
  await py.runPythonAsync('import sys\nsys.path.insert(0, "/csef/tooling")\nimport policy\nQ = policy.Q()');
  PY = py; return py;
}
const GEN_PY = `
import json, shutil, importlib.util
from pathlib import Path
raw = json.loads(RAW); prev = json.loads(PREVJSON) if PREVJSON else None
out = Path("/out"); shutil.rmtree(out, ignore_errors=True)
fmts = ("md", "html", "docx") if importlib.util.find_spec("docx") else ("md", "html")
res = policy.generate(Q, raw, out, formats=fmts, previous=prev, with_skill=False)
if res["ok"]:
    policy.zip_kit(out, Path("/kit.zip"), res["pack_id"] + "-policy")
json.dumps(res)
`;
function blobUrl(bytes, type){ return URL.createObjectURL(new Blob([bytes], {type})); }
async function browserGenerate(r){
  const status = m => { r.innerHTML = `<p class="busy">${esc(m)}</p>`; };
  try {
    const py = await engine(status);
    status(T('st_gen'));
    py.globals.set('RAW', JSON.stringify(payload()));
    py.globals.set('PREVJSON', PREVDOC ? JSON.stringify(PREVDOC) : '');
    const d = JSON.parse(await py.runPythonAsync(GEN_PY));
    if (!d.ok) { r.innerHTML = `<p class="err">${esc(T('fix'))}</p><ul>` + d.errors.map(x => `<li class="err">${esc(x)}</li>`).join('') + '</ul>'; return; }
    PREVDOC = JSON.parse(new TextDecoder().decode(py.FS.readFile('/out/answers.json')));
    setTimeout(() => r.scrollIntoView({block: 'nearest', behavior: 'smooth'}), 50);
    const zipUrl = blobUrl(py.FS.readFile('/kit.zip'), 'application/zip');
    const open = f => blobUrl(py.FS.readFile('/out/' + f), 'text/html');
    const name = d.pack_id + '-policy-kit.zip';
    r.innerHTML = `<p><strong>${esc(T('ready', {v: d.version}))}</strong></p>` +
      `<a class="btn" href="${zipUrl}" download="${esc(name)}">${esc(T('dl_kit'))}</a>` +
      `<a class="btn sec" href="${open('staff-policy.html')}" target="_blank" rel="noopener">${esc(T('open_policy'))}</a>` +
      `<a class="btn sec" href="${open('boundaries-report.html')}" target="_blank" rel="noopener">${esc(T('open_report'))}</a>` +
      `<p class="small">${esc(T('pdf_tip'))}</p>` +
      (d.changes.length ? `<p>${esc(T('changes'))}</p><ul>` + d.changes.map(x => `<li>${esc(x)}</li>`).join('') + '</ul>' : '') +
      (d.warnings.length ? `<p>${esc(T('check_first'))}</p><ul>` + d.warnings.map(x => `<li>${esc(x.replace(/\*\*/g, ''))}</li>`).join('') + '</ul>' : '');
  } catch (x) {
    console.error(x);
    r.innerHTML = `<p class="err">${esc(T('gen_fail'))}</p>`;
  }
}
$('#go').addEventListener('click', async () => {
  const r = $('#result');
  if (!SERVED) { $('#go').disabled = true; try { await browserGenerate(r); } finally { $('#go').disabled = false; } return; }
  r.textContent = T('st_gen');
  try {
    const res = await fetch('/api/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload())});
    const d = await res.json();
    if (!d.ok) { r.innerHTML = `<p class="err">${esc(T('fix'))}</p><ul>` + d.errors.map(x => `<li class="err">${esc(x)}</li>`).join('') + '</ul>'; return; }
    r.innerHTML = `<p><strong>${esc(T('ready', {v: d.version}))}</strong> ${esc(T('served_written'))} <code>${esc(d.out_dir)}</code>.</p>` +
      (d.changes.length ? `<p>${esc(T('served_changes'))}</p><ul>` + d.changes.map(x => `<li>${esc(x)}</li>`).join('') + '</ul>' : '') +
      '<ul>' + d.files.map(f => `<li><a href="/files/${encodeURIComponent(f)}" target="_blank" rel="noopener">${esc(f)}</a></li>`).join('') + '</ul>';
  } catch (x) { r.innerHTML = `<p class="err">${esc(T('served_unreach'))}</p>`; }
});
chrome(); render();
"""


def render_form(q: Q, previous: dict | None, served: bool, home: str | None = None) -> str:
    schema = json.dumps(q.schema(), ensure_ascii=False).replace("</", "<\\/")
    prev = json.dumps(previous or {}, ensure_ascii=False).replace("</", "<\\/")
    ui = UI_EN
    privacy = "privacy_local" if served else "privacy_web"

    def tx(key, tag="span", attrs=""):
        return f'<{tag} data-i18n="{key}"{attrs}>{html.escape(ui[key])}</{tag}>'

    gets = "".join(f'<div class="get" style="--r:var(--c-{c})"><strong data-i18n="get{i}_t">{html.escape(ui[f"get{i}_t"])}</strong>'
                   f'<span data-i18n="get{i}_d">{html.escape(ui[f"get{i}_d"])}</span></div>'
                   for i, c in enumerate(("teal", "indigo", "sky", "lilac"), 1))
    stats = "".join(f'<div class="stat" style="--d:var(--c-{d})">{tx("c_" + k)}<b id="c-{k}">0</b></div>'
                    for k, d in (("red", "coral"), ("amber", "sun"), ("covered", "teal"), ("gap", "ink2"), ("na", "line")))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>CSEF Policy Questionnaire</title>
<meta name="description" content="Set your organisation's child-safety boundaries and get a staff policy, a report matched with the law and a guardrails file.">
{brand.head()}<style>{FORM_CSS}</style></head><body data-served="{1 if served else 0}" data-pyodide="{PYODIDE_URL}">
<div class="csef-stripe"></div>
<header class="top"><a href="{home or REPO_URL}" aria-label="CSEF home">{brand.logo("lockup", 40)}</a>
<nav aria-label="CSEF"><a href="{home or REPO_URL}" data-i18n="about">{ui["about"]}</a></nav></header>
<div class="hero">
<div class="langs" role="group" aria-labelledby="lang-l"><span id="lang-l" data-i18n="lang_label">{ui["lang_label"]}</span><span class="seg" id="langs"></span></div>
{tx("hero_title", "h1")}
<p class="lead" id="lead">{html.escape(ui["lead_new"] + " " + ui["lead_tail"])}</p>
<div class="gets">{gets}</div>
<p class="privacy">{tx(privacy, "span")}</p>
<p class="outnote" id="outnote" hidden></p>
</div>
<div class="wrap"><main>
<div id="form"></div>
<p class="foot" data-i18n="foot" data-v="{html.escape(q.std.version)}">{html.escape(ui["foot"].replace("{v}", q.std.version))}</p>
</main><aside>
<div class="panel steps-panel">{tx("steps", "h2")}<ol class="steps" id="steps"></ol></div>
<div class="panel">{tx("so_far", "h2")}
{stats}
<button id="go" data-i18n="generate">{ui["generate"]}</button>
<button id="dl" class="sec" type="button" data-i18n="save">{ui["save"]}</button>
<label class="btn sec"><span data-i18n="load">{ui["load"]}</span>
<input id="load" type="file" accept=".json,application/json" hidden></label>
<div id="result" aria-live="polite"></div></div>
<div class="panel legend"><span><span class="tier tier1" data-i18n="tier1">{ui["tier1"]}</span>{tx("legend_law")}</span>
<span><span class="tier tier2" data-i18n="tier2">{ui["tier2"]}</span>{tx("legend_coming")}</span>
<span><span class="tier tier3" data-i18n="tier3">{ui["tier3"]}</span>{tx("legend_rec")}</span></div>
</aside></div>
<script type="application/json" id="schema">{schema}</script>
<script type="application/json" id="prev">{prev}</script>
<script>{FORM_JS}</script></body></html>"""


def serve(q: Q, out: Path, previous: dict | None, port: int, formats, with_skill: bool) -> None:  # pragma: no cover
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import mimetypes
    import webbrowser
    state = {"prev": previous}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body: bytes, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                return self.send(200, render_form(q, state["prev"], True).encode(), "text/html; charset=utf-8")
            if self.path.startswith("/files/"):
                from urllib.parse import unquote
                name = unquote(self.path[len("/files/"):])
                p = out / name
                if "/" in name or "\\" in name or not p.is_file():
                    return self.send(404, b"not found", "text/plain")
                return self.send(200, p.read_bytes(), mimetypes.guess_type(name)[0] or "application/octet-stream")
            self.send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/generate":
                return self.send(404, b"not found", "text/plain")
            n = int(self.headers.get("Content-Length", 0))
            try:
                raw = json.loads(self.rfile.read(n) or b"{}")
                res = generate(q, raw, out, formats, state["prev"], with_skill)
                if res["ok"]:
                    state["prev"] = load_previous(out / "answers.json")
            except Exception as ex:  # noqa: BLE001
                res = {"ok": False, "errors": [str(ex)]}
            self.send(200, json.dumps(res).encode(), "application/json")

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    url = f"http://127.0.0.1:{port}/"
    print(f"CSEF policy questionnaire running at {url}  (output: {out})\nPress Ctrl+C to stop.")
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


# --------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CSEF policy questionnaire: boundaries to guardrails")
    ap.add_argument("--answers", help="answers.json from an earlier run (default: OUT/answers.json if it exists)")
    ap.add_argument("--out-dir", default="csef-policy")
    ap.add_argument("--web", action="store_true", help="answer in a local web page")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--batch", action="store_true", help="no questions; generate from --answers")
    ap.add_argument("--formats", default="md,html,pdf,docx")
    ap.add_argument("--no-skill", action="store_true", help="do not add csef-review.zip to the kit")
    args = ap.parse_args(argv)
    out = Path(args.out_dir).resolve()
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    q = Q()
    src = Path(args.answers) if args.answers else out / "answers.json"
    previous = load_previous(src)
    # A new answers file given explicitly is the input; the history comes from the kit folder if present.
    kit_prev = load_previous(out / "answers.json") if args.answers else previous
    if args.web:
        serve(q, out, previous, args.port, formats, not args.no_skill)
        return 0
    raw = (previous or {}).get("answers", {}) if args.batch else ask_terminal(q, (previous or {}).get("answers", {}))
    if args.batch and not previous:
        print(f"{TOOL}: --batch needs --answers (no {src})", file=sys.stderr)
        return 2
    res = generate(q, raw, out, formats, kit_prev, not args.no_skill)
    if not res["ok"]:
        print("Please fix:", *res["errors"], sep="\n  - ")
        return 1
    c = res["counts"]
    print(f"\nPolicy v{res['version']} written to {out}")
    print(f"red lines {c['red']} (beyond the law {c['above_law']}) | approval {c['amber']} | covered {c['covered']} | "
          f"recommended, not adopted {c['gap']}")
    for w in res["warnings"]:
        print("warning:", re.sub(r"\*\*", "", w))
    for ch in res["changes"]:
        print("changed:", ch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
