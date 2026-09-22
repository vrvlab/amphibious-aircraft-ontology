#!/usr/bin/env python3
"""Check the `implementations` claims in parameters/ against the real sources.

Each parameter records where it appears in real tools, under what name, and
with what bounds. Those are claims about other repositories, and claims rot.
This re-reads each system's own source and fails if one has gone stale in
either direction — a divergence quietly fixed, or one quietly introduced.

A recorded range is keyed by its KIND — `validity`, `search` or `tested` — and
each kind is read from the source that declares it. A system may have more
than one: a tool can declare what it accepts in one place and a narrower
optimiser box in another. Comparing one kind against the other reports a
conflict that is not there, which is exactly what issue #8 was opened on.

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

RANGE_FIELDS = ("min", "max", "min_exclusive", "max_exclusive", "basis")


# --------------------------------------------------------------------------
# Readers — one per source, each parsing that project's own declaration.
# Every reader returns {key: range}, a range in the schema's own shape:
# `min`, `max`, `min_exclusive` / `max_exclusive` only where true, and `basis`
# only where the source states one.
# --------------------------------------------------------------------------

# Which end of a range each JSON Schema keyword bounds.
_END = {"minimum": "min", "exclusiveMinimum": "min", "maximum": "max", "exclusiveMaximum": "max"}


def _json_schema_range(spec: dict) -> dict:
    """A JSON Schema number node's bounds, as a range.

    `bounds_basis`, where a source carries it, labels each keyword in this
    corpus's vocabulary. It is read rather than dropped: a `conceptual` ceiling
    is reported, not refused, and a record that lost that would call a warning
    a rejection.
    """
    r: dict = {}
    if "minimum" in spec:
        r["min"] = float(spec["minimum"])
    if "exclusiveMinimum" in spec:
        r["min"] = float(spec["exclusiveMinimum"])
        r["min_exclusive"] = True
    if "maximum" in spec:
        r["max"] = float(spec["maximum"])
    if "exclusiveMaximum" in spec:
        r["max"] = float(spec["exclusiveMaximum"])
        r["max_exclusive"] = True
    basis = {_END[k]: v for k, v in (spec.get("bounds_basis") or {}).items() if k in _END}
    if basis:
        r["basis"] = basis
    return r


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
    return {key: _json_schema_range(spec) for key, spec in params.items()}


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


def fmt_range(r: dict) -> str:
    """Interval notation, so an exclusive end reads differently from an inclusive one."""
    lo = f"{'(' if r.get('min_exclusive') else '['}{r['min']}" if "min" in r else "(-inf"
    hi = f"{r['max']}{')' if r.get('max_exclusive') else ']'}" if "max" in r else "+inf)"
    return f"{lo}, {hi}"


def bounds_differ(claimed: dict, actual: dict) -> list[str]:
    """Field-by-field differences between a recorded range and a declared one.

    An end present on one side and open on the other is a difference, and so is
    an end that is exclusive on one side only: `(0, 45]` refuses a zero that
    `[0, 45]` admits, and for a deadrise that zero is a division by tan(0).
    """
    diffs = []
    for end in ("min", "max"):
        want, got = claimed.get(end), actual.get(end)
        if want is None and got is None:
            continue
        if want is None or got is None or abs(float(want) - float(got)) > TOL:
            diffs.append(f"{end}: recorded {want}, source says {got}")
            continue
        flag = f"{end}_exclusive"
        if bool(claimed.get(flag)) != bool(actual.get(flag)):
            diffs.append(
                f"{end}: recorded {'exclusive' if claimed.get(flag) else 'inclusive'}, "
                f"source says {'exclusive' if actual.get(flag) else 'inclusive'}"
            )
        want_basis = (claimed.get("basis") or {}).get(end)
        got_basis = (actual.get("basis") or {}).get(end)
        if want_basis != got_basis:
            diffs.append(f"{end}: recorded basis {want_basis}, source says {got_basis}")
    return diffs


def check_implementation(
    param: dict, impl: dict, sources: list[tuple[str, str, dict[str, dict]]]
) -> tuple[list[str], list[str]]:
    """Check one `implementations` entry against a system's readable sources.

    `sources` is one (kind, authority, declarations) triple per source the
    system has on disk. Returns (findings, notes).
    """
    pid, system = param["id"], impl["system"]
    findings: list[str] = []
    notes: list[str] = []

    identifier = impl.get("identifier")
    if identifier is None:
        # Recorded absent. If it has reappeared upstream, say so.
        for _kind, authority, declared in sources:
            reappeared = find_by_name(param, declared)
            if reappeared:
                findings.append(
                    f"{pid} -> {system}: recorded absent, but {reappeared!r} "
                    f"now appears in {authority} — record it"
                )
                break
        return findings, notes

    short = identifier.split(".")[-1]
    recorded = impl.get("bounds") or {}
    seen = False

    for kind, authority, declared in sources:
        # By membership, not truthiness: a key declared with no bounds is `{}`,
        # and it is present.
        found = declared[identifier] if identifier in declared else declared.get(short)
        claimed = recorded.get(kind)
        if found is None:
            # A search box need not cover every parameter; a validity table
            # need not either. Only a range recorded against it is a claim.
            if claimed is not None:
                findings.append(
                    f"{pid} -> {system}: {kind} range recorded, but {identifier!r} "
                    f"does not appear in {authority}"
                )
            continue
        seen = True
        if found.get("_ambiguous"):
            notes.append(f"{system}: {identifier!r} declared more than once — bounds not compared")
            continue
        declared_range = {k: v for k, v in found.items() if k in RANGE_FIELDS}
        if claimed is None:
            if declared_range:
                findings.append(
                    f"{pid} -> {system}: {authority} declares a {kind} range "
                    f"{fmt_range(declared_range)} for {identifier!r} that is not recorded"
                )
            continue
        diffs = bounds_differ(claimed, declared_range)
        if diffs:
            findings.append(
                f"{pid} -> {system}: {identifier!r} {kind} range moved since "
                f"recorded — " + "; ".join(diffs)
            )

    if sources and not seen:
        where = ", ".join(authority for _, authority, _ in sources)
        findings.append(f"{pid} -> {system}: {identifier!r} no longer appears in {where}")
    return findings, notes


def consumer_sources(consumer: dict) -> list[dict]:
    """A consumer's declared sources, one per kind of range it publishes."""
    return consumer.get("sources") or []


