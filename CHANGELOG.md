# Changelog

## Unreleased

- **Several countries and shared infrastructure** (`framework/05-several-countries.md`). Many products are
  built for several countries at once, and Member States have started shared education infrastructure.
  - 4 new SHOULD rules: CORE-INT-01 country rules are configuration, not code (tier 3); CORE-INT-02 schools can
    take their data and leave (tier 2, Data Act Chapter VI); CORE-INT-03 sign-in and rosters come from the
    school, with the minimum data (tier 3, feature `accounts`); CORE-INT-04 critical dependencies are declared
    and replaceable (tier 3).
  - 3 manifest checks: `country_config_missing` (two or more countries without a `country_config` file),
    `third_party_jurisdiction_missing`, `critical_dependency_without_fallback`. A static pattern flags
    hard-coded consent ages.
  - Manifest fields: `country_config`; `jurisdiction`, `critical` and `fallback` on third parties.
  - New sources: EDU-EDIC (Commission Implementing Decision (EU) 2026/2413, context only), DATA-ACT (Regulation
    (EU) 2023/2854, Chapter VI), 1EDTECH (LTI 1.3 and OneRoster 1.2).
  - Rules: 114 to 118. Sources: 69 to 72.

## v0.9.0 (2026-11-14)

- **Literacy Compass**, a second lens next to the rules: what does the product teach about digital, media and
  AI literacy, and how do we know? (`framework/04-literacy-compass.md`).
  - `framework/compass/targets.yaml`: 45 targets on 8 axes. Learner lens (INF, COM, CRE, SAF, PRB, AI), counted
    only when the product claims the axis; design lens (TRN transparency that teaches, EDU educator and family
    enablement), universal or feature-triggered. Each target has framework references (DigComp 3.0, AILit,
    UNESCO), sources, terms in English and European Portuguese, improvement, design ideas and, where relevant,
    hidden-curriculum phrases.
  - Evidence ladder per target: 0 Not found, 1 Stated, 2 Designed, 3 Tested, 4 Measured. Plans do not count.
  - Claim checks (unsupported claims, strong claims without measured evidence) and hidden-curriculum conflicts.
  - `tooling/compass.py`: reads `.md`, `.txt`, `.html`, `.pdf`, `.docx` and in-product text (`.json`, `.yaml`,
    `.po`, `.csv`, `.arb`); writes `compass.md`, `compass.html` (compass rose with a needle to the next step,
    CSEF safety status at the centre via `--csef-findings`) and `compass.json`. Never a score or ranking.
  - `framework/compass/crosswalk.yaml`: one dossier, many frameworks (EU guidelines on digital education
    content, Swedish Edtech Kvalitetsportfolio v1.0, UNICEF EdTech for Good 2.0).
  - Packs can amend Compass targets (`compass.amend`) or add their own; the Portugal pack maps targets to the
    *Referencial de Educação para os Media* and Linha Internet Segura.
  - `compass` section in the manifest template; example product `examples/compass/fact-quest` (fictional);
    skill section and `references/compass-review.md`; generated `framework/compass/catalogue.md`; build
    validation; tests.
- 16 new sources: DIGCOMP3, AILIT, UNESCO-MIL, UNESCO-AIMIL, UNESCO-AICFS, UNESCO-AIAGE, EU-DEC, EU-EDUPKG,
  ET4G2, SWE-KP, NL-3E, IEEE3527, IEEE2089, 5R-AICODE, UNICEF-AI, RPF-PRINC; PT-EPM in the Portugal pack.
- Correction: AIA-OMNIBUS is now law (adopted June 2026, published 24 Jul 2026, in force 27 Jul 2026); AIA
  status notes that Art. 4 now asks providers and deployers to take measures to support staff AI literacy.
- **Personal questions**: new manifest feature `survey` (questions to the child or family about the child's
  life, family, opinions, interests or feelings: surveys, "about me" profiles, mood check-ins, onboarding).
  - Eight new core rules: CORE-DAT-13 (purpose and skip, no rewards for answering), CORE-DAT-14 (no data about
    other people), CORE-DAT-15 (no special category or vulnerability questions, including indirect ones, per
    CJEU C-184/20; needs asked as settings; mood check-ins without history or labels), CORE-DAT-16 (who answers
    by age; teenagers' opinions private by default), CORE-DAT-17 (teachers see totals of 5 or more, uniform and
    small cells hidden), CORE-DAT-18 (purpose, deletion, see, correct, delete), CORE-SAF-11 (disclosures in
    open answers and AI chats reach the school's safeguarding lead), CORE-DES-08 (families without one default
    model).
  - `survey` section in `csef.yaml` and six manifest checks (`survey_register_missing`,
    `survey_teacher_view_individual`, `survey_answered_by_child`, `survey_min_group_low`,
    `survey_free_text_without_route`, `survey_research_without_approval`); detection patterns in English and
    European Portuguese for family, third-party and reward-for-answering questions.
  - `templates/survey-register.md`; review-guide section; code-of-conduct topics; questionnaire mechanism and
    boundary question in all six form languages.
  - B-OPS-01 (dashboards show learning, not surveillance) now applies to profile A as well.
  - Portugal pack: PT-SUR-01 (questionnaires in public schools go through MIME approval by EduQA, I.P.,
    formerly DGE; Despacho 15847/2007); sources PT-MIME and PT-LPCJP; notes on CORE-DAT-15, CORE-SAF-11 and B-DAT-01.
  - New sources: CJEU-ART9, EDPB-DDP (Guidelines 03/2022 on deceptive design patterns), WP216 (anonymisation).
