"""Tests for the CSEF scanner and catalogue. Run: python3 -m pytest -q"""
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
    (repo / "csef.yaml").write_text(base + "waivers:\n  - {rule: CORE-SEC-03, reason: legacy}\n", encoding="utf-8")
    _, _, res = run(repo)
    assert "CORE-SEC-03" in rules_with(res, "REVIEW")
    (repo / "csef.yaml").write_text(base + "waivers:\n  - {rule: CORE-SEC-03, reason: legacy, approved_by: DPO, expires: 2099-01-01}\n", encoding="utf-8")
    _, _, res = run(repo)
    assert "CORE-SEC-03" in rules_with(res, "WAIVED")


def test_inline_ignore(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "a.ts").write_text(
        '// cses-ignore: CORE-SEC-03 -- public static asset host\nconst x = "http://cdn.example.org/img.png";\n', encoding="utf-8")
    (repo / "csef.yaml").write_text("product: t\nprofiles: [C]\nage_bands: [B4]\n", encoding="utf-8")
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


UNITY = ROOT / "examples" / "unity-sample"
COC = ROOT / "examples" / "codes-of-conduct" / "example-code.md"


def test_communications_inventory():
    _, _, res = run(BAD, level=2)
    inv = res["communications"]
    assert inv["has_communication"]
    assert {"Socket.IO", "Agora"} <= {c["name"] for c in inv["channels"]}
    assert not inv["safeguards"]["report"]["evidence"]
    flagged = rules_with(res, "REVIEW") | rules_with(res, "BLOCK")
    for rid in ["CORE-CHT-02", "CORE-CHT-03", "CORE-CHT-04", "CORE-CHT-05", "CORE-CHT-06", "CORE-CHT-07"]:
        assert rid in flagged, rid
    assert "CORE-CHT-06" in rules_with(res, "BLOCK")          # voiceChatEnabled: true


def test_no_comms_in_compliant_example():
    _, _, res = run(GOOD, level=3)
    assert not res["communications"]["has_communication"]
    assert not any(f.rule_id.startswith("CORE-CHT") for f in res["findings"])


def test_unity_project():
    _, _, res = run(UNITY, level=2)
    block = rules_with(res, "BLOCK")
    assert "CORE-COM-01" in block                              # com.unity.ads + Advertisement.Initialize
    assert "CORE-CHT-06" in block                              # voiceChatEnabled: 1 in a prefab
    assert "Vivox / Photon Voice" in {c["name"] for c in res["communications"]["channels"]}
    deps = scan.collect_dependencies(UNITY)
    assert "com.unity.purchasing" in deps


def test_dependency_parsers(tmp_path):
    (tmp_path / "pom.xml").write_text("<project><dependencies><dependency><groupId>com.appsflyer</groupId><artifactId>af-android-sdk</artifactId></dependency></dependencies></project>", encoding="utf-8")
    (tmp_path / "App.csproj").write_text('<Project><ItemGroup><PackageReference Include="GoogleMobileAds" Version="9.0.0" /></ItemGroup></Project>', encoding="utf-8")
    (tmp_path / "go.mod").write_text("module x\n\nrequire (\n\tgithub.com/gorilla/websocket v1.5.0\n)\n", encoding="utf-8")
    (tmp_path / "composer.json").write_text('{"require": {"pusher/pusher-php-server": "^7.0"}}', encoding="utf-8")
    (tmp_path / "Gemfile").write_text("gem 'rails'\n", encoding="utf-8")
    deps = scan.collect_dependencies(tmp_path)
    for name in ["com.appsflyer:af-android-sdk", "GoogleMobileAds", "github.com/gorilla/websocket", "pusher/pusher-php-server", "rails"]:
        assert name in deps, name


def test_out_dir_relative_to_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scan.main(["--repo", str(GOOD), "--out-dir", "out", "--format", "none"])
    assert (tmp_path / "out" / "report.md").exists()


def test_code_of_conduct_comparison(tmp_path):
    import coc
    code = scan.main  # noqa: F841  (scan imported above)
    assert coc.main(["--input", str(COC), "--name", "Example", "--level", "2", "--out-dir", str(tmp_path)]) == 0
    res = json.loads((tmp_path / "coc-comparison.json").read_text(encoding="utf-8"))
    by = {r["rule_id"]: r["status"] for r in res["rules"]}
    assert by["A-ECO-01"] == "conflict"                      # loot boxes allowed if odds disclosed
    assert by["CORE-SAF-02"] == "conflict"                   # notifications enabled by default
    assert by["CORE-CHT-02"] == "covered"                    # report and block in every chat
    assert by["CORE-AI-01"] == "missing"
    s = {x["id"]: x["status"] for x in res["structure"]}
    assert s["COC-S05"] == "missing" and s["COC-S06"] == "covered"
    assert "Possible conflicts" in (tmp_path / "coc-comparison.md").read_text(encoding="utf-8")


