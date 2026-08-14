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
