# Legislation, proposals and guidance

This page lists every legal and policy source behind the Child-Safe EdTech Framework (CSEF): what it is, its status, the provisions that matter for EdTech used by children, and which CSEF rules rely on it.

> Status as of **16 November 2026**. Each source has a `verified` date in `framework/sources.yaml`. Proposals are not law. This page is not legal advice.

## How sources map to compliance levels

| Source type | Can support | Meaning |
|---|---|---|
| Law in force, or adopted with a fixed date | Level 1 | Binding today or on a known date |
| Proposal, guidance, recommendation, technical standard | Level 2 | Where the law is heading, or the benchmark regulators use |
| Research and expert recommendations | Level 3 | See [research.md](research.md) |
| National law (packs) | Level 1 in that country | Loaded with `jurisdictions:` in `csef.yaml` |

## At a glance

| Source | Type | Status | CSEF rules | Compass targets |
|---|---|---|---|---|
| **GDPR** Regulation (EU) 2016/679, General Data Protection Regulation | law | In force since 25 May 2018 | 45 | 3 |
| **EPRIV** Directive 2002/58/EC, ePrivacy Directive (cookies and terminal equipment) | law | In force (transposed nationally) | 1 | 0 |
| **DSA** Regulation (EU) 2022/2065, Digital Services Act | law | Fully applicable since 17 Feb 2024 | 7 | 2 |
| **AIA** Regulation (EU) 2024/1689, Artificial Intelligence Act | law | Prohibitions (Art. 5) and AI literacy (Art. 4) apply since 2 Feb 2025 | 15 | 3 |
| **UCPD** Directive 2005/29/EC, Unfair Commercial Practices Directive | law | In force (transposed nationally) | 8 | 3 |
| **EAA** Directive (EU) 2019/882, European Accessibility Act | law | Applies since 28 Jun 2025 | 4 | 1 |
| **CRA** Regulation (EU) 2024/2847, Cyber Resilience Act | law | Reporting obligations from 11 Sep 2026 | 1 | 0 |
| **DATA-ACT** Regulation (EU) 2023/2854 (Data Act), Chapter VI: switching between data processing services | law | In force 11 Jan 2024; applies from 12 Sep 2025 | 1 | 0 |
| **CJEU-ART9** CJEU (Grand Chamber), C-184/20, OT v Vyriausioji tarnybinės etikos komisija, 1 Aug 2022 (EU:C:2022:601); see also C-252/21, Meta Platforms v Bundeskartellamt, 4 Jul 2023 | law | Case law | 1 | 0 |
| **AIA-OMNIBUS** Digital Omnibus on AI: Regulation amending the AI Act (reported as Regulation (EU) 2026/1744) | law | Adopted by Parliament 16 Jun 2026 and Council 29 Jun 2026; published in the Official Journal 24 Jul 2026; in force 27 Jul 2026 | 3 | 1 |
| **KIDS** Proposal for a Regulation: EU KIDS Act (Keeping Internet Digital Spaces Accountable and Trustworthy), COM(2026) 681 | proposal | Commission proposal of 17 Sep 2026 (2026/0286 COD) | 56 | 9 |
| **DFA** Digital Fairness Act (proposal replacing the Unfair Commercial Practices Directive) | proposal | Proposal due 11 Nov 2026 | 14 | 3 |
| **DSA-G28** Commission Guidelines on the protection of minors under Article 28 DSA | guidance | Adopted 14 Jul 2025 | 23 | 2 |
| **KIDS-COM** Communication: An EU approach to online child safety, COM(2026) 680 | guidance | Published 17 Sep 2026 | 5 | 0 |
| **KIDS-FAQ** The KIDS Act explained (Commission Q&A) | guidance | Published Sep 2026 | 1 | 0 |
| **AVREC** Commission Recommendation on an EU-wide framework for age verification (EU age verification app) | guidance | Adopted 29 Apr 2026 | 1 | 0 |
| **EDPB-CONSENT** EDPB Guidelines 05/2020 on consent under Regulation 2016/679 (section on children) | guidance | Adopted 4 May 2020 | 2 | 0 |
| **BIK** European strategy for a better internet for kids (BIK+) | guidance | Adopted May 2022 | 1 | 4 |
| **UNCRC-GC25** UN Committee on the Rights of the Child, General Comment No. 25 (2021) on children's rights in relation to the digital environment | guidance | Adopted 2021 | 19 | 3 |
| **EDPB-DDP** EDPB Guidelines 03/2022 on deceptive design patterns in social media platform interfaces: how to recognise and avoid them, version 2.0 | guidance | Adopted 14 Feb 2023 | 1 | 0 |
| **WP216** Article 29 Working Party, Opinion 05/2014 on Anonymisation Techniques (WP216) | guidance | Adopted 10 Apr 2014; endorsed by the EDPB. Aggregation and k-anonymity fail when groups are small or every member shares the same value | 1 | 0 |
| **DIGCOMP3** DigComp 3.0: European Digital Competence Framework, fifth edition (JRC144121). Cosgrove, J. and Cachia, R., Joint Research Centre | guidance | Published 27 Nov 2025. 5 areas, 21 competences, 4 proficiency levels, AI integrated across all competences | 0 | 24 |
| **AILIT** Empowering Learners for the Age of AI: an AI Literacy Framework for Primary and Secondary Education (AILit), European Commission and OECD | guidance | Final version presented 18 Jun 2026. 4 domains (Engage, Create, Manage, Shape AI), 19 competences, learner expectations at basic, intermediate and advanced levels | 0 | 20 |
| **EU-DEC** European Commission (2025). Making informed choices on digital education content: EU guidelines for teachers and educators | guidance | Manuscript completed Oct 2025; launched 5 Mar 2026 | 1 | 4 |
| **EDU-EDIC** Commission Implementing Decision (EU) 2026/2413 of 3 November 2026 on setting up the European Digital Infrastructure Consortium on Education (EDU-EDIC) | policy | In force 4 Nov 2026 | 4 | 0 |
| **EU-EDUPKG** European Commission (2026). Education and Skills Package (factsheet), with the Communication on stronger education foundations in the age of AI | policy | Presented 2026 | 0 | 3 |
| **WCAG22** W3C Web Content Accessibility Guidelines (WCAG) 2.2 | standard | W3C Recommendation | 6 | 0 |
| **W3C-233** W3C, Understanding WCAG Success Criterion 2.3.3 Animation from Interactions (Level AAA) | standard | W3C guidance | 2 | 0 |
| **EN301549** EN 301 549, Accessibility requirements for ICT products and services | standard | Harmonised European standard | 3 | 0 |
| **PEGI** PEGI, Pan European Game Information age rating system | standard | Industry self-regulation | 1 | 0 |
| **1EDTECH** 1EdTech Learning Tools Interoperability (LTI) 1.3 and OneRoster 1.2 | standard | Current versions (OneRoster 1.2 published Sep 2022) | 2 | 0 |
| **IEEE3527** IEEE 3527.1-2020, Standard for Digital Intelligence (DQ): Framework for Digital Literacy, Skills, and Readiness | standard | Active standard, published 15 Jan 2021. 8 areas of digital life, 3 levels, 24 competences | 0 | 4 |
| **IEEE2089** IEEE 2089-2021, Standard for an Age Appropriate Digital Services Framework Based on the 5Rights Principles for Children | standard | Active standard (2021) | 0 | 1 |
| **UNESCO-MIL** UNESCO (2021). Media and Information Literate Citizens: Think Critically, Click Wisely! Media and Information Literacy Curriculum for Educators and Learners, second edition | guidance | Published 2021. 19 broad learning outcomes and 6 values; 14 modules | 0 | 6 |
| **UNESCO-AIMIL** UNESCO (2026). AI Answers. You Decide. A Companion Guide to the UNESCO Media and Information Literacy Curriculum | guidance | Published 2026 | 0 | 6 |
| **UNESCO-AICFS** UNESCO (2024). AI Competency Framework for Students | guidance | Published 2024 | 0 | 4 |
| **UNESCO-AIAGE** UNESCO (2026). Is there a right age for AI in education? Deciding whether AI is age-appropriate and why (ED/FLI/ICT/2026/02) | guidance | Published 2026 | 0 | 4 |
| **ET4G2** UNICEF (2026). EdTech for Good Framework, Version 2.0 | guidance | Launched 24 Jun 2026 | 1 | 4 |
| **5R-AICODE** 5Rights Foundation (2025). Children and AI Design Code | guidance | Published 2025 | 0 | 1 |
| **UNICEF-AI** UNICEF Innocenti (2025). Guidance on AI and Children, version 3: checklist of 10 requirements and 48 recommendations | guidance | Published 2025 | 0 | 1 |
| **RPF-PRINC** Raspberry Pi Foundation (2026). Design principles for safe and responsible education technology, version 1.0 (draft for feedback) | guidance | Published Jul 2026 for feedback | 0 | 0 |
| **SWE-KP** Swedish Edtech Industry (2026). Kvalitetsportfolio för edtech, version 1.0 (published on Edtechkartan) | guidance | Version 1.0 of 18 Aug 2026 | 0 | 0 |
| **NL-3E** Garg, M. and Bakker, T. (2025). Dutch 3E Framework: Evidence-informed Evaluation of EdTech (The Hague University of Applied Sciences, Npuls) | guidance | Launched 10 Apr 2025 | 0 | 1 |
| **PT-LEI58** Lei n.º 58/2019, execução do RGPD na ordem jurídica nacional | law | In force since 9 Aug 2019 | 2 | 0 |
| **PT-DL83** Decreto-Lei n.º 83/2018, acessibilidade dos sítios web e aplicações móveis de organismos públicos | law | In force | 1 | 0 |
| **PT-CNPD** CNPD, guidance and list of processing operations requiring a DPIA | guidance | Check the current list on the CNPD website (verify) | 3 | 0 |
| **PT-ANACOM** ANACOM, Portuguese Digital Services Coordinator under the DSA | guidance | Designated Digital Services Coordinator | 0 | 0 |
| **PT-ISEGURA** Internet Segura (Portuguese Safer Internet Centre) and Linha Internet Segura | guidance | Operating | 3 | 1 |
| **PT-EPM** Referencial de Educação para os Media para a Educação Pré-escolar, o Ensino Básico e o Ensino Secundário (DGE), versão revista e atualizada | guidance | First approved 29 Apr 2014; revised and updated version of Dec 2023 (verify the current edition) | 0 | 5 |
| **PT-MIME** Despacho n.º 15847/2007, de 19 de junho (DR 2.ª série, n.º 140, 23 jul 2007): inquéritos em meio escolar; sistema MIME (Monitorização de Inquéritos em Meio Escolar), apreciação pela DGE, hoje EduQA, I.P. | law | In force | 3 | 1 |
| **PT-LPCJP** Lei de Proteção de Crianças e Jovens em Perigo, Lei n.º 147/99, de 1 de setembro (versão atual) | law | In force, as amended (latest by Lei 26/2018) | 1 | 0 |

