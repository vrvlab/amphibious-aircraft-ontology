#!/usr/bin/env python3
"""What each edition added, superseded, changed and removed, from dist/.

A consumer pins one tag (README, Using it) and needs to know, before it pins
the next, which of the ids it uses moved. The published artifacts already hold
every entry by id, so the changelog is computed from them rather than written:
each edition's dist/*.json against the one before it.

It also holds the edition promise (docs/CONOPS.md, Editions and what they
promise), which applies from the first edition after v0.6.0:

  * an id is removed only in a major edition (the first component of the
    version rises), and only when the edition before marked it `superseded_by`;
  * a parameter's unit does not change.

A changed meaning under the same id cannot be detected from the data. That
part of the promise is the reviewer's.

Usage:
  python3 tools/changelog.py                     # last tag -> working tree, printed
  python3 tools/changelog.py --promise           # the same, exit 1 if the promise is broken
  python3 tools/changelog.py --promise --next v1.0.0   # judged as that edition
  python3 tools/changelog.py --write             # CHANGELOG.md from the tags alone
  python3 tools/changelog.py --write --next v0.7.0
      # rewrite CHANGELOG.md with every tag, and the working tree as v0.7.0;
      # run before tagging, and commit the result in the tagged commit
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ("constraints", "parameters", "units", "vocabularies")
WORKTREE = None  # a ref of None means the files on disk
#: The last edition published before the promise was made. Removals and unit
#: changes up to and including it are listed, not judged.
PROMISE_AFTER = (0, 6, 0)


def _version(tag: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", tag))


def tags() -> list[str]:
    out = subprocess.run(
        ["git", "tag", "--list", "v*"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return sorted(out, key=_version)


def load(ref: str | None) -> dict[str, dict[str, dict]]:
    """Every layer's entries by id, at a ref or on disk. A layer an edition did
    not publish yet is empty."""
    layers = {}
    for layer in LAYERS:
        path = f"dist/{layer}.json"
        if ref is WORKTREE:
            file = ROOT / path
            text = file.read_text(encoding="utf-8") if file.exists() else None
        else:
            done = subprocess.run(
                ["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True
            )
            text = done.stdout if done.returncode == 0 else None
        entries = json.loads(text)["entries"] if text else []
        layers[layer] = {e["id"]: e for e in entries if "id" in e}
    return layers


def is_major(old: str | None, new: str | None) -> bool:
    """True when `new` raises the first component of `old`'s version: the only
    edition that may remove an id. Unknown editions are not major."""
    return bool(old and new) and _version(new)[:1] > _version(old)[:1]


def diff(old: dict, new: dict, major: bool = False) -> dict[str, dict[str, list]]:
    out = {}
    for layer in LAYERS:
        a, b = old[layer], new[layer]
        added = sorted(set(b) - set(a))
        removed = sorted(set(a) - set(b))
        superseded = sorted(
            i for i in set(a) & set(b)
            if b[i].get("superseded_by") and not a[i].get("superseded_by")
        )
        changed = []
        for i in sorted(set(a) & set(b)):
            if a[i] == b[i] or i in superseded:
                continue
            keys = sorted(k for k in set(a[i]) | set(b[i]) if a[i].get(k) != b[i].get(k))
            changed.append((i, keys))
        broken = [
            f"`{i}` removed without being superseded in the edition before"
            for i in removed if not a[i].get("superseded_by")
        ] + [
            f"`{i}` removed in an edition that is not major"
            for i in removed if a[i].get("superseded_by") and not major
        ]
        if layer == "parameters":
            for i in sorted(set(a) & set(b)):
                ua = (a[i].get("quantity") or {}).get("unit")
                ub = (b[i].get("quantity") or {}).get("unit")
                if ua != ub:
                    broken.append(f"`{i}` changed unit, {ua} to {ub}")
        out[layer] = {
            "added": added, "superseded": [(i, b[i]["superseded_by"]) for i in superseded],
            "changed": changed, "removed": removed, "broken": broken,
        }
    return out


def render(title: str, d: dict, judged: bool) -> str:
    lines = [f"## {title}", ""]
    empty = True
    for layer in LAYERS:
        x = d[layer]
        if not any(x[k] for k in ("added", "superseded", "changed", "removed")):
            continue
        empty = False
        lines.append(f"### {layer}")
        lines.append("")
        if x["added"]:
            lines.append("- **Added:** " + ", ".join(f"`{i}`" for i in x["added"]))
        for i, to in x["superseded"]:
            lines.append(f"- **Superseded:** `{i}` by `{to}`")
        for i, keys in x["changed"]:
            lines.append(f"- **Changed:** `{i}` ({', '.join(keys)})")
        if x["removed"]:
            lines.append("- **Removed:** " + ", ".join(f"`{i}`" for i in x["removed"]))
        if judged:
            for b in x["broken"]:
                lines.append(f"- **Breaks the edition promise:** {b}")
        lines.append("")
    if empty:
        lines += ["No entry changed.", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--promise", action="store_true", help="exit 1 if the promise is broken")
    ap.add_argument("--write", action="store_true", help="rewrite CHANGELOG.md")
    ap.add_argument("--next", help="the edition the working tree will be tagged as")
    args = ap.parse_args()

    ts = tags()
    if not ts:
        sys.exit("no v* tags: fetch them first (git fetch --tags)")

    if args.write:
        # Without --next, the tagged editions only; with it, the working tree too.
        editions = [(t, t) for t in ts] + ([(args.next, WORKTREE)] if args.next else [])
        sections, prev, prev_name, broken = [], None, None, []
        for name, ref in editions:
            cur = load(ref)
            if prev is None:
                sections.append(f"## {name}\n\nThe first tagged edition.\n")
            else:
                d = diff(prev, cur, is_major(prev_name, name))
                judged = _version(name) > PROMISE_AFTER
                sections.append(render(name, d, judged))
                if judged:
                    broken += [b for x in d.values() for b in x["broken"]]
            prev, prev_name = cur, name
        head = (
            "# Changelog\n\n"
            "Generated by `python3 tools/changelog.py --write`; do not edit by hand.\n"
            "Each edition against the one before, computed from `dist/`. From the first\n"
            "edition after v0.6.0 the edition promise holds (docs/CONOPS.md), and a\n"
            "change that breaks it is named here.\n\n"
        )
        (ROOT / "CHANGELOG.md").write_text(head + "\n".join(reversed(sections)), encoding="utf-8")
        return 1 if broken else 0

    last = ts[-1]
    # Without --next the working tree is taken as a minor edition: the strict case.
    d = diff(load(last), load(WORKTREE), is_major(last, args.next))
    judged = _version(last) >= PROMISE_AFTER
    print(render(f"{last} to the working tree", d, judged))
    broken = [b for x in d.values() for b in x["broken"]]
    return 1 if (args.promise and judged and broken) else 0


if __name__ == "__main__":
    raise SystemExit(main())
