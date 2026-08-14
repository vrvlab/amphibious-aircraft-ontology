#!/usr/bin/env python3
"""Validate the constraint and parameter corpus.

Checks the things that rot silently:

  - every file parses, and every entry matches its JSON Schema
  - ids are unique across the WHOLE corpus -- constraints and parameters share
    one namespace, because a mapping cites them the same way
  - every parameter -> constraint mapping resolves to a real constraint id
  - relationships come from the closed vocabulary
  - a non-identical relationship carries a caveat explaining why
  - units are QUDT IRIs from the known set, and the symbol agrees
  - every cross-reference inside a constraint resolves
  - every symbol used in a formula expression is declared in that entry

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
CONSTRAINT_SCHEMA = ROOT / "schema" / "constraint.schema.json"
PARAMETER_SCHEMA = ROOT / "schema" / "parameter.schema.json"

RELATIONSHIPS = {"identical", "discretization", "subset", "derived", "selects"}
STATUSES = {"verified", "partial", "unverified", "interpretation"}

# QUDT IRIs in use. Each verified to resolve at qudt.org.
UNIT_SYMBOL = {
    "unit:M": "m",
    "unit:MilliM": "mm",
    "unit:DEG": "deg",
    "unit:M2": "m^2",
    "unit:M3": "m^3",
    "unit:UNITLESS": "1",
    "unit:LB_F": "lbf",
    "unit:KN": "kn",
    "unit:PSI": "psi",
    "unit:FT": "ft",
    "unit:FT3": "ft^3",
}
QUANTITY_KINDS = {
    "quantitykind:Length",
    "quantitykind:Angle",
    "quantitykind:Area",
    "quantitykind:Volume",
    "quantitykind:DimensionlessRatio",
    "quantitykind:Force",
    "quantitykind:Speed",
    "quantitykind:Pressure",
    "quantitykind:Mass",
}

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
            if unit not in UNIT_SYMBOL:
                errors.append(f"{pid}: unit {unit!r} not a known QUDT IRI")
            elif sym != UNIT_SYMBOL[unit]:
                errors.append(
                    f"{pid}: unit {unit} implies symbol {UNIT_SYMBOL[unit]!r}, got {sym!r}"
                )
            if qk not in QUANTITY_KINDS:
                errors.append(f"{pid}: quantity_kind {qk!r} not a known QUDT IRI")

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

    if not quiet:
        print(f"constraints: {len(constraint_ids)}   parameters: {len(parameter_ids)}")
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
