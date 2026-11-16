# Bullying: what the product can do, and who can respond

Most bullying online is between children who know each other, often from the same class. Closed class
groups keep strangers out, but not the bully. CSEF looks at bullying through two questions:

- **Ability:** what does the product make possible or impossible?
- **Capacity:** can the people around it (teachers, the school, the company's moderators, families and
  the child) actually respond?

A product should not offer more than its people can cover. If nobody can answer a report at 10 pm, chat
should not be open at 10 pm. This guide is not legal advice.

## Ability: design

| What | Rule | Level |
|---|---|---|
| Strangers cannot make contact; play stays in closed groups | CORE-SAF-05 | MUST |
| Every channel is declared, including emotes, avatar names, drawings and shared worlds | CORE-CHT-01 | MUST |
| Report and block in every channel | CORE-CHT-02 | MUST |
| No voting out, ratings of children, polls about classmates, children picking teams, visible paid status or friend counts; teachers can keep two children apart | CORE-CHT-12 | SHOULD |
| No follower counts or likes on appearance; leaderboards by class, without names | CORE-SAF-10, C-ENG-02 | MUST |
| No images, video or voices of real people from generative features | CORE-AI-12 | MUST |

## Ability: reporting

| What | Rule | Level |
|---|---|---|
| The child hears the report arrived, gets help now, learns the outcome and can say "still happening" | CORE-SAF-06 | MUST |
| Do not show who reported | CORE-CHT-10 | SHOULD |
| Children can report for a friend; repeated unfounded reports go to an adult, never to automatic penalties | CORE-CHT-11 | SHOULD |
| The child can keep an evidence record and reach the national helpline or the EU online safety app | CORE-CHT-13 | SHOULD |

## Capacity: people and procedures

| What | Rule | Level |
|---|---|---|
| Named moderators with powers to hide, remove, mute and suspend | CORE-CHT-03 | MUST |
| Communication is open only when someone can respond: hours, languages, response targets, what happens outside them | CORE-CHT-14 | SHOULD |
| Bullying goes to the school's anti-bullying plan, or to a default procedure the product offers | CORE-CHT-15 | SHOULD, strongly recommended |
| Safeguarding procedure with a route for each kind of harm | CORE-CHT-08 | MUST |
| Teacher guide with a short part on bullying | Compass EDU-02 | Target |
| The child learns the tools and how to help a friend | Compass TRN-06 | Target |

## When the school has no anti-bullying plan

Many schools have one, but not all. The product should still work. At set-up, ask the school for its
anti-bullying contact. If there is none, offer the default procedure in
[`templates/bullying-procedure.md`](../templates/bullying-procedure.md): roles, eight steps, report categories
from the EU definition, and helplines. Declare the choice in `csef.yaml` under `moderation.bullying_procedure`.

## Help a friend

Bystanders often see what adults do not. Next to "report for a friend", show four short steps:

1. Don't join in.
2. Tell them you are on their side.
3. Report it for them.
4. Tell a trusted adult.

A child who is targeted hears: "It's not your fault." They are also told what will happen next.

## Sources

The EU action plan against cyberbullying, COM(2026) 71 (`CB-AP`); EDPB Guidelines 3/2025 (`EDPB-DSAGDPR`);
DSA Art. 16 and 23; Directive (EU) 2024/1385 (`VAW-DIR`); Juvonen and Gross (2008); Wolke, Lee and Guy (2017).
In Portugal, the national plan "Escola Sem Bullying. Escola Sem Violência" (`PT-ESBEV`).
