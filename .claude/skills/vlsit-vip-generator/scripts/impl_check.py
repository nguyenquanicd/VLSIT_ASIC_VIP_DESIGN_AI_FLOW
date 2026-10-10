#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Complete one (or many) SVA check stub in a generated checker from an expression.

The same expression form as Section 8.1 of the specification: single-cycle boolean
expressions, operator SAME (|->) or NEXT (|=>), OR for ||. The tool validates the
identifiers against the VIP signals, replaces the stub, removes the stub markers, keeps
the requirement and coverage-ID comments, and prints the Section 8.1 row to add to the
specification so the specification and the code stay in step.

Usage:
    python impl_check.py --vip-dir DIR/<tag>_vip --id <CHECK_ID> --op SAME|NEXT --ante "..." --cons "..." --msg "..."
    python impl_check.py --vip-dir DIR/<tag>_vip --from-csv checks.csv     # columns: id,op,ante,cons,msg
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_vip_skeleton as gen  # noqa: E402
import vip_common as vc  # noqa: E402


def implement(vip: Path, cfg: dict, cid: str, op: str, ante: str, cons: str, msg: str) -> str:
    ck = next((c for c in cfg["checks"] if c["id"] == cid), None)
    if ck is None or ck["type"] != "SVA":
        raise SystemExit(f"error: {cid} is not an SVA check of this VIP")
    if op not in vc.CHECK_OPS:
        raise SystemExit(f"error: operator must be one of {list(vc.CHECK_OPS)}")
    allowed = {s["name"] for s in cfg["signals"]} | {p["name"] for p in cfg["parameters"]}
    for label, text in (("antecedent", ante), ("consequent", cons)):
        idents, problems = vc.expr_identifiers(text)
        if problems or idents - allowed:
            raise SystemExit(f"error: {label}: " + "; ".join(problems + [f"unknown identifier {i}" for i in sorted(idents - allowed)]))
    path = vip / "rtl_if" / f"{cfg['tag']}_checker.sv"
    lines = path.read_text(encoding="utf-8").split("\n")
    stub = next((i for i, ln in enumerate(lines) if ln.startswith(f"  `VLSIT_VIP_CHK_TODO({cid},")), None)
    if stub is None:
        raise SystemExit(f"error: no stub for {cid} in {path.name}; it is already implemented")
    start = stub
    while start > 0 and lines[start - 1].startswith("  //"):
        start -= 1
    keep = []
    for ln in lines[start:stub]:
        if f"VIP_TODO({cid})" in ln:
            break
        if "Coverage ID" in ln:
            ln = ln.split(" VIP_TODO(")[0]
        keep.append(ln)
    macro = "VLSIT_VIP_CHK_REC" if ck["is_rec"] else "VLSIT_VIP_CHK_ERR"
    ck = dict(ck, expr={"op": vc.CHECK_OPS[op], "ante": vc.translate_expr(ante), "cons": vc.translate_expr(cons), "msg": msg})
    block = keep + [gen.emit_check(ck, macro)]
    lines[start:stub + 1] = block
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    row = f"| {ck['req_id']} | {op} | {ante.replace('||', 'OR')} | {cons.replace('||', 'OR')} | {msg} |"
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vip-dir", required=True)
    ap.add_argument("--id")
    ap.add_argument("--op")
    ap.add_argument("--ante")
    ap.add_argument("--cons")
    ap.add_argument("--msg")
    ap.add_argument("--from-csv")
    a = ap.parse_args()
    vip = Path(a.vip_dir)
    cfg = json.loads((vip / "spec" / "vip_config.json").read_text(encoding="utf-8"))
    jobs = []
    if a.from_csv:
        jobs = [(r["id"], r["op"], r["ante"], r["cons"], r["msg"]) for r in csv.DictReader(open(a.from_csv, encoding="utf-8"))]
    elif a.id and a.op and a.ante and a.cons and a.msg:
        jobs = [(a.id, a.op, a.ante, a.cons, a.msg)]
    else:
        ap.error("give --id --op --ante --cons --msg, or --from-csv")
    rows = [implement(vip, cfg, *j) for j in jobs]
    print(f"implemented {len(rows)} check(s). Add to specification Section 8.1:")
    print("\n".join(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
