# Governance

## Roles

- **Maintainers** review and merge changes, cut releases and keep the source registry current.
  Initial maintainer: Kendir Studios (Worlds4Education, Lda.). We aim for maintainers from at least three
  organisations and two countries by v1.0.
- **Pack stewards** own a country or sector pack and confirm its legal accuracy.
- **Contributors**: anyone who opens an issue or pull request.

## Decisions

- Editorial fixes and new sources: one maintainer approval.
- New or changed rules: two maintainer approvals and a public comment period of at least 14 days
  (issue labelled `rule-change`).
- Changing a rule's level or removing a rule: two approvals, 30-day comment period, entry in CHANGELOG
  explaining the evidence.
- Packs: approval by the pack steward and one maintainer.

## Independence

CSEF is vendor-neutral. No rule may reference a specific commercial product as the required solution.
Maintainers declare conflicts of interest on rule changes that affect their own products.

## Versioning

Semantic versioning on the framework:

- **Major**: a rule becomes stricter in a way that can change existing self-assessment results (new MUST, lower level number).
- **Minor**: new rules at SHOULD, new packs, new sources, new detection patterns.
- **Patch**: wording, links, false-positive fixes.

## Regulatory watch

Maintainers review the registry at least monthly and on any major EU publication (Official Journal,
Commission proposals, EDPB and AI Office guidance). When a proposal is adopted, rules move from Level 2 to
Level 1 in a major release, with the application date.

## Releases

Tagged `vX.Y.Z`. Each release publishes the catalogue, checklists and the packaged skill. Release notes live in `docs/releases/`.
