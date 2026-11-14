# Literacy Compass

Status: **Draft for public comment**, v0.1, November 2026. Part of CSEF v0.9.

## 1. Why a second lens

The CSEF rules ask: **does the product do harm?** They check data, safety by design, commercial practices,
AI and accessibility against law and recommendations.

The Literacy Compass asks a different question: **what does the product teach about digital life, and how do
we know?** Every product used by children teaches something about the digital world, whether it means to or
not. A detective game can teach lateral reading. An AI tutor that calls itself "your best friend" teaches the
opposite of what AI literacy frameworks ask for.

European and international policy now sets clear targets for these literacies:

- **DigComp 3.0** (JRC, November 2025): 5 areas, 21 competences, with AI integrated across all of them.
- **AILit** (European Commission and OECD, final June 2026): 4 domains and 19 AI literacy competences for
  primary and secondary education, with learner expectations at three levels. It informs the PISA 2029 Media
  and AI Literacy assessment.
- **UNESCO**: the Media and Information Literacy curriculum (2021), its AI companion guide *AI Answers. You
  Decide.* (2026), the AI Competency Framework for Students (2024) and *Is there a right age for AI in
  education?* (2026).
- **EU Education and Skills Package** (2026): mainstreams AI literacy on the AILit framework, pilots an AI
  Literacy Certificate for 15-year-olds in 2027/2028, launches a European Healthy Screens Pledge, and sets
  a 2030 target of under 15% low achievers in computer and information literacy at age 13 to 14.
- **AI Act Art. 4** (as recast by the AI Omnibus, 2026): providers and deployers take measures to support the
  AI literacy of staff. In schools, the deployer is often the school; providers can help.

None of the quality frameworks EdTech companies already use checks, target by target, whether a product
contributes to these literacies, or whether its own behaviour undermines them. The Compass does that, and
reuses the evidence for those frameworks (section 7).

## 2. Two lenses

| Lens | Axes | When a target applies |
|---|---|---|
| **Learner**: what learners should know and be able to do | INF Information and media · COM Communication, citizenship and rights · CRE Creation and computational thinking · SAF Safety, privacy and wellbeing · PRB Problem solving and learning to learn · AI AI literacy | When the product **claims** the axis or target (in `csef.yaml` or in its own documents). Otherwise the target is shown as an opportunity, never as a failure. A maths game is not marked down for not teaching media literacy. |
| **Design**: what the product teaches by how it is built and supported | TRN Transparency that teaches · EDU Educator and family enablement | **Universal** targets apply to every product used by children. **Feature** targets apply when the product has the feature (AI, purchases, chat, recommender), using the same feature names as `csef.yaml`. |

The full list of 45 targets, with sources and framework references, is in the
[target catalogue](compass/catalogue.md). Each target says what to look for, why it matters, how to improve
and gives design ideas, mostly for games.

## 3. The evidence ladder

Each target in scope gets one level. Coverage and evidence strength are shown separately, never added up.

| Level | Name | Meaning |
|---|---|---|
| 0 | Not found | Nothing in the documents addresses the target. |
| 1 | Stated | The documents name or claim the target, without saying how. |
| 2 | Designed | Specific activities, mechanics, features or teacher materials are linked to the target. |
| 3 | Tested | The design was tried with learners or teachers (pilot, playtest, co-design) and results are recorded. |
| 4 | Measured | Learning outcomes were measured (pre/post, comparison group, independent evaluation). |

Plans do not count: "next step: a comparison study" stays a plan. The ladder lines up with the evidence tiers
of UNICEF's EdTech for Good Framework 2.0 (basic, intermediate, advanced) and the Dutch 3E framework
(Bronze, Silver, Gold), so a provider can move up one ladder and use it in the others.

## 4. Claims and the hidden curriculum

Two checks protect against "literacy-washing":

- **Claims.** Marketing and product texts are read for literacy claims ("teaches critical thinking",
  "builds online safety", "scientifically proven to boost digital literacy"). A claim on an axis with no
  target at Designed is reported as **unsupported**. A strong claim ("proven", "evidence-based") without
  Measured evidence is reported too. Claims about learning must be accurate (UCPD Art. 6 and 7; reliability
  in the EU guidelines on digital education content).
- **Hidden curriculum.** Copy, dialogue and mechanics that teach the opposite of a target are flagged as
  possible conflicts: an AI that says it is a friend or knows everything (AILit Engage 2), "spin the wheel"
  mechanics (consumer literacy), "don't break your streak" (wellbeing). Phrases quoted as something *not*
  to do are skipped.

