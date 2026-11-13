# Packs: national laws, literature and your own rules

The core framework covers EU-level instruments. Everything else enters through **packs**: YAML files that
add sources and rules, and tighten existing rules.

## What a pack can contain

| Section | Use it for | Example |
|---|---|---|
| `sources` | Laws, guidance, standards, research to cite | A national data protection act; a Ministry guide on digital resources; a peer-reviewed study |
| `rules` | Requirements the base framework does not have | "Child-facing text in the national language" |
| `policy` | Organisation-wide decisions (company packs) | Minimum level, no-gos, forbidden packages and phrases, required decision records |
| `amend` | Make an existing rule stricter or add national nuance | Add the national consent age; raise a Level 2 rule to Level 1 because the country already made it law; add local-language detection patterns |
| `parameters` | Values shown in reports | Digital consent age, supervisory authority, child helpline |

A pack **cannot** remove or weaken a rule. The scanner refuses to lower a MUST to SHOULD or to move a rule
to a higher (less binding) level.

## Types of pack

- **Country packs** live in `packs/<iso-code>.yaml` in this repository and load automatically when a
  product lists the country in `jurisdictions`. `packs/pt.yaml` is the worked example.
- **Sector packs** (e.g. a Ministry's procurement rules for digital educational resources) can live here
  or in the product repository.
- **Literature packs** add research sources you want reports to cite, and Level 3 rules based on them.
- **Company packs** encode your own red lines. Keep them in your product repository
  (e.g. `.csef/packs/acme.yaml`) and list them under `packs:` in `csef.yaml`.

## Company packs: your organisation's policy

The easiest way to write one is the **policy questionnaire** (`python3 tooling/policy.py --web`). It asks
about your boundaries, matches each answer with the law and recommendations, and writes the pack together with
a boundaries report and a plain-language staff policy. Run it again with `answers.json` to change anything.
You can also write or extend the pack by hand, for example to add amendments (see `examples/company-packs/`).

A company pack can also carry a `policy` section. It turns your organisation's decisions into checks:

| Key | Effect |
|---|---|
| `minimum_level` | Every product is assessed at least at this level, even if its manifest asks for less |
| `no_go` | Framework rules you never break. They always apply (Level 1) and block at any confidence |
| `forbid_dependencies` | Packages your products never ship |
| `forbid_phrases` | Phrases never shown to children (pressure, guilt, scarcity), in any language |
| `forbid_patterns` | Your own regular expressions, with title and improvement |
| `require_decision_for_features` | Declared features need a decision record linked in `csef.yaml` under `decisions:` |
| `review_every_days` | Product manifests must be reviewed within this many days |
| `require_agent_instructions` | Repositories must give AI coding agents the CSEF rules (CLAUDE.md, AGENTS.md, ...) |

The scanner creates rules `<ID>-POL-01`, `-02`, ... from these keys and a source `<ID>-POLICY` of type
`policy`, so reports show which findings come from your policy and which from law.

**Pack Builder.** Make a company pack without writing YAML at
`docs/pack-builder/index.html` (published on the project's GitHub Pages site). Choose your minimum level,
tick your no-gos, list forbidden packages and phrases, add your own rules, then download the file or
publish it straight to a GitHub repository. An example is in `examples/company-packs/acme.yaml`.

Validate any pack with:

```bash
python3 tooling/build.py --validate-pack path/to/your-pack.yaml
```

## Writing a pack

1. Copy `packs/_template.yaml`.
2. Give every source a `type`, a `status` with a date, a `url` where one exists, and a `verified` date.
3. Prefix new rule ids with the pack id in upper case (`ES-DAT-01`).
4. Respect level evidence: a Level 1 rule must cite a law, a Level 2 rule at least a proposal,
   guidance or standard.
5. Run `python3 tooling/build.py` to validate. Country packs in this repository also get a generated
   page in `framework/catalogue/`.

## Contributing a country pack

Open a pull request with the pack and a short note on who reviewed it (ideally a lawyer or DPO from that
country). Entries you could not verify should say *verify* in their status. See CONTRIBUTING.md.
