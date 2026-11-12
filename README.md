# Child-Safe EdTech Standard (CSES)

An open standard and toolkit for building safe educational software for under-18 students.
It turns EU law, pending EU proposals (EU KIDS Act, Digital Fairness Act) and expert recommendations into
rules a team can check in code, in CI and in review.

> **Status:** v0.1.0, draft for public comment (November 2026).
> **Not legal advice and not a certification.** CSES produces *pre-compliance* reports. Legal compliance
> depends on facts code cannot show; involve your DPO and legal counsel.

## What you get

| | |
|---|---|
| **The standard** | 97 rules in a core set plus three profiles: **A** educational games, **B** game-based applications and software, **C** gamified applications. Age-band modifiers for 3 to 17. Design-for-learning rules on visuals, audio/sound, motion and motivation, from current research. |
| **Three compliance levels** | **1** Legal baseline, **2** Forward-compliant (adds adopted proposals and official benchmarks), **3** Best practice (adds research and expert recommendations). You decide which level of compliance you want in your software. |
| **Sources on every rule** | A source registry with type, status and verification date. Reports list the sources they rely on. |
| **Packs** | Add national laws, sector rules, literature or your own red lines without forking. Portugal pack included (not legally binding). |
| **Company packs and Pack Builder** | Each organisation sets its minimum level, no-gos, forbidden SDKs and phrases and its own rules, in a web form, then publishes the pack to GitHub. |
| **Scanner** | `tooling/scan.py` writes a pre-compliance report, a prioritised improvement plan, JSON and SARIF. |
| **Dashboard and exports** | `tooling/export.py` turns a scan into an interactive HTML dashboard (levels, age bands, colour-coded findings, checklists, legal counsel section), a PDF and a Word document. |
| **AI review skill** | `skill/cses-review/` lets Claude run the scanner, verify findings, review what patterns cannot see, and finalise both documents. |
| **CI** | A GitHub Action, generated Semgrep rules, a PR template. |
| **Templates** | Manifest, DPIA starter, AI risk file, waiver record, instructions for AI coding agents. |

## Quick start

```bash
# 1. Describe your product
cp templates/cses.yaml /path/to/your-product/cses.yaml   # then edit it

# 2. Scan
pip install pyyaml
python3 tooling/scan.py --repo /path/to/your-product --out-dir cses-report

# 3. Read the two outputs
#    cses-report/report.md         pre-compliance report with sources
#    cses-report/improvements.md   prioritised improvement plan
```

Repository: <https://github.com/eduardon83/child-safe-edtech-standards>

Try it on the examples:

```bash
python3 tooling/scan.py --repo examples/noncompliant-game --out-dir cses-report
python3 tooling/scan.py --repo examples/compliant-game --out-dir cses-report --level 3
```

### Dashboard, PDF and Word

For a friendlier review with product owners, clients or legal counsel, export the scan:

```bash
python3 tooling/scan.py --repo /path/to/your-product --out-dir cses-report --export html,pdf,docx
# or, from an existing scan:
python3 tooling/export.py --input cses-report/findings.json --formats html,pdf,docx
```

- `dashboard.html`: interactive, self-contained dashboard. Status at each of the three levels, age bands,
  filters by severity and level, a human-check list you can tick and export, the improvement plan, a
  "for legal counsel" section and all sources. Works offline; open it in any browser.
- `report.pdf`: print version (uses Chrome or Chromium; falls back to WeasyPrint).
- `report.docx`: Word version for comments and sign-off (needs `pip install python-docx`).

### Your organisation's pack

Open the [Pack Builder](https://eduardon83.github.io/child-safe-edtech-standards/pack-builder/), choose your
minimum level and no-gos, add your rules, and publish the pack to your repository. Then list it in each
product's `cses.yaml` under `packs:`. See `standard/02-packs.md`.

### In GitHub Actions

Copy `templates/github/cses-check.yml` into `.github/workflows/` of your product repository. It runs the
scan on each pull request, fails on blocking findings, uploads SARIF to code scanning and attaches the
report.

### With Claude

- **Claude Code:** copy `skill/cses-review/` into your project's `.claude/skills/` (or your user skills folder)
  and ask: *"Run a CSES review of this repository at level 2."*
- **Claude apps:** run `python3 tooling/build.py --zip dist` and upload `dist/cses-review.zip` as a skill.

## Read the standard

1. [Introduction](standard/00-introduction.md): profiles, age bands, levels, severities, how to claim conformance
2. [Regulatory map](standard/01-regulatory-map.md): which instrument says what, and the EU KIDS Act education exemption
3. [Packs](standard/02-packs.md): extending with national rules and literature
4. [Design for learning](standard/03-design-and-motivation.md): what research says about visuals, motion and rewards
5. [Rule catalogue](standard/catalogue/index.md): every rule with requirement, rationale, improvement and sources
6. [Self-assessment checklists](self-assessment/)

## Repository layout

```
standard/        rules.yaml + sources.yaml (single source of truth), docs, generated catalogue
packs/           country and extra packs (pt.yaml, _template.yaml)
tooling/         scan.py, build.py, generated Semgrep rules
skill/           cses-review skill for Claude (generated copies + SKILL.md)
templates/       manifest, DPIA starter, AI risk file, waiver, agent instructions, GitHub files
self-assessment/ generated checklists per profile and level
examples/        a non-compliant and a compliant sample product
tests/           test-suite for the scanner and the catalogue
docs/            GitHub Pages site, Pack Builder (generated), release notes
```

Edit `standard/rules.yaml`, `standard/sources.yaml` or `packs/*.yaml`, then run `python3 tooling/build.py`.
Never edit generated files by hand; CI checks they are up to date.

## Licence

- Standard text, rules, sources, packs, checklists and templates: [CC BY 4.0](LICENSE-CC-BY-4.0.txt)
- Code (scanner, build, action, skill scripts): [Apache 2.0](LICENSE-APACHE-2.0.txt)

See [LICENSE](LICENSE) for which applies where.

## Maintainers and governance

Maintained by Kendir Studios (Worlds4Education, Lda., Portugal), Eduardo Nunes and contributions from the EdTech
community. See [GOVERNANCE.md](GOVERNANCE.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
