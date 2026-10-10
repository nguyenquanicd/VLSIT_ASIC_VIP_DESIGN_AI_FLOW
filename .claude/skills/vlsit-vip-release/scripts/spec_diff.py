#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare the requirements of two specification revisions and list what must be re-qualified.

Each side is a requirements.csv or a VIP specification markdown. IDs are permanent
(VNAM-03): a requirement that disappears is reported as REMOVED and must be marked
`withdrawn` instead of being deleted.

Usage:
    python spec_diff.py --old OLD --new NEW --out spec_diff.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402

COMPARE = ["strength", "role", "kind", "text", "spec_ref", "profile", "signals", "rule_key", "check_type",
           "chk_id", "bound_refs"]
# changes in these fields alter the check or its traces, not just the wording
BEHAVIOR = {"strength", "role", "kind", "check_type", "chk_id", "bound_refs", "signals", "rule_key", "profile"}


def load(path: str) -> dict[str, dict]:
    if path.lower().endswith(".csv"):
        rows = vc.read_csv(path)
    else:
        spec = vc.load_spec(path)
        rows = vc.spec_requirements(spec)
        for r in rows:  # resolve the derived check ID so both sides are comparable
            if r["check_type"] in ("SVA", "CLASS") and r["chk_id"].strip().lower() in ("auto", ""):
                r["chk_id"] = vc.derive_check_id(spec.tag, r["strength"], r["role"], r["signals"], r["rule_key"])
            elif r["check_type"] not in ("SVA", "CLASS"):
                r["chk_id"] = "-"
    return {r["req_id"]: r for r in rows}


def norm(field: str, v: str) -> str:
    v = (v or "").strip()
    if field == "chk_id" and v.lower() in ("auto", ""):
        return "-"
    return v


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    vc.refuse_overwrite(args.out)
    old, new = load(args.old), load(args.new)
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = []
    for rid in sorted(set(old) & set(new)):
        diffs = [(f, norm(f, old[rid].get(f)), norm(f, new[rid].get(f))) for f in COMPARE
                 if norm(f, old[rid].get(f)) != norm(f, new[rid].get(f))]
        if diffs:
            changed.append((rid, diffs))
    L = ["# Specification diff", "", f"Old: `{args.old}`", f"New: `{args.new}`", f"Generated: {vc.now_iso()}", "",
         f"- Added: {len(added)}", f"- Removed: {len(removed)}", f"- Changed: {len(changed)}",
         f"- Unchanged: {len(set(old) & set(new)) - len(changed)}", ""]
    L += ["## Added requirements", "", "Run S1 to S5 for each: new check, coverage, injection, and traces.", ""]
    L += [f"- {r}: {new[r]['text']}" for r in added] or ["- None."]
    L += ["", "## Removed requirements", "",
          "IDs are permanent. Keep the row with status `withdrawn` instead of deleting it (VNAM-03).", ""]
    L += [f"- {r}: {old[r]['text']}" for r in removed] or ["- None."]
    L += ["", "## Changed requirements", ""]
    if changed:
        L += ["| Requirement | Field | Old | New | Impact |", "|---|---|---|---|---|"]
        for rid, diffs in changed:
            for f, o, n in diffs:
                impact = "re-plan, re-implement the check, re-qualify" if f in BEHAVIOR else "review wording and spec reference"
                L.append(f"| {rid} | {f} | {o} | {n} | {impact} |")
    else:
        L.append("- None.")
    L += ["", "## Re-qualification scope", ""]
    scope = sorted(set(added) | {rid for rid, d in changed if any(f in BEHAVIOR for f, _, _ in d)})
    L += [f"- {r}" for r in scope] or ["- No behavior change; review the changed wording only."]
    Path(args.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"added {len(added)}, removed {len(removed)}, changed {len(changed)}; re-qualification scope {len(scope)}")
    return 1 if removed else 0


if __name__ == "__main__":
    sys.exit(main())
