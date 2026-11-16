"""Tests for several countries and shared infrastructure (CORE-INT): manifest checks and detection."""
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
import scan  # noqa: E402

GOOD = ROOT / "examples" / "compliant-game"


def make_repo(tmp_path, jurisdictions=("EU", "PT"), third_parties=None, extra=None, files=None):
    repo = tmp_path / "repo"
    shutil.copytree(GOOD, repo)
    m = yaml.safe_load((repo / "csef.yaml").read_text(encoding="utf-8"))
    m["jurisdictions"] = list(jurisdictions)
    if third_parties is not None:
        m["third_parties"] = third_parties
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
    return scan.scan(repo, std, m, level)


def evidence(res, rid):
    return " ".join(f.evidence for f in res["findings"] if f.rule_id == rid)


def test_compliant_example_passes_the_new_checks(tmp_path):
    res = run(make_repo(tmp_path))
    found = {f.rule_id for f in res["findings"]}
    assert not found & {"CORE-INT-01", "CORE-INT-04"}, sorted(found)


def test_several_countries_need_a_country_config(tmp_path):
    res = run(make_repo(tmp_path, jurisdictions=("EU", "PT", "ES")))
    assert "country_config" in evidence(res, "CORE-INT-01")
    res = run(make_repo(tmp_path / "b", jurisdictions=("EU", "PT", "ES"), extra={"country_config": "config/countries.yaml"},
                        files={"config/countries.yaml": "PT: {digital_consent_age: 13}\nES: {digital_consent_age: 14}\n"}))
    assert "country_config" not in evidence(res, "CORE-INT-01")


def test_hard_coded_consent_age_is_flagged(tmp_path):
    files = {"src/consent.ts": "export const AGE_OF_CONSENT = 13;\n", "src/cfg.json": '{"digitalConsentAge": 16}\n'}
    res = run(make_repo(tmp_path, files=files))
    paths = {f.path for f in res["findings"] if f.rule_id == "CORE-INT-01"}
    assert {"src/consent.ts", "src/cfg.json"} <= paths, paths


def test_dependencies_need_jurisdiction_and_fallback(tmp_path):
    tps = [
        {"name": "Hosting", "region": "eu-central-1", "jurisdiction": "DE", "critical": True, "dpa_signed": True},
        {"name": "AI model", "region": "eu-west-1", "jurisdiction": "US", "critical": True, "dpa_signed": True},
        {"name": "Email", "region": "eu-west-1", "dpa_signed": True},
        {"name": "Maps", "region": "eu-west-1", "jurisdiction": "US", "critical": True, "fallback": "static maps", "dpa_signed": True},
    ]
    ev = evidence(run(make_repo(tmp_path, third_parties=tps)), "CORE-INT-04")
    assert "'AI model' is established in US" in ev
    assert "'Email' has no `jurisdiction`" in ev
    assert "Hosting" not in ev and "Maps" not in ev
