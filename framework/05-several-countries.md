# Several countries and shared infrastructure

Many EdTech products are built for several countries at once. Member States are also starting to build
shared education infrastructure. Both change what a product's architecture has to handle. This guide
explains why, and what to prepare now. It is not legal advice.

## Why now

**EDU-EDIC.** Commission Implementing Decision (EU) 2026/2413 set up the European Digital Infrastructure
Consortium on Education. It has been in force since 4 November 2026. The first applicants are the Netherlands,
France, Spain and Greece, followed by Croatia, Slovenia, Finland and Belgium. The seat is in The Hague.

Its aims:

- sovereign and interoperable digital infrastructure for education;
- fewer structural dependencies on providers from outside the EU;
- a European EdTech offer for schools, AI tools included;
- education data governance and interoperability.

The decision puts no obligations on EdTech providers. It does show what public buyers in those countries are
likely to ask for: open interfaces, portable data, clear governance and alternatives to non-EU providers.
CSEF cites it as context only (source `EDU-EDIC`).

**Data Act.** Chapter VI of Regulation (EU) 2023/2854 has applied since 12 September 2025. It gives customers
of data processing services, SaaS included, a right to switch provider. Switching charges are prohibited from
12 January 2027. Whether a given EdTech service is in scope needs case-by-case assessment.

**National differences.** The age of digital consent ranges from 13 to 16 (GDPR Art. 8). Rules on school
surveys, safeguarding routes, retention and approvals differ by country. The Portugal pack shows how much one
country adds.

## What to prepare

| Decision in your architecture | Rule | Prepare now |
|---|---|---|
| Where country differences live | CORE-INT-01 | One versioned file per country, referenced as `country_config`. No consent ages or approval steps in code. The strictest value is the default |
| How a school leaves | CORE-INT-02 | A school-level export with a published schema, OneRoster where it fits, an exit process in the contract, no switching fee |
| How people sign in | CORE-INT-03 | OpenID Connect or SAML from the school, LTI 1.3 launch from its learning platform, minimum roster fields, pseudonymous learner IDs |
| What you depend on | CORE-INT-04 | `jurisdiction`, `critical` and `fallback` for each third party. AI models behind one internal interface |
| Where data goes | CORE-DAT-03 | EEA hosting, or a documented transfer mechanism |
| National rules | Packs | One pack per country (see [02-packs.md](02-packs.md)) |

## Checklist for a product team

1. List the countries you sell in, or plan to, in `jurisdictions`.
2. Search the code for consent ages, retention periods and country names. Move them to configuration.
3. Export one school's full data. Could another provider import it?
4. Count the separate passwords a school has to manage. Can the school's own sign-in replace them?
5. For each critical provider outside the EU or EEA, write down what happens if it stops tomorrow.
6. Check that AI features can switch model without changing feature code.

## What we don't know yet

EDU-EDIC has not yet published a work programme or chosen technical standards. When it does, CSEF will map
them here and may turn some of these SHOULD rules into more specific ones. Feedback from teams already
selling in several countries is welcome: see [CONTRIBUTING.md](../CONTRIBUTING.md).
