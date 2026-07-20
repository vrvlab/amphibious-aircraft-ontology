# Appendix B

> **Correction (2026-07-20):** an earlier version of this file described Appendix B as
> an unsolved digitization problem and called it the project's hard blocker. That was
> wrong. The figures were not examined before the claim was published. They have now
> been read, and none of them require digitization. See
> [`../docs/verification-log.md`](../docs/verification-log.md) for the full retraction.

14 CFR Part 25 Appendix B contains three figures referenced throughout the water-load sections. All three have been read from the images the regulation publishes, and all three are encoded in [`../constraints/appendix-b-hull-station-weighing-factors.yaml`](../constraints/appendix-b-hull-station-weighing-factors.yaml).

## Figure 1 — Pictorial definition of angles, dimensions, and directions

`EC28SE91.055`. A **nomenclature diagram**, not a chart. It fixes the body-axis convention (X, Y, Z), the forebody/afterbody split at the main step, and the deadrise geometry.

It supplies **no numeric values**. `β` is a geometric property of the hull being designed — a design input. Figure 1 defines how to *measure* it, not what it is.

Key content: for an unflared bottom `β = β_k` (constant keel to chine). For a flared bottom the two differ, with `β_k` at the keel being the steeper.

## Figure 2 — Hull station weighing factor

`EC28SE91.056`. **Piecewise-linear with every breakpoint value printed on the figure.** Encoded exactly; no curve fitting, no interpolation error, no uncertainty.

**`K₁` (vertical loads), § 25.527(a)(2)**

| Station | Value |
| --- | --- |
| bow | 1.5 |
| forward of step | 1.0 |
| aft of step | 0.375 |
| stern | 1.0 |

**`K₂` (bottom pressures), § 25.533**

| Station | Value |
| --- | --- |
| bow | 2.0 |
| half forebody (`L_f/2`) | 0.75 |
| forward of step | 1.0 |
| aft of step | 0.5 |
| stern | 1.0 |

Note `K₂` is **not monotonic** over the forebody — it falls to a minimum at `L_f/2` and recovers toward the step. Treating it as a single ramp from bow to step is a material error.

## Figure 3 — Transverse pressure distributions

`EC28SE91.057`. A **schematic** of four distribution shapes: local pressure (unflared and flared), and distributed pressure (symmetrical and unsymmetrical). Every value it depicts — `0.75 P_k`, `P/2` — is already stated in the text of § 25.533. It confirms the textual reading and adds nothing independent.

## What we still want

Digitization is not needed. Independent verification and provenance still are:

1. **Independent reading of Figure 2.** These values were read from a raster by one person. A second reading is cheap and worth having. If you disagree with any breakpoint, open a correction issue.
2. **Provenance of the numbers.** Where do 1.5, 0.375, 2.0, 0.75, 0.5 come from? They date to the 1964 rulemaking (Doc. No. 5066) and are almost certainly fitted to NACA seaplane tank data — plausibly the Langley tank series. **Finding the original test data behind the curve would be a genuinely significant contribution**, both to this project and to the field.
3. **ANC-3.** § 25.521(b) names it as an alternate standard. We have not located a copy.

Item 2 is the interesting one. Recovering the empirical basis of a regulation still in force would let downstream tools reason about *why* the factors are what they are, rather than just applying them.
