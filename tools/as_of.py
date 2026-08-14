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

Coverage is only as good as the history recorded. An entry with no `history`
block is *asserted* unchanged over the period its source registry record covers,
and that assertion is checked no further back than eCFR's own version history
reaches — 2016-12-30. Before that date the citation line is the only evidence,
and a section whose citation line shows an amendment this corpus has not
characterised is reported as a gap rather than passed over silently.
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
SOURCES = ROOT / "sources"

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

    # Sections amended before our history reaches, or before eCFR's horizon.
    gaps: list[str] = []
    characterised = {
        _SECTION_RE.match(d["section"]).group(1)
        for d in differed
        if _SECTION_RE.match(d["section"])
    }
    for sec, rec in sorted(registry.items()):
        for d in citation_dates(rec.get("amendment_history")):
            if when < d and sec not in characterised:
                gaps.append(
                    f"§ {sec} was amended {d.isoformat()}, after the date asked "
                    f"for, and no entry records what it said before. "
                    f"{'Pre-dates eCFR version history; ' if d < ECFR_HORIZON else ''}"
                    f"citation line: {' '.join(rec['amendment_history'].split())[:120]}"
                )
                break

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
        print(f"{len(gaps)} section(s) amended after that date with no recorded history —")
        print("the corpus cannot say what these required then:\n")
        for g in gaps:
            print(f"  ! {g}")
        print()

    print("An entry with no history block is asserted unchanged. That assertion is")
    print("only checked back to 2016-12-30, where eCFR's version history begins.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
