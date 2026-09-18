#!/usr/bin/env python3
"""Check the `implementations` claims in parameters/ against the real sources.

Each parameter records where it appears in real tools, under what name, and
with what bounds. Those are claims about other repositories, and claims rot.
This re-reads each system's own source and fails if one has gone stale in
either direction — a divergence quietly fixed, or one quietly introduced.

Also reports the standing conflations. A `collapsed` or `conflated` mapping is
not an error: it is a known simplification that someone decided to live with.
The failure mode this guards against is nobody knowing it is there.

Consumers are read strictly read-only and are located relative to this repo via
tools/consumers.yaml. A consumer that is not checked out is skipped, not failed
— that is what --report-only is for in CI, where the siblings are absent.

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
    sys.exit("pyyaml required:  pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ROOT / "parameters"
REGISTRY = ROOT / "tools" / "consumers.yaml"

TOL = 1e-9


# --------------------------------------------------------------------------
# Readers — one per system, each parsing that project's own source of truth.
# --------------------------------------------------------------------------

def loftline_spec_rs(root: Path, authority: str) -> dict[str, dict]:
    src = root / authority
    if not src.exists():
        return {}
    text = src.read_text(encoding="utf-8")
    found: dict[str, dict] = {}
    # Both constructors carry bounds. `dist` marks a key that also accepts a
    # distribution rather than a scalar.
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


def aerogit_facet_json(root: Path, authority: str) -> dict[str, dict]:
    facet = root / authority
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


def flightforge_design_vars_py(root: Path, authority: str) -> dict[str, dict]:
    src = root / authority
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
    "loftline_spec_rs": loftline_spec_rs,
    "aerogit_facet_json": aerogit_facet_json,
    "flightforge_design_vars_py": flightforge_design_vars_py,
}


def load_parameters() -> list[dict]:
    params: list[dict] = []
    for path in sorted(PARAMETERS.glob("*.yaml")):
        for entry in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            entry["_file"] = path.name
            params.append(entry)
    return params


# Unit tokens a consumer may append to a key. This schema forbids units in
# parameter names, so a consumer's `chine_flare_deg` and this corpus's
# `chine-flare` are the same quantity spelled to two different conventions.
# Stripping the suffix is what lets them be compared at all.
UNIT_SUFFIXES = (
    "deg", "degs", "degrees", "rad", "rads",
    "ft", "feet", "in", "inch", "inches", "m", "mm", "cm",
    "lb", "lbs", "kg", "kt", "kts", "psi", "pa",
)


def normalise(name: str) -> str:
    """Reduce a name to comparable letters: `L_forebody_fraction` -> `lforebodyfraction`."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def find_by_name(param: dict, actual: dict[str, dict]) -> str | None:
    """The consumer's key for this parameter, if it declares one under any known name.

    Used only for entries recorded `absent`, to catch a gap that has since been
    filled without the record being updated. Deliberately conservative: it
    matches a name exactly, or a name plus a trailing unit token, and nothing
    looser. A substring rule would fire on `L_a` inside half the corpus, and a
    checker that cries wolf gets switched off.

    So this is a floor, not a ceiling. It will miss a tool that adopts a name
    this parameter does not list — the fix for which is adding the spelling to
    `aliases`, where a tool author searching for it would land anyway.
    """
    candidates = {normalise(param["id"]), normalise(param["name"])}
    candidates.update(normalise(a) for a in param.get("aliases") or [])
    candidates.discard("")

    for key in actual:
        stem = normalise(key.split(".")[-1])
        forms = {stem}
        for suffix in UNIT_SUFFIXES:
            if stem.endswith(suffix) and len(stem) > len(suffix):
                forms.add(stem[: -len(suffix)])
        if forms & candidates:
            return key
    return None


def bounds_differ(claimed: list, actual: dict) -> list[str]:
    """`claimed` is the [min, max] pair recorded in an implementations block."""
    diffs = []
    for field, want in (("min", claimed[0]), ("max", claimed[1])):
        got = actual.get(field)
        if got is None or abs(float(want) - float(got)) > TOL:
            diffs.append(f"{field}: recorded {want}, source says {got}")
    return diffs


