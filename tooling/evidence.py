#!/usr/bin/env python3
"""CSEF learning data: check event files, build open evidence feeds, check feeds.

Learning games can log what pupils do with the Open Game Data (OGD) event standard. This tool keeps that data
child-safe (framework/08-learning-data.md):

  check-events  an OGD event file (TSV) against the child-safe profile and the product's event catalogue:
                undeclared events and fields, forbidden columns, possible free text, emails, IP addresses,
                player codes that look like hashes, player metadata beyond the allow-list.
  build-feed    an open evidence feed (csef-evidence-0.1) from an event file and its catalogue: one row per
                figure, per unit (time to finish, completion, stuck, help) and for the whole game (time,
                learning gain, accessibility settings, natural stops, play mode, devices), for everyone and for
                each age band and country large enough on its own. Every row has at least 10 players and
                3 classes behind it; smaller groups are left out. Counts are rounded to 5, periods to the
                month. Writes population.tsv, META.json, README.md and MANIFEST.json (and a zip).
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
VERSION = "0.14.1"
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
COLUMNS = ["unit", "unit_order", "feature", "category", "stat", "value", "players", "classes", "age_band", "country", "period", "instrument"]
WHOLE = "Whole game"


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


def unit_label(u: str) -> str:
    m = re.match(r"^lvl\s*(\d+)$", u, re.I)
    return f"Level {m.group(1)}" if m else u


def _num(x: float, nd: int = 2):
    x = round(float(x), nd)
    return int(x) if x == int(x) else x


def play_facts(events: list[dict], cat: dict) -> dict:
    """Per player and per session facts from an event file, read once."""
    idx = catalogue_index(cat)
    role = lambda ev: (idx.get(str(ev.get("event_name"))) or {}).get("evidence_role")  # noqa: E731
    by_session = defaultdict(list)
    for ev in events:
        by_session[ev.get("session_id")].append(ev)
    for evs in by_session.values():
        evs.sort(key=lambda e: (int(e.get("session_sequence_index") or 0), str(e.get("timestamp") or "")))
    f = {"player_class": {}, "player_age": {}, "started": defaultdict(set), "finished": defaultdict(dict),
         "helped": defaultdict(set), "stuck": defaultdict(set), "settings": defaultdict(set), "pre": {}, "post": {},
         "active": defaultdict(float), "sess_player": {}, "sess_mode": {}, "sess_device": {}, "sess_stop": {},
         "months": set(), "unit_order": {}}
    for ev in events:
        pid = ev.get("player_id")
        if pid:
            f["player_class"].setdefault(pid, ev.get("instance_id") or "?")
            pm = ev.get("player_metadata")
            if isinstance(pm, dict) and pm.get("age_band"):
                f["player_age"].setdefault(pid, str(pm["age_band"]))
    for sid, evs in by_session.items():
        open_units: dict[str, float] = {}
        prev_t = None
        pid = next((e.get("player_id") for e in evs if e.get("player_id")), None)
        f["sess_player"][sid] = pid
        for ev in evs:
            t = ts(ev.get("timestamp"))
            if t:
                f["months"].add(t.strftime("%Y-%m"))
            gap = max(min((t - prev_t).total_seconds(), ACTIVE_GAP_S), 0.0) if (t and prev_t) else 0.0
            prev_t = t or prev_t
            if pid:
                f["active"][pid] += gap
            for u in open_units:
                open_units[u] += gap
            r, u = role(ev), _unit(ev)
            data = ev.get("event_data") if isinstance(ev.get("event_data"), dict) else {}
            gs = ev.get("game_state") if isinstance(ev.get("game_state"), dict) else {}
            if gs.get("mode") and sid not in f["sess_mode"]:
                f["sess_mode"][sid] = str(gs["mode"])
            if u and u not in f["unit_order"] and r in ("unit_start", "unit_complete"):
                f["unit_order"][u] = len(f["unit_order"]) + 1
            if not pid:
                continue
            if r == "unit_start" and u:
                f["started"][u].add(pid)
                open_units.setdefault(u, 0.0)
            elif r == "unit_complete" and u:
                f["started"][u].add(pid)
                if u in open_units and pid not in f["finished"][u]:
                    f["finished"][u][pid] = open_units[u] / 60.0
                open_units.pop(u, None)
            elif r == "help" and u:
                f["helped"][u].add(pid)
            elif r == "stuck" and u and str(ev.get("event_source", "")).upper() != "GAME":
                f["stuck"][u].add(pid)
            elif r == "setting" and data.get("on") is True and data.get("setting"):
                f["settings"][str(data["setting"])].add(pid)
            elif r == "assessment" and isinstance(data.get("score"), (int, float)) and data.get("max"):
                (f["pre"] if data.get("phase") == "pre" else f["post"])[pid] = float(data["score"]) / float(data["max"])
            elif r == "mode" and data.get("mode"):
                f["sess_mode"][sid] = str(data["mode"])
            elif r == "session_start" and data.get("device"):
                f["sess_device"][sid] = str(data["device"])
            elif r == "session_end" and isinstance(data.get("natural_stop"), bool):
                f["sess_stop"][sid] = data["natural_stop"]
    # Units in playing order: the order they were first started in the file is close; the catalogue can set it.
    order = {str(u.get("unit")): i for i, u in enumerate(cat.get("units") or [], 1) if isinstance(u, dict)}
    if order:
        f["unit_order"] = {u: order.get(u, 100 + n) for u, n in f["unit_order"].items()}
    else:
        f["unit_order"] = {u: i for i, u in enumerate(sorted(f["unit_order"], key=lambda u: (re.sub(r"\d+", "", u), int(re.sub(r"\D", "", u) or 0), u)), 1)}
    return f


SETTING_CATS = {"captions": "captions", "text_size": "text_size", "reduced_motion": "reduced_motion", "audio_descriptions": "audio",
                "read_aloud": "audio", "audio": "audio", "high_contrast": "high_contrast"}


def compute_features(events: list[dict], cat: dict, ont: dict, min_players: int, min_classes: int, round_to: int = 5,
                     class_country: dict | None = None, instrument: str | None = None) -> dict:
    """One row per figure, for the whole group and for every age band and country large enough on its own."""
    f = play_facts(events, cat)
    class_country = class_country or {}
    pc = f["player_class"]
    sm = sorted(f["months"])
    period = f"{sm[0]}/{sm[-1]}" if sm else "all"
    rows, suppressed = [], []

    def classes(players) -> int:
        return len({pc.get(p, "?") for p in players} - {"?"})

    def ok(players) -> bool:
        return len(players) >= min_players and classes(players) >= min_classes

    def add(unit, order, feature, stat, value, players, age, country, category="", instr=""):
        rows.append({"unit": unit, "unit_order": order, "feature": feature, "category": category, "stat": stat,
                     "value": value, "players": r5(len(players), round_to), "classes": classes(players),
                     "age_band": age, "country": country, "period": period, "instrument": instr})

    def figures(group: set, age: str, country: str):
        tag = {"age_band": age, "country": country}
        for u, order in sorted(f["unit_order"].items(), key=lambda x: x[1]):
            ps = f["started"][u] & group
            if not ok(ps):
                suppressed.append(dict(tag, unit=u, reason="fewer than the minimum players or classes"))
                continue
            name = unit_label(u)
            fin = {p: m for p, m in f["finished"][u].items() if p in group}
            if ok(set(fin)):
                for st, q in (("p25", .25), ("p50", .5), ("p75", .75)):
                    add(name, order, "EV-TIME", st, _num(pct(list(fin.values()), q), 1), set(fin), age, country)
            else:
                suppressed.append(dict(tag, unit=u, feature="EV-TIME", reason="fewer finishers than the minimum"))
            add(name, order, "EV-DONE", "share", _num(len(set(fin) & ps) / len(ps)), ps, age, country)
            if any(d.get("evidence_role") == "stuck" for d in cat.get("detectors") or []):
                add(name, order, "EV-STUCK", "share", _num(len(f["stuck"][u] & ps) / len(ps)), ps, age, country)
            add(name, order, "EV-HELP", "share", _num(len(f["helped"][u] & ps) / len(ps)), ps, age, country)
        if not ok(group):
            suppressed.append(dict(tag, unit=WHOLE, reason="fewer than the minimum players or classes"))
            return
        act = {p: f["active"][p] / 60.0 for p in group if f["active"].get(p)}
        if ok(set(act)):
            for st, q in (("p25", .25), ("p50", .5), ("p75", .75)):
                add(WHOLE, 0, "EV-TIME", st, _num(pct(list(act.values()), q), 1), set(act), age, country)
        if any(d.get("evidence_role") == "stuck" for d in cat.get("detectors") or []):
            add(WHOLE, 0, "EV-STUCK", "share", _num(len(set().union(*f["stuck"].values()) & group) / len(group)) if f["stuck"] else 0, group, age, country)
        add(WHOLE, 0, "EV-HELP", "share", _num(len(set().union(*f["helped"].values()) & group) / len(group)) if f["helped"] else 0, group, age, country)
        stops = {s: v for s, v in f["sess_stop"].items() if f["sess_player"].get(s) in group}
        if stops and ok({f["sess_player"][s] for s in stops}):
            add(WHOLE, 0, "EV-STOP", "share", _num(sum(1 for v in stops.values() if v) / len(stops)), {f["sess_player"][s] for s in stops}, age, country)
        both = set(f["pre"]) & set(f["post"]) & group
        if both and ok(both):
            d = [f["post"][p] - f["pre"][p] for p in both]
            mean = sum(d) / len(d)
            sd = (sum((x - mean) ** 2 for x in d) / (len(d) - 1)) ** .5 if len(d) > 1 else 0
            ins = instrument or "Pre and post check (name it with --instrument)"
            for st, v in (("pre", sum(f["pre"][p] for p in both) / len(both)), ("post", sum(f["post"][p] for p in both) / len(both)),
                          ("change", mean)) + ((("effect_size", mean / sd),) if sd else ()):
                add(WHOLE, 0, "EV-GAIN", st, _num(v), both, age, country, instr=ins)
        elif both or f["pre"] or f["post"]:
            suppressed.append(dict(tag, unit=WHOLE, feature="EV-GAIN", reason="fewer players with both checks than the minimum"))
        for s, ps in sorted(f["settings"].items()):
            add(WHOLE, 0, "EV-ACCESS", "share", _num(len(ps & group) / len(group)), group, age, country, category=SETTING_CATS.get(s, "other"))
        for key, src in (("EV-MODE", f["sess_mode"]), ("EV-DEVICE", f["sess_device"])):
            have = {s: v for s, v in src.items() if f["sess_player"].get(s) in group}
            players = {f["sess_player"][s] for s in have}
            if have and ok(players):
                for val in sorted(set(have.values())):
                    add(WHOLE, 0, key, "share", _num(sum(1 for v in have.values() if v == val) / len(have)), players, age, country, category=val)

    everyone = set(pc)
    figures(everyone, "all", "all")
    bands = defaultdict(set)
    for p, b in f["player_age"].items():
        bands[b].add(p)
    for b in sorted(bands):
        if len(bands) > 1 and ok(bands[b]):
            figures(bands[b], b, "all")
    countries = defaultdict(set)
    for p, c in pc.items():
        if class_country.get(c):
            countries[class_country[c].upper()].add(p)
    for c in sorted(countries):
        if len(countries) > 1 and ok(countries[c]):
            figures(countries[c], "all", c)
    published_countries = sorted(c for c in countries if ok(countries[c]))
    age_list = sorted(b for b in bands if ok(bands[b]))
    if ok(everyone):
        for cat_, stat, val in (("players", "count", r5(len(everyone), round_to)), ("classes", "count", classes(everyone)),
                                ("age_bands", "list", ",".join(age_list)), ("countries", "list", ",".join(published_countries)),
                                ("months", "list", ",".join(sm))):
            if val not in ("", None):
                add(WHOLE, 0, "CONTEXT", stat, val, everyone, "all", "all", category=cat_)
    rows.sort(key=lambda r: (r["age_band"] != "all", r["age_band"], r["country"] != "all", r["country"], r["unit_order"] == 0, r["unit_order"]))
    return {
        "rows": rows, "suppressed": suppressed, "period": period,
        "players": r5(len(everyone), round_to), "sessions": r5(len(f["sess_player"]), round_to), "classes": classes(everyone),
        "start": sm[0] if sm else None, "end": sm[-1] if sm else None, "age_bands": age_list, "countries": published_countries,
        "units": [[unit_label(u), o] for u, o in sorted(f["unit_order"].items(), key=lambda x: x[1])
                  if any(r["unit"] == unit_label(u) for r in rows)],
    }


def tsv(rows: list[dict], cols: list[str] = COLUMNS) -> str:
    cell = lambda v: "" if v is None else re.sub(r"[\t\r\n]+", " ", str(v))  # noqa: E731
    return "\t".join(cols) + "\n" + "".join("\t".join(cell(r.get(c)) for c in cols) + "\n" for r in rows)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_class_countries(path: Path | str | None) -> dict:
    """Optional: a CSV or TSV with instance_id and country (two-letter code). Kept by the controller, never in events."""
    if not path:
        return {}
    text = Path(path).read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(text), delimiter="\t" if "\t" in text.splitlines()[0] else ","))
    head = [norm_col(c) for c in rows[0]]
    i, j = head.index("instance_id"), head.index("country")
    return {r[i].strip(): r[j].strip().upper() for r in rows[1:] if len(r) > max(i, j) and re.match(r"^[A-Za-z]{2}$", r[j].strip())}


def build_feed(events: list[dict], cat: dict, opts: dict, root: Path = ROOT) -> dict:
    """Returns {files: {name: text}, meta, features}. opts: game, url, maker, maker_url, collected_under, approval,
    instrument, countries, languages, purposes, min_players, min_classes, licence, class_countries (dict)."""
    ont = load_ontology(root)
    th = ont["thresholds"]
    mp = max(int(opts.get("min_players") or th["min_players"]), th["min_players"])
    mc = max(int(opts.get("min_classes") or th["min_classes"]), th["min_classes"])
    feat = compute_features(events, cat, ont, mp, mc, th.get("round_counts_to", 5), opts.get("class_countries") or {},
                            opts.get("instrument"))
    if opts.get("languages") and feat["rows"]:
        r0 = next((r for r in feat["rows"] if r["feature"] == "CONTEXT"), None)
        if r0:
            feat["rows"].append(dict(r0, category="languages", stat="list", value=",".join(opts["languages"])))
    game_id = next((ev.get("game_id") for ev in events if ev.get("game_id")), cat.get("game_id", "game"))
    name = opts.get("game") or game_id
    maker = opts.get("maker") or ""
    countries = feat["countries"] or [c.upper() for c in opts.get("countries") or []]
    meta = {
        "ontology": ONTOLOGY, "csef_profile": PROFILE,
        "title": f"{name}: open evidence",
        "game": {"id": game_id, "name": name, "url": opts.get("url")},
        "maker": maker, "maker_url": opts.get("maker_url"),
        "period": feat["period"],
        "licence": opts.get("licence") or "CC0-1.0",
        "purposes": opts.get("purposes") or ["improvement", "evaluation"],
        "collected_under": opts.get("collected_under"),
        "approval": opts.get("approval"),
        "thresholds": {"min_players": mp, "min_classes": mc, "round_counts_to": th.get("round_counts_to", 5), "time_resolution": "month"},
        "citation": f"{maker or 'The maker'}. {name}: open evidence ({feat['period']}). {ONTOLOGY}.",
        # Open Game Data dataset keys
        "dataset_id": f"{game_id}_{feat['start'] or 'na'}_{feat['end'] or 'na'}_population", "dataset_type": "Population",
        "game_id": game_id, "start_date": feat["start"], "end_date": feat["end"],
        "player_count": feat["players"], "session_count": feat["sessions"], "class_count": feat["classes"],
        "units": feat["units"], "age_bands": feat["age_bands"], "countries": countries, "languages": opts.get("languages") or [],
        "suppressed_cells": len(feat["suppressed"]), "generated_by": f"{TOOL} {VERSION}",
    }
    files = {"population.tsv": tsv(feat["rows"]), "META.json": json.dumps(meta, indent=2, ensure_ascii=False) + "\n"}
    files["README.md"] = feed_readme(meta, ont)
    files["MANIFEST.json"] = json.dumps({"ontology": ONTOLOGY, "files": [
        {"path": n, "sha256": sha256_bytes(t.encode("utf-8")), "bytes": len(t.encode("utf-8"))} for n, t in files.items()]}, indent=2) + "\n"
    return {"files": files, "meta": meta, "features": feat, "columns": COLUMNS}


def feed_readme(meta: dict, ont: dict) -> str:
    g = meta["game"]
    cu = {"processor_for_school": "for schools, as their processor; released under their contract",
          "own_study": "in the maker's own study" + (f" ({meta['approval']})" if meta.get("approval") else "")}.get(meta.get("collected_under"), "not stated")
    lines = [f"# {meta['title']}", "",
             f"Group figures from play, in the {ONTOLOGY} format of the Child-Safe EdTech Framework (CSEF). "
             "They describe how groups of pupils played, never one pupil or one class.", "",
             "| | |", "|---|---|",
             f"| Game | {g.get('name')}" + (f" ({g['url']})" if g.get("url") else "") + " |",
             f"| Maker | {meta.get('maker') or 'not given'}" + (f" ({meta['maker_url']})" if meta.get("maker_url") else "") + " |",
             f"| Period | {meta['period']} |",
             f"| Players (rounded to 5) | {meta['player_count']} in {meta['class_count']} classes |",
             f"| Age bands | {', '.join(meta['age_bands']) or 'not shown'} |",
             f"| Countries | {', '.join(meta['countries']) or 'not given'} |",
             f"| Collected | {cu} |",
             f"| Thresholds | at least {meta['thresholds']['min_players']} players and {meta['thresholds']['min_classes']} classes behind every row; {meta['suppressed_cells']} small group(s) left out |",
             f"| Licence | {meta['licence']} |", "",
             "## population.tsv", "", "One row per figure. Tab-separated.", "", "| Column | Meaning |", "|---|---|"]
    lines += [f"| {c['name']} | {c['meaning']} |" for c in ont["columns"]]
    lines += ["", "| Feature | Stats | Meaning |", "|---|---|---|"]
    lines += [f"| {x['id']} | {', '.join(x['stats'])} | {x['meaning']} |" for x in ont["features"]]
    lines += ["", "## How to cite", "", meta["citation"], "",
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


PERIOD_RX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])/\d{4}-(0[1-9]|1[0-2])$")


def check_feed(files: dict[str, str], root: Path = ROOT) -> dict:
    """The rules a feed must meet before it is published or shown. Same rules as the Play to Learn Toolkit."""
    ont = load_ontology(root)
    th = ont["thresholds"]
    feats = {f["id"]: f for f in ont["features"]}
    issues = []

    def add(sev, msg, rule="CORE-DAT-24"):
        issues.append({"severity": sev, "rule": rule, "message": msg})

    forbidden = ont["forbidden_metrics"]
    bad_word = lambda s: any(w in str(s).lower() for w in forbidden)  # noqa: E731
    for n in FEED_FILES:
        if n not in files:
            add("BLOCK" if n != "README.md" else "REVIEW", f"{n} is missing.")
    meta = {}
    if "META.json" in files:
        try:
            meta = json.loads(files["META.json"])
        except json.JSONDecodeError:
            add("BLOCK", "META.json is not valid JSON.")
    if "MANIFEST.json" in files:
        try:
            man = json.loads(files["MANIFEST.json"]).get("files", [])
            entries = man if isinstance(man, list) else [{"path": k, "sha256": v} for k, v in man.items()]
            for e in entries:
                n = str(e.get("path") or e.get("name") or "")
                if n not in files:
                    add("BLOCK", f"MANIFEST.json lists {n}, which is missing.")
                elif sha256_bytes(files[n].encode("utf-8")) != str(e.get("sha256", "")).lower():
                    add("BLOCK", f"{n} does not match its SHA-256 hash in MANIFEST.json: the file changed after the feed was built.")
            if not any(str(e.get("path") or e.get("name")) == "population.tsv" for e in entries):
                add("REVIEW", "MANIFEST.json does not list population.tsv.")
        except (json.JSONDecodeError, AttributeError):
            add("BLOCK", "MANIFEST.json is not valid.")
    else:
        add("REVIEW", "MANIFEST.json is missing: hashes cannot be checked.")
    if meta:
        if meta.get("ontology") != ONTOLOGY:
            add("BLOCK", f"META.json ontology is '{meta.get('ontology')}', not {ONTOLOGY}.")
        t = meta.get("thresholds") or {}
        if int(t.get("min_players") or 0) < th["min_players"] or int(t.get("min_classes") or 0) < th["min_classes"]:
            add("BLOCK", f"Thresholds are {t.get('min_players')} players and {t.get('min_classes')} classes: at least "
                         f"{th['min_players']} and {th['min_classes']} are needed.")
        if meta.get("period") and not PERIOD_RX.match(str(meta["period"])):
            add("BLOCK", f"META.json period is '{meta['period']}': months only (YYYY-MM/YYYY-MM).")
        if meta.get("collected_under") not in ("processor_for_school", "own_study"):
            add("REVIEW", "META.json does not say how the data were collected (collected_under: processor_for_school or own_study).")
        for k in _keys(meta):
            if bad_word(k.rsplit(".", 1)[-1]):
                add("BLOCK", f"META.json key '{k}' is an engagement or commercial metric.", "CORE-DAT-23")
    rows, cols = [], []
    if "population.tsv" in files:
        lines = [ln for ln in files["population.tsv"].splitlines() if ln.strip() and not ln.startswith("#")]
        cols = [c.strip().lower() for c in lines[0].split("\t")] if lines else []
        rows = [dict(zip(cols, [x.strip() for x in ln.split("\t")]), _line=i) for i, ln in enumerate(lines[1:], 2)]
        bad_cols = [c for c in cols if c in ont["forbidden_columns"]]
        if bad_cols:
            add("BLOCK", f"Columns that could point at a person, class, school or moment: {', '.join(bad_cols)}.")
        missing = [c for c in ont["required"] if c not in cols]
        if missing:
            add("BLOCK", f"Missing columns: {', '.join(missing)}.")
        extra = [c for c in cols if c not in COLUMNS and c not in bad_cols]
        if extra:
            add("REVIEW", f"Columns not in {ONTOLOGY}: {', '.join(extra)}.")
        step = int(th.get("round_counts_to", 5))
        for r in rows if not missing else []:
            where = f"Line {r['_line']} ({r.get('unit')}, {r.get('feature')} {r.get('stat')})"
            f = feats.get(r.get("feature"))
            if bad_word(r.get("feature")) or bad_word(r.get("category")) or bad_word(r.get("stat")):
                add("BLOCK", f"{where}: an engagement or commercial metric.", "CORE-DAT-23")
                continue
            if not f:
                add("BLOCK", f"{where}: unknown feature.")
                continue
            if r.get("stat") not in f["stats"]:
                add("BLOCK", f"{where}: stat is not one of {', '.join(f['stats'])}.")
            if f.get("categories") and r.get("category") and r["category"] not in f["categories"]:
                add("REVIEW", f"{where}: category '{r['category']}' is not declared.")
            age, country, period = r.get("age_band") or "all", r.get("country") or "all", r.get("period") or "all"
            if age != "all" and age not in ("B1", "B2", "B3", "B4", "B5"):
                add("BLOCK", f"{where}: age band '{age}' is not B1 to B5.")
            if country != "all" and not re.match(r"^[A-Z]{2}$", country):
                add("BLOCK", f"{where}: country '{country}' is not a two-letter code.")
            if period != "all" and not PERIOD_RX.match(period):
                add("BLOCK", f"{where}: period '{period}' is not month level (YYYY-MM/YYYY-MM).")
            try:
                p, c = int(r.get("players") or 0), int(r.get("classes") or 0)
            except ValueError:
                add("BLOCK", f"{where}: players and classes must be numbers.")
                continue
            if p < th["min_players"] or c < th["min_classes"]:
                add("BLOCK", f"{where}: {p} players in {c} classes, below the thresholds.")
            if p % step:
                add("BLOCK", f"{where}: players ({p}) is not rounded to {step}.")
            v = r.get("value", "")
            if f["kind"] == "context":
                if r.get("stat") == "list" and not re.match(r"^[A-Za-z0-9_,\- ]{0,120}$", v):
                    add("BLOCK", f"{where}: lists hold codes only.")
            else:
                try:
                    x = float(v)
                    if f["kind"] == "share" and not 0 <= x <= 1:
                        add("BLOCK", f"{where}: a share is between 0 and 1.")
                    if f["kind"] == "minutes" and not 0 <= x <= 600:
                        add("REVIEW", f"{where}: minutes out of range.")
                except ValueError:
                    add("BLOCK", f"{where}: value must be a number.")
                if f["id"] == "EV-GAIN" and not r.get("instrument"):
                    add("BLOCK", f"{where}: a learning gain must name its instrument.")
        if not rows:
            add("BLOCK", "population.tsv has no rows.")
    order = {"BLOCK": 0, "REVIEW": 1}
    issues.sort(key=lambda x: order.get(x["severity"], 9))
    counts = {s: sum(1 for i in issues if i["severity"] == s) for s in ("BLOCK", "REVIEW")}
    return {"kind": "feed", "tool": f"{TOOL} {VERSION}", "ok": counts["BLOCK"] == 0, "meta": meta,
            "columns": [c for c in cols], "rows": [{k: v for k, v in r.items() if k != "_line"} for r in rows],
            "issues": issues, "counts": counts}


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
              f"{m.get('player_count', '?')} players in {m.get('class_count', '?')} classes, {m.get('period', '?')}.", ""]
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
                    f'{e(str(m.get("period")))}. Thresholds: {e(str((m.get("thresholds") or {}).get("min_players")))} players and '
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
    bf.add_argument("--class-countries", help="CSV or TSV with instance_id and country, kept by the controller: adds figures per country")
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
            "min_players": a.min_players, "min_classes": a.min_classes,
            "class_countries": read_class_countries(a.class_countries)})
        paths = write_feed(feed, Path(a.out_dir), a.zip)
        res = check_feed(feed["files"])
        f = feed["features"]
        print(f"{TOOL}: {len(f['rows'])} rows, {len(f['suppressed'])} small group(s) left out, feed {'ready' if res['ok'] else 'NOT ready'} | "
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