def main() -> int:
    report_only = "--report-only" in sys.argv
    findings: list[str] = []
    notes: list[str] = []

    registry = {c["system"]: c for c in yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))}
    params = load_parameters()

    # Cache each readable source's live declarations, per system.
    live: dict[str, list[tuple[str, str, dict[str, dict]]]] = {}
    for name, consumer in registry.items():
        sources = consumer_sources(consumer)
        if not sources:
            notes.append(f"{name}: no reader declared — claims are unverifiable, not checked")
            continue
        path = (ROOT / consumer["path"]).resolve()
        if not path.exists():
            notes.append(f"{name}: not on disk at {consumer['path']} — drift check skipped")
            continue
        for source in sources:
            found = READERS[source["reader"]](path, source["authority"])
            if not found:
                notes.append(
                    f"{name}: could not read {source['authority']} — "
                    f"{source['kind']} drift check skipped"
                )
                continue
            live.setdefault(name, []).append((source["kind"], source["authority"], found))

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

            if system not in live:
                continue
            f, n = check_implementation(param, impl, live[system])
            findings.extend(f)
            notes.extend(n)

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
    # The same ambiguity is met once per parameter that names the key.
    notes = list(dict.fromkeys(notes))

    readable = sum(len(s) for s in live.values())
    print(
        f"{len(params)} parameters, {len(registry)} systems, "
        f"{len(live)} readable through {readable} source(s), "
        f"{len(conflations)} collapsed or conflated mappings"
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
