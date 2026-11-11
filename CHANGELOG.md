# Changelog

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