def main() -> int:
    report_only = "--report-only" in sys.argv
    findings: list[str] = []
    notes: list[str] = []

    registry = {c["system"]: c for c in yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))}
    params = load_parameters()

    # Cache each readable consumer's live declarations.
    live: dict[str, dict] = {}
    for name, consumer in registry.items():
        reader_name = consumer.get("reader")
        if not reader_name:
            notes.append(f"{name}: no reader declared — claims are unverifiable, not checked")
            continue
        path = (ROOT / consumer["path"]).resolve()
        if not path.exists():
            notes.append(f"{name}: not on disk at {consumer['path']} — drift check skipped")
            continue
        found = READERS[reader_name](path, consumer["authority"])
        if not found:
            notes.append(f"{name}: could not read {consumer['authority']} — drift check skipped")
            continue
        live[name] = found

    conflations: list[tuple[str, str, str, str]] = []
    scoped_misses: list[str] = []

    for param in params:
        pid = param["id"]
        impls = param.get("implementations") or []
        declared_systems = {i["system"] for i in impls}

        for impl in impls:
            system = impl["system"]
            if system not in registry:
                findings.append(
                    f"{pid}: implementation names system {system!r}, "
                    f"which is not in tools/consumers.yaml"
                )
                continue
            if impl.get("status") in ("collapsed", "conflated"):
                conflations.append((system, impl.get("identifier") or "-", pid, impl["status"]))

            actual = live.get(system)
            if actual is None:
                continue

            identifier = impl.get("identifier")
            if identifier is None:
                # Recorded absent. If it has reappeared upstream, say so.
                reappeared = find_by_name(param, actual)
                if reappeared:
                    findings.append(
                        f"{pid} -> {system}: recorded absent, but "
                        f"{reappeared!r} now appears in "
                        f"{registry[system]['authority']} — record it"
                    )
                continue
            short = identifier.split(".")[-1]
            found = actual.get(identifier) or actual.get(short)
            if found is None:
                findings.append(
                    f"{pid} -> {system}: {identifier!r} no longer appears in "
                    f"{registry[system]['authority']}"
                )
                continue
            if found.get("_ambiguous"):
                notes.append(
                    f"{system}: {identifier!r} declared more than once — bounds not compared"
                )
                continue
            if impl.get("bounds"):
                diffs = bounds_differ(impl["bounds"], found)
                if diffs:
                    findings.append(
                        f"{pid} -> {system}: {identifier!r} bounds moved since "
                        f"recorded — " + "; ".join(diffs)
                    )

        # Coverage: a system in scope for this parameter's tags must say
        # something about it, even if that something is "absent". Notes are
        # exempt — they are recorded consequences of modelling, not quantities
        # a tool holds, so there is nothing for one to declare.
        if param.get("kind") == "note":
            continue
        tags = set(param.get("tags") or [])
        for name, consumer in registry.items():
            scope = set(consumer.get("scope") or [])
            if scope & tags and name not in declared_systems:
                scoped_misses.append(
                    f"{pid}: {name} is in scope for tags {sorted(scope & tags)} "
                    f"but declares no implementation — map it, or record status: absent"
                )

    findings.extend(scoped_misses)

    print(
        f"{len(params)} parameters, {len(registry)} systems, "
        f"{len(live)} readable, {len(conflations)} collapsed or conflated mappings"
    )
    for system, ident, pid, status in sorted(conflations):
        print(f"  ! {system}: {ident} -> {pid} [{status}]")
    for n in notes:
        print(f"  - {n}")

    if findings:
        print(f"\n{'REPORT' if report_only else 'FAIL'} — {len(findings)} finding(s)\n")
        for f in findings:
            print(f"  • {f}")
        return 0 if report_only else 1

    print("\nOK — every implementation claim still holds against its source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
