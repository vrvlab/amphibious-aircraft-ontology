# Appendix B — the open problem

**This directory is deliberately empty. Filling it is the highest-value contribution anyone can make to this project right now.**

## The problem

14 CFR Part 25 Appendix B contains three figures that the water-load regulations depend on:

| Figure | Supplies | Used by |
| --- | --- | --- |
| **Figure 1** | Angle of dead rise `β`, `β_k` | §§ 25.527(a), 25.533(b), 25.533(c) |
| **Figure 2** | Hull station weighing factors `K₁`, `K₂` | §§ 25.527(a)(2), 25.533(b), 25.533(c) |
| **Figure 3** | Pressure distribution keel → chine | § 25.533(b), (c) |

These are **printed curves**. The regulation provides no closed form, no tabulated values, and no parametric fit. Every water-load calculation in Part 25 bottoms out in reading a graph.

## Why this blocks everything

`constraints/` currently marks several entries `status: partial` rather than `verified`. Not because the text is uncertain — it is verified — but because the constraint **cannot be evaluated end to end** without `K₁`, `K₂`, and `β`. The formulas are known and the coefficients are not.

Until Appendix B is digitized:

- no constraint that depends on `K₁`/`K₂` can be executed
- no worked test case for §§ 25.527(a)(2) or 25.533 can be produced
- any "AI-assisted Part 25 compliance" claim is resting on values nobody can trace

This is also why the popular approach — NLP-mine the regulatory text into an ontology — cannot work for this subpart. There is nothing in the text to mine.

## What a good contribution looks like

For each figure:

1. **Provenance** — source of the scan (Federal Register image ID, GPO PDF, or ANC-3 if the curve originates there), and the edition
2. **Extracted points** — digitized `(x, y)` pairs in CSV, with the extraction method stated (manual, WebPlotDigitizer, etc.)
3. **A fit** — parametric approximation with reported max and RMS error against the extracted points
4. **Uncertainty** — honest error bars. A curve read off a 1964 raster at 300 dpi has real uncertainty and it should be published, not hidden.
5. **Validation** — ideally, agreement with an independently published seaplane sizing example

**Digitized values are approximations of a legal document. They must never be presented as authoritative.** Anything landed here will carry that caveat prominently.

## Prior art wanted

If Appendix B curves have already been digitized and published — in a textbook, a NACA/NASA TN, an ANC-3 reproduction, a thesis, or someone's old FORTRAN — that reference is as valuable as new digitization work. Open an issue.

Historic seaplane structural design literature (Mayo, Locke, NACA wartime reports) may contain the original empirical data these curves were fit to. Finding the underlying source would be better than digitizing the picture of it.

## How to help

Open an issue titled `appendix-b: figure N` describing what you have or intend to do, so effort is not duplicated. Partial work is welcome — a careful digitization of one figure is a complete contribution.
