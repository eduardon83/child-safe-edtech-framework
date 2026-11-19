"""Tests for v0.14: learning data rules, event checks, open evidence feeds and the description-only scan."""
import json
import shutil
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
import evidence  # noqa: E402
import scan  # noqa: E402

GOOD = ROOT / "examples" / "compliant-game"
BAD = ROOT / "examples" / "noncompliant-game"
SAMPLE = ROOT / "examples" / "evidence-feed"
CAT = GOOD / "docs" / "event-catalogue.yaml"
NEW = ["CORE-DAT-19", "CORE-DAT-20", "CORE-DAT-21", "CORE-DAT-22", "CORE-DAT-23", "CORE-DAT-24", "CORE-DAT-25"]


def run(repo, level=2, description_only=False):
    std = scan.load_standard(ROOT)
    m = scan.load_yaml(repo / "csef.yaml")
    return scan.scan(repo, std, m, level, description_only=description_only)


def ids(res, sev=None):
    return {f.rule_id for f in res["findings"] if sev is None or f.severity in sev}


def events():
    return evidence.read_events(SAMPLE / "events.tsv")


def test_rules_and_sources_present():
    std = scan.load_standard(ROOT)
    for rid in NEW:
        assert rid in std.rules, rid
    for sid in ("EDPB-PSEUDO", "CJEU-SRB", "EDPB-ART53", "OMNIBUS-DATA", "R-OGD2024", "R-OGD-EDS"):
        assert sid in std.sources, sid
    assert std.rules["CORE-DAT-23"]["level"] == "SHOULD"


def test_good_example_passes_learning_data_rules():
    res = run(GOOD)
    assert not ids(res) & set(NEW)


def test_bad_example_hits_each_learning_data_rule():
    res = run(BAD)
    hit = ids(res)
    for rid in NEW:
        assert rid in hit, rid
    blocks = ids(res, {"BLOCK"})
    assert {"CORE-DAT-20", "CORE-DAT-22", "CORE-DAT-24", "CORE-DAT-25"} <= blocks


