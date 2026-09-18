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

## Round 4 — § 25.535 speed units resolved, and a fifty-eight-year error found (2026-08-14)

**Source:** eCFR versioner API, Title 14, issues **2022-01-01** and **2023-06-01**, diffed
against each other and against the **typeset printed CFR** (GPO, 14 CFR Ch. I, 1-1-11
edition, p. 418). The printed edition matters here: it is set from the authoritative text
rather than rendered from XML, so it settles questions eCFR's markup mangles.

Opened to close the § 25.535(f) speed-unit item. It closed that item and found something
larger on the way.

### § 25.535(d) was wrong in the regulation from 1964 until 2022

The section read **"a side component equal to 3.25 tan β"**. It now reads **0.25**.

`Amdt. 25-148` (87 FR 75710, 9 December 2022, corrected at 88 FR 2813, 18 January 2023)
changed it as part of a Miscellaneous Amendments rule addressing typographical and
editorial errors. The diff between the two eCFR issues shows the change and nothing else
of substance in the section.

**That is a thirteenfold reduction in the unsymmetrical step side load on an auxiliary
float.** On the wing-tip float used as this corpus's worked case, 1758.83 lb under the
rule in force against 22864.75 lb under the text that stood for fifty-eight years.

Anything built on a pre-2023 copy of Part 25 carries the larger figure — and the 2011
printed CFR, which is what a search engine is most likely to surface as a PDF, still shows
`3.25`. The sibling paragraph (e) had `0.25` throughout, as do § 25.529(b)(1) for hulls
and § 25.529(c) for twin floats, so `3.25` was always the odd one out.

This is the strongest argument this corpus has yet produced for its own `edition` field.
A constant is not a fact; it is a fact *as of an issue date*.

### A defect the 2022 pass did not fix

§ 25.535(d) takes 0.75 times "the load specified in paragraph (a)". Paragraph (a) is the
General paragraph and specifies no load at all — the step load is in (b). The corrections
pass fixed the coefficient in that sentence and left the dangling cross-reference beside
it. Read literally the vertical component of the condition is undefined.

`cfr-25.535-d-unsymmetrical-step-loading` binds it to the (b) step load, which is what (e)
does for the bow case and the only reading under which the paragraph operates at all. That
is recorded in the entry as an engineering reading, not as regulatory text.

### The § 25.535(f) speed units

**Established, and no longer inferred:** ρ is slugs/ft³ and V is ft³. The eCFR XML renders
both as `ft.2`; the typeset CFR shows the superscript the XML lost. Round 3 reached the
same conclusion by dimensional analysis alone. It is now read from the source, which is
what the Round 2 process change requires.

**Also established:** the section really does say **knots**, in both renderings. It is not
an eCFR artifact, and it survived a targeted FAA typo-correction pass over this very
section in 2022.

**Not established, and not establishable from the regulation:** which unit closes the
equation. The two readings differ by 1.68781² = 2.849.

The argument for ft/s is that § 25.535(f) is the *only* water-load expression in Subpart C
written in genuine physical quantities. Every other one — `cfr-25.527-a1`,
`cfr-25.533-b1-keel-pressure`, `cfr-25.535-b-step-load` — is an empirical fit whose
constant absorbs the units, which is why knots is unremarkable there. Here the form is
`C·(ρ/2)·area·speed²`, the textbook dynamic pressure, and C_x and C_y are called
*"coefficient of drag force"* and *"coefficient of side force"* — the language of
dimensionless coefficients. And the companion component in the same load set, `ρ g V`, is
exactly lbf in consistent units with no fitted constant at all. One load set cannot
coherently use consistent units for its vertical component and knots for its horizontal
ones.

The argument for knots is that the section says knots.

**Resolution.** The corpus does not pretend the regulation is consistent. It splits the
two claims:

- `cfr-25.535-f-immersed-drag-and-side` stays **verified** and records the expression and
  the stated unit exactly as published.
- `interp-25.535-f-speed-units` is a new **interpretation** entry carrying the ft/s
  reading, the arithmetic, and the reasoning above.

