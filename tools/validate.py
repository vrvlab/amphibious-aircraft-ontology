#!/usr/bin/env python3
"""Validate the constraint and parameter corpus.

Checks the things that rot silently:

  - every file parses
  - every parameter -> constraint mapping resolves to a real constraint id
  - relationships come from the closed vocabulary
  - a non-identical relationship carries a caveat explaining why
  - units are QUDT IRIs from the known set, and the symbol agrees
  - verification status comes from the closed vocabulary
  - ids are unique across the corpus

Usage:
    python tools/validate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml required:  pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent

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
}
QUANTITY_KINDS = {
    "quantitykind:Length",
    "quantitykind:Angle",
    "quantitykind:Area",
    "quantitykind:Volume",
    "quantitykind:DimensionlessRatio",
}

errors: list[str] = []
warnings: list[str] = []


def load(path: Path):
    try:
        return yaml.safe_load(path.read_text()) or []
    except yaml.YAMLError as e:
        errors.append(f"{path.name}: does not parse -- {e}")
        return []


def main() -> int:
    constraint_ids: set[str] = set()
    seen: dict[str, str] = {}

    for path in sorted((ROOT / "constraints").glob("*.yaml")):
        for entry in load(path):
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

    param_count = 0
    for path in sorted((ROOT / "parameters").glob("*.yaml")):
        for entry in load(path):
            pid = entry.get("id")
            if not pid:
                errors.append(f"{path.name}: entry with no id")
                continue
            if pid in seen:
                errors.append(f"duplicate id {pid!r} in {path.name} and {seen[pid]}")
            seen[pid] = path.name
            param_count += 1

            q = entry.get("quantity") or {}
            unit, sym, qk = q.get("unit"), q.get("symbol"), q.get("quantity_kind")
            if unit not in UNIT_SYMBOL:
                errors.append(f"{pid}: unit {unit!r} not a known QUDT IRI")
            elif sym != UNIT_SYMBOL[unit]:
                errors.append(f"{pid}: unit {unit} implies symbol {UNIT_SYMBOL[unit]!r}, got {sym!r}")
            if qk not in QUANTITY_KINDS:
                errors.append(f"{pid}: quantity_kind {qk!r} not a known QUDT IRI")

            st = (entry.get("verification") or {}).get("status")
            if st not in STATUSES:
                errors.append(f"{pid}: verification.status {st!r} not in {sorted(STATUSES)}")

            for m in entry.get("regulatory_mapping") or []:
                cid = m.get("constraint")
                rel = m.get("relationship")
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

            # A parameter with no regulatory mapping is legal but worth noting:
            # the point of this layer is the join.
            if not entry.get("regulatory_mapping"):
                warnings.append(f"{pid}: no regulatory_mapping")

    print(f"constraints: {len(constraint_ids)}   parameters: {param_count}")
    for w in warnings:
        print(f"  warning: {w}")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
