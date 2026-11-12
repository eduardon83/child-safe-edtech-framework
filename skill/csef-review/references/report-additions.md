# Adding the reviewer's judgement to the generated files

The scanner output is the starting point. After manual review, edit both files as follows.

## report.md

Insert this section right after "## Summary":

```markdown
## Reviewer assessment

Reviewed by: <name or "Claude (AI-assisted review)"> on <date>, CSEF v<version>, Level <N>.

**Overall.** <Two or three sentences: the main risks for children and the state of readiness.>

**Confirmed findings.** <count> of <count> automated findings confirmed. <count> re-graded REVIEW -> BLOCK.

**Dismissed findings.**
| Rule | Location | Reason |
|---|---|---|

**Additional findings from manual review.**
| Severity | Rule | Location | What the code does | Sources |
|---|---|---|---|---|

**Human checks partly answered from code.**
| Rule | What the code shows | Still needs |
|---|---|---|

**Who needs to act.** <DPO / legal / product owner / school as controller, and on what.>
```

Keep the generated "Sources" section and add any source ids used in your additions (registry ids only).

## improvements.md

- Add new items from manual review in the right section (Fix before release, Confirm and fix, ...),
  using the same format: action in bold, rule, why, where, sources.
- Remove items for dismissed findings, and say so in one line at the top.
- If the user chose a level, keep the "To reach the next level" section: it is how teams plan ahead.
