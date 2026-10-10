#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bug log of a VIP fix run, with gated status transitions.

The log is a CSV file (00_change/bug_log.csv). A bug moves through
    open -> analyzed -> planned -> fixed -> verified -> closed        (or wontfix, duplicate)
and a transition is refused unless its evidence exists:
    analyzed   a defect class (vip, spec, trace, counterpart, environment, dut)
    planned    the affected requirements or files are named
    fixed      a regression test is named (test first: it must fail before the fix)
    verified   an evidence log or report file exists
    closed     the regression test file exists in the VIP tree, and the status is verified

Commands:
    new    --title T --symptom S --severity critical|major|minor [--found-in VER] [--req IDS] [--evidence F]
    list   [--status S]
    show   BUG-nnn
    set    BUG-nnn key=value ...   keys: status class req_ids files regression_test fix_summary evidence_log severity
    report                         markdown summary for the release notes
Common: --log FILE (default 00_change/bug_log.csv) --vip-dir DIR (to check regression tests)
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402

COLUMNS = ["bug_id", "title", "symptom", "severity", "status", "class", "found_in", "req_ids", "files",
           "regression_test", "fix_summary", "evidence_log", "reported", "updated"]
STATUS = ["open", "analyzed", "planned", "fixed", "verified", "closed", "wontfix", "duplicate"]
CLASSES = ["vip", "spec", "trace", "counterpart", "environment", "dut", "unknown"]
SEVERITY = ["critical", "major", "minor"]


def load(path: Path) -> list[dict]:
    return vc.read_csv(path) if path.is_file() else []


def save(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    vc.write_csv(path, rows, COLUMNS)


def find(rows: list[dict], bid: str) -> dict:
    for r in rows:
        if r["bug_id"] == bid:
            return r
    raise SystemExit(f"error: no bug {bid}")


def check_transition(row: dict, new: dict, base: Path, vip: Path | None) -> None:
    st = new["status"]
    if st not in STATUS:
        raise SystemExit(f"error: status must be one of {STATUS}")
    cur, cls = STATUS.index(row["status"]), STATUS.index(st)
    if st in ("open", "wontfix", "duplicate"):
        return
    if cls > cur + 1 and st != "closed":
        raise SystemExit(f"error: {row['bug_id']} is {row['status']}; move to {STATUS[cur + 1]} first")
    if st == "analyzed" and new["class"] in ("", "unknown"):
        raise SystemExit("error: classify the defect first (class=vip|spec|trace|counterpart|environment|dut)")
    if st == "planned" and not (new["req_ids"].strip() or new["files"].strip()):
        raise SystemExit("error: name the affected requirements (req_ids) or files before planning the fix")
    if st == "fixed" and not new["regression_test"].strip():
        raise SystemExit("error: name the regression test (regression_test=qual_...); it is written before the fix and must fail without it")
    if st == "verified":
        ev = new["evidence_log"].strip()
        if not ev or not (base / ev).is_file():
            raise SystemExit("error: verified needs evidence_log=<file> that exists (the log of the regression run)")
    if st == "closed":
        if row["status"] != "verified":
            raise SystemExit("error: only a verified bug can be closed")
        t = new["regression_test"].strip()
        if vip is not None and not (vip / "qual" / "tests" / f"{t}.sv").is_file() and not list(vip.rglob(f"{t}*")):
            raise SystemExit(f"error: regression test {t} is not in {vip}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default="00_change/bug_log.csv")
    ap.add_argument("--vip-dir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--title", required=True)
    n.add_argument("--symptom", required=True)
    n.add_argument("--severity", required=True, choices=SEVERITY)
    n.add_argument("--found-in", default="")
    n.add_argument("--req", default="")
    n.add_argument("--evidence", default="")
    ls = sub.add_parser("list")
    ls.add_argument("--status")
    sh = sub.add_parser("show")
    sh.add_argument("bug_id")
    st = sub.add_parser("set")
    st.add_argument("bug_id")
    st.add_argument("pairs", nargs="+")
    sub.add_parser("report")
    a = ap.parse_args()
    log = Path(a.log)
    base = log.parent.parent
    rows = load(log)
    vip = Path(a.vip_dir) if a.vip_dir else None
    now = vc.now_iso()
    if a.cmd == "new":
        bid = f"BUG-{len(rows) + 1:03d}"
        rows.append({"bug_id": bid, "title": a.title, "symptom": a.symptom, "severity": a.severity, "status": "open", "class": "unknown",
                     "found_in": a.found_in, "req_ids": a.req, "files": "", "regression_test": "", "fix_summary": "",
                     "evidence_log": a.evidence, "reported": now, "updated": now})
        save(log, rows)
        print(bid)
        return 0
    if a.cmd == "list":
        sel = [r for r in rows if not a.status or r["status"] == a.status]
        for r in sel:
            print(f"{r['bug_id']}\t{r['severity']}\t{r['status']}\t{r['class']}\t{r['title']}")
        print(f"{len(sel)} of {len(rows)} bug(s)")
        return 0
    if a.cmd == "show":
        for k, v in find(rows, a.bug_id).items():
            if v:
                print(f"{k}\t{v}")
        return 0
    if a.cmd == "report":
        by: dict[str, int] = {}
        for r in rows:
            by[r["status"]] = by.get(r["status"], 0) + 1
        print("| Bug | Severity | Class | Status | Requirements | Regression test | Fix |")
        print("|---|---|---|---|---|---|---|")
        for r in rows:
            print(f"| {r['bug_id']} {r['title']} | {r['severity']} | {r['class']} | {r['status']} | {r['req_ids'] or '-'} | {r['regression_test'] or '-'} | {r['fix_summary'] or '-'} |")
        print("\nby status: " + ", ".join(f"{k} {v}" for k, v in by.items()))
        return 0
    row = find(rows, a.bug_id)
    new = dict(row)
    for p in a.pairs:
        k, sep, v = p.partition("=")
        if not sep or k not in ("status", "class", "req_ids", "files", "regression_test", "fix_summary", "evidence_log", "severity"):
            raise SystemExit("error: use key=value; keys: status class req_ids files regression_test fix_summary evidence_log severity")
        if k == "class" and v not in CLASSES:
            raise SystemExit(f"error: class must be one of {CLASSES}")
        if k == "severity" and v not in SEVERITY:
            raise SystemExit(f"error: severity must be one of {SEVERITY}")
        new[k] = v
    if new["status"] != row["status"]:
        check_transition(row, new, base, vip)
    new["updated"] = now
    row.update(new)
    save(log, rows)
    print(f"{row['bug_id']} {row['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
