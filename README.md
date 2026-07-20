# Amphibious Aircraft Ontology

**A machine-checkable formalization of the regulations and physics governing amphibious and seaplane design — starting with 14 CFR Part 25 water loads.**

> **Status: v0.1 — early. The constraint kernel is real and primary-sourced. The ontology layer does not exist yet.**
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

**14 CFR Part 25 Subpart C water loads cannot be extracted from regulatory text by NLP.** We verified this directly against eCFR:

1. **The governing formulas are raster images.** §§ 25.527 and 25.533 render their equations as PNGs hosted on `img.federalregister.gov` (e.g. `EC28SE91.036`). The surrounding text defines only the variables. A language model reading the CFR sees "computed as follows:" followed by nothing.

2. **Three critical coefficients are graphs, not numbers.** `K₁` (hull station weighing factor), `K₂`, and `β` (deadrise angle) all resolve to *figures in Appendix B* — printed curves. There is no closed form in the regulation.

3. **The whole method is conditional.** § 25.521(b): the §§ 25.523–25.537 procedure applies *"unless a more rational analysis of the water loads is made, or the standards in ANC-3 are used."* These are a default path, not hard requirements. Any formalization that encodes them as mandatory constraints is semantically wrong.

**Consequence:** digitizing Appendix B figures 1–3 is a hard prerequisite for this entire effort, and it is the single most reusable artifact we could publish. See [`appendix-b/`](appendix-b/).

## What's here now

- **[`constraints/`](constraints/)** — Part 25 water-load and float constraints in representation-neutral YAML. Every entry carries its formula, units, bounds, primary-source citation, and verification status.
- **[`schema/`](schema/)** — the constraint schema.
- **[`docs/verification-log.md`](docs/verification-log.md)** — what was checked against eCFR, what was confirmed, and what turned out to be wrong in secondary sources.
- **[`appendix-b/`](appendix-b/)** — the open problem. Empty, deliberately.

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
