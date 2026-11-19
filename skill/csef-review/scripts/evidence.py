#!/usr/bin/env python3
"""CSEF learning data: check event files, build open evidence feeds, check feeds.

Learning games can log what pupils do with the Open Game Data (OGD) event standard. This tool keeps that data
child-safe (framework/08-learning-data.md):

  check-events  an OGD event file (TSV) against the child-safe profile and the product's event catalogue:
                undeclared events and fields, forbidden columns, possible free text, emails, IP addresses,
                player codes that look like hashes, player metadata beyond the allow-list.
  build-feed    an open evidence feed (csef-evidence-0.1) from an event file and its catalogue: group figures
                per unit (time to finish, completion, stuck, help) and for the whole game (learning gain,
                accessibility settings, natural stops, play mode, devices). Every figure has at least
                10 players and 3 classes behind it; smaller cells are removed. Counts are rounded to 5, dates
                to the month. Writes population.tsv, META.json, README.md and MANIFEST.json (and a zip).
  check-feed    a feed (folder or zip) before release, or before a catalogue such as the Play to Learn
                Toolkit shows it: hashes, format, thresholds, forbidden metrics.

  python3 tooling/evidence.py check-events --events events.tsv --catalogue docs/event-catalogue.yaml --out-dir csef-events
  python3 tooling/evidence.py build-feed --events events.tsv --catalogue docs/event-catalogue.yaml \
          --game "Garden of Numbers" --maker "Example Studio" --collected-under processor_for_school --out-dir feed --zip
  python3 tooling/evidence.py check-feed --feed feed --out-dir csef-feed-check

Pre-compliance support, not legal advice. Exit code 1 when a check finds a blocking issue.
Licence: Apache-2.0
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import io
import json
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import brand  # noqa: E402

TOOL = "csef-evidence"
VERSION = "0.14.0"
ONTOLOGY = "csef-evidence-0.1"
PROFILE = "csef-ogd-0.1"
ACTIVE_GAP_S = 60
FEED_FILES = ("population.tsv", "META.json", "README.md")
EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IPV4_RX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PHONE_RX = re.compile(r"\+?\d[\d \-]{8,}\d")
MONTH_RX = re.compile(r"^\d{4}-\d{2}$")


# --------------------------------------------------------------------------- loading
def load_yaml(p: Path):
    return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}


def load_profile(root: Path = ROOT) -> dict:
    return load_yaml(root / "framework" / "data" / "profile.yaml")


def load_ontology(root: Path = ROOT) -> dict:
    return load_yaml(root / "framework" / "data" / "evidence-ontology.yaml")


def norm_col(c: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", c.strip().lower()).strip("_")


def _json(v):
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    v = str(v).strip()
    if not v or v.lower() in ("null", "none"):
        return None
    try:
        return json.loads(v)
    except json.JSONDecodeError:
        return v


def read_events(path: Path | str | None = None, text: str | None = None) -> tuple[list[str], list[dict]]:
    """An OGD event file: tab-separated, one row per event, JSON in event_data, game_state and player_metadata."""
    if text is None:
        text = Path(path).read_text(encoding="utf-8-sig")
    rd = csv.reader(io.StringIO(text), delimiter="\t")
    rows = list(rd)
    if not rows:
        return [], []
    cols = [norm_col(c) for c in rows[0]]
    out = []
    for i, r in enumerate(rows[1:], 2):
        if not any(x.strip() for x in r):
            continue
        d = dict(zip(cols, r))
        d["_row"] = i
        for k in ("event_data", "game_state", "player_metadata"):
            if k in d:
                d[k] = _json(d[k])
        out.append(d)
    return cols, out


def catalogue_index(cat: dict) -> dict:
    """event name -> catalogue entry (events and detectors)."""
    idx = {}
    for e in cat.get("events") or []:
        idx[str(e.get("name"))] = dict(e, _kind="event")
    for e in cat.get("detectors") or []:
        idx[str(e.get("name"))] = dict(e, _kind="detector")
    return idx


def ts(v) -> dt.datetime | None:
    if not v:
        return None
    s = str(v).strip().replace("Z", "+00:00")
    for f in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return dt.datetime.fromisoformat(s) if f is None else dt.datetime.strptime(s, f)
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- check-events
def check_events(cols: list[str], events: list[dict], cat: dict, profile: dict | None = None) -> dict:
    profile = profile or load_profile()
    issues: list[dict] = []

    def add(sev, rule, msg, rows=None):
        issues.append({"severity": sev, "rule": rule, "message": msg, "rows": (rows or [])[:5], "count": len(rows or [])})

    known = {f["name"] for f in profile["fields"]}
    forbidden = {f["name"]: f["why"] for f in profile.get("forbidden_columns", [])}
    for c in cols:
        if c in forbidden:
            add("BLOCK", "CORE-DAT-04", f"Column '{c}' must never be in an event file: {forbidden[c]}")
        elif c not in known and c != "_row":
            add("REVIEW", "CORE-DAT-19", f"Column '{c}' is not an OGD field. Check it holds no personal data, or drop it.")
    for need in ("game_id", "session_id", "event_name", "event_data"):
        if need not in cols:
            add("BLOCK", "CORE-DAT-19", f"Required OGD column '{need}' is missing.")

    idx = catalogue_index(cat)
    profile_meta = set(next(f for f in profile["fields"] if f["name"] == "player_metadata")["allowed_keys"])
    allowed_meta = profile_meta & set(cat.get("player_metadata") or ["age_band"])
    allowed_state = set(cat.get("game_state") or [])
    vc = profile.get("value_checks", {})
    hash_rx = re.compile(vc.get("hash_like", r"^[0-9a-f]{64}$"))
    min_free = int(vc.get("free_text_min_chars", 40))

    undeclared, bad_keys, bad_types = defaultdict(list), defaultdict(list), defaultdict(list)
    free, pii, meta_keys, state_keys, hashes, src_game = [], [], defaultdict(list), defaultdict(list), [], []
    for ev in events:
        name = str(ev.get("event_name", ""))
        entry = idx.get(name)
        row = ev["_row"]
        if not entry:
            undeclared[name].append(row)
        else:
            fields = entry.get("fields") or {}
            data = ev.get("event_data") if isinstance(ev.get("event_data"), dict) else {}
            for k, v in data.items():
                if k not in fields:
                    bad_keys[f"{name}.{k}"].append(row)
                    continue
                spec = fields[k] or {}
                t = spec.get("type")
                ok = (t == "boolean" and isinstance(v, bool)) or (t == "integer" and isinstance(v, int) and not isinstance(v, bool)) or \
                     (t == "number" and isinstance(v, (int, float)) and not isinstance(v, bool)) or \
                     (t == "enum" and v in (spec.get("values") or [])) or (t == "id" and isinstance(v, (str, int)) and len(str(v)) <= 40) or t is None
                if not ok:
                    bad_types[f"{name}.{k}"].append(row)
            if entry["_kind"] == "detector" and str(ev.get("event_source", "")).upper() == "GAME":
                src_game.append(row)
        for k in ("event_data", "game_state"):
            v = ev.get(k)
            if isinstance(v, dict):
                for x in v.values():
                    if isinstance(x, str) and len(x) >= min_free and " " in x:
                        free.append(row)
        for k, v in ev.items():
            if k.startswith("_"):
                continue
            s = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v or "")
            if EMAIL_RX.search(s) or (k not in ("timestamp", "offset", "game_version", "source_hash") and IPV4_RX.search(s)):
                pii.append(row)
                break
        pm = ev.get("player_metadata")
        if isinstance(pm, dict):
            for k in pm:
                if k not in allowed_meta:
                    meta_keys[k].append(row)
        gs = ev.get("game_state")
        if isinstance(gs, dict) and allowed_state:
            for k in gs:
                if k not in allowed_state:
                    state_keys[k].append(row)
        pid = str(ev.get("player_id") or "")
        if pid and hash_rx.match(pid.lower()):
            hashes.append(row)

    for name, rows in sorted(undeclared.items()):
        add("BLOCK", "CORE-DAT-19", f"Event '{name}' is not declared in the event catalogue.", rows)
    for key, rows in sorted(bad_keys.items()):
        add("BLOCK", "CORE-DAT-19", f"Field '{key}' is not declared in the event catalogue.", rows)
    for key, rows in sorted(bad_types.items()):
        add("REVIEW", "CORE-DAT-19", f"Field '{key}' does not match its declared type or values.", rows)
    if free:
        add("BLOCK", "CORE-DAT-04", f"Values that look like free text ({min_free}+ characters with spaces). Children's text must not be logged.", free)
    if pii:
        add("BLOCK", "CORE-DAT-04", "Values that look like an email or IP address.", pii)
    for k, rows in sorted(meta_keys.items()):
        add("BLOCK", "CORE-DAT-22", f"player_metadata key '{k}' is not allowed: only the age band and declared settings.", rows)
    for k, rows in sorted(state_keys.items()):
        add("REVIEW", "CORE-DAT-19", f"game_state key '{k}' is not declared in the catalogue.", rows)
    if hashes:
        add("REVIEW", "CORE-DAT-20", "Player codes look like hashes (32, 40 or 64 hex characters). If they hash an email, name or "
                                     "account id, replace them with random codes.", hashes)
    if src_game:
        add("REVIEW", "CORE-DAT-22", "Detector events with event_source GAME: detectors must name themselves as the source.", src_game)
    if "timestamp" in cols and any(isinstance(ev.get("timestamp"), str) and ev.get("timestamp") and ts(ev["timestamp"]) is None for ev in events):
        add("REVIEW", "CORE-DAT-19", "Some timestamps cannot be read (use ISO 8601 or 'YYYY-MM-DD HH:MM:SS', UTC).")
    branches = sorted({str(ev.get("game_version", "")).split("-", 1)[1] for ev in events if "-" in str(ev.get("game_version", ""))})
    order = {"BLOCK": 0, "REVIEW": 1, "WARN": 2}
    issues.sort(key=lambda x: order.get(x["severity"], 9))
    return {
        "kind": "events", "tool": f"{TOOL} {VERSION}", "profile": PROFILE,
        "game_id": next((ev.get("game_id") for ev in events if ev.get("game_id")), cat.get("game_id")),
        "events": len(events), "event_types": len({ev.get("event_name") for ev in events}),
        "players": len({ev.get("player_id") for ev in events if ev.get("player_id")}),
        "sessions": len({ev.get("session_id") for ev in events if ev.get("session_id")}),
        "classes": len({ev.get("instance_id") for ev in events if ev.get("instance_id")}),
        "version_branches": branches,
        "issues": issues,
        "counts": {s: sum(1 for i in issues if i["severity"] == s) for s in ("BLOCK", "REVIEW", "WARN")},
    }


# --------------------------------------------------------------------------- build-feed
def r5(n: int, step: int = 5) -> int:
    return int(step * round(n / step))


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return float("nan")
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def _unit(ev) -> str | None:
    for k in ("event_data", "game_state"):
        v = ev.get(k)
        if isinstance(v, dict) and v.get("unit") not in (None, ""):
            return str(v["unit"])
    return None


def compute_features(events: list[dict], cat: dict, ont: dict, min_players: int, min_classes: int, round_to: int = 5) -> dict:
    """Population features per unit and for the whole game, with suppression of small cells."""
    idx = catalogue_index(cat)
    role = lambda ev: (idx.get(str(ev.get("event_name"))) or {}).get("evidence_role")  # noqa: E731
    by_session = defaultdict(list)
    for ev in events:
        by_session[ev.get("session_id")].append(ev)
    for evs in by_session.values():
        evs.sort(key=lambda e: (int(e.get("session_sequence_index") or 0), str(e.get("timestamp") or "")))

    player_class = {}
    for ev in events:
        if ev.get("player_id"):
            player_class.setdefault(ev["player_id"], ev.get("instance_id") or "?")

    started, finished, helped, stuck = defaultdict(set), defaultdict(dict), defaultdict(set), defaultdict(set)
    settings, gain_pre, gain_post = defaultdict(set), {}, {}
    sess_mode, sess_device, sess_stop = {}, {}, {}
    months = set()
    for sid, evs in by_session.items():
        open_units: dict[str, list] = {}
        prev_t = None
        for ev in evs:
            t = ts(ev.get("timestamp"))
            if t:
                months.add(t.strftime("%Y-%m"))
            gap = min((t - prev_t).total_seconds(), ACTIVE_GAP_S) if (t and prev_t) else 0.0
            prev_t = t or prev_t
            for u in open_units:
                open_units[u][1] += max(gap, 0.0)
            pid, r, u = ev.get("player_id"), role(ev), _unit(ev)
            data = ev.get("event_data") if isinstance(ev.get("event_data"), dict) else {}
            gs = ev.get("game_state") if isinstance(ev.get("game_state"), dict) else {}
            if gs.get("mode") and sid not in sess_mode:
                sess_mode[sid] = str(gs["mode"])
            if not pid:
                continue
            if r == "unit_start" and u:
                started[u].add(pid)
                open_units.setdefault(u, [pid, 0.0])
            elif r == "unit_complete" and u:
                started[u].add(pid)
                if u in open_units and pid not in finished[u]:
                    finished[u][pid] = open_units[u][1] / 60.0
                open_units.pop(u, None)
            elif r == "help" and u:
                helped[u].add(pid)
            elif r == "stuck" and u and str(ev.get("event_source", "")).upper() != "GAME":
                stuck[u].add(pid)
            elif r == "setting" and data.get("on") is True and data.get("setting"):
                settings[str(data["setting"])].add(pid)
            elif r == "assessment" and isinstance(data.get("score"), (int, float)) and data.get("max"):
                (gain_pre if data.get("phase") == "pre" else gain_post)[pid] = float(data["score"]) / float(data["max"])
            elif r == "mode" and data.get("mode"):
                sess_mode[sid] = str(data["mode"])
            elif r == "session_start" and data.get("device"):
                sess_device[sid] = str(data["device"])
            elif r == "session_end" and isinstance(data.get("natural_stop"), bool):
                sess_stop[sid] = data["natural_stop"]

    def classes(players) -> int:
        return len({player_class.get(p, "?") for p in players} - {"?"})

    def ok(players) -> bool:
        return len(players) >= min_players and classes(players) >= min_classes

    sess_player = {sid: next((e.get("player_id") for e in evs if e.get("player_id")), None) for sid, evs in by_session.items()}
    all_players = set(player_class)
    rows, suppressed = [], []
    units = sorted(started, key=lambda u: (re.sub(r"\d+", "", u), int(re.sub(r"\D", "", u) or 0), u))
    for u in units:
        ps = started[u]
        if not ok(ps):
            suppressed.append({"unit_id": u, "reason": "fewer than the minimum players or classes"})
            continue
        row = {"population_id": "dataset", "unit_id": u, "players": r5(len(ps), round_to), "classes": classes(ps)}
        fin = finished[u]
        if ok(set(fin)):
            mins = list(fin.values())
            row.update({"ev_time_p25_min": round(pct(mins, .25), 1), "ev_time_p50_min": round(pct(mins, .5), 1),
                        "ev_time_p75_min": round(pct(mins, .75), 1)})
        else:
            suppressed.append({"unit_id": u, "feature": "EV-TIME", "reason": "fewer finishers than the minimum"})
        row["ev_done_share"] = round(len(set(fin) & ps) / len(ps), 2)
        row["ev_help_share"] = round(len(helped[u] & ps) / len(ps), 2)
        if any(d.get("evidence_role") == "stuck" for d in cat.get("detectors") or []):
            row["ev_stuck_share"] = round(len(stuck[u] & ps) / len(ps), 2)
        rows.append(row)

    whole = {"population_id": "dataset", "unit_id": "*", "players": r5(len(all_players), round_to), "classes": classes(all_players)}
    if ok(all_players):
        both = set(gain_pre) & set(gain_post)
        if ok(both):
            whole["ev_gain_mean"] = round(sum(gain_post[p] - gain_pre[p] for p in both) / len(both), 2)
            whole["ev_gain_n"] = r5(len(both), round_to)
        elif gain_pre or gain_post:
            suppressed.append({"unit_id": "*", "feature": "EV-GAIN", "reason": "fewer players with both checks than the minimum"})
        for s, ps in sorted(settings.items()):
            whole[f"ev_access_{norm_col(s)}"] = round(len(ps) / len(all_players), 2)
        stops = {sid: v for sid, v in sess_stop.items() if sess_player.get(sid)}
        if stops and ok({sess_player[s] for s in stops}):
            whole["ev_stop_share"] = round(sum(1 for v in stops.values() if v) / len(stops), 2)
        for key, src in (("mode", sess_mode), ("device", sess_device)):
            have = {sid: v for sid, v in src.items() if sess_player.get(sid)}
            if have and ok({sess_player[s] for s in have}):
                for val in sorted(set(have.values())):
                    whole[f"ev_{key}_{norm_col(val)}"] = round(sum(1 for v in have.values() if v == val) / len(have), 2)
        rows.insert(0, whole)
    else:
        suppressed.append({"unit_id": "*", "reason": "fewer than the minimum players or classes in the whole dataset"})

    age = defaultdict(set)
    for ev in events:
        pm = ev.get("player_metadata")
        if isinstance(pm, dict) and pm.get("age_band") and ev.get("player_id"):
            age[str(pm["age_band"])].add(ev["player_id"])
    sm = sorted(months)
    return {
        "rows": rows, "suppressed": suppressed,
        "players": r5(len(all_players), round_to), "sessions": r5(len(by_session), round_to),
        "classes": classes(all_players),
        "start": sm[0] if sm else None, "end": sm[-1] if sm else None,
        "age_bands": sorted(b for b, ps in age.items() if ok(ps)),
        "units": [[r["unit_id"], r["players"]] for r in rows if r["unit_id"] != "*"],
    }


def feed_columns(rows: list[dict], ont: dict) -> list[str]:
    cols = list(ont.get("context_columns") or ["population_id", "unit_id", "players", "classes"])
    for f in ont["features"]:
        for c in f.get("columns", []):
            if any(c in r for r in rows):
                cols.append(c)
        if f.get("columns_prefix"):
            cols += sorted({k for r in rows for k in r if k.startswith(f["columns_prefix"])})
    return cols


def tsv(rows: list[dict], cols: list[str]) -> str:
    out = ["\t".join(cols)]
    for r in rows:
        out.append("\t".join("" if r.get(c) is None else str(r[c]) for c in cols))
    return "\n".join(out) + "\n"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build_feed(events: list[dict], cat: dict, opts: dict, root: Path = ROOT) -> dict:
    """Returns {files: {name: text}, meta, features}. opts: game, maker, url, maker_url, collected_under,
    approval, instrument, countries, languages, purposes, min_players, min_classes, licence."""
    ont = load_ontology(root)
    th = ont["thresholds"]
    mp = max(int(opts.get("min_players") or th["min_players"]), th["min_players"])
    mc = max(int(opts.get("min_classes") or th["min_classes"]), th["min_classes"])
    feat = compute_features(events, cat, ont, mp, mc, th.get("round_counts_to", 5))
    cols = feed_columns(feat["rows"], ont)
    game_id = next((ev.get("game_id") for ev in events if ev.get("game_id")), cat.get("game_id", "game"))
    meta = {
        "dataset_id": f"{game_id}_{feat['start'] or 'na'}_{feat['end'] or 'na'}_population",
        "dataset_type": "Population",
        "game_id": game_id,
        "player_count": feat["players"], "session_count": feat["sessions"], "class_count": feat["classes"],
        "start_date": feat["start"], "end_date": feat["end"],
        "units": feat["units"],
        "csef_profile": PROFILE, "ontology": ONTOLOGY,
        "thresholds": {"min_players": mp, "min_classes": mc, "round_counts_to": th.get("round_counts_to", 5), "time_precision": "month"},
        "purposes": opts.get("purposes") or ["improvement", "evaluation"],
        "collected_under": opts.get("collected_under"),
        "approval": opts.get("approval"),
        "instrument": opts.get("instrument"),
        "age_bands": feat["age_bands"],
        "countries": opts.get("countries") or [],
        "languages": opts.get("languages") or [],
        "game": {"name": opts.get("game") or game_id, "url": opts.get("url")},
        "maker": {"name": opts.get("maker"), "url": opts.get("maker_url")},
        "licence": opts.get("licence") or "CC0-1.0",
        "suppressed_cells": len(feat["suppressed"]),
        "generated_by": f"{TOOL} {VERSION}",
    }
    files = {"population.tsv": tsv(feat["rows"], cols),
             "META.json": json.dumps(meta, indent=2, ensure_ascii=False) + "\n"}
    files["README.md"] = feed_readme(meta, cols, ont)
    manifest = {"ontology": ONTOLOGY, "files": {n: sha256_bytes(t.encode("utf-8")) for n, t in files.items()}}
    files["MANIFEST.json"] = json.dumps(manifest, indent=2) + "\n"
    return {"files": files, "meta": meta, "features": feat, "columns": cols}


def feed_readme(meta: dict, cols: list[str], ont: dict) -> str:
    g = meta["game"]
    lines = [f"# Open evidence feed: {g.get('name')}", "",
             f"Group figures from play, in the {ONTOLOGY} format of the Child-Safe EdTech Framework (CSEF). "
             f"They describe how groups of pupils played, never one pupil or one class.", "",
             "| | |", "|---|---|",
             f"| Game | {g.get('name')}" + (f" ({g['url']})" if g.get("url") else "") + " |",
             f"| Maker | {meta['maker'].get('name') or 'not given'}" + (f" ({meta['maker']['url']})" if meta["maker"].get("url") else "") + " |",
             f"| Period | {meta['start_date']} to {meta['end_date']} |",
             f"| Players (rounded to 5) | {meta['player_count']} in {meta['class_count']} classes |",
             f"| Age bands | {', '.join(meta['age_bands']) or 'not shown'} |",
             f"| Countries | {', '.join(meta['countries']) or 'not given'} |",
             f"| Collected | {'as a processor for schools, released under their contract' if meta['collected_under'] == 'processor_for_school' else 'in the maker’s own study' if meta['collected_under'] == 'own_study' else 'not stated'} |",
             f"| Thresholds | at least {meta['thresholds']['min_players']} players and {meta['thresholds']['min_classes']} classes behind every figure; {meta['suppressed_cells']} small cell(s) removed |",
             f"| Licence | {meta['licence']} |", "",
             "## Columns", "", "| Column | Meaning |", "|---|---|"]
    ctx = {"population_id": "The group: 'dataset' is everyone in this file.", "unit_id": "A unit of play (level, mission); * is the whole game.",
           "players": "Players behind the row, rounded to 5.", "classes": "Classes behind the row."}
    for c in cols:
        if c in ctx:
            lines.append(f"| {c} | {ctx[c]} |")
            continue
        f = next((f for f in ont["features"] if c in f.get("columns", []) or (f.get("columns_prefix") and c.startswith(f["columns_prefix"]))), None)
        if f:
            lines.append(f"| {c} | {f['id']}: {f['meaning']} |")
    if meta.get("instrument"):
        lines += ["", f"Learning gain instrument: {meta['instrument']}."]
    lines += ["", "## How to cite", "", f"{meta['maker'].get('name') or 'The maker'} ({(meta['end_date'] or '')[:4]}). "
              f"Open evidence feed for {g.get('name')}, {meta['start_date']} to {meta['end_date']}. {ONTOLOGY}.", "",
              "## Not in this file", "",
              "No player codes, sessions, timestamps, schools, classes or free text. No retention, daily users, streaks or revenue.",
              "Figures are the maker's own unless a researcher or curator has checked the method.", ""]
    return "\n".join(lines)


def write_feed(feed: dict, out: Path, make_zip: bool = False) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, text in feed["files"].items():
        p = out / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    if make_zip:
        z = out.parent / f"{out.name}.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, text in feed["files"].items():
                zf.writestr(f"{out.name}/{name}", text)
        paths.append(z)
    return paths


# --------------------------------------------------------------------------- check-feed
def read_feed(path: Path) -> dict[str, str]:
    path = Path(path)
    files = {}
    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            for n in zf.namelist():
                base = n.rsplit("/", 1)[-1]
                if base and not n.endswith("/"):
                    files[base] = zf.read(n).decode("utf-8")
    else:
        for p in path.iterdir():
            if p.is_file():
                files[p.name] = p.read_text(encoding="utf-8")
    return files


def check_feed(files: dict[str, str], root: Path = ROOT) -> dict:
    ont = load_ontology(root)
    th = ont["thresholds"]
    issues = []

    def add(sev, msg):
        issues.append({"severity": sev, "rule": "CORE-DAT-24", "message": msg})

    for n in FEED_FILES:
        if n not in files:
            add("BLOCK", f"{n} is missing.")
    meta = {}
    if "META.json" in files:
        try:
            meta = json.loads(files["META.json"])
        except json.JSONDecodeError:
            add("BLOCK", "META.json is not valid JSON.")
    if "MANIFEST.json" in files:
        try:
            man = json.loads(files["MANIFEST.json"]).get("files", {})
            for n, h in man.items():
                if n not in files:
                    add("BLOCK", f"MANIFEST.json lists {n}, which is missing.")
                elif sha256_bytes(files[n].encode("utf-8")) != h:
                    add("BLOCK", f"{n} does not match its SHA-256 hash in MANIFEST.json: the file changed after the feed was built.")
        except json.JSONDecodeError:
            add("BLOCK", "MANIFEST.json is not valid JSON.")
    else:
        add("REVIEW", "MANIFEST.json is missing: hashes cannot be checked.")
    if meta:
        if meta.get("ontology") != ONTOLOGY:
            add("BLOCK", f"META.json ontology is '{meta.get('ontology')}', not {ONTOLOGY}.")
        t = meta.get("thresholds") or {}
        if int(t.get("min_players") or 0) < th["min_players"] or int(t.get("min_classes") or 0) < th["min_classes"]:
            add("BLOCK", f"Thresholds are {t.get('min_players')} players and {t.get('min_classes')} classes: at least "
                         f"{th['min_players']} and {th['min_classes']} are needed.")
        for k in ("start_date", "end_date"):
            if meta.get(k) and not MONTH_RX.match(str(meta[k])):
                add("BLOCK", f"META.json {k} is '{meta[k]}': dates are given to the month (YYYY-MM).")
        if meta.get("collected_under") not in ("processor_for_school", "own_study"):
            add("REVIEW", "META.json does not say how the data were collected (collected_under: processor_for_school or own_study).")
        for k in _keys(meta):
            if any(w in k.lower() for w in ont["forbidden_metrics"]):
                add("BLOCK", f"META.json key '{k}' is an engagement or commercial metric (CORE-DAT-23).")
    rows, cols = [], []
    if "population.tsv" in files:
        rd = list(csv.reader(io.StringIO(files["population.tsv"]), delimiter="\t"))
        cols = rd[0] if rd else []
        rows = [dict(zip(cols, r)) for r in rd[1:] if any(x.strip() for x in r)]
        allowed = set(ont.get("context_columns") or [])
        prefixes = []
        for f in ont["features"]:
            allowed |= set(f.get("columns", []))
            if f.get("columns_prefix"):
                prefixes.append(f["columns_prefix"])
        for c in cols:
            if any(w in c.lower() for w in ont["forbidden_metrics"]):
                add("BLOCK", f"Column '{c}' is an engagement or commercial metric (CORE-DAT-23).")
            elif c in ("player_id", "session_id", "instance_id", "timestamp") or "school" in c or "class_name" in c:
                add("BLOCK", f"Column '{c}' identifies players, sessions or classes: open feeds hold group figures only.")
            elif c not in allowed and not any(c.startswith(p) for p in prefixes):
                add("REVIEW", f"Column '{c}' is not in {ONTOLOGY}.")
        mp = max(int((meta.get("thresholds") or {}).get("min_players") or 0), th["min_players"])
        mc = max(int((meta.get("thresholds") or {}).get("min_classes") or 0), th["min_classes"])
        step = int(th.get("round_counts_to", 5))
        for r in rows:
            try:
                p, c = int(r.get("players") or 0), int(r.get("classes") or 0)
            except ValueError:
                add("BLOCK", f"Row {r.get('unit_id')}: players or classes is not a number.")
                continue
            if p < mp or c < mc:
                add("BLOCK", f"Row {r.get('unit_id')}: {p} players in {c} classes, below the thresholds.")
            if p % step:
                add("BLOCK", f"Row {r.get('unit_id')}: players ({p}) is not rounded to {step}.")
            for k, v in r.items():
                if v and k.endswith("_share"):
                    try:
                        if not 0 <= float(v) <= 1:
                            add("REVIEW", f"Row {r.get('unit_id')}: {k} = {v} is not a share between 0 and 1.")
                    except ValueError:
                        add("REVIEW", f"Row {r.get('unit_id')}: {k} = {v} is not a number.")
        if not rows:
            add("BLOCK", "population.tsv has no rows.")
    order = {"BLOCK": 0, "REVIEW": 1}
    issues.sort(key=lambda x: order.get(x["severity"], 9))
    counts = {s: sum(1 for i in issues if i["severity"] == s) for s in ("BLOCK", "REVIEW")}
    return {"kind": "feed", "tool": f"{TOOL} {VERSION}", "ok": counts["BLOCK"] == 0, "meta": meta,
            "columns": cols, "rows": rows, "issues": issues, "counts": counts}


def _keys(d, prefix=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield f"{prefix}{k}"
            yield from _keys(v, f"{prefix}{k}.")


# --------------------------------------------------------------------------- reports
def render_md(res: dict) -> str:
    L = []
    if res["kind"] == "events":
        L += [f"# CSEF event file check: {res.get('game_id') or 'events'}", "",
              f"{res['events']} events of {res['event_types']} types, {res['players']} player codes, {res['sessions']} sessions, "
              f"{res['classes']} class ids. Checked against the child-safe profile {PROFILE} and the event catalogue.", ""]
        if res.get("version_branches"):
            L += [f"Version branches in the file: {', '.join(res['version_branches'])}.", ""]
    else:
        m = res.get("meta") or {}
        L += [f"# CSEF evidence feed check: {(m.get('game') or {}).get('name') or m.get('game_id') or 'feed'}", "",
              f"{'Ready to publish' if res['ok'] else 'Not ready to publish'}: {len(res['rows'])} rows, "
              f"{m.get('player_count', '?')} players in {m.get('class_count', '?')} classes, {m.get('start_date')} to {m.get('end_date')}.", ""]
    L += [f"Blocking: {res['counts'].get('BLOCK', 0)} · To review: {res['counts'].get('REVIEW', 0)}", ""]
    if res["issues"]:
        L += ["| Severity | Rule | Issue | Rows |", "|---|---|---|---|"]
        for i in res["issues"]:
            rows = ", ".join(map(str, i.get("rows") or [])) + (f" (+{i['count'] - 5} more)" if i.get("count", 0) > 5 else "")
            L.append(f"| {i['severity']} | {i['rule']} | {i['message']} | {rows} |")
    else:
        L.append("No issues found.")
    L += ["", f"{res['tool']}. Pre-compliance support, not legal advice. See framework/08-learning-data.md.", ""]
    return "\n".join(L)


CSS = """body{margin:0;background:var(--c-paper);color:var(--c-ink);font-family:var(--font);line-height:1.5}
main{max-width:1040px;margin:0 auto;padding:28px 20px 60px}h1,h2{font-family:var(--font-display)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin:18px 0}
.card{background:var(--c-panel);border:1px solid var(--c-line);border-radius:10px;padding:12px 14px}
.card b{display:block;font-family:var(--font-display);font-size:1.6rem}
table{width:100%;border-collapse:collapse;background:var(--c-panel);border:1px solid var(--c-line);margin:8px 0 20px}
th,td{text-align:left;vertical-align:top;padding:9px 11px;border-bottom:1px solid var(--c-line);font-size:.92rem}
th{color:var(--c-ink2);font-weight:600}.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.78rem;font-weight:600}
.BLOCK{background:var(--c-coral-bg);color:var(--c-coral-t)}.REVIEW{background:var(--c-sun-bg);color:var(--c-sun-t)}
.ok{background:var(--c-teal-bg);color:var(--c-teal-t)}.note{color:var(--c-ink2);font-size:.9rem}"""


def render_html(res: dict) -> str:
    e = html.escape
    title = "Event file check" if res["kind"] == "events" else "Evidence feed check"
    body = []
    if res["kind"] == "events":
        body.append(f'<div class="cards"><div class="card"><b>{res["events"]}</b>events</div><div class="card"><b>{res["event_types"]}</b>event types</div>'
                    f'<div class="card"><b>{res["players"]}</b>player codes</div><div class="card"><b>{res["classes"]}</b>class ids</div>'
                    f'<div class="card"><b>{res["counts"]["BLOCK"]}</b>blocking</div><div class="card"><b>{res["counts"]["REVIEW"]}</b>to review</div></div>')
        name = res.get("game_id") or ""
    else:
        m = res.get("meta") or {}
        name = (m.get("game") or {}).get("name") or m.get("game_id") or ""
        st = '<span class="pill ok">Ready to publish</span>' if res["ok"] else '<span class="pill BLOCK">Not ready to publish</span>'
        body.append(f'<p>{st} {e(str(m.get("player_count", "?")))} players in {e(str(m.get("class_count", "?")))} classes, '
                    f'{e(str(m.get("start_date")))} to {e(str(m.get("end_date")))}. Thresholds: {e(str((m.get("thresholds") or {}).get("min_players")))} players and '
                    f'{e(str((m.get("thresholds") or {}).get("min_classes")))} classes per figure.</p>')
        if res["rows"]:
            cols = res["columns"]
            body.append("<h2>Figures</h2><div style='overflow-x:auto'><table><thead><tr>" + "".join(f"<th>{e(c)}</th>" for c in cols) + "</tr></thead><tbody>"
                        + "".join("<tr>" + "".join(f"<td>{e(str(r.get(c, '')))}</td>" for c in cols) + "</tr>" for r in res["rows"]) + "</tbody></table></div>")
    body.append("<h2>Issues</h2>")
    if res["issues"]:
        body.append("<table><thead><tr><th>Severity</th><th>Rule</th><th>Issue</th><th>Rows</th></tr></thead><tbody>")
        for i in res["issues"]:
            rows = ", ".join(map(str, i.get("rows") or [])) + (f" (+{i['count'] - 5} more)" if i.get("count", 0) > 5 else "")
            body.append(f'<tr><td><span class="pill {e(i["severity"])}">{e(i["severity"])}</span></td><td>{e(i["rule"])}</td><td>{e(i["message"])}</td><td>{e(rows)}</td></tr>')
        body.append("</tbody></table>")
    else:
        body.append("<p>No issues found.</p>")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>CSEF {e(title)}: {e(name)}</title>{brand.head()}<style>{brand.tokens_css()}{brand.BASE_CSS}{CSS}</style></head>'
            f'<body><div class="csef-stripe"></div><main>{brand.logo("lockup", 40)}<h1>{e(title)}: {e(name)}</h1>'
            f'<p class="note">Child-safe profile {PROFILE}, ontology {ONTOLOGY}. Pre-compliance support, not legal advice. '
            f'See the <a href="https://csef.kendirstudios.pt/learning-data/">Learning data guide</a>.</p>'
            + "".join(body) + f'<p class="note">{e(res["tool"])}</p></main></body></html>')


def write_report(res: dict, out: Path, stem: str, formats=("md", "html", "json")) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    if "md" in formats:
        paths.append(out / f"{stem}.md")
        paths[-1].write_text(render_md(res), encoding="utf-8")
    if "html" in formats:
        paths.append(out / f"{stem}.html")
        paths[-1].write_text(render_html(res), encoding="utf-8")
    if "json" in formats:
        paths.append(out / f"{stem}.json")
        paths[-1].write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return paths


# --------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CSEF learning data: check event files, build and check open evidence feeds.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ce = sub.add_parser("check-events", help="check an OGD event file against the child-safe profile and the event catalogue")
    ce.add_argument("--events", required=True)
    ce.add_argument("--catalogue", required=True)
    ce.add_argument("--out-dir", default="csef-events")
    ce.add_argument("--formats", default="md,html,json")
    bf = sub.add_parser("build-feed", help="build an open evidence feed (csef-evidence-0.1) from an event file")
    bf.add_argument("--events", required=True)
    bf.add_argument("--catalogue", required=True)
    bf.add_argument("--out-dir", default="evidence-feed")
    bf.add_argument("--game")
    bf.add_argument("--url")
    bf.add_argument("--maker")
    bf.add_argument("--maker-url")
    bf.add_argument("--collected-under", choices=["processor_for_school", "own_study"], required=True)
    bf.add_argument("--approval", help="ethics or study approval reference (own_study)")
    bf.add_argument("--instrument", help="name of the pre and post check, for EV-GAIN")
    bf.add_argument("--countries", default="")
    bf.add_argument("--languages", default="")
    bf.add_argument("--min-players", type=int)
    bf.add_argument("--min-classes", type=int)
    bf.add_argument("--zip", action="store_true")
    bf.add_argument("--skip-event-check", action="store_true", help="build even when check-events finds blocking issues")
    ck = sub.add_parser("check-feed", help="check a feed folder or zip before release or before showing it")
    ck.add_argument("--feed", required=True)
    ck.add_argument("--out-dir", default="csef-feed-check")
    ck.add_argument("--formats", default="md,html,json")
    a = ap.parse_args(argv)

    if a.cmd == "check-events":
        cols, events = read_events(a.events)
        res = check_events(cols, events, load_yaml(Path(a.catalogue)))
        paths = write_report(res, Path(a.out_dir), "events-check", [f.strip() for f in a.formats.split(",")])
        print(f"{TOOL}: {res['events']} events, {res['counts']['BLOCK']} blocking, {res['counts']['REVIEW']} to review | "
              + ", ".join(str(p) for p in paths))
        return 1 if res["counts"]["BLOCK"] else 0
    if a.cmd == "build-feed":
        cols, events = read_events(a.events)
        cat = load_yaml(Path(a.catalogue))
        chk = check_events(cols, events, cat)
        if chk["counts"]["BLOCK"] and not a.skip_event_check:
            print(f"{TOOL}: the event file has {chk['counts']['BLOCK']} blocking issue(s). Run check-events first.", file=sys.stderr)
            return 1
        feed = build_feed(events, cat, {
            "game": a.game, "url": a.url, "maker": a.maker, "maker_url": a.maker_url, "collected_under": a.collected_under,
            "approval": a.approval, "instrument": a.instrument,
            "countries": [x.strip() for x in a.countries.split(",") if x.strip()],
            "languages": [x.strip() for x in a.languages.split(",") if x.strip()],
            "min_players": a.min_players, "min_classes": a.min_classes})
        paths = write_feed(feed, Path(a.out_dir), a.zip)
        res = check_feed(feed["files"])
        f = feed["features"]
        print(f"{TOOL}: {len(f['rows'])} rows, {len(f['suppressed'])} small cell(s) removed, feed {'ready' if res['ok'] else 'NOT ready'} | "
              + ", ".join(str(p) for p in paths))
        return 0 if res["ok"] else 1
    if a.cmd == "check-feed":
        res = check_feed(read_feed(Path(a.feed)))
        paths = write_report(res, Path(a.out_dir), "feed-check", [f.strip() for f in a.formats.split(",")])
        print(f"{TOOL}: feed {'ready to publish' if res['ok'] else 'NOT ready'}, {res['counts']['BLOCK']} blocking, "
              f"{res['counts']['REVIEW']} to review | " + ", ".join(str(p) for p in paths))
        return 0 if res["ok"] else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