ft/s was chosen for two reasons in order: it is the only reading under which the
expression is the drag equation it visibly is, and it is the conservative one for a
strength requirement, yielding loads 2.849 times larger. Choosing the other way would be
choosing the unconservative reading of an ambiguous rule.

A certification programme must obtain FAA agreement rather than rely on this entry.
§ 25.521(b) makes the whole method defeasible in any case. **If the FAA ever states the
unit, this entry is retracted here rather than quietly edited.**

The corpus now has **no `pending` test cases**: 41 worked cases, all reproducing.

### What was tried and did not resolve it

| Source | Result |
| --- | --- |
| Part 29 water loads (§ 29.519) | Rotorcraft dropped the formula entirely in 1968 for a qualitative "fully immersed float" requirement. No units to compare. |
| Part 23 § 23.535 | Gone. Amdt. 23-64 replaced prescriptive Part 23 with performance-based rules; the versioner returns 404 at 2016. |
| MIL-A-8864 | *Airplane Strength and Rigidity, Water and Handling Loads for Seaplanes* — the likely engineering ancestor. Cancelled 1982, no accessible full text. |
| ANC-3 | Still not located. Now blocking three items. |
| Gudmundsson, *General Aviation Aircraft Design*, App. C3 | Publisher's copy decommissioned; no accessible text. |
| CS-25.535 | A search summary asserted EASA reads `0.25`, but no primary EASA text was obtained. **Not recorded as a finding** — a secondary claim about a harmonised text is exactly what this corpus does not accept. |

## Round 5 — the corpus learns to notice when the regulation moves (2026-08-14)

**Source:** eCFR versioner API (`/full/` for text, `/versions/` for amendment dates),
Title 14 Part 25; and the typeset printed CFR where the XML is unreliable.

Round 4 found that § 25.535(d) had been wrong in the regulation for fifty-eight years.
That raised a question Round 4 did not answer: **how would we ever have known?** We found
it by accident, while chasing an unrelated units question. Nothing in the corpus, and
nothing in the FAA's publication of the correction, would have told us.

This round makes that a machine's job.

### A second change from the same amendment, found by looking properly

Querying the eCFR versions API for every section the corpus cites showed that Amdt. 25-148
touched **two** of them, not one. § 25.525 had been amended on the same day and the corpus
had not noticed.

Diffing § 25.525 across the amendment:

> **(b)** … using pressures not less than those prescribed in § 25.533~~(b)~~ **(c)**.

That is not cosmetic. § 25.533(b) is the **local** pressure case, sizing plating and
stringers; § 25.533(c) is the **distributed** case, sizing frames, keel and chine.
Distributing a resultant water load over the bottom is a distributed-pressure problem, so
the correction moves the floor onto the right design case.

The corpus had already made exactly that distinction the headline note of
`cfr-25.533-c1-c4-value` — *"Distributed pressures are for design of the frames, keel and
chine structure — a different design case from the local pressures in (b) … Conflating the
two is a common error"* — without knowing the FAA had just corrected the regulation in the
same direction.

**§ 25.525(b) was missing from the corpus entirely.** It is now
`cfr-25.525-b-load-distribution-pressure-floor`, with the superseded reference in its
`history` block.

### `sources/` — one record per section

Sixty-seven entries cite eighteen sections. Edition metadata on each entry would be
duplicated fivefold and drift, so it is normalised into a registry carrying, per section:
the issue read, the date the current text took effect, the verbatim Federal Register
citation line, and **a digest of the section text**.

`tools/validate.py` joins the two, so an entry cannot claim an edition its section's record
disagrees with. Perturbing one registry edition raises the mismatch on all fifty-nine
entries citing those sections.

### `tools/check_editions.py` — drift detection against the regulation

`check_consumers.py` asks whether the consumers still match what this repo says about them.
This asks the harder question in the other direction. Three checks:

| Check | Catches |
| --- | --- |
| Citation line unchanged | A recorded amendment |
| Versions API reports no later amendment | An amendment not yet in the citation line |
| **Text digest unchanged** | Everything else — including a correction that never touched the citation line |

