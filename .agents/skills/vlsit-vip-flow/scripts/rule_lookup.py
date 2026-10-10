#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Print exact rule text from VLSIT_VIP_Design_Rule.md by ID or prefix.

Use it instead of loading the whole rule file: the output is the original rule text,
not a summary, so it keeps the rule file authoritative while costing only the lines
that apply. A prefix such as VCHK prints every VCHK rule; VP prints the prohibited
table rows.

Usage:
    python rule_lookup.py --index                 prefixes with titles and counts
    python rule_lookup.py VCHK VIFC               every rule of these groups
    python rule_lookup.py VCHK-02 VP-03           single rules
    python rule_lookup.py --grep "clocking"       rules that mention a word
    python rule_lookup.py --section 11            a numbered section of the rule file
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULE_FILE = "VLSIT_VIP_Design_Rule.md"


def find_rule_file(explicit: str | None) -> Path:
    cands = [Path(explicit)] if explicit else []
    cands += [HERE.parent / "references" / RULE_FILE, HERE.parent / "spec_template" / RULE_FILE,
              HERE.parent.parent / "spec_template" / RULE_FILE]
    for c in cands:
        if c.is_file():
            return c
    raise SystemExit(f"error: {RULE_FILE} not found; pass --rule-file")


def parse(path: Path):
    """Return (entries, sections): entries are (id, prefix, text, section number)."""
    entries, sections = [], {}
    sec = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(\d+)\.\s+(.*)$", line)
        if m:
            sec = m.group(1)
            sections[sec] = m.group(2)
            continue
        m = re.match(r"^- \*\*([A-Z]+-\d+)\*\*\s", line)
        if m:
            rid = m.group(1)
            entries.append((rid, rid.split("-")[0], line, sec))
            continue
        m = re.match(r"^\| (VP-\d+) \|", line)
        if m:
            entries.append((m.group(1), "VP", line, sec))
    return entries, sections


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="rule IDs or prefixes")
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--grep")
    ap.add_argument("--section")
    ap.add_argument("--rule-file")
    a = ap.parse_args()
    path = find_rule_file(a.rule_file)
    entries, sections = parse(path)
    if a.index:
        pref: dict[str, list] = {}
        for rid, p, _, sec in entries:
            pref.setdefault(p, []).append(sec)
        for p, secs in pref.items():
            print(f"{p}\t{len(secs)} rule(s)\tsection {secs[0]}: {sections.get(secs[0], '')}")
        return 0
    if a.section:
        lines = path.read_text(encoding="utf-8").splitlines()
        out, on = [], False
        for ln in lines:
            m = re.match(r"^##\s+(\d+)\.", ln)
            if m:
                on = m.group(1) == a.section
            if on:
                out.append(ln)
        print("\n".join(out) if out else f"error: no section {a.section}")
        return 0 if out else 1
    picked = []
    for rid, p, text, _ in entries:
        if a.grep and a.grep.lower() in text.lower():
            picked.append(text)
        elif any(rid == q or p == q or rid.startswith(q + "-") for q in a.ids):
            picked.append(text)
    if not picked:
        print("no matching rule; try --index", file=sys.stderr)
        return 1
    print("\n".join(picked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
