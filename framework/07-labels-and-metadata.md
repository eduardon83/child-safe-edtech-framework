# Labels and metadata: describe once, submit anywhere

Quality labels and catalogues ask for the same facts in different forms: what the product is for, who it is
for, what it costs, what data it collects, and what evidence stands behind it. CSEF already holds most of
these facts in `csef.yaml` and in its scan results. This guide shows how to turn them into a **label package**.

There are two tools:

- `tooling/precheck.py` checks a serious game against published quality criteria and says what is missing.
- `tooling/metadata.py` exports the product description in standard formats and bundles everything into a
  package for a label or catalogue.

Neither tool awards a label. A label is awarded by its own body, after its own assessment.

## 1. The serious-game pre-check

Serious games have two jobs: reach a goal beyond fun (learning, training, health) and be good to play. The
criteria of Caserman et al. (2020) judge both, and the balance between them, in 22 aspects. They are one of
the two publications behind the quality label of the Serious Games Gütegemeinschaft. CSEF maps each aspect to
its own rules and Compass targets in `framework/serious-games/criteria.yaml`:

| Coverage | Aspects | What it means |
|---|---|---|
| CSEF checks it | 5 | Feedback, rewards, proof of effectiveness (Compass EDU-03), graphics and interface, interaction technology |
| CSEF checks part of it | 10 | The scan or Compass covers part; the team adds a statement for the rest |
| Team statement needed | 5 | Cannot be read from code: learning cannot be skipped, correct and neutral content, awards and ratings, enjoyment, team and co-design |
| CSEF sets limits for children | 2 | Emotional hooks and competitive play. The criteria recommend them; CSEF limits them for children |

Where CSEF and the criteria pull in different directions, the pre-check shows both, and **for under-18s the
CSEF rule applies**. Competition stays inside the class, with nicknames, a teacher switch and team goals
(C-ENG-02, CORE-CHT-12). Emotions are welcome; pressure is not (CORE-COM-03, C-ENG-04, CORE-AI-06).

### Statements with evidence

For the aspects CSEF cannot read from code, the team writes a short statement and points to evidence: a design
document, a playtest summary, an expert review, a study, an award. Paths are checked; links are listed.

```yaml
serious_game:
  characterizing_goal: "Pupils aged 6 to 9 understand and compare simple fractions."
  claims:
    SG-03: {statement: "Paths open only when a fraction task is solved.", evidence: [docs/design-document.md]}
    SG-09: {statement: "Playtested with two classes (41 pupils).", evidence: [docs/playtest-summary.md]}
```

### Run it

```bash
python3 tooling/scan.py --repo . --out-dir csef-report
python3 tooling/compass.py --input docs/ --manifest csef.yaml --csef-findings csef-report/findings.json --out-dir csef-compass
python3 tooling/precheck.py --repo . --findings csef-report/findings.json --compass csef-compass/compass.json --out-dir csef-precheck
```

Each criterion gets a status:

- **Ready**: CSEF rules in scope pass, Compass reaches the level needed, and the statement has evidence.
- **Partial**: something needs review, the Compass was not run, or a statement has no evidence yet.
- **Missing**: a required statement is missing, or the Compass level is too low.
- **CSEF issue**: a CSEF rule linked to the criterion has a blocking finding.

The label's own test rules are not public. Treat the pre-check as preparation, and ask the label body what it
assesses before you apply.

## 2. The metadata export

```bash
python3 tooling/metadata.py --repo . --out-dir csef-metadata            # sg-mdf.json, sg-mdf.xml, lrmi.jsonld
python3 tooling/metadata.py --repo . --strict                           # fail if required fields are missing
```

Two formats:

- **SG-MDF** (Serious Games Metadata Format, DIN SPEC 91380:2018-06), the format of the Serious Games
  Information Center. CSEF writes the Core fields (Level 1) and, when a `learning` block is present, the
  learning-games profile (Level 3).
- **schema.org LearningResource (LRMI)**, JSON-LD for any learning product, game or not. Search engines and
  many repositories read it.

Much of it comes from what `csef.yaml` already says: title, summary, age groups, game mode, purchases and
the data statement. The rest goes in a `metadata` block (see `templates/csef.yaml`). The data statement
(SG-MDF field 2.8, required) is written from the features, third parties, GDPR role and retention you declared,
so it always matches what CSEF checked.

**About the format.** DIN SPEC 91380 defines SG-MDF as a grammar and tables, with no official JSON or XML
schema. CSEF's files follow its element names and nesting, and say that they are CSEF's serialisation. The
allowed values for the selection lists are in Annex A of the DIN SPEC, a free download from DIN Media
(https://doi.org/10.31030/2853739). CSEF does not copy them and accepts free text; use the DIN values where
they fit. Do not commit a copy of the DIN SPEC to your repository: its licence does not allow it.

## 3. The label package

```bash
python3 tooling/metadata.py --repo . --package --findings csef-report/findings.json \
        --compass csef-compass/compass.json --out-dir csef-package
```

One zip with:

| Path | Content |
|---|---|
| `metadata/` | `sg-mdf.json`, `sg-mdf.xml`, `lrmi.jsonld` |
| `csef/` | `findings.json` (and `compass.json` when given) |
| `precheck/` | the serious-game pre-check in Markdown, HTML and JSON |
| `evidence/index.json` | every piece of evidence cited, with path or link; `--include-evidence` copies local files |
| `MANIFEST.json` | files with SHA-256 hashes, tool and framework versions, missing SG-MDF fields |
| `README.txt` | what each file is |

The package holds no learner data. Read the evidence files before you include them: design documents can
hold names or internal details you do not want to share.

## 4. Other labels

The same package answers more than one label. The Compass crosswalk already links CSEF evidence to the EU
guidelines on digital education content, Swedish Edtech's Kvalitetsportfolio and UNICEF's EdTech for Good
Framework. New labels can be added as crosswalks, without changing the product description.
