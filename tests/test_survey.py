"""Tests for personal questions (feature `survey`): manifest checks, detection, Portugal pack, Compass join."""
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
import scan  # noqa: E402

GOOD = ROOT / "examples" / "compliant-game"
SURVEY_RULES = {"CORE-DAT-13", "CORE-DAT-14", "CORE-DAT-15", "CORE-DAT-16", "CORE-DAT-17", "CORE-DAT-18", "CORE-SAF-11"}


def make_repo(tmp_path, survey: dict | None, bands=("B2",), files=None, jurisdictions=("EU",)):
    repo = tmp_path / "repo"
    shutil.copytree(GOOD, repo)
    m = yaml.safe_load((repo / "csef.yaml").read_text(encoding="utf-8"))
    m["age_bands"] = list(bands)
    m["jurisdictions"] = list(jurisdictions)
    if survey is not None:
        m["features"] = sorted(set(m["features"]) | {"survey"})
        m["survey"] = survey
    (repo / "csef.yaml").write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True), encoding="utf-8")
    for rel, text in (files or {}).items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return repo


def run(repo, level=3, packs=()):
    std = scan.load_standard(ROOT)
    m = scan.load_yaml(repo / "csef.yaml")
    for p in scan.resolve_packs(repo, ROOT, m, list(packs)):
        scan.apply_pack(std, p)
    return std, scan.scan(repo, std, m, level)


def ids(res, sev=None):
    return {f.rule_id for f in res["findings"] if sev is None or f.severity == sev}


def test_survey_rules_only_with_the_feature(tmp_path):
    _, res = run(make_repo(tmp_path, None))
    assert not ids(res) & SURVEY_RULES
    assert not {h["rule_id"] for h in res["human_checks"]} & {"CORE-DAT-13", "CORE-DAT-15"}


def test_risky_survey_manifest_trips_every_check(tmp_path):
    survey = {"answered_by": "child", "teacher_view": "individual", "min_group": 3, "free_text": True,
              "uses": ["personalisation", "research"]}
    _, res = run(make_repo(tmp_path, survey, bands=("B2", "B3")))
    found = ids(res)
    for rid in ("CORE-DAT-13", "CORE-DAT-16", "CORE-DAT-17", "CORE-DAT-18", "CORE-SAF-11"):
        assert rid in found, f"{rid} missing: {sorted(found)}"
    msgs = " ".join(f.evidence for f in res["findings"] if f.rule_id == "CORE-DAT-17")
    assert "individual" in msgs                                    # teacher_view: individual
    assert "CORE-DAT-01" not in ids(res, "BLOCK")                 # DPIA present in the example


def test_min_group_only_checked_for_aggregate_views(tmp_path):
    survey = {"register": "docs/survey-register.md", "answered_by": "guardian", "teacher_view": "aggregate", "min_group": 3}
    repo = make_repo(tmp_path, survey, files={"docs/survey-register.md": "# Survey register\n"})
    _, res = run(repo)
    msgs = [f.evidence for f in res["findings"] if f.rule_id == "CORE-DAT-17"]
    assert len(msgs) == 1 and "min_group" in msgs[0]


def test_well_declared_survey_passes_manifest_checks(tmp_path):
    survey = {"register": "docs/survey-register.md", "answered_by": "guardian", "teacher_view": "aggregate",
              "min_group": 5, "free_text": False, "uses": ["personalisation"]}
    repo = make_repo(tmp_path, survey, files={"docs/survey-register.md": "# Survey register\n"})
    _, res = run(repo)
    assert not ids(res) & SURVEY_RULES
    human = {h["rule_id"] for h in res["human_checks"]}
    assert {"CORE-DAT-13", "CORE-DAT-15"} <= human                  # mixed rules still need a person
    assert "CORE-DES-08" in human


def test_teenagers_may_answer_for_themselves(tmp_path):
    survey = {"register": "docs/survey-register.md", "answered_by": "child", "teacher_view": "aggregate", "min_group": 5}
    repo = make_repo(tmp_path, survey, bands=("B4",), files={"docs/survey-register.md": "# Survey register\n"})
    _, res = run(repo)
    assert "CORE-DAT-16" not in ids(res)


def test_detection_of_family_and_third_party_questions(tmp_path):
    code = (
        "export const questions = [\n"
        "  'Os teus pais são separados?',\n"
        "  'Qual é o nome da tua mãe?',\n"
        "  'Where were your parents born?',\n"
        "  \"What is your best friend's phone?\",\n"
        "  'Complete the survey to earn 50 coins!',\n"
        "];\n"
    )
    survey = {"register": "docs/survey-register.md", "answered_by": "guardian", "teacher_view": "aggregate", "min_group": 5}
    repo = make_repo(tmp_path, survey, files={"src/questions.ts": code, "docs/survey-register.md": "# r\n"})
    _, res = run(repo)
    lines = {(f.rule_id, f.line) for f in res["findings"] if f.path == "src/questions.ts"}
    assert ("CORE-DAT-15", 2) in lines and ("CORE-DAT-15", 4) in lines
    assert ("CORE-DAT-14", 3) in lines and ("CORE-DAT-14", 5) in lines
    assert ("CORE-DAT-13", 6) in lines


def test_portugal_pack_adds_mime_rule(tmp_path):
    survey = {"register": "docs/survey-register.md", "answered_by": "guardian", "teacher_view": "aggregate",
              "min_group": 5, "uses": ["evaluation"]}
    repo = make_repo(tmp_path, survey, files={"docs/survey-register.md": "# r\n"}, jurisdictions=("EU", "PT"))
    std, res = run(repo)
    assert "PT-SUR-01" in std.rules and "PT-MIME" in std.sources
    assert {"PT-SUR-01", "CORE-DAT-18"} <= ids(res)                 # evaluation use without an approval record
    assert "PT-LPCJP" in std.rules["CORE-SAF-11"]["sources"]


def test_compass_trn08_follows_the_survey_feature(tmp_path):
    import compass
    std = scan.load_standard(ROOT)
    c = compass.load_compass(ROOT, [], std)
    (tmp_path / "doc.md").write_text("# Questions\n\nBefore the questions the game says why we ask and that you can skip any of them.\n",
                                     encoding="utf-8")

    class A:
        bands, claims, product = "B3", "", "T"
    a = A()
    a.features = "survey"
    res = compass.run([tmp_path / "doc.md"], c, std, compass.resolve_scope(None, a, c), None)
    t = {x["id"]: x for x in res["targets"]}
    assert t["TRN-08"]["status"] == "in_scope" and t["TRN-08"]["level"] >= 1
    a.features = ""
    res = compass.run([tmp_path / "doc.md"], c, std, compass.resolve_scope(None, a, c), None)
    assert {x["id"]: x for x in res["targets"]}["TRN-08"]["status"] == "out_of_scope"