- **Compass and personal questions joined**: Compass target TRN-08 (personal questions say why they are asked);
  `survey` makes SAF-02 and COM-05 natural opportunities; evidence collection in pilots and studies follows the
  personal-question rules, and in Portugal MIME approval (EDU-03, next steps).
- Rules: 106 to 114. Sources: 66 to 69 (plus 3 in the Portugal pack).

## v0.8.0 (2026-11-13)

- CSEF brand kit in `brand/` (logo, icons, colour tokens, fonts, GitHub banner and social preview).
- `tooling/brand.py`: one inline logo that follows light and dark mode, brand colour tokens, Space Grotesk and
  Inter with system fallbacks, favicon. Outputs stay self-contained.
- Branded: policy questionnaire (new hero, steps, role colours), staff policy and boundaries report, scan
  dashboard, code-of-conduct report, Pack Builder, Word exports (logo and heading colours), PDF.
- New landing page for companies, designers, educators and developers, with favicons and web manifest.
- README banner. LICENSE: the logo is not under CC BY or Apache; use it to refer to CSEF.
- The questionnaire on the site now makes the whole kit in the browser (Pyodide running `tooling/policy.py`)
  and downloads it as a zip, with Word files. Load an earlier `answers.json` to change the policy; the version
  goes up and the changes are listed. `docs/questionnaire/csef-bundle.json` is generated by `build.py`.
- Site on its own domain: https://csef.kendirstudios.pt
- Questionnaire in English, Portuguese, Spanish, French, Danish, Norwegian and Swedish, with a language
  switch at the start of the page (`framework/i18n/`; `build.py` fails if a translation is incomplete).
  Spanish, French, Danish, Norwegian and Swedish are machine translations, marked as such on the page until
  a native speaker reviews them. The kit documents stay in English for now.
- "Features" are now "mechanisms", each with what it means and the official wording or article it comes from
  (EU KIDS Act proposal, AI Act, DSA, GDPR). New "None of these" options for mechanisms and for who pays,
  with an explanation of what happens.
- AI questions now say they apply only to AI systems (AI Act Art. 3(1)); emotion recognition explains that
  children choosing emotes is not emotion recognition (Art. 3(39)); AI companions quote the KIDS Act
  definition (Art. 3(5)(c)). New question for characters without AI that act like a friend.

## v0.7.0 (2026-11-13)

- Policy questionnaire (`tooling/policy.py`, `framework/questionnaire.yaml`): 31 boundary questions in six
  groups (money and advertising, attention and pressure, contact, AI, data, security), plus organisation,
  products, level, tools and process. Runs in the terminal or as a local web form (`--web`); a static copy is
  on the site.
- Each answer is matched with the tier of the rules behind it (Law, Coming, Recommended) and the chosen level:
  red line, allowed with approval, covered, or recommended but not adopted. Warnings for risky combinations.
- Writes a kit: company pack (validated), boundaries report and plain-language staff policy (Markdown, HTML,
  PDF, Word), AI agent instructions, a CI workflow with the pack, the skill zip and a README.
- Re-runnable: `answers.json` keeps the answers and a version history; each run with changes bumps the policy
  version and lists the changes.
- Pressure-phrase sets in English, Portuguese, Spanish, French, German, Italian and Swedish.
- The `csef-review` skill can run the questionnaire in conversation.

## v0.6.0 (2026-11-12)

- Renamed from Child-Safe EdTech Standard (CSES) to **Child-Safe EdTech Framework (CSEF)**. CSEF is a
  framework, not a formal standard: it is not adopted by a standards body and gives no presumption of
  conformity. Thanks to Swedish EdTech Industry for the feedback.
- Repository renamed to `child-safe-edtech-framework` (GitHub redirects the old URL).
- `standard/` folder is now `framework/`; skill `cses-review` is now `csef-review`; tools report as
  `csef-scan` and `csef-coc`; manifest template `templates/csef.yaml`; workflow template `csef-check.yml`;
  default output folder `csef-report`.
- "Claiming conformance" replaced by "Describing your results" (self-assessment wording) and a new section
  "A framework, not a standard" in the introduction.
- Backward compatible: `cses.yaml` and `.cses/` manifests, `cses-ignore` comments, `--standard-root` and
  `CSES_STANDARD_ROOT` still work. New names take precedence when both exist.
