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

## Round 3 — the remaining water load sections, and a defect of our own (2026-08-13)

**Source:** eCFR versioner API, Title 14 issue **2026-07-07**, retrieved **2026-08-13**.
The `api/versioner/v1/full/{date}/title-14.xml?...&section=NN` endpoint used in Round 2
continues to work and was used throughout. Formula images were downloaded from
`img.federalregister.gov` and read directly, per the Round 2 process change.

Prompted by a cross-repository QA pass over `aerogit`, `flightforge` and `Loftline`.

### The defect: § 25.337(c)(1) encoded the opposite of its own quotation

`cfr-25.337-c1-negative-limit-to-vc` carried `operator: "<="` against `value: -1.0`,
while its `notes` field quoted the regulation — *"may not be less than −1.0"* — two lines
above. Those say opposite things, and the entry was marked `verified`.

Read as signed algebra, "not less than −1.0" is `n >= -1.0`, which would make the
**weaker** design (n = −0.5) compliant and reject the stronger one. That is plainly not
the rule's intent; the airplane must withstand a negative factor of at least 1.0 in
magnitude.

The bound is now stated **on the magnitude**, which is true under either reading and
cannot be inverted by a consumer's sign convention. A `verification.sign_convention`
field has been added to the schema and is **required** wherever the plain wording and the
engineering reading differ in sign or in magnitude-versus-signed form.

This is the second time a plausible-looking claim has survived into a release. Round 2
was a claim about a source that had not been read; this one is worse, because the source
*was* read and quoted correctly, and the machine-readable field next to the quotation
still contradicted it. Prose was doing the verification; nothing checked the field.

**Process change: the corpus is now executed, not just written.** `tools/validate.py`
enforces the schema, id uniqueness, cross-reference integrity, and that every symbol in
an expression is declared. `tools/run_tests.py` evaluates every `worked` test case from
the corpus itself. Both run in CI. The first run of the validator found **11 findings
across 27 entries**, none of which a human reader had caught.

### What the new tooling found immediately

| Finding | Entries |
| --- | --- |
| `assertion`/`qualitative` entries whose substance lived only in `verification.notes`, with no `statement` | 2 |
| `cfr-25.527-a2` declared only `K1` and `r_x`, silently inheriting four symbols from `a1` | 1 |
| `n_min` and `n_neg` used in expressions but never declared as variables | 2 |
| Test inputs keyed `W_lb` against a declared symbol `W` — nothing could ever bind them | 5 cases |
| `notes_additional_bound`, an undeclared one-off key carrying the 2.33 step load floor — a load-bearing rule travelling as a comment, already implemented downstream | 1 |

### Sections read for the first time

All five previously-unread sections of §§ 25.523–25.537 are now encoded. **§ 25.531 was
read first because it was already a dangling reference:** the encoded
`cfr-25.525-d-aerodynamic-lift` carves out "the takeoff condition of § 25.531" as its one
exception, so the corpus was asserting an exception to a section it had never opened.

| Section | What it contains | Image |
| --- | --- | --- |
| **25.523** | Conditions met at *each* operating weight up to design landing weight; takeoff case uses design water takeoff weight | — |
| **25.529** | Load application points and directions; unsymmetrical split of 0.75 up and 0.25 tan β side | — |
| **25.531** | `n = C_TO·V_S1²/(tan^⅔β·W^⅓)`, `C_TO = 0.004`, wing lift assumed **zero** | `.038` |
| **25.535** | `L = C5·V_S0²·W^⅔/(tan^⅔β_S·(1+r_y²)^⅔)`, `C5 = 0.0053`, β_S floor 15°, immersed float components | `.042`, `.043` |
| **25.537** | One sentence: seawing loads must be based on test data | — |

§ 25.537 is encoded *because* it is empty: a seawing configuration has no default
analytical path in Subpart C, so a tool asked to size one must decline rather than fall
back on the hull formulas.

### § 25.533 was encoding constants without their formulas

The section carried `C3` and `C4` as bare values with no expression, while `flightforge`
implemented both formulas anyway. A constant without its formula is not an encoding of
the rule. Both are now encoded from the published images:

| Formula | Image | Result |
| --- | --- | --- |
| § 25.533(b)(2) flared chine | `.040` | `P_ch = C3 × K2·V_S1²/tan β` |
| § 25.533(c)(1) distributed | `.041` | `P = C4 × K2·V_S0²/tan β` |

**The distributed case takes V_S0, not V_S1.** Both the glossary and the image confirm
it: the local pressures of (b) are referred to the takeoff stalling speed, the
distributed pressures of (c) to the landing stalling speed. Two different speeds in
adjacent paragraphs of one section. `flightforge` had this right; the corpus had not
recorded it either way.

