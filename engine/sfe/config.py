"""Framework configuration: framework/framework.yaml."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    id: str
    short: str
    name: str
    repo: str = ""
    site: str = ""
    levels: dict = field(default_factory=lambda: {1: "Legal baseline", 2: "Forward-compliant", 3: "Best practice"})
    profiles: set = field(default_factory=set)
    profile_names: dict = field(default_factory=dict)
    dimension_key: str = "age_bands"          # the second scope axis of a rule (CSEF: age bands; HDSF: audiences)
    dimension_label: str = "Age bands"
    dimension_values: dict = field(default_factory=dict)   # value -> label
    features: set = field(default_factory=set)
    feature_groups: dict = field(default_factory=dict)
    id_pattern: str = r"^[A-Z]{1,8}-[A-Z0-9]{2,4}-\d{2}$"
    source_types: set = field(default_factory=set)
    tier_min_types: dict = field(default_factory=dict)
    source_required: tuple = ("title", "type", "jurisdiction", "status", "verified")
    manifest_names: list = field(default_factory=list)
    ignore_token: str = ""
    rule_meta_key: str = "rule"
    generator: str = "tooling/build.py"

    @property
    def id_re(self):
        return re.compile(self.id_pattern)

    @property
    def required_fields(self):
        return ["id", "title", "level", "tier", "profiles", self.dimension_key, "requirement", "rationale",
                "improvement", "effort", "sources", "detection"]

    @property
    def feature_names(self):
        return set(self.features) | set(self.feature_groups)


def load(path: Path) -> Config:
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    dim = d.get("dimension", {})
    st = set(d.get("source_types", []))
    tmt = {int(k): (st if v == "all" else set(v)) for k, v in (d.get("tier_min_types") or {}).items()}
    profiles = d.get("profiles", {})
    return Config(
        id=d["id"], short=d["short"], name=d["name"], repo=d.get("repo", ""), site=d.get("site", ""),
        levels={int(k): v for k, v in (d.get("levels") or {1: "Legal baseline", 2: "Forward-compliant", 3: "Best practice"}).items()},
        profiles=set(profiles), profile_names=dict(profiles) if isinstance(profiles, dict) else {},
        dimension_key=dim.get("key", "age_bands"), dimension_label=dim.get("label", "Age bands"),
        dimension_values=dict(dim.get("values", {})),
        features=set(d.get("features", [])), feature_groups=dict(d.get("feature_groups", {})),
        id_pattern=d.get("id_pattern", r"^[A-Z]{1,8}-[A-Z0-9]{2,4}-\d{2}$"),
        source_types=st, tier_min_types=tmt,
        manifest_names=list(d.get("manifest_names", [])), ignore_token=d.get("ignore_token", ""),
        rule_meta_key=d.get("rule_meta_key", "rule"), generator=d.get("generator", "tooling/build.py"),
    )
