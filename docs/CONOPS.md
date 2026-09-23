# Concept of operations

**Status: proposed (#17).** This document says what the ontology is for, who uses it, how an
entry comes to exist, and what an edition promises the tools that pin it. Where it describes
something the corpus does not do yet, it says so and names the issue that would build it.

## What it is for

The ontology has two jobs, and they are different jobs.

1. **Say what the regulation requires, with a citation.** The constraint kernel: § 25.527's
   step load, § 25.533's bottom pressures, § 25.751's float volume, executed and tested. The
   meaning of every constant belongs to the regulation. The ontology's work is to read it
   correctly and to notice when it changes.
2. **Say exactly what a design quantity means.** The parameter layer, the units and the
   vocabularies: what *hull length* measures, from where to where; what *high wing* includes.
   The goal is a shared understanding, so that two tools, or two engineers, holding a number
   under the same name hold the same quantity. The meaning belongs to the ontology.

The first job depends on the second: a rule reads its symbols through definitions. The second
does not depend on finding the definition in someone else's document.

## Who uses it

| Who | Does what | Needs from the ontology |
|---|---|---|
| **A design tool** | Vendors a tagged edition, names its quantities by the ontology's ids, evaluates the constraints against them, and reports what it could not do | Ids that do not move, a meaning that does not change under an id, one file per layer in `dist/` |
| **A contributor**, human or agent | Adds or corrects an entry by pull request | A clear test for when an entry is done, and a point at which to stop looking |
| **A reviewer** | Decides whether an entry is merged | The same test, so review is a check, not a second search |
| **A reader** | Wants to know what the regulation says, or what a word means | Citations for the rules; definitions that stand on their own |

## What it is not

- **Not certification advice.** A `verified` rule means the source was read carefully, not
  that anything is airworthiness-approved.
- **Not a library of the historical literature.** Old reports are cited where they state a
  definition or disagree with one. They are not collected for their own sake, and an entry
  never waits on one.
- **Not a design tool's schema.** A tool's search range is the tool's. The ontology holds
  validity limits (a hull length is greater than zero) and says which kind a bound is.
- **Not a solver.** It bounds solvers.

## Two kinds of entry

| | **Rule** | **Definition** |
|---|---|---|
| Where it lives | `constraints/` | `parameters/`, `vocabularies/` |
| Whose meaning | The regulation's | The ontology's |
| Done when | It matches the primary text, with the edition read | It is exact enough to measure: two people measuring the same drawing get the same number |
| Sources | Required. The regulation itself, read, not a summary of it | Optional. Cited where they agree or where they differ, never required |
| Statuses | `verified`, `partial`, `unverified`, `interpretation`, as now | `defined` when the ontology sets the meaning (proposed, #18); `verified` when a primary source states it exactly as the entry does |

Units sit with the rules: a metre is the SI Brochure's, not ours, and its source is easy to
read. They keep the statuses they have.

### What makes a definition exact enough

A definition says, where it applies:

- **what** is measured, and what is excluded (the tail extension is not hull length);
- **from where to where**: the datum and the end point;
- **along what**: the direction or line, when more than one would give a different number;
- **in what condition**, when the value depends on one (a draft carries its load);
- **what reads it**: the rule or method that needs the quantity, since that decides which
  convention is useful.

A definition that leaves any of these open, where the answer would change the number, is not
done. That gap is closed by **choosing** and saying why, not by searching.

### Sources for a definition

A source is cited to say one of two things:

- **agrees**: the source defines the quantity the same way. Useful, because a reader can check
  it, and the entry may then be `verified`.
- **differs**: the source uses the same name or symbol for something else. More useful, because
  it stops a consumer from reading an old value as ours. `hull-length` already does this for
  Locke's *L*, whose afterbody ends at a second step.

Silence is not a finding. When the sources read do not say along which line hull length is
measured, the entry picks one, says why, and notes the sources' silence. It does not become an
open item waiting for a document that may not exist.

## How far a search goes

For a **rule**, the search goes as far as the primary text. That is the job, and the § 25.535(d)
correction, 3.25 tan β to 0.25 after fifty-eight years, is why.

For a **definition**, one bounded pass:

1. The sources already cited in the corpus.
2. One search of the public archives (NTRS, govinfo, the Federal Register).
3. What is found and legible in that pass is read and cited as agrees or differs.

Then the definition is written. The pass does not extend to library requests, to inferring a
statement from a drawing, or to a scan too damaged to read. A later reader who finds a source
that differs adds it as a `differs` citation; if it shows the ontology's definition is the
less useful one, that is a new id (below), not a silent change.

## Editions and what they promise

A consumer vendors one tag and pins it, and never transcribes a constant into its own source
(README, *Using it*). What changes between the editions it pins is governed by this promise.
**Proposed (#18); the corpus has made no such promise before v1.0 until now.**

| Change | Allowed in | Consumer effect |
|---|---|---|
| A new id | any edition | none until the consumer uses it |
| Wording made clearer, no measured value changes | any edition | none |
| A rule follows an amendment of the regulation | any edition, with the edition read | intended: the consumer re-evaluates |
| A definition's meaning changes | never under the same id: a new id, the old one marked superseded | the consumer moves when it chooses |
| A parameter's unit changes | never | — |
| An id removed | a major edition, after one edition in which it was superseded | the consumer had an edition's notice |

Each edition says what it added, superseded and changed, in a changelog a consumer can read
before re-pinning (proposed, #18).

## Where the work comes from

The ontology does not depend on any consumer to build or validate. It depends on one to be
worth anything. **A design tool that uses it in earnest is its discovery engine**: sizing a
hull against § 25.533 is where a definition turns out to leave the line of measurement open,
where two tools' numbers under one name disagree, where a unit is missing, or where a rule
cannot be evaluated as written. Without that use the corpus is a list of terms, and nothing
says which of its gaps matter.

So the work is led by use, not by the literature:

- **The queue is here.** A consumer that finds a word, a unit or a rule missing, unclear,
  uncertain or wrong opens an issue in this repository, naming what reads it and what it could
  not do. A consumer does not define the word itself; it may hold a marked candidate of its own
  until an edition holds the word.
- **What a consumer is blocked on comes first.** Research items stay open and welcome:
  Appendix B's provenance, amendments before 1997, the EASA side, ANC-3. None of them blocks a
  definition.
- **A human merges.** Every pull request is reviewed against this document and
  [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## What exists and what is proposed

| | Exists | Proposed |
|---|---|---|
| Rules primary-sourced, executed, edition-tracked | yes | — |
| Definitions with measurement conventions | yes, 28 parameters and 3 vocabularies, filed `verified`, `partial` or `interpretation` | the `defined` status (#18) |
| A bounded search for a definition | no | this document |
| The edition promise and a changelog | no | #18 |
| `CONTRIBUTING.md` written for both kinds of entry | no | #18 |
