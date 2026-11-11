# Contributing

Thank you for helping make EdTech safer for children.

## Ways to contribute

- **Report a false positive or missed pattern**: open an issue with a minimal code sample.
- **Propose a rule**: open an issue labelled `rule-change` with requirement, rationale, level, sources.
- **Add or update a source**: include the official URL, status with a date, and the date you verified it.
- **Write a country pack**: start from `packs/_template.yaml`; see `standard/02-packs.md`.
- **Improve the tools**: scanner, build, action, skill.

## Rule quality bar

A rule must be:

1. **Sourced.** Level 1 cites a law; Level 2 at least a proposal, guidance or standard; Level 3 can cite literature.
2. **Actionable.** It says what to build or change (`improvement`).
3. **Checkable.** Prefer detection patterns; otherwise it becomes a human check with clear wording.
4. **Proportionate.** Explain why the requirement fits the age bands and profiles it targets.

## Workflow

```bash
pip install pyyaml pytest
python3 tooling/build.py      # validate + regenerate
python3 -m pytest -q          # tests
```

Edit only `standard/rules.yaml`, `standard/sources.yaml`, `packs/*.yaml`, docs and tooling. Generated files
(catalogue, checklists, Semgrep, skill copies) are rebuilt by `tooling/build.py`; CI fails if they are stale.

## Language

The reference text is English. Write rules in plain English with short sentences. Child-facing detection
strings in other languages belong in country packs (`add_patterns`).

## Conduct

Be respectful and assume good faith. Discussions about children's safety can involve sensitive topics:
never post real children's data, screenshots or identifiable information.