def test_undeclared_event_in_code(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(GOOD, repo)
    (repo / "src" / "log.ts").write_text('logEvent("unit_start", {unit: "lvl1"});\nlogEvent("secret_bonus", {});\n', encoding="utf-8")
    res = run(repo)
    msgs = [f.evidence for f in res["findings"] if f.rule_id == "CORE-DAT-19"]
    assert any("secret_bonus" in (m or "") for m in msgs)
    assert not any("'unit_start'" in (m or "") for m in msgs)


def test_no_data_collection_block_is_flagged(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(GOOD, repo)
    m = yaml.safe_load((repo / "csef.yaml").read_text(encoding="utf-8"))
    m.pop("data_collection")
    (repo / "csef.yaml").write_text(yaml.safe_dump(m, sort_keys=False), encoding="utf-8")
    assert "CORE-DAT-19" in ids(run(repo))
    m["data_collection"] = {"event_standard": "none"}
    (repo / "csef.yaml").write_text(yaml.safe_dump(m, sort_keys=False), encoding="utf-8")
    assert not ids(run(repo)) & set(NEW)


def test_description_only_skips_code():
    full = run(BAD)
    desc = run(BAD, description_only=True)
    assert desc["mode"] == "description"
    assert any(f.path and f.path.startswith("src/") for f in full["findings"])
    assert not any(f.path and f.path.startswith("src/") for f in desc["findings"])
    assert "CORE-DAT-21" in desc["code_rules_not_checked"]
    assert "CORE-DAT-24" in ids(desc)


def test_sample_events_are_clean():
    cols, evs = events()
    res = evidence.check_events(cols, evs, evidence.load_yaml(CAT))
    assert res["counts"]["BLOCK"] == 0 and res["counts"]["REVIEW"] == 0
    assert res["classes"] == 6 and res["players"] == 60
    assert res["version_branches"] == ["study"]


def test_bad_events_are_caught():
    cols, evs = events()
    cols = cols + ["ip"]
    bad = [dict(e) for e in evs[:30]]
    bad[0]["event_name"] = "secret_bonus"
    bad[1]["event_data"] = {"unit": "lvl1", "note": "my name is Ana and I live in Porto near the school"}
    bad[2]["player_metadata"] = {"age_band": "B2", "gender": "f"}
    bad[3]["player_id"] = "a" * 64
    bad[4]["event_data"] = {"device": "tablet", "contact": "ana@example.org"}
    res = evidence.check_events(cols, bad, evidence.load_yaml(CAT))
    text = json.dumps(res["issues"])
    for needle in ("'ip'", "secret_bonus", "free text", "gender", "hashes", "email"):
        assert needle in text, needle
    assert res["counts"]["BLOCK"] >= 5


def test_feed_thresholds_and_suppression():
    cols, evs = events()
    feed = evidence.build_feed(evs, evidence.load_yaml(CAT), {"collected_under": "own_study", "game": "Garden of Numbers"})
    rows = feed["features"]["rows"]
    units = {r["unit"] for r in rows}
    assert {"Whole game", "Level 1", "Level 4"} <= units
    assert "Level 5" not in units                          # reached by too few players: left out
    assert any(s["unit"] == "lvl5" for s in feed["features"]["suppressed"])
    for r in rows:
        assert r["players"] >= 10 and r["classes"] >= 3 and r["players"] % 5 == 0
    assert feed["files"]["population.tsv"].splitlines()[0].split("\t") == evidence.COLUMNS
    assert {r["feature"] for r in rows} >= {"EV-TIME", "EV-DONE", "EV-STUCK", "EV-HELP", "EV-GAIN", "EV-ACCESS", "EV-STOP", "EV-MODE", "EV-DEVICE", "CONTEXT"}
    gain = [r for r in rows if r["feature"] == "EV-GAIN"]
    assert {r["stat"] for r in gain} == {"pre", "post", "change", "effect_size"} and all(r["instrument"] for r in gain)
    tsv = feed["files"]["population.tsv"]
    for word in ("player_id", "session_id", "timestamp", "retention"):
        assert word not in tsv
    meta = json.loads(feed["files"]["META.json"])
    assert evidence.PERIOD_RX.match(meta["period"]) and meta["ontology"] == "csef-evidence-0.1"
    assert evidence.check_feed(feed["files"])["ok"]


def test_feed_respects_higher_thresholds():
    cols, evs = events()
    feed = evidence.build_feed(evs, evidence.load_yaml(CAT), {"collected_under": "own_study", "min_players": 25})
    assert "Level 4" not in {r["unit"] for r in feed["features"]["rows"]}
    lower = evidence.build_feed(evs, evidence.load_yaml(CAT), {"collected_under": "own_study", "min_players": 2, "min_classes": 1})
    assert lower["meta"]["thresholds"]["min_players"] == 10 and lower["meta"]["thresholds"]["min_classes"] == 3


def test_check_feed_catches_tampering_and_bad_metrics():
    files = evidence.read_feed(SAMPLE / "feed")
    assert evidence.check_feed(files)["ok"]
    t = dict(files)
    t["population.tsv"] = files["population.tsv"].replace("\t60\t6\t", "\t5\t1\t", 1)
    res = evidence.check_feed(t)
    assert not res["ok"] and any("SHA-256" in i["message"] for i in res["issues"])
    assert any("below the thresholds" in i["message"] for i in res["issues"])
    m = json.loads(files["META.json"])
    m["d7_retention"] = 0.4
    t2 = dict(files, **{"META.json": json.dumps(m)})
    t2.pop("MANIFEST.json")
    res2 = evidence.check_feed(t2)
    assert any("engagement" in i["message"] for i in res2["issues"]) and not res2["ok"]


def test_committed_feed_matches_sample():
    cols, evs = events()
    meta = json.loads((SAMPLE / "feed" / "META.json").read_text(encoding="utf-8"))
    feed = evidence.build_feed(evs, evidence.load_yaml(CAT), {
        "game": meta["game"]["name"], "url": meta["game"]["url"], "maker": meta["maker"], "maker_url": meta["maker_url"],
        "collected_under": meta["collected_under"], "approval": meta["approval"], "instrument": "Fractions check, 10 items",
        "languages": meta["languages"], "class_countries": evidence.read_class_countries(SAMPLE / "class-countries.csv")})
    for name, text in feed["files"].items():
        assert (SAMPLE / "feed" / name).read_text(encoding="utf-8") == text, name


def test_cli_round_trip(tmp_path):
    out = tmp_path / "feed"
    code = evidence.main(["build-feed", "--events", str(SAMPLE / "events.tsv"), "--catalogue", str(CAT),
                          "--collected-under", "processor_for_school", "--out-dir", str(out), "--zip"])
    assert code == 0 and (tmp_path / "feed.zip").exists()
    with zipfile.ZipFile(tmp_path / "feed.zip") as zf:
        assert "feed/population.tsv" in zf.namelist()
    assert evidence.main(["check-feed", "--feed", str(tmp_path / "feed.zip"), "--out-dir", str(tmp_path / "chk")]) == 0
    assert (tmp_path / "chk" / "feed-check.html").exists()
    assert evidence.main(["check-events", "--events", str(SAMPLE / "events.tsv"), "--catalogue", str(CAT),
                          "--out-dir", str(tmp_path / "ev")]) == 0


# --------------------------------------------------------------------------- Workbench (v0.14)
import workbench  # noqa: E402


def test_workbench_form_round_trip():
    text = (GOOD / "csef.yaml").read_text(encoding="utf-8")
    form = workbench.manifest_to_form(text)
    assert form["product"].startswith("Garden of Numbers") and form["profiles"] == ["A"] and form["logs_events"] == "ogd-0.1"
    out = yaml.safe_load(workbench.form_to_manifest(text, form))
    m = yaml.safe_load(text)
    for k in ("product", "profiles", "age_bands", "third_parties", "retention", "metadata", "serious_game", "data_collection"):
        assert out.get(k) == m.get(k), k
    form["features"] = ["accounts", "chat"]
    form["product"] = "New name"
    out2 = yaml.safe_load(workbench.form_to_manifest(text, form))
    assert out2["features"] == ["accounts", "chat"] and out2["product"] == "New name"
    assert workbench.check_form("product: x") and not workbench.check_form(text)


def test_workbench_runs_every_tool(tmp_path):
    work = tmp_path / "work"
    for k, v in json.loads(workbench.example_bundle()).items():
        (work / k).parent.mkdir(parents=True, exist_ok=True)
        (work / k).write_text(v, encoding="utf-8")
    feed = tmp_path / "feed.zip"
    evidence.main(["build-feed", "--events", str(work / "data/events.tsv"), "--catalogue", str(work / "docs/event-catalogue.yaml"),
                   "--collected-under", "own_study", "--out-dir", str(tmp_path / "feed"), "--zip"])
    res = workbench.run(work, workbench.TOOLS, tmp_path / "out",
                        {"coc": str(work / "coc/example-code.md"), "events": str(work / "data/events.tsv"), "feed": str(feed)})
    by = {r["tool"]: r for r in res["results"]}
    assert set(by) == set(workbench.TOOLS)
    for t, r in by.items():
        assert r["ok"], (t, r["note"], r["log"][-500:])
        assert r["summary"], t
    d = json.loads((tmp_path / "out" / "describe" / "findings.json").read_text(encoding="utf-8"))
    assert d["mode"] == "description" and d["code_rules_not_checked"]
    assert not any(f["path"] and f["path"].startswith("src/") for f in d["findings"])
    assert Path(res["zip"]).exists()


def test_workbench_explains_missing_inputs(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    res = workbench.run(work, ["describe", "compass", "coc", "events", "feedcheck"], tmp_path / "out")
    assert all(not r["ok"] and r["note"] for r in res["results"])


def test_site_pages_are_built():
    for p in ("docs/workbench/index.html", "docs/workbench/csef-bundle.json", "docs/workbench/example.json",
              "docs/learning-data/index.html", "docs/learning-data/tiers.svg"):
        assert (ROOT / p).exists(), p
    b = json.loads((ROOT / "docs/workbench/csef-bundle.json").read_text(encoding="utf-8"))
    for f in ("tooling/workbench.py", "tooling/evidence.py", "framework/data/profile.yaml", "framework/rules.yaml"):
        assert f in b["files"], f
    guide = (ROOT / "docs/learning-data/index.html").read_text(encoding="utf-8")
    assert "csef-evidence-0.1" in guide and 'src="tiers.svg"' in guide


def test_feed_breaks_down_by_country_only_when_large_enough():
    cols, evs = events()
    cc = evidence.read_class_countries(SAMPLE / "class-countries.csv")
    feed = evidence.build_feed(evs, evidence.load_yaml(CAT), {"collected_under": "own_study", "class_countries": cc})
    rows = feed["features"]["rows"]
    assert {r["country"] for r in rows} == {"all", "PT", "ES"}
    assert feed["meta"]["countries"] == ["ES", "PT"]
    one = {k: ("PT" if i < 5 else "ES") for i, k in enumerate(cc)}           # ES left with one class
    rows2 = evidence.build_feed(evs, evidence.load_yaml(CAT), {"collected_under": "own_study", "class_countries": one})["features"]["rows"]
    assert "ES" not in {r["country"] for r in rows2}


def test_check_feed_reads_both_manifest_shapes():
    files = evidence.read_feed(SAMPLE / "feed")
    man = json.loads(files["MANIFEST.json"])
    assert isinstance(man["files"], list)
    files2 = dict(files, **{"MANIFEST.json": json.dumps({"files": {e["path"]: e["sha256"] for e in man["files"]}})})
    assert evidence.check_feed(files2)["ok"]
