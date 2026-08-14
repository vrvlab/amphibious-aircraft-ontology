#!/usr/bin/env python3
"""Execute every worked test case in the constraint corpus.

`status: worked` is a claim that the entry's own arithmetic reproduces a stated
result. This runner makes that claim earned rather than asserted.

Everything is derived from the YAML. There is no second copy of any formula in
this file — expressions are parsed and evaluated as written, and graph-valued
terms are interpolated from their declared breakpoints. Edit a constant in the
corpus and this fails; that is the whole point.

Three evaluation modes:

  via omitted        this entry's formula, or its breakpoints if it has them
  via: bound         this entry's own bound predicate, against inputs.value
  via: <entry-id>    the named entry's formula — for a bound that constrains a
                     quantity some other entry computes

Usage:  python3 tools/run_tests.py [--verbose]
Exit:   0 all worked cases reproduce, 1 otherwise.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / "constraints"

#: Relative tolerance for a reproduced value. The corpus states results to four
#: decimals, so this is looser than the arithmetic but tighter than the digits.
RTOL = 5e-5

_TRIG = {
    # The corpus states every angle in degrees, because the regulation does.
    "tan": lambda d: math.tan(math.radians(d)),
    "sin": lambda d: math.sin(math.radians(d)),
    "cos": lambda d: math.cos(math.radians(d)),
    "atan": lambda x: math.degrees(math.atan(x)),
    "sqrt": math.sqrt,
    "abs": abs,
    "min": min,
    "max": max,
}

_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: math.isclose(a, b, rel_tol=RTOL, abs_tol=1e-12),
}


class Unevaluable(Exception):
    """Raised when a case claims `worked` but nothing can execute it."""


def load_corpus() -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for path in sorted(CONSTRAINTS.glob("*.yaml")):
        for entry in yaml.safe_load(path.read_text(encoding="utf-8")):
            entry["_file"] = path.name
            entries[entry["id"]] = entry
    return entries


def split_expression(expression: str) -> tuple[str, str]:
    """Return (result symbol, evaluable right-hand side).

    Handles `n_w = ...`, `n_neg(V) = ...`, and a trailing domain clause such as
    `   for V_C <= V <= V_D`, which is documentation rather than arithmetic.
    """
    if expression.count("\n") > 0:
        raise Unevaluable("expression is multi-line prose; use breakpoints instead")
    # Split on the first '=' that is not part of <=, >=, ==.
    m = re.search(r"(?<![<>=!])=(?!=)", expression)
    if not m:
        raise Unevaluable("expression has no left-hand side")
    lhs, rhs = expression[: m.start()], expression[m.end():]

    symbol = lhs.strip()
    if "(" in symbol:  # n_neg(V) -> n_neg
        symbol = symbol.split("(", 1)[0].strip()

    rhs = re.split(r"\s{2,}for\s|\s+for\s+\w+\s*<=", rhs)[0]
    return symbol, rhs.strip()


def evaluate(rhs: str, inputs: dict) -> float:
    """Evaluate a corpus expression with the supplied symbol bindings."""
    py = rhs.replace("^", "**")
    env = dict(_TRIG)
    env.update({k: v for k, v in inputs.items() if isinstance(v, (int, float))})
    try:
        return float(eval(py, {"__builtins__": {}}, env))  # noqa: S307
    except NameError as exc:
        raise Unevaluable(f"unbound symbol in expression: {exc}") from exc
    except ZeroDivisionError as exc:
        raise Unevaluable(f"division by zero evaluating {rhs!r}") from exc
    except SyntaxError as exc:
        # Most often an expression carrying several equations at once, or
        # implicit multiplication. Both are corpus defects; report, don't crash.
        raise Unevaluable(
            f"{rhs!r} is not a single evaluable expression ({exc.msg}). "
            f"Split multiple equations into separate entries and make every "
            f"multiplication explicit."
        ) from exc
    except TypeError as exc:
        raise Unevaluable(f"type error evaluating {rhs!r}: {exc}") from exc


def interpolate(entry: dict, inputs: dict) -> tuple[str, float]:
    """Piecewise-linear lookup from an entry's declared breakpoints.

    The forebody/afterbody split carries the discontinuity at the main step: a
    station at the end of the forebody and one at the start of the afterbody
    share a physical location but not a value, and must not be interpolated
    across.
    """
    pts = entry.get("breakpoints") or []
    if not all("t" in p and "body" in p for p in pts):
        raise Unevaluable("breakpoints lack numeric body/t positions")

    body, t = inputs.get("body"), inputs.get("t")
    if body is None or t is None:
        raise Unevaluable("inputs must supply body and t")

    on_body = sorted((p for p in pts if p["body"] == body), key=lambda p: p["t"])
    if not on_body:
        raise Unevaluable(f"no breakpoints declared on the {body}")

    if t <= on_body[0]["t"]:
        value = float(on_body[0]["value"])
    elif t >= on_body[-1]["t"]:
        value = float(on_body[-1]["value"])
    else:
        value = float("nan")
        for lo, hi in zip(on_body, on_body[1:]):
            if lo["t"] <= t <= hi["t"]:
                span = hi["t"] - lo["t"]
                frac = 0.0 if span == 0 else (t - lo["t"]) / span
                value = lo["value"] + (hi["value"] - lo["value"]) * frac
                break

    # The result symbol is the first declared variable of the entry's formula.
    symbol = entry["formula"]["variables"][0]["symbol"]
    return symbol, value


def check_bound(entry: dict, inputs: dict) -> tuple[str, bool]:
    bound = entry.get("bound")
    if not bound:
        raise Unevaluable("via: bound but the entry declares no bound")
    value = bound.get("value")
    if not isinstance(value, (int, float)):
        raise Unevaluable(f"bound value {value!r} is symbolic, not numeric")
    if "value" not in inputs:
        raise Unevaluable("inputs must supply `value` for a bound check")
    op = _OPS.get(bound["operator"])
    if op is None:
        raise Unevaluable(f"operator {bound['operator']!r} is not checkable")
    return "compliant", op(float(inputs["value"]), float(value))


def run_case(entry: dict, case: dict, corpus: dict) -> list[str]:
    """Return a list of failure strings; empty means the case reproduced."""
    via = case.get("via")
    inputs, expected = case["inputs"], case["expected"]

    if via == "bound":
        key, got = check_bound(entry, inputs)
        results = {key: got}
    else:
        target = entry if via is None else corpus.get(via)
        if target is None:
            return [f"via names unknown entry {via!r}"]
        if via is None and target.get("breakpoints"):
            key, got = interpolate(target, inputs)
            results = {key: got}
        else:
            formula = target.get("formula")
            if not formula:
                raise Unevaluable(f"{target['id']} has no formula to evaluate")
            key, rhs = split_expression(formula["expression"])
            results = {key: evaluate(rhs, inputs)}

    failures = []
    for key, want in expected.items():
        if key not in results:
            failures.append(
                f"expected key {key!r} is not produced "
                f"(this case yields {', '.join(results)})"
            )
            continue
        got = results[key]
        if isinstance(want, bool) or isinstance(got, bool):
            if bool(got) != bool(want):
                failures.append(f"{key}: expected {want}, got {got}")
        elif not math.isclose(float(got), float(want), rel_tol=RTOL, abs_tol=1e-9):
            failures.append(f"{key}: expected {want}, got {got:.6f}")
    return failures


def main() -> int:
    verbose = "--verbose" in sys.argv
    corpus = load_corpus()

    ran = skipped = 0
    failures: list[str] = []

    for entry in corpus.values():
        for case in entry.get("test_cases") or []:
            label = f"{entry['id']} — {case['description'].strip().splitlines()[0]}"
            if case["status"] != "worked":
                skipped += 1
                if verbose:
                    print(f"  skip  {label}  [{case['status']}]")
                continue
            try:
                problems = run_case(entry, case, corpus)
            except Unevaluable as exc:
                failures.append(
                    f"{label}\n      claims `worked` but is not machine-evaluable: {exc}"
                )
                continue
            ran += 1
            if problems:
                failures.append(label + "\n      " + "\n      ".join(problems))
            elif verbose:
                print(f"  ok    {label}")

    print()
    if failures:
        print(f"FAIL — {len(failures)} of {ran + len(failures)} worked case(s)\n")
        for f in failures:
            print(f"  • {f}")
        return 1

    print(f"OK — {ran} worked case(s) reproduce; {skipped} pending case(s) skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
