# Packs: national laws, literature and your own rules

The core standard covers EU-level instruments. Everything else enters through **packs**: YAML files that
add sources and rules, and tighten existing rules.

## What a pack can contain

| Section | Use it for | Example |
|---|---|---|
| `sources` | Laws, guidance, standards, research to cite | A national data protection act; a Ministry guide on digital resources; a peer-reviewed study |
| `rules` | Requirements the base standard does not have | "Child-facing text in the national language" |
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
  (e.g. `.cses/packs/acme.yaml`) and list them under `packs:` in `cses.yaml`.

## Writing a pack

1. Copy `packs/_template.yaml`.
2. Give every source a `type`, a `status` with a date, a `url` where one exists, and a `verified` date.
3. Prefix new rule ids with the pack id in upper case (`ES-DAT-01`).
4. Respect level evidence: a Level 1 rule must cite a law, a Level 2 rule at least a proposal,
   guidance or standard.
5. Run `python3 tooling/build.py` to validate. Country packs in this repository also get a generated
   page in `standard/catalogue/`.

## Contributing a country pack

Open a pull request with the pack and a short note on who reviewed it (ideally a lawyer or DPO from that
country). Entries you could not verify should say *verify* in their status. See CONTRIBUTING.md.
