# Regulatory map

Status as of **11 November 2026**. Check `standard/sources.yaml` for each source's `verified` date.
Rule ids link the instruments to the catalogue.

| Instrument | Status | What it means for EdTech used by children | Main CSES rules |
|---|---|---|---|
| **GDPR** (Reg. 2016/679) | In force | Legal basis, children's consent age (Art. 8, 13 to 16 nationally), DPIA, minimisation, rights, processors, transfers | CORE-DAT-*, CORE-SEC-*, AGE-B4-01 |
| **ePrivacy Directive** | In force | Consent for non-essential storage and cookies | CORE-DAT-11 |
| **Digital Services Act** (Reg. 2022/2065) | In force | Online platforms accessible to minors: high privacy, safety and security (Art. 28); no profiling ads to minors; no dark patterns (Art. 25) | CORE-COM-01, CORE-COM-03, CORE-SAF-* |
| **DSA Art. 28 guidelines** | Adopted Jul 2025, benchmark | Safe defaults, age assurance, contact safeguards, reporting, recommender choices | CORE-SAF-* (Level 2) |
| **AI Act** (Reg. 2024/1689) | Prohibitions since Feb 2025; Art. 50 from Aug 2026; high-risk education from 2 Dec 2027 (Digital Omnibus) | Emotion recognition in education banned; disclosure of AI; AI that evaluates, places or proctors learners is high-risk | CORE-AI-*, B-EVL-01, B-EVL-02 |
| **EU KIDS Act** proposal, COM(2026) 681 | Proposal of 17 Sep 2026; feedback until 3 Dec 2026 | Safety by design for online games, AI companions and chatbots: no addictive design, safe defaults, contact safeguards, tools for guardians, child-friendly reporting, privacy-preserving age assurance | Most Level 2 rules |
| **Digital Fairness Act** proposal | Due 11 Nov 2026 (leaked draft) | Blacklist of dark patterns; ban on paid loot boxes and pay-to-win for minors; virtual currency value and default-off; right to switch off streaks, autoplay and relationship-simulating chatbots | A-ECO-*, C-ENG-01, CORE-AI-06, CORE-SAF-03 |
| **UCPD** (Dir. 2005/29) | In force | No direct exhortation to children to buy | CORE-COM-04 |
| **Age verification Recommendation** | Adopted Apr 2026 | EU age verification app available in every Member State by end 2026 | CORE-SAF-08 |
| **European Accessibility Act** | Applies since Jun 2025 | Accessibility of covered digital services | CORE-ACC-* |
| **Cyber Resilience Act** | Reporting from Sep 2026, full from Dec 2027 | Vulnerability handling for products with digital elements | CORE-SEC-05 |
| **UN CRC General Comment 25** | Adopted 2021 | Children's rights in the digital environment; basis for child rights impact assessment | CORE-GOV-03, Level 3 rules |

## The EU KIDS Act and educational products

Three provisions of the proposal matter most for EdTech:

- **Art. 2(4)(c), exemption.** Services and systems *designed for primarily educational purposes, and
  operated by educational establishments or organisations, or on their behalf* are out of scope. A game
  deployed by a school can be exempt. The same game sold in an app store to families is an **online game**
  in scope (Art. 15).
- **Art. 3(5)(d), chatbots.** Educational AI is excluded from "general conversational chatbot". But an AI
  that provides *sustained, personalised interaction or companionship* simulating a relationship is an
  **AI companion** (Art. 3(5)(c)), whatever its domain.
- **Art. 15, online games.** Games must apply the addictive-design bans of Art. 9(1) and 9(2)(b)(d), safe
  default settings of Art. 11(1), contact safeguards of Art. 12(1) and 12(3)(c), mandatory tools for
  guardians (Art. 20), and guardian-controlled access below 13.

CSES Level 2 applies these measures as good practice in both cases. Teams record their actual legal
scope per distribution channel in `cses.yaml` (`legal_scope.kids_act`).
