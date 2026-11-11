# Manual review guide

The scanner finds patterns. These are the places to read by hand. For each, the rules it informs.

## All products (core)

| Look at | What to check | Rules |
|---|---|---|
| Settings model, user defaults, migrations that create users | Private, sharing off, notifications off, location/mic/camera off by default | CORE-SAF-01, CORE-SAF-02, CORE-DAT-09, CORE-DAT-10 |
| Notification scheduler, email and push campaigns | Only own activity or teacher assignments; no re-engagement; quiet hours | CORE-SAF-02 |
| Analytics wrapper and event definitions | No identifiers or free text; pseudonymous IDs; vendor and region | CORE-DAT-04, CORE-COM-02 |
| Data models (DB schema, ORM models) | Data categories match the manifest; nothing collected "just in case" | CORE-DAT-01, CORE-DAT-05 |
| Access policies (RLS, security rules, API middleware) | Every learner table protected at the data layer; class and role scoping | CORE-SEC-02 |
| Deletion and export jobs, admin tools | Retention enforced; per-learner export and erasure exist | CORE-DAT-05, CORE-DAT-06 |
| Seeds, fixtures, test data, staging config | Synthetic only | CORE-DAT-07 |
| Login and onboarding | No email or phone for children; age gate proportionate; guardian or school activation under 13 | CORE-SEC-06, CORE-SAF-08, AGE-B3-01 |
| Child-facing copy (i18n files) | No pressure, guilt or scarcity; understandable for the band | CORE-COM-03, CORE-DAT-12 |
| Help and report screens | One step away; priority handling; national helplines | CORE-SAF-06, PT-SUP-01 |
| UI components | Alt text, labels, contrast, keyboard, reduced motion | CORE-ACC-01, CORE-ACC-02 |

## AI features

| Look at | What to check | Rules |
|---|---|---|
| System prompts, persona definitions | No feelings, friendship, missing the child, exclusivity | CORE-AI-06 |
| Conversation memory and user profiles | Memory off by default; no use of past chats except for safety | CORE-AI-06 |
| Provider configuration | No-training / zero-retention settings; region; processor agreement | CORE-AI-04, CORE-DAT-02 |
| Input and output filters, eval sets | Age-appropriate filters; red-team set per language | CORE-AI-05 |
| UI around AI output | Visible AI label; generated media marked | CORE-AI-03 |
| Any use of camera, microphone or typing dynamics | No emotion inference, no proctoring | CORE-AI-01, B-EVL-02 |

## Profile A, educational games

| Look at | What to check | Rules |
|---|---|---|
| Economy: shop, currency, rewards tables | No paid randomness, no pay-to-win, currency not sold to children, euro value shown | A-ECO-01, A-ECO-02, A-ECO-03 |
| Progression and timers | No energy refill timers, decay, punishment for absence | A-PLY-01 |
| Reward mapping | Rewards tied to learning mechanics, not to time or logins | A-ECO-04 |
| Multiplayer rooms and matchmaking | Closed groups, teacher-controlled; no external handles or links | A-SOC-01, CORE-SAF-05 |
| Assessment hooks inside gameplay | Disclosed; stored separately; purpose-bound | A-ASM-01 |

## Profile B, game-based applications

| Look at | What to check | Rules |
|---|---|---|
| Scoring, levelling, placement logic | Human confirmation; explanation; contest route; risk file if AI | B-EVL-01, B-EVL-03, CORE-AI-07 |
| Test delivery | No webcam/biometric proctoring; accommodations | B-EVL-02, B-EVL-04 |
| User-generated content | Moderation, teacher visibility, EXIF stripping, no public galleries | B-UGC-01, B-UGC-02 |
| Research exports | Agreement, pseudonymisation, logging | B-DAT-01 |
| Dashboards | Learning view, not surveillance | B-OPS-01 |

## Profile C, gamified applications

| Look at | What to check | Rules |
|---|---|---|
| Streak logic and copy | Optional, no loss framing, no reset penalty | C-ENG-01 |
| Leaderboards | Class scope, nicknames, teacher toggle | C-ENG-02 |
| Points and badges | No money value or purchase path | C-ENG-03 |
| Bonus and reward schedule | Predictable rewards, no spins or random drops | C-ENG-04 |
| Product metrics and goals | Learning and wellbeing metrics next to engagement | C-ENG-05 |
| Quests and challenges | No anxiety timers for under-13s | C-ENG-06 |
