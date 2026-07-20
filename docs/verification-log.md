# Verification Log

Every constant in `constraints/` was checked against primary regulatory text rather than transcribed from a secondary summary. This log records what was checked, what held up, and what did not.

**Source:** eCFR enhanced renderer API, Title 14 issue **2026-07-07**. Retrieved **2026-07-20**.
**Method:** eCFR blocks direct page scraping; text was pulled via `api/ecfr.gov/api/renderer/v1/content/enhanced/...`. Formula images were downloaded from `img.federalregister.gov` and read directly, since the regulation publishes equations as rasters.

## Round 1 — seeded from an AI-generated research report

The project began from an LLM-authored research report on amphibious ontology design. That report was used **only as a structural guide**. Every quantitative claim in it was independently checked.

### Confirmed correct

| Claim | Section | Result |
| --- | --- | --- |
| `C₁ = 0.012` | 25.527(b)(2) | ✅ exact |
| minimum step load factor `2.33` | 25.527(b)(2) | ✅ exact |
| `C₂ = 0.00213` | 25.533(b)(1) | ✅ exact |
| chine pressure `= 0.75 × P_k` | 25.533(b)(1) | ✅ exact |
| twin-float `K₁` reducible to `0.8` | 25.527(c) | ✅ exact |
| main float buoyancy `80%` in excess | 25.751(a) | ✅ exact |
| `≥ 5` watertight compartments per float | 25.751(b) | ✅ exact |
| aerodynamic lift `= ⅔ W` during impact | 25.525(d) | ✅ exact |
| twin float = equivalent hull at ½ weight | 25.525(c) | ✅ exact |

Formula structure for `n_w` (both step and bow/stern cases) and `P_k` was confirmed by reading the published equation images `EC28SE91.036`, `.037`, and `.039`. The report's algebra was correct.

### Omissions found

| Missing | Section |
| --- | --- |
| **`C₃ = 0.0016`** — chine pressure for a *flared* bottom | 25.533(b)(2) |
| **`C₄ = 0.078 · C₁`** — distributed pressures for frames, keel, chine structure | 25.533(c)(1) |
| The `§ 25.531` exception to the ⅔ aerodynamic lift assumption | 25.525(d) |
| `β_k` is deadrise **at the keel** specifically, not at an arbitrary station | 25.533(b)(1) |

The `(b)` local-pressure case and the `(c)` distributed-pressure case are distinct design conditions — plating and stringers vs. frames, keel and chine structure. Treating § 25.533 as a single pressure rule loses this.

### Misstatements found

| Asserted | Actual |
| --- | --- |
| "zero-capsizing probability" | 25.755(a) requires stability "great enough to **minimize the probability** of capsizing." Not zero — that is not an achievable criterion. |
| `GM > 0` as the Part 25 criterion | Not in the regulation. A naval-architecture proxy. Recorded in `constraints/` as `status: interpretation` so it cannot be mistaken for rule text. |
| float buoyancy vs "maximum **design** weight" | 25.751(a) says "maximum weight." |
| `n_w ≥ 2.33` as a blanket floor | The floor is on `C₁` being sufficient to achieve a minimum **step** load factor of 2.33. Narrower than usually stated. |

### The structural finding

**Subpart C water loads cannot be extracted from regulatory text by NLP.**

1. The equations in §§ 25.527 and 25.533 are **PNG images**, not text. A model reading the CFR sees `computed as follows:` followed by a variable glossary and no equation.
2. `K₁`, `K₂`, and `β` resolve to **printed graphs** in Appendix B figures 1–3. No closed form exists in the regulation.
3. § 25.521(b) makes the entire §§ 25.523–25.537 method **defeasible** — it applies "unless a more rational analysis of the water loads is made, or the standards in ANC-3 are used."

Point 3 is the one most often lost. Encoding these as mandatory constraints would cause a reasoner to reject designs that are legitimately substantiated by higher-fidelity analysis. Every derived constraint carries an `applicability` block for this reason.

Points 1 and 2 mean any pipeline whose first step is "NLP-mine the regulatory text" will silently produce an incomplete model. Digitizing Appendix B is a prerequisite, not a refinement. See [`../appendix-b/`](../appendix-b/).

## Open items

- [ ] Digitize Appendix B figures 1–3
- [ ] §§ 25.523, 25.529, 25.531, 25.535, 25.537 not yet read
- [ ] ANC-3 alternate standard not yet located or assessed
- [ ] CS-25 Appendix S (water scooping) — no primary text obtained; all secondary
- [ ] Fresh water density used in the 25.751 worked example (62.4 lb/ft³) is an engineering value, not regulatory
