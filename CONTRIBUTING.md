# Contributing

This project is early and openly looking for collaborators — particularly people with seaplane/flying-boat structures experience, naval architecture background, certification experience, or ontology engineering chops. You do not need all four. Nobody has all four.

## Two kinds of entry, two rules

The corpus holds **rules** and **definitions**, and they are held to different things ([`docs/CONOPS.md`](docs/CONOPS.md)).

**A rule traces to a primary source, or it is labelled as not doing so.** A rule is an entry in `constraints/`: its meaning is the regulation's. Not a textbook, not a paper summarizing the regulation, not an LLM. The regulation itself, or the standard itself, read, with the edition. If a value comes from somewhere else, it still belongs here — but it gets `status: unverified` or `status: interpretation` and says where it came from. Units are held the same way: a unit's meaning is the SI Brochure's or NIST's.

This exists because the project was seeded from an AI-generated report that was *mostly* right. Checking it against eCFR found two omitted coefficients and one materially wrong criterion (see [`docs/verification-log.md`](docs/verification-log.md)). Plausible and correct are different things, and a compliance artifact that blurs them is worse than useless — it is confidently wrong.

**A definition is exact enough to measure.** A definition is an entry in `parameters/` or `vocabularies/`: its meaning is the ontology's. It is done when two people measuring the same drawing get the same number, which means it says what is measured and what is excluded, from where to where, along what line where that matters, in what condition where the value depends on one, and what reads it. Sources are cited where they **agree** or **differ**; none is required. Where the sources read are silent, the entry chooses, says why, and is `defined`.

**The search for a definition's source is one pass.** The sources already cited in the corpus, and one search of the public archives (NTRS, govinfo, the Federal Register). What is found and legible is read and cited. Then the definition is written. No library requests, no statement inferred from a drawing, no scan too damaged to read. Record the pass in `checked_against`, so the next contributor does not repeat it.

### Verification statuses

| Status | Meaning | Rule | Definition |
| --- | --- | --- | --- |
| `verified` | Matches the primary source exactly. Cite the section or page and the edition date. | yes | yes, when a source states it exactly as the entry does |
| `partial` | Text verified, but depends on an undigitized figure or an unresolved reference. Cannot be evaluated end to end. | yes | yes |
| `unverified` | From a secondary source. Not yet checked. Legitimate to add — just say so. | yes | yes |
| `interpretation` | An engineering reading *not stated* in the regulation. Must be explicitly marked. `GM > 0` is the worked example of this. | yes | yes |
| `defined` | The ontology sets the meaning, or the part of it no source read states. Carries `verification.rationale`: why this convention, and what reads it. | **never** | yes |

Downgrading something from `verified` to `interpretation` because you checked and found it was an inference is a **valuable contribution**, not a criticism.

## Where help is most needed

1. **[Appendix B provenance](appendix-b/)** — the figure values are encoded; where they came from is not. Tracing them to the underlying NACA tank data would be a significant contribution. An independent second reading of the figure is also welcome.
2. **Sections not yet read** — §§ 25.523, 25.529, 25.531, 25.535, 25.537.
3. **CS-25 / EASA equivalents** — everything here is FAA. The EASA side is unstarted.
4. **ANC-3** — § 25.521(b) names it as an alternate standard. We have not located a copy.
5. **Worked examples from real aircraft** — a documented sizing case for any certified amphibian would let us validate the kernel against reality.
6. **Ontology engineering** — when the corpus is large enough to justify an OWL projection, we will need people who know description logic well enough to say what should *not* be modeled in it.

## Adding a constraint

Follow [`schema/constraint.schema.json`](schema/constraint.schema.json). Include:

- the primary-source URL **and the edition date you read** (regulations change; an undated citation is not reproducible)
- units on every variable, or `dimensionless`
- an `applicability` block if the constraint is conditional — most of Subpart C is, via § 25.521(b)
- a worked test case where the constraint is evaluable

## Adding a definition

Follow [`schema/parameter.schema.json`](schema/parameter.schema.json) or [`schema/vocabulary.schema.json`](schema/vocabulary.schema.json). Include:

- a definition and a measurement convention exact enough to measure (above)
- the unit, as a record in [`units/`](units/), whose kind the quantity is
- what reads it: a constraint in `regulatory_mapping`, or the use named in `rationale`
- the sources read, as agreeing or differing, and the search that was made

## What an edition promises

A consumer pins a tag. From the first edition after v0.6.0:

- **An id is permanent.** It is never reused or repurposed.
- **A meaning never changes under an id.** Wording may be made clearer where no measured value changes. A new meaning is a new id, and the old entry names it in `superseded_by`.
- **A parameter's unit never changes.**
- **An id is removed only in a major edition, after one edition in which it was superseded.**
- **A rule follows the regulation.** When an amendment changes the text, the entry changes with the edition read, under the same id.

`python3 tools/changelog.py --promise` compares the working tree with the last tag and fails on a removal or a unit change that breaks the promise. A changed meaning cannot be seen in the data; that part is the reviewer's.

## Releasing an edition

1. `python3 tools/changelog.py --write --next vX.Y.Z` rewrites [`CHANGELOG.md`](CHANGELOG.md) with every tag and the working tree as the new edition. It exits non-zero if the new edition breaks the promise.
2. Commit it, merge, and tag that commit. A human tags.

## What this project is not

Not certification guidance. Nothing here has regulatory standing, and a `verified` tag means "we read the source carefully," not "this is airworthiness-approved." Anyone doing real certification work uses the actual regulation and their ACO.

Saying so clearly is part of the contribution standard.
