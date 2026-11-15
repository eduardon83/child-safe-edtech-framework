#!/usr/bin/env python3
"""CSEF Literacy Compass.

Reads the documents and in-product text of an educational product (design documents, teacher guides,
evaluation reports, marketing copy, dialogue and translation files) and shows what the product teaches about
digital life: information and media, communication and rights, creation, safety and wellbeing, problem
solving, AI literacy, and how the product itself teaches by design.

For each target it gives an evidence level (0 Not found, 1 Stated, 2 Designed, 3 Tested, 4 Measured) with the
passages that support it, flags copy that teaches the opposite (hidden curriculum), checks literacy claims
against the evidence, and points the next three steps. It never adds up a score and never ranks products.

  python3 tooling/compass.py --input docs/ --input marketing/site.md --manifest csef.yaml \\
         [--claims AI,INF] [--features ai_generative,purchases] [--bands B3,B4] \\
         [--csef-findings csef-report/findings.json] [--pack file.yaml] \\
         [--out-dir csef-compass] [--formats md,html,json]

This is a first pass based on wording. Every result needs a person, or the csef-review skill, to confirm
meaning. A product can say the right words and do the wrong thing; the Compass looks for the words.

Licence: Apache-2.0
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as htmllib
import json
import math
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan  # noqa: E402
import coc  # noqa: E402

TOOL = "csef-compass"
VERSION = "0.1.0"
LEVELS = {0: "Not found", 1: "Stated", 2: "Designed", 3: "Tested", 4: "Measured"}
ITALIC = ' font-style="italic"'
LEVEL_COLOR = {0: "var(--c-line)", 1: "var(--c-sun)", 2: "var(--c-sky)", 3: "var(--c-indigo)", 4: "var(--c-teal)"}
LEVEL_TEXT = {0: "var(--c-ink2)", 1: "var(--c-sun-t)", 2: "var(--c-sky-t)", 3: "var(--c-indigo-t)", 4: "var(--c-teal-t)"}
DOC_EXT = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf", ".docx"}
CONTENT_EXT = {".json", ".yaml", ".yml", ".po", ".csv", ".xliff", ".xlf", ".strings", ".properties", ".arb"}
SKIP_NAMES = {"package.json", "package-lock.json", "tsconfig.json", "csef.yaml", "csef.yml", "compass.json", "findings.json",
              "composer.json", "manifest.json", "yarn.lock", "pnpm-lock.yaml"}
MAX_BYTES = 8_000_000


# --------------------------------------------------------------------------- loading
def load_compass(root: Path, pack_paths: list[Path], std: scan.Standard) -> dict:
    base = root / "framework" / "compass"
    doc = scan.load_yaml(base / "targets.yaml")
    cw = scan.load_yaml(base / "crosswalk.yaml")
    targets = {t["id"]: dict(t, origin="CSEF", notes=[]) for t in doc["targets"]}
    for pp in pack_paths:
        pdoc = scan.load_yaml(pp)
        pid = (pdoc.get("pack") or {}).get("id", pp.stem)
        ext = pdoc.get("compass") or {}
        for t in ext.get("targets", []) or []:
            if t["id"] in targets:
                raise ValueError(f"Pack {pid}: compass target {t['id']} already exists")
            targets[t["id"]] = dict(t, origin=f"pack:{pid}", notes=[])
        for a in ext.get("amend", []) or []:
            tid = a["target"]
            if tid not in targets:
                raise ValueError(f"Pack {pid}: compass amend targets unknown target {tid}")
            t = targets[tid]
            t["sources"] = list(t.get("sources", [])) + [s for s in a.get("add_sources", []) or [] if s not in t.get("sources", [])]
            if a.get("add_refs"):
                refs = dict(t.get("refs") or {})
                for k, v in a["add_refs"].items():
                    refs[k] = list(refs.get(k, [])) + list(v)
                t["refs"] = refs
            if a.get("add_terms"):
                t["terms"] = [list(g) + list(extra) for g, extra in zip(t["terms"], a["add_terms"])] + \
                             [list(g) for g in a["add_terms"][len(t["terms"]):]]
            if a.get("add_conflict"):
                t["conflict"] = list(t.get("conflict") or []) + list(a["add_conflict"])
            if a.get("note"):
                t["notes"] = list(t["notes"]) + [f"[{pid.upper()}] {a['note']}"]
    for t in targets.values():
        for sid in t.get("sources", []):
            if sid not in std.sources:
                raise ValueError(f"Compass target {t['id']}: unknown source {sid}")
    return {"version": doc.get("version", "?"), "axes": doc["axes"], "levels": doc["evidence_levels"],
            "signals": doc["signals"], "claims": doc["claims"], "targets": targets, "crosswalk": cw}


# --------------------------------------------------------------------------- reading
def collect_inputs(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if not f.is_file() or any(part in scan.SKIP_DIRS or part.startswith(".") for part in f.relative_to(p).parts[:-1]):
                    continue
                if f.name in SKIP_NAMES or f.name.startswith("."):
                    continue
                if f.suffix.lower() in DOC_EXT | CONTENT_EXT and f.stat().st_size <= MAX_BYTES:
                    out.append(f)
        else:
            print(f"csef compass: input {raw} not found", file=sys.stderr)
    return list(dict.fromkeys(out))


def _json_strings(node, out):
    if isinstance(node, str):
        if len(node.split()) >= 2:
            out.append(node)
    elif isinstance(node, dict):
        for v in node.values():
            _json_strings(v, out)
    elif isinstance(node, list):
        for v in node:
            _json_strings(v, out)


def read_any(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in DOC_EXT:
        return coc.read_input(path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    if suf in (".json", ".arb"):
        try:
            strings: list[str] = []
            _json_strings(json.loads(text), strings)
            return "\n\n".join(strings)
        except json.JSONDecodeError:
            return text
    if suf in (".yaml", ".yml"):
        try:
            strings = []
            _json_strings(yaml.safe_load(text), strings)
            return "\n\n".join(strings)
        except yaml.YAMLError:
            return text
    if suf == ".po":
        return "\n\n".join(m.group(1) for m in re.finditer(r'msgstr\s+"(.*)"', text) if m.group(1).strip())
    return text


CITATION_RX = re.compile(r"\b(?:ailit[^a-z0-9]{0,3}(?:engage|create|manage|shape)(?: with)?(?: ai)? ?\d|(?:engage|create|manage|shape) with ai ?\d|"
                         r"digcomp(?: ?3(?: ?0)?)?[^a-z0-9]{0,3}\d\.\d)")
HEADING_RX = re.compile(r"^(#{1,6}\s|article\s+\d+|section\s+\d+|chapter\s+\d+|\d+(\.\d+)*\.?\s+[A-Z])", re.I)


def split_passages(text: str, file: str) -> list[dict]:
    """Paragraphs and list items with their nearest heading and first line number."""
    out, heading, buf, start = [], "", [], 0

    def flush():
        if buf:
            t = " ".join(x.strip() for x in buf).strip()
            if len(t) > 12:
                n = coc.norm(t)
                out.append({"file": file, "line": start, "heading": heading, "text": t, "n": n, "nt": CITATION_RX.sub(" ", n),
                            "hn": coc.norm(heading)})
            buf.clear()

    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            flush()
            continue
        if (HEADING_RX.match(line) and len(line) < 100) or (len(line) < 80 and line.isupper() and len(line.split()) <= 10):
            flush()
            heading = line.lstrip("# ").strip()
            continue
        if re.match(r"^([-*•]|\(?[a-z0-9]{1,3}[.)])\s+", line, re.I) or line.startswith("|"):
            flush()
        if not buf:
            start = i
        buf.append(line)
    flush()
    return out


# --------------------------------------------------------------------------- matching
def any_rx(terms):
    return [coc.term_rx(t) for t in terms]


def hit(rxs, text):
    return any(r.search(text) for r in rxs)


REF_PATTERNS = {
    "DIGCOMP3": lambda r: rf"digcomp(?: ?3(?: ?0)?)?[^a-z0-9]{{0,3}}{re.escape(r)}(?!\d)" if re.match(r"^\d\.\d$", r) else None,
    "AILIT": lambda r: (rf"(?:ailit[^a-z]{{0,3}})?{r.split()[0].lower()}(?: with)?(?: ai)? ?{r.split()[1]}(?!\d)"
                        if re.match(r"^(Engage|Create|Manage|Shape) \d$", r) else None),
}


def unique_refs(targets: dict, axes: dict) -> dict:
    """Framework references that point to exactly one learner-lens target. Only those can match on their own:
    a document that cites "DigComp 1.2" could mean several targets, so that citation alone decides nothing."""
    seen: dict = {}
    for t in targets.values():
        if axes.get(t["axis"], {}).get("lens") != "learner":
            continue
        for fw, items in (t.get("refs") or {}).items():
            for it in items or []:
                seen.setdefault((fw, str(it)), []).append(t["id"])
    by_t: dict = {}
    for (fw, it), ids in seen.items():
        mk = REF_PATTERNS.get(fw)
        pat = mk(it) if mk and len(ids) == 1 else None
        if pat:
            by_t.setdefault(ids[0], []).append(re.compile(pat))
    return by_t


PLAN_RX = re.compile(r"\b(next step|next steps|we plan|we will|will be|planned|plan to|future work|in the future|roadmap|"
                     r"proximo passo|proximos passos|planeamos|vamos|sera|serao|no futuro)\b")


def evidence_level(window: str, sig) -> int:
    """Highest level signalled in the window. Sentences about plans (next step, we will) do not count as tested
    or measured: a planned study is not evidence."""
    done = " ".join(x for x in re.split(r"(?<=[.!?])\s+", window) if not PLAN_RX.search(x))
    if hit(sig["measured"], done) or any(r.search(done) for r in sig["measured_rx"]):
        return 4
    if hit(sig["tested"], done) or any(r.search(done) for r in sig["tested_rx"]):
        return 3
    if hit(sig["designed"], window):
        return 2
    return 1


def compile_signals(signals):
    return {
        "designed": any_rx(signals["designed"]),
        "tested": any_rx(signals["tested"]),
        "measured": any_rx(signals["measured"]),
        "tested_rx": [re.compile(x) for x in signals.get("tested_regex", [])],
        "measured_rx": [re.compile(x) for x in signals.get("measured_regex", [])],
    }


def assess_target(t, passages, sig, refs=()):
    groups = [any_rx(g) for g in t["terms"]]
    need = t.get("need") or min(2, len(groups))
    matches = []
    for i, p in enumerate(passages):
        n = p["n"]
        nh = p["nt"] + " " + p["hn"]  # framework citations removed, so "AILit Create 4" does not match "create"
        score = sum(1 for g in groups if hit(g, nh))
        by_ref = any(r.search(n) for r in refs)
        if score >= need or by_ref:
            nb = passages[i + 1] if i + 1 < len(passages) else None
            nxt = nb["n"] if nb and nb["file"] == p["file"] and nb["heading"] == p["heading"] else ""
            lvl = evidence_level(p["hn"] + ". " + n + " " + nxt, sig)
            matches.append((lvl, p, by_ref))
    matches.sort(key=lambda m: (-m[0], m[1]["file"], m[1]["line"]))
    level = matches[0][0] if matches else 0
    anchors = [{"file": p["file"], "line": p["line"], "heading": p["heading"], "level": lv, "by_ref": br,
                "excerpt": (p["text"][:240] + ("…" if len(p["text"]) > 240 else ""))} for lv, p, br in matches[:3]]
    return level, anchors, len(matches)


def find_conflicts(t, passages):
    out = []
    for phrase in t.get("conflict") or []:
        rx = coc.term_rx(phrase)
        for p in passages:
            for s in coc.sentences(p["n"]):
                if rx.search(s):
                    rest = rx.sub(" ", s)
                    if re.search(coc.NEGATION, rest) or re.search(r"\b(avoid|instead of|rather than|should not|evitar|em vez de|nao dizer|nunca dizer)\b", rest):
                        continue  # the phrase is quoted as something not to do
                    out.append({"target": t["id"], "phrase": phrase, "file": p["file"], "line": p["line"],
                                "excerpt": p["text"][:240]})
                    break
    return out


def find_claims(passages, claims_cfg):
    verbs = any_rx(claims_cfg["verbs"])
    proof = any_rx(claims_cfg["proof"])
    topics = {ax: any_rx(ts) for ax, ts in claims_cfg["topics"].items()}
    found = []
    for p in passages:
        for s in coc.sentences(p["n"]):
            if not hit(verbs, s) and not hit(proof, s):
                continue
            axes = [ax for ax, rxs in topics.items() if hit(rxs, s)]
            if axes:
                found.append({"axes": axes, "strong": hit(proof, s), "file": p["file"], "line": p["line"],
                              "excerpt": p["text"][:240]})
    return found


# --------------------------------------------------------------------------- scope
def resolve_scope(manifest, args, compass):
    m = manifest or {}
    mc = m.get("compass") or {}
    bands = set(args.bands.split(",")) if args.bands else set(m.get("age_bands") or [])
    feats = set(m.get("features") or [])
    if args.features:
        feats |= {f.strip() for f in args.features.split(",") if f.strip()}
    declared = set(mc.get("claims") or [])
    if args.claims:
        declared |= {c.strip() for c in args.claims.split(",") if c.strip()}
    na = {x["target"]: x.get("reason", "") for x in mc.get("not_applicable") or []}
    return {"bands": sorted(bands), "features": sorted(feats), "claims_declared": sorted(declared), "not_applicable": na,
            "product": args.product or m.get("product") or "Unnamed product"}


def band_ok(t, bands):
    tb = t.get("age_bands") or ["all"]
    return tb == ["all"] or not bands or bool(set(tb) & set(bands))


# --------------------------------------------------------------------------- compass
def run(inputs: list[Path], compass: dict, std, scope: dict, csef_findings: dict | None) -> dict:
    sig = compile_signals(compass["signals"])
    passages, files = [], []
    for f in inputs:
        try:
            text = read_any(f)
        except RuntimeError as ex:
            print(f"csef compass: skipped {f}: {ex}", file=sys.stderr)
            continue
        ps = split_passages(text, str(f))
        passages += ps
        files.append({"file": str(f), "passages": len(ps)})

    claims = find_claims(passages, compass["claims"])
    claimed_axes = {ax for c in claims for ax in c["axes"]}
    declared = set(scope["claims_declared"])
    axes_by_id = {a["id"]: a for a in compass["axes"]}
    feats = set(scope["features"])

    results, conflicts = [], []
    urefs = unique_refs(compass["targets"], axes_by_id)
    for tid, t in compass["targets"].items():
        level, anchors, nmatch = assess_target(t, passages, sig, urefs.get(tid, []))
        cf = find_conflicts(t, passages)
        conflicts += cf
        sc = t.get("scope", "claimed")
        why_scope = ""
        if tid in scope["not_applicable"]:
            status, why_scope = "not_applicable", scope["not_applicable"][tid] or "declared not applicable"
        elif not band_ok(t, scope["bands"]):
            status, why_scope = "out_of_scope", "not for the declared age bands"
        elif sc == "universal":
            status, why_scope = "in_scope", "applies to every product used by children"
        elif sc == "feature":
            hitf = sorted(set(t.get("features") or []) & feats)
            status, why_scope = ("in_scope", "feature: " + ", ".join(hitf)) if hitf else ("out_of_scope", "feature not declared")
        else:
            if tid in declared or t["axis"] in declared:
                status, why_scope = "in_scope", "claimed in the manifest"
            elif t["axis"] in claimed_axes:
                status, why_scope = "in_scope", "claimed in the documents"
            else:
                hitf = sorted(set(t.get("features") or []) & feats)
                if hitf:
                    status, why_scope = "opportunity", "natural fit for: " + ", ".join(hitf)
                else:
                    status, why_scope = "not_claimed", "not claimed"
        results.append({"id": tid, "axis": t["axis"], "title": t["title"], "scope": sc, "status": status, "why_scope": why_scope,
                        "level": level, "level_name": LEVELS[level], "matches": nmatch, "anchors": anchors,
                        "conflicts": cf, "target": t["target"], "why": t["why"], "look_for": t.get("look_for", ""),
                        "improvement": t["improvement"], "next": next_step(level, t), "ideas": t.get("ideas", []), "refs": t.get("refs") or {},
                        "sources": t.get("sources", []), "origin": t.get("origin", "CSEF"), "notes": t.get("notes", [])})

    # TRN-07 summarises every conflict found
    for r in results:
        if r["id"] == "TRN-07" and conflicts:
            r["conflicts"] = conflicts

    axes = []
    for a in compass["axes"]:
        rs = [r for r in results if r["axis"] == a["id"]]
        ins = [r for r in rs if r["status"] == "in_scope"]
        extra = [r for r in rs if r["status"] in ("not_claimed", "opportunity") and r["level"] >= 2]
        counts = {k: sum(1 for r in ins if r["level"] == k) for k in LEVELS}
        designed = sum(1 for r in ins if r["level"] >= 2)
        axes.append({"id": a["id"], "title": a["title"], "lens": a["lens"], "question": a["question"],
                     "in_scope": len(ins), "designed": designed, "reach": (designed / len(ins)) if ins else None,
                     "top": max((r["level"] for r in ins), default=None), "counts": counts,
                     "conflicts": sum(len(r["conflicts"]) for r in rs if r["id"] != "TRN-07"),
                     "claimed": a["id"] in declared or a["id"] in claimed_axes,
                     "also_found": [r["id"] for r in extra], "sources": a.get("sources", [])})

    claim_findings = []
    ax = {a["id"]: a for a in axes}
    for axis_id in sorted(claimed_axes | {d for d in declared if d in axes_by_id}):
        if axis_id == "ANY" or axis_id not in ax:
            continue
        a = ax[axis_id]
        cl = [c for c in claims if axis_id in c["axes"]]
        strong = any(c["strong"] for c in cl)
        if a["designed"] == 0:
            claim_findings.append({"axis": axis_id, "kind": "unsupported", "strong": strong, "claims": cl[:3],
                                   "message": f"{a['title']}: claimed, but no target on this axis reaches Designed."})
        elif strong and (a["top"] or 0) < 4:
            claim_findings.append({"axis": axis_id, "kind": "strong_without_measure", "strong": True, "claims": cl[:3],
                                   "message": f"{a['title']}: a strong claim (proven, evidence-based) without Measured evidence."})
    generic = [c for c in claims if "ANY" in c["axes"]]
    learner = [a for a in axes if a["lens"] == "learner"]
    if generic and sum(1 for a in learner if a["designed"]) < 2:
        claim_findings.append({"axis": "ANY", "kind": "generic", "strong": any(c["strong"] for c in generic), "claims": generic[:3],
                               "message": "Generic claim (digital literacy, digital skills) with fewer than two learner axes at Designed."})
    elif any(c["strong"] for c in generic) and not any((a["top"] or 0) >= 4 for a in learner):
        claim_findings.append({"axis": "ANY", "kind": "strong_without_measure", "strong": True, "claims": [c for c in generic if c["strong"]][:3],
                               "message": "Strong generic claim (proven, evidence-based) while no learner axis has Measured evidence."})

    recs = recommendations(results, axes, claim_findings, conflicts, compass)
    safety = None
    if csef_findings:
        from collections import Counter
        cnt = Counter(f["severity"] for f in csef_findings.get("findings", []))
        safety = {"level": csef_findings.get("level"), "block": cnt.get("BLOCK", 0), "review": cnt.get("REVIEW", 0),
                  "warn": cnt.get("WARN", 0), "human": len(csef_findings.get("human_checks", []))}

    used = sorted({s for r in results if r["status"] == "in_scope" for s in r["sources"]} |
                  {s for a in compass["axes"] for s in a.get("sources", [])} | {"EU-DEC", "SWE-KP", "ET4G2"})
    return {"format": 1, "tool": {"name": TOOL, "version": VERSION, "compass_version": compass["version"],
                                  "framework_version": std.version},
            "generated": dt.date.today().isoformat(), "product": scope["product"], "scope": scope,
            "inputs": files, "passages": len(passages), "axes": axes, "targets": results, "conflicts": conflicts,
            "claims": claims, "claim_findings": claim_findings, "recommendations": recs,
            "crosswalk": crosswalk(results, compass), "safety": safety,
            "sources": {s: {k: std.sources[s].get(k) for k in ("title", "type", "status", "url", "verified")} for s in used if s in std.sources}}


def next_step(level: int, t: dict) -> str:
    if level <= 1:
        return t["improvement"]
    if level == 2:
        return ("Try it with learners and teachers (a short pilot or playtest) and record what happened. Collect evidence under the "
                "CSEF rules on personal questions (CORE-DAT-13 to 18): closed answers, no family questions, teachers see totals only.")
    if level == 3:
        return ("Measure learning for this target (for example a pre/post task or a comparison group), ideally with an independent "
                "partner, with ethics and national approval recorded (B-DAT-01; in Portugal, EduQA approval through MIME).")
    return "Keep the evidence current and share it in your quality description."


def recommendations(results, axes, claim_findings, conflicts, compass):
    recs = []
    by_t = {r["id"]: r for r in results}
    for tid in dict.fromkeys(c["target"] for c in conflicts):
        r = by_t[tid]
        recs.append({"priority": 1, "kind": "Fix a hidden-curriculum conflict", "axis": r["axis"], "targets": [tid],
                     "title": f"Rewrite what contradicts {tid} {r['title']}",
                     "do": r["improvement"], "why": r["why"], "ideas": r["ideas"][:2], "sources": r["sources"]})
    for r in results:
        if r["id"] == "TRN-07" and conflicts:
            continue
        if r["status"] == "in_scope" and r["scope"] in ("universal", "feature") and r["level"] <= 1:
            recs.append({"priority": 2, "kind": "Close a baseline gap", "axis": r["axis"], "targets": [r["id"]],
                         "title": f"{r['id']} {r['title']}", "do": r["improvement"], "why": r["why"],
                         "ideas": r["ideas"][:2], "sources": r["sources"]})
    for c in claim_findings:
        ax = next((a for a in axes if a["id"] == c["axis"]), None)
        tids = [r["id"] for r in results if r["axis"] == c["axis"] and r["status"] == "in_scope"][:4]
        recs.append({"priority": 3, "kind": "Back up or soften a claim", "axis": c["axis"], "targets": tids,
                     "title": c["message"], "do": "Either show where the product does this (activities, tests, results) or reword the claim to what the evidence supports.",
                     "why": "Claims about learning must be accurate (UCPD Art. 6 and 7 on misleading claims; reliability in the EU guidelines).",
                     "ideas": [], "sources": ["UCPD", "EU-DEC"] + (ax["sources"] if ax else [])})
    for r in results:
        if r["status"] == "in_scope" and r["scope"] == "claimed" and r["level"] <= 1 and r["why_scope"] != "claimed in the documents":
            recs.append({"priority": 4, "kind": "Make a claimed target real", "axis": r["axis"], "targets": [r["id"]],
                         "title": f"{r['id']} {r['title']}", "do": r["improvement"], "why": r["why"],
                         "ideas": r["ideas"][:2], "sources": r["sources"]})
    for lvl, prio, kind, verb in ((2, 5, "Test what is designed", "Test with learners and teachers: "),
                                  (3, 6, "Measure what is tested", "Measure learning for: ")):
        for a in axes:
            ts = [r for r in results if r["axis"] == a["id"] and r["status"] == "in_scope" and r["level"] == lvl]
            if ts:
                recs.append({"priority": prio, "kind": kind, "axis": a["id"], "targets": [r["id"] for r in ts],
                             "title": f"{a['title']}: {len(ts)} target(s) at {LEVELS[lvl]}",
                             "do": verb + ", ".join(f"{r['id']} {r['title']}" for r in ts) + ".",
                             "why": "Evidence strength matters more than coverage (EdTech for Good evidence tiers; Dutch 3E).",
                             "ideas": ["Short classroom pilot with a debrief and a simple pre/post task"] if lvl == 2 else
                                      ["Partner with a research group or testbed for a comparison study"],
                             "sources": ["ET4G2", "NL-3E"]})
    recs.sort(key=lambda x: x["priority"])
    for i, r in enumerate(recs, 1):
        r["n"] = i
    return recs


def crosswalk(results, compass):
    cw = compass["crosswalk"]
    out = {}
    for fw, meta in cw["frameworks"].items():
        rows = []
        for key, label in meta["items"].items():
            ev, gaps = [], []
            for r in results:
                if r["status"] != "in_scope":
                    continue
                m = cw["targets"].get(r["id"]) or cw["axes"].get(r["axis"]) or {}
                if str(key) in [str(x) for x in m.get(fw, [])]:
                    (ev if r["level"] >= 2 else gaps).append(f"{r['id']} ({LEVELS[r['level']]})")
            rows.append({"key": str(key), "label": label, "evidence": ev, "gaps": gaps})
        out[fw] = {"title": meta["title"], "rows": rows}
    return out


# --------------------------------------------------------------------------- rendering: markdown
def e(s):
    return htmllib.escape(str(s))


def render_md(res: dict) -> str:
    sc = res["scope"]
    L = [f"# Literacy Compass: {res['product']}", "",
         f"CSEF Literacy Compass v{res['tool']['compass_version']} · {res['generated']} · {len(res['inputs'])} file(s), {res['passages']} passages · "
         f"age bands: {', '.join(sc['bands']) or 'not declared'} · features: {', '.join(sc['features']) or 'none declared'}", "",
         "> **A profile, not a score.** This first pass reads wording in the documents you gave it. It shows where the documents link the product to "
         "digital, media and AI literacy targets and how strong the evidence is. It does not rate, rank or certify the product, and it is not "
         "legal advice. Confirm every result by reading the passages cited.", ""]
    L += ["## Heading: the next three steps", ""]
    for r in res["recommendations"][:3]:
        L.append(f"{r['n']}. **{r['kind']}.** {r['title']}. {r['do']}")
    if not res["recommendations"]:
        L.append("No gaps found in scope. Consider claiming a new axis or measuring outcomes.")
    L += ["", "## Profile", "", "| Axis | Lens | In scope | At Designed or above | Highest level | Conflicts | Also found (not claimed) |",
          "|---|---|---|---|---|---|---|"]
    for a in res["axes"]:
        top = LEVELS[a["top"]] if a["top"] is not None else "-"
        of = f" of {a['in_scope']}" if a["in_scope"] else ""
        L.append(f"| {a['id']} {a['title']} | {a['lens']} | {a['in_scope'] or 'not claimed'} | {a['designed']}{of}"
                 f" | {top} | {a['conflicts'] or ''} | {', '.join(a['also_found'])} |")
    if res["safety"]:
        s = res["safety"]
        L += ["", f"Safety lens (CSEF scan at level {s['level']}): {s['block']} blocking, {s['review']} to review, {s['warn']} warnings, {s['human']} human checks."]
    else:
        L += ["", "Safety lens: run `tooling/scan.py` and pass `--csef-findings` to show the CSEF safety status next to the Compass."]
    if res["claim_findings"]:
        L += ["", "## Claims", ""]
        for c in res["claim_findings"]:
            L.append(f"- **{c['message']}**")
            for x in c["claims"][:2]:
                L.append(f"  - `{x['file']}:{x['line']}` \"{x['excerpt'][:160]}\"")
    if res["conflicts"]:
        L += ["", "## Hidden curriculum: possible conflicts", ""]
        for c in res["conflicts"]:
            L.append(f"- **{c['target']}** \"{c['phrase']}\" in `{c['file']}:{c['line']}`: \"{c['excerpt'][:160]}\"")
    L += ["", "## Targets in scope", ""]
    for r in [x for x in res["targets"] if x["status"] == "in_scope"]:
        L += [f"### {r['id']} {r['title']} · {r['level_name']}", "", f"*{r['why_scope']}*. {r['target']}", ""]
        for an in r["anchors"]:
            L.append(f"- {LEVELS[an['level']]}: `{an['file']}:{an['line']}`{(' (' + an['heading'] + ')') if an['heading'] else ''} \"{an['excerpt'][:200]}\"")
        L.append(f"- Next: {r['next']}" + (f" Ideas: {'; '.join(r['ideas'][:2])}." if r["ideas"] and r["level"] <= 1 else ""))
        refs = "; ".join(f"{k} {', '.join(map(str, v))}" for k, v in r["refs"].items() if v)
        L += [f"- Framework references: {refs or '-'}. Sources: {', '.join(r['sources'])}", ""]
    opp = [x for x in res["targets"] if x["status"] == "opportunity"]
    if opp:
        L += ["## Opportunities", "", "Not claimed, but a natural fit for the product's features.", ""]
        L += [f"- **{r['id']} {r['title']}** ({r['why_scope']}). {r['improvement']}" for r in opp]
        L.append("")
    L += ["## One dossier, many frameworks", "", "Evidence at Designed or above that also answers these frameworks (indicative mapping).", ""]
    for fw, d in res["crosswalk"].items():
        L += [f"### {d['title']}", "", "| Item | Evidence you can reuse | Gaps |", "|---|---|---|"]
        for row in d["rows"]:
            L.append(f"| {row['key']} {row['label']} | {', '.join(row['evidence']) or '-'} | {', '.join(row['gaps']) or '-'} |")
        L.append("")
    L += ["## Evidence ladder", "", "| Level | Meaning |", "|---|---|"]
    for k, v in LEVEL_MEANING.items():
        L.append(f"| {k} {LEVELS[k]} | {v} |")
    L += ["", "## Sources", ""]
    for sid, s in res["sources"].items():
        L.append(f"- **{sid}** {s['title']}. {s.get('status') or ''}. {s.get('url') or ''} (verified {s.get('verified')})")
    L += ["", "## Limits", "",
          "- Reads words, not behaviour. A product can describe a good activity and ship a poor one; play it with learners.",
          "- Matching is in English and European Portuguese. Use the csef-review skill for meaning in any language, or add terms in a pack.",
          "- Evidence levels come from the nearest passages. A pilot described in another section may be missed; the skill reads the whole document.",
          "- No learner data is needed or used. Do not feed personal data of pupils into this tool.", ""]
    return "\n".join(L)


LEVEL_MEANING = {
    0: "Nothing in the documents addresses the target.",
    1: "The documents name or claim the target, without saying how the product achieves it.",
    2: "Specific activities, mechanics, features or teacher materials are linked to the target.",
    3: "The design was tried with learners or teachers and results are recorded.",
    4: "Learning outcomes were measured (pre/post, comparison group, independent evaluation).",
}


# --------------------------------------------------------------------------- rendering: html
def compass_svg(res: dict) -> str:
    axes = res["axes"]
    n = len(axes)
    W, H, cx, cy, R = 680, 600, 340, 300, 185
    half = math.pi / n * 0.78
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="ct cd" style="width:100%;max-width:620px;height:auto">'
         '<title id="ct">Literacy Compass</title><desc id="cd">One petal per axis. Petal length is the share of targets in scope that reach '
         'Designed or above. Petal colour is the highest evidence level. Dashed outlines show axes in scope. The needle points to the first step.</desc>']
    for k in (0.25, 0.5, 0.75, 1):
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{R * k:.1f}" fill="none" stroke="var(--c-line)" stroke-dasharray="{"0" if k == 1 else "3 4"}"/>')

    def pt(r, ang):
        return cx + r * math.cos(ang), cy + r * math.sin(ang)

    def wedge(r, a0, a1):
        x0, y0 = pt(r, a0)
        x1, y1 = pt(r, a1)
        return f"M{cx},{cy} L{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 0 1 {x1:.1f},{y1:.1f} Z"

    for i, a in enumerate(axes):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        x, y = pt(R, ang)
        o.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="var(--c-line)"/>')
        if a["in_scope"]:
            o.append(f'<path d="{wedge(R, ang - half, ang + half)}" fill="none" stroke="var(--c-ink2)" stroke-dasharray="4 4" stroke-width="1.2"/>')
            r = max(a["reach"] or 0, 0.04) * R
            col = LEVEL_COLOR[a["top"] or 0]
            o.append(f'<path d="{wedge(r, ang - half, ang + half)}" fill="{col}" fill-opacity=".85" stroke="{col}"><title>{e(a["title"])}: '
                     f'{a["designed"]} of {a["in_scope"]} at Designed or above; highest {LEVELS[a["top"] or 0]}</title></path>')
        if a["conflicts"]:
            cxx, cyy = pt(R + 14, ang + half * 0.9)
            o.append(f'<circle cx="{cxx:.1f}" cy="{cyy:.1f}" r="7" fill="var(--c-coral)"><title>{a["conflicts"]} possible conflict(s)</title></circle>'
                     f'<text x="{cxx:.1f}" y="{cyy + 4:.1f}" text-anchor="middle" font-size="10" font-weight="700" fill="#fff">!</text>')
        lx, ly = pt(R + 46, ang)
        anchor = "middle" if abs(math.cos(ang)) < 0.3 else ("start" if math.cos(ang) > 0 else "end")
        col = "var(--c-ink)" if a["in_scope"] else "var(--c-ink2)"
        sub = f'{a["designed"]}/{a["in_scope"]} · {LEVELS[a["top"] or 0]}' if a["in_scope"] else ("found, not claimed" if a["also_found"] else "not claimed")
        o.append(f'<text x="{lx:.1f}" y="{ly - 4:.1f}" text-anchor="{anchor}" font-family="var(--font-display)" font-weight="700" font-size="18" fill="{col}">{e(a["id"])}</text>'
                 f'<text x="{lx:.1f}" y="{ly + 14:.1f}" text-anchor="{anchor}" font-size="13" fill="var(--c-ink2)"'
                 f'{ITALIC if not a["in_scope"] else ""}>{e(sub)}</text>')
    top = res["recommendations"][0] if res["recommendations"] else None
    if top:
        idx = next((i for i, a in enumerate(axes) if a["id"] == top["axis"]), 0)
        ang = -math.pi / 2 + idx * 2 * math.pi / n
        tip = pt(R * 0.92, ang)
        tail = pt(R * 0.30, ang + math.pi)
        l = pt(14, ang - math.pi / 2)
        rr = pt(14, ang + math.pi / 2)
        o.append(f'<g><title>Heading: {e(top["title"])}</title>'
                 f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {l[0]:.1f},{l[1]:.1f} {cx},{cy} {rr[0]:.1f},{rr[1]:.1f}" fill="var(--c-coral)" opacity=".95"/>'
                 f'<polygon points="{tail[0]:.1f},{tail[1]:.1f} {l[0]:.1f},{l[1]:.1f} {cx},{cy} {rr[0]:.1f},{rr[1]:.1f}" fill="var(--c-ink)" opacity=".85"/></g>')
    s = res["safety"]
    ring = "var(--c-ink2)" if not s else ("var(--BLOCK)" if s["block"] else ("var(--REVIEW)" if s["review"] else "var(--c-teal)"))
    label = "Safety: not run" if not s else (f'Safety: {s["block"]} blocking' if s["block"] else (f'Safety: {s["review"]} to review' if s["review"] else "Safety: no blocking"))
    o.append(f'<circle cx="{cx}" cy="{cy}" r="16" fill="var(--c-panel)" stroke="{ring}" stroke-width="5"><title>{e(label)}</title></circle>')
    o.append('</svg>')
    return "".join(o)


def render_html(res: dict) -> str:
    import export  # reuse dashboard styles and brand
    sc = res["scope"]
    o = []
    a = o.append
    css = export.CSS + """
