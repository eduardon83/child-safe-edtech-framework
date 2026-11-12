"""Tests for the CSES scanner and catalogue. Run: python3 -m pytest -q"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
import scan  # noqa: E402

BAD = ROOT / "examples" / "noncompliant-game"
GOOD = ROOT / "examples" / "compliant-game"


def run(repo, level=None, packs=(), manifest=None):
    std = scan.load_standard(ROOT)
    mpath = scan.find_manifest(repo, manifest)
    m = scan.load_yaml(mpath) if mpath and mpath.exists() else None
    for p in scan.resolve_packs(repo, ROOT, m, list(packs)):
        scan.apply_pack(std, p)
    lvl = level or int((m or {}).get("compliance_level", 1))
    return std, m, scan.scan(repo, std, m, lvl)


def rules_with(result, severity):
    return {f.rule_id for f in result["findings"] if f.severity == severity}


def test_build_check_passes():
    r = subprocess.run([sys.executable, str(ROOT / "tooling" / "build.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_noncompliant_blocks_on_key_rules():
    _, _, res = run(BAD)
    block = rules_with(res, "BLOCK")
    for rid in ["CORE-COM-01", "A-ECO-01", "CORE-AI-01", "CORE-AI-06", "CORE-SAF-02",
                "C-ENG-01", "CORE-DAT-03", "CORE-COM-04"]:
        assert rid in block, f"{rid} not blocking: {sorted(block)}"


def test_compliant_has_no_blocking_findings_at_level_3():
    _, _, res = run(GOOD, level=3)
    assert not rules_with(res, "BLOCK")
    assert not rules_with(res, "REVIEW")


def test_level_1_turns_forward_rules_into_next():
    _, _, res = run(BAD, level=1)
    assert "A-ECO-01" in rules_with(res, "NEXT")       # tier 2 rule
    assert "A-ECO-01" not in rules_with(res, "BLOCK")
    assert "CORE-AI-01" in rules_with(res, "BLOCK")    # tier 1 rule still blocks


def test_human_checks_marked_next_level():
    _, _, res = run(GOOD, level=1)
    nxt = {h["rule_id"] for h in res["human_checks"] if h["next_level"]}
    assert "CORE-SAF-07" in nxt                         # tier 2 manual rule
    now = {h["rule_id"] for h in res["human_checks"] if not h["next_level"]}
    assert "CORE-DAT-06" in now                         # tier 1 manual rule


def test_pt_pack_loaded_from_jurisdiction():
    std, _, res = run(GOOD)
    assert any(p["id"] == "pt" for p in std.packs)
    assert "PT-LNG-01" in res["rules_in_scope"]
    assert "PT-LEI58" in std.rules["AGE-B4-01"]["sources"]
    assert std.rules["CORE-ACC-01"]["tier"] == 1


def test_pack_cannot_weaken(tmp_path):
    bad_pack = tmp_path / "weak.yaml"
    bad_pack.write_text("pack: {id: weak}\namend:\n  - rule: CORE-AI-01\n    level: SHOULD\n", encoding="utf-8")
    std = scan.load_standard(ROOT)
    with pytest.raises(ValueError):
        scan.apply_pack(std, bad_pack)
    raise_tier = tmp_path / "tier.yaml"
    raise_tier.write_text("pack: {id: tier}\namend:\n  - rule: CORE-AI-01\n    tier: 3\n", encoding="utf-8")
    with pytest.raises(ValueError):
        scan.apply_pack(scan.load_standard(ROOT), raise_tier)


def test_custom_pack_adds_rule_and_pattern(tmp_path):
    pack = tmp_path / "acme.yaml"
    pack.write_text(
        "pack: {id: acme, title: Acme red lines}\n"
        "rules:\n"
        "  - id: ACME-COM-01\n    title: No coins\n    level: MUST\n    tier: 3\n    profiles: [core]\n"
        "    age_bands: [all]\n    requirement: No coins.\n    rationale: House rule.\n    improvement: Remove coins.\n"
        "    effort: low\n    sources: [UNCRC-GC25]\n"
        "    detection: {method: static, patterns: [{type: regex, confidence: high, pattern: 'gemPack'}]}\n",
        encoding="utf-8")
    _, _, res = run(BAD, level=3, packs=[str(pack)])
    assert "ACME-COM-01" in rules_with(res, "BLOCK")


def test_waiver_requires_approver(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "a.ts").write_text('const x = "http://cdn.example.org/img.png";\n', encoding="utf-8")
    base = "product: t\nprofiles: [C]\nage_bands: [B4]\ncompliance_level: 1\n"
    (repo / "cses.yaml").write_text(base + "waivers:\n  - {rule: CORE-SEC-03, reason: legacy}\n", encoding="utf-8")
    _, _, res = run(repo)
    assert "CORE-SEC-03" in rules_with(res, "REVIEW")
    (repo / "cses.yaml").write_text(base + "waivers:\n  - {rule: CORE-SEC-03, reason: legacy, approved_by: DPO, expires: 2099-01-01}\n", encoding="utf-8")
    _, _, res = run(repo)
    assert "CORE-SEC-03" in rules_with(res, "WAIVED")


def test_inline_ignore(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "a.ts").write_text(
        '// cses-ignore: CORE-SEC-03 -- public static asset host\nconst x = "http://cdn.example.org/img.png";\n', encoding="utf-8")
    (repo / "cses.yaml").write_text("product: t\nprofiles: [C]\nage_bands: [B4]\n", encoding="utf-8")
    _, _, res = run(repo)
    assert "CORE-SEC-03" in rules_with(res, "WAIVED")


def test_cli_writes_all_outputs(tmp_path):
    out = tmp_path / "out"
    code = scan.main(["--repo", str(BAD), "--out-dir", str(out), "--format", "none"])
    assert code == 1
    for f in ["report.md", "improvements.md", "findings.json", "findings.sarif"]:
        assert (out / f).exists()
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "## Sources" in report and "eur-lex.europa.eu" in report
    imp = (out / "improvements.md").read_text(encoding="utf-8")
    assert "Fix before release" in imp and "To reach the next level" in imp
    sarif = json.loads((out / "findings.sarif").read_text(encoding="utf-8"))
    assert sarif["runs"][0]["results"]


def test_missing_manifest_is_reported(tmp_path):
    (tmp_path / "x.js").write_text("console.log('hi')\n", encoding="utf-8")
    _, _, res = run(tmp_path)
    assert "CORE-GOV-01" in rules_with(res, "BLOCK")


def test_design_and_motivation_checks():
    _, _, res = run(BAD, level=3)
    warn = rules_with(res, "WARN")
    assert "A-MOT-01" in warn          # reward pile-up signal
    assert "CORE-DES-01" in warn       # animations without reduced-motion handling
    _, _, res2 = run(BAD, level=2)
    assert "A-MOT-01" in rules_with(res2, "NEXT")   # tier 3 shows as next level at level 2


def test_research_sources_are_literature():
    std = scan.load_standard(ROOT)
    assert std.sources["R-DECI1999"]["type"] == "literature"
    assert "R-RADESKY2022" in std.rules["CORE-COM-03"]["sources"]


ACME = ROOT / "examples" / "company-packs" / "acme.yaml"


def test_company_pack_policy(tmp_path):
    std, _, res = run(BAD, level=1, packs=[str(ACME)])
    assert std.minimum_level == 2
    assert std.sources["ACME-POLICY"]["type"] == "policy"
    assert std.rules["A-ECO-01"]["tier"] == 1 and std.rules["A-ECO-01"].get("no_go")
    block = rules_with(res, "BLOCK")
    assert "A-ECO-01" in block                          # no-go blocks even at level 1
    assert "ACME-POL-01" in block                       # forbidden dependency (@hotjar/browser)
    assert "ACME-POL-03" in block                       # decision record missing for ai_generative / leaderboards
    assert "CORE-DAT-07" in block                       # medium-confidence finding escalated by no-go


def test_cli_minimum_level_from_pack(tmp_path):
    out = tmp_path / "out"
    scan.main(["--repo", str(GOOD), "--pack", str(ACME), "--level", "1", "--out-dir", str(out), "--format", "none"])
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "Level 2: Forward-compliant" in report and "Minimum level" in report


def test_validate_pack_cli():
    r = subprocess.run([sys.executable, str(ROOT / "tooling" / "build.py"), "--validate-pack", str(ACME)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_pack_cannot_weaken_via_policy(tmp_path):
    bad = tmp_path / "x.yaml"
    bad.write_text("pack: {id: x}\npolicy: {no_go: [NOPE-01]}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        scan.apply_pack(scan.load_standard(ROOT), bad)


def test_pack_builder_embeds_catalogue():
    html = (ROOT / "docs" / "pack-builder" / "index.html").read_text(encoding="utf-8")
    assert "/*CATALOGUE*/null" not in html and '"A-MOT-01"' in html


def test_export_html_and_docx(tmp_path):
    out = tmp_path / "out"
    scan.main(["--repo", str(BAD), "--out-dir", str(out), "--format", "none"])
    sys.path.insert(0, str(ROOT / "tooling"))
    import export
    written = export.export(out / "findings.json", ["html", "docx"], out)
    html_text = (out / "dashboard.html").read_text(encoding="utf-8")
    assert "Where you stand at each level" in html_text and "For legal counsel" in html_text
    assert "A-ECO-01" in html_text and "B3 · ages 10-12" in html_text
    assert (out / "report.docx").stat().st_size > 10000
    model = export.build_model(json.loads((out / "findings.json").read_text(encoding="utf-8")))
    assert [lv["status"] for lv in model["levels"]][0] == "blocked"
    assert any(b["declared"] for b in model["bands"])


def test_kids_act_commercial_and_ai_rules():
    _, _, res = run(BAD, level=2)
    flagged = rules_with(res, "REVIEW") | rules_with(res, "BLOCK")
    for rid in ["CORE-AI-08", "CORE-AI-10", "CORE-AI-11", "CORE-COM-06"]:
        assert rid in flagged, rid
    std = scan.load_standard(ROOT)
    assert std.rules["CORE-COM-07"]["tier"] == 1