def test_legacy_cses_names_still_work(tmp_path):
    """v0.6 renamed CSES to CSEF; the old manifest name and ignore marker must keep working."""
    (tmp_path / "cses.yaml").write_text("product: legacy\nprofiles: [A]\nage_bands: [B2]\n", encoding="utf-8")
    assert scan.find_manifest(tmp_path, None) == tmp_path / "cses.yaml"
    (tmp_path / "csef.yaml").write_text("product: new\nprofiles: [A]\nage_bands: [B2]\n", encoding="utf-8")
    assert scan.find_manifest(tmp_path, None) == tmp_path / "csef.yaml"
    assert scan.IGNORE_RE.search("// cses-ignore: CORE-DAT-01 -- reason")
    assert scan.IGNORE_RE.search("// csef-ignore: CORE-DAT-01 -- reason")


def test_policy_questionnaire(tmp_path):
    import policy
    q = policy.Q(ROOT)
    raw = json.loads((ROOT / "examples" / "policy" / "answers.json").read_text())["answers"]
    out = tmp_path / "kit"
    res = policy.generate(q, raw, out, formats=("md", "html"), with_skill=False, today="2026-11-13")
    assert res["ok"], res
    assert res["version"] == "1.0.0"
    for f in ("acme.yaml", "answers.json", "boundaries-report.md", "staff-policy.html", "agent-instructions.md",
              "csef-check.yml", "README.md"):
        assert (out / f).exists(), f
    pack = scan.load_yaml(out / "acme.yaml")
    assert pack["policy"]["minimum_level"] == 2
    assert "CORE-COM-01" in pack["policy"]["no_go"] and "C-ENG-01" not in pack["policy"]["no_go"]
    assert "streaks" in pack["policy"]["require_decision_for_features"]
    assert pack["rules"][0]["id"] == "ACME-OWN-01"
    std = scan.load_standard(ROOT)
    scan.apply_pack(std, out / "acme.yaml")
    assert std.minimum_level == 2 and std.rules["A-ECO-01"]["no_go"]
    # Redo with one change: version goes up and the change is reported.
    prev = policy.load_previous(out / "answers.json")
    res2 = policy.generate(q, dict(raw, streaks="never"), out, formats=("md",), previous=prev, with_skill=False)
    assert res2["version"] == "1.1.0" and any("Streaks" in c for c in res2["changes"])
    assert "C-ENG-01" in scan.load_yaml(out / "acme.yaml")["policy"]["no_go"]
    # Same answers again: version unchanged.
    res3 = policy.generate(q, dict(raw, streaks="never"), out, formats=("md",),
                           previous=policy.load_previous(out / "answers.json"), with_skill=False)
    assert res3["version"] == "1.1.0" and not res3["changes"]
    # Invalid answers are rejected, never written.
    bad = policy.generate(q, dict(raw, pack_id="X1", minimum_level="5"), tmp_path / "bad", formats=("md",), with_skill=False)
    assert not bad["ok"] and len(bad["errors"]) == 2


def test_policy_hides_questions_for_unused_features():
    import policy
    q = policy.Q(ROOT)
    a, errs = policy.normalise(q, {"org_name": "Tiny", "profiles": ["B"], "age_bands": ["B4"], "features": [],
                                   "minimum_level": "1", "streaks": "approval"})
    assert not errs and a["pack_id"] == "tiny"
    res = policy.assess(q, a)
    items = {i["id"]: i for i in res["items"]}
    assert items["streaks"]["key"] == "na" and items["ads"]["key"] == "covered"
    assert items["commercial_learning"]["key"] == "gap"


def test_brand_in_html_outputs(tmp_path):
    import brand
    import policy
    logo = brand.logo()
    assert "<svg" in logo and "var(--c-ink" in logo and 'width="594"' not in logo
    html_form = policy.render_form(policy.Q(ROOT), None, False)
    assert "csef-stripe" in html_form and "--c-paper" in html_form
    res = subprocess.run([sys.executable, str(ROOT / "skill" / "csef-review" / "scripts" / "policy.py"), "--answers",
                          str(ROOT / "examples" / "policy" / "answers.json"), "--batch", "--out-dir", str(tmp_path / "k"),
                          "--formats", "html"], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert "csef-brand" in (tmp_path / "k" / "staff-policy.html").read_text()
