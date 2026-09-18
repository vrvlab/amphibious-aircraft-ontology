#!/usr/bin/env python3
"""Validate the constraint and parameter corpus.

Checks the things that rot silently:

  - every file parses, and every entry matches its JSON Schema
  - ids are unique across the WHOLE corpus -- constraints and parameters share
    one namespace, because a mapping cites them the same way
  - every parameter -> constraint mapping resolves to a real constraint id
  - relationships come from the closed vocabulary
  - a non-identical relationship carries a caveat explaining why
  - every unit a parameter names has a record in units/, the symbol agrees with
    it, and the parameter's quantity kind is one the unit measures
  - every unit that is not coherent SI converts to one that is, of the same
    dimension, and no two units share an id, a symbol or a UCUM code
  - every cross-reference inside a constraint resolves
  - every symbol used in a formula expression is declared in that entry
  - every section a constraint cites has a record in sources/sections/, and the
    entry's edition matches the registry's
  - every published figure a constraint reads from is registered in
    sources/figures/ with a digest, and every registered figure is read by
    something

The last two exist because entries do not inherit from their siblings:
cfr-25.527-a2 must be resolvable without knowing cfr-25.527-a1 exists, since a
consumer can pin either one alone.

Usage:  python3 tools/validate.py [--quiet]
Exit:   0 clean, 1 on any error. Warnings do not fail the build.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml required:  pip install pyyaml")

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.exit("jsonschema required:  pip install jsonschema")

ROOT = Path(__file__).resolve().parent.parent
CONSTRAINTS = ROOT / "constraints"
PARAMETERS = ROOT / "parameters"
SOURCES = ROOT / "sources" / "sections"
FIGURES = ROOT / "sources" / "figures"
CONSTRAINT_SCHEMA = ROOT / "schema" / "constraint.schema.json"
PARAMETER_SCHEMA = ROOT / "schema" / "parameter.schema.json"
SOURCE_SCHEMA = ROOT / "schema" / "source.schema.json"
FIGURE_SCHEMA = ROOT / "schema" / "figure.schema.json"
UNITS = ROOT / "units"
UNIT_SCHEMA = ROOT / "schema" / "unit.schema.json"

#: The FAA's image identifiers, wherever they appear in an entry. The corpus
#: cites them in verification notes as well as in formula.source_render, and an
#: image read but not digested is an unverifiable source.
_FIGURE_RE = re.compile(r"\bEC[0-9A-Z]+\.[0-9]+\b")

#: A constraint cites a paragraph ("25.535(d)"); the registry is keyed on the
#: section it belongs to. Entries whose section is an appendix have no registry
#: record, because the appendix is not retrievable from the versioner the way a
#: numbered section is — its figures were read from published images instead.
_SECTION_RE = re.compile(r"^(\d+\.\d+)")

RELATIONSHIPS = {"identical", "discretization", "subset", "derived", "selects"}
STATUSES = {"verified", "partial", "unverified", "interpretation"}

#: Tokens that appear in expressions but are operators, calls or literals
#: rather than declared quantities.
_NON_SYMBOLS = {
    "tan", "sin", "cos", "atan", "sqrt", "log", "exp", "abs", "min", "max",
    "for", "and", "or", "if", "else", "where", "Forebody", "Afterbody",
    "Forward", "Aft", "forebody", "afterbody",
}
_SYMBOL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

errors: list[str] = []
warnings: list[str] = []


def _isoify(obj):
    """YAML turns unquoted dates into date objects; JSON Schema wants strings."""
    if isinstance(obj, dict):
        return {k: _isoify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_isoify(v) for v in obj]
    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    return obj


def load(path: Path):
    try:
        return _isoify(yaml.safe_load(path.read_text(encoding="utf-8")) or [])
    except yaml.YAMLError as e:
        errors.append(f"{path.name}: does not parse -- {e}")
        return []


def _evaluate(expression: str):
    """A conversion factor's exact arithmetic: decimals, * / ^ and pi, nothing else.

    Decimals become Fractions so that 0.45359237*9.80665 is exact; pi makes the
    whole thing a float, because it has to.
    """
    import math
    from fractions import Fraction

    if not re.fullmatch(r"[0-9.*/^ pi]+", expression):
        raise ValueError("only decimals, * / ^ and pi")
    python = re.sub(r"[0-9]+(?:\.[0-9]+)?", lambda m: f"Fraction('{m.group(0)}')", expression)
    python = python.replace("^", "**").replace("pi", "math.pi")
    return eval(python, {"__builtins__": {}}, {"Fraction": Fraction, "math": math})  # noqa: S307


def check_symbols(entry: dict) -> list[str]:
    formula = entry.get("formula")
    if not formula:
        return []
    declared = {v["symbol"] for v in formula.get("variables", [])}
    used = {
        tok
        for tok in _SYMBOL_RE.findall(formula["expression"])
        if tok not in _NON_SYMBOLS and not tok.isdigit()
    }
    return [
        f"formula uses undeclared symbol {sym!r} "
        f"(declared: {', '.join(sorted(declared)) or 'none'})"
        for sym in sorted(used - declared)
    ]


def main() -> int:
    quiet = "--quiet" in sys.argv
    constraint_validator = Draft202012Validator(
        json.loads(CONSTRAINT_SCHEMA.read_text(encoding="utf-8"))
    )
    parameter_validator = Draft202012Validator(
        json.loads(PARAMETER_SCHEMA.read_text(encoding="utf-8"))
    )
    source_validator = Draft202012Validator(
        json.loads(SOURCE_SCHEMA.read_text(encoding="utf-8"))
    )
    figure_validator = Draft202012Validator(
        json.loads(FIGURE_SCHEMA.read_text(encoding="utf-8"))
    )

    # ---- unit registry ---------------------------------------------------
    # This table lived in this file, as a dict, until a consumer needed it: a
    # vocabulary that exists only inside the validator cannot be pinned.
    unit_validator = Draft202012Validator(
        json.loads(UNIT_SCHEMA.read_text(encoding="utf-8"))
    )
    units: dict[str, dict] = {}
    for path in sorted(UNITS.glob("*.yaml")):
        records = load(path)
        for err in unit_validator.iter_errors(records):
            where = "".join(f"[{p!r}]" for p in err.absolute_path)
            errors.append(f"{path.name}{where}: {err.message}")
        for rec in records:
            uid = rec.get("id")
            if uid in units:
                errors.append(f"{path.name}: duplicate unit record for {uid!r}")
            units[uid] = rec
    for field in ("symbol", "ucum"):
        owner: dict[str, str] = {}
        for uid, rec in units.items():
            word = rec.get(field)
            if word is None:
                continue
            if word in owner:
                errors.append(
                    f"{uid}: {field} {word!r} is already {owner[word]}'s -- "
                    f"a consumer that writes it could not say which unit it meant"
                )
            owner[word] = uid
    for uid, rec in units.items():
        conv = rec.get("to_coherent_si")
        if not conv:
            continue
        target = units.get(conv.get("unit"))
        if target is None:
            errors.append(f"{uid}: converts to unknown unit {conv.get('unit')!r}")
        elif not target.get("si_coherent"):
            errors.append(f"{uid}: converts to {conv['unit']}, which is not coherent SI")
        elif target.get("dimension") != rec.get("dimension"):
            errors.append(
                f"{uid}: converts to {conv['unit']}, whose dimension differs -- "
                f"a factor cannot turn one dimension into another"
            )
        if not conv.get("exact") and not (conv.get("expression") or "").strip():
            errors.append(
                f"{uid}: a factor that is not exact must carry the expression that is"
            )
        # The arithmetic is executed, like a worked test case: a factor beside an
        # expression it does not equal is two claims, and one of them is wrong.
        if (conv.get("expression") or "").strip():
            from fractions import Fraction

            try:
                value = _evaluate(conv["expression"])
            except Exception as e:  # noqa: BLE001
                errors.append(f"{uid}: expression {conv['expression']!r} does not evaluate -- {e}")
            else:
                factor = str(conv.get("factor"))
                if conv.get("exact"):
                    if not isinstance(value, Fraction) or value != Fraction(factor):
                        errors.append(
                            f"{uid}: factor {factor} is declared exact and is not "
                            f"{conv['expression']}"
                        )
                elif float(value) != float(factor):
                    errors.append(
                        f"{uid}: factor {factor} is not the nearest double to "
                        f"{conv['expression']} ({float(value)!r})"
                    )
    # A quantity kind is known when some unit measures it.
    quantity_kinds = {
        k for rec in units.values() for k in rec.get("quantity_kinds", [])
    }

    # ---- source registry -------------------------------------------------
    registry: dict[str, dict] = {}
    for path in sorted(SOURCES.glob("*.yaml")):
        records = load(path)
        for err in source_validator.iter_errors(records):
            where = "".join(f"[{p!r}]" for p in err.absolute_path)
            errors.append(f"{path.name}{where}: {err.message}")
        for rec in records:
            sec = rec.get("section")
            if sec in registry:
                errors.append(f"{path.name}: duplicate source record for {sec!r}")
            registry[sec] = rec

    # ---- figure registry -------------------------------------------------
    figures: dict[str, dict] = {}
    for path in sorted(FIGURES.glob("*.yaml")):
        records = load(path)
        for err in figure_validator.iter_errors(records):
            where = "".join(f"[{p!r}]" for p in err.absolute_path)
            errors.append(f"{path.name}{where}: {err.message}")
        for rec in records:
            fid = rec.get("id")
            if fid in figures:
                errors.append(f"{path.name}: duplicate figure record for {fid!r}")
            figures[fid] = rec

    constraint_ids: set[str] = set()
    parameter_ids: set[str] = set()
    seen: dict[str, str] = {}
    constraints: list[tuple[Path, list]] = []
    parameters: list[tuple[Path, list]] = []

    # ---- constraints -----------------------------------------------------
    for path in sorted(CONSTRAINTS.glob("*.yaml")):
        entries = load(path)
        constraints.append((path, entries))
        for err in constraint_validator.iter_errors(entries):
            where = "".join(f"[{p!r}]" for p in err.absolute_path)
            errors.append(f"{path.name}{where}: {err.message}")
        for entry in entries:
            cid = entry.get("id")
            if not cid:
                errors.append(f"{path.name}: entry with no id")
                continue
            if cid in seen:
                errors.append(f"duplicate id {cid!r} in {path.name} and {seen[cid]}")
            seen[cid] = path.name
            constraint_ids.add(cid)
            st = (entry.get("verification") or {}).get("status")
            if st not in STATUSES:
                errors.append(f"{cid}: verification.status {st!r} not in {sorted(STATUSES)}")

            # Join to the source registry. An entry that cites a section
            # nobody has registered has no recorded edition, no amendment
            # history and no drift tripwire — which is how a corpus ends up
            # quoting a superseded value without noticing.
            src = entry.get("source") or {}
            if src.get("authority") == "none":
                continue  # an interpretation with no regulatory basis
            m = _SECTION_RE.match(str(src.get("section", "")))
            if not m:
                continue  # appendix or non-numbered citation
            sec = m.group(1)
            if sec not in registry:
                errors.append(
                    f"{cid}: cites § {sec} but sources/ has no record for it"
                )
            elif str(src.get("edition")) != str(registry[sec].get("edition")):
                errors.append(
                    f"{cid}: edition {src.get('edition')} disagrees with the "
                    f"sources/ record for § {sec} ({registry[sec].get('edition')})"
                )

    # Cross-references inside constraints. Only tokens that look like corpus
    # ids are checked; "more rational analysis" is prose and is meant to be.
    ref_re = re.compile(r"\b((?:cfr|interp)-[A-Za-z0-9._-]+)")
    for path, entries in constraints:
        for entry in entries:
            for field in ("formula", "applicability"):
                for ref in ref_re.findall(json.dumps(entry.get(field, {}))):
                    ref = ref.rstrip(".,;:")
                    if ref not in constraint_ids:
                        errors.append(
                            f"{path.name}: {entry.get('id')} references "
                            f"unknown entry {ref!r}"
                        )
            errors.extend(
                f"{path.name}: {entry.get('id')}: {m}" for m in check_symbols(entry)
            )

    # ---- parameters ------------------------------------------------------
    for path in sorted(PARAMETERS.glob("*.yaml")):
        entries = load(path)
        parameters.append((path, entries))
        for err in parameter_validator.iter_errors(entries):
            where = "".join(f"[{p!r}]" for p in err.absolute_path)
            errors.append(f"{path.name}{where}: {err.message}")
        for entry in entries:
            pid = entry.get("id")
            if not pid:
                errors.append(f"{path.name}: entry with no id")
                continue
            if pid in seen:
                errors.append(f"duplicate id {pid!r} in {path.name} and {seen[pid]}")
            seen[pid] = path.name
            parameter_ids.add(pid)

    for path, entries in parameters:
        for entry in entries:
            pid = entry.get("id")
            q = entry.get("quantity") or {}
            unit, sym, qk = q.get("unit"), q.get("symbol"), q.get("quantity_kind")
            if unit not in units:
                errors.append(f"{pid}: unit {unit!r} has no record in units/")
            else:
                if sym != units[unit]["symbol"]:
                    errors.append(
                        f"{pid}: unit {unit} implies symbol "
                        f"{units[unit]['symbol']!r}, got {sym!r}"
                    )
                if qk in quantity_kinds and qk not in units[unit]["quantity_kinds"]:
                    errors.append(
                        f"{pid}: {unit} does not measure {qk} "
                        f"(it measures {', '.join(units[unit]['quantity_kinds'])})"
                    )
            if qk not in quantity_kinds:
                errors.append(f"{pid}: quantity_kind {qk!r} is measured by no unit in units/")

            st = (entry.get("verification") or {}).get("status")
            if st not in STATUSES:
                errors.append(f"{pid}: verification.status {st!r} not in {sorted(STATUSES)}")

            for m in entry.get("regulatory_mapping") or []:
                cid, rel = m.get("constraint"), m.get("relationship")
                if cid not in constraint_ids:
                    errors.append(f"{pid}: maps to unknown constraint {cid!r}")
                if rel not in RELATIONSHIPS:
                    errors.append(f"{pid}: relationship {rel!r} not in {sorted(RELATIONSHIPS)}")
                # A mapping that is not `identical` is making a claim about HOW
                # the two differ. Unexplained, it is worse than no mapping.
                if rel and rel != "identical" and not (m.get("caveats") or "").strip():
                    errors.append(
                        f"{pid} -> {cid}: relationship {rel!r} requires a caveat "
                        f"explaining how the quantities differ"
                    )

            # `distinct_from` names the parameters this one is routinely
            # confused with. A dangling one means a rename lost the warning.
            for other in entry.get("distinct_from") or []:
                if other not in parameter_ids:
                    errors.append(f"{pid}: distinct_from names unknown parameter {other!r}")

            # A parameter with no regulatory mapping is legal but worth noting:
            # the point of this layer is the join.
            if not entry.get("regulatory_mapping"):
                warnings.append(f"{pid}: no regulatory_mapping")

    # Every figure an entry reads from must be digested, and every digested
    # figure must be read by something that exists.
    for path, entries in constraints:
        for entry in entries:
            for fid in sorted(set(_FIGURE_RE.findall(json.dumps(entry)))):
                if fid not in figures:
                    errors.append(
                        f"{entry.get('id')}: reads figure {fid} but "
                        f"sources/figures/ has no record for it"
                    )
    for fid, rec in figures.items():
        for cid in rec.get("read_by", []):
            if cid not in constraint_ids:
                errors.append(f"figure {fid}: read_by names unknown entry {cid!r}")

    if not quiet:
        print(
            f"constraints: {len(constraint_ids)}   "
            f"parameters: {len(parameter_ids)}   "
            f"units: {len(units)}   "
            f"sections: {len(registry)}   "
            f"figures: {len(figures)}"
        )
    for w in warnings:
        print(f"  warning: {w}")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")
        return 1
    if not quiet:
        print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
