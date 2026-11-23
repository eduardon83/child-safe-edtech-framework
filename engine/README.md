# Safety Framework Engine (sfe)

The domain-free core shared by two open frameworks from Kendir Studios:

- **CSEF**, the Child-Safe EdTech Framework (this repository)
- **HDSF**, the Health Data Safety Framework ([eduardon83/health-data-safety-framework](https://github.com/eduardon83/health-data-safety-framework))

Each framework keeps its own rules, sources, manifest checks, guides and site. The engine holds what they share:

| Module | What it does |
|---|---|
| `sfe/config.py` | Reads `framework/framework.yaml`: name, levels, profiles, the second scope axis (CSEF: age bands; HDSF: users), features, id pattern, source types, manifest names |
| `sfe/catalogue.py` | Validates rules and sources; writes catalogue pages, self-assessment checklists and Semgrep rules |
| `sfe/patterns.py` | Walks a code base; regex and dependency findings (16 package formats); inline ignore comments |
| `sfe/scanner.py` | Which rules apply to a product; findings from code and manifest; Markdown, JSON and SARIF reports |
| `sfe/export.py` | Reports: interactive HTML dashboard (search, filters, print), PDF (Chrome or WeasyPrint) and Word (python-docx), with optional extra sections such as a document review |
| `sfe/markdown.py` | A small deterministic Markdown renderer for guide pages |

## How the frameworks use it

- CSEF: `tooling/build.py` uses `sfe.catalogue`; `tooling/mdpage.py` uses `sfe.markdown`. `tooling/scan.py` still has its
  own copy of the pattern code, because the Claude skill and the browser Workbench ship it as one file;
  `tests/test_engine.py` checks both give the same results. It moves onto `sfe` in a later version.
- HDSF vendors a pinned copy in `engine/sfe/` and records the CSEF commit in `engine/ENGINE.lock`. Its CI checks the
  copy against that commit.

## Changing the engine

Change it here, run CSEF's `python3 tooling/build.py --check` and `pytest` (generated files must not change unless you
mean them to), then update HDSF with `python3 tooling/sync_engine.py --from <path to CSEF>`.

Version: see `sfe/__init__.py`. Licence: Apache-2.0.
