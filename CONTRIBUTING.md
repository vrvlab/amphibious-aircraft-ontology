# Contributing

This project is early and openly looking for collaborators — particularly people with seaplane/flying-boat structures experience, naval architecture background, certification experience, or ontology engineering chops. You do not need all four. Nobody has all four.

## The one rule

**Every quantitative claim traces to a primary source, or it is labelled as not doing so.**

Not a textbook, not a paper summarizing the regulation, not an LLM. The regulation itself, or the standard itself. If a value comes from somewhere else, it still belongs here — but it gets `status: unverified` or `status: interpretation` and says where it came from.

This exists because the project was seeded from an AI-generated report that was *mostly* right. Checking it against eCFR found two omitted coefficients and one materially wrong criterion (see [`docs/verification-log.md`](docs/verification-log.md)). Plausible and correct are different things, and a compliance artifact that blurs them is worse than useless — it is confidently wrong.

### Verification statuses

| Status | Meaning |
| --- | --- |
| `verified` | Matches primary regulatory text exactly. Cite the section and the edition date. |
| `partial` | Text verified, but depends on an undigitized figure or an unresolved reference. Cannot be evaluated end to end. |
| `unverified` | From a secondary source. Not yet checked. Legitimate to add — just say so. |
| `interpretation` | An engineering reading *not stated* in the regulation. Must be explicitly marked. `GM > 0` is the worked example of this. |

Downgrading something from `verified` to `interpretation` because you checked and found it was an inference is a **valuable contribution**, not a criticism.

## Where help is most needed

1. **[Appendix B digitization](appendix-b/)** — the hard blocker. Bounded, verifiable, and useful outside this project.
2. **Sections not yet read** — §§ 25.523, 25.529, 25.531, 25.535, 25.537.
3. **CS-25 / EASA equivalents** — everything here is FAA. The EASA side is unstarted.
4. **ANC-3** — § 25.521(b) names it as an alternate standard. We have not located a copy.
5. **Worked examples from real aircraft** — a documented sizing case for any certified amphibian would let us validate the kernel against reality.
6. **Ontology engineering** — when the corpus is large enough to justify an OWL projection, we will need people who know description logic well enough to say what should *not* be modeled in it.

## Adding a constraint

Follow [`schema/constraint.schema.yaml`](schema/constraint.schema.yaml). Include:

- the primary-source URL **and the edition date you read** (regulations change; an undated citation is not reproducible)
- units on every variable, or `dimensionless`
- an `applicability` block if the constraint is conditional — most of Subpart C is, via § 25.521(b)
- a worked test case where the constraint is evaluable

## What this project is not

Not certification guidance. Nothing here has regulatory standing, and a `verified` tag means "we read the source carefully," not "this is airworthiness-approved." Anyone doing real certification work uses the actual regulation and their ACO.

Saying so clearly is part of the contribution standard.
