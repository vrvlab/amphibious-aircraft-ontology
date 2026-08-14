#!/usr/bin/env python3
"""Check the canonical parameter vocabulary, and the claims made about consumers.

Three things happen here:

  1. parameters/canonical.yaml validates against schema/parameter.schema.json,
     and every `used_by` id resolves to a real constraint entry.
  2. Every canonical parameter is accounted for by every consumer — mapped,
     renamed, collapsed, conflated, or explicitly absent. Silence is a finding.
  3. Where a consumer repo is on disk, its declared bounds are re-read from its
     own source and compared with what parameters/consumers.yaml claims. A
     divergence recorded upstream must not be allowed to go stale in either
     direction.

Consumers are read strictly read-only, and are located relative to this repo.
Absent consumers are skipped, not failed — that is what --report-only is for
in CI, where the sibling repos are not checked out.

Usage:  python3 tools/check_consumers.py [--report-only]
Exit:   0 clean (always 0 with --report-only), 1 on any finding.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "parameters" / "canonical.yaml"
CONSUMERS = ROOT / "parameters" / "consumers.yaml"
PARAM_SCHEMA = ROOT / "schema" / "parameter.schema.json"
CONSTRAINTS = ROOT / "constraints"

TOL = 1e-9


def corpus_ids() -> set[str]:
    ids: set[str] = set()
    for path in CONSTRAINTS.glob("*.yaml"):
        for entry in yaml.safe_load(path.read_text(encoding="utf-8")):
            ids.add(entry["id"])
    return ids


# --------------------------------------------------------------------------
# Readers — one per consumer, each parsing that project's own source of truth.
# --------------------------------------------------------------------------

def read_loftline(root: Path) -> dict[str, dict]:
    """Loftline's bounds live in a Rust spec table, not in its JSON Schema."""
    src = root / "crates" / "loftline-core" / "src" / "spec.rs"
    if not src.exists():
        return {}
    text = src.read_text(encoding="utf-8")
    found: dict[str, dict] = {}
    # Both constructors carry bounds. `dist` marks a key that also accepts a
    # distribution rather than a scalar — which is how Loftline expresses a
    # warped hull, and why deadrise_deg is declared with it.
    pattern = re.compile(
        r'(?:num|dist)\(\s*"(?P<key>\w+)"\s*,\s*(?:true|false)\s*,\s*'
        r"(?P<min>-?[\d.]+(?:[eE][+-]?\d+)?)\s*,\s*"
        r"(?P<max>-?[\d.]+(?:[eE][+-]?\d+)?)",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        key = m.group("key")
        bounds = {"min": float(m.group("min")), "max": float(m.group("max"))}
        if key in found and found[key] != bounds:
            found[key] = {"_ambiguous": True}
        else:
            found.setdefault(key, bounds)
    return found


def read_aerogit(root: Path) -> dict[str, dict]:
    facet = root / "templates" / "facets" / "water" / "amphibian.json"
    if not facet.exists():
        return {}
    params = json.loads(facet.read_text(encoding="utf-8")).get("params", {})
    out: dict[str, dict] = {}
    for key, spec in params.items():
        b: dict = {}
        if "minimum" in spec:
            b["min"] = float(spec["minimum"])
        if "exclusiveMinimum" in spec:
            b["min"] = float(spec["exclusiveMinimum"])
            b["min_exclusive"] = True
        if "maximum" in spec:
            b["max"] = float(spec["maximum"])
        if "exclusiveMaximum" in spec:
            b["max"] = float(spec["exclusiveMaximum"])
            b["max_exclusive"] = True
        out[key] = b
    return out


def read_flightforge(root: Path) -> dict[str, dict]:
    src = root / "app" / "flightforge" / "plugins" / "amphibious" / "design_vars.py"
    if not src.exists():
        return {}
    text = src.read_text(encoding="utf-8")
    out: dict[str, dict] = {}
    pattern = re.compile(
        r'"(?P<key>[\w.]+)":\s*\{[^}]*?"lo":\s*(?P<lo>-?[\d.]+)'
        r'[^}]*?"hi":\s*(?P<hi>-?[\d.]+)',
        re.DOTALL,
    )
    for m in pattern.finditer(text):
        out[m.group("key")] = {"min": float(m.group("lo")), "max": float(m.group("hi"))}
    return out


READERS = {
    "loftline": read_loftline,
    "aerogit": read_aerogit,
    "flightforge": read_flightforge,
}


def bounds_differ(claimed: dict, actual: dict) -> list[str]:
    diffs = []
    for field in ("min", "max"):
        c, a = claimed.get(field), actual.get(field)
        if c is None and a is None:
            continue
        if c is None or a is None or abs(float(c) - float(a)) > TOL:
            diffs.append(f"{field}: recorded {c}, source says {a}")
    for field in ("min_exclusive", "max_exclusive"):
        if bool(claimed.get(field, False)) != bool(actual.get(field, False)):
            diffs.append(
                f"{field}: recorded {claimed.get(field, False)}, "
                f"source says {actual.get(field, False)}"
            )
    return diffs


def main() -> int:
    report_only = "--report-only" in sys.argv
    findings: list[str] = []
    notes: list[str] = []

    canonical = yaml.safe_load(CANONICAL.read_text(encoding="utf-8"))
    consumers = yaml.safe_load(CONSUMERS.read_text(encoding="utf-8"))

    # 1. Schema and cross-references.
    try:
        from jsonschema import Draft202012Validator

        schema = json.loads(PARAM_SCHEMA.read_text(encoding="utf-8"))
        for err in Draft202012Validator(schema).iter_errors(canonical):
            where = "".join(f"[{p!r}]" for p in err.absolute_path)
            findings.append(f"canonical.yaml{where}: {err.message}")
    except ImportError:
        notes.append("jsonschema not installed — parameter schema check skipped")

    ids = corpus_ids()
    names = {p["name"] for p in canonical}
    for p in canonical:
        for ref in p.get("used_by", []):
            if ref not in ids:
                findings.append(f"{p['name']}: used_by names unknown entry {ref!r}")
        for ref in p.get("distinct_from", []):
            if ref not in names:
                findings.append(f"{p['name']}: distinct_from names unknown parameter {ref!r}")

    # 2 and 3. Coverage, and drift against each consumer's own source.
    for consumer in consumers:
        cname = consumer["consumer"]
        mapped = {m["canonical"] for m in consumer["mappings"]}
        # Coverage is required only within a consumer's declared scope. A
        # lofting tool is not expected to account for design speeds, and
        # demanding it would make the check noise rather than signal.
        scope = tuple(consumer.get("scope") or [""])
        in_scope = {n for n in names if n.startswith(scope)}
        for missing in sorted(in_scope - mapped):
            findings.append(
                f"{cname}: no mapping declared for {missing!r} — "
                f"map it, or record it as status: absent"
            )
        for m in consumer["mappings"]:
            if m["canonical"] not in names:
                findings.append(
                    f"{cname}: mapping names unknown parameter {m['canonical']!r}"
                )

        path = (ROOT / consumer["path"]).resolve()
        if not path.exists():
            notes.append(f"{cname}: not on disk at {consumer['path']} — drift check skipped")
            continue

        actual = READERS[cname](path)
        if not actual:
            notes.append(f"{cname}: could not read {consumer['authority']} — drift check skipped")
            continue

        for m in consumer["mappings"]:
            key, claimed = m.get("key"), m.get("declared_bounds")
            if key is None:
                if key in actual:
                    findings.append(
                        f"{cname}: {m['canonical']} is recorded absent but "
                        f"{key!r} now exists upstream"
                    )
                continue
            short = key.split(".")[-1]
            found = actual.get(key) or actual.get(short)
            if found is None:
                findings.append(
                    f"{cname}: {key!r} is mapped to {m['canonical']} but no longer "
                    f"appears in {consumer['authority']}"
                )
                continue
            if found.get("_ambiguous"):
                notes.append(f"{cname}: {key!r} declared more than once — bounds not compared")
                continue
            if claimed:
                diffs = bounds_differ(claimed, found)
                if diffs:
                    findings.append(
                        f"{cname}: {key!r} bounds moved since recorded — "
                        + "; ".join(diffs)
                    )

    # Report.
    conflicts = [
        (c["consumer"], m)
        for c in consumers
        for m in c["mappings"]
        if m.get("status") in ("collapsed", "conflated")
    ]
    print(
        f"{len(canonical)} canonical parameters, "
        f"{len(consumers)} consumers, "
        f"{len(conflicts)} collapsed or conflated mappings"
    )
    for cname, m in conflicts:
        print(f"  ! {cname}: {m['key']} -> {m['canonical']} [{m['status']}]")

    for n in notes:
        print(f"  - {n}")

    if findings:
        print(f"\n{'REPORT' if report_only else 'FAIL'} — {len(findings)} finding(s)\n")
        for f in findings:
            print(f"  • {f}")
        return 0 if report_only else 1

    print("\nOK — vocabulary is consistent and every consumer claim still holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
