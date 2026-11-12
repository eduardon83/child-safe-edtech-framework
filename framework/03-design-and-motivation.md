# Design for learning: look, sound, motion and motivation

This part of CSEF turns current research on visual design and rewards into rules. Most are Level 3
(best practice): no law requires them, but the evidence says they protect learning and children's
motivation. Two accessibility rules sit at Level 1 and one at Level 2.

The evidence was gathered for the European Digital Education Hub game-based learning squad (Quality
Compass workstream, November 2026). Full references are in `framework/sources.yaml` (ids starting `R-`).

## What the evidence says, in short

| Claim | Verdict | Strongest evidence |
|---|---|---|
| Decoration and "seductive details" harm learning | Supported | g = -0.33 across 58 studies (R-SUNDARARAJAN2020) |
| Some learners are hit harder | Supported | Young and autistic children are more distracted by busy displays (R-HANLEY2017, R-FISHER2014); flashing and motion harm learners with photosensitive epilepsy or vestibular disorders (W3C-233) |
| Animation in general is the problem | Contradicted | Animation that shows the content beats static pictures, g = 0.23 (R-BERNEY2016) |
| Fast pace is the problem | Partly contradicted | For 4-year-olds, fantastical events drove the attention cost, not pace (R-LILLARD2011) |
| Colour and style matter | Supported, both ways | Pleasant colours and faces help (R-BROM2018); pictures inside maths graphics hurt 6 to 8-year-olds (R-KAMINSKI2013) |
| Popular colour psychology ("red lowers scores") | Not supported | Does not survive publication-bias correction (R-GNAMBS2020) |
| Rewards that pile up are a risk | Supported for single elements; stacking inferred | Expected rewards lower intrinsic motivation, d = -0.36 (R-DECI1999); badges plus leaderboards lowered motivation and exam scores (R-HANUS2015) |
| Rewards crowd out deep learning and helping over time | Plausible, consistent with evidence, not tested long-term | R-VANSTEENKISTE2005, R-WARNEKEN2008, R-HOWARD2021, R-CERASOLI2014, R-LEPPER2005 |

## Rules

| Rule | Level | In one line |
|---|---|---|
| CORE-ACC-04 | 1 (MUST) | Auto-moving content and audio can be paused |
| CORE-ACC-05 | 1 (MUST) | Colour is never the only cue |
| CORE-DES-01 | 2 (SHOULD) | Honour reduced motion; motion and sound can be turned down or off |
| CORE-DES-02 | 3 | Motion shows the content, not decoration |
| CORE-DES-03 | 3 | Calm screens under 8: few elements at once, spoken help |
| CORE-DES-04 | 3 | Fantasy does not blur facts for young children |
| CORE-DES-05 | 3 | Visual style matches the concept; no pictures inside maths graphics |
| CORE-DES-06 | 3 | Celebrations short, proportional, skippable |
| CORE-DES-07 | 3 | No colour-psychology claims |
| A-MOT-01 | 3 | No reward pile-up: keep a reward inventory |
| A-MOT-02 | 3 | Feedback informs, it does not control |
| A-MOT-03 | 3 | The product works with rewards switched off; debrief prompts |
| A-MOT-04 | 3 | Room for curiosity |
| A-MOT-05 | 3 | Helping and creativity are recognised, not paid |

Full text: [rule catalogue](catalogue/index.md).

## The reward pile-up check

A 30-second check any team or teacher can run:

1. List every reward the product gives: points, coins, badges, streaks, levels, leaderboards,
   unlockables, celebrations.
2. For each one, ask: *is it given for learning, or for showing up?*
3. Mostly for learning, and explained: fine. Three or more layers given for playing time, logging in or
   just finishing: flag it. A leaderboard everyone sees in a mixed-ability class: flag it, unless the
   teacher can switch it off or turn it into a team goal.

The scanner gives a signal when it finds four or more reward layers in code (rule A-MOT-01). It cannot
tell what each layer is given for; that is the human part of the check.

**Not harmful motivators:** feedback that explains, unexpected praise, visible progress, a shared class goal.

## Why stacking makes it worse

This is a reading of single-element studies, not a direct test:

1. Each layer makes rewards more expected and more tied to just playing, the worst case in Deci et al.
2. Each reward effect is itself a seductive detail competing for attention.
3. Stacks drift from informing ("you solved 3 of 5") to controlling ("come back or lose your streak").
4. When every action pays, learning stops being the reason to play.
5. Comparison features reward those already ahead and hurt the weakest.
