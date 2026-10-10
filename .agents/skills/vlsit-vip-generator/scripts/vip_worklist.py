#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""List the stubs that remain in a generated VIP, with the context needed to finish each one.

An agent that follows this list opens only the named file regions instead of reading the
generated tree. Items are ordered: checks, monitor, drivers, sequences, coverage, qualification
traces. Each item is one line; --show prints the code region of the first selected item.

Usage:
    python vip_worklist.py --vip-dir DIR/<tag>_vip [--kind check|mon|drv|seq|cov|test|other] [--n 5] [--show]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ORDER = ["check", "mon", "drv", "seq", "cov", "test", "other"]
MARK = re.compile(r"VIP_TODO\(\s*([A-Za-z0-9_\-]+)\s*\)|`VLSIT_VIP_CHK_TODO\(\s*([A-Za-z0-9_]+)")


def classify(i: str, checks: set[str], tag: str) -> str:
    if i in checks:
        return "check"
    if i.startswith("MON-"):
        return "mon"
    if i.startswith(f"{tag}_driver"):
        return "drv"
    if i.startswith(("CAP-", "SEQ-")):
        return "seq"
    if i.startswith("COV_"):
        return "cov"
    if i.startswith("qual_"):
        return "test"
    return "other"


def context(i: str, kind: str, cfg: dict, reqs: dict) -> str:
    if kind == "check":
        c = next(x for x in cfg["checks"] if x["id"] == i)
        return f"{c['req_id']} {c['strength']} role {c['role']} signals {','.join(c['signals'])}: {c['text']} [{c['spec_ref']}]"
    if kind == "cov":
        cv = next((x for x in cfg["coverage"] if x["id"] == i), None)
        if cv:
            b = next((x for x in cfg["bounds"] if x["id"] == cv["bound"]), None) if cv["bound"] else None
            return (f"{cv['req_id']} ({cv['kind']}): " + (f"bins of {b['quantity']} valid {b['valid_min']}..{b['valid_max']}"
                    f" invalid {b['invalid_below']}/{b['invalid_above']}" if b else "scenario seen at least once"))
    if kind == "seq":
        cp = next((x for x in cfg["caps"] if x["id"] == i), None)
        if cp:
            return f"{cp['capability']} (role {cp['role']}, knobs {','.join(cp['knobs']) or 'none'}, requirements {','.join(cp['requirements'])})"
        sq = next((x for x in cfg["sequences"] if x["id"] == i), None)
        return sq["purpose"] if sq else ""
    if kind == "test":
        t = next((x for x in cfg["tests"] if x["name"] == i), None)
        if t and t["kind"] == "neg":
            inj = next((x for x in cfg["injections"] if x["requirement"] == t["req_id"]), None)
            return f"counterpart stimulus: exactly one violation for {t['check']}" + (f" ({inj['id']}: {inj['violation']})" if inj else "")
        if t and t["kind"] == "pos":
            return f"counterpart stimulus: legal traffic at the valid boundary of {t['check']}"
        return f"counterpart stimulus: capability of {t['req_id']}" if t else ""
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vip-dir", required=True)
    ap.add_argument("--kind", choices=ORDER)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--show", action="store_true", help="print the code region of the first selected item")
    a = ap.parse_args()
    vip = Path(a.vip_dir)
    cfg = json.loads((vip / "spec" / "vip_config.json").read_text(encoding="utf-8"))
    tag = cfg["tag"]
    checks = {c["id"] for c in cfg["checks"]}
    items: dict[str, tuple[str, Path, int]] = {}
    for f in sorted(vip.rglob("*")):
        if f.is_file() and f.suffix in (".sv", ".svh") and "base" not in f.relative_to(vip).parts[:1]:
            for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                for m in MARK.finditer(line):
                    i = m.group(1) or m.group(2)
                    items.setdefault(i, (classify(i, checks, tag), f, n))
    rows = [(k, i, f, n) for i, (k, f, n) in items.items() if not a.kind or k == a.kind]
    rows.sort(key=lambda r: (ORDER.index(r[0]), r[1]))
    total = len(rows)
    print(f"{total} stub(s) remain" + (f" of kind {a.kind}" if a.kind else "") + "; by kind: "
          + ", ".join(f"{k} {sum(1 for r in rows if r[0] == k)}" for k in ORDER if any(r[0] == k for r in rows)))
    for k, i, f, n in rows[:a.n]:
        ctx = context(i, k, cfg, {})
        print(f"{k:5s} {i}  {f.relative_to(vip).as_posix()}:{n}" + (f"  | {ctx[:170]}" if ctx else ""))
    if total > a.n:
        print(f"... {total - a.n} more (raise --n or filter with --kind)")
    if a.show and rows:
        k, i, f, n = rows[0]
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        lo, hi = max(0, n - 4), min(len(lines), n + 14)
        print(f"--- {f.relative_to(vip).as_posix()} lines {lo + 1}-{hi} ---")
        print("\n".join(f"{x + 1:4d} {lines[x]}" for x in range(lo, hi)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