The third is the one that matters, and it is why the registry stores a digest at all.

**Tested against the real event.** Pointing the § 25.535 record at the 2022 issue — as if
we had verified against the pre-amendment text — fires all three checks independently:
digest `e8b39bc61d89e321` recorded against `79adb0d4393fa85c` live, 3530 chars against
3464, the citation line short by two amendments, and the versions API reporting
2022-12-09 and 2023-01-18. The tool would have caught the fifty-eight-year error on the
day it was corrected.

It runs weekly rather than on push, and opens an issue. An eCFR outage must not fail a
build that has nothing to do with it.

All eighteen sections currently verify clean against live eCFR.

### `tools/as_of.py` — what did it say then?

An aircraft is certified to Part 25 *as amended through a stated amendment level*, not to
whatever the section says today. A corpus that can only answer "what does it require now?"
cannot be used to review an in-service type.

Entries whose value changed carry a `history` block. Asked about 2015-06-01, the corpus
now reports both Amdt. 25-148 changes with their superseded values.

**Where it cannot answer, it says so.** Asked about 1995 it names five sections — 25.345,
25.349, 25.473, 25.479, 25.807 — amended since that date and whose earlier text nobody
here has characterised. Silence there would be worse than a gap report: it would read as
"unchanged".

### The horizon problem, recorded rather than hidden

eCFR's version history begins **2016-12-30**. Everything earlier is a single baseline
snapshot, so the versions API cannot see the 1964–2016 record at all. The bracketed
citation line can — it reaches back to original adoption — which is why
`amendment_history` stores it verbatim rather than reconstructing it.

This means the corpus's confidence is not uniform in time. Changes since 2017 are
detectable three ways. Changes between 1964 and 2016 are visible only as an amendment
*date* in the citation line, with no text to diff against. `as_of.py` reports those as
gaps for exactly that reason.

Closing them means reading the historical Federal Register issues named in each citation
line. That is now the largest open item in this repository, and § 25.807 — five amendments
between 1990 and 2004 — is the worst of it.

### Appendix B has no text at all

Round 5 left Appendix B without a source record, because the versioner's `appendix=`
parameter returned what looked like an empty document. It was not a broken endpoint.

Extracting Appendix B from the full Part 25 XML gives **twenty-one characters** of text:
the words "Appendix B to Part 25". Everything else in the appendix is three images. There
is nothing to digest because there is nothing there.

So all eleven published images the corpus reads from are now registered in
`sources/figures/` with a digest of their bytes — the eight formula rasters of §§ 25.527,
25.531, 25.533 and 25.535, and the three Appendix B figures. For the appendix figures this
is not a supplement to a text check. It is the only verification that exists.

The images were checked to be byte-stable before the digests were relied on: repeated
fetches return identical bytes, with an ETag and a `Last-Modified` of 2022-05-20. A digest
over a re-encoded image would have been noise.

**What this catches that nothing else can.** A figure redrawn while the regulatory text
stands untouched. A breakpoint moving on figure 2 would change every K1 and K2 in the
corpus and would not alter one character of § 25.527 — no text digest, citation line or
amendment date would see it. Given that this repository's Round 2 retraction was itself
about the contents of figure 2, that is not a hypothetical failure mode.

`tools/validate.py` now enforces the join both ways: every `EC…` identifier appearing in
an entry must have a registry record, and every record's `read_by` must resolve.

## Round 6 — the pre-2017 gap, and an error of ours it uncovered (2026-08-14)

**Source:** govinfo annual CFR granules, `CFR-1997-title14-vol1` and
`CFR-2016-title14-vol1`, XML, compared against each other and against current eCFR.

Round 5 recorded that eCFR's version history begins 2016-12-30 and that everything
earlier was visible only as a date in a citation line. That was true of *eCFR*. It is not
true of the record: **govinfo publishes annual CFR editions, and the earliest XML granule
for title 14 is 1997.** Diffing 1997 against 2016 closes twenty years of the gap
mechanically, in one consistent source.

