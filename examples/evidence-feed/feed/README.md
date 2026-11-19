# Garden of Numbers: open evidence

Group figures from play, in the csef-evidence-0.1 format of the Child-Safe EdTech Framework (CSEF). They describe how groups of pupils played, never one pupil or one class.

| | |
|---|---|
| Game | Garden of Numbers (https://example.org/garden-of-numbers) |
| Maker | Example Studio (https://example.org) |
| Period | 2026-09/2026-11 |
| Players (rounded to 5) | 60 in 6 classes |
| Age bands | B2 |
| Countries | ES, PT |
| Collected | in the maker's own study (Example University ethics committee, ref. 2026-031) |
| Thresholds | at least 10 players and 3 classes behind every row; 5 small group(s) left out |
| Licence | CC0-1.0 |

## population.tsv

One row per figure. Tab-separated.

| Column | Meaning |
|---|---|
| unit | A unit of play (level, mission, chapter), or 'Whole game'. |
| unit_order | 0 for the whole game; 1, 2, 3 for units in playing order. |
| feature | One of the feature ids below. |
| category | For features with categories (a setting, a mode, a device, a context item). Empty otherwise. |
| stat | One of the feature's stats. |
| value | A number; a list of codes for CONTEXT lists. |
| players | Players behind the row, rounded to 5. At least min_players. |
| classes | Classes behind the row. At least min_classes. |
| age_band | all, or B1 to B5. |
| country | all, or a two-letter country code. |
| period | YYYY-MM/YYYY-MM, or all. |
| instrument | The pre and post check, required for EV-GAIN. A short name. |

| Feature | Stats | Meaning |
|---|---|---|
| EV-TIME | p25, p50, p75 | Active minutes to finish a unit, among players who finished it (for the whole game: active minutes played in total). Gaps over 60 seconds count as 60. |
| EV-DONE | share | Share of players who started the unit and finished it. |
| EV-STUCK | share | Share of players a detector marked as stuck (in the unit, or anywhere for the whole game). |
| EV-HELP | share | Share of players who used a hint or help (in the unit, or anywhere for the whole game). |
| EV-GAIN | pre, post, change, effect_size | Mean score before and after (score / max), the mean change, and the paired effect size (mean change / its standard deviation), for players with both checks. The instrument is named on every row. |
| EV-ACCESS | share | Share of players who turned on each accessibility setting. |
| EV-STOP | share | Share of sessions that ended at a natural stopping point. |
| EV-MODE | share | Share of sessions played solo, in teams or teacher-led. |
| EV-DEVICE | share | Share of sessions per device class. |
| CONTEXT | count, list | Who stands behind the feed: counts, and lists of codes. |

## How to cite

Example Studio. Garden of Numbers: open evidence (2026-09/2026-11). csef-evidence-0.1.

## Not in this file

No player codes, sessions, timestamps, schools, classes or free text. No retention, daily users, streaks or revenue.
Figures are the maker's own unless a researcher or curator has checked the method.