## Law in force

### Regulation (EU) 2016/679, General Data Protection Regulation

*Id `GDPR` · law · EU · verified 2026-11-11*

The base layer for any product that processes children's personal data.

**Status.** In force since 25 May 2018.

**Provisions that matter for EdTech.**

- Art. 5: principles (minimisation, purpose limitation, storage limitation, accountability).
- Art. 6 and 8: legal basis; for information society services offered directly to a child and based on consent, guardian consent below the national age of digital consent (13 to 16).
- Art. 9: special categories, including biometric data used to identify a person.
- Art. 12: information in clear and plain language, in particular for children.
- Art. 22: no decisions with significant effects based solely on automated processing.
- Art. 25: data protection by design and by default.
- Art. 28: processor contracts (most school deployments).
- Art. 32 to 35: security, breach notification within 72 hours, Data Protection Impact Assessment.
- Chapter V: transfers outside the EEA.

**In CSEF.** Level 1 rules on data, security, roles, transfers and automated decisions.

**Rules citing it.** `CORE-GOV-01`, `CORE-DAT-01`, `CORE-DAT-02`, `CORE-DAT-03`, `CORE-DAT-04`, `CORE-DAT-05`, `CORE-DAT-06`, `CORE-DAT-07`, `CORE-DAT-08`, `CORE-DAT-09`, `CORE-DAT-10`, `CORE-DAT-11`, `CORE-DAT-12`, `CORE-DAT-13`, `CORE-DAT-14`, `CORE-DAT-15`, `CORE-DAT-16`, `CORE-DAT-17`, `CORE-DAT-18`, `CORE-COM-01`, `CORE-COM-02`, `CORE-AI-04`, `CORE-AI-07`, `CORE-SEC-01`, `CORE-SEC-02`, `CORE-SEC-03`, `CORE-SEC-04`, `CORE-SEC-05`, `CORE-SEC-06`, `CORE-INT-01`, `CORE-INT-02`, `CORE-INT-03`, `CORE-INT-04`, `A-ASM-01`, `B-EVL-02`, `B-EVL-03`, `B-UGC-01`, `B-UGC-02`, `B-DAT-01`, `C-ENG-02`, `AGE-B4-01`, `CORE-AI-08`, `CORE-CHT-01`, `CORE-CHT-07`, `CORE-CHT-09`

