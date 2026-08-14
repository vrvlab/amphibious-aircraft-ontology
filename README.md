# Amphibious Aircraft Ontology

**A machine-checkable formalization of the regulations and physics governing amphibious and seaplane design — starting with 14 CFR Part 25 water loads.**

> **Status: v0.2 — early. The constraint kernel is real, primary-sourced, and now
> executed in CI. The OWL layer still does not exist; a parameter vocabulary does.**
> We are looking for collaborators. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Why this exists

Amphibious aircraft design is one of the most tightly coupled problems in aerospace: a hull must be an efficient lifting body in flight and a rugged planing surface on water, while surviving transient slamming loads that excite aero- and hydro-elastic modes. The regulations governing this — 14 CFR Part 25 Subparts C and D — are prescriptive, interconnected, and entirely document-centric.

That last part is the bottleneck. Compliance is demonstrated by manual verification, which delays novel configurations and makes automated or AI-assisted design exploration unsafe: a generative model proposing hull geometry has no way to know it has violated a buoyancy margin or a minimum step load factor.

**The goal here is a substrate that lets a machine answer "is this design legal, and why?" with a citation.**

## The gap

Existing aerospace data models don't cover this. Concretely:

| Framework | What it is | Why it doesn't cover amphibians |
| --- | --- | --- |
| **CPACS** (DLR) | XML/XSD parametric aircraft schema | Syntactic, not semantic. No regulatory representation and no reasoning — it can describe a hull but not tell you *why* a thickness was chosen or whether a change violates Part 25. |
| **CMDOWS** | MDO workflow schema | Process automation only; captures no product physics. |
| **NASA CSSO** | Common Space Systems Ontology (OML) | Launch vehicles and spacecraft. Splashdown only; no atmospheric airworthiness rules. |
| **AIRCRAFT ontology** | OWL, civil single-aisle | Assumes a conventional land-based configuration. No planing hulls, transverse steps, chines, or flooding states. |
| **Codex** (DLR) | OWL/RDF over CPACS + SysML | Structural linkages; no aero–hydrodynamic coupling. |

No existing ontology represents planing-hull geometry, water-impact loads, or hydrostatic flooding states against airworthiness rules. That is the hole this project aims at.

## The finding that shapes this project

**The governing equations in §§ 25.527 and 25.533 are published as raster images, not
text.** The regulation states "computed as follows:", renders a PNG, and then defines the
variables. Any pipeline whose first step is "NLP-mine the regulatory text" will silently
miss the formulas entirely. Confirming them required reading the images directly.

**And the whole method is conditional.** § 25.521(b): §§ 25.523–25.537 apply *"unless a
more rational analysis of the water loads is made, or the standards in ANC-3 are used."*
These are a default path, not hard requirements. A formalization that encodes them as
mandatory is semantically wrong and will reject valid designs. Every constraint here
carries an `applicability` block.

> **We have got two of these wrong so far.** The first release claimed the Appendix B
> coefficients were undigitized empirical curves. They are not — Figure 2 is piecewise
> linear with every breakpoint labelled, and it is now encoded exactly. The claim was
> inferred from the text without reading the figures.
>
> Then § 25.337(c)(1) was encoded as `<= -1.0` while quoting *"may not be less than
> −1.0"* two lines above it — the machine-readable field contradicting the primary source
> printed beside it. Prose was doing the verification and nothing checked the field.
> **That is why the corpus is now executed rather than merely written**, and the first
> run of the validator found 11 more findings across 27 entries. Both retractions and the
> resulting process changes are in [`docs/verification-log.md`](docs/verification-log.md).

## What's here now

