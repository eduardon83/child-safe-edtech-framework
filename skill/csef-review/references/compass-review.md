# Literacy Compass review

Use this when someone asks what a product teaches about digital, media or AI literacy, wants to check its
learning claims, or wants a quality description they can reuse (EU guidelines on digital education content,
Swedish Edtech Kvalitetsportfolio, UNICEF EdTech for Good). The Compass is not about harm; the CSEF rules are.
Run both when the user wants the full picture.

## 1. Gather inputs

Ask for, or find in the repository: design documents, learning goals, teacher guides, family material,
evaluation or pilot reports, marketing and store texts, and in-product text (dialogue, translation files).
Marketing texts matter: that is where claims live. Never ask for data about individual pupils.

Read `csef.yaml` if there is one. If it has no `compass:` section, ask the user what the product claims to
teach (axes INF, COM, CRE, SAF, PRB, AI or target ids) and its age bands and features. Write the answers into
`csef.yaml`.

## 2. Run the tool

```bash
python3 <skill-folder>/scripts/compass.py --input <docs> --input <content> --manifest csef.yaml \
        [--csef-findings csef-report/findings.json] --out-dir csef-compass
```

It writes `compass.md`, `compass.html` and `compass.json`, and prints the next three steps.

## 3. Verify by meaning

The tool matches words in English and European Portuguese. You read meaning, in any language.

- **Each target in scope.** Open the passages cited. Raise or lower the level using the ladder:
  1 Stated, 2 Designed (a specific activity, mechanic, feature or teacher material is linked to the target),
  3 Tested (tried with learners or teachers, results recorded), 4 Measured (outcomes measured). A plan is not
  evidence. Internal user tests are level 3; say whether evaluation was independent.
- **Missed evidence.** Search the documents for the target's intent in other words or languages. Add it with
  the file and line.
- **Claims.** Check each claim in marketing and store texts. If the evidence does not support it, propose a
  rewording that does, for example "practises checking sources in five cases" instead of "teaches critical
  thinking".
- **Hidden curriculum.** Confirm each conflict in context. Dismiss quotes of what not to do. Look for more:
  AI characters presented as friends, people or all-knowing; pressure to return or spend; disguised ads;
  rewards that undercut the learning goal (see `framework/03-design-and-motivation.md`).
- **Age.** Check AI targets against the age bands (UNESCO recalls a minimum age of 13 for independent use of
  generative AI in class) and say what changes for younger learners.

## 4. Write the result

Add a "Reviewer assessment" section to `compass.md`: confirmed and changed levels with reasons, new evidence,
dismissed conflicts, suggested claim rewordings, and the next three steps in your own words. Keep the
disclaimer: a profile, not a score; no rating, ranking or certification.

Rules:
- Cite only sources in `framework/sources.yaml` or a loaded pack.
- Never give a total score or compare products with each other.
- Do not say a product "is AI-literate", "is certified" or "complies with DigComp". Say what the documents
  show, at which level, on which date.

## 5. Report back

In a few lines: axes in scope, how many targets reach Designed and Tested, conflicts found, unsupported
claims, and the next three steps. Offer the HTML compass for sharing.