## 5. The compass

The output is a compass rose, not a radar score:

- one **petal** per axis; its length is the share of targets in scope at Designed or above, its colour the
  highest evidence level reached;
- **dashed outlines** show which axes are in scope; axes not claimed stay empty and are labelled as such;
- a coral **needle** points to the first of the **next three steps** (the "heading"): fix conflicts first,
  then close baseline gaps, then back up or soften claims, then make claimed targets real, then test what is
  designed, then measure what is tested;
- the **centre ring** shows the CSEF safety scan, when its results are passed in.

The EU guidelines on digital education content suggest a radar chart for teachers; the Compass keeps each
axis separate instead, so nobody reads an area as a total.

## 6. Principles

1. **A profile, not a score.** No totals, no ranking, no league tables, no badge implying quality. This follows
   the stance of Swedish Edtech Industry's Kvalitetsportfolio and of UNICEF's EdTech for Good Framework.
2. **Evidence over claims.** Every result points to the passage that supports it. Claims are checked against
   evidence.
3. **People decide.** The tool reads wording; a person, or the csef-review skill, confirms meaning, and
   learners and teachers test the product.
4. **Fit before coverage.** Learner targets count only when the product claims them.
5. **Open and extensible.** CC BY 4.0 for the catalogue, Apache-2.0 for the code. National curricula and
   sector frameworks come in through packs (the Portugal pack maps targets to the *Referencial de Educação
   para os Media*).
6. **No learner data.** The Compass reads product documents and content, never data about pupils.

## 7. One dossier, many frameworks

Companies are asked to describe quality again and again, in different formats. The crosswalk
([compass/crosswalk.yaml](compass/crosswalk.yaml)) shows which Compass evidence also answers:

- the **EU guidelines on digital education content**: 8 criteria (pedagogical fit, engaging experiences,
  design and accessibility, reliability, impact and assessment, legal compliance, interoperability, financial
  viability);
- **Swedish Edtech Industry's Kvalitetsportfolio** v1.0: 7 quality areas, a self-declaration published on
  Edtechkartan. It is not a rating; the Compass keeps that spirit;
- **UNICEF's EdTech for Good Framework 2.0**: 5 pillars.

The mapping is indicative. Each framework keeps its own method.

## 8. How to run it

```bash
python3 tooling/compass.py --input docs/ --input marketing/ --input content/ --manifest csef.yaml \
        --csef-findings csef-report/findings.json --out-dir csef-compass
```

Inputs: design documents, teacher guides, evaluation reports, marketing copy (`.md`, `.txt`, `.html`, `.pdf`,
`.docx`) and in-product text (`.json`, `.yaml`, `.po`, `.csv`, `.arb`). Outputs: `compass.md`,
`compass.html` (self-contained, with the compass) and `compass.json` (the reusable dossier).

Declare what the product claims to teach in `csef.yaml`:

```yaml
compass:
  claims: [INF, AI]            # axes or target ids
  not_applicable:
    - target: INF-05
      reason: "Covered by the school's library programme."
```

Try it: `python3 tooling/compass.py --input examples/compass/fact-quest --manifest examples/compass/fact-quest/csef.yaml`.

With Claude, ask the csef-review skill: *"Run a Literacy Compass review of these documents."* The skill runs
the tool, then reads every document for meaning, in any language, and confirms or corrects each level.

## 9. Limits

- The tool reads words, not behaviour. A product can describe a good activity and ship a poor one; play it
  with learners.
- Matching works in English and European Portuguese. Other languages need terms in a pack, or the skill.
- Evidence levels come from the nearest passages and headings. A pilot described elsewhere may be missed.
- The catalogue maps to frameworks as published; it does not replace them. Framework owners (JRC, OECD,
  UNESCO, UNICEF, Swedish Edtech Industry) have not reviewed or endorsed this mapping.
- Like the rest of CSEF, the Compass is a framework, not a standard, and gives no presumption of conformity.

## 10. Open questions for reviewers

1. Are the eight axes the right cut, or should the learner lens follow DigComp's five areas exactly, with AI
   as a lens across them, as DigComp 3.0 does?
2. Which targets should be universal for every product used by children, beyond TRN and EDU?
3. Should the evidence ladder distinguish internal tests from independent evaluation at level 3?
4. How should age guidance (for example UNESCO's minimum age of 13 for independent use of generative AI in
   class) shape AI targets for younger bands?
5. Which national curricula and frameworks should come next as packs?