- Rules and sources unchanged (106 rules, 50 sources).

## v0.5.0 (2026-11-12)

- Communications audit (`tooling/comms.py`): inventory of chat SDKs, message tables, direct messages,
  voice, video, comments and live streaming, and of safeguards (report, block, moderation roles, automated
  filters, link and contact-detail filtering, rate limits, preset messages, retention, teacher visibility).
  Shown in `report.md`, the dashboard, PDF and Word.
- Nine communications rules CORE-CHT-01 to 09 (KIDS Act Art. 12, 15(2), Recital 36; DSA Art. 16).
  CORE-SAF-05 also detects random matching, public rooms and global chat.
- Code-of-conduct comparison (`tooling/coc.py`, `standard/coc-topics.yaml`): structure checks from KIDS
  Act Art. 17, 23 and Recital 39, and covered / partial / missing / possible conflict per rule. Markdown,
  HTML and JSON. Fictional example in `examples/codes-of-conduct/`.
- Unity support: Unity Package Manager and External Dependency Manager, Unity text assets (`.prefab`,
  `.asset`, `.unity`), Unity Ads, LevelPlay, IAP, Analytics, Vivox and Photon detection; `examples/unity-sample`.
- More ecosystems: Maven, NuGet, Go modules, Cargo, Composer, Bundler, Swift Package Manager; Rust, C and
  C++, Scala, Elixir and Godot files.
- `standard/legislation.md` and `standard/research.md`.
- Fix: `--out-dir` is now relative to the current directory (it was relative to the scanned repository,
  which broke CI example exports in v0.3 and v0.4).
- CI and templates use `actions/checkout@v5` and `actions/setup-python@v6`.

## v0.4.0 (2026-11-12)

- EU KIDS Act commercial practices (Recital 31, Art. 13): new rules CORE-COM-05 purchases labelled in
  real time, CORE-COM-06 no design for impulsive spending, CORE-COM-07 no disguised advertising (Level 1,
  UCPD Annex I point 11), CORE-COM-08 no commercial content inside learning activities (Level 3).
- EU KIDS Act AI companions and chatbots (Recitals 32 to 34, Art. 14): CORE-AI-08 conversation memory off
  by default, CORE-AI-09 regular re-testing and post-market monitoring, CORE-AI-10 AI assistant inside a
  game or app is opt-in and easy to leave, CORE-AI-11 AI never nudges children to spend.
- CORE-SAF-08 now cites KIDS Act Art. 28(1) and Art. 31 (national guardian attestation and age verification).
- CORE-AI-06 no longer covers memory (moved to CORE-AI-08).

## v0.3.0 (2026-11-11)

- New `tooling/export.py` and `scan.py --export html,pdf,docx`: interactive HTML dashboard (status at
  each level, age bands, colour-coded findings with filters, human-check list with CSV export, improvement
  plan, "for legal counsel" section, sources), PDF and Word exports.
- `findings.json` format 2: includes rule metadata, manifest summary, minimum level and each finding's
  severity at Level 3 (used for per-level views).
- GitHub Action input `export` (default `html`).

## v0.2.0 (2026-11-11)

- Company packs: `policy` section (minimum level, no-gos, forbidden packages and phrases, decision
  records, review cadence, AI agent instructions) and a `policy` source type.
- `tooling/build.py --validate-pack` to validate any pack file.
- Web Pack Builder (`docs/pack-builder/`, on GitHub Pages): build a company pack in a form, then download
  it or publish it to a GitHub repository.
- Example company pack: `examples/company-packs/acme.yaml`.

## v0.1.0 (2026-11-11), draft for public comment

- First public draft: 89 rules (core, profiles A, B, C, age-band modifiers), 50 sources.
- Design-for-learning rules (CORE-DES-*, CORE-ACC-04/05, A-MOT-*) and 28 research sources on visuals,
  motion, rewards and intrinsic motivation, gathered for the EDEH game-based learning squad (Quality Compass).
  Scanner checks for missing reduced-motion handling and reward pile-up.
- Three compliance levels: Legal baseline, Forward-compliant, Best practice.
- Built on the EU KIDS Act proposal COM(2026) 681 (17 Sep 2026), the DSA Art. 28 guidelines, the AI Act as
  amended by the Digital Omnibus on AI, and the leaked draft of the Digital Fairness Act.
- Packs mechanism with a Portugal pack.
- Scanner producing pre-compliance report, improvement plan, JSON and SARIF.
- `cses-review` skill for Claude, GitHub Action, generated Semgrep rules, templates.

### To revisit

- Replace DFA source with the official proposal text once published; confirm rules A-ECO-01, A-ECO-02,
  A-ECO-03, C-ENG-01, CORE-AI-06, CORE-SAF-03.
- Track EU KIDS Act negotiations; feedback period closes 3 Dec 2026.
- Replace the Digital Omnibus secondary source with the Official Journal reference.
