---
name: cses-review
description: Pre-compliance review of a codebase used by children (educational games, game-based applications, gamified apps) against the Child-Safe EdTech Standard (CSES), covering GDPR, DSA, AI Act, EU KIDS Act and DFA proposals, accessibility and national packs. Produces a pre-compliance report and a prioritised improvement plan, both with sources. Use when asked to check, audit or review child safety, children's privacy or EU compliance of an app, game or repository.
---

# CSES review

You review a product repository against the Child-Safe EdTech Standard and produce two deliverables:

1. `cses-report/report.md`: the **pre-compliance report** (scope, findings, human checks, sources)
2. `cses-report/improvements.md`: the **improvement plan**, prioritised, with sources

You never declare a product "compliant" or "legal". The strongest statement allowed is:
"No blocking issues found at Level N by automated and manual review on <date>." Always keep the
disclaimer that this is not legal advice.

Bundled files (paths relative to this skill folder):
- `scripts/scan.py`: the deterministic scanner (needs Python 3.10+ and PyYAML)
- `standard/rules.yaml`, `standard/sources.yaml`: rules and source registry (the only sources you may cite)
- `packs/*.yaml`: national and extra packs; `packs/_template.yaml` shows how to write one
- `references/review-guide.md`: what to inspect by hand, per profile
- `references/report-additions.md`: how to add your judgement to the generated report
- `templates/`: manifest, DPIA starter, AI risk file, waiver record, agent instructions

## Workflow

### 1. Establish scope

Look for `cses.yaml` (or `.cses/manifest.yaml`) at the repository root.

- If it exists, read it. Check that the declared `features` match what you see in the code.
- If it is missing, infer profiles, age bands and features from the code and README, write a draft
  `cses.yaml` from `templates/cses.yaml`, and tell the user which values are assumptions. Ask the user only
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
python3 <skill-folder>/scripts/scan.py --repo <repo> --out-dir cses-report
# options: --level 1|2|3   --pack path/to/extra-pack.yaml   --format json
```

It writes `report.md`, `improvements.md`, `findings.json`, `findings.sarif` into `<repo>/cses-report/`.

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
- Cite only ids present in `standard/sources.yaml` or a loaded pack. Every finding keeps its sources.
- If a statement needs a source that is not in the registry, propose adding it through a pack; do not
  invent citations or URLs.
- Keep the status and `verified` date shown: proposals (KIDS Act, DFA) are not law yet.

### 6. Report back

Summarise in a few lines: level, number of blocking issues, the top three improvements, and what needs a
human (DPO, legal, product owner). Link both files.

## Important nuances

- **EU KIDS Act scope.** Art. 2(4)(c) exempts services designed primarily for education *and operated by or
  on behalf of educational establishments*. The same game can be exempt in a school deployment and in
  scope when sold to families. At Level 2 and above, CSES applies the KIDS Act measures as good practice
  in both cases; say which situation applies.
- **Educational AI** is excluded from "general conversational chatbot" (Art. 3(5)(d)) but becomes an
  "AI companion" if it simulates a relationship. Check personas and memory.
- **Proposals change.** If the user asks about the current state of the KIDS Act or DFA, check the
  official source before answering; the registry has a `verified` date.
- **Roles.** In school deployments the provider is usually a processor. Many obligations (DPIA, legal
  basis) sit with the school; the report should say what the provider must supply.
