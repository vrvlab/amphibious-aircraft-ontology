# Constraint schema

[`constraint.schema.json`](constraint.schema.json) is **normative** and enforced in CI
by [`tools/validate.py`](../tools/validate.py). This file is its prose companion. Where
the two disagree, the JSON Schema wins.

> This replaces the earlier `constraint.schema.yaml`, which described the fields in
> prose (`id: string`, `kind: enum`) and could not be executed. Nothing validated
> against it, and the corpus had already drifted away from it in three places — the
> first run of the new validator found 11 findings across 27 entries.

## Shape

A constraint file is a **list** of entries. Each entry always carries `id`, `title`,
`kind`, `source`, and `verification`, plus a payload determined by `kind`:

| `kind` | Payload required | Meaning |
| --- | --- | --- |
| `formula` | `formula` | A computable expression with every symbol declared |
| `bound` | `bound` | A one-sided or exact limit on a quantity |
| `cardinality` | `bound` | A count (e.g. ≥ 5 watertight compartments) |
| `assertion` | `statement` | A rule stated in prose that is not arithmetic |
| `qualitative` | `statement` | A definition, convention, or scope note |

## The load-bearing fields

**`verification.status`** is what separates this corpus from a transcription of a
secondary source.

- `verified` — matches primary regulatory text exactly.
- `partial` — text verified, but depends on a source not yet read.
- `unverified` — from a secondary source, not yet checked against primary.
- `interpretation` — an engineering reading **not stated in the regulation**. The id
  must then begin with `interp-`, so that downstream code filtering on id prefix does
  not have to open the file to find out.

**`verification.checked_against`** must name what was actually read — an endpoint, an
issue date, an image id. "The regulation" is not an answer.

**`verification.sign_convention`** is required wherever the regulation's plain wording
and its engineering reading differ in sign or in magnitude-vs-signed form. It exists
because of a real defect: `cfr-25.337-c1-negative-limit-to-vc` encoded `<= -1.0` while
quoting *"may not be less than −1.0"* immediately above it. Those say opposite things.
An operator that silently contradicts the text beside it is the exact failure this
corpus exists to prevent.

**`applicability`** carries § 25.521(b): §§ 25.523–25.537 apply *"unless a more rational
analysis of the water loads is made, or the standards in ANC-3 are used."* Most of
Subpart C is a default path, not a hard requirement. A reasoner that treats these as
mandatory will reject valid designs.

**`formula.source_render`** is a URL to the published image, present when the regulation
prints the equation as a raster instead of as text — which §§ 25.527, 25.531, 25.533 and
25.535 all do. Its presence is a claim that the image was read. Do not add it otherwise.

**`test_cases[].status: worked`** is *earned* by [`tools/run_tests.py`](../tools/run_tests.py),
not asserted by an author. CI fails if a `worked` case does not reproduce.

## Rules the schema cannot express

`tools/validate.py` additionally enforces:

1. **ids are unique across the whole corpus**, not merely within a file.
2. **cross-references resolve** — any `cfr-…` or `interp-…` token appearing in a
   `formula` or `applicability` block must name an entry that exists.
3. **every symbol in an expression is declared.** Entries do not inherit variables from
   their siblings: `cfr-25.527-a2` must be resolvable without knowing `cfr-25.527-a1`
   exists, because a consumer can pin either one alone.

## Adding an entry

```bash
python3 tools/validate.py && python3 tools/run_tests.py
```

Both run in CI on every push and pull request. See
[`CONTRIBUTING.md`](../CONTRIBUTING.md) for the verification standard itself — the
schema checks shape, not truth.

---

# Parameter schema

[`parameter.schema.json`](parameter.schema.json) is **normative** and enforced by the same
validator. It replaces the earlier `parameter.schema.yaml`, which described the fields in
prose and could not be executed — the same problem the constraint schema had, and it was
solved the same way.

A parameter is an engineering quantity with a canonical definition, a unit, a measurement
convention, and typed links to the regulatory symbols it corresponds to.

## Why the layer exists

`constraints/` encodes what the regulation requires. It does not say what the quantities
in those formulas correspond to in a design tool. 14 CFR 25.527 uses `beta`; a parametric
model has `deadrise_fwd` and `deadrise_aft`. These describe the same physical quantity
under different conventions, and nothing else connects them. A wrong mapping feeds a wrong
number into a load factor with nothing to catch it.

## Units

Units are **QUDT IRIs, not strings**. QUDT originated at NASA Ames (NExIOM / Constellation),
is RDF/OWL so it is usable directly by a reasoner, and cross-references UCUM, UNECE and
IEC 61360. A `symbol` field carries the CPACS-style bracket form for human readability, and
the validator checks the two agree — `unit:DEG` must carry `deg`. Both come from the unit's
record in [`units/`](../units/), described below.

