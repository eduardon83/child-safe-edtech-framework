# Instructions for AI coding agents

Paste this block into `CLAUDE.md`, `AGENTS.md`, Lovable project knowledge, Cursor rules or any other
agent configuration in a product repository that follows CSEF.

```markdown
## Child-safety rules (CSEF, mandatory)

Users of this product are children. Before changing code, read csef.yaml (profiles, age bands,
compliance level, features).

Never add, even if asked:
- advertising, ad attribution, fingerprinting or session-replay SDKs on child screens
- loot boxes, paid random rewards, pay-to-win, virtual currency purchases by children
- countdowns, scarcity messages, pre-ticked options, guilt-tripping copy
- notifications that ask the child to come back; push must default to off
- streak loss framing, decay or energy timers that punish absence
- emotion recognition, face or voice identification, webcam proctoring
- AI personas that claim feelings, friendship or that they missed the child
- public rankings with real names; contact from people outside the child's group
- real learner data in seeds, tests, fixtures or prompts

If a request conflicts with these rules, stop and name the CSEF rule id (e.g. A-ECO-01).
If you add a feature listed in csef.yaml `features`, update csef.yaml in the same change.
After changes, run: python3 <path-to-cses>/tooling/scan.py --repo . --out-dir csef-report
```
