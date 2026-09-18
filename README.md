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

## The regulation gets things wrong too

§ 25.535(d) specified a side load coefficient of **`3.25 tan β`** from 1964 until 2022,
when [Amdt. 25-148](https://www.federalregister.gov/documents/2022/12/09/2022-23327/miscellaneous-amendments)
corrected it to **`0.25`** in a rule addressing typographical errors. That is a
**thirteenfold** change in the unsymmetrical step side load on an auxiliary float, and it
stood for fifty-eight years in a paragraph whose sibling had `0.25` all along.

Anything built on a pre-2023 copy of Part 25 carries the larger figure — and the 2011
printed CFR, the version a search is most likely to surface as a PDF, still shows `3.25`.

This is why every entry carries an `edition`. A constant is not a fact; it is a fact *as
of an issue date*.

[`sources/`](sources/) makes that operational. One record per regulatory section — the
issue it was read from, the date the current text took effect, the verbatim Federal
Register amendment history, and **a digest of the section text itself**:

```bash
python3 tools/check_editions.py     # does the regulation still say what we verified?
python3 tools/as_of.py 2015-06-01   # what did it say then?
```

`check_editions.py` re-fetches every cited section and checks three things in increasing
order of reach: the citation line still matches, the eCFR versions API reports no later
amendment, and the **text digest** still matches. The third catches what the other two
miss — a correction that never touched the citation line. Pointed at the 2022 text it
fires on all three for § 25.535, which is how the capability was tested.

Figures get a fourth check, and for Appendix B it is the only one there is. **The entire
text content of Appendix B is twenty-one characters** — the words "Appendix B to Part 25".
Everything else in it is three images. So the eCFR endpoint that appeared to return an
empty document was not failing; there is nothing to return. All eleven published images
the corpus reads from are digested by their bytes, which is also the only thing anywhere
that would catch a figure being redrawn while the surrounding text stands untouched: a
breakpoint moving on figure 2 would change every K1 and K2 in the corpus without altering
one character of § 25.527.

It runs [weekly](.github/workflows/edition-drift.yml) rather than on push, and opens an
issue when the regulation moves. An upstream outage should not fail an unrelated build.

`as_of.py` answers the question a design review actually asks, because an aircraft is
certified to Part 25 *as amended through a stated amendment level* — not to whatever the
section says today.

Its horizon is **1997**, established by diffing the govinfo annual CFR editions rather
than eCFR, whose own history starts only in 2016. Above that date an entry with no
`history` block is unchanged *because the comparison was made*. Below it the tool says the
corpus cannot speak, rather than returning a confident answer it has not earned — govinfo
publishes no title-14 granule for 1996, and Amdt. 25-23 (1970), 25-46 (1978) and 25-72
(1990) predate the Federal Register's online archive too.

That exercise found that **§ 25.479 had no lateral drift landing condition at all** until
Amdt. 25-103 added it in 2001, so an airplane certified below that amendment was never
required to show the case.

## What's here now

- **[`constraints/`](constraints/)** — 63 entries across Part 25 water loads, flight and ground loads in representation-neutral YAML. Every entry carries its formula, units, bounds, primary-source citation, and verification status.
- **[`parameters/`](parameters/)** — the join between design parameters and regulatory symbols. Each quantity carries a QUDT unit IRI, an explicit measurement convention, and typed links to the constraints it appears in.
- **[`sources/`](sources/)** — [`sections/`](sources/sections/) records which issue was read, when the text took effect, and its full amendment history; [`figures/`](sources/figures/) digests the raster images the regulation publishes in place of text. Both trip when the source changes underneath.
- **[`schema/`](schema/)** — JSON Schema for constraints, parameters and sources, all enforced in CI.
- **[`tools/`](tools/)** — validator, test runner, artifact builder, consumer conformance checker.
- **[`units/`](units/)** — one record per unit the corpus uses: QUDT IRI, symbol, the UCUM code a consumer writes (`kg/m3`, `m/s`), the quantity kinds it measures, its SI dimension, and an exact factor to the coherent SI unit where it is not one. Shipped as [`dist/units.json`](dist/units.json).
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
`C4 = 0.078 · C1` as a Python literal alongside a formula the corpus had never encoded, and
how the 2.33 step load floor came to be implemented downstream from a key no schema
declared. Load the entry and assert against it.

Everything is checked on every push:

```bash
python3 tools/validate.py && python3 tools/run_tests.py && python3 tools/check_consumers.py
```

`validate.py` enforces both schemas, id uniqueness across the whole corpus, cross-reference
integrity, and that every symbol used in an expression is declared. `run_tests.py`
evaluates each `worked` test case **from the corpus itself** — expressions are parsed as
written and graph-valued terms interpolated from their declared breakpoints, so there is
no second copy of any formula to drift. Change a constant and the tests fail.

## The parameter layer

`constraints/` says what the regulation requires. It does not say what those symbols correspond to in a design tool — and that gap is where errors live.

14 CFR 25.527 uses `beta`. A parametric model has `deadrise_fwd` and `deadrise_aft`. Same physical quantity, different conventions, no connection. Existing frameworks cover one side each: **CPACS** has parametric geometry with no regulatory meaning; **14 CFR** has regulatory meaning with no parametric geometry. Neither covers the join.

`parameters/` is that join. Each entry declares its unit as a [QUDT](https://qudt.org) IRI, pins down its measurement convention, and links to regulatory symbols with a typed relationship:

| Relationship | Meaning |
| --- | --- |
| `identical` | same quantity, same convention |
| `discretization` | the tool samples a continuous regulatory quantity |
| `subset` | applies over part of the regulatory domain |
| `derived` | computed from, not equal to |
| `selects` | **the value determines which regulatory case applies** |

Anything other than `identical` must carry a caveat explaining the difference; the validator enforces it. An unexplained non-identical mapping is worse than no mapping.

**`selects` is why this layer is worth building.** Chine flare is a plain angle in degrees — a units registry would confirm that and catch nothing else. But its *value* decides whether § 25.533(b)(1) applies with `C₂ = 0.00213` or § 25.533(b)(2) applies with `C₃ = 0.0016`. A tool that carries a flare parameter and always evaluates the unflared formula is non-compliant in a way no unit check and no bounds check would ever detect.

### What the layer found

Each parameter records where it appears in real tools, under what name and with what bounds. Three consuming projects had independently invented three vocabularies for the same hull:

| | Ontology | Loftline | AeroGit | Flightforge |
| --- | --- | --- | --- | --- |
| deadrise | three distinct angles — `beta` at station, `beta_k` at keel, `beta` at the step | one `deadrise_deg`, `0.0–60.0` | one `deadrise_deg`, `>0–45` | one `deadrise_deg`, `10–25` |
| forebody | `L_f` — the step station, definitionally | `forebody_fraction`, may differ from `step_fraction` | `L_forebody_fraction` | `step_fraction`, plus a Parkinson spray `L_forebody_fraction` |
| chine flare | selects § 25.533(b)(1) vs (b)(2) | carried | **absent** | carried, switches on flare > 1° |

Two of those are live defects. Loftline admits `deadrise_deg = 0.0` inclusive, and § 25.533 divides by `tan β` — that hull is not flat-bottomed, it is *undefined*; AeroGit made the same bound exclusive for exactly this reason, and Flightforge's `_tan_deg` floors the angle at 1°, which is a numerical guard doing a validation job. And "forebody fraction" means the step station in two projects and a spray correlation length in the third; Flightforge's is correctly the latter, which is why the two are separate parameters here.

A third finding is an absence: § 25.535 auxiliary float loads are fully encoded, and **no consumer carries a float deadrise for them to act on**.

[`tools/check_consumers.py`](tools/check_consumers.py) reads each project's own source read-only and fails if an `implementations` claim goes stale in either direction — so a conflation cannot be quietly fixed, or quietly introduced, without this repo noticing.

### Units follow QUDT and CPACS

Units are QUDT IRIs, not strings — QUDT originated at NASA Ames (NExIOM/Constellation), is RDF/OWL so a reasoner can use it directly, and cross-references UCUM, UNECE and IEC 61360. Every IRI in use is checked to resolve at qudt.org.

Units are never encoded in parameter *names*. CPACS development guidelines §5 (*"element names are descriptive, without abbreviations or symbols"*) and QUDT (a unit is a property of a quantity) agree, and CPACS practice confirms it — 32 uses of `[m]` in its schema, zero of `[mm]`.

### Units are records, not a table inside the validator

Until v0.3.0 the list of known units was a Python dict in `tools/validate.py`. It checked the
corpus and reached no consumer: a tool pinning an edition could read that a parameter was in
`unit:LB_F` and could not read what `unit:LB_F` was. [`units/`](units/) is that table as data,
each record read against its defining document: the SI Brochure (9th edition, V4.01) for the
SI units, their dimensions, the degree and the knot; NIST SP 811 (2008) for the foot, the
pound-force and the pound-force per square inch.

Three things it makes checkable that were not:

- **A parameter's unit must measure its kind.** A length in pounds-force is refused. Dimension
  alone would not do it: plane angle and a ratio are both dimension one, a torque and an energy
  are both `kg m² s⁻²`. The `quantity_kinds` on a unit tell them apart.
- **A factor's arithmetic is executed.** `unit:LB_F` is `0.45359237*9.80665`, declared exact, and
  the validator multiplies it out. The knot is `1852/3600`, which no decimal holds, so it says
  `exact: false` and carries the expression.
- **A consumer that is SI inside knows where the boundary is.** `si_coherent` says which units
  it may write; `to_coherent_si` is the one factor by which a regulatory value in pounds or
  knots crosses over.

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
