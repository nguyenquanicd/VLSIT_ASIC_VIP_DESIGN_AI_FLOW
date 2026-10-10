#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Create the qualification evidence matrix (schema vlsit_vip_qual_evidence/1).

Every trace of every applicable requirement on every variant of the selected
profile starts as NOT_RUN. Only collect_qual_results.py moves an entry to
PASS or FAIL, and only from logs.

Usage:
    python create_qual_matrix.py --requirements requirements.csv --spec SPEC.md \
        --profile PROF-01 --vip vip_name --out qual_evidence.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402
import trace_lint as tl  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--requirements", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--vip", required=True, help="VIP name, for example apb_vip")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    vc.refuse_overwrite(args.out)

    spec = vc.load_spec(args.spec)
    rows = vc.read_csv(args.requirements)
    variants = [v["variant_id"] for v in spec.rows("variants") if v["profile"] == args.profile]
    if not variants:
        raise SystemExit(f"error: no variant of profile {args.profile} in the specification")
    entries = []
    for r in rows:
        if r["status"] == "withdrawn" or not tl.req_applies(r["profile"], args.profile):
            continue
        for test, kind in ((r["test_pos"], "pos"), (r["test_neg"], "neg")):
            if test in ("-", ""):
                continue
            if test.endswith("_cap"):
                kind = "cap"
            for v in variants:
                entries.append({"test": test, "variant": v, "kind": kind, "req_id": r["req_id"],
                                "chk_id": r["chk_id"] if r["chk_id"] != "-" else "",
                                "status": "NOT_RUN", "seeds": [], "log": "", "note": ""})
    # a capability test can be shared by several requirements; keep one entry per (test, variant)
    seen, unique = set(), []
    for e in entries:
        k = (e["test"], e["variant"])
        if k not in seen:
            seen.add(k)
            unique.append(e)
    ev = {"schema": "vlsit_vip_qual_evidence/1", "vip": args.vip, "profile": args.profile,
          "spec_rev": spec.front.get("spec_revision_locked", ""), "created": vc.now_iso(), "variants": variants,
          "lint": {"status": "NOT_RUN", "log": "", "note": ""},
          "compile": {"status": "NOT_RUN", "log": "", "note": ""},
          "coverage": {"status": "NOT_RUN", "database": "", "summary": "", "log": "", "note": ""},
          "entries": unique, "history": [{"time": vc.now_iso(), "event": "created", "detail": f"{len(unique)} entries"}]}
    vc.write_json(args.out, ev)
    print(f"wrote {args.out}: {len(unique)} entries for {len(variants)} variant(s), all NOT_RUN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
