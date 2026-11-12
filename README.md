# Child-Safe EdTech Framework (CSEF)

An open framework and toolkit for building safe educational software for under-18 students.
It turns EU law, pending EU proposals (EU KIDS Act, Digital Fairness Act) and expert recommendations into
rules a team can check in code, in CI and in review.

> **Status:** v0.6.0, draft for public comment (November 2026).
> **Not legal advice and not a certification.** CSEF produces *pre-compliance* reports. Legal compliance
> depends on facts code cannot show; involve your DPO and legal counsel. See [Limitations](#limitations).
>
> **A framework, not a standard.** CSEF is open guidance and tooling, not a formal standard adopted by a
> standards body (CEN, CENELEC, ETSI, ISO), and using it gives no presumption of conformity with any law. It
> aims to inform future standards and codes of conduct; any such use needs validation by official bodies.
> Until v0.5 it was called the Child-Safe EdTech Standard (CSES). See [why we renamed it](framework/00-introduction.md#a-framework-not-a-standard).

Repository: <https://github.com/eduardon83/child-safe-edtech-framework> ·
Site and Pack Builder: <https://eduardon83.github.io/child-safe-edtech-framework/>

## What you get

| | |
|---|---|
| **The framework** | 106 rules: a core set plus three profiles, **A** educational games, **B** game-based applications and software, **C** gamified applications. Age-band modifiers for 3 to 17. Rules on data, safety by design, commercial practices, AI companions and chatbots, communications, accessibility, security, and design for learning (visuals, sound, motion, motivation). |
| **Three compliance levels** | **1** Legal baseline, **2** Forward-compliant (adds adopted proposals and official benchmarks), **3** Best practice (adds research and expert recommendations). You decide which level of compliance you want in your software. |
| **Sources on every rule** | 50 sources with type, status and verification date. Every report lists the sources it relies on. See [legislation.md](framework/legislation.md) and [research.md](framework/research.md). |
| **Packs** | Add national laws, sector rules, literature or your own red lines without forking. Portugal pack included (draft, not legally reviewed). |
| **Company packs and Pack Builder** | Each organisation sets its minimum level, no-gos, forbidden SDKs and phrases and its own rules, in a web form, then publishes the pack to GitHub. |
| **Scanner** | `tooling/scan.py`: pre-compliance report, prioritised improvement plan, communications inventory, JSON and SARIF. |
| **Dashboard and exports** | `tooling/export.py`: interactive HTML dashboard (levels, age bands, communications, colour-coded findings, checklists, legal counsel section), PDF and Word. |
| **Code-of-conduct comparison** | `tooling/coc.py`: compares any code of conduct with the KIDS Act expectations for codes and with CSEF rules; shows what is covered, partial, missing or in conflict. |
| **AI review skill** | `skill/csef-review/`: Claude runs the tools, verifies findings, reviews what patterns cannot see, and finalises the reports. |
| **CI** | A GitHub Action, generated Semgrep rules, a PR template. |
| **Templates** | Manifest, DPIA starter, AI risk file, waiver record, instructions for AI coding agents. |

## New since v0.2

| Version | Added |
|---|---|
| **v0.3** | Interactive dashboard, PDF and Word exports (`--export html,pdf,docx`). |
| **v0.4** | EU KIDS Act commercial practices (Recital 31, Art. 13): real-time purchase labels, no design for impulsive spending, no disguised advertising, no commercial content in learning. AI companions and chatbots (Recitals 32 to 34, Art. 14): memory off by default, regular re-testing and monitoring, opt-in assistants inside games, no AI nudging to spend. |
| **v0.6** | Renamed to **Child-Safe EdTech Framework (CSEF)**: `framework/` folder, `csef.yaml` manifest, `csef-review` skill, `csef-scan` and `csef-coc` tools, repository `child-safe-edtech-framework`. Old names (`cses.yaml`, `cses-ignore`, `--standard-root`) still work. |
| **v0.5** | **Communications audit**: inventory of chat, direct messages, voice, video, comments and live streaming, and of the safeguards around them (report, block, moderation, filters, link filtering), with nine CORE-CHT rules from KIDS Act Art. 12, 15(2) and Recital 36. **Code-of-conduct comparison tool.** **Unity support** and more ecosystems (see below). `legislation.md` and `research.md`. Output folders now relative to the current directory. |

Full history: [CHANGELOG.md](CHANGELOG.md).

## Quick start

```bash
# 1. Describe your product
cp templates/csef.yaml /path/to/your-product/csef.yaml   # then edit it

# 2. Scan, with the dashboard, PDF and Word exports
pip install pyyaml python-docx
python3 tooling/scan.py --repo /path/to/your-product --out-dir csef-report --export html,pdf,docx

# 3. Open the outputs in csef-report/
#    report.md, improvements.md, dashboard.html, report.pdf, report.docx, findings.json, findings.sarif
```

Output folders are relative to the directory you run the command from.

Try it on the examples:

```bash
python3 tooling/scan.py --repo examples/noncompliant-game --out-dir out/bad --export html
python3 tooling/scan.py --repo examples/unity-sample --out-dir out/unity --export html
python3 tooling/scan.py --repo examples/compliant-game --out-dir out/good --level 3
```

### Dashboard, PDF and Word

- `dashboard.html`: self-contained and offline. Status at each level, age bands, communications, filters by
  severity and level, a human-check list you can tick and export as CSV, the improvement plan, a
  "for legal counsel" section and all sources.
- `report.pdf`: print version (Chrome or Chromium; falls back to WeasyPrint).
- `report.docx`: Word version for comments and sign-off (needs `python-docx`).

From an existing scan: `python3 tooling/export.py --input csef-report/findings.json --formats html,pdf,docx`.

### Compare a code of conduct

```bash
python3 tooling/coc.py --input our-code.pdf --name "Our Code" --level 2 --profiles A,C --bands B2,B3 --out-dir coc-report
```

Reads `.txt`, `.md`, `.html`, `.pdf` and `.docx`. Writes `coc-comparison.md`, `.html` and `.json`:

- **Structure**: what the EU KIDS Act proposal expects of codes of conduct (Art. 17, Art. 23, Recital 39):
  objectives, verifiable commitments, criteria for violent, sexual, gambling and self-harm content, in-app
  purchases, contact risks and addictive design, independent redress, age labels, independent monitoring
  with KPIs, reporting, stakeholder involvement.
- **Rules**: for each CSEF rule in scope, *covered*, *partial* (weak or narrow commitment), *missing*, or
  *possible conflict* (the code permits what a rule forbids, e.g. loot boxes "provided that odds are
  disclosed"), with the clauses cited and a suggested addition.

Example: `examples/codes-of-conduct/example-code.md` (fictional).

### Your organisation's pack

Open the [Pack Builder](https://eduardon83.github.io/child-safe-edtech-framework/pack-builder/), choose your
minimum level and no-gos, add your rules, and publish the pack to your repository. Then list it in each
product's `csef.yaml` under `packs:`. See [framework/02-packs.md](framework/02-packs.md).

### In GitHub Actions

Copy `templates/github/csef-check.yml` into `.github/workflows/` of your product repository. It runs the
scan on each pull request, fails on blocking findings, uploads SARIF to code scanning and attaches the
report and dashboard.

### With Claude

- **Claude Code:** copy `skill/csef-review/` into your project's `.claude/skills/` (or your user skills folder)
  and ask: *"Run a CSEF review of this repository at level 2"* or *"Compare this code of conduct with CSEF."*
- **Claude apps:** download `csef-review.zip` from the latest release (or run `python3 tooling/build.py --zip dist`)
  and upload it as a skill.

## Limitations

CSEF finds signals. It does not prove compliance, and a clean scan is not a clean bill of health.

### What automated checks cover

| Area | Covered |
|---|---|
| **Code and copy** | JavaScript and TypeScript (React, Vue, Svelte), HTML and CSS, Python, Java and Kotlin, Swift and Objective-C, Dart (Flutter), C# (including Unity scripts), Go, Ruby, PHP, Rust, C and C++, Scala, Elixir, GDScript (Godot), Lua, SQL, JSON, YAML, XML, translation files |
| **Game engine text assets** | Unity `.prefab`, `.asset`, `.unity`, `.asmdef` (with the default "Force Text" serialisation); Godot `.tscn`, `.tres` |
| **Dependency lists** | npm, Python (requirements, pyproject), CocoaPods, Swift Package Manager, Gradle, Maven, NuGet and .csproj, Unity Package Manager (`Packages/manifest.json`), Unity External Dependency Manager (`*Dependencies.xml`), Flutter, Go modules, Cargo, Composer, Bundler |
| **Database** | SQL migrations (for example row-level security being disabled, message tables) |
| **UI language** | English and European Portuguese patterns. Other languages need a pack with their phrases (`add_patterns`) |

### What cannot be checked yet

| Not covered | Why | What to do |
|---|---|---|
| **Unreal Blueprints, GameMaker, Construct, other binary engine assets** | Stored in binary formats | Review by hand; export configuration or C++ where possible |
| **Unity scenes saved as binary**, asset-store packages not in `Packages/` | Binary or vendored without a manifest | Use Force Text serialisation; keep SDKs in UPM or EDM4U |
| **Live databases, Firebase and Firestore security rules, cloud IAM** | Not read from live systems; Firebase rules not yet parsed | Review access policies by hand (CORE-SEC-02) |
| **Hosting regions from Terraform or cloud consoles** | Infrastructure-as-code not parsed yet | Declare regions in `csef.yaml` `third_parties` |
| **Third-party dashboards** (chat moderation settings, analytics retention, ad network settings) | Configured outside the repository | Confirm by hand; the communications audit marks safeguards "not found" as REVIEW, not BLOCK |
| **No-code tools without a repository** (e.g. Bubble) | No code to read | Use the manifest, human checks and dashboard |
| **Other UI languages** | Patterns exist only for English and PT-PT | Add phrases in a country pack; the Claude skill reads any language |
| **Runtime behaviour** (what the app actually shows, sends or stores) | Static analysis does not run the product | Test on devices; inspect network traffic |

### Processes code cannot show

These are always **human checks** in the report and dashboard:

- Contracts and roles: processor agreements, legal basis, the school as controller.
- DPIA, child rights impact assessment, AI risk file and their sign-off.
- Moderation in practice, the safeguarding procedure (CORE-CHT-08), moderator training and escalation.
- Age assurance and guardian tools as experienced by families.
- Accessibility with real assistive technology, and testing with children and teachers.
- Commercial practices in content: product placement, sponsorship and influencer marketing.
- Whether a code of conduct is applied in practice (the comparison tool reads wording, not behaviour).

### The code-of-conduct comparison

It matches English wording. A clause can use the right words and still be too narrow, or meet a rule in
words the tool does not know. Every result must be confirmed by a person, or by the Claude skill, which
compares meaning and reads any language.

## Read the framework

1. [Introduction](framework/00-introduction.md): profiles, age bands, levels, severities, how to describe your results; why CSEF is a framework, not a standard
2. [Regulatory map](framework/01-regulatory-map.md): which instrument says what, and the EU KIDS Act education exemption
3. [Legislation](framework/legislation.md): every legal and policy source, the provisions that matter, the rules that use them
4. [Research](framework/research.md): every study, its findings and limits, the rules that use it
5. [Packs](framework/02-packs.md): extending with national rules, literature and company policies
6. [Design for learning](framework/03-design-and-motivation.md): what research says about visuals, motion and rewards
7. [Rule catalogue](framework/catalogue/index.md): every rule with requirement, rationale, improvement and sources
8. [Self-assessment checklists](self-assessment/)

## Repository layout

```
framework/        rules.yaml + sources.yaml (single source of truth), coc-topics.yaml, docs, generated catalogue
packs/           country and extra packs (pt.yaml, _template.yaml)
tooling/         scan.py, comms.py, export.py, coc.py, build.py, generated Semgrep rules
skill/           csef-review skill for Claude (generated copies + SKILL.md + references)
templates/       manifest, DPIA starter, AI risk file, waiver, agent instructions, GitHub files
self-assessment/ generated checklists per profile and level
examples/        non-compliant, compliant and Unity sample products; example company pack and code of conduct
tests/           test-suite
docs/            GitHub Pages site, Pack Builder (generated), release notes
```

Edit `framework/rules.yaml`, `framework/sources.yaml`, `framework/coc-topics.yaml` or `packs/*.yaml`, then run
`python3 tooling/build.py`. Never edit generated files by hand; CI checks they are up to date.

## Licence

- Framework text, rules, sources, packs, checklists and templates: [CC BY 4.0](LICENSE-CC-BY-4.0.txt)
- Code (scanner, tools, build, action, skill scripts): [Apache 2.0](LICENSE-APACHE-2.0.txt)

See [LICENSE](LICENSE) for which applies where.

## Maintainers and governance

Maintained by Kendir Studios (Worlds4Education, Lda., Portugal), Eduardo Nunes and contributions from the EdTech
community. See [GOVERNANCE.md](GOVERNANCE.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