The five sections whose citation lines show no amendment — 25.457, 25.521, 25.525(pre-2022),
25.537, 25.751, 25.755 — come out byte-identical across the window. That is the method
validating itself: a technique that reported spurious change on a section nobody amended
would not be worth running.

### An error of ours, found on the way

§ 25.807(g) was encoded with **every value doubled**.

The regulation prints: *"the maximum number of passenger seats permitted FOR EACH EXIT of
a specific type installed IN EACH SIDE of the fuselage is as follows: Type A 110, Type B
75, Type C 55, Type I 45, Type II 40, Type III 35, Type IV 9."*

The corpus carried 220, 150, 110, 90, 80, 70, 18 as `cfr-25.807-g1-seats-per-exit-pair`,
units "seats per pair" — and asserted in its own notes that *"halving a pair's allowance
to get a per-exit number is a reading the table does not support"*. That is exactly
backwards. Both the 1997 and 2016 editions print the per-exit values, independently
corroborating it.

**How it survived.** The entry was authored downstream in flightforge and upstreamed in
an earlier round. Upstreaming normalised its structure — the operator vocabulary, an
unquoted section number, a `status` field holding prose — and marked the result
`verified` without re-reading its numbers against primary source. **Structural
normalisation is not verification.** Marking it verified asserted a check that had not
happened.

Corrected to `cfr-25.807-g-seats-per-exit` with the printed values. The doubled figures
are a correct derivation for a pair of exits and are kept as
`interp-25.807-g-seats-per-exit-pair`, which also records that § 25.807(g)(1) through
(g)(9) further restrict the allowance in ways the doubling does not capture.

**Process change: upstreaming a file from a downstream repository does not inherit its
verification status.** A `verified` entry means someone read the primary source for that
entry. Adopting an entry means reading it again.

### § 25.479 gained a whole design case in 2001

The largest substantive finding. Amdt. 25-103 (66 FR 27394, 16 May 2001) **added the
lateral drift landing condition**. Before it, § 25.479 ran (a) level attitude, (b)
downwind landings, (c) spin-up/springback combinations, (d) tail-wheel attitude, (e)
nose-wheel attitudes — and stopped.

`cfr-25.479-d2i-drift-{vertical,drag,side}-component` and `cfr-25.479-d2ii-drift-deflections`
therefore have no predecessor: an airplane certified below Amdt. 25-103 was not required
to show the case at all. Their `history` blocks carry a null `superseded_value` and say so.

The same amendment moved the 25 percent aft drag from § 25.479(c)(2) to (d)(1), and moved
the 0.8 friction cap out of § 25.479 entirely into § 25.473(e).

### § 25.473 was restated, and its lift assumption narrowed

Also Amdt. 25-103. The 10 fps and 6 fps descent velocities are unchanged, but their
paragraphs moved from (a)(1)(ii) and (a)(1)(iii) to (a)(2) and (a)(3), and the section was
retitled from "Ground load conditions and assumptions" to "Landing load conditions and
assumptions".

Substantively: the lift assumption was unconditional and acted through the centre of
gravity. It is now granted *"unless the presence of systems or procedures significantly
affects the lift"*, with the centre-of-gravity clause dropped. A design with automatic
ground spoilers may claim less lift relief now than the pre-2001 rule allowed, which
raises gear and support loads.

### Everything else in the window

§§ 25.337, 25.523, 25.527, 25.529, 25.531, 25.533 and 25.535 differ between 1997 and 2016
only in typesetting: quotation marks around symbols removed, spacing around `=`
normalised, `Appendix` lowercased, a line-break hyphen in "Unsymmet-rical" closed up, and
in § 25.349 two OCR corrections ("reaching" → "reacting", "fores." → "forces."). **No
constant in any water-load section changed.** § 25.345 and § 25.807 changed in wording and
structure with no change to any encoded value.

### What is recorded, and what is still open

Every section record now carries `history_verified_from: 1997-01-01` and a
`history_method` stating how it was established. `tools/as_of.py` reports against that
horizon instead of guessing from citation dates: above it, an entry with no `history`
block is unchanged *because the comparison was made*; below it, the tool says the corpus
cannot speak.

