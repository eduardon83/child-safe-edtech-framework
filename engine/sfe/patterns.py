"""Pattern matching over a code base: files, inline ignores, regex and dependency findings.

Lifted from CSEF tooling/scan.py (v0.14.1). tests/test_engine.py in CSEF keeps the two in step until scan.py
imports this module.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
from pathlib import Path

import yaml

SOURCE_EXT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".html", ".htm", ".css", ".scss", ".less",
    ".py", ".java", ".kt", ".kts", ".swift", ".m", ".dart", ".cs", ".go", ".rb", ".php",
    ".sql", ".json", ".yaml", ".yml", ".xml", ".plist", ".gd", ".lua", ".gradle", ".strings",
    ".po", ".arb", ".properties", ".toml", ".env",
    ".prefab", ".asset", ".unity", ".asmdef", ".tscn", ".tres", ".godot",          # Unity and Godot text assets
    ".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".scala", ".ex", ".exs", ".m", ".mm", ".rules",
}
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".nuxt", "out", "coverage", "vendor",
    "Pods", ".gradle", ".idea", ".vscode", "__pycache__", ".venv", "venv", "env", "Library",
    "Temp", "csef-report", "cses-report", ".csef", ".cses", "Logs", "obj", "UserSettings", "Build", "Builds", ".godot", "target",
}
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Podfile.lock",
    "pubspec.lock", "composer.lock", "Cargo.lock",
}
MAX_FILE_BYTES = 1_000_000


def iter_files(repo: Path, manifest_names=(), skip_dirs=None):
    skip_dirs = SKIP_DIRS if skip_dirs is None else skip_dirs
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            if fn in SKIP_FILES or fn in manifest_names:
                continue
            p = Path(dirpath) / fn
            if p.suffix.lower() not in SOURCE_EXT and fn not in ("Podfile",):
                continue
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield p


def read_text(p: Path):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


class Ignore:
    """Inline ignore comments, for example `csef-ignore: CORE-DAT-01 because ...`."""

    def __init__(self, token: str, aliases: dict | None = None):
        self.rx = re.compile(token + r":\s*([A-Z0-9, -]+?)(?:\s+(?:--|because|reason:)\s*(.*))?$", re.I) if token else None
        self.aliases = aliases or {}

    def check(self, lines, idx, rule_id) -> str | None:
        if not self.rx:
            return None
        for j in (idx, idx - 1):
            if 0 <= j < len(lines):
                m = self.rx.search(lines[j])
                if m and rule_id in [self.aliases.get(x.strip(), x.strip()) for x in m.group(1).split(",")]:
                    return (m.group(2) or "no reason given").strip()
        return None


def compile_pattern(p):
    flags = re.I if "i" in str(p.get("flags", "")) else 0
    return re.compile(p["pattern"], flags | re.M)


def regex_findings(rule, pat, files_cache, repo: Path, ignore: "Ignore | None" = None):
    rx = compile_pattern(pat)
    globs = pat.get("globs")
    out = []
    for rel, lines, text in files_cache:
        if globs and not any(fnmatch.fnmatch(Path(rel).name, g) or fnmatch.fnmatch(rel, g) for g in globs):
            continue
        if not rx.search(text):
            continue
        for i, line in enumerate(lines):
            if rx.search(line):
                out.append((rel, i + 1, line.strip()[:160], (ignore.check(lines, i, rule["id"]) if ignore else None)))
                if len(out) > 25:
                    return out
    return out


def collect_dependencies(repo: Path, skip_dirs=None):
    skip_dirs = SKIP_DIRS if skip_dirs is None else skip_dirs
    deps = {}  # name -> file
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = str(p.relative_to(repo))
            try:
                if fn == "package.json":
                    data = json.loads(p.read_text(encoding="utf-8"))
                    for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                        for name in (data.get(k) or {}):
                            deps.setdefault(name, rel)
                elif fn.startswith("requirements") and fn.endswith(".txt"):
                    for ln in p.read_text(encoding="utf-8").splitlines():
                        m = re.match(r"\s*([A-Za-z0-9_.\-]+)", ln)
                        if m and not ln.strip().startswith("#"):
                            deps.setdefault(m.group(1).lower(), rel)
                elif fn == "pyproject.toml":
                    for m in re.finditer(r'^\s*"?([A-Za-z0-9_.\-]+)\s*(?:[<>=~!\[]|"|\s*=)', p.read_text(encoding="utf-8"), re.M):
                        deps.setdefault(m.group(1).lower(), rel)
                elif fn == "Podfile":
                    for m in re.finditer(r"pod\s+['\"]([^'\"/]+)", p.read_text(encoding="utf-8")):
                        deps.setdefault(m.group(1), rel)
                elif fn.endswith((".gradle", ".gradle.kts")):
                    for m in re.finditer(r"['\"]([a-zA-Z0-9_.\-]+:[a-zA-Z0-9_.\-]+)(?::[^'\"]*)?['\"]", p.read_text(encoding="utf-8")):
                        deps.setdefault(m.group(1), rel)
                elif fn == "manifest.json" and p.parent.name == "Packages":  # Unity Package Manager
                    data = json.loads(p.read_text(encoding="utf-8"))
                    for name in (data.get("dependencies") or {}):
                        deps.setdefault(name, rel)
                elif fn.endswith("Dependencies.xml"):  # Unity External Dependency Manager (Android and iOS SDKs)
                    t = p.read_text(encoding="utf-8")
                    for m in re.finditer(r'androidPackage\s+spec="([^":]+:[^":]+)', t):
                        deps.setdefault(m.group(1), rel)
                    for m in re.finditer(r'iosPod\s+name="([^"]+)"', t):
                        deps.setdefault(m.group(1), rel)
                elif fn == "pom.xml":
                    t = p.read_text(encoding="utf-8")
                    for m in re.finditer(r"<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>", t):
                        deps.setdefault(f"{m.group(1).strip()}:{m.group(2).strip()}", rel)
                elif fn.endswith((".csproj", ".fsproj")) or fn in ("packages.config", "Directory.Packages.props"):
                    for m in re.finditer(r'(?:PackageReference|PackageVersion|package)\s+(?:Include|id)="([^"]+)"', p.read_text(encoding="utf-8"), re.I):
                        deps.setdefault(m.group(1), rel)
                elif fn == "go.mod":
                    for m in re.finditer(r"^\s*(?:require\s+)?([\w.\-]+\.[\w.\-/]+)\s+v[\d.]+", p.read_text(encoding="utf-8"), re.M):
                        deps.setdefault(m.group(1), rel)
                elif fn == "Cargo.toml":
                    t = p.read_text(encoding="utf-8")
                    sec = re.search(r"^\[dependencies\]([\s\S]*?)(^\[|\Z)", t, re.M)
                    for m in re.finditer(r"^\s*([A-Za-z0-9_\-]+)\s*=", sec.group(1) if sec else "", re.M):
                        deps.setdefault(m.group(1), rel)
                elif fn == "composer.json":
                    data = json.loads(p.read_text(encoding="utf-8"))
                    for k in ("require", "require-dev"):
                        for name in (data.get(k) or {}):
                            deps.setdefault(name, rel)
                elif fn == "Gemfile":
                    for m in re.finditer(r"^\s*gem\s+['\"]([^'\"]+)", p.read_text(encoding="utf-8"), re.M):
                        deps.setdefault(m.group(1), rel)
                elif fn == "Package.swift":
                    for m in re.finditer(r'\.package\s*\(\s*(?:name:\s*"[^"]*",\s*)?url:\s*"[^"]*/([^/"]+?)(?:\.git)?"', p.read_text(encoding="utf-8")):
                        deps.setdefault(m.group(1), rel)
                elif fn == "pubspec.yaml":
                    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                    for k in ("dependencies", "dev_dependencies"):
                        for name in (data.get(k) or {}):
                            deps.setdefault(name, rel)
            except (OSError, ValueError, yaml.YAMLError):
                continue
    return deps


def dependency_findings(pat, deps):
    names = pat.get("names", [])
    lower = {k.lower(): (k, v) for k, v in deps.items()}
    hits = []
    for n in names:
        if n.lower() in lower:
            k, f = lower[n.lower()]
            hits.append((f, k))
    return hits
