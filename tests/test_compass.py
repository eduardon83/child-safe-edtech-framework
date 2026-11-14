"""Tests for the CSEF Literacy Compass (tooling/compass.py)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))

import compass  # noqa: E402
import scan  # noqa: E402

EX = ROOT / "examples" / "compass" / "fact-quest"


def run_on(tmp_path, files: dict, claims="", features="", bands="B3,B4", packs=()):
    for name, text in files.items():
        p = tmp_path / "in" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    std = scan.load_standard(ROOT)
    for pp in packs:
        scan.apply_pack(std, pp)
    c = compass.load_compass(ROOT, list(packs), std)

    class A:
        pass
    a = A()
    a.bands, a.features, a.claims, a.product = bands, features, claims, "Test"
    return compass.run(compass.collect_inputs([str(tmp_path / "in")]), c, std, compass.resolve_scope(None, a, c), None)


def by_id(res):
    return {t["id"]: t for t in res["targets"]}


def test_example_profile(tmp_path):
    out = tmp_path / "out"
    rc = compass.main(["--input", str(EX), "--manifest", str(EX / "csef.yaml"), "--out-dir", str(out)])
    assert rc == 0
    res = json.loads((out / "compass.json").read_text(encoding="utf-8"))
    t = by_id(res)
    assert t["INF-02"]["status"] == "in_scope" and t["INF-02"]["level"] == 3          # pilot report: Tested
    assert t["AI-03"]["level"] == 3
    assert t["INF-05"]["status"] == "not_applicable"                                  # declared in csef.yaml
    assert t["TRN-04"]["status"] == "in_scope" and t["TRN-04"]["level"] == 0          # purchases, no labels
    assert {c["target"] for c in res["conflicts"]} == {"AI-02", "SAF-05"}             # "your best friend", "spin the wheel"
    assert any(f["axis"] == "SAF" and f["kind"] == "unsupported" for f in res["claim_findings"])
    assert res["recommendations"][0]["priority"] == 1
    assert "score" not in res and all("score" not in a for a in res["axes"])          # a profile, never a score
    html = (out / "compass.html").read_text(encoding="utf-8")
    assert "<svg" in html and "A profile, not a score" in html
    assert (out / "compass.md").read_text(encoding="utf-8").startswith("# Literacy Compass")


def test_universal_targets_always_in_scope(tmp_path):
    res = run_on(tmp_path, {"doc.md": "# Game\n\nA maths game about fractions.\n"})
    t = by_id(res)
    assert t["TRN-01"]["status"] == "in_scope" and t["EDU-01"]["status"] == "in_scope"
    assert t["INF-02"]["status"] == "not_claimed"                                     # not claimed, not a failure
    assert t["TRN-02"]["status"] == "out_of_scope"                                    # no AI feature


def test_quoted_rule_is_not_a_conflict(tmp_path):
    res = run_on(tmp_path, {"style.md": "# Style guide\n\nThe helper must never say \"I am your friend\" and must avoid saying it knows everything.\n"},
                 claims="AI")
    assert res["conflicts"] == []


def test_real_conflict_is_flagged(tmp_path):
    res = run_on(tmp_path, {"dialogue.json": json.dumps({"a": "Hi, I am your friend and I know everything!"})}, claims="AI")
    assert {c["target"] for c in res["conflicts"]} == {"AI-02"}


def test_plans_are_not_evidence(tmp_path):
    text = ("# Evaluation\n\nLearners evaluate AI answers and decide to accept, revise or reject them in each mission.\n\n"
            "Next step: a randomised study with a control group.\n")
    res = run_on(tmp_path, {"plan.md": text}, claims="AI")
    assert by_id(res)["AI-03"]["level"] == 2


def test_measured_evidence(tmp_path):
    text = ("# Evaluation\n\nLearners evaluate AI answers and decide to accept, revise or reject them. In a study with a control group, "
            "the effect size was d = 0.42.\n")
    res = run_on(tmp_path, {"eval.md": text}, claims="AI")
    assert by_id(res)["AI-03"]["level"] == 4


def test_framework_citation_does_not_match_words(tmp_path):
    res = run_on(tmp_path, {"doc.md": "# Goals\n\nPlayers spot manipulated media (AILit Create 4).\n"}, claims="CRE,INF")
    t = by_id(res)
    assert t["CRE-01"]["level"] == 0          # "Create" in the citation is not content creation
    assert t["INF-04"]["level"] >= 2


def test_unique_reference_matches_on_its_own(tmp_path):
    res = run_on(tmp_path, {"doc.md": "# Goals\n\nMission 2 covers DigComp 3.4 with block puzzles.\n"}, claims="CRE")
    assert by_id(res)["CRE-03"]["level"] == 2


def test_strong_claim_needs_measured_evidence(tmp_path):
    files = {"site.md": "Scientifically proven to teach critical thinking.\n",
             "design.md": "# Missions\n\nLearners verify each claim against a second source in every mission.\n"}
    res = run_on(tmp_path, files)
    assert any(f["axis"] == "INF" and f["kind"] == "strong_without_measure" for f in res["claim_findings"])


def test_pack_amends_targets():
    std = scan.load_standard(ROOT)
    pt = ROOT / "packs" / "pt.yaml"
    scan.apply_pack(std, pt)
    c = compass.load_compass(ROOT, [pt], std)
    assert "PT-EPM" in c["targets"]["INF-02"]["sources"]
    assert any("PT" in n for n in c["targets"]["INF-02"]["notes"])


def test_crosswalk_rows(tmp_path):
    res = run_on(tmp_path, {"doc.md": "# Teacher guide\n\nDebrief questions for each mission link play to the learning goals.\n"})
    rows = {r["key"]: r for r in res["crosswalk"]["SWE-KP"]["rows"]}
    assert any(x.startswith("EDU-02") for x in rows["6"]["evidence"])
