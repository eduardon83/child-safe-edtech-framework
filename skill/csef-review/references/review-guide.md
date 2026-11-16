# Manual review guide

The scanner finds patterns. These are the places to read by hand, and the rules each one informs.
What to check is in each rule's requirement: see the [rule catalogue](../../../framework/catalogue/index.md)
(in the skill, `framework/rules.yaml`). This guide only says where to look, so it cannot drift from the rules.

## All products (core)

| Where to look | Rules |
|---|---|
| Settings model, user defaults, migrations that create users | CORE-SAF-01, CORE-SAF-02, CORE-DAT-09, CORE-DAT-10 |
| Notification scheduler, email and push campaigns | CORE-SAF-02 |
| Analytics wrapper and event definitions | CORE-DAT-04, CORE-COM-02 |
| Data models (DB schema, ORM models) | CORE-DAT-01, CORE-DAT-05 |
| Access policies (RLS, security rules, API middleware) | CORE-SEC-02 |
| Deletion and export jobs, admin tools | CORE-DAT-05, CORE-DAT-06 |
| Seeds, fixtures, test data, staging config | CORE-DAT-07 |
| Login and onboarding | CORE-SEC-06, CORE-SAF-08, AGE-B3-01 |
| Child-facing copy (i18n files) | CORE-COM-03, CORE-DAT-12 |
| Help and report screens, report outcome messages | CORE-SAF-06, PT-SUP-01 |
| UI components | CORE-ACC-01, CORE-ACC-02 |

## Personal questions (feature `survey`)

| Where to look | Rules |
|---|---|
| Question sets, onboarding, "about me" screens, mood check-ins, i18n files | CORE-DAT-13 |
| Question wording, AI system prompts | CORE-DAT-14, CORE-DAT-15 |
| Who answers (guardian page, child flow) | CORE-DAT-16 |
| Teacher dashboards and exports | CORE-DAT-17, B-OPS-01 |
| Storage, deletion, personalisation code | CORE-DAT-18, B-DAT-01 |
| Open questions, voice answers, AI chats | CORE-CHT-08 |
| Family-themed content and illustrations | CORE-DES-08 |
| Portugal | PT-SUR-01 |

## Several countries and shared infrastructure

| Where to look | Rules |
|---|---|
| Consent, retention, approvals, helplines, languages | CORE-INT-01 |
| Export and offboarding | CORE-INT-02 |
| Sign-in and roster import | CORE-INT-03 |
| Third parties, AI model calls | CORE-INT-04 |

## Communication and bullying (features `chat`, `multiplayer`, `social`, `ugc`)

| Where to look | Rules |
|---|---|
| Every way children interact: chat, emotes, reactions, avatar names, drawings, shared worlds | CORE-CHT-01 |
| Report and block actions on messages, creations and profiles | CORE-CHT-02 |
| Report acknowledgement, outcome and "still happening" screens | CORE-SAF-06 |
| Moderator and teacher views of reports; anything other children can see after a report | CORE-CHT-10 |
| Report flow for "this is happening to someone else"; handling of unfounded reports | CORE-CHT-11 |
| Team and pair forming, votes, ratings, polls, friend lists, online status, cosmetic shop items | CORE-CHT-12 |
| "My reports" view, evidence records, helpline links, national app integration | CORE-CHT-13 |
| `moderation` in csef.yaml, open hours, out-of-hours behaviour, response times | CORE-CHT-14 |
| School set-up: anti-bullying contact or default procedure; report categories; school totals | CORE-CHT-15 |
| Safeguarding procedure document | CORE-CHT-08 |

## AI features

| Where to look | Rules |
|---|---|
| System prompts, persona definitions | CORE-AI-06 |
| Conversation memory and user profiles | CORE-AI-06 |
| Provider configuration | CORE-AI-04, CORE-DAT-02 |
| Input and output filters | CORE-AI-05 |
| Red-team sets, eval schedule, incident log | CORE-AI-09 |
| Image, video and voice generation; prompt handling; uploads | CORE-AI-12 |
| UI around AI output | CORE-AI-03 |
| Any use of camera, microphone or typing dynamics | CORE-AI-01, B-EVL-02 |

## Look, sound, motion and rewards (all profiles)

| Where to look | Rules |
|---|---|
| Animations, transitions, celebration effects | CORE-ACC-04, CORE-DES-01, CORE-DES-02, CORE-DES-06 |
| Screens for under-8s | CORE-DES-03, CORE-DES-04 |
| Feedback states (right/wrong) | CORE-ACC-05, A-MOT-02 |
| Maths graphics and diagrams | CORE-DES-05 |
| Every reward layer | A-MOT-01, A-MOT-03 |
| Helping, collaboration, creative tasks | A-MOT-05 |

## Profile A, educational games

| Where to look | Rules |
|---|---|
| Economy: shop, currency, rewards tables | A-ECO-01, A-ECO-02, A-ECO-03 |
| Progression and timers | A-PLY-01 |
| Reward mapping | A-MOT-01 |
| Multiplayer rooms and matchmaking | CORE-SAF-05 |
| Assessment hooks inside gameplay | A-ASM-01 |

## Profile B, game-based applications

| Where to look | Rules |
|---|---|
| Scoring, levelling, placement logic | B-EVL-01, B-EVL-03, CORE-AI-07 |
| Test delivery | B-EVL-02, B-EVL-04 |
| User-generated content | B-UGC-01, B-UGC-02 |
| Research exports | B-DAT-01 |
| Dashboards | B-OPS-01 |

## Profile C, gamified applications

| Where to look | Rules |
|---|---|
| Streak logic and copy | C-ENG-01 |
| Leaderboards | C-ENG-02 |
| Points and badges | C-ENG-03 |
| Bonus and reward schedule | C-ENG-04 |
| Product metrics and goals | C-ENG-05 |
| Quests and challenges | C-ENG-06 |