Units are **never** encoded in parameter names. CPACS development guidelines §5 (*"element
names are descriptive, without abbreviations or symbols"*) and QUDT (a unit is a property
of a quantity) agree on this.

## `regulatory_mapping`

The join. `relationship` comes from a closed vocabulary:

| Value | Meaning |
| --- | --- |
| `identical` | the same quantity, same convention |
| `discretization` | the tool samples a continuous regulatory quantity |
| `subset` | the tool value applies over part of the regulatory domain |
| `derived` | computed from, not equal to |
| `selects` | the value determines **which** regulatory case applies |

**A non-`identical` relationship must carry a `caveats` string** — enforced by the
validator, not merely encouraged. Such a mapping is claiming the two quantities differ;
unexplained, it is worse than no mapping at all.

## `bounds` and `bounds_basis`

Canonical validity bounds, distinct from any one tool's search range. `bounds_basis` is
required alongside them because a bound with no stated authority gets enforced as though
it had one:

- `regulatory` — the rule states it.
- `mathematical` — outside this range a governing expression is singular or undefined.
- `conceptual` — a sanity range carrying no authority. **Report it; do not reject on it.**
  Rejecting a valid unusual design is the failure mode this whole corpus exists to avoid.

## `implementations`

Where the quantity appears in real tools — descriptive, not normative. `status` records
what each tool did to it: `exact`, `renamed`, `collapsed` (one identifier standing for
several parameters), `conflated` (used where a different parameter belongs), or `absent`.

These are claims about other repositories, and claims rot.
[`tools/check_consumers.py`](../tools/check_consumers.py) locates each project via
[`tools/consumers.yaml`](../tools/consumers.yaml), re-reads its own source read-only, and
fails if a recorded bound has moved or an identifier has vanished. A divergence cannot be
quietly fixed or quietly introduced without this repo noticing.

## `kind: note`

An entry that is not a quantity a tool holds — a recorded consequence of modelling, kept
next to the parameter it concerns. Exempt from implementation-coverage checks, since there
is nothing for a tool to declare.

---

# Unit registry

[`unit.schema.json`](unit.schema.json) — one record per unit, in [`units/`](../units/),
enforced by the same validator and shipped as [`dist/units.json`](../dist/units.json) with its
own `content_sha256`, so a consumer pinning `constraints.json` is not disturbed by a new unit.

