---
name: csef-review
description: Pre-compliance review of a codebase used by children (educational games, game-based applications, gamified apps) against the Child-Safe EdTech Framework (CSEF, formerly CSES), covering GDPR, DSA, AI Act, EU KIDS Act and DFA proposals, accessibility and national packs. Produces a pre-compliance report and a prioritised improvement plan with sources, an interactive dashboard, PDF and Word exports, a communications audit, and code-of-conduct gap analysis. Use when asked to check, audit or review child safety, children's privacy or EU compliance of an app, game, repository or code of conduct.
---

# CSEF review

You review a product repository against the Child-Safe EdTech Framework and produce two deliverables:

1. `csef-report/report.md`: the **pre-compliance report** (scope, findings, human checks, sources)
2. `csef-report/improvements.md`: the **improvement plan**, prioritised, with sources

You never declare a product "compliant" or "legal". The strongest statement allowed is:
"No blocking issues found at Level N by automated and manual review on <date>." Always keep the
disclaimer that this is not legal advice.

Bundled files (paths relative to this skill folder):
- `scripts/scan.py`: the deterministic scanner (needs Python 3.10+ and PyYAML)
- `framework/rules.yaml`, `framework/sources.yaml`: rules and source registry (the only sources you may cite)
- `packs/*.yaml`: national and extra packs; `packs/_template.yaml` shows how to write one
- `references/review-guide.md`: what to inspect by hand, per profile
- `references/report-additions.md`: how to add your judgement to the generated report
- `templates/`: manifest, DPIA starter, AI risk file, waiver record, agent instructions

## Workflow

### 1. Establish scope

Look for `csef.yaml` (or `.cses/manifest.yaml`) at the repository root.

- If it exists, read it. Check that the declared `features` match what you see in the code.
- If it is missing, infer profiles, age bands and features from the code and README, write a draft
  `csef.yaml` from `templates/csef.yaml`, and tell the user which values are assumptions. Ask the user only
  for what you cannot infer and that changes the result: **age bands**, **compliance level**, and
  **whether schools operate the product** (this decides EU KIDS Act scope).

Profiles: **A** educational game (play is the learning activity), **B** game-based application
(a game or simulation used for assessment, training or another non-play purpose; also anything whose
results are used to grade, place or certify learners), **C** gamified application (a non-game product
with points, badges, streaks, leaderboards). A product can be more than one.

Compliance levels: **1** Legal baseline (binding law), **2** Forward-compliant (adds adopted proposals
and official benchmarks: EU KIDS Act, DFA, DSA Art. 28 guidelines), **3** Best practice (adds research and
expert recommendations). Default to the manifest; if absent, recommend 2 for products used by children.

National packs: add the country codes to `jurisdictions`. If the user names a law, guideline or paper that
is not in the registry, offer to write a pack for it (see `packs/_template.yaml`) instead of citing it ad hoc.

### 2. Run the scanner

```bash
pip install pyyaml  # if missing
python3 <skill-folder>/scripts/scan.py --repo <repo> --out-dir <repo>/csef-report
# options: --level 1|2|3   --pack path/to/extra-pack.yaml   --format json
```

It writes `report.md`, `improvements.md`, `findings.json`, `findings.sarif` into the output folder
(relative paths are relative to the current directory).

When the user wants something to share with non-developers (product owners, clients, legal counsel), add
`--export html,pdf,docx` (or run `scripts/export.py --input csef-report/findings.json --formats ...`). It writes
`dashboard.html` (interactive), `report.pdf` (needs Chrome/Chromium) and `report.docx` (needs python-docx).
Re-export after you finalise the Markdown files, and say that the dashboard reflects the automated scan,
while your reviewer assessment is in `report.md`.

### 3. Verify every automated finding

Open each location in `findings.json` with severity BLOCK, REVIEW or WARN.

- **Confirm** it when the code really does what the rule forbids.
- **Dismiss** it when it is a false positive (e.g. a word in a comment, test fixture for the rule itself,
  admin-only screen). Record dismissals with the reason; never silently drop a finding.
- **Re-grade** REVIEW items to BLOCK when confirmed against a MUST rule.

### 4. Review what the scanner cannot see

