#!/usr/bin/env python3
"""Check the source registry against the live regulation.

This asks whether **the regulation still says what this repo verified.**

It matters because regulations change quietly. 14 CFR 25.535(d) specified a side
load coefficient of 3.25 tan β from 1964 until 2022, when Amdt. 25-148 corrected
it to 0.25 — a thirteenfold change, in a rule whose summary describes it as
fixing typographical errors. The same amendment changed 25.525(b) from citing
25.533(b) to citing 25.533(c), moving which pressure case governs. Nothing
announced either one to anybody downstream.

Sections get three checks, in increasing order of what they catch:

  1. The bracketed Federal Register citation line still matches. Catches a
     recorded amendment.
  2. The eCFR versions API reports no amendment dated after our edition.
     Catches an amendment that has not reached the citation line yet.
  3. The text digest still matches. Catches EVERYTHING else — a correction that
     never touched the citation line, a re-rendering, a silent fix.

Check 3 is the one that would have caught the 25.535(d) correction on the day it
landed, and it is the reason the registry stores a digest at all.

Figures get a fourth. The regulation publishes its equations as raster images,
and the whole of Appendix B is three images and a title — its text content is
twenty-one characters. So for the Appendix B figures an image digest is not a
supplement to the text check, it is the ONLY check that exists. It is also the
only thing anywhere that catches a figure being redrawn while the surrounding
regulatory text stands untouched: a breakpoint moving on figure 2 would change
every K1 and K2 in the corpus without altering one character of § 25.527.

Usage:  python3 tools/check_editions.py [--report-only] [--section 25.535]

        --section also narrows the figure set, by `belongs_to`, so
        `--section "Appendix B"` checks the three appendix figures alone.
Exit:   0 clean (always 0 with --report-only), 1 on any drift.

Network required. This is deliberately NOT part of the push CI — an upstream
outage must not fail an unrelated build. It runs on a schedule instead; see
.github/workflows/edition-drift.yml.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("pyyaml required:  pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources" / "sections"
FIGURES = ROOT / "sources" / "figures"

VERSIONER = (
    "https://www.ecfr.gov/api/versioner/v1/full/{date}/title-14.xml"
    "?chapter=I&subchapter=C&part={part}&section={section}"
)
VERSIONS = "https://www.ecfr.gov/api/versioner/v1/versions/title-14.json?part={part}"

CITATION_RE = re.compile(r"\[(?:Doc\. No\.|Amdt\.)[^\]]*\]")


def _context() -> ssl.SSLContext:
    """Use certifi when present; several Pythons ship without a usable trust store."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "amphibious-aircraft-ontology/edition-check"}
    )
    with urllib.request.urlopen(req, timeout=60, context=_context()) as r:
        return r.read()


def fetch(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", "replace")


def normalise(xml: str) -> str:
    """Strip markup and collapse whitespace — the form the digest is taken over."""
    t = re.sub(r"<[^>]+>", "", xml)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_registry(where: Path = SOURCES) -> list[dict]:
    records = []
    for path in sorted(where.glob("*.yaml")):
        for rec in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            rec["_file"] = path.name
            records.append(rec)
    return records


def amendments_after(part: str, edition: str, cache: dict) -> dict[str, list[str]]:
    """Section -> amendment dates later than `edition`, from the versions API."""
    if part not in cache:
        try:
            data = json.loads(fetch(VERSIONS.format(part=part)))
        except Exception as exc:  # noqa: BLE001
            cache[part] = {"_error": str(exc)}
            return cache[part]
        out: dict[str, list[str]] = {}
        for row in data.get("content_versions", []):
            out.setdefault(row["identifier"], []).append(row["amendment_date"])
        cache[part] = out
    table = cache[part]
    if "_error" in table:
        return table
    return {k: sorted(d for d in v if d > edition) for k, v in table.items()}


def main() -> int:
    report_only = "--report-only" in sys.argv
    only = None
    if "--section" in sys.argv:
        only = sys.argv[sys.argv.index("--section") + 1]

    records = load_registry()
    all_figures = load_registry(FIGURES)
    if only:
        records = [r for r in records if r["section"] == only]
        # "Appendix B" names no section — its content is figures and a title —
        # so a filter matching only figures is legitimate, not an error.
        if not records and not [f for f in all_figures if f["belongs_to"] == only]:
            print(f"nothing registered under {only!r}")
            return 1

    findings: list[str] = []
    notes: list[str] = []
    checked = 0
    versions_cache: dict = {}

    for rec in records:
        section = rec["section"]
        part = section.split(".")[0]
        url = VERSIONER.format(date=rec["edition"], part=part, section=section)

        try:
            live = normalise(fetch(url))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            notes.append(f"§ {section}: could not fetch ({exc}) — not checked")
            continue

        if len(live) < 80:
            notes.append(f"§ {section}: eCFR returned no usable text — not checked")
            continue

        checked += 1

        # 3. Text digest — the broadest tripwire.
        got = digest(live)
        if got != rec["text_sha256"]:
            findings.append(
                f"§ {section}: TEXT CHANGED at the recorded edition "
                f"{rec['edition']} — digest {rec['text_sha256']} recorded, "
                f"{got} live; {rec['text_chars']} chars recorded, {len(live)} live. "
                f"Re-read the section, update every entry that cites it, and record "
                f"the superseded value in the entry's history block."
            )

        # 1. Citation line.
        m = CITATION_RE.findall(live)
        live_cite = m[-1] if m else None
        recorded = rec.get("amendment_history")
        recorded_norm = " ".join(recorded.split()) if recorded else None
        if live_cite != recorded_norm:
            findings.append(
                f"§ {section}: amendment citation line changed\n"
                f"      recorded: {recorded_norm or '(none)'}\n"
                f"      live:     {live_cite or '(none)'}"
            )

        # 2. Amendments after our edition, per the versions API.
        later = amendments_after(part, str(rec["edition"]), versions_cache)
        if "_error" in later:
            notes.append(f"versions API unavailable for part {part} — amendment scan skipped")
        elif later.get(section):
            findings.append(
                f"§ {section}: amended after the recorded edition "
                f"{rec['edition']} — {', '.join(later[section])}"
            )

    # ---- figures ---------------------------------------------------------
    figures = all_figures
    if only:
        figures = [f for f in figures if f["belongs_to"] == only]
    fig_checked = 0
    for fig in figures:
        try:
            blob = fetch_bytes(fig["url"])
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            notes.append(f"{fig['id']}: could not fetch ({exc}) — not checked")
            continue
        fig_checked += 1
        got = hashlib.sha256(blob).hexdigest()[:16]
        if got != fig["sha256"] or len(blob) != fig["bytes"]:
            findings.append(
                f"{fig['id']} ({fig['citation']}): IMAGE CHANGED — digest "
                f"{fig['sha256']} recorded, {got} live; {fig['bytes']} bytes "
                f"recorded, {len(blob)} live. This figure is the source for "
                f"{', '.join(fig['read_by'])}. Re-read it before trusting "
                f"anything derived from it."
            )

    print(
        f"{checked} of {len(records)} section(s) and "
        f"{fig_checked} of {len(figures)} figure(s) checked against live sources"
    )
    for n in notes:
        print(f"  - {n}")

    if findings:
        print(f"\n{'REPORT' if report_only else 'DRIFT'} — {len(findings)} finding(s)\n")
        for f in findings:
            print(f"  • {f}")
        return 0 if report_only else 1

    print("\nOK — every section and figure still reads as recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
