#!/usr/bin/env python3
"""Report what the corpus said on a given date.

An aircraft is certified to Part 25 *as amended through a stated amendment
level*, not to whatever the section says today. So "what did § 25.535(d)
require in 2015?" is an ordinary engineering question, and a corpus that can
only answer "what does it require now?" cannot be used for a design review of
an in-service type.

This reads the `history` blocks and reports every entry whose substance differed
on the date asked for.

    python3 tools/as_of.py 2015-06-01
    python3 tools/as_of.py 2015-06-01 --json

Coverage is only as good as the evidence held. Each section in `sources/` carries
a `history_verified_from` date: the earliest edition its text has actually been
compared against. Above that date, an entry with no `history` block is unchanged
because the comparison was made. Below it, the corpus cannot speak, and says so
rather than returning a confident answer it has not earned.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml required:  pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / "constraints"
SOURCES = ROOT / "sources" / "sections"

#: eCFR's own version history begins here. Older changes are visible only
#: through the amendment citation line.
ECFR_HORIZON = _dt.date(2016, 12, 30)

_SECTION_RE = re.compile(r"^(\d+\.\d+)")
#: Dates inside a Federal Register citation line, e.g. "Apr. 8, 1970".
_CITE_DATE_RE = re.compile(
    r"(Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec)\w*\.?\s+(\d{1,2}),\s*(\d{4})"
)
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"], 1)}


def as_date(v) -> _dt.date:
    if isinstance(v, _dt.date):
        return v
    return _dt.date.fromisoformat(str(v))


def load(dirpath: Path) -> list[dict]:
    out = []
    for path in sorted(dirpath.glob("*.yaml")):
        for rec in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            out.append(rec)
    return out


def citation_dates(line: str | None) -> list[_dt.date]:
    if not line:
        return []
    dates = []
    for mon, day, year in _CITE_DATE_RE.findall(line):
        try:
            dates.append(_dt.date(int(year), _MONTHS[mon], int(day)))
        except ValueError:
            pass
    return sorted(dates)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__.strip().splitlines()[0])
        print("\nusage: python3 tools/as_of.py YYYY-MM-DD [--json]")
        return 2
    try:
        when = _dt.date.fromisoformat(args[0])
    except ValueError:
        print(f"not a date: {args[0]!r} — use YYYY-MM-DD")
        return 2
    want_json = "--json" in sys.argv

    entries = load(CONSTRAINTS)
    registry = {r["section"]: r for r in load(SOURCES)}
    if not registry:
        # An empty registry silently disables every horizon check below, which
        # would report full confidence for dates nothing has been verified at.
        print(f"no source records found under {SOURCES.relative_to(ROOT)} — cannot "
              f"report what has and has not been verified")
        return 1

    differed: list[dict] = []
    for e in entries:
        for h in e.get("history") or []:
            if as_date(h["effective_from"]) <= when < as_date(h["effective_to"]):
                differed.append({
                    "id": e["id"],
                    "section": e["source"]["section"],
                    "title": e["title"],
                    "current": (e.get("bound") or {}).get("value")
                    or (e.get("formula") or {}).get("expression")
                    or " ".join(str(e.get("statement", "")).split())[:160]
                    or None,
                    "as_of": h.get("superseded_value"),
                    "amendment": " ".join(str(h["amendment"]).split()),
                    "substantive": h.get("substantive", True),
                    "change": " ".join(str(h["change"]).split()),
                })

    # Below a section's verified horizon the corpus holds no evidence either
    # way. Reporting that is the point: silence would read as "unchanged".
    gaps: list[str] = []
    for sec, rec in sorted(registry.items()):
        horizon = rec.get("history_verified_from")
        if horizon and when < as_date(horizon):
            cite = rec.get("amendment_history")
            amendments = [d for d in citation_dates(cite) if d > when]
            gaps.append(
                f"§ {sec}: text has only been compared back to {horizon}, so the "
                f"corpus cannot say what it required on this date"
                + (f" — its citation line records {len(amendments)} amendment(s) "
                   f"after it ({', '.join(d.isoformat() for d in amendments)})"
                   if amendments else " — its citation line records no later amendment")
            )

    if want_json:
        print(json.dumps(
            {"as_of": when.isoformat(), "entries_differing": differed, "gaps": gaps},
            indent=2))
        return 0

    print(f"Corpus as of {when.isoformat()}\n")
    if differed:
        print(f"{len(differed)} entr{'y' if len(differed)==1 else 'ies'} differed on that date:\n")
        for d in differed:
            flag = "" if d["substantive"] else "  (non-substantive)"
            print(f"  {d['id']}  [§ {d['section']}]{flag}")
            print(f"    then: {d['as_of']}")
            print(f"    now:  {d['current']}")
            print(f"    changed by: {d['amendment']}")
            print(f"    {d['change'][:300]}\n")
    else:
        print("No entry has a recorded history covering that date.\n")

    if gaps:
        print(f"{len(gaps)} section(s) fall below their verified horizon:\n")
        for g in gaps:
            print(f"  ! {g}")
        print()
        print("For these the corpus holds no evidence either way. Closing them means")
        print("reading the Federal Register issues named in the citation line —")
        print("govinfo publishes no CFR granule for this title before 1997.")
    else:
        print("Every section has been compared back past this date, so an entry with")
        print("no history block above is unchanged rather than merely unexamined.")
        print("The comparison is between editions at the ends of the window: it")
        print("detects net change, not a value that changed and changed back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