Two limits, both stated in the tool's own output rather than left implicit:

1. **Endpoint comparison.** 1997 against 2016 detects net change across the window, not a
   value that changed and changed back inside it.
2. **1997 is a hard floor for this method.** govinfo publishes no title-14 granule for
   1996. Amdt. 25-23 (1970), 25-46 (1978) and 25-72 (1990) predate the Federal Register's
   own online archive as well, so those three need printed sources.

Fixing `as_of.py` also surfaced a latent bug: it still pointed at `sources/` after Round
5 moved the records into `sources/sections/`, so its registry loaded empty and it reported
full confidence for every date. It now fails loudly on an empty registry, because a
silently empty registry is worse than no tool.

## Round 7 — the conformance checker was not checking half of what it claimed (2026-08-14)

**Source:** the consuming repositories themselves, read through `tools/check_consumers.py`.

Two findings this corpus filed against AeroGit were fixed there — chine flare is now
carried, and the `conceptual` bounds distinction is now enforced rather than only stated.
Neither fix was noticed here. That is the interesting part.

### An `absent` claim was never verified

`tools/consumers.yaml` and the checker's own docstring both promise it fails when a claim
goes stale "in either direction — a divergence quietly fixed, or one quietly introduced."
Only the second direction was implemented:

```python
identifier = impl.get("identifier")
if identifier is None:
    # Recorded absent. If it has reappeared upstream, say so.
    continue
```

The comment states the intent and the `continue` skips it. So every `status: absent` entry
was unfalsifiable: nothing looked for the parameter reappearing. AeroGit added
`chine_flare_deg`, and the checker reported "every implementation claim still holds against
its source" — byte-identical output before and after.

This is the same failure this project exists to catch, turned on itself: a claim that reads
as checked, is not, and looks fine because nothing contradicts it. It was found by a
consumer running the checker after making a change it should have flagged, which is an
argument for consumers running it in their own CI rather than only this repository doing so.

The fix matches a null identifier against the parameter's `name` and `aliases`, plus the
consumer's key with a trailing unit token stripped — `chine_flare_deg` against `chine-flare`.
It is deliberately conservative and will miss a tool that invents a spelling this corpus
does not list. A looser substring rule would have fired on `L_a` throughout, and a checker
that cries wolf gets switched off. Where it misses, the remedy is to add the spelling to
`aliases`, which is where a tool author searching for their own name would land anyway.

### Three entries recorded against the wrong parameter

AeroGit's `L_forebody_fraction` was recorded as the regulatory forebody length. It is the
spray length; its `step_fraction` is the regulatory one. The mapping had been read from that
facet's description, which said "Forebody length as a fraction of hull length" — and the
description was simply wrong, as its authors have since agreed and corrected.

Worth recording as a limitation rather than a one-off: **a mapping read from prose is only as
good as the prose.** The checker verifies bounds, which are machine-readable, and cannot
verify identity, which is not. Both `forebody-length` and `spray-forebody-length` now carry
a note saying where their AeroGit entry came from.

The same pass corrected the note that two of three consumers carry both a step fraction and
a forebody fraction permitted to differ. It is three of three.
## Round 8 — the units, which had never been read against anything (2026-09-18)

**Sources:** *The International System of Units (SI)*, BIPM, 9th edition (2019), **V4.01, June
2026**, the PDF at bipm.org (sha256 `5442eea2…e02c` as fetched). *NIST Special Publication
811*, **2008 Edition**, the PDF at nvlpubs.nist.gov (sha256 `788dd8f0…482f`). QUDT, each unit's
record at `https://qudt.org/vocab/unit/<id>`, fetched 2026-09-18 as Turtle. *The Unified Code
for Units of Measure*, **Version 2.2, 2024-06-17**, https://ucum.org/ucum (sha256
`08584e17…4f71` as fetched).

Sent from the consumer side. AeroHydro Studio pins an edition of this corpus and takes its
vocabulary from it, and asked a plain question of `v0.3.0`: what is `unit:LB_F`? The corpus
could not say. The eleven units it knew were a dict in `tools/validate.py`, with the comment
"each verified to resolve at qudt.org". Nothing else about them was recorded, no consumer
could read them, and six of the eleven were used by no parameter, so nothing had ever checked
them against anything.