A unit is looked up by its QUDT IRI. `symbol` is the corpus's readable form. `ucum` is the unit
as a [UCUM](https://ucum.org/ucum) code, and it is **the spelling a consumer writes**: `m`, `kg`,
`m2`, `kg/m3`, `m/s`, `Pa`, `N`, `1`. UCUM is the one public grammar for units that both a parser
and a person can read; it gives division its own operator (§7), and its own table of example
terms lists `kg/m3`. No two units share a symbol or a code.

QUDT records a UCUM code too, and for three units spells it the other way UCUM allows:
`kg.m-3`, `m.s-1`, `m.s-2`. Those are equal terms, and unnatural ones. Where QUDT's spelling
differs it is kept as `ucum_qudt`, so a consumer holding it can find the unit; it is never the
code the corpus writes. QUDT records no code for the unit one, which UCUM writes `1` (§8).

`dimension` is the SI Brochure's dimensional product over its seven base quantities, in its
order: `T L M I Theta N J`. QUDT marks plane angle and the unit one with its own `D1`; the
Brochure gives both all zeros, and that is what is recorded. **Dimension does not tell an angle
from a ratio, or a torque from an energy.** `quantity_kinds` does, and the validator holds every
parameter to it: the parameter's `quantity_kind` must be one its unit measures.

`to_coherent_si` is present exactly when `si_coherent` is false. `factor` is a decimal
**string**, so no reader rounds it on the way in. `exact: true` means the string is the value.
Where the exact value is not a finite decimal (`pi/180`, `1852/3600`, a quotient),
`expression` holds it, `factor` is the shortest decimal that reads back as the nearest double,
and the validator evaluates the one against the other. An expression is decimals, `* / ^` and
`pi`, and nothing else.

[`tools/test_validate_units.py`](../tools/test_validate_units.py) breaks a copy of the corpus
one way at a time and requires the validator to refuse each.

---

# Vocabulary registry

[`vocabulary.schema.json`](vocabulary.schema.json) — closed sets of named alternatives, in
[`vocabularies/`](../vocabularies/), enforced by the same validator and shipped as
[`dist/vocabularies.json`](../dist/vocabularies.json) with its own digest.

A parameter says how much. A vocabulary says **which**: `wing-position` is `high-wing`,
`midwing`, `low-wing` or `parasol`. Tools hold these as enums and invent the words; here each
value carries a definition read from a source, and a consumer writes the value's id verbatim.
Vocabulary ids share the corpus's one namespace with constraints and parameters. A value's id
is unique within its vocabulary, and no alias may answer to two values.

## `admits`

The reason the layer is more than a glossary. A value lists the parameters that **exist only
under it**. `deadrise-auxiliary-float` is admitted by the two stabilizing-float values of
`lateral-stabilization-on-water` and by neither hull-borne one: on a flying boat stabilized by
sponsons there is no auxiliary float for the angle to be of. The rule for a consumer: a
parameter named by any value of a vocabulary may be held only when the chosen value names it;
a parameter no value names is not that vocabulary's business. Every `admits` must resolve to a
parameter, so a rename cannot leave one dangling.

## `exhaustive`

False unless the source says these are all there are. It is the vocabulary's counterpart of
`bounds_basis: conceptual`: **a design outside the list is reported, not rejected.** A
propeller both ahead of and behind the wing has no word in `propeller-position`, and is not
thereby wrong.

[`tools/test_validate_vocabularies.py`](../tools/test_validate_vocabularies.py) breaks a copy of
the corpus one way at a time and requires the validator to refuse each.

---

# Source registry

[`source.schema.json`](source.schema.json) — one record per regulatory **section**, in
[`sources/`](../sources/), enforced by the same validator.

Sixty-seven entries cite eighteen sections. Edition metadata carried on each entry would
be duplicated roughly fivefold and would drift apart the first time one copy was updated
and another was not, so it is normalised here instead. `tools/validate.py` joins the two:
every entry citing a section must declare the same `edition` as the registry record, so a
partially re-verified section cannot pass unnoticed.

## Why a digest

A constant is not a fact. It is a fact as of an issue date.

§ 25.535(d) specified a side load coefficient of `3.25 tan β` from 1964 until 2022, when
Amdt. 25-148 corrected it to `0.25` — a thirteenfold change, inside a rule described as
fixing typographical errors. The same amendment changed § 25.525(b) from citing
§ 25.533(b) to citing § 25.533(c), moving which pressure case governs a distributed load.
Neither announced itself.

So each record stores `text_sha256`, a digest of the section text with markup stripped and
whitespace collapsed. [`tools/check_editions.py`](../tools/check_editions.py) re-fetches
and compares. **The digest is the only one of its three checks that catches a correction
which never touched the amendment citation line** — which is the class of change that hid
the § 25.535(d) error for fifty-eight years.

`text_chars` sits beside it so a mismatch can be read at a glance: a one-character
correction and a wholesale restatement are both digest changes, and the length
distinguishes them.

## `effective_from` versus `edition`

`edition` is the eCFR issue this repo read. `effective_from` is the date the text became
law. They answer different questions, and the second is the one certification cares about
— an aircraft is certified to Part 25 *as amended through* a stated amendment level.

## Horizons

eCFR's own version history begins **2016-12-30**; everything before is one baseline
snapshot. The bracketed Federal Register citation line has no such limit — it reaches back
to original adoption — which is why `amendment_history` stores it verbatim rather than
reconstructing it from the versions API. A section with `amendment_history: null` has not
been amended since the part was adopted.

---

# Figure registry

[`figure.schema.json`](figure.schema.json) — one record per raster image the regulation
publishes in place of text, in [`sources/figures/`](../sources/figures/).

The equations of §§ 25.527, 25.531, 25.533 and 25.535 are all published as images: the
paragraph says *"computed as follows:"*, renders a PNG, and then defines the variables.

**Appendix B is the extreme case.** Its entire text content is twenty-one characters —
the words "Appendix B to Part 25". Everything else in it is three images. That is why the
versioner's `appendix=` endpoint looked like it was returning an empty document: it was
not failing, there is genuinely nothing to return. Appendix B has no record in
`sources/sections/` for the same reason, and its verification rests entirely on the image
digests here.

`sha256` is over the image **bytes** as fetched. That is only meaningful because the
server was checked, against repeated fetches, to send a byte-stable file with an ETag
rather than re-rendering per request — a digest over a re-encoded image would be noise.

## What the image digest catches that nothing else does

A figure redrawn, replaced, or re-rendered while the regulatory text stands untouched. A
breakpoint moving on figure 2 would change every K1 and K2 in the corpus and would not
alter one character of § 25.527, so no text digest, citation line or amendment date would
notice.

`tools/validate.py` enforces the join in both directions: every `EC…` identifier appearing
anywhere in an entry must have a registry record, and every record's `read_by` must name
entries that exist. An image read but not digested is an unverifiable source; a digested
image nothing reads is dead weight.

`last_modified` is the HTTP header, and is evidence about the *file* rather than the
regulation — when the image was last written to that server, not when the figure was
adopted.

## `history` on a constraint entry

Where a *value* changed, the entry itself carries a `history` block with the superseded
value, the amendment that ended it, and what the change means for anything built on the old
text. [`tools/as_of.py`](../tools/as_of.py) reads those to answer "what did this require on
date D", and reports sections it *cannot* answer for rather than passing over them.

Reserve `history` for changes in the **regulation**. Changes to our own encoding belong in
git.
