#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Update the qualification evidence from logs.

results   parse the logs listed in run_summary.json and set each trace to PASS or FAIL
item      set the lint, compile, or coverage evidence from a log file

Rules (VQUA-08): an entry becomes PASS only when every required seed has a
log that contains a VLSIT_VIP_QUAL_RESULT line with status=PASS, the UVM
summary shows no UVM_ERROR and no UVM_FATAL, and the run exited with code 0.
A log without a result line is FAIL. An entry without any log stays NOT_RUN.
The evidence file is updated in place and every change is recorded in `history`.

Usage:
    python collect_qual_results.py results --evidence qual_evidence.json --summary logs/run_summary.json --min-seeds 3
    python collect_qual_results.py item --evidence qual_evidence.json --item lint --status PASS --log logs/lint.log
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402

RESULT_RE = re.compile(
    r"VLSIT_VIP_QUAL_RESULT\s+test=(?P<test>\S+)\s+seed=(?P<seed>\d+)\s+status=(?P<status>PASS|FAIL)"
    r"\s+expected=(?P<expected>\d+)\s+unexpected=(?P<unexpected>\d+)\s+missing=(?P<missing>\d+)")
UVM_ERR_RE = re.compile(r"^UVM_ERROR\s*:\s*(\d+)", re.M)
UVM_FATAL_RE = re.compile(r"^UVM_FATAL\s*:\s*(\d+)", re.M)


def save(path: Path, ev: dict) -> None:
    path.write_text(json.dumps(ev, indent=2) + "\n", encoding="utf-8")


def judge_log(path: Path, test: str, rc: int) -> tuple[str, str]:
    """Return (PASS|FAIL, note) for one run log."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if rc != 0:
        return "FAIL", f"simulator exit code {rc}"
    m = next((x for x in RESULT_RE.finditer(text) if x.group("test") == test), None)
    if m is None:
        return "FAIL", "no VLSIT_VIP_QUAL_RESULT line for this test"
    if m.group("status") != "PASS":
        return "FAIL", f"result line reports FAIL (unexpected={m.group('unexpected')}, missing={m.group('missing')})"
    for rx, name in ((UVM_ERR_RE, "UVM_ERROR"), (UVM_FATAL_RE, "UVM_FATAL")):
        s = rx.search(text)
        if s is None:
            return "FAIL", "UVM report summary not found in the log"
        if int(s.group(1)) != 0:
            return "FAIL", f"{name} count is {s.group(1)}"
    return "PASS", ""


def cmd_results(a: argparse.Namespace) -> int:
    ev_path = Path(a.evidence)
    ev = json.loads(ev_path.read_text(encoding="utf-8"))
    summ_path = Path(a.summary)
    summ = json.loads(summ_path.read_text(encoding="utf-8"))
    log_dir = summ_path.parent
    by_key: dict[tuple[str, str], list[dict]] = {}
    for r in summ["runs"]:
        if r["kind"] == "run":
            by_key.setdefault((r["test"], r["variant"]), []).append(r)
    changed = 0
    for e in ev["entries"]:
        runs = by_key.get((e["test"], e["variant"]), [])
        if not runs:
            continue
        verdicts, logs, seeds, notes = [], [], [], []
        for r in runs:
            p = log_dir / r["log"]
            if not p.is_file():
                verdicts.append("FAIL")
                notes.append(f"seed {r['seed']}: log missing")
                continue
            v, note = judge_log(p, e["test"], r["rc"])
            verdicts.append(v)
            logs.append(r["log"])
            seeds.append(r["seed"])
            if note:
                notes.append(f"seed {r['seed']}: {note}")
        status = "PASS" if all(v == "PASS" for v in verdicts) and len(set(seeds)) >= a.min_seeds else "FAIL"
        if status == "FAIL" and all(v == "PASS" for v in verdicts):
            notes.append(f"only {len(set(seeds))} seed(s), {a.min_seeds} required")
        new = {"status": status, "seeds": sorted(set(seeds)), "log": ";".join(logs), "note": "; ".join(notes)}
        if any(e.get(k) != v for k, v in new.items()):
            e.update(new)
            changed += 1
    ev.setdefault("history", []).append({"time": vc.now_iso(), "event": "results",
                                          "detail": f"{changed} entr(ies) updated from {summ_path.name}"})
    save(ev_path, ev)
    counts = {}
    for e in ev["entries"]:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    print(f"{changed} entr(ies) updated; totals: {counts}")
    return 0


def cmd_item(a: argparse.Namespace) -> int:
    ev_path = Path(a.evidence)
    ev = json.loads(ev_path.read_text(encoding="utf-8"))
    if a.status == "PASS" and (not a.log or not Path(a.log).is_file()):
        raise SystemExit("error: PASS needs an existing --log file (VQUA-08)")
    item = ev[a.item]
    item.update({"status": a.status, "log": a.log or "", "note": a.note})
    if a.item == "coverage":
        item["database"], item["summary"] = a.database, a.summary
    ev.setdefault("history", []).append({"time": vc.now_iso(), "event": f"item_{a.item}", "detail": a.status})
    save(ev_path, ev)
    print(f"{a.item}: {a.status}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("results")
    r.add_argument("--evidence", required=True)
    r.add_argument("--summary", required=True)
    r.add_argument("--min-seeds", type=int, default=1)
    r.set_defaults(fn=cmd_results)
    i = sub.add_parser("item")
    i.add_argument("--evidence", required=True)
    i.add_argument("--item", required=True, choices=["lint", "compile", "coverage"])
    i.add_argument("--status", required=True, choices=["PASS", "FAIL", "NOT_RUN"])
    i.add_argument("--log", default="")
    i.add_argument("--note", default="")
    i.add_argument("--database", default="")
    i.add_argument("--summary", default="")
    i.set_defaults(fn=cmd_item)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