**Link.** [https://eur-lex.europa.eu/eli/reg/2016/679/oj](https://eur-lex.europa.eu/eli/reg/2016/679/oj)

### Directive 2002/58/EC, ePrivacy Directive

*Id `EPRIV` · law · EU · verified 2026-11-11*

Rules on storing or reading information on a user's device (cookies, local storage, SDK identifiers).

**Status.** In force (transposed nationally).

**Provisions that matter for EdTech.**

- Art. 5(3): consent for non-essential storage and access, transposed in national law.

**In CSEF.** Level 1 rule on consent for non-essential storage.

**Rules citing it.** `CORE-DAT-11`

**Link.** [https://eur-lex.europa.eu/eli/dir/2002/58/oj](https://eur-lex.europa.eu/eli/dir/2002/58/oj)

### Regulation (EU) 2022/2065, Digital Services Act

*Id `DSA` · law · EU · verified 2026-11-11*

Applies to intermediary services; the strongest duties fall on online platforms (users share content with each other).

**Status.** Fully applicable since 17 Feb 2024.

**Provisions that matter for EdTech.**

- Art. 16: notice and action (reporting illegal content); applies to hosting services, including chat and user content in learning products.
- Art. 25: no dark patterns in platform interfaces.
- Art. 28(1): appropriate and proportionate measures for a high level of privacy, safety and security of minors.
- Art. 26: advertisements on platforms must be clearly identifiable as such, with the advertiser shown.
- Art. 28(2): no advertising based on profiling when the provider is reasonably certain the user is a minor.
- Art. 39: advertising repositories for very large platforms.

**In CSEF.** Level 1 rules on advertising, dark patterns and contact; the Art. 28 guidelines drive many Level 2 rules.

**Rules citing it.** `CORE-COM-01`, `CORE-COM-03`, `CORE-SAF-05`, `CORE-SAF-06`, `CORE-COM-07`, `CORE-CHT-02`, `CORE-CHT-03`

**Link.** [https://eur-lex.europa.eu/eli/reg/2022/2065/oj](https://eur-lex.europa.eu/eli/reg/2022/2065/oj)

### Regulation (EU) 2024/1689, Artificial Intelligence Act

*Id `AIA` · law · EU · verified 2026-11-11*

The AI rulebook. Education is named both in the prohibitions and in the high-risk list.

**Status.** Prohibitions (Art. 5) and AI literacy (Art. 4) apply since 2 Feb 2025; Art. 4 recast by the AI Omnibus (2026): providers and deployers must take measures to support AI literacy of staff, no specific level required. GPAI rules since 2 Aug 2025. Transparency (Art. 50) from 2 Aug 2026.

**Provisions that matter for EdTech.**

- Art. 4: AI literacy for staff deploying AI (since 2 Feb 2025).
- Art. 5(1)(a)(b): ban on manipulative AI and AI exploiting age-related vulnerability.
- Art. 5(1)(f): ban on emotion recognition in education institutions (since 2 Feb 2025).
- Art. 50: tell people they interact with AI; mark AI-generated content (from 2 Aug 2026).
- Annex III(3): AI for admission, evaluating learning outcomes, steering learning, assessing level and monitoring tests is high-risk (obligations from 2 Dec 2027 after the Digital Omnibus).

**In CSEF.** Level 1 AI rules, the high-risk path for assessment products (Profile B), and AI disclosure.

**Rules citing it.** `CORE-AI-01`, `CORE-AI-02`, `CORE-AI-03`, `CORE-AI-04`, `CORE-AI-05`, `CORE-AI-06`, `CORE-AI-07`, `CORE-CNT-01`, `A-ASM-01`, `B-EVL-01`, `B-EVL-02`, `B-EVL-03`, `B-EVL-04`, `CORE-AI-09`, `CORE-AI-11`

**Link.** [https://eur-lex.europa.eu/eli/reg/2024/1689/oj](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)

### Directive 2005/29/EC, Unfair Commercial Practices Directive

*Id `UCPD` · law · EU · verified 2026-11-11*

Consumer protection against misleading and aggressive practices.

**Status.** In force (transposed nationally). Annex I point 28 bans direct exhortations to children to buy.

**Provisions that matter for EdTech.**

- Annex I point 11: using editorial content to promote a product, paid for by the trader, without making that clear (advertorial) is always unfair.
- Annex I point 28: including in an advertisement a direct exhortation to children to buy is always unfair.
- Arts. 5 to 9: misleading and aggressive practices, with vulnerability of children taken into account.

**In CSEF.** Level 1 rules on purchases, disguised advertising and dark patterns; will be replaced or amended by the Digital Fairness Act.

**Rules citing it.** `CORE-COM-03`, `CORE-COM-04`, `A-ECO-02`, `A-ECO-03`, `CORE-COM-05`, `CORE-COM-06`, `CORE-COM-07`, `CORE-AI-11`

**Link.** [https://eur-lex.europa.eu/eli/dir/2005/29/oj](https://eur-lex.europa.eu/eli/dir/2005/29/oj)

### Directive (EU) 2019/882, European Accessibility Act

*Id `EAA` · law · EU · verified 2026-11-11*

Accessibility requirements for a list of products and services, applying since 28 June 2025.

**Status.** Applies since 28 Jun 2025.

**Provisions that matter for EdTech.**

- Annex I: accessibility requirements, presumed met by applying harmonised standards (EN 301 549).

**In CSEF.** Level 1 accessibility rules (WCAG 2.2 AA target, pausing motion, colour not the only cue).

**Rules citing it.** `CORE-ACC-01`, `CORE-ACC-02`, `CORE-ACC-04`, `CORE-ACC-05`

**Link.** [https://eur-lex.europa.eu/eli/dir/2019/882/oj](https://eur-lex.europa.eu/eli/dir/2019/882/oj)

### Regulation (EU) 2024/2847, Cyber Resilience Act

*Id `CRA` · law · EU · verified 2026-11-11*

Cybersecurity for products with digital elements (software placed on the market, including apps).

**Status.** Reporting obligations from 11 Sep 2026. Main obligations from 11 Dec 2027.

**Provisions that matter for EdTech.**

- Art. 14: reporting of actively exploited vulnerabilities and severe incidents (from 11 Sep 2026).
- Annex I: security and vulnerability handling requirements (from 11 Dec 2027).

**In CSEF.** Level 1 rule on vulnerability handling and breach response.

**Rules citing it.** `CORE-SEC-05`

**Link.** [https://eur-lex.europa.eu/eli/reg/2024/2847/oj](https://eur-lex.europa.eu/eli/reg/2024/2847/oj)

### Regulation (EU) 2023/2854, Data Act (Chapter VI)

*Id `DATA-ACT` · law · EU · verified 2026-11-16*

Rules on switching between data processing services: IaaS, PaaS and SaaS offered to customers in the EU,
wherever the provider is established.

**Status.** In force 11 Jan 2024; applies from 12 Sep 2025. Chapter VI covers IaaS, PaaS and SaaS offered to customers in the EU, wherever the provider is established. Switching charges are prohibited from 12 Jan 2027 (Art. 29). Whether a given EdTech service is a data processing service needs case-by-case assessment.
12 Jan 2027 (Art. 29).

**Provisions that matter for EdTech.**

- Art. 23 to 26: customers can switch provider or move their exportable data; the contract sets out how.
- Art. 29: switching charges limited to costs until 12 Jan 2027, then prohibited.
- Whether an EdTech service sold to schools is a data processing service needs case-by-case assessment.

**In CSEF.** Level 2 basis for schools being able to take their data and leave.

**Rules citing it.** `CORE-INT-02`

**Link.** [https://eur-lex.europa.eu/eli/reg/2023/2854/oj](https://eur-lex.europa.eu/eli/reg/2023/2854/oj)

### CJEU (Grand Chamber), C-184/20, OT v Vyriausioji tarnybinės etikos komisija, 1 Aug 2022 (EU:C:2022:601); see also C-252/21, Meta Platforms v Bundeskartellamt, 4 Jul 2023

*Id `CJEU-ART9` · law · EU · verified 2026-11-14*

Data that can indirectly reveal special-category information (origin, religion, health, orientation) falls under GDPR Art. 9.

**Status.** Case law. Data liable to reveal special categories indirectly, by deduction or cross-referencing, fall under GDPR Art. 9.

**In CSEF.** Basis for not asking children questions that indirectly reveal family origin, religion or health.

**Rules citing it.** `CORE-DAT-15`

**Link.** [https://curia.europa.eu/juris/liste.jsf?num=C-184/20](https://curia.europa.eu/juris/liste.jsf?num=C-184/20)

## Adopted, applying later

### Digital Omnibus on AI (amendments to the AI Act)

*Id `AIA-OMNIBUS` · law · EU · verified 2026-11-14*

Moves the start of Annex III high-risk obligations, including education, to 2 December 2027.

**Status.** Adopted by Parliament 16 Jun 2026 and Council 29 Jun 2026; published in the Official Journal 24 Jul 2026; in force 27 Jul 2026. Annex III high-risk obligations (incl. education) apply from 2 Dec 2027. Art. 4 AI literacy becomes a duty to take measures to support AI literacy.

**Provisions that matter for EdTech.**

- Annex III high-risk obligations, including education, from 2 Dec 2027.

**Note.** Secondary source (law firm analysis). Replace with Official Journal reference when cited.

**In CSEF.** Dates on the high-risk path. The registry cites a law firm summary until the Official Journal reference is added.

**Rules citing it.** `CORE-AI-07`, `A-ASM-01`, `B-EVL-01`

**Link.** [https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/)

## EU proposals (in negotiation)

### EU KIDS Act (Keeping Internet Digital Spaces Accountable and Trustworthy), COM(2026) 681

*Id `KIDS` · proposal · EU · verified 2026-11-11*

Commission proposal of 17 September 2026 (procedure 2026/0286 COD). The single most important source for CSEF Level 2. Like all EU acts it has recitals, numbered (1), (2)..., which explain the intent, and articles, which carry the obligations. CSEF rules cite the article for the duty and the recital for the reasoning.

**Status.** Commission proposal of 17 Sep 2026 (2026/0286 COD). In legislative procedure. Would apply 6 months after entry into force.

**Provisions that matter for EdTech.**

- Scope. Art. 2(4)(c): services designed primarily for education and operated by or on behalf of educational establishments are exempt. Art. 3(5)(c): an AI companion is an AI system that simulates or facilitates a social, emotional or interpersonal relationship, whatever its domain. Art. 3(5)(d): educational AI is excluded from 'general conversational chatbot'.
- Minimum ages and accounts (Art. 6 to 8): limited accounts and minimum ages for social and video services; safe defaults.
- Addictive design (Art. 9): no infinite scroll, autoplay, re-engagement notifications or penalties for not engaging.
- Recommender systems (Art. 10).
- Safe default settings (Art. 11): location, microphone, camera, notifications, contact, image filters.
- Contact safeguards (Art. 12): no direct contact unless pre-approved, no contact recommendations, groups only with agreement, blocking without identity disclosed (12(1)); no enticing minors to approve contact (12(2)); limited visibility, no sharing of contact details, no downloading or screenshots of minors' content, no hosting of live streams by default (12(3)).
- Commercial practices (Recital 31, Art. 13). Recital 31 lists advertisements, product placement, virtual currencies, influencer marketing, sponsorship and AI-enhanced nudging as tactics with particular persuasive effects on minors, and confirms the UCPD and DSA Art. 25, 26, 28(2) and 39 continue to apply. Art. 13(1): a minor is told clearly and in real time that a purchase is an economic transaction, and virtual currency purchases show the value in the national currency. Art. 13(2): no design leading to excessive, impulsive or unwanted spending, including friction between content and purchases, and no variable reward systems (loot boxes). Art. 13 binds social and video services, and AI companions and chatbots through Art. 14(1)(c); Art. 15 does not apply it to online games, where the UCPD and the DFA apply.
- AI companions and chatbots (Recitals 32 to 34, Art. 14). Recital 32: safety by design, no simulated emotions or relationships that create dependency, persistent conversational memory disabled by default, testing before release and at regular intervals. Recital 33: post-market monitoring (micro and small enterprises exempt); mitigations by the provider of a general-purpose model under AI Act Art. 55 can be relied on but are not sufficient. Recital 34: when an AI chatbot is a feature of a platform or online game, minors can choose and opt out, are not nudged to use it, and safeguards apply where in-game purchases can occur. Art. 14(1): (a) no addictive design or relationship simulation, (b) safe settings and memory off by default, (c) economic transaction safeguards, (d) under 13 only through tools for guardians, (e) testing before release, (f) post-market monitoring. Art. 14(2): a chatbot inside a social service, video platform or online game is not activated automatically, not displayed prominently, not encouraged, and can be turned off at any time.
- Online games (Recitals 36 and 37, Art. 15): addictive design rules (no penalties or loss of benefits for not playing regularly), safe defaults, contact safeguards, mandatory tools for guardians, under 13 only through guardian tools, and safeguards so the game is not used to entice minors to other services, for example by restricting link-outs and showing warning messages (Recital 36). Recital 36 names cyberbullying, harassment, grooming, sexual abuse and extortion, trafficking, recruitment into criminal gangs and radicalisation as contact risks.
- Codes of conduct (Recital 39, Art. 17 and Art. 23): Art. 17 codes on age rating and online games must set criteria for violent, sexual, gambling and self-harm content, in-app purchases, contact risks and addictive design; free, independent redress; recognisable age labels shown before access or purchase; and regular, independent monitoring with KPIs. Art. 23 codes must set specific objectives and commitments and report regularly. Online games adhering to a code assessed as adequate may rely on it (Art. 15(4)), but participation alone does not presume compliance (Recital 39). PEGI is named as a benchmark. CSEF compares codes against these criteria with tooling/coc.py.
- Age ratings (Art. 16 to 17); child-friendly settings and reporting (Art. 18 to 19); tools for guardians (Art. 20).
- Age assurance (Art. 27 to 29). Art. 28(1): age assurance must not identify, locate, track, target, advertise to or profile the user.
- Member State duties (Art. 31): a free, privacy-preserving way for guardians to prove parental responsibility, and free access to the EU age verification solution. These bind governments, not providers, but products should use these means rather than collect ID.

**Note.** Art. 2(4)(c) exempts services designed primarily for education and operated by or on behalf of educational establishments. Art. 3(5)(d) excludes educational AI from 'general conversational chatbot'.

**In CSEF.** Most Level 2 rules: safe defaults, addictive design, contact and communications (CORE-SAF-05, CORE-CHT-*), rewards, purchases (CORE-COM-05 to 08), AI companions and chatbots (CORE-AI-06, 08 to 11), guardians, reporting, age assurance; and the code-of-conduct structure checks (COC-S01 to S11).

**Rules citing it.** `CORE-GOV-02`, `CORE-DAT-09`, `CORE-DAT-10`, `CORE-DAT-12`, `CORE-DAT-16`, `CORE-DAT-18`, `CORE-COM-04`, `CORE-SAF-01`, `CORE-SAF-02`, `CORE-SAF-03`, `CORE-SAF-04`, `CORE-SAF-05`, `CORE-SAF-06`, `CORE-SAF-07`, `CORE-SAF-08`, `CORE-SAF-09`, `CORE-SAF-10`, `CORE-SAF-11`, `CORE-AI-05`, `CORE-AI-06`, `CORE-CNT-02`, `A-ECO-01`, `A-ECO-03`, `A-PLY-01`, `A-SOC-01`, `B-UGC-01`, `B-UGC-02`, `B-OPS-01`, `C-ENG-01`, `C-ENG-02`, `C-ENG-03`, `C-ENG-04`, `C-ENG-05`, `AGE-B1-01`, `AGE-B2-01`, `AGE-B3-01`, `AGE-B4-01`, `AGE-B5-01`, `CORE-COM-05`, `CORE-COM-06`, `CORE-COM-07`, `CORE-COM-08`, `CORE-AI-08`, `CORE-AI-09`, `CORE-AI-10`, `CORE-AI-11`, `CORE-CHT-01`, `CORE-CHT-02`, `CORE-CHT-03`, `CORE-CHT-04`, `CORE-CHT-05`, `CORE-CHT-06`, `CORE-CHT-07`, `CORE-CHT-08`, `PT-LNG-01`, `PT-SUP-01`

**Link.** [https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52026PC0681](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52026PC0681)

### Digital Fairness Act (proposal)

*Id `DFA` · proposal · EU · verified 2026-11-11*

Expected to revise consumer law for the digital environment. Content in CSEF is based on a leaked draft and must be re-checked.

**Status.** Proposal due 11 Nov 2026. Content known from a leaked draft only. Re-verify against the official text.

**Provisions that matter for EdTech.**

- Leaked draft: blacklist of manipulative design practices.
- Ban on paid loot boxes and pay-to-win mechanics for minors.
- Virtual currencies: real-money value shown; off by default for children unless a guardian approves.
- Right to switch off streaks, autoplay and relationship-simulating chatbots.
- Ban on profiling-based advertising to minors extended to all traders.

**Note.** Leaked draft: ban on paid loot boxes and pay-to-win for minors, virtual currency value shown and off by default for children, right to switch off streaks, autoplay and relationship-simulating chatbots, blacklist of 10 dark patterns.

**In CSEF.** Level 2 rules on economy (A-ECO), streaks, autoplay and AI personas.

**Rules citing it.** `CORE-COM-01`, `CORE-COM-03`, `CORE-COM-04`, `CORE-SAF-02`, `CORE-SAF-03`, `CORE-AI-06`, `A-ECO-01`, `A-ECO-02`, `A-ECO-03`, `A-PLY-01`, `C-ENG-01`, `C-ENG-03`, `CORE-COM-05`, `CORE-COM-06`

**Link.** [https://www.euronews.com/2026/11/09/eu-to-blacklist-ten-manipulative-online-design-traps-leaked-draft-shows](https://www.euronews.com/2026/11/09/eu-to-blacklist-ten-manipulative-online-design-traps-leaked-draft-shows)

## EU guidance and recommendations

### Commission Guidelines on the protection of minors under Article 28 DSA (14 July 2025)

*Id `DSA-G28` · guidance · EU · verified 2026-11-11*

Not binding, but the benchmark the Commission uses to assess Art. 28 compliance.

**Status.** Adopted 14 Jul 2025. Not binding, used by the Commission as a compliance benchmark.

**Provisions that matter for EdTech.**

- Risk review; age assurance proportionate to risk; safe default settings; contact safeguards; recommender choices; moderation, reporting and support; child-friendly terms.

**In CSEF.** Level 2 safety-by-design and communications rules.

**Rules citing it.** `CORE-GOV-03`, `CORE-DAT-09`, `CORE-COM-02`, `CORE-SAF-01`, `CORE-SAF-02`, `CORE-SAF-03`, `CORE-SAF-05`, `CORE-SAF-06`, `CORE-SAF-08`, `CORE-SEC-06`, `A-SOC-01`, `B-UGC-01`, `B-SIM-01`, `C-ENG-02`, `AGE-B2-01`, `AGE-B5-01`, `CORE-CHT-01`, `CORE-CHT-02`, `CORE-CHT-03`, `CORE-CHT-04`, `CORE-CHT-06`, `CORE-CHT-07`, `CORE-CHT-08`

**Link.** [https://digital-strategy.ec.europa.eu/en/library/commission-publishes-guidelines-protection-minors](https://digital-strategy.ec.europa.eu/en/library/commission-publishes-guidelines-protection-minors)

### Communication: An EU approach to online child safety, COM(2026) 680 (17 September 2026)

*Id `KIDS-COM` · guidance · EU · verified 2026-11-11*

The policy frame around the KIDS Act.

**Status.** Published 17 Sep 2026.

**In CSEF.** Context for wellbeing and engagement rules.

**Rules citing it.** `CORE-SAF-04`, `A-ECO-04`, `C-ENG-04`, `C-ENG-05`, `C-ENG-06`

**Link.** [https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52026DC0680](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52026DC0680)

### The KIDS Act explained (Commission Q&A)

*Id `KIDS-FAQ` · guidance · EU · verified 2026-11-16*

Plain-language explanation of the proposal. Feedback open until 26 November 2026 (midnight Brussels time).

**Status.** Published Sep 2026. Feedback open until 26 Nov 2026 (midnight Brussels time).

**In CSEF.** Scope assessment rule (CORE-GOV-02).

**Rules citing it.** `CORE-GOV-02`

**Link.** [https://digital-strategy.ec.europa.eu/en/policies/kids-act](https://digital-strategy.ec.europa.eu/en/policies/kids-act)

### Commission Recommendation on an EU-wide framework for age verification (29 April 2026)

*Id `AVREC` · guidance · EU · verified 2026-11-11*

EU age verification app; Member States to offer a solution by 31 December 2026.

**Status.** Adopted 29 Apr 2026. Member States to offer a solution by 31 Dec 2026.

**In CSEF.** Age assurance rule.

**Rules citing it.** `CORE-SAF-08`

**Link.** [https://digital-strategy.ec.europa.eu/en/news/commission-urges-member-states-rollout-eu-age-verification-app](https://digital-strategy.ec.europa.eu/en/news/commission-urges-member-states-rollout-eu-age-verification-app)

### EDPB Guidelines 05/2020 on consent (section on children)

*Id `EDPB-CONSENT` · guidance · EU · verified 2026-11-11*

How to obtain and verify guardian consent.

**Status.** Adopted 4 May 2020.

**In CSEF.** Consent rules for minors.

**Rules citing it.** `CORE-DAT-11`, `AGE-B4-01`

**Link.** [https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-052020-consent-under-regulation-2016679_en](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-052020-consent-under-regulation-2016679_en)

### European strategy for a better internet for kids (BIK+), May 2022

*Id `BIK` · guidance · EU · verified 2026-11-11*

EU strategy on safe digital experiences, empowerment and participation of children.

**Status.** Adopted May 2022.

**In CSEF.** Currently in the registry without a rule citing it. Proposed: cite on reporting and support (CORE-SAF-06).

**Rules citing it.** `CORE-SAF-11`

**Link.** [https://digital-strategy.ec.europa.eu/en/policies/strategy-better-internet-kids](https://digital-strategy.ec.europa.eu/en/policies/strategy-better-internet-kids)

### UN Committee on the Rights of the Child, General Comment No. 25 (2021)

*Id `UNCRC-GC25` · guidance · international · verified 2026-11-11*

How the UN Convention on the Rights of the Child applies to the digital environment.

**Status.** Adopted 2021.

**In CSEF.** Child rights impact assessment and several Level 3 rules.

**Rules citing it.** `CORE-GOV-03`, `CORE-DAT-13`, `CORE-DAT-14`, `CORE-DAT-15`, `CORE-DAT-16`, `CORE-DAT-17`, `CORE-SAF-07`, `CORE-SAF-09`, `CORE-SAF-11`, `CORE-ACC-03`, `A-PLY-02`, `B-EVL-04`, `B-SIM-01`, `B-OPS-01`, `C-ENG-06`, `AGE-B1-01`, `CORE-DES-08`, `CORE-COM-08`, `CORE-CHT-08`

**Link.** [https://www.ohchr.org/en/documents/general-comments-and-recommendations/general-comment-no-25-2021-childrens-rights-relation](https://www.ohchr.org/en/documents/general-comments-and-recommendations/general-comment-no-25-2021-childrens-rights-relation)

### EDPB Guidelines 03/2022 on deceptive design patterns in social media platform interfaces: how to recognise and avoid them, version 2.0

*Id `EDPB-DDP` · guidance · EU · verified 2026-11-14*

How interface design can push people into sharing data or choices against their interest.

**Status.** Adopted 14 Feb 2023. Written for social media, but the patterns (overloading, skipping, stirring, obstructing, fickle, left in the dark) apply to any interface that asks for personal data.

**In CSEF.** Personal questions without pressure, rewards or nudges.

**Rules citing it.** `CORE-DAT-13`

**Link.** [https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-032022-deceptive-design-patterns-social-media_en](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-032022-deceptive-design-patterns-social-media_en)

### Article 29 Working Party, Opinion 05/2014 on Anonymisation Techniques (WP216)

*Id `WP216` · guidance · EU · verified 2026-11-14*

Why small or uniform groups can make aggregated data identifiable.

**Status.** Adopted 10 Apr 2014; endorsed by the EDPB. Aggregation and k-anonymity fail when groups are small or every member shares the same value.

**In CSEF.** Teacher views show only class totals large and varied enough to hide individuals.

**Rules citing it.** `CORE-DAT-17`

**Link.** [https://ec.europa.eu/justice/article-29/documentation/opinion-recommendation/files/2014/wp216_en.pdf](https://ec.europa.eu/justice/article-29/documentation/opinion-recommendation/files/2014/wp216_en.pdf)

### DigComp 3.0: European Digital Competence Framework, fifth edition (JRC144121). Cosgrove, J. and Cachia, R., Joint Research Centre

*Id `DIGCOMP3` · guidance · EU · verified 2026-11-14*

The European reference for digital competence: 5 areas, 21 competences, AI across all of them.

**Status.** Published 27 Nov 2025. 5 areas, 21 competences, 4 proficiency levels, AI integrated across all competences. CC BY 4.0.

**In CSEF.** Main reference for the Literacy Compass learner lens.

**Compass targets citing it.** `INF-01`, `INF-02`, `INF-03`, `INF-04`, `INF-05`, `COM-01`, `COM-02`, `COM-03`, `COM-04`, `COM-05`, `CRE-01`, `CRE-02`, `CRE-03`, `SAF-01`, `SAF-02`, `SAF-03`, `SAF-04`, `SAF-05`, `SAF-06`, `PRB-01`, `PRB-02`, `PRB-03`, `EDU-01`, `EDU-04`

**Link.** [https://data.europa.eu/doi/10.2760/0001149](https://data.europa.eu/doi/10.2760/0001149)

### Empowering Learners for the Age of AI: an AI Literacy Framework for Primary and Secondary Education (AILit), European Commission and OECD

*Id `AILIT` · guidance · EU · verified 2026-11-14*

European Commission and OECD framework for AI literacy in primary and secondary education.

**Status.** Final version presented 18 Jun 2026. 4 domains (Engage, Create, Manage, Shape AI), 19 competences, learner expectations at basic, intermediate and advanced levels. Informs the PISA 2029 Media and AI Literacy assessment.

**In CSEF.** Reference for the Compass AI axis.

**Compass targets citing it.** `INF-04`, `CRE-02`, `CRE-03`, `SAF-06`, `PRB-02`, `PRB-03`, `AI-01`, `AI-02`, `AI-03`, `AI-04`, `AI-05`, `AI-06`, `AI-07`, `AI-08`, `TRN-02`, `TRN-03`, `TRN-05`, `TRN-07`, `EDU-01`, `EDU-04`

**Link.** [https://ailiteracyframework.org/](https://ailiteracyframework.org/)

### European Commission (2025). Making informed choices on digital education content: EU guidelines for teachers and educators

*Id `EU-DEC` · guidance · EU · verified 2026-11-14*

Commission guidelines that help teachers judge digital education content against 8 quality criteria.

**Status.** Manuscript completed Oct 2025; launched 5 Mar 2026. Eight quality criteria (pedagogical fit and curriculum alignment, engaging learning experiences, design, accessibility and inclusion, reliability, impact and assessment, legal compliance, technical interoperability, financial viability); suggests a radar chart.

**In CSEF.** Crosswalk target for the Compass dossier.

**Rules citing it.** `CORE-DES-08`

**Compass targets citing it.** `EDU-01`, `EDU-02`, `EDU-03`, `EDU-05`

**Link.** [https://op.europa.eu/en/publication-detail/-/publication/1fa0183b-dbbe-11f0-8da2-01aa75ed71a1/language-en](https://op.europa.eu/en/publication-detail/-/publication/1fa0183b-dbbe-11f0-8da2-01aa75ed71a1/language-en)

## Policy context

### European Digital Infrastructure Consortium on Education (EDU-EDIC)

*Id `EDU-EDIC` · policy · EU · verified 2026-11-16*

Commission Implementing Decision (EU) 2026/2413 of 3 November 2026 sets up a consortium of Member States for
shared digital infrastructure in education. Applicants: Netherlands, France, Spain and Greece, then Croatia,
Slovenia, Finland and Belgium. Seat: The Hague.

**Status.** In force 4 Nov 2026. Applicants: Netherlands, France, Spain and Greece, then Croatia, Slovenia, Finland and Belgium; seat The Hague. Aims: sovereign and interoperable digital infrastructure for education, fewer dependencies on third-country providers, a European EdTech offer for schools including AI tools, education data governance and interoperability. Sets no obligations on EdTech providers; cited as context.

**Why it matters for EdTech.** Its aims are sovereign and interoperable infrastructure, fewer dependencies
on providers from outside the EU, a European EdTech offer for schools (AI tools included), and education data
governance and interoperability. Public buyers in member countries are likely to ask for the same. See
[05-several-countries.md](05-several-countries.md).

**In CSEF.** Context for the SHOULD rules on several countries and shared infrastructure.

**Rules citing it.** `CORE-INT-01`, `CORE-INT-02`, `CORE-INT-03`, `CORE-INT-04`

**Link.** [https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202602413](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202602413)

### European Commission (2026). Education and Skills Package (factsheet), with the Communication on stronger education foundations in the age of AI

*Id `EU-EDUPKG` · policy · EU · verified 2026-11-14*

Commission package with AI literacy, healthy screens and digital competence targets for 2030.

**Status.** Presented 2026. Mainstreams AI literacy on the AILit framework; AI Literacy Certificate pilot for 15-year-olds in 2027/2028; European Healthy Screens Pledge; EU 2030 target: under 15% low achievers in computer and information literacy (age 13-14).

**In CSEF.** Context for the Literacy Compass.

**Compass targets citing it.** `SAF-04`, `EDU-06`, `EDU-07`

**Link.** [https://doi.org/10.2766/6358386](https://doi.org/10.2766/6358386)

## Technical standards

### W3C Web Content Accessibility Guidelines 2.2

*Id `WCAG22` · standard · international · verified 2026-11-11*

The accessibility reference for web and app content.

**Status.** W3C Recommendation.

**Provisions that matter for EdTech.**

- 1.4.1 Use of colour, 1.4.2 Audio control, 2.2.2 Pause, stop, hide, 2.3.1 Three flashes (Levels A/AA).

**In CSEF.** Accessibility rules.

**Rules citing it.** `CORE-ACC-01`, `CORE-ACC-02`, `CORE-ACC-03`, `CORE-ACC-04`, `CORE-ACC-05`, `CORE-DES-01`

**Link.** [https://www.w3.org/TR/WCAG22/](https://www.w3.org/TR/WCAG22/)

### WCAG 2.3.3 Animation from Interactions (Level AAA)

*Id `W3C-233` · standard · international · verified 2026-11-11*

Motion triggered by interaction can be disabled.

**Status.** W3C guidance. Motion triggered by interaction can be disabled.

**In CSEF.** Reduced motion rule (Level 2).

**Rules citing it.** `CORE-ACC-02`, `CORE-DES-01`

**Link.** [https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html](https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html)

### EN 301 549, Accessibility requirements for ICT products and services

*Id `EN301549` · standard · EU · verified 2026-11-11*

Harmonised European standard used to show conformity with accessibility law.

**Status.** Harmonised European standard.

**Note.** Use the current version referenced in the Official Journal.

**In CSEF.** Accessibility rules. Exact version to be added.

**Rules citing it.** `CORE-ACC-01`, `CORE-ACC-02`, `CORE-ACC-04`

**Link.** [https://www.etsi.org/standards](https://www.etsi.org/standards)

### PEGI age rating system

*Id `PEGI` · standard · EU · verified 2026-11-11*

Industry self-regulation for game age ratings and content descriptors. Named by the KIDS Act proposal (Recital 39) as a benchmark for age labelling, promotion and marketing.

**Status.** Industry self-regulation.

**In CSEF.** Age rating self-assessment; reference point for code-of-conduct comparisons.

**Rules citing it.** `CORE-CNT-02`

**Link.** [https://pegi.info](https://pegi.info)

### 1EdTech LTI 1.3 and OneRoster 1.2

*Id `1EDTECH` · standard · international · verified 2026-11-16*

Open interoperability standards for education. LTI 1.3 launches a tool from a learning platform with OpenID
Connect based security. OneRoster 1.2 exchanges rosters, resources and gradebook data in CSV or REST.

**Status.** Current versions (OneRoster 1.2 published Sep 2022). LTI 1.3 launches a tool from a learning platform with OpenID Connect based security; OneRoster 1.2 exchanges rosters, resources and gradebook data in CSV or REST.

**In CSEF.** Recommended formats for school sign-in, launch and data export.

**Rules citing it.** `CORE-INT-02`, `CORE-INT-03`

**Link.** [https://www.1edtech.org/standards/oneroster](https://www.1edtech.org/standards/oneroster)

### IEEE 3527.1-2020, Standard for Digital Intelligence (DQ): Framework for Digital Literacy, Skills, and Readiness

*Id `IEEE3527` · standard · international · verified 2026-11-14*

IEEE standard for digital intelligence (DQ): literacy, skills and readiness.

**Status.** Active standard, published 15 Jan 2021. 8 areas of digital life, 3 levels, 24 competences.

**In CSEF.** Reference for Compass targets.

**Compass targets citing it.** `COM-01`, `COM-05`, `SAF-01`, `SAF-02`

**Link.** [https://standards.ieee.org/ieee/3527.1/7589/](https://standards.ieee.org/ieee/3527.1/7589/)

### IEEE 2089-2021, Standard for an Age Appropriate Digital Services Framework Based on the 5Rights Principles for Children

*Id `IEEE2089` · standard · international · verified 2026-11-14*

IEEE standard for age-appropriate design of digital services for children.

**Status.** Active standard (2021).

**In CSEF.** Reference for design-lens targets and rules.

**Compass targets citing it.** `TRN-01`

**Link.** [https://ieeexplore.ieee.org/document/9627644](https://ieeexplore.ieee.org/document/9627644)

## International guidance and frameworks

Guidance from UN agencies, foundations and other countries' industry and research bodies. Most of it feeds the [Literacy Compass](04-literacy-compass.md).

### UNESCO (2021). Media and Information Literate Citizens: Think Critically, Click Wisely! Media and Information Literacy Curriculum for Educators and Learners, second edition

*Id `UNESCO-MIL` · guidance · international · verified 2026-11-14*

UNESCO curriculum for media and information literacy.

**Status.** Published 2021. 19 broad learning outcomes and 6 values; 14 modules.

**In CSEF.** Reference for the Compass information and communication axes.

**Compass targets citing it.** `INF-01`, `INF-02`, `INF-03`, `INF-04`, `COM-03`, `COM-04`

**Link.** [https://www.unesco.org/en/media-information-literacy](https://www.unesco.org/en/media-information-literacy)

### UNESCO (2026). AI Answers. You Decide. A Companion Guide to the UNESCO Media and Information Literacy Curriculum

*Id `UNESCO-AIMIL` · guidance · international · verified 2026-11-14*

UNESCO companion guide on AI and media and information literacy.

**Status.** Published 2026. Extends MIL to AI: sources, accountability, filtering, lateral reading, rights. Recalls UNESCO's minimum age of 13 for independent use of generative AI in class.

**In CSEF.** Reference for the Compass AI and information axes.

**Compass targets citing it.** `INF-02`, `INF-04`, `AI-02`, `AI-03`, `AI-05`, `AI-06`

**Link.** [https://doi.org/10.58338/JXYO3928](https://doi.org/10.58338/JXYO3928)

### UNESCO (2024). AI Competency Framework for Students

*Id `UNESCO-AICFS` · guidance · international · verified 2026-11-14*

UNESCO AI competency framework for students.

**Status.** Published 2024. Human-centred mindset, ethics of AI, AI techniques and applications, AI system design.

**In CSEF.** Reference for the Compass AI axis.

**Compass targets citing it.** `AI-01`, `AI-04`, `AI-05`, `AI-08`

**Link.** [https://www.unesco.org/en/articles/ai-competency-framework-students](https://www.unesco.org/en/articles/ai-competency-framework-students)

### UNESCO (2026). Is there a right age for AI in education? Deciding whether AI is age-appropriate and why (ED/FLI/ICT/2026/02)

*Id `UNESCO-AIAGE` · guidance · international · verified 2026-11-14*

UNESCO guidance on deciding at what age and how AI should be used in education.

**Status.** Published 2026. Calls for shared, evidence-based criteria for age-appropriate AI and for independent evaluation schemes.

**In CSEF.** Reference for AI targets by age band.

**Compass targets citing it.** `AI-02`, `AI-04`, `TRN-07`, `EDU-04`

**Link.** [https://www.unesco.org/en/digital-education](https://www.unesco.org/en/digital-education)

### UNICEF (2026). EdTech for Good Framework, Version 2.0

*Id `ET4G2` · guidance · international · verified 2026-11-14*

UNICEF framework for EdTech that is safe, inclusive and effective.

**Status.** Launched 24 Jun 2026. Five pillars (safety and well-being, educational impact, designed for teaching and learning, contextual readiness, inclusive access); evidence portfolio; does not rank or certify. CC BY 4.0.

**In CSEF.** Crosswalk target for the Compass dossier.

**Rules citing it.** `CORE-DES-08`

**Compass targets citing it.** `EDU-01`, `EDU-02`, `EDU-03`, `EDU-05`

**Link.** [https://www.unicef.org/digitaleducation/edtech-for-good](https://www.unicef.org/digitaleducation/edtech-for-good)

### 5Rights Foundation (2025). Children and AI Design Code

*Id `5R-AICODE` · guidance · international · verified 2026-11-14*

5Rights Foundation design code for AI systems that children use.

**Status.** Published 2025.

**In CSEF.** Reference for AI transparency targets.

**Compass targets citing it.** `TRN-02`

**Link.** [https://5rightsfoundation.com/resource/children-ai-design-code/](https://5rightsfoundation.com/resource/children-ai-design-code/)

### UNICEF Innocenti (2025). Guidance on AI and Children, version 3: checklist of 10 requirements and 48 recommendations

*Id `UNICEF-AI` · guidance · international · verified 2026-11-14*

UNICEF Innocenti guidance on AI and children's rights.

**Status.** Published 2025.

**In CSEF.** Reference for AI targets and rules.

**Compass targets citing it.** `TRN-02`

**Link.** [https://www.unicef.org/innocenti/media/11996/file/UNICEF-Innocenti-Guidance-on-AI-and-Children-3-Checklist-2025.pdf](https://www.unicef.org/innocenti/media/11996/file/UNICEF-Innocenti-Guidance-on-AI-and-Children-3-Checklist-2025.pdf)

### Raspberry Pi Foundation (2026). Design principles for safe and responsible education technology, version 1.0 (draft for feedback)

*Id `RPF-PRINC` · guidance · international · verified 2026-11-14*

Raspberry Pi Foundation design principles for AI in education.

**Status.** Published Jul 2026 for feedback. Eight principles drawing on RITEC, UN General Comment 25, Child Rights by Design and EdTech for Good.

**In CSEF.** Reference for AI literacy targets.

**Link.** [https://www.raspberrypi.org/blog/draft-principles-for-safe-responsible-edtech/](https://www.raspberrypi.org/blog/draft-principles-for-safe-responsible-edtech/)

### Swedish Edtech Industry (2026). Kvalitetsportfolio för edtech, version 1.0 (published on Edtechkartan)

*Id `SWE-KP` · guidance · SE · verified 2026-11-14*

Swedish Edtech Industry self-declaration portfolio for EdTech quality.

**Status.** Version 1.0 of 18 Aug 2026. Self-declaration in seven quality areas for members; not a rating, certification or evidence framework.

**In CSEF.** Crosswalk target for the Compass dossier.

**Link.** [https://edtechkartan.se/kvalitetsportfolio/](https://edtechkartan.se/kvalitetsportfolio/)

### Garg, M. and Bakker, T. (2025). Dutch 3E Framework: Evidence-informed Evaluation of EdTech (The Hague University of Applied Sciences, Npuls)

*Id `NL-3E` · guidance · NL · verified 2026-11-14*

Dutch framework for evidence-informed evaluation of EdTech.

**Status.** Launched 10 Apr 2025. Bronze, Silver and Gold tiers for the strength of evidence.

**In CSEF.** Reference for the Compass evidence ladder.

**Compass targets citing it.** `EDU-03`

**Link.** [https://www.thuas.com/research/centre-expertise/3e-evidence-based-evaluation-edtech](https://www.thuas.com/research/centre-expertise/3e-evidence-based-evaluation-edtech)

## National: Portugal (pack, draft)

### Lei n.º 58/2019

*Id `PT-LEI58` · law · PT · verified 2026-11-11*

Portuguese GDPR implementation law.

**Status.** In force since 9 Aug 2019. Art. 16: age of digital consent is 13.

**Provisions that matter for EdTech.**

- Art. 16: age of digital consent is 13.

**In CSEF.** Consent rules for minors in Portugal.

**Rules citing it.** `AGE-B4-01 (PT amendment)`, `CORE-DAT-11 (PT amendment)`

**Link.** [https://diariodarepublica.pt/dr/detalhe/lei/58-2019-123815982](https://diariodarepublica.pt/dr/detalhe/lei/58-2019-123815982)

### Decreto-Lei n.º 83/2018

*Id `PT-DL83` · law · PT · verified 2026-11-11*

Accessibility of public bodies' websites and apps, including public schools.

**Status.** In force. Applies to public bodies, including public schools, and their apps.

**In CSEF.** Raises CORE-ACC-01 to Level 1 for products delivered to public bodies.

**Rules citing it.** `CORE-ACC-01 (PT amendment)`

**Link.** [https://diariodarepublica.pt/dr/detalhe/decreto-lei/83-2018-116734769](https://diariodarepublica.pt/dr/detalhe/decreto-lei/83-2018-116734769)

### CNPD (Comissão Nacional de Proteção de Dados)

*Id `PT-CNPD` · guidance · PT · verified 2026-11-11*

Portuguese supervisory authority; list of processing requiring a DPIA (to verify).

**Status.** Check the current list on the CNPD website (verify).

**In CSEF.** DPIA and breach notes.

**Rules citing it.** `CORE-DAT-01 (PT amendment)`, `CORE-SEC-05 (PT amendment)`, `CORE-DAT-15 (PT amendment)`

**Link.** [https://www.cnpd.pt](https://www.cnpd.pt)

### ANACOM

*Id `PT-ANACOM` · guidance · PT · verified 2026-11-11*

Portuguese Digital Services Coordinator under the DSA.

**Status.** Designated Digital Services Coordinator.

**In CSEF.** Registry only.

**Rules citing it.** none (context)

**Link.** [https://www.anacom.pt](https://www.anacom.pt)

### Internet Segura and Linha Internet Segura

*Id `PT-ISEGURA` · guidance · PT · verified 2026-11-11*

Portuguese Safer Internet Centre and helpline.

**Status.** Operating. Helpline for children, guardians and educators.

**In CSEF.** Help screens and support.

**Rules citing it.** `PT-SUP-01`, `CORE-SAF-06 (PT amendment)`, `CORE-SAF-11 (PT amendment)`

**Link.** [https://www.internetsegura.pt](https://www.internetsegura.pt)

### Referencial de Educação para os Media para a Educação Pré-escolar, o Ensino Básico e o Ensino Secundário (DGE), versão revista e atualizada

*Id `PT-EPM` · guidance · PT · verified 2026-11-14*

Portuguese reference framework for media education, from pre-school to secondary.

**Status.** First approved 29 Apr 2014; revised and updated version of Dec 2023 (verify the current edition).

**In CSEF.** Portugal pack: mapped to Compass information and communication targets.

**Compass targets citing it.** `INF-02 (PT)`, `INF-03 (PT)`, `INF-04 (PT)`, `COM-03 (PT)`, `EDU-01 (PT)`

**Link.** [https://cidadania.dge.mec.pt/sites/default/files/pdfs/referencial-epm-versaoatualizada-12dez2023.pdf](https://cidadania.dge.mec.pt/sites/default/files/pdfs/referencial-epm-versaoatualizada-12dez2023.pdf)

### Despacho n.º 15847/2007, de 19 de junho (DR 2.ª série, n.º 140, 23 jul 2007): inquéritos em meio escolar; sistema MIME (Monitorização de Inquéritos em Meio Escolar), apreciação pela DGE, hoje EduQA, I.P.

*Id `PT-MIME` · law · PT · verified 2026-11-15*

Despacho requiring prior approval of questionnaires and surveys in schools, now appraised by EduQA, I.P. through MIME.

**Status.** In force. Questionnaires and surveys in public schools need prior authorisation through MIME. The DGE was extinguished and its functions passed to EduQA, I.P. (Decreto-Lei 105/2025), which now appraises requests and says when guardian authorisation is needed. Sensitive questions may need a prior CNPD opinion.

**In CSEF.** Portugal pack: rule PT-SUR-01.

**Rules citing it.** `PT-SUR-01`, `CORE-DAT-15 (PT amendment)`, `B-DAT-01 (PT amendment)`

**Compass targets citing it.** `EDU-03 (PT)`

**Link.** [https://www.dge.mec.pt/sites/default/files/DSPE/mime/despacho_n_15_846_de_2007.pdf](https://www.dge.mec.pt/sites/default/files/DSPE/mime/despacho_n_15_846_de_2007.pdf)

### Lei de Proteção de Crianças e Jovens em Perigo, Lei n.º 147/99, de 1 de setembro (versão atual)

*Id `PT-LPCJP` · law · PT · verified 2026-11-14*

Portuguese law on the protection of children and young people in danger.

**Status.** In force, as amended (latest by Lei 26/2018). Schools are entities with competence in childhood matters; danger situations are reported to the CPCJ.

**In CSEF.** Portugal pack: safeguarding route for disclosures.

**Rules citing it.** `CORE-SAF-11 (PT amendment)`

**Link.** [https://diariodarepublica.pt/dr/detalhe/lei/147-1999-581619](https://diariodarepublica.pt/dr/detalhe/lei/147-1999-581619)

## Open discussions and watch list

| Item | What to watch | Effect on CSEF |
|---|---|---|
| EU KIDS Act | Feedback until 26 Nov 2026; then Parliament and Council positions | Level 2 rules may change; when adopted, they move to Level 1 with the application date |
| Digital Fairness Act | Publication of the official proposal | Replace leaked-draft source; confirm A-ECO-01/02/03, C-ENG-01, CORE-AI-06, CORE-SAF-03 |
| Digital Omnibus on AI | Commission guidance on the recast Art. 4 | Check AI literacy wording and high-risk dates |
| EDU-EDIC | Work programme and the technical standards it chooses | CORE-INT rules may become more specific |
| AI Office guidance | Art. 50 code of practice; guidelines on Annex III classification | Detail on AI disclosure and assessment products |
| EDPB | Guidance on age assurance and children's data | Possible updates to CORE-SAF-08 and consent rules |
| National packs | Contributions for other Member States; Portugal review by a lawyer | National consent ages, authorities, helplines |
