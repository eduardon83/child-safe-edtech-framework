# Reviewing a code of conduct against CSES

Use this when the user gives you a code of conduct (industry, company, or a draft code under the EU KIDS Act
proposal, Art. 17 on age rating and online games or Art. 23 on general codes).

## 1. Run the first pass

```bash
python3 <skill-folder>/scripts/coc.py --input <file> --name "<code name>" --level <1|2|3> \
  --profiles <A,B,C> --bands <B1..B5> [--pack packs/pt.yaml] --out-dir coc-report
```

Ask the user only what changes the result: which products the code applies to (profiles), the ages
covered (bands), and the level they want to compare against (default 3: everything, so gaps show).

The tool matches English wording. For codes in other languages, read the code yourself and skip to step 3,
using the JSON output only as a list of rules to check.

## 2. Check the structure

The `structure` section lists what the KIDS Act proposal expects of codes of conduct (COC-S01 to S11):
objectives, verifiable commitments, criteria for violent, sexual, gambling and self-harm content, in-app
purchases, contact risks and addictive design, free and independent redress, age labels shown before
access or purchase, independent monitoring with KPIs, reporting to authorities, stakeholder involvement,
measures for online games, and a statement that adherence does not by itself mean compliance.

## 3. Confirm every rule by meaning

For each rule in scope, read the clauses cited and the rest of the code:

- **Covered**: a clear commitment (must, shall, will, never) that meets the rule's requirement in substance.
  Downgrade to partial if the commitment is narrower than the rule (for example, only for under-13s when the
  rule covers all minors).
- **Partial**: the topic is addressed but the commitment is weak (should, encourage, where possible) or
  narrower than the rule.
- **Missing**: nothing in the code addresses it. Check synonyms and other sections before confirming.
- **Possible conflict**: the code permits what the rule forbids (for example, loot boxes allowed if odds are
  disclosed; notifications enabled by default; streak rewards). Confirm the conflict, quote the sentence.
  Dismiss false positives with a reason (for example, "may not" in another sentence).

Rules marked "not expected in a code" are engineering practices; mention them only if the code claims to
cover engineering.

## 4. Write the gap analysis

Edit `coc-comparison.md` and add, after the summary:

```markdown
## Reviewer assessment

Reviewed by <name or "Claude (AI-assisted review)"> on <date>, CSES v<version>, Level <N>.

**Overall.** <2 to 3 sentences.>

**Confirmed conflicts.** <table: rule, clause, quote, why it conflicts, suggested rewording>

**Most important gaps.** <the 5 to 10 missing or partial rules that matter most for the code's scope, with
suggested clause wording the code owners could adopt>

**Structure.** <what the code needs to meet Art. 17 / Art. 23 expectations>

**Dismissed tool results.** <rule, reason>
```

Suggested clause wording must be neutral and generic (not legal drafting advice), cite the CSES rule id and
its sources, and keep the status of proposals clear (the KIDS Act and DFA are proposals).

## 5. Say what the comparison cannot do

A code can be complete on paper and not applied in practice. Recommend independent monitoring and, for
member products, a CSES scan of each product.