Use `references/review-guide.md`. Read the code paths it lists for each declared profile and feature:
settings defaults, notification scheduling, reward and economy logic, social and contact features,
AI system prompts and memory, data models and access policies, analytics events, age gates.
Turn what you find into findings with the rule id, file and line. For human checks you can partly answer
from code (e.g. defaults in a settings model), say what the code shows and what still needs a person.

### 5. Finalise both deliverables

Edit the generated `report.md` and `improvements.md` following `references/report-additions.md`:
add a "Reviewer assessment" section, your confirmed and dismissed findings, and any new findings.

Rules for sources:
- Cite only ids present in `framework/sources.yaml` or a loaded pack. Every finding keeps its sources.
- If a statement needs a source that is not in the registry, propose adding it through a pack; do not
  invent citations or URLs.
- Keep the status and `verified` date shown: proposals (KIDS Act, DFA) are not law yet.

### 6. Report back

Summarise in a few lines: level, number of blocking issues, the top three improvements, and what needs a
human (DPO, legal, product owner). Link both files.

## Important nuances

- **EU KIDS Act scope.** Art. 2(4)(c) exempts services designed primarily for education *and operated by or
  on behalf of educational establishments*. The same game can be exempt in a school deployment and in
  scope when sold to families. At Level 2 and above, CSEF applies the KIDS Act measures as good practice
  in both cases; say which situation applies.
- **Educational AI** is excluded from "general conversational chatbot" (Art. 3(5)(d)) but becomes an
  "AI companion" if it simulates a relationship. Check personas and memory.
- **Proposals change.** If the user asks about the current state of the KIDS Act or DFA, check the
  official source before answering; the registry has a `verified` date.
- **Roles.** In school deployments the provider is usually a processor. Many obligations (DPIA, legal
  basis) sit with the school; the report should say what the provider must supply.

## Communications audit

The scan includes a communications inventory (`findings.json` > `communications`, and a section in
`report.md` and the dashboard): channels found (chat SDKs, message tables, voice and video, comments,
live streaming) and safeguards found (report, block, moderation roles, filters, link filtering, rate
limits, preset messages, retention, teacher visibility). A safeguard "not found" may live in a service
dashboard (for example the chat provider's moderation settings) or a backend outside the repository.
Look for it, ask the user if needed, and say which you confirmed. CORE-CHT-08 (safeguarding procedure)
is always a human check.

## Code of conduct comparison

When the user wants to check a code of conduct (an industry code, their own code, a draft code under the
EU KIDS Act), follow `references/coc-review.md`. In short:

```bash
python3 <skill-folder>/scripts/coc.py --input code.pdf --name "Code name" --level 2 --profiles A,C --bands B2,B3 --out-dir coc-report
```

It writes `coc-comparison.md`, `.html` and `.json`: structural criteria from the KIDS Act (Art. 17, 23,
Recital 39) and, per rule, covered, partial, missing or possible conflict. The tool matches wording;
you then read the code and confirm or correct every result by meaning, in any language.

## Company policy questionnaire

When someone wants to set or change their organisation's boundaries ("define our policy", "what are our red
lines", "make a pack like Kendir's"), run the questionnaire with them:

1. If they have an earlier `answers.json`, read it and only ask what they want to change.
2. Otherwise ask the questions in `framework/questionnaire.yaml`, section by section, in their language.
   Skip boundary questions whose `features` or `profiles` do not match their answers. For each boundary, say
   whether it is Law (tier 1), Coming (tier 2) or Recommended (tier 3), and offer Never, Only with approval
   (when the question has an `approval` text) or Follow our level.
3. Write the answers to `answers.json` as `{"answers": {...}}` using the question ids and option values.
4. Run `python3 scripts/policy.py --answers answers.json --batch --out-dir <id>-policy`.
5. Share the staff policy and the boundaries report, point out the "Check these first" warnings, and explain
   that answers can only make rules stricter: an approval never switches off a rule that applies at their level.

People who prefer a form can run `python3 tooling/policy.py --web` from the repository.

## Limits to state in every report

- Static analysis reads files; it does not run the product, inspect live databases, cloud consoles or
  third-party dashboards.
- Contracts, legal bases, DPIAs, moderation practice and safeguarding procedures are human checks.
- Binary engine assets (Unreal Blueprints, GameMaker, Construct) and no-code tools without a repository
  cannot be scanned; review them by hand or from exported configuration.
