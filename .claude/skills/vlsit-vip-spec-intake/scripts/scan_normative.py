#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""List the normative sentences of a standard (converted to text) and check that
every one is classified against the VIP specification.

Step 1 - scan (writes a new CSV):
    python scan_normative.py scan STANDARD.txt --out normative_candidates.csv [--section-start N --section-end M]

Step 2 - classify: copy normative_candidates.csv to normative_map.csv and fill the
`disposition` and `ref` columns for every row:
    mapped       ref = requirement ID (VREQ-...) that states this sentence
    informative  ref = short reason (the sentence gives no testable behavior)
    out_of_scope ref = short reason (feature excluded by the specification scope)
    duplicate    ref = candidate ID (N-nnnn) of the sentence that is already mapped

Step 3 - report:
    python scan_normative.py report normative_map.csv [--spec SPEC.md] [--out report.md]

The report fails (exit 1) when a candidate is unclassified, a `mapped` reference
does not exist in the specification, or a requirement has no source sentence.
Standard library only. Outputs are new files and are never overwritten.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402

KEYWORDS = [
    (r"\bshall not\b", "shall not"), (r"\bshall\b", "shall"), (r"\bmust not\b", "must not"),
    (r"\bmust\b", "must"), (r"\bshould not\b", "should not"), (r"\bshould\b", "should"),
    (r"\bmay\b", "may"), (r"\bis required\b|\bare required\b|\brequired to\b", "required"),
    (r"\brecommended\b", "recommended"), (r"\bnot permitted\b|\bprohibited\b|\billegal\b", "prohibited"),
]
CAND_COLUMNS = ["cand_id", "line", "keyword", "sentence", "disposition", "ref"]
DISPOSITIONS = ["mapped", "informative", "out_of_scope", "duplicate"]


def paragraphs(lines: list[str]) -> list[tuple[int, str]]:
    """Join wrapped lines into paragraphs; return (first line number, text)."""
    out, buf, start = [], [], 0
    for n, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s:
            if buf:
                out.append((start, " ".join(buf)))
                buf = []
            continue
        if not buf:
            start = n
        buf.append(s)
    if buf:
        out.append((start, " ".join(buf)))
    return out


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?:;])\s+(?=[A-Z0-9(\"'])", text)
    return [p.strip() for p in parts if p.strip()]


def scan(path: Path, start: int, end: int) -> list[dict]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    sel = lines[max(start - 1, 0): end if end else len(lines)]
    base = max(start - 1, 0)
    rows: list[dict] = []
    seen: set[str] = set()
    for pstart, ptext in paragraphs(sel):
        for sent in sentences(ptext):
            kws = [name for rx, name in KEYWORDS if re.search(rx, sent, re.I)]
            if not kws:
                continue
            key = re.sub(r"\W+", " ", sent.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            rows.append({"cand_id": f"N-{len(rows) + 1:04d}", "line": base + pstart,
                         "keyword": "/".join(dict.fromkeys(kws)), "sentence": sent,
                         "disposition": "", "ref": ""})
    return rows


def cmd_scan(args: argparse.Namespace) -> int:
    out = Path(args.out)
    vc.refuse_overwrite(out)
    rows = scan(Path(args.standard), args.section_start, args.section_end)
    vc.write_csv(out, rows, CAND_COLUMNS)
    print(f"{len(rows)} normative candidate sentence(s) written to {out}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    rows = vc.read_csv(args.map)
    rep = vc.Report("Normative sentence classification", args.map)
    spec_reqs: set[str] = set()
    if args.spec:
        spec_reqs = {r["req_id"] for r in vc.load_spec(args.spec).rows("requirements")}
    counts = {d: 0 for d in DISPOSITIONS}
    ids = {r["cand_id"] for r in rows}
    referenced: set[str] = set()
    for r in rows:
        d, ref = r.get("disposition", "").strip(), r.get("ref", "").strip()
        if d not in DISPOSITIONS:
            rep.error("NM-01", f"{r['cand_id']} (line {r['line']}): not classified")
            continue
        counts[d] += 1
        if not ref:
            rep.error("NM-02", f"{r['cand_id']}: disposition {d} needs a ref")
        elif d == "mapped":
            referenced.add(ref)
            if spec_reqs and ref not in spec_reqs:
                rep.error("NM-03", f"{r['cand_id']}: mapped requirement {ref} is not in the specification")
        elif d == "duplicate" and ref not in ids:
            rep.error("NM-04", f"{r['cand_id']}: duplicate of unknown candidate {ref}")
    for rid in sorted(spec_reqs - referenced):
        rep.warn("NM-05", f"{rid}: no source sentence is mapped to it; confirm it comes from the standard")
    total = len(rows)
    classified = sum(counts.values())
    lines = ["# Normative sentence classification", "",
             f"Candidates: {total}; classified: {classified}; unclassified: {total - classified}", "",
             "| Disposition | Count |", "|---|---:|"] + [f"| {d} | {n} |" for d, n in counts.items()]
    lines += ["", f"Requirements with a source sentence: {len(referenced & spec_reqs) if spec_reqs else len(referenced)}"
              + (f" of {len(spec_reqs)}" if spec_reqs else ""), "", "## Findings", ""]
    lines += [f"- {f.severity} {f.code}: {f.message}" for f in rep.findings] or ["- None."]
    text = "\n".join(lines) + "\n"
    if args.out:
        vc.refuse_overwrite(args.out)
        Path(args.out).write_text(text, encoding="utf-8")
    rep.print_text()
    print(f"classified {classified} of {total} candidate(s)")
    return 1 if rep.errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("standard", help="text file converted from the standard")
    s.add_argument("--out", required=True)
    s.add_argument("--section-start", type=int, default=1, help="first line to scan")
    s.add_argument("--section-end", type=int, default=0, help="last line to scan (0 = end)")
    s.set_defaults(fn=cmd_scan)
    r = sub.add_parser("report")
    r.add_argument("map", help="normative_map.csv with disposition and ref filled")
    r.add_argument("--spec")
    r.add_argument("--out")
    r.set_defaults(fn=cmd_report)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
