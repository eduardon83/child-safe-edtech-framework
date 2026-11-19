#!/usr/bin/env python3
"""Make the fictional sample event file for Garden of Numbers (examples/evidence-feed/events.tsv).

Synthetic data, no real children: 6 classes, 2 sessions per player, a pre and a post check, four units.
One class has only 4 players and the bonus level 5 is reached by few, so build-feed shows how small cells are removed.
The output is deterministic (fixed seed), so the file in the repository can be rebuilt and compared.

  python3 examples/evidence-feed/make_sample.py
"""
from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "events.tsv"
COLS = ["game_id", "instance_id", "player_id", "session_id", "timestamp", "offset", "session_sequence_index",
        "event_name", "event_source", "source_hash", "event_data", "game_state", "player_metadata", "game_version", "game_log_version"]


def main():
    rnd = random.Random(20261119)
    hexid = lambda n: "".join(rnd.choice("0123456789abcdef") for _ in range(n))  # noqa: E731
    classes = [(f"c{hexid(8)}", n) for n in (12, 11, 12, 10, 11, 4)]
    rows = []
    day0 = dt.datetime(2026, 9, 21, 9, 0)
    for ci, (cls, size) in enumerate(classes):
        mode = ["solo", "team", "teacher_led", "solo", "team", "solo"][ci]
        for _ in range(size):
            pid = f"p{hexid(10)}"
            meta = {"age_band": "B2"}
            settings = [s for s, pr in (("captions", .2), ("text_size", .15), ("reduced_motion", .1)) if rnd.random() < pr]
            skill = rnd.uniform(0.6, 1.4)
            pre = rnd.randint(3, 7)
            reached = 0
            for s in range(2):
                sid = f"{rnd.randint(10**15, 10**16 - 1)}"
                t = day0 + dt.timedelta(days=ci * 9 + s * 7, minutes=rnd.randint(0, 40))
                seq = 0
                ev = []

                def log(name, data, src="GAME", unit=None, dt_s=0):
                    nonlocal t, seq
                    t = t + dt.timedelta(seconds=dt_s)
                    gs = {"unit": unit, "mode": mode} if unit else {"mode": mode}
                    ev.append([ "garden-of-numbers", cls, pid, sid, t.strftime("%Y-%m-%d %H:%M:%S"), "+1:00:00", str(seq), name, src,
                                "a63eb9" if src == "GAME" else "d41f02", json.dumps(data), json.dumps(gs), json.dumps(meta),
                                "1.4.0-study", "3"])
                    seq += 1

                log("session_start", {"device": rnd.choice(["tablet", "tablet", "laptop", "desktop"])})
                log("mode_set", {"mode": mode}, dt_s=5)
                if s == 0:
                    for st in settings:
                        log("setting_changed", {"setting": st, "on": True}, dt_s=4)
                    log("check_score", {"phase": "pre", "score": pre, "max": 10}, dt_s=rnd.randint(120, 240))
                units = ["lvl1", "lvl2"] if s == 0 else ["lvl3", "lvl4", "lvl5"]
                for u in units:
                    if (u == "lvl4" and rnd.random() > 0.35) or (u == "lvl5" and rnd.random() > 0.2):
                        break
                    log("unit_start", {"unit": u}, unit=u, dt_s=rnd.randint(5, 20))
                    steps = max(3, int(rnd.gauss(9, 2) * skill * (1 + 0.25 * int(u[-1]))))
                    hinted = False
                    for k in range(steps):
                        if not hinted and rnd.random() < 0.012 * int(u[-1]):
                            log("hint_used", {"unit": u}, unit=u, dt_s=rnd.randint(20, 70))
                            hinted = True
                            if rnd.random() < 0.4:
                                log("stuck", {"unit": u}, src="StuckDetector", unit=u, dt_s=1)
                        else:
                            log("answer", {"unit": u, "correct": rnd.random() < 0.7}, unit=u, dt_s=rnd.randint(20, 75))
                    if rnd.random() < 0.035 * int(u[-1]):
                        break  # the lesson ends before the unit is finished
                    log("unit_complete", {"unit": u, "attempts": rnd.randint(1, 3)}, unit=u, dt_s=rnd.randint(10, 40))
                    reached = int(u[-1])
                if s == 1:
                    post = min(10, pre + rnd.randint(0, 4) + (1 if reached >= 3 else 0))
                    log("check_score", {"phase": "post", "score": post, "max": 10}, dt_s=rnd.randint(120, 240))
                log("session_end", {"natural_stop": rnd.random() < 0.85}, dt_s=10)
                rows += ev
    OUT.write_text("\t".join(COLS) + "\n" + "\n".join("\t".join(r) for r in rows) + "\n", encoding="utf-8")
    print(f"{OUT}: {len(rows)} events")


if __name__ == "__main__":
    main()