### What was read, and what it settled

| Claim | Read in | Finding |
|---|---|---|
| Seven base quantities, their units and dimension symbols | SI Brochure Tables 2 and 3 | As recorded. The order `T L M I Θ N J` is the Brochure's |
| newton `kg m s⁻²`, pascal `kg m⁻¹ s⁻²`, radian | Table 4 and note (b) | As recorded. The Brochure warns that `rad = m/m` "may be misleading since angle is not the same kind of quantity as other length ratios": the reason a unit carries `quantity_kinds` and not only a dimension |
| area, volume, speed, acceleration, density; newton metre | Tables 5 and 6 | As recorded. `m⁴` is tabulated nowhere; it stands on § 2.3.4, products of powers of base units |
| degree | Table 8 | `1° = (π/180) rad`. Not a finite decimal: `exact: false`, with the expression |
| knot | Table 8, note (k) | `(1852/3600) m/s`. **The Brochure gives the knot no symbol**; `kn` is this corpus's own and is recorded as such |
| foot, inch | SP 811 B.8 | `3.048 E−01` and `2.54 E−02`, both in bold, and "a factor in boldface is exact" (B.7). Boldface does not survive the PDF's text layer; it was read on the HTML edition of B.8 at nist.gov |
| pound-force | SP 811 B.8 and its footnote | The table prints the rounded `4.448 222`. The footnote gives "the exact conversion factor", `4.448 221 615 260 5`, as the exact pound (`0.453 592 37 kg`, its own footnote) times standard gravity (`9.806 65`, bold). Recorded exact, with the product as its expression, which the validator multiplies out |
| psi, cubic foot | SP 811 B.8, B.9 | Printed rounded. The exact values are this corpus's arithmetic on the exact foot, inch and pound-force, and say so |

Every QUDT IRI resolved. QUDT's multipliers agree with each factor here to the digits a double
carries; they were a cross-check and are not the authority for any of them.

### The code a consumer writes

The first draft of this registry copied QUDT's `qudt:ucumCode` verbatim and called it the UCUM
code: `kg.m-3`, `m.s-1`. The consumer's designer asked why units would be written so
unnaturally, and the answer was that they need not be. **QUDT's string had been taken for the
standard's.** Read, UCUM 2.2 says: §7, "all units can be combined in an algebraic term using
the operators for multiplication (period) and division (solidus)", evaluated left to right;
§9, an exponent "is written immediately behind the unit term"; §8, "a positive integer number
may appear in place of a simple unit symbol", which is how the unit one is written `1`. Its
Appendix D lists `kg/m3` by name, and its own table of derived units defines the newton as
`kg.m/s2` and the pascal as `N/m2`.

So `ucum` holds the natural term, and QUDT's spelling is kept as `ucum_qudt` for the three units
where it differs. Every customary atom the registry uses, `[ft_i]`, `[lbf_av]`, `[psi]`,
`[kn_i]`, and `deg` and `rad`, was found in the specification's tables.

### One disagreement, recorded rather than resolved

QUDT gives `unit:UNITLESS`, `unit:RAD` and `unit:DEG` the dimension vector `A0E0L0I0M0H0T0D1`:
its own marker, `D1`, for "dimensionless". The Brochure gives quantities with the unit one a
dimension whose exponents are all zero. The registry records the Brochure's, because it is the
primary source for the SI and QUDT is a projection of it. A consumer comparing against QUDT
vectors must know the two spell it differently.

### What the registry refuses that the dict did not

A parameter whose unit does not measure its kind; a factor that changes the dimension; a factor
to a unit that is itself not coherent; an "exact" factor that is not its expression; two units
with one symbol or one UCUM code; a QUDT spelling that is another unit's code. `tools/test_validate_units.py` breaks a copy of the corpus
each way and requires the refusal. Each rule was also removed in turn and its self-check seen
to go red.

