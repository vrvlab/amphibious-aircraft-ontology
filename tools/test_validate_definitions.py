#!/usr/bin/env python3
"""Self-checks for the definition rules in tools/validate.py: which entries may
be `defined`, what a `defined` entry must say, and where `superseded_by` may
point (docs/CONOPS.md).

Each case copies the corpus to a scratch directory, breaks one thing, and
requires the validator to refuse it with the words that say why. A rule that
has never been seen to fail is not known to work.

Usage:  python3 tools/test_validate_definitions.py
Exit:   0 when every broken corpus is refused and the intact one passes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COPIED = ("constraints", "parameters", "units", "vocabularies", "sources", "schema", "tools")


def run(mutate) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        for name in COPIED:
            shutil.copytree(ROOT / name, Path(tmp) / name)
        mutate(Path(tmp))
        done = subprocess.run(
            [sys.executable, str(Path(tmp) / "tools" / "validate.py")],
            capture_output=True, text=True, check=False,
        )
        return done.returncode, done.stdout + done.stderr


def edit(relative: str, old: str, new: str):
    def mutate(root: Path) -> None:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        assert old in text, f"{relative} no longer holds {old!r}; the case is stale"
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return mutate


TAIL_STATUS = """  distinct_from: [horizontal-tail-area]
  verification:
    status: defined"""
TAIL_RATIONALE = """    rationale: >-
      Summing the fins"""


def insert_after(relative: str, anchor: str, added: str):
    return edit(relative, anchor, anchor + added)


CASES = [
    ("the corpus as committed passes", lambda root: None, 0, "OK"),
    ("a rule filed as defined",
     edit("constraints/25.337-limit-maneuvering-load-factors.yaml",
          "    status: verified", "    status: defined"),
     1, "a rule's meaning is the regulation's, so it is never `defined`"),
    ("a unit filed as defined",
     edit("units/non-si.yaml", "    status: verified", "    status: defined"),
     1, "'defined' is not one of"),
    ("a defined parameter that does not say why",
     edit("parameters/lifting-surfaces.yaml", TAIL_RATIONALE, "    notes_: >-\n      Summing the fins"),
     1, "'rationale' is a required property"),
    ("a defined vocabulary that does not say why",
     edit("vocabularies/configuration.yaml", "    status: verified", "    status: defined"),
     1, "'rationale' is a required property"),
    ("a parameter superseded by nothing",
     insert_after("parameters/lifting-surfaces.yaml", TAIL_STATUS.split("\n")[0],
                  "\n  superseded_by: fin-area-of-nothing"),
     1, "superseded_by names 'fin-area-of-nothing', which is no parameter"),
    ("a parameter superseded by itself",
     insert_after("parameters/lifting-surfaces.yaml", TAIL_STATUS.split("\n")[0],
                  "\n  superseded_by: vertical-tail-area"),
     1, "superseded_by names itself"),
    ("a parameter superseded by a vocabulary",
     insert_after("parameters/lifting-surfaces.yaml", TAIL_STATUS.split("\n")[0],
                  "\n  superseded_by: wing-position"),
     1, "superseded_by names 'wing-position', which is no parameter"),
    ("a pointer to a pointer",
     lambda root: (
         insert_after("parameters/lifting-surfaces.yaml", TAIL_STATUS.split("\n")[0],
                      "\n  superseded_by: horizontal-tail-area")(root),
         insert_after("parameters/lifting-surfaces.yaml",
                      "  distinct_from: [vertical-tail-area]",
                      "\n  superseded_by: wing-area")(root),
     ),
     1, "which is itself superseded by 'wing-area'; name the current one"),
]


def main() -> int:
    failed = 0
    for name, mutate, want_code, want_text in CASES:
        code, out = run(mutate)
        ok = code == want_code and want_text in out
        failed += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        wanted exit {want_code} and {want_text!r}; got exit {code}:")
            print("        " + out.strip().replace("\n", "\n        "))
    print(f"{len(CASES) - failed} of {len(CASES)} self-checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