- **[`constraints/`](constraints/)** — 63 entries across Part 25 water loads, flight and ground loads in representation-neutral YAML. Every entry carries its formula, units, bounds, primary-source citation, and verification status.
- **[`parameters/`](parameters/)** — the canonical parameter vocabulary, and what each consuming project calls the same quantities. See below.
- **[`schema/`](schema/)** — JSON Schema for both, enforced in CI.
- **[`tools/`](tools/)** — validator, test runner, artifact builder, consumer conformance checker.
- **[`dist/constraints.json`](dist/constraints.json)** — the whole corpus as one file, for consumers without a YAML parser.
- **[`docs/verification-log.md`](docs/verification-log.md)** — what was checked against eCFR, what was confirmed, what was wrong in secondary sources, and what we got wrong ourselves.
- **[`appendix-b/`](appendix-b/)** — what Appendix B figures 1–3 actually contain, and what remains open about them (provenance, not digitization).

## Using it

Vendor `dist/constraints.json` and pin a tag. It is a single self-contained file readable
from any standard library, with entries sorted by id and a `content_sha256` over them:

```bash
python3 -c "import json;d=json.load(open('dist/constraints.json'));print(d['entry_count'],d['content_sha256'][:12])"
```

Do not transcribe constants into your own source. That is how `flightforge` came to carry
`C4 = 0.078 · C1` as a Python literal and a formula the corpus had never encoded, and how
the 2.33 step load floor came to be implemented downstream from a key no schema declared.
Load the entry and assert against it.

Everything is checked on every push:

```bash
python3 tools/validate.py && python3 tools/run_tests.py && python3 tools/check_consumers.py
```

`validate.py` enforces the schema, id uniqueness across the whole corpus, cross-reference
integrity, and that every symbol used in an expression is declared. `run_tests.py`
evaluates each `worked` test case **from the corpus itself** — expressions are parsed as
written and graph-valued terms interpolated from their declared breakpoints, so there is
no second copy of any formula to drift. Change a constant and the tests fail.

## The parameter vocabulary

The constraints say what the regulations require. [`parameters/`](parameters/) says what
the quantities are *called* — because three consuming projects independently invented
three vocabularies for the same hull, and each lost something different:

| | Ontology | Loftline | AeroGit | Flightforge |
| --- | --- | --- | --- | --- |
| deadrise | `beta` at station, `beta_k` at keel, `beta` at step — three distinct angles | one `deadrise_deg`, `0.0–60.0` | one `deadrise_deg`, `>0–45` | one `deadrise_deg` |
| forebody | `L_f` — the step station, definitionally | `forebody_fraction`, may differ from `step_fraction` | `L_forebody_fraction` | `step_fraction` *and* a Parkinson spray `L_forebody_fraction` |
| chine flare | selects § 25.533(b)(1) vs (b)(2) | carried | **absent** | carried |

Two of those are live defects. Loftline admits `deadrise_deg = 0.0`, and § 25.533 divides
by `tan β` — that hull is not flat-bottomed, it is undefined; AeroGit made the same bound
exclusive for exactly this reason. And "forebody fraction" means the step station in two
projects and a spray correlation length in the third, which are genuinely different
quantities that must not be substituted.

[`tools/check_consumers.py`](tools/check_consumers.py) reads each project's own source
read-only and fails if a recorded divergence goes stale in either direction — so a
conflation cannot be quietly fixed, or quietly introduced, without this repo noticing.

## Design decision: not OWL (yet)

This is deliberately **not** an OWL/SWRL ontology today, despite the name.

Ontologies are optimized for classification and consistency checking, and are poorly suited to the continuous numerical evaluation that sizing requires. The competency questions that actually matter early — *what is the minimum float volume for a 120,000 lb design landing weight?*, *does a 3% step height violate ventilation limits?* — are arithmetic with citations, not description logic.

So the kernel is stored in a neutral form that can be **projected into** OWL/RDF, SysML, or plain Python. A neutral kernel projects into OWL later; OWL does not project back out. When open-world subsumption reasoning is genuinely needed — classifying novel configurations against rule families — the OWL layer gets added on top of a corpus that is already verified.

## Non-goals

- **This is not certification advice.** Nothing here has regulatory standing. It is a research artifact. Verify against primary sources before relying on any of it.
- We are not reimplementing CPACS. Geometry interchange should reuse it where possible.
- We are not building solvers. The kernel is meant to *bound* solvers, not replace them.

## License

Apache-2.0. See [LICENSE](LICENSE).
