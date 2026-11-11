# Child-Safe EdTech Standard (CSES) v0.1: introduction

Status: **Draft for public comment**, 11 November 2026.

## 1. Purpose

CSES helps EdTech teams build software that children use safely, and prove it. It turns European law,
pending EU proposals and expert recommendations into **rules a team can check in code and in review**.

It gives each product three things:

1. a set of rules selected for its type, its users' ages and the level of ambition the team chooses;
2. a scanner and an AI review skill that produce a **pre-compliance report** and an **improvement plan**, with sources;
3. checklists for what code cannot show.

CSES is **not** a certification and **not** legal advice. Conformance is self-assessed (see section 8).

## 2. Scope

Any software used by minors (under 18) for learning: games, apps, platforms, tools, including AI features.
It applies whether the product is sold to schools, families or institutions.

Key words **MUST** and **SHOULD** follow RFC 2119. A MUST rule is required at its level; a SHOULD rule is
expected unless the team records a reason not to.

## 3. Product profiles

Every product gets the **core** rules. It then declares one or more profiles:

| Profile | What it is | Typical examples |
|---|---|---|
| **A. Educational game** | A game is the learning activity. The child plays to learn. | Maths puzzle game, language adventure, history narrative game |
| **B. Game-based application or software** | A game or simulated environment is the vehicle for another purpose: assessing, training, certifying, rehearsing. Also any product whose results grade, place or certify learners. | Digital-skills assessment in game form, simulator for professional training, serious game used for placement |
| **C. Gamified application** | A non-game product with game elements added: points, badges, levels, streaks, leaderboards, avatars. | Learning platform with XP, homework app with streaks, reading tracker with badges |

How to decide:

1. *Would the product still do its job if you removed the game layer?* Yes: **C**. No: continue.
2. *Is play the main activity the child chooses to do?* Yes: **A**.
3. *Are results used to make decisions about the learner (grade, level, certificate, access)?* Yes: add **B**.

A game with in-game assessment that teachers use for grading is **A + B**. A platform that mixes
mini-games and a points system is **A + C**.

## 4. Age bands

| Band | Ages | Why this cut |
|---|---|---|
| B1 | 3 to 5 | Pre-readers; adult in the loop for everything |
| B2 | 6 to 9 | Early readers; no free-text contact |
| B3 | 10 to 12 | Below the age of 13 used across EU rules (KIDS Act, many national consent ages) |
| B4 | 13 to 15 | Between 13 and 15, the KIDS Act thresholds; national consent ages vary 13 to 16 |
| B5 | 16 to 17 | More autonomy, protective defaults remain |

In practice, age band changes the rules more than product type does. Declare every band that uses the product.

## 5. Compliance levels

The team chooses how far to go. Each rule belongs to one level.

| Level | Name | Includes | Typical use |
|---|---|---|---|
| **1** | Legal baseline | Rules backed by binding law in force, or by law with a fixed application date (e.g. AI Act high-risk on 2 Dec 2027) | Minimum to sell legally today |
| **2** | Forward-compliant | Level 1 plus adopted Commission proposals and official benchmarks: EU KIDS Act proposal, Digital Fairness Act proposal, DSA Art. 28 guidelines, age verification Recommendation | Products for children; avoids rebuilding when proposals become law |
| **3** | Best practice | Level 2 plus research and expert recommendations (UN General Comment 25, EU Kids Online, learning-design and motivation research, see 03-design-and-motivation.md) | Products that want to lead, or tenders that score child-rights design |

Choosing a level does not hide the others. Rules above the chosen level appear in the improvement plan
under *To reach the next level*, so teams can plan ahead.

Levels are checked by the build: a level 1 rule must cite at least one law; a level 2 rule must cite at
least a proposal, guidance or standard.

## 6. Severities in reports

| Severity | Meaning |
|---|---|
| **BLOCK** | High-confidence breach of a MUST rule at the chosen level. Fix or waive before release. |
| **REVIEW** | Pattern suggests a breach of a MUST rule; a person must confirm. |
| **WARN** | A SHOULD rule at the chosen level is not met. |
| **HUMAN** | The rule applies but code cannot show it; a person checks it. |
| **NEXT** | Signal against a rule above the chosen level. Not a failure. |
| **WAIVED** | Accepted gap with reason, named approver and expiry. |

## 7. Extending the standard

National laws, sector rules, literature and company red lines are added through **packs**
(see [02-packs.md](02-packs.md)). Packs can add sources and rules, and make existing rules stricter. They
can never weaken a rule. This keeps one shared baseline across Europe while respecting national rules.

## 8. Claiming conformance

Allowed wording:

> "Self-assessed against CSES v0.1, Level 2, profiles Core + A, age bands B2 to B3, with the PT pack, on 2026-11-11.
> No open blocking findings; N waivers recorded."

Not allowed: "CSES certified", "compliant with the KIDS Act", or any badge implying third-party approval.

## 9. What CSES does not cover

Contracts, legal bases and the work of the controller (often the school); content quality and curriculum
alignment; physical hardware safety; and the full DSA obligations of very large platforms.
