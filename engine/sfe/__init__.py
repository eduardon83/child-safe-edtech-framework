"""Safety Framework Engine (sfe).

The parts of the Kendir Studios frameworks that do not depend on the domain: the rule and source schema, catalogue
and checklist generation, pattern scanning (regex, dependency, manifest checks), reports and a small Markdown
renderer. Each framework describes itself in framework/framework.yaml and keeps its own rules, sources, checks
and texts.

Used by the Child-Safe EdTech Framework (CSEF, home of this package) and the Health Data Safety Framework (HDSF,
which vendors a pinned copy). Licence: Apache-2.0
"""
ENGINE_VERSION = "0.2.0"
