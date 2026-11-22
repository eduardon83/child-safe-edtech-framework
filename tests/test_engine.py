"""The Safety Framework Engine (engine/sfe) stays in step with CSEF's own tooling."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT / "engine"))

import scan  # noqa: E402
from sfe import catalogue, config, patterns, scanner  # noqa: E402

CFG = config.load(ROOT / "framework" / "framework.yaml")
EXAMPLES = [ROOT / "examples" / "compliant-game", ROOT / "examples" / "noncompliant-game"]


def test_config_matches_scan_constants():
    assert CFG.profiles == scan.PROFILES
    assert list(CFG.dimension_values) == scan.BANDS
    assert CFG.dimension_values == scan.BAND_AGES
    assert CFG.levels == scan.LEVEL_NAMES
    assert CFG.feature_groups == scan.FEATURE_GROUPS
    assert CFG.manifest_names == scan.MANIFEST_NAMES
    assert patterns.SKIP_DIRS == scan.SKIP_DIRS and patterns.SOURCE_EXT == scan.SOURCE_EXT
    assert patterns.SKIP_FILES == scan.SKIP_FILES


def test_patterns_match_scan_on_examples():
    std = scan.load_standard(ROOT)
    ign = patterns.Ignore(CFG.ignore_token, scan.ALIASES)
    for repo in EXAMPLES:
        assert sorted(map(str, patterns.iter_files(repo, CFG.manifest_names))) == sorted(map(str, scan.iter_files(repo)))
        assert patterns.collect_dependencies(repo) == scan.collect_dependencies(repo)
        cache = []
        for p in scan.iter_files(repo):
            t = scan.read_text(p)
            if t is not None:
                cache.append((str(p.relative_to(repo)), t.splitlines(), t))
        for r in std.rules.values():
            for p in (r.get("detection") or {}).get("patterns", []) or []:
                if p["type"] == "regex":
                    assert patterns.regex_findings(r, p, cache, repo, ign) == scan.regex_findings(r, p, cache, repo), r["id"]


def test_engine_validation_reports_problems():
    errs = []
    bad = {"id": "core-x-1", "title": "x", "level": "MAY", "tier": 4, "profiles": ["Z"], "age_bands": ["B9"],
           "requirement": "", "rationale": "", "improvement": "", "effort": "none", "sources": ["NOPE"],
           "detection": {"method": "magic", "patterns": [{"type": "regex", "pattern": "("}]}}
    catalogue.validate_rule(CFG, bad, {}, "test", errs.append)
    text = " ".join(errs)
    for needle in ("PREFIX-AREA-NN", "MUST or SHOULD", "tier must", "unknown profile", "unknown age band",
                   "effort must", "unknown source", "detection.method", "bad regex"):
        assert needle in text, needle


def test_generic_scanner_runs_on_csef_rules():
    std = scan.load_standard(ROOT)
    res = scanner.run(CFG, EXAMPLES[1], list(std.rules.values()), {"profiles": ["core", "A"], "features": ["chat"]}, 1,
                      manifest_checks={n: (lambda m, r, p: []) for n in scan.MANIFEST_CHECKS},
                      ignore=patterns.Ignore(CFG.ignore_token, scan.ALIASES))
    assert res["rules_in_scope"] and res["counts"]["BLOCK"] + res["counts"]["REVIEW"] > 0
    md = scanner.render_markdown(CFG, res, std.sources, "noncompliant example")
    assert md.startswith("# CSEF report")