A useful cross-check on the flared reading: `C3/C2 = 0.7512`, so where β happens to equal
β_k the flared formula returns essentially the same `0.75 × P_k` the unflared case gives
directly. The two paths agree at the unflared limit.

### Corrections to eCFR's own rendering

- **§ 25.535(f)** — the XML prints both ρ and V as `ft.2`. This is a mangled superscript;
  dimensional analysis settles it, since `ρ g V` must yield lbf, so ρ is slug/ft³ and V is
  ft³. The corpus records the corrected units.
- **§ 25.533(c)(1)** — the XML duplicates the `VS0` glossary line and runs the β
  definition onto the end of the repeat. The image was used instead.

### Unresolved, and recorded as such

**§ 25.535(f) speed units.** This is the only water load formula in Subpart C written in
genuine physical quantities — it contains an explicit ρ and a dynamic-pressure form —
rather than being an empirical fit whose constants absorb the units. Every other
expression takes V_S0 or V_S1 in knots because the constant was fitted that way. Here the
dimensions must close on their own, and they only do so with the speed in ft/s. The
regulation's glossary nevertheless says knots, and the choice changes the answer by
1.688² = 2.85.

No primary source consulted resolves this. The test case is therefore marked `pending`,
not `worked`, and the entry states both candidate values.

### Consequence for the ecosystem

A parameter vocabulary (`parameters/`) now names the quantities the constraints consume,
because three consumers had independently invented three vocabularies for one hull:

- All three collapse the **two distinct deadrise angles** — β at the station and β_k at
  the keel — into a single `deadrise_deg`. AeroGit's facet documents its own loss in its
  description; nothing checked it, and nothing propagated it.
- **Loftline admits `deadrise_deg = 0.0` inclusive.** § 25.533 divides by tan β, so that
  is not a flat hull with a large pressure — it is undefined. AeroGit made the same bound
  exclusive for exactly this reason. Loftline sits upstream of the geometry, so the
  permissive bound is the one that decides what reaches the formulas, and Flightforge's
  `_tan_deg` floors the angle at 1° — a numerical guard doing a validation job.
- **"Forebody fraction" names two different things.** In Loftline and AeroGit it means the
  step station; in Flightforge it is a Parkinson spray correlation length, and its note
  says so. Those are genuinely different quantities. For Appendix B, L_f *is* the step
  station by definition, and substituting the other moves the K1/K2 discontinuity to a
  station the hull does not have.
- **The auxiliary float load path is encoded but unreachable.** § 25.535 is now fully
  encoded, and no consumer carries a float deadrise for it to act on.

`tools/check_consumers.py` re-reads each consumer's own source read-only and fails if a
recorded divergence goes stale in either direction.

## Open items

- [ ] Trace the empirical provenance of the Appendix B figure 2 breakpoints (1964 rulemaking, Doc. No. 5066; likely NACA tank data)
- [ ] Independent second reading of Appendix B figure 2 values
- [x] ~~§§ 25.523, 25.529, 25.531, 25.535, 25.537 not yet read~~ — all five read and encoded, Round 3
- [x] ~~§ 25.337(c) negative case has no worked test case~~ — now covered by magnitude-bound cases; a VC/VD pair from a real aircraft would still be better than the synthetic 300/400 KEAS pair
- [x] ~~Fresh water density in the 25.751 worked example is an engineering value~~ — split into `interp-25.751-required-float-volume` so it can no longer inherit a `verified` status by adjacency
- [ ] **§ 25.535(f) speed units unresolved** — glossary says knots, dimensional closure requires ft/s, factor of 2.85 between them. Needs a source that states it: Advisory Circular material, the 1964 rulemaking record, or ANC-3
- [ ] § 25.335 (design airspeeds) is referenced by 25.337(c) via VC and VD but is not yet read
- [ ] § 25.485 and the remaining ground load sections referenced by the upstreamed 25.473 file are not read
- [ ] ANC-3 alternate standard not yet located or assessed — now blocking two items rather than one
- [ ] CS-25 Appendix S (water scooping) — no primary text obtained; all secondary
- [ ] Extend `parameters/` scope beyond `geometry.` — the weights, speeds and inertia families reach Flightforge through seed_state and have no declared consumer mapping yet
- [ ] No consumer carries an auxiliary float deadrise, so the § 25.535 load path has no geometry source anywhere in the ecosystem
- [ ] AeroGit carries no chine flare, so the § 25.533(b)(1)-versus-(b)(2) selector is lost at the layer that versions the design
