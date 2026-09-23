#!/usr/bin/env python3
"""Self-checks for the edition promise in tools/changelog.py.

Each case builds two small editions, breaks or keeps the promise one way, and
requires the diff to say so. A rule never seen to fail is not known to work.

Usage:  python3 tools/test_changelog.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from changelog import LAYERS, diff  # noqa: E402


def edition(**parameters) -> dict:
    layers = {layer: {} for layer in LAYERS}
    layers["parameters"] = {i: {"id": i, **e} for i, e in parameters.items()}
    return layers


BASE = edition(**{
    "hull-length": {"quantity": {"unit": "unit:M"}},
    "wing-area": {"quantity": {"unit": "unit:M2"}},
})


def broken(old, new) -> list[str]:
    return diff(old, new)["parameters"]["broken"]


def case_superseded_then_removed():
    marked = copy.deepcopy(BASE)
    marked["parameters"]["wing-area"]["superseded_by"] = "hull-length"
    gone = copy.deepcopy(marked)
    del gone["parameters"]["wing-area"]
    d = diff(BASE, marked)["parameters"]
    return d["superseded"] == [("wing-area", "hull-length")] and not d["broken"] \
        and not broken(marked, gone)


CASES = [
    ("an edition against itself breaks nothing", lambda: broken(BASE, BASE) == []),
    ("an added id breaks nothing",
     lambda: broken(BASE, edition(**BASE["parameters"], **{"draft": {"quantity": {"unit": "unit:M"}}})) == []),
    ("an id removed without being superseded breaks the promise",
     lambda: any("`wing-area` removed" in b for b in broken(
         BASE, edition(**{"hull-length": BASE["parameters"]["hull-length"]})))),
    ("an id superseded in one edition and removed in the next does not", case_superseded_then_removed),
    ("a unit changed breaks the promise",
     lambda: any("`hull-length` changed unit" in b for b in broken(
         BASE, edition(**{**BASE["parameters"], "hull-length": {"quantity": {"unit": "unit:FT"}}})))),
    ("a changed entry is listed with the keys that changed",
     lambda: diff(BASE, edition(**{**BASE["parameters"],
                                   "wing-area": {"quantity": {"unit": "unit:M2"}, "definition": "x"}}))
     ["parameters"]["changed"] == [("wing-area", ["definition"])]),
]


def main() -> int:
    failed = 0
    for name, check in CASES:
        ok = bool(check())
        failed += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
    print(f"{len(CASES) - failed} of {len(CASES)} self-checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
