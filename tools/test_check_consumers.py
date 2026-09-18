#!/usr/bin/env python3
"""Self-checks for the parts of check_consumers.py that are not obviously right.

Plain asserts and no test framework, so CI needs no dependency it does not
already install. Run it the same way as run_tests.py.

`find_by_name` is what makes a `status: absent` claim falsifiable. It went in
after that check was found to be missing entirely — the comment said "if it has
reappeared upstream, say so" and the code said `continue` — so the thing most
worth pinning is that it neither goes quiet again nor starts crying wolf.

Usage:  python3 tools/test_check_consumers.py
Exit:   0 all pass, 1 on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_consumers import find_by_name, normalise  # noqa: E402

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

    for f in failures:
        print(f"  FAIL  {f}")

    if failures:
        print(f"\nFAIL — {len(failures)} of {len(CASES) + 3} check(s)")
        return 1

    print(f"OK — {len(CASES) + 3} consumer-checker self-check(s) pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
