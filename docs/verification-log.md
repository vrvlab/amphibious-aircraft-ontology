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

**The equations in §§ 25.527 and 25.533 are published as PNG images, not text.** A model
reading the CFR sees `computed as follows:` followed by a variable glossary and no
equation. Confirming the formulas required reading `EC28SE91.036`, `.037` and `.039`
directly. This part holds.

**§ 25.521(b) makes the entire §§ 25.523–25.537 method defeasible** — it applies "unless a
more rational analysis of the water loads is made, or the standards in ANC-3 are used."
Encoding these as mandatory would cause a reasoner to reject designs legitimately
substantiated by higher-fidelity analysis. Every derived constraint carries an
`applicability` block for this reason.

## Round 2 — retraction of our own finding (2026-07-20)

**The first release of this repository claimed that Appendix B figures 1–3 were printed
empirical curves requiring digitization, that `K₁`, `K₂` and `β` were therefore
unavailable, and that digitizing them was a hard prerequisite for the project. This was
wrong.**

The claim was inferred from the phrase "in accordance with figure 2 of appendix B" in the
regulatory text. **The figures themselves were not examined before the claim was
published.** When they were read:

| Figure | What it actually is |
| --- | --- |
| **1** | Pictorial nomenclature — axes, sign conventions, deadrise geometry. No numeric values. `β` is a design input, not a chart value. |
| **2** | Piecewise-linear distribution with **every breakpoint value printed on the figure**. Encodable exactly. |
| **3** | Schematic of pressure distribution shapes. Introduces no values beyond the § 25.533 text. |

Consequences:

- Three constraints previously marked `partial` are now `verified`
- `K₁` and `K₂` are encoded exactly in `constraints/appendix-b-hull-station-weighing-factors.yaml`
- `appendix-b/` is no longer an open problem
- **The claim that Subpart C "cannot be NLP-extracted" was overstated.** The narrow version survives — the equations really are images — but the coefficients were available all along.

This is recorded rather than quietly edited because it is the exact failure this
repository exists to prevent: a plausible inference, confidently stated, published as a
verified finding. It occurred in the same commit that established the verification
standard. The lesson is the one already in `CONTRIBUTING.md` — plausible and correct are
different things — and it applies to maintainers first.

**Process change:** a claim about what a source contains now requires reading that source,
including when the source is an image. "The text references a figure" is not evidence
about the figure's contents.

## Round 2 — § 25.337 limit maneuvering load factors

**Source:** eCFR versioner API, full XML for Title 14 § 25.337, issue **2026-07-07**.
Retrieved **2026-08-04**. The enhanced renderer endpoint used in Round 1 now 302s to an
interstitial; `api/versioner/v1/full/{date}/title-14.xml?...&section=25.337` returns the
section text directly and was used instead.

Prompted by an audit of `vrvlab/flightforge`, which selects the limit load factor from a table
keyed on vehicle class where every civil entry is `2.5`.

### Confirmed correct

| Claim | Section | Result |
| --- | --- | --- |
| `n ≥ 2.1 + 24,000/(W + 10,000)` | 25.337(b) | ✅ exact |
| lower bound `2.5` | 25.337(b) | ✅ exact |
| upper relief `3.8` | 25.337(b) | ✅ exact |
| `W` is design maximum takeoff weight | 25.337(b) | ✅ explicit in text |

### Corrections to how this section was being characterised

The formula had been stated from recollection in `flightforge/docs/CONCEPTUAL_FIDELITY_PLAN.md`
and flagged there as unverified pending this check. The expression itself survived. Its framing
did not.

| Misstatement | What the text says |
| --- | --- |
| "n is a function of weight" | It is a **minimum**. "may not be less than" — a design may use more. Computing the expression yields the least acceptable value, not the value. |
| "capped at 3.8" | "**need not be greater than** 3.8" is relief from further increase, not a prohibition on exceeding it. |
| "floored at 2.5" | True as written in (b), but **25.337(d)** permits lower factors where design features make exceeding them impossible in flight. (b) is a default path, not an invariant. |
| — | **25.337(c) was omitted entirely.** The negative limit load factor — not less than −1.0 up to VC, varying linearly to zero at VD — is a distinct design condition. |
| — | **25.337(a)** requires pitching velocities appropriate to pull-up and steady turn maneuvers to be accounted for. Applying the (b) scalar alone does not evaluate this. |

The units are not stated in the section. The constants are dimensional, so the expression is
valid only with `W` in pounds; this is recorded as `interpretation` inside an otherwise
`verified` entry rather than being asserted as regulatory.

### Consequence for the tool that prompted this

A load factor of 2.5 is correct only above 50 000 lb, where the expression falls to the floor.
Below it the table under-predicts, and the shortfall grows as weight falls — 2.90 at 20 000 lb,
3.19 at 12 000 lb. The omission of the negative case and of (a) means the section is not being
evaluated at all, only one paragraph of it approximated.

## Open items

- [ ] Trace the empirical provenance of the Appendix B figure 2 breakpoints (1964 rulemaking, Doc. No. 5066; likely NACA tank data)
- [ ] Independent second reading of Appendix B figure 2 values
- [ ] §§ 25.523, 25.529, 25.531, 25.535, 25.537 not yet read
- [ ] § 25.337(c) negative case is captured but has no worked test case — needs VC/VD from a real aircraft
- [ ] § 25.335 (design airspeeds) is referenced by 25.337(c) via VC and VD but is not yet read
- [ ] ANC-3 alternate standard not yet located or assessed
- [ ] CS-25 Appendix S (water scooping) — no primary text obtained; all secondary
- [ ] Fresh water density used in the 25.751 worked example (62.4 lb/ft³) is an engineering value, not regulatory
