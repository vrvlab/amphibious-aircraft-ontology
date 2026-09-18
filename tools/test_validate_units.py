#!/usr/bin/env python3
"""Self-checks for the unit registry's rules in tools/validate.py.

Each case copies the corpus to a scratch directory, breaks one thing, and
requires the validator to refuse it with the words that say why. A rule that
has never been seen to fail is not known to work: the unit table lived inside
the validator for two releases and nothing checked it against anything.

Usage:  python3 tools/test_validate_units.py
Exit:   0 when every broken corpus is refused and the intact one passes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COPIED = ("constraints", "parameters", "units", "sources", "schema", "tools")


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
    ("a parameter in a unit with no record",
     edit("parameters/chine-flare.yaml", "unit: unit:DEG", "unit: unit:GRAD"),
     1, "has no record in units/"),
    ("a symbol that is not the unit's",
     edit("parameters/chine-flare.yaml", "symbol: deg", "symbol: m"),
     1, "implies symbol 'deg'"),
    ("a length in pounds-force: the unit does not measure the kind",
     edit("parameters/hull-stations.yaml",
          "unit: unit:M\n    symbol: m", "unit: unit:LB_F\n    symbol: lbf"),
     1, "unit:LB_F does not measure quantitykind:Length"),
    ("a quantity kind no unit measures",
     edit("parameters/chine-flare.yaml", "quantitykind:Angle", "quantitykind:Luminance"),
     1, "is measured by no unit"),
    ("a factor that changes the dimension",
     edit("units/non-si.yaml", "unit: unit:N\n", "unit: unit:PA\n"),
     1, "whose dimension differs"),
    ("a factor to a unit that is not coherent",
     edit("units/non-si.yaml", "unit: unit:M3\n", "unit: unit:FT3\n"),
     1, "is not coherent SI"),
    ("a factor to a unit with no record",
     edit("units/non-si.yaml", "unit: unit:RAD\n", "unit: unit:GON\n"),
     1, "converts to unknown unit"),
    ("an exact factor that is not its expression",
     edit("units/non-si.yaml", 'factor: "4.4482216152605"', 'factor: "4.448222"'),
     1, "is declared exact and is not"),
    ("a rounded factor that is not the nearest double",
     edit("units/non-si.yaml", 'factor: "0.5144444444444445"', 'factor: "0.5144444"'),
     1, "is not the nearest double"),
    ("an expression that is not arithmetic",
     edit("units/non-si.yaml", 'expression: "pi/180"', 'expression: "__import__(1)"'),
     1, "does not evaluate"),
    ("an inexact factor with no expression",
     edit("units/non-si.yaml", '    expression: "pi/180"\n', ""),
     1, "must carry the expression"),
    ("two units with one symbol",
     edit("units/non-si.yaml", 'symbol: "mm"', 'symbol: "m"'),
     1, "symbol 'm' is already"),
    ("two units with one UCUM code",
     edit("units/si.yaml", 'ucum: "m/s2"', 'ucum: "m/s"'),
     1, "ucum 'm/s' is already"),
    ("QUDT's spelling recorded where it does not differ",
     edit("units/si.yaml", 'ucum_qudt: "kg.m-3"', 'ucum_qudt: "kg/m3"'),
     1, "ucum_qudt repeats ucum"),
    ("QUDT's spelling that is another unit's code",
     edit("units/si.yaml", 'ucum_qudt: "m.s-2"', 'ucum_qudt: "m/s"'),
     1, "is unit:M-PER-SEC's ucum"),
    ("a unit record twice",
     lambda root: (root / "units" / "again.yaml").write_text(
         (root / "units" / "si.yaml").read_text(encoding="utf-8").split("\n- id: unit:KiloGM")[0],
         encoding="utf-8"),
     1, "duplicate unit record"),
    ("a coherent unit with a factor",
     edit("units/si.yaml", "  si_coherent: true\n",
          "  si_coherent: true\n  to_coherent_si: {unit: \"unit:M\", factor: \"1\", exact: true}\n"),
     1, "si.yaml"),
    ("a unit that is not coherent and has no factor",
     edit("units/non-si.yaml",
          '  to_coherent_si:\n    unit: unit:M\n    factor: "0.001"\n    exact: true\n'
          "    basis: SI prefix milli, 10^-3. SI Brochure Table 7. A prefixed unit is SI and is not coherent (section 2.3.4).\n",
          ""),
     1, "'to_coherent_si' is a required property"),
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
