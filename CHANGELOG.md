# Changelog

Newest first. One short entry per version; the full story of each release is in [docs/releases/](docs/releases/).
Open items and what we are watching: [legislation.md, watch list](framework/legislation.md#open-discussions-and-watch-list).

## v0.14.0 (2026-11-19)

- **Learning data** ([08-learning-data.md](framework/08-learning-data.md), online at csef.kendirstudios.pt/learning-data/):
  a child-safe profile of the Open Game Data event standard (`framework/data/profile.yaml`), four data tiers, and
  an open evidence feed format, csef-evidence-0.1 (`framework/data/evidence-ontology.yaml`): one row per figure
  (time per unit, completion, stuck, help, learning gain, accessibility, natural stops, play mode, devices), for
  everyone and per age band, country and period; at least 10 players and 3 classes per row, counts rounded to 5,
  periods to the month. Same layout as the Play to Learn Toolkit.
- New rules: CORE-DAT-19 event catalogue, CORE-DAT-20 random product-scoped player codes, CORE-DAT-21 no
  fingerprinting in telemetry, CORE-DAT-22 inferences at population level (level 2), CORE-DAT-23 no engagement
  targets for children (SHOULD, level 2), CORE-DAT-24 open releases hold group figures only, CORE-DAT-25 research
  logging only in a study build. B-DAT-01 adds the study build and "keys stay home".
- `tooling/evidence.py`: check-events, build-feed, check-feed. `data_collection` block in csef.yaml with five
  manifest checks; event names in code compared with the catalogue; `templates/event-catalogue.yaml`.
  The metadata export links a product's feed.
- **Workbench** (csef.kendirstudios.pt/workbench/): every check that does not read code, in the browser, for
  designers, decision makers and researchers. A form writes csef.yaml; documents stay on the computer.
  `scan.py --description-only` and `tooling/workbench.py` run the same on a computer.
- Guides can be published as website pages (`tooling/mdpage.py`). Example reports for researchers.
- New sources: EDPB-PSEUDO, CJEU-SRB, EDPB-ART53, OMNIBUS-DATA (watch list), R-OGD2024, R-OGD-EDS.
- Rules: 124 to 131. Sources: 83 to 89, plus 9 in the Portugal pack.

## v0.13.0 (2026-11-18)

- **Serious-game pre-check** (`tooling/precheck.py`, [07-labels-and-metadata.md](framework/07-labels-and-metadata.md)):
  22 quality criteria (Caserman et al. 2020) mapped to CSEF rules and Compass targets in
  `framework/serious-games/criteria.yaml`. Statuses ready, partial, missing or CSEF issue. Statements with
  evidence go in a new `serious_game` block in csef.yaml. Where the criteria recommend competition or emotional
  hooks, CSEF limits apply for children.
- **Metadata export** (`tooling/metadata.py`): a new `metadata` block; SG-MDF (DIN SPEC 91380) Core and
  learning-games profile as JSON and XML (CSEF serialisation; the DIN SPEC has no official schema), and
  schema.org LearningResource JSON-LD. The required data statement is written from what csef.yaml declares.
- **Label package**: metadata, findings, pre-check, evidence index, MANIFEST.json with SHA-256 hashes, zipped.
- New sources: R-CASERMAN2020, DIN-SPEC-91380. Example: the compliant game now has metadata and statements.
- **Website** (csef.kendirstudios.pt): new home page that starts with "Let's get you started" (six paths,
  with suggestions by role) and a section per path; example reports for each audience in `docs/examples/`
  (dashboards, PDF and Word reports, policy kit, Compass, code-of-conduct comparison, pre-check, metadata,
  label package), made by `tooling/examples.py`; a submission preview in `docs/submit/` (nothing is sent).
  The build checks every local link on the site.
- Rules unchanged (124). Sources: 81 to 83, plus 9 in the Portugal pack.

## v0.12.0 (2026-11-17)

- **In-game purchases, as EU consumer authorities read the law.** New sources: CPC-VC (CPC Network Key Principles
  on in-game virtual currencies, 2025), CPC-JS (Joint Statement on video games and coordinated actions against
  nine game companies, 30 Sep 2026), CRD (Consumer Rights Directive), UCTD (Unfair Contract Terms Directive).
- New MUST rules: CORE-COM-09 clear purchase information and a working 14-day withdrawal, unused currency
  included; CORE-COM-10 fair, plain terms (no one-sided changes to bought content or currency value, bans with a
  reason and an appeal). Both apply with feature `purchases`.
- A-ECO-03 now asks for real prices everywhere, one purchasable currency and exact amounts, and applies to
  profile B too. CORE-COM-04 adds exhortation to ask adults, products likely to appeal to children, and spending
  off by default. CORE-COM-03, COM-05, COM-06, A-ECO-01 and Compass TRN-04 cite the CPC texts.
- DFA source updated to the official proposal, COM(2026) 1100 (11 Nov 2026). Watch list: CPC actions on games.
- Detection of "all sales final" and "we may change or remove your currency" wording.
- Rules: 122 to 124. Sources: 77 to 81, plus 9 in the Portugal pack.

## v0.11.0 (2026-11-16)

- **Bullying and peer safety** ([06-bullying.md](framework/06-bullying.md)): six SHOULD rules, CORE-CHT-10 reports
  stay confidential, CORE-CHT-11 report for a friend (misuse handled by people, never automatic penalties),
  CORE-CHT-12 no design that lets children exclude or rank each other, CORE-CHT-13 evidence and national help,
  CORE-CHT-14 communication open only when someone can respond, CORE-CHT-15 bullying goes to the school's
  procedure or a default one; and a MUST rule, CORE-AI-12, generative features cannot depict real people.
- CORE-SAF-06 now gives the child an acknowledgement, the outcome and a "still happening" option. CORE-CHT-01
  covers channels without text (emotes, avatar names, drawings, shared worlds). Compass TRN-06 teaches how to
  help a friend; EDU-02 asks for a short bullying section in the teacher guide.
- `templates/bullying-procedure.md` for schools without a plan; `moderation` block in csef.yaml with two checks
  (`moderation_coverage_missing`, `bullying_route_missing`); detection of vote-kick, peer ratings, face swap and
  voice cloning.
- **Overlaps removed.** A-SOC-01 merged into CORE-SAF-05, A-ECO-04 into A-MOT-01, CORE-SAF-11 into CORE-CHT-08.
  Old ids keep working in packs, waivers and `csef-ignore` comments (`retired` in rules.yaml). Clearer split
  between CORE-SAF-06 and CHT-02, CORE-AI-05 and AI-09, CORE-DAT-11 and AGE-B4-01, CORE-COM-04 and A-ECO-03;
  CORE-SAF-01 no longer contradicts AGE-B5-01.
- Compass design targets declare `builds_on` rules and show their CSEF status; they score only the teaching layer.
- `communication` feature group (chat, multiplayer, social, ugc) in rules, targets and manifests.
- The build now keeps `legislation.md` and `research.md` up to date (status, citing rules and Compass targets,
  stubs for new sources) and checks the review guide, which now only says where to look.
- New sources: CB-AP (EU action plan against cyberbullying), EDPB-DSAGDPR, VAW-DIR, R-JUVONEN2008, R-WOLKE2017;
  PT-ESBEV in the Portugal pack.
- Rules: 118 to 122 (7 added, 3 merged). Sources: 72 to 77, plus 9 in the Portugal pack.

## v0.10.0 (2026-11-16)

- **Several countries and shared infrastructure** ([05-several-countries.md](framework/05-several-countries.md)):
  four SHOULD rules, CORE-INT-01 to 04 (country rules as configuration, school data export and exit, school
  sign-in with minimal rosters, declared and replaceable critical dependencies), three manifest checks and a
  pattern for hard-coded consent ages.
- Sources EDU-EDIC (context only), DATA-ACT (Data Act Chapter VI), 1EDTECH (LTI 1.3, OneRoster 1.2).
- `legislation.md` lists every legal, policy and guidance source again.
- Corrected: EU KIDS Act feedback closes on 26 Nov 2026 (earlier versions said 3 Dec).
- Rules: 114 to 118. Sources: 69 to 72.

## v0.9.0 (2026-11-14)

- **Literacy Compass** ([04-literacy-compass.md](framework/04-literacy-compass.md)): what a product teaches about
  digital, media and AI literacy, and how strong the evidence is. 45 targets on 8 axes, an evidence ladder
  (Stated, Designed, Tested, Measured), claim and hidden-curriculum checks, a compass rose, and a crosswalk to
  the EU guidelines on digital education content, Swedish Edtech's Kvalitetsportfolio and UNICEF EdTech for Good.
- **Personal questions**: feature `survey`, eight rules (CORE-DAT-13 to 18, CORE-SAF-11, CORE-DES-08), six
  manifest checks and a survey register template. Portugal: PT-SUR-01 (MIME approval, now EduQA, I.P.).
- AIA-OMNIBUS corrected to law in force (27 Jul 2026).
- Rules: 106 to 114. Sources: 50 to 69.

## v0.8.0 (2026-11-13)

- CSEF brand on every output; new landing page at https://csef.kendirstudios.pt.
- The questionnaire makes the whole policy kit in the browser, in seven languages.
- Features renamed "mechanisms" in the questionnaire, each with its legal wording.

## v0.7.0 (2026-11-13)

- Policy questionnaire (`tooling/policy.py`): 31 boundary questions in, a validated company pack, boundaries
  report, staff policy, agent instructions and CI workflow out. Re-runnable, with versions and change lists.

## v0.6.0 (2026-11-12)

- Renamed to **Child-Safe EdTech Framework (CSEF)**: a framework, not a formal standard. Thanks to Swedish
  EdTech Industry for the feedback. Old names (`cses.yaml`, `cses-ignore`) still work.

## v0.5.0 (2026-11-12)

- Communications audit and nine rules CORE-CHT-01 to 09; code-of-conduct comparison (`tooling/coc.py`);
  Unity and more ecosystems; `legislation.md` and `research.md`.

## v0.4.0 (2026-11-12)

- EU KIDS Act commercial practices (CORE-COM-05 to 08) and AI companions and chatbots (CORE-AI-08 to 11).

## v0.3.0 (2026-11-11)

- Interactive dashboard, PDF and Word exports (`--export html,pdf,docx`); `findings.json` format 2.

## v0.2.0 (2026-11-11)

- Company packs with a `policy` section, `--validate-pack`, and the web Pack Builder.

## v0.1.0 (2026-11-11)

- First public draft: 89 rules (core, profiles A, B, C, age bands), 50 sources, three compliance levels, the
  Portugal pack, the scanner, the review skill, a GitHub Action and Semgrep rules.
