#!/usr/bin/env python3
"""Self-checks for the parts of check_consumers.py that are not obviously right.

Plain asserts and no test framework, so CI needs no dependency it does not
already install. Run it the same way as run_tests.py.

`find_by_name` is what makes a `status: absent` claim falsifiable. It went in
after that check was found to be missing entirely — the comment said "if it has
reappeared upstream, say so" and the code said `continue` — so the thing most
worth pinning is that it neither goes quiet again nor starts crying wolf.

`check_implementation` compares a recorded range only with a source of the same
kind. Issue #8 was opened on a search ceiling read as a validity limit, so the
kind cases below are the ones that stop that recurring.

Usage:  python3 tools/test_check_consumers.py
Exit:   0 all pass, 1 on any failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_consumers import (  # noqa: E402
    bounds_differ,
    check_implementation,
    find_by_name,
    fmt_range,
    normalise,
)

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "parameter.schema.json"

CHINE_FLARE = {
    "id": "chine-flare",
    "name": "Chine flare angle",
    "aliases": ["flare", "chine flare"],
}

AUX_FLOAT = {
    "id": "deadrise-auxiliary-float",
    "name": "Auxiliary float dead rise at three-quarters bow-to-step",
    "aliases": ["beta_S", "float deadrise", "tip float deadrise"],
}

AFTERBODY = {
    "id": "afterbody-length",
    "name": "Afterbody length, main step to stern post",
    "aliases": ["afterbody", "L_a"],
}

# AeroGit's water facet as it stands, which is what the reader returns.
AEROGIT = {
    "hull_length": {},
    "hull_beam": {},
    "hull_depth": {},
    "deadrise_deg": {},
    "chine_flare_deg": {},
    "step_fraction": {},
    "L_forebody_fraction": {},
    "water_loads_part": {},
}

CASES: list[tuple[str, dict, dict, str | None]] = [
    (
        "a unit suffix does not hide a match",
        CHINE_FLARE,
        AEROGIT,
        "chine_flare_deg",
    ),
    (
        "an absence that is still real stays unreported",
        AUX_FLOAT,
        AEROGIT,
        None,
    ),
    (
        "a two-letter alias does not match half the corpus",
        AFTERBODY,
        AEROGIT,
        None,
    ),
    (
        "a dotted consumer key matches on its last segment",
        CHINE_FLARE,
        {"geometry.hull.chine_flare_deg": {}},
        "geometry.hull.chine_flare_deg",
    ),
    (
        "an exact name match needs no suffix stripping",
        CHINE_FLARE,
        {"chine_flare": {}},
        "chine_flare",
    ),
    (
        "a bare unit token is not mistaken for a parameter",
        {"id": "m", "name": "m", "aliases": []},
        {"beam_m": {}},
        None,
    ),
    (
        "nothing declared means nothing found",
        CHINE_FLARE,
        {},
        None,
    ),
]


# A tool with two sources: validity from its published schema, and a
# narrower optimiser box that covers fewer keys.
TOOL_VALIDITY = (
    "validity",
    "tool.schema.json",
    {
        "chine_flare_deg": {"min": 0.0, "max": 45.0},
        "length": {"min": 0.0, "min_exclusive": True},
        # Dotted and bound-less: the case a truthiness lookup loses, since
        # `{}` is falsy and the bare `hull_id` is not declared at all.
        "geometry.hull.hull_id": {},
    },
)
TOOL_SEARCH = (
    "search",
    "search_box.py",
    {"geometry.hull.chine_flare_deg": {"min": 0.0, "max": 20.0}},
)
TOOL = [TOOL_VALIDITY, TOOL_SEARCH]

FLARE_IMPL = {"system": "tool", "identifier": "geometry.hull.chine_flare_deg"}

# (label, implementation bounds, identifier, sources, finding substrings expected)
KIND_CASES: list[tuple[str, dict | None, str, list, list[str]]] = [
    (
        "each kind recorded against its own source is clean",
        {"validity": {"min": 0.0, "max": 45.0}, "search": {"min": 0.0, "max": 20.0}},
        "geometry.hull.chine_flare_deg",
        TOOL,
        [],
    ),
    (
        "a search box is never compared with a validity limit",
        {"search": {"min": 0.0, "max": 20.0}},
        "geometry.hull.chine_flare_deg",
        TOOL,
        ["declares a validity range [0.0, 45.0]"],
    ),
    (
        "a search box recorded as validity is a moved range, not a pass",
        {"validity": {"min": 0.0, "max": 20.0}, "search": {"min": 0.0, "max": 20.0}},
        "geometry.hull.chine_flare_deg",
        TOOL,
        ["validity range moved", "max: recorded 20.0, source says 45.0"],
    ),
    (
        "a half-open range is recorded as one, and matches",
        {"validity": {"min": 0.0, "min_exclusive": True}},
        "geometry.hull.length",
        TOOL,
        [],
    ),
    (
        "a search source that does not list the key is not a finding",
        {"validity": {"min": 0.0, "min_exclusive": True}},
        "length",
        TOOL,
        [],
    ),
    (
        "a range recorded against a source that lacks the key is",
        {"validity": {"min": 0.0, "min_exclusive": True}, "search": {"min": 1.0, "max": 2.0}},
        "length",
        TOOL,
        ["search range recorded, but 'length' does not appear in search_box.py"],
    ),
    (
        "a key declared with no bounds is present, not vanished",
        None,
        "geometry.hull.hull_id",
        TOOL,
        [],
    ),
    (
        "a key in no source has vanished",
        None,
        "geometry.hull.keel_rocker",
        TOOL,
        ["no longer appears in tool.schema.json, search_box.py"],
    ),
]

# (label, recorded, declared, number of differences expected)
DIFF_CASES: list[tuple[str, dict, dict, int]] = [
    ("identical ranges", {"min": 0.0, "max": 45.0}, {"min": 0.0, "max": 45.0}, 0),
    ("within tolerance", {"min": 0.1, "max": 1.0}, {"min": 0.1 + 1e-12, "max": 1.0}, 0),
    (
        "an end exclusive on one side only",
        {"min": 0.0, "max": 45.0},
        {"min": 0.0, "min_exclusive": True, "max": 45.0},
        1,
    ),
    ("an end open on one side only", {"min": 0.0, "max": 45.0}, {"min": 0.0}, 1),
    ("an explicit false equals an absent flag", {"min": 0.0, "min_exclusive": False}, {"min": 0.0}, 0),
    ("both ends moved", {"min": 0.0, "max": 20.0}, {"min": 1.0, "max": 45.0}, 2),
    (
        "a conceptual end recorded without its basis",
        {"min": 0.0, "max": 45.0},
        {"min": 0.0, "max": 45.0, "basis": {"max": "conceptual"}},
        1,
    ),
    (
        "a basis that changed upstream",
        {"max": 45.0, "basis": {"max": "conceptual"}},
        {"max": 45.0, "basis": {"max": "regulatory"}},
        1,
    ),
    (
        "matching bases",
        {"min": 0.0, "max": 45.0, "basis": {"min": "mathematical", "max": "conceptual"}},
        {"min": 0.0, "max": 45.0, "basis": {"min": "mathematical", "max": "conceptual"}},
        0,
    ),
]


def schema_cases() -> tuple[list[str], int]:
    """The implementation `bounds` shape: kind-keyed, and never the old pair.

    Returns (failures, cases run). Without jsonschema none run, and the count
    says so rather than reporting them as passed.
    """
    try:
        import jsonschema
    except ImportError:  # pragma: no cover — CI installs it
        print("  SKIP  schema cases: jsonschema not installed")
        return [], 0
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def valid(bounds) -> bool:
        doc = [{
            "id": "x",
            "name": "x",
            "quantity": {"unit": "unit:DEG", "symbol": "deg", "quantity_kind": "quantitykind:Angle"},
            "definition": "x",
            "measurement_convention": {"datum": "x", "station": "x", "source": "x"},
            "implementations": [{"system": "s", "identifier": "k", "bounds": bounds}],
            "verification": {"status": "unverified", "checked_against": "x"},
        }]
        return jsonschema.Draft202012Validator(schema).is_valid(doc)

    cases = (
        ("kind-keyed ranges are accepted", {"validity": {"min": 0}, "search": {"min": 0, "max": 1}}, True),
        ("the old unkinded pair is refused", [0.0, 45.0], False),
        ("an unknown kind is refused", {"recommended": {"min": 0}}, False),
        ("a range with neither end is refused", {"validity": {"min_exclusive": True}}, False),
        ("an empty bounds block is refused", {}, False),
        ("a per-end basis is accepted", {"validity": {"max": 45, "basis": {"max": "conceptual"}}}, True),
        ("a basis outside the vocabulary is refused", {"validity": {"max": 45, "basis": {"max": "advisory"}}}, False),
    )
    failures = [f"schema: {label}" for label, bounds, want in cases if valid(bounds) != want]
    return failures, len(cases)


def main() -> int:
    failures = []

    for label, param, live, expected in CASES:
        got = find_by_name(param, live)
        if got != expected:
            failures.append(f"{label}: expected {expected!r}, got {got!r}")

    # normalise is the whole basis of the comparison; if it stops stripping
    # separators, every case above passes for the wrong reason.
    for raw, want in (
        ("L_forebody_fraction", "lforebodyfraction"),
        ("chine-flare", "chineflare"),
        ("Chine flare angle", "chineflareangle"),
    ):
        if normalise(raw) != want:
            failures.append(f"normalise({raw!r}): expected {want!r}, got {normalise(raw)!r}")

    for label, bounds, identifier, sources, expected in KIND_CASES:
        impl = {**FLARE_IMPL, "identifier": identifier}
        if bounds is not None:
            impl["bounds"] = bounds
        findings, _ = check_implementation({"id": "p", "name": "p"}, impl, sources)
        if not expected and findings:
            failures.append(f"{label}: expected clean, got {findings}")
        for want in expected:
            if not any(want in f for f in findings):
                failures.append(f"{label}: expected a finding containing {want!r}, got {findings}")

    for label, recorded, declared, want in DIFF_CASES:
        got = bounds_differ(recorded, declared)
        if len(got) != want:
            failures.append(f"bounds_differ, {label}: expected {want} difference(s), got {got}")

    # The notation is what a reader of a finding sees; an exclusive end that
    # printed as inclusive would hide the difference the finding is about.
    for r, want in (
        ({"min": 0.0, "max": 45.0}, "[0.0, 45.0]"),
        ({"min": 0.0, "min_exclusive": True, "max": 1.0, "max_exclusive": True}, "(0.0, 1.0)"),
        ({"min": 0.0}, "[0.0, +inf)"),
    ):
        if fmt_range(r) != want:
            failures.append(f"fmt_range({r}): expected {want!r}, got {fmt_range(r)!r}")

    schema_failures, schema_run = schema_cases()
    failures.extend(schema_failures)

    total = len(CASES) + 3 + len(KIND_CASES) + len(DIFF_CASES) + 3 + schema_run

    for f in failures:
        print(f"  FAIL  {f}")

    if failures:
        print(f"\nFAIL — {len(failures)} of {total} check(s)")
        return 1

    print(f"OK — {total} consumer-checker self-check(s) pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
