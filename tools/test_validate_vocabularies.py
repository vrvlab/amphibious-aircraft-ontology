#!/usr/bin/env python3
"""Self-checks for the vocabulary layer's rules in tools/validate.py.

Each case copies the corpus to a scratch directory, breaks one thing, and
requires the validator to refuse it with the words that say why. A rule that
has never been seen to fail is not known to work.

Usage:  python3 tools/test_validate_vocabularies.py
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


CASES = [
    ("the corpus as committed passes", lambda root: None, 0, "OK"),
    ("a value that admits a parameter that does not exist",
     edit("vocabularies/configuration.yaml",
          "admits: [deadrise-auxiliary-float]", "admits: [deadrise-of-nothing]"),
     1, "admits unknown parameter 'deadrise-of-nothing'"),
    ("a vocabulary with a parameter's id",
     edit("vocabularies/configuration.yaml", "- id: wing-position", "- id: wing-area"),
     1, "duplicate id 'wing-area'"),
    ("one value written twice",
     edit("vocabularies/configuration.yaml", "    - id: pusher", "    - id: tractor"),
     1, "'tractor' names both"),
    ("an alias that is another value's id",
     edit("vocabularies/configuration.yaml",
          "aliases: [stub planes]", "aliases: [sponsons]"),
     1, "'sponsons' names both"),
    ("a vocabulary of one value",
     edit("vocabularies/configuration.yaml",
          "    - id: pusher\n      definition: >-\n        The propeller or propellers are aft of the main supporting surfaces.\n",
          ""),
     1, "is too short"),
    ("a value with no definition",
     edit("vocabularies/configuration.yaml",
          "    - id: low-wing\n      definition: The wing is located at, or near, the bottom of the fuselage.\n",
          "    - id: low-wing\n"),
     1, "'definition' is a required property"),
    ("an id that is not a slug",
     edit("vocabularies/configuration.yaml", "    - id: high-wing", "    - id: High_Wing"),
     1, "does not match"),
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