.ev{display:inline-flex;align-items:center;gap:6px;font-size:.78rem;font-weight:700;border-radius:999px;padding:2px 9px;color:var(--t);border:1px solid var(--t)}
.ev i{width:9px;height:9px;border-radius:50%;background:var(--f);display:inline-block}
.lad{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:8px}.lad div{border-radius:10px;padding:8px 10px;border:1px solid var(--line);border-top:6px solid var(--f)}
@media(max-width:820px){.lad{grid-template-columns:1fr 1fr}}
.axes{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:10px}@media(max-width:900px){.axes{grid-template-columns:1fr 1fr}}
.axis{border:1px solid var(--line);border-radius:12px;padding:12px;background:var(--panel)}.axis.off{opacity:.6}
.seg{display:flex;height:9px;border-radius:99px;overflow:hidden;background:var(--code);margin:8px 0 4px}.seg i{display:block;height:100%}
.heading li{margin:8px 0}.kind{font-size:.75rem;font-weight:700;color:var(--c-coral-t);text-transform:uppercase;letter-spacing:.04em}
blockquote{margin:6px 0;padding:6px 10px;border-left:3px solid var(--line);background:var(--bg);border-radius:6px;font-size:.88rem}
"""
    a(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
      f'<title>Literacy Compass: {e(res["product"])}</title>{export.brand.head()}<style>{css}</style></head><body><div class="csef-stripe"></div>'
      f'<div class="wrap">{export.brand.logo("lockup", 40)}')
    a(f'<h1>Literacy Compass</h1><p class="sub"><strong>{e(res["product"])}</strong> · {res["generated"]} · {len(res["inputs"])} file(s), '
      f'{res["passages"]} passages · age bands {e(", ".join(sc["bands"]) or "not declared")} · features {e(", ".join(sc["features"]) or "none declared")} · '
      f'Compass v{e(res["tool"]["compass_version"])}</p>')
    a('<p class="disclaimer"><strong>A profile, not a score.</strong> This first pass reads wording in the documents provided and shows where they link '
      'the product to digital, media and AI literacy targets, and how strong the evidence is. It does not rate, rank or certify the product and is not '
      'legal advice. Confirm every result by reading the passages cited.</p>')
    a('<section class="panel"><div class="verdict"><div>' + compass_svg(res) + '<div class="legend">')
    for k in LEVELS:
        a(f'<span class="ev" style="--f:{LEVEL_COLOR[k]};--t:{LEVEL_TEXT[k]}"><i></i>{k} {LEVELS[k]}</span>')
    a('</div></div><div><h2>Heading</h2><p class="muted small">The next three steps. The needle points to the first.</p><ol class="heading">')
    for r in res["recommendations"][:3]:
        a(f'<li><div class="kind">{e(r["kind"])}</div><strong>{e(r["title"])}</strong><div class="small">{e(r["do"])}</div>'
          + (f'<div class="small muted">Ideas: {e("; ".join(r["ideas"]))}</div>' if r["ideas"] else "") + '</li>')
    if not res["recommendations"]:
        a('<li>No gaps in scope. Consider claiming a new axis or measuring outcomes.</li>')
    a('</ol>')
    if res["safety"]:
        s = res["safety"]
        a(f'<p class="note">Safety lens (CSEF scan, level {s["level"]}): <strong>{s["block"]}</strong> blocking, {s["review"]} to review, '
          f'{s["warn"]} warnings, {s["human"]} human checks.</p>')
    else:
        a('<p class="note small">Safety lens not run. Run the CSEF scan and pass <code>--csef-findings</code> to show it at the centre.</p>')
    a('</div></div></section>')

    a('<section class="panel"><h2>Axes</h2><p class="muted small">Learner axes count when the product claims them. Design axes apply to every product used by children.</p><div class="axes">')
    for x in res["axes"]:
        tot = max(x["in_scope"], 1)
        seg = "".join(f'<i style="width:{100 * x["counts"][k] / tot:.0f}%;background:{LEVEL_COLOR[k]}"></i>' for k in (4, 3, 2, 1, 0)) if x["in_scope"] else ""
        state = (f'{x["designed"]} of {x["in_scope"]} at Designed or above' if x["in_scope"] else
                 ("Not claimed. Evidence found for " + ", ".join(x["also_found"]) if x["also_found"] else "Not claimed"))
        a(f'<div class="axis{"" if x["in_scope"] else " off"}"><div class="rid">{e(x["id"])} · {e(x["lens"])}</div><h3>{e(x["title"])}</h3>'
          f'<div class="seg">{seg}</div><div class="small">{e(state)}</div>'
          + (f'<div class="small" style="color:var(--c-coral-t)">{x["conflicts"]} possible conflict(s)</div>' if x["conflicts"] else "")
          + f'<div class="small muted">{e(x["question"])}</div></div>')
    a('</div></section>')

    if res["claim_findings"] or res["conflicts"]:
        a('<section class="panel"><h2>Claims and hidden curriculum</h2>')
        for c in res["claim_findings"]:
            a(f'<p class="imp" style="--c:var(--WARN)"><strong>{e(c["message"])}</strong></p>')
            for x in c["claims"][:2]:
                a(f'<blockquote><span class="loc">{e(x["file"])}:{x["line"]}</span> {e(x["excerpt"][:200])}</blockquote>')
        for c in res["conflicts"]:
            a(f'<p class="imp" style="--c:var(--BLOCK)"><strong>{e(c["target"])}</strong>: “{e(c["phrase"])}” teaches the opposite of the target.</p>'
              f'<blockquote><span class="loc">{e(c["file"])}:{c["line"]}</span> {e(c["excerpt"][:220])}</blockquote>')
        a('</section>')

    a('<section class="panel"><h2>Targets</h2><div class="filters">')
    for st, lab, on in (("in_scope", "In scope", True), ("opportunity", "Opportunities", True), ("not_claimed", "Not claimed", False),
                        ("out_of_scope", "Out of scope", False), ("not_applicable", "Not applicable", False)):
        a(f'<label class="fchip" style="--c:var(--c-ink);--cb:var(--code)"><input type="checkbox" data-st value="{st}"{" checked" if on else ""}> {lab}</label>')
    a('<select id="fax" aria-label="Axis"><option value="">All axes</option>' + "".join(f'<option value="{x["id"]}">{e(x["id"])} {e(x["title"])}</option>' for x in res["axes"])
      + '</select><input id="q" type="search" placeholder="Search" aria-label="Search targets"><span id="fcount" class="small muted"></span></div>')
    order = {"in_scope": 0, "opportunity": 1, "not_claimed": 2, "out_of_scope": 3, "not_applicable": 4}
    for r in sorted(res["targets"], key=lambda r: (order[r["status"]], r["axis"], r["id"])):
        k = r["level"]
        a(f'<details class="card" data-st="{r["status"]}" data-ax="{r["axis"]}" style="--c:{LEVEL_COLOR[k]}"><summary>'
          f'<span class="ev" style="--f:{LEVEL_COLOR[k]};--t:{LEVEL_TEXT[k]}"><i></i>{k} {LEVELS[k]}</span><span class="rid">{e(r["id"])}</span>'
          f'<strong>{e(r["title"])}</strong><span class="typ">{e(r["why_scope"])}</span>'
          + (f'<span class="sev" style="--c:var(--BLOCK);--cb:var(--BLOCK-bg)">conflict</span>' if r["conflicts"] else "")
          + f'</summary><div class="body"><p>{e(r["target"])}</p><p class="small muted">{e(r["why"])}</p>')
        for an in r["anchors"]:
            a(f'<blockquote><span class="ev" style="--f:{LEVEL_COLOR[an["level"]]};--t:{LEVEL_TEXT[an["level"]]}"><i></i>{LEVELS[an["level"]]}</span> '
              f'<span class="loc">{e(an["file"])}:{an["line"]}</span>{(" · " + e(an["heading"])) if an["heading"] else ""}<br>{e(an["excerpt"])}</blockquote>')
        for c in r["conflicts"][:3]:
            a(f'<p class="note" style="background:var(--BLOCK-bg)"><strong>Possible conflict</strong> “{e(c["phrase"])}” in <span class="loc">{e(c["file"])}:{c["line"]}</span></p>')
        a(f'<p><strong>Next.</strong> {e(r["next"])}</p>')
        if r["ideas"] and k <= 1:
            a(f'<p class="small"><strong>Ideas.</strong> {e("; ".join(r["ideas"]))}</p>')
        refs = "; ".join(f"{kk} {', '.join(map(str, v))}" for kk, v in r["refs"].items() if v)
        a(f'<p class="small muted">Look for: {e(r["look_for"])}<br>Framework references: {e(refs or "-")} · Sources: {e(", ".join(r["sources"]))}</p>')
        for nt in r["notes"]:
            a(f'<p class="small">{e(nt)}</p>')
        a('</div></details>')
    a('</section>')

    a('<section class="panel"><h2>One dossier, many frameworks</h2><p class="muted small">Evidence at Designed or above that also answers these '
      'frameworks. Indicative mapping; each framework keeps its own method, and none of them is a rating.</p>')
    for fw, d in res["crosswalk"].items():
        a(f'<h3 style="margin-top:12px">{e(d["title"])}</h3><table><thead><tr><th>Item</th><th>Evidence you can reuse</th><th>Gaps</th></tr></thead><tbody>')
        for row in d["rows"]:
            a(f'<tr><td><strong>{e(row["key"])}</strong> {e(row["label"])}</td><td class="small">{e(", ".join(row["evidence"]) or "-")}</td>'
              f'<td class="small">{e(", ".join(row["gaps"]) or "-")}</td></tr>')
        a('</tbody></table>')
    a('</section>')

    a('<section class="panel"><h2>Evidence ladder</h2><div class="lad">')
    for k, v in LEVEL_MEANING.items():
        a(f'<div style="--f:{LEVEL_COLOR[k]}"><strong style="color:{LEVEL_TEXT[k]}">{k} {LEVELS[k]}</strong><div class="small">{e(v)}</div></div>')
    a('</div></section><section class="panel"><h2>Sources</h2><table><tbody>')
    for sid, s in res["sources"].items():
        t = f'<a href="{e(s["url"])}">{e(s["title"])}</a>' if s.get("url") else e(s["title"])
        a(f'<tr><td class="rid">{e(sid)}</td><td>{t}</td><td class="small">{e(s.get("status") or "")}</td></tr>')
    a('</tbody></table></section>')
    a('<section class="panel small muted"><h2>Limits</h2><ul><li>Reads words, not behaviour: play the product with learners.</li>'
      '<li>Matching is in English and European Portuguese; the csef-review skill compares meaning in any language.</li>'
      '<li>Evidence levels come from the nearest passages; check the whole document.</li><li>No learner data is needed or used.</li></ul></section></div>')
    a('''<script>(function(){const q=document.getElementById('q'),ax=document.getElementById('fax');
function f(){const st=new Set([...document.querySelectorAll('[data-st]:checked')].map(x=>x.value));const t=(q.value||'').toLowerCase();let n=0;
document.querySelectorAll('details.card').forEach(c=>{const ok=st.has(c.dataset.st)&&(!ax.value||c.dataset.ax===ax.value)&&(!t||c.textContent.toLowerCase().includes(t));c.classList.toggle('hidden',!ok);if(ok)n++;});
document.getElementById('fcount').textContent=n+' shown';}
document.querySelectorAll('[data-st]').forEach(x=>x.addEventListener('change',f));q.addEventListener('input',f);ax.addEventListener('change',f);f();})();</script>''')
    a('</body></html>')
    return "".join(o)


# --------------------------------------------------------------------------- cli
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CSEF Literacy Compass: what does this product teach about digital life, and how do we know?")
    ap.add_argument("--input", action="append", required=True, help="file or folder (repeatable): .md .txt .html .pdf .docx and text content (.json .yaml .po .csv)")
    ap.add_argument("--manifest", help="csef.yaml with age_bands, features and an optional compass section")
    ap.add_argument("--product", help="product name (default: from the manifest)")
    ap.add_argument("--claims", help="comma-separated axes or target ids the product claims (adds to the manifest)")
    ap.add_argument("--features", help="comma-separated features (adds to the manifest)")
    ap.add_argument("--bands", help="comma-separated age bands (overrides the manifest)")
    ap.add_argument("--csef-findings", help="findings.json from tooling/scan.py, for the safety lens")
    ap.add_argument("--pack", action="append", default=[], help="extra pack with sources and compass amendments (repeatable)")
    ap.add_argument("--framework-root", dest="root", default=None)
    ap.add_argument("--out-dir", default="csef-compass")
    ap.add_argument("--formats", default="md,html,json")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else scan.default_root()
    std = scan.load_standard(root)
    manifest = scan.load_yaml(Path(args.manifest)) if args.manifest else None
    packs = [Path(p) for p in args.pack]
    for code in (manifest or {}).get("jurisdictions", []) or []:
        pp = root / "packs" / f"{str(code).lower()}.yaml"
        if pp.exists() and pp not in packs:
            packs.insert(0, pp)
    for pp in packs:
        scan.apply_pack(std, pp)
    try:
        compass = load_compass(root, packs, std)
    except ValueError as ex:
        print(f"csef compass: {ex}", file=sys.stderr)
        return 2
    inputs = collect_inputs(args.input)
    if not inputs:
        print("csef compass: no readable input files", file=sys.stderr)
        return 2
    findings = json.loads(Path(args.csef_findings).read_text(encoding="utf-8")) if args.csef_findings else None
    res = run(inputs, compass, std, resolve_scope(manifest, args, compass), findings)
    res["packs"] = [str(p) for p in packs]
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fm = [f.strip() for f in args.formats.split(",")]
    if "md" in fm:
        (out / "compass.md").write_text(render_md(res), encoding="utf-8")
    if "html" in fm:
        (out / "compass.html").write_text(render_html(res), encoding="utf-8")
    if "json" in fm:
        (out / "compass.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    ins = [x for x in res["targets"] if x["status"] == "in_scope"]
    print(f"{res['product']}: {len(ins)} targets in scope, {sum(1 for x in ins if x['level'] >= 2)} at Designed or above, "
          f"{len(res['conflicts'])} possible conflict(s), {len(res['claim_findings'])} claim finding(s) | written to {out}/")
    for r in res["recommendations"][:3]:
        print(f"  {r['n']}. {r['kind']}: {r['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
