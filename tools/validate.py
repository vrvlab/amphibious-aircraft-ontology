#!/usr/bin/env python3
"""Validate the constraint corpus against schema/constraint.schema.json.

Checks three things the schema alone cannot:

  * ids are unique across the whole corpus, not merely within a file
  * every cross-reference (resolves_to, superseded_by) names an entry that exists
  * every symbol used in a formula expression is declared in its variables list

Usage:  python3 tools/validate.py [--quiet]
Exit:   0 clean, 1 on any finding.
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
    sys.exit("PyYAML is required: pip install pyyaml")

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.exit("jsonschema is required: pip install jsonschema")

ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / "constraints"
SCHEMA = ROOT / "schema" / "constraint.schema.json"

#: Tokens that appear in expressions but are operators, calls or literals rather
#: than declared quantities.
_NON_SYMBOLS = {
    "tan", "sin", "cos", "atan", "sqrt", "log", "exp", "abs", "min", "max",
    "for", "and", "or", "if", "else", "where", "Forebody", "Afterbody",
    "Forward", "Aft", "forebody", "afterbody",
}

_SYMBOL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _isoify(obj):
    """YAML turns unquoted dates into date objects; JSON Schema wants strings."""
    if isinstance(obj, dict):
        return {k: _isoify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_isoify(v) for v in obj]
    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    return obj


def load_corpus() -> list[tuple[Path, list[dict]]]:
    out = []
    for path in sorted(CONSTRAINTS.glob("*.yaml")):
        data = _isoify(yaml.safe_load(path.read_text(encoding="utf-8")))
        if not isinstance(data, list):
            raise SystemExit(f"{path.name}: top level must be a list of entries")
        out.append((path, data))
    return out


def check_symbols(entry: dict) -> list[str]:
    """Every identifier in a formula expression must be a declared variable."""
    formula = entry.get("formula")
    if not formula:
        return []
    declared = {v["symbol"] for v in formula.get("variables", [])}
    # A declared symbol may legitimately appear with subscript-ish suffixes in
    # prose-formatted piecewise expressions; compare on the bare token.
    used = {
        tok
        for tok in _SYMBOL_RE.findall(formula["expression"])
        if tok not in _NON_SYMBOLS and not tok.isdigit()
    }
    missing = sorted(used - declared)
    return [
        f"formula uses undeclared symbol {sym!r} "
        f"(declared: {', '.join(sorted(declared)) or 'none'})"
        for sym in missing
    ]


def main() -> int:
    quiet = "--quiet" in sys.argv
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    corpus = load_corpus()
    findings: list[str] = []
    seen: dict[str, str] = {}
    all_ids: set[str] = set()
    entry_count = 0

    for path, entries in corpus:
        for err in validator.iter_errors(entries):
            where = "".join(f"[{p!r}]" for p in err.absolute_path)
            findings.append(f"{path.name}{where}: {err.message}")
        for entry in entries:
            entry_count += 1
            eid = entry.get("id")
            if not isinstance(eid, str):
                continue
            if eid in seen:
                findings.append(
                    f"{path.name}: duplicate id {eid!r} (also in {seen[eid]})"
                )
            seen[eid] = path.name
            all_ids.add(eid)

    # Cross-references resolve. Only tokens that look like corpus ids are
    # checked; "more rational analysis" is prose and is meant to be.
    ref_re = re.compile(r"\b((?:cfr|interp)-[A-Za-z0-9._-]+)")
    for path, entries in corpus:
        for entry in entries:
            for field in ("formula", "applicability"):
                blob = json.dumps(entry.get(field, {}))
                for ref in ref_re.findall(blob):
                    ref = ref.rstrip(".,;:")
                    if ref not in all_ids:
                        findings.append(
                            f"{path.name}: {entry.get('id')} references "
                            f"unknown entry {ref!r}"
                        )
            findings += [
                f"{path.name}: {entry.get('id')}: {m}" for m in check_symbols(entry)
            ]

    if findings:
        print(f"FAIL — {len(findings)} finding(s) across {entry_count} entries\n")
        for f in findings:
            print(f"  • {f}")
        return 1

    if not quiet:
        print(
            f"OK — {entry_count} entries in {len(corpus)} files "
            f"validate against {SCHEMA.name}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
