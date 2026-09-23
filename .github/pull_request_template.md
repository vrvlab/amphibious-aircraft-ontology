## What this changes

<!-- Brief description. -->

## Source

<!--
For any change to constraints/, cite the primary source and the edition date you read.
Regulations change; an undated citation is not reproducible.
-->

- Section:
- URL:
- Edition / issue date read:

## Checklist

- [ ] Every rule traces to a primary source, **or** is labelled `unverified` / `interpretation`
- [ ] Every definition is exact enough to measure; where no source read states it, it is `defined` with a `rationale`, and `checked_against` records the one search that was made
- [ ] No id removed, repurposed or given a new unit (`python3 tools/changelog.py --promise`); a new meaning is a new id with `superseded_by` on the old
- [ ] Units declared on every variable (or `dimensionless`)
- [ ] `applicability` block present if the constraint is conditional (most of Subpart C is, via § 25.521(b))
- [ ] Worked test case added where the constraint is evaluable
- [ ] YAML parses

<!--
Downgrading something from `verified` to `interpretation` because you checked and found
it was an inference is a valuable contribution. Say so plainly in the description.
-->
