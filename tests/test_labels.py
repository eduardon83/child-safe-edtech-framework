"""Tests for v0.13: serious-game pre-check, metadata export and label package."""
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
import metadata  # noqa: E402
import precheck  # noqa: E402
import scan  # noqa: E402

GOOD = ROOT / "examples" / "compliant-game"
BAD = ROOT / "examples" / "noncompliant-game"


def copy_repo(tmp_path, edit=None):
    repo = tmp_path / "repo"
    shutil.copytree(GOOD, repo)
    if edit:
        m = yaml.safe_load((repo / "csef.yaml").read_text(encoding="utf-8"))
        edit(m)
        (repo / "csef.yaml").write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return repo


def by_id(model):
    return {c["id"]: c for c in model["criteria"]}


def test_criteria_map_shape():
    crit = precheck.load_criteria(ROOT)["criteria"]
    assert len(crit) == 22
    assert Counter(c["coverage"] for c in crit) == {"partial": 10, "covered": 5, "declaration": 5, "tension": 2}
    assert all(c.get("csef_note") for c in crit if c["coverage"] == "tension")


def test_precheck_statuses_on_good_example():
    m, _ = precheck.run(GOOD, ROOT)
    c = by_id(m)
    assert c["SG-03"]["status"] == "ready"          # statement with evidence that exists
    assert c["SG-02"]["status"] == "missing"        # declaration required, none given
    assert c["SG-06"]["status"] == "ready"          # CSEF rules in scope, no findings
    assert c["SG-01"]["status"] == "partial" and any("Compass not run" in r for r in c["SG-01"]["reasons"])
    compass = {"targets": [{"id": "EDU-01", "level": 2}, {"id": "EDU-03", "level": 1}]}
    std = scan.load_standard(ROOT)
    findings = precheck.scan_dict(GOOD, ROOT, scan.load_yaml(GOOD / "csef.yaml"), None)
    m2 = precheck.assess(GOOD, ROOT, scan.load_yaml(GOOD / "csef.yaml"), findings, compass)
    c2 = by_id(m2)
    assert c2["SG-01"]["status"] == "ready"
    assert c2["SG-07"]["status"] == "missing" and "EDU-03 at level 1" in c2["SG-07"]["reasons"][0]
    assert std.version == m2["tool"]["version"]


def test_precheck_flags_missing_evidence_and_csef_issues(tmp_path):
    def edit(m):
        m["serious_game"]["claims"]["SG-12"] = {"statement": "Choices change the garden.", "evidence": ["docs/nope.md"]}
    m, _ = precheck.run(copy_repo(tmp_path, edit), ROOT)
    assert by_id(m)["SG-12"]["status"] == "partial"
    assert "evidence not found: docs/nope.md" in by_id(m)["SG-12"]["reasons"]
    bad, _ = precheck.run(BAD, ROOT)
    assert by_id(bad)["SG-11"]["status"] == "issue"
    md = precheck.render_md(bad)
    assert "not a quality label" in md and "For children, CSEF applies" in md


def test_sgmdf_export_complete_and_derived():
    man = scan.load_yaml(GOOD / "csef.yaml")
    doc, notes = metadata.build_sgmdf(man)
    assert metadata.validate_sgmdf(doc) == []
    use = doc["useInfo"]
    assert {"targetUserGroup": "players - pupils, ages 6 to 9"} in use["targetUserGroups"]
    assert "Hosting provider" in use["dataRecordingTransfer"] and "processor" in use["dataRecordingTransfer"]
    assert "No purchases inside the product" in doc["distributionInfo"][0]["priceInfo"]
    assert doc["gameInfo"]["gameMode"] == ["single player"]
    assert doc["metadataInfo"]["metadataFormat"]["metadataFormatVersion"] == "DIN SPEC 91380:2018-06"
    root = ET.fromstring(metadata.sgmdf_xml(doc).split("\n", 2)[2])
    assert root.tag == "SG-MD" and root.find("gameInfo/titleInfo/gameID").text == "garden-of-numbers"
    assert len(root.findall("gameInfo/keywordInfo")) == 3
    js = json.loads(metadata.sgmdf_json(doc))
    assert "no official JSON or XML schema" in js["serialisation"]["note"]


def test_sgmdf_reports_missing_core_fields(tmp_path):
    repo = copy_repo(tmp_path, lambda m: m.pop("metadata"))
    doc, _ = metadata.build_sgmdf(scan.load_yaml(repo / "csef.yaml"))
    refs = {p["ref"] for p in metadata.validate_sgmdf(doc)}
    assert {"1.9.1", "2.3.1", "2.5", "3.4", "4.1.1", "5.1.1"} <= refs
    assert "1.1.2" not in refs and "2.8" not in refs  # title and data statement come from csef.yaml


def test_lrmi():
    man = scan.load_yaml(GOOD / "csef.yaml")
    doc, _ = metadata.build_sgmdf(man)
    lr = metadata.build_lrmi(man, doc)
    assert lr["@type"] == ["LearningResource", "VideoGame"]
    assert lr["typicalAgeRange"] == "6-9" and lr["isAccessibleForFree"] is False
    assert lr["teaches"] == ["Pupils aged 6 to 9 understand and compare simple fractions."]
    assert lr["playMode"] == ["https://schema.org/SinglePlayer"]


def test_label_package(tmp_path):
    z, man = metadata.build_package(GOOD, ROOT, tmp_path)
    assert man["sgmdf_core_complete"] and man["precheck_summary"]["ready"] >= 4
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
        top = names[0].split("/")[0]
        for f in man["files"]:
            data = zf.read(f"{top}/{f['path']}")
            assert hashlib.sha256(data).hexdigest() == f["sha256"]
        assert f"{top}/MANIFEST.json" in names and f"{top}/metadata/sg-mdf.xml" in names
        ev = json.loads(zf.read(f"{top}/evidence/index.json"))
        assert {"criterion": "SG-09", "ref": "docs/playtest-summary.md", "found": True} in ev


def test_site_example_links_resolve():
    import re
    page = (ROOT / "docs" / "examples" / "index.html").read_text(encoding="utf-8")
    links = [h for h in re.findall(r'href="([^"]+)"', page) if not re.match(r"^(https?:|#|\.\./)", h)]
    assert len(links) >= 15
    for h in links:
        assert (ROOT / "docs" / "examples" / h).exists(), h
    landing = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "Let's get you started" in landing and 'href="examples/"' in landing and 'href="submit/"' in landing
    assert "Nothing is uploaded or sent" in (ROOT / "docs" / "submit" / "index.html").read_text(encoding="utf-8")
