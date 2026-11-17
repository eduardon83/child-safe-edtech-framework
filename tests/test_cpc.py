"""Tests for v0.12: CPC Network principles on in-game purchases."""
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
import scan  # noqa: E402

GOOD = ROOT / "examples" / "compliant-game"
NEW = {"CORE-COM-09", "CORE-COM-10"}


def make_repo(tmp_path, features=("accounts",), files=None):
    repo = tmp_path / "repo"
    shutil.copytree(GOOD, repo)
    m = yaml.safe_load((repo / "csef.yaml").read_text(encoding="utf-8"))
    m["features"] = list(features)
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
    return scan.scan(repo, std, m, level)


def active(res):
    return {h["rule_id"] for h in res["human_checks"]} | {f.rule_id for f in res["findings"]}


def test_sources_and_tiers():
    std = scan.load_standard(ROOT)
    for rid in NEW:
        r = std.rules[rid]
        assert r["level"] == "MUST" and r["tier"] == 1 and r["features"] == ["purchases"]
        assert "CPC-VC" in r["sources"]
    assert {"CPC-VC", "CPC-JS", "CRD"} <= set(std.rules["A-ECO-03"]["sources"])
    assert "B" in std.rules["A-ECO-03"]["profiles"]
    for rid in ("CORE-COM-03", "CORE-COM-04", "A-ECO-01"):
        assert "CPC-JS" in std.rules[rid]["sources"]


def test_new_rules_only_with_purchases(tmp_path):
    assert not NEW & active(run(make_repo(tmp_path)))
    assert NEW <= active(run(make_repo(tmp_path / "b", features=("accounts", "purchases"))))


def test_refund_and_unilateral_terms_patterns(tmp_path):
    files = {"src/i18n/en.json": '{"shop.footer": "All sales are final."}\n',
             "public/terms.html": "<p>We reserve the right to change or remove virtual currency at any time.</p>\n"}
    res = run(make_repo(tmp_path, features=("accounts", "purchases"), files=files))
    paths = {(f.rule_id, f.path) for f in res["findings"]}
    assert ("CORE-COM-09", "src/i18n/en.json") in paths
    assert ("CORE-COM-10", "public/terms.html") in paths
