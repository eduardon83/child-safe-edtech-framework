"""Tests for v0.11: bullying rules, feature groups, retired rule ids and Compass builds_on."""
import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
import scan  # noqa: E402
import compass  # noqa: E402

GOOD = ROOT / "examples" / "compliant-game"
CHT_NEW = {"CORE-CHT-10", "CORE-CHT-11", "CORE-CHT-12", "CORE-CHT-13", "CORE-CHT-14", "CORE-CHT-15"}


def make_repo(tmp_path, features=("accounts",), extra=None, files=None):
    repo = tmp_path / "repo"
    shutil.copytree(GOOD, repo)
    m = yaml.safe_load((repo / "csef.yaml").read_text(encoding="utf-8"))
    m["features"] = list(features)
    m.update(extra or {})
    (repo / "csef.yaml").write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True), encoding="utf-8")
    for rel, text in (files or {}).items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return repo


def run(repo, level=3):
    std = scan.load_standard(ROOT)
    m = scan.load_yaml(repo / "csef.yaml")
    for p in scan.resolve_packs(repo, ROOT, m, []):
        scan.apply_pack(std, p)
    return std, scan.scan(repo, std, m, level)


def evidence(res, rid):
    return " ".join(f.evidence or "" for f in res["findings"] if f.rule_id == rid)


def test_communication_group_expands_everywhere():
    std = scan.load_standard(ROOT)
    assert set(std.rules["CORE-CHT-02"]["features"]) == {"chat", "multiplayer", "social", "ugc"}
    raw = yaml.safe_load((ROOT / "framework" / "rules.yaml").read_text(encoding="utf-8"))
    assert all("chat" not in (r.get("features") or []) or "communication" not in (r.get("features") or [])
               for r in raw["rules"])
    c = compass.load_compass(ROOT, [], std)
    assert "chat" in c["targets"]["TRN-06"]["features"]
    assert scan.features_declared(std.rules["CORE-CHT-02"], {"features": ["communication"]})


def test_bullying_rules_only_with_communication(tmp_path):
    def active(res):
        return {h["rule_id"] for h in res["human_checks"]} | {f.rule_id for f in res["findings"]}
    _, res = run(make_repo(tmp_path))
    assert not CHT_NEW & active(res)
    _, res = run(make_repo(tmp_path / "b", features=("accounts", "chat")))
    assert CHT_NEW <= active(res)


def test_moderation_checks(tmp_path):
    _, res = run(make_repo(tmp_path, features=("accounts", "multiplayer")))
    assert "open_hours" in evidence(res, "CORE-CHT-14")
    assert "bullying_procedure" in evidence(res, "CORE-CHT-15")
    mod = {"by": "teacher", "open_hours": "school days", "out_of_hours": "closed",
           "response_targets": {"urgent": "1 hour"}, "bullying_procedure": "school"}
    _, res = run(make_repo(tmp_path / "b", features=("accounts", "multiplayer"), extra={"moderation": mod}))
    assert not evidence(res, "CORE-CHT-14") and not evidence(res, "CORE-CHT-15")


def test_exclusion_and_deepfake_patterns(tmp_path):
    files = {"src/lobby.ts": "export function voteKick(player) {}\n",
             "src/avatar.py": "def face_swap(img, target):\n    pass\n"}
    _, res = run(make_repo(tmp_path, features=("accounts", "multiplayer", "ai_generative"), files=files))
    paths = {(f.rule_id, f.path) for f in res["findings"]}
    assert ("CORE-CHT-12", "src/lobby.ts") in paths
    assert ("CORE-AI-12", "src/avatar.py") in paths


def test_retired_ids_keep_working(tmp_path):
    std = scan.load_standard(ROOT)
    assert std.resolve("A-SOC-01") == "CORE-SAF-05" and "A-SOC-01" not in std.rules
    files = {"src/lobby.ts": "const g = joinPublicRoom(); // csef-ignore: A-SOC-01 -- tested with teachers\n"}
    waiver = [{"rule": "CORE-SAF-11", "approved_by": "DPO", "expires": "2999-01-01", "reason": "pilot"}]
    _, res = run(make_repo(tmp_path, features=("accounts", "multiplayer"), extra={"waivers": waiver}, files=files))
    saf05 = [f for f in res["findings"] if f.rule_id == "CORE-SAF-05" and f.path == "src/lobby.ts"]
    assert saf05 and all(f.severity == "WAIVED" for f in saf05)
    pack = tmp_path / "pack.yaml"
    pack.write_text("pack: {id: test, title: Test}\namend:\n  - rule: A-ECO-04\n    note: still works\n", encoding="utf-8")
    scan.apply_pack(std, pack)
    assert any("still works" in n for n in std.rules["A-MOT-01"]["notes"])


def test_compass_builds_on_shows_rule_status(tmp_path):
    std = scan.load_standard(ROOT)
    c = compass.load_compass(ROOT, [], std)
    scope = {"product": "x", "features": ["chat"], "bands": ["B3"], "claims_declared": [], "not_applicable": []}
    findings = {"level": 2, "findings": [{"rule_id": "CORE-CHT-02", "severity": "REVIEW"}], "human_checks": []}
    doc = tmp_path / "doc.md"
    doc.write_text("# Safety\nReport and block are explained in the tutorial.\n", encoding="utf-8")
    try:
        res = compass.run([doc], c, std, scope, findings)
    except (KeyError, TypeError):
        scope = compass.resolve_scope({"features": ["chat"], "age_bands": ["B3"]}, None, None, None, "x")
        res = compass.run([doc], c, std, scope, findings)
    trn06 = next(t for t in res["targets"] if t["id"] == "TRN-06")
    st = {b["rule"]: b["status"] for b in trn06["builds_on"]}
    assert st["CORE-CHT-02"] == "1 open finding" and st["CORE-CHT-11"] == "no open findings"
    json.dumps(res, default=str)