## Open items

- [x] ~~Characterise pre-2017 amendments for §§ 25.345, 25.349, 25.473, 25.479, 25.807~~ — closed to 1997 by diffing govinfo annual CFR granules; substantive changes recorded in `history` blocks
- [ ] **Below 1997 nothing has been compared.** Amdt. 25-23 (1970), 25-46 (1978) and 25-72 (1990) predate both the govinfo CFR granules and the Federal Register online archive, so they need printed sources — a library, not an API
- [ ] The 1997-to-2016 comparison is endpoint-only. A value that changed and changed back inside the window would not be seen; closing that means walking the annual editions year by year
- [x] ~~Appendix B has no `sources/` record and no digest~~ — it has no text to digest: twenty-one characters, the rest images. All eleven published figures are now digested by their bytes in `sources/figures/`
- [ ] Trace the empirical provenance of the Appendix B figure 2 breakpoints (1964 rulemaking, Doc. No. 5066; likely NACA tank data)
- [ ] Independent second reading of Appendix B figure 2 values
- [x] ~~§§ 25.523, 25.529, 25.531, 25.535, 25.537 not yet read~~ — all five read and encoded, Round 3
- [x] ~~§ 25.337(c) negative case has no worked test case~~ — now covered by magnitude-bound cases; a VC/VD pair from a real aircraft would still be better than the synthetic 300/400 KEAS pair
- [x] ~~Fresh water density in the 25.751 worked example is an engineering value~~ — split into `interp-25.751-required-float-volume` so it can no longer inherit a `verified` status by adjacency
- [x] ~~§ 25.535(f) speed units unresolved~~ — resolved as far as the sources allow in Round 4. Recorded as `interp-25.535-f-speed-units`, not as regulatory fact. **Still worth an FAA query**; a statement of the intended unit would retire that entry
- [ ] Confirm whether CS-25.535 carries the FAA's 2022 correction of (d) from 3.25 to 0.25. If EASA has not picked it up, that is a live harmonisation gap worth reporting. Needs primary EASA text, not a search summary
- [ ] § 25.535(d) still takes 0.75 times "the load specified in paragraph (a)", which specifies no load. Worth an FAA query alongside the units question
- [ ] Locate MIL-A-8864 (cancelled 1982) — the probable engineering ancestor of §§ 25.527-25.535 and the most likely place the immersed-float units are stated explicitly
- [ ] § 25.335 (design airspeeds) is referenced by 25.337(c) via VC and VD but is not yet read
- [ ] § 25.485 and the remaining ground load sections referenced by the upstreamed 25.473 file are not read
- [ ] ANC-3 alternate standard not yet located or assessed — now blocking two items rather than one
- [ ] CS-25 Appendix S (water scooping) — no primary text obtained; all secondary
- [ ] Extend `parameters/` scope beyond `geometry.` — the weights, speeds and inertia families reach Flightforge through seed_state and have no declared consumer mapping yet
- [ ] No consumer carries an auxiliary float deadrise, so the § 25.535 load path has no geometry source anywhere in the ecosystem
- [x] ~~AeroGit carries no chine flare, so the § 25.533(b)(1)-versus-(b)(2) selector is lost at the layer that versions the design~~ — AeroGit now declares `chine_flare_deg` and aliases it to the key the amphibious plugin selects on. It passes the angle and does not choose the path itself, which is right: the choice belongs to whatever evaluates the pressures
- [ ] AeroGit carries no chine flare, so the § 25.533(b)(1)-versus-(b)(2) selector is lost at the layer that versions the design
- [ ] The weights are forces in `lbf`, as the regulation writes them. A consumer that is SI inside carries mass in `kg`, and nothing here yet says that the two relate by standard gravity, `9.806 65 m/s²` exactly. `unit:LB_F`'s record now holds the number; no parameter holds the statement
- [ ] `.github/workflows/verify.yml` does not run `tools/test_validate_units.py`. It runs `test_check_consumers.py` the same way; one more step would cover the unit rules. Staleness of `dist/units.json` is already caught, since the workflow now diffs all of `dist/`
