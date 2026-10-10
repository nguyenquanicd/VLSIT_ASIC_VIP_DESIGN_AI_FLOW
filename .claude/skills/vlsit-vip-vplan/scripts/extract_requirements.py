#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Derive the VIP verification plan from a validated VIP specification.

Reads the machine-readable tables of the specification, assigns the check,
coverage, injection, sequence, and test IDs, and writes:

    requirements.csv        one row per requirement with every trace ID
    traceability.csv        compact requirement-to-test view
    traceability_table.md   the body of specification Section 13
    vplan.md                human-readable verification plan
    plan_report.json        counts and gaps

The specification must pass validate_vip_spec.py first. Output files are new;
existing files are never overwritten.

Usage:
    python extract_requirements.py SPEC.md --out-dir DIR
        [--status draft|reviewed] [--reviewer NAME] [--update-spec NEW_SPEC.md]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402
import validate_vip_spec as vv  # noqa: E402


def build_plan(spec: vc.Spec, status: str, reviewer: str) -> list[dict]:
    tag = spec.tag
    rows = vc.spec_requirements(spec)
    caps = spec.rows("caps")
    injs = spec.rows("injections")
    for r in rows:
        r["status"], r["reviewer"] = status, reviewer
        num = vc.req_number(r["req_id"])
        if r["check_type"] in ("SVA", "CLASS"):
            cid = r["chk_id"].strip()
            if cid.lower() in ("auto", ""):
                cid = vc.derive_check_id(tag, r["strength"], r["role"], r["signals"], r["rule_key"])
            r["chk_id"] = cid
            r["test_pos"], r["test_neg"] = vc.tests_for(cid)
        else:
            r["chk_id"] = "-"
            r["test_pos"], r["test_neg"] = "-", "-"
        r["cov_id"] = f"COV_{tag.upper()}_{num}" if r["check_type"] != "NONE" else "-"
        r["inj_id"] = ";".join(i["inj_id"] for i in injs if i["violated_requirement"] == r["req_id"]) or "-"
        my_caps = [c for c in caps if r["req_id"] in vc.split_list(c["requirements"])]
        r["seq_id"] = ";".join(c["sequence"] for c in my_caps) or "-"
        if r["check_type"] in ("COV", "NONE") and my_caps:
            r["test_pos"] = vc.cap_test(my_caps[0]["cap_id"])
        if not r["bound_refs"].strip():
            r["bound_refs"] = "-"
    return rows


def trace_table(rows: list[dict]) -> list[str]:
    out = []
    for r in rows:
        seqinj = "; ".join(x for x in (r["seq_id"], r["inj_id"]) if x != "-") or "-"
        pos = r["test_pos"]
        neg = r["test_neg"]
        out.append(f"| {r['req_id']} | {r['chk_id']} | {r['cov_id']} | {seqinj} | {pos} | {neg} | {r['status']} |")
    return out


def write_vplan(path: Path, spec: vc.Spec, rows: list[dict], gaps: list[str]) -> None:
    tag = spec.tag.upper()
    cnt = Counter((r["strength"], r["check_type"]) for r in rows)
    checks = [r for r in rows if r["check_type"] in ("SVA", "CLASS")]
    L: list[str] = []
    L += [f"# {spec.front.get('title', tag + ' VIP')} - verification plan", "",
          f"Generated {vc.now_iso()} from `{spec.path.name}` (spec version {spec.front.get('version')},",
          f"locked revision {spec.front.get('spec_revision_locked')}). Status: draft until Gate 1 and Gate 2 approvals.", "",
          "## 1. Summary", "",
          f"- Requirements: {len(rows)}",
          f"- Checks: {len(checks)} (SVA {sum(1 for r in checks if r['check_type'] == 'SVA')}, "
          f"CLASS {sum(1 for r in checks if r['check_type'] == 'CLASS')})",
          f"- Qualification traces: {2 * len(checks)} per variant (one positive and one negative per check)",
          f"- Capability tests: {len({r['test_pos'] for r in rows if r['test_pos'].endswith('_cap')})} per variant",
          f"- Variants: {len(spec.rows('variants'))}", ""]
    L += ["| Strength | Check type | Count |", "|---|---|---:|"]
    for (s, c), n in sorted(cnt.items()):
        L.append(f"| {s} | {c} | {n} |")
    L += ["", "## 2. Checks", "",
          "| Check ID | Requirement | Strength | Role | Type | Positive trace | Negative trace | Injection |",
          "|---|---|---|---|---|---|---|---|"]
    for r in checks:
        L.append(f"| {r['chk_id']} | {r['req_id']} | {r['strength']} | {r['role']} | {r['check_type']} | "
                 f"{r['test_pos']} | {r['test_neg']} | {r['inj_id']} |")
    L += ["", "## 3. Coverage items", "",
          "| Coverage ID | Requirement | Kind | Source |", "|---|---|---|---|"]
    for r in rows:
        if r["cov_id"] != "-":
            src = "boundary bins" if r["bound_refs"] != "-" else ("capability" if r["kind"] == "CAP" else "check antecedent")
            L.append(f"| {r['cov_id']} | {r['req_id']} | {r['kind']} | {src} |")
    L += ["", "### 3.1 Boundary bins", "",
          "| Bound ID | Quantity | Valid bins | Invalid bins | Source requirement |", "|---|---|---|---|---|"]
    for b in spec.rows("boundaries"):
        valid = f"{b['valid_min']} to {b['valid_max']}"
        inv = ", ".join(x for x in (b["invalid_below"], b["invalid_above"]) if x.strip() != "-") or "none"
        L.append(f"| {b['bound_id']} | {b['quantity']} | {valid} {b['unit']} | {inv} | {b['source_req']} |")
    L += ["", "## 4. Capabilities and sequences", "",
          "| Cap ID | Role | Capability | Sequence | Test | Requirements |", "|---|---|---|---|---|---|"]
    for c in spec.rows("caps"):
        L.append(f"| {c['cap_id']} | {c['role']} | {c['capability']} | {c['sequence']} | {vc.cap_test(c['cap_id'])} | {c['requirements']} |")
    L += ["", "## 5. Error injections", "",
          "| Injection | Role | Violated requirement | Expected check |", "|---|---|---|---|"]
    chk_of = {r["req_id"]: r["chk_id"] for r in rows}
    for i in spec.rows("injections"):
        exp = chk_of.get(i["violated_requirement"], "-") if i["expected_check"].lower() == "auto" else i["expected_check"]
        L.append(f"| {i['inj_id']} | {i['role']} | {i['violated_requirement']} | {exp} |")
    L += ["", "## 6. Plan gaps", ""]
    L += [f"- {g}" for g in gaps] if gaps else ["- None found."]
    L += ["", "## 7. Open decisions", ""]
    opens = [d for d in spec.rows("decisions") if d["type"] == "Open" or "open" in d["resolution_status"].lower()]
    L += [f"- {d['decision_id']}: {d['statement']} ({d['resolution_status']})" for d in opens] if opens else ["- None."]
    L += ["", "## 8. Approval", "", "Awaiting user sign-off (Gate 2). No code is generated before approval.", ""]
    path.write_text("\n".join(L), encoding="utf-8")


def plan_gaps(rows: list[dict]) -> list[str]:
    gaps = []
    for r in rows:
        if r["strength"] == "MUST" and r["check_type"] in ("SVA", "CLASS") and r["inj_id"] == "-":
            gaps.append(f"{r['req_id']} ({r['chk_id']}): no injection; the negative trace has no way to produce one violation.")
        if r["kind"] == "CAP" and r["seq_id"] == "-":
            gaps.append(f"{r['req_id']}: capability requirement has no stimulus sequence.")
        if r["check_type"] == "SVA" and r["strength"] == "MUST" and r["bound_refs"] == "-" and r["kind"] in ("SIG", "SEQ"):
            pass  # no numeric boundary needed for pure stability or sequencing rules
    return gaps


def replace_trace_section(spec: vc.Spec, new_rows: list[str], dest: Path) -> None:
    tables = spec.tables_of("trace")
    if not tables:
        raise SystemExit("error: specification has no traceability table to update")
    t = tables[0]
    start = t.line + 1  # zero-based index of the first data row (header at t.line-1, separator at t.line)
    lines = spec.lines[:start] + new_rows + spec.lines[start + len(t.rows):]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out-dir", required=True, help="directory for the plan files (created if absent)")
    ap.add_argument("--status", default="draft", choices=["draft", "reviewed"])
    ap.add_argument("--reviewer", default="", help="reviewer recorded in requirements.csv")
    ap.add_argument("--update-spec", help="write a copy of the spec with Section 13 filled (new file)")
    args = ap.parse_args()

    spec = vc.load_spec(args.spec)
    rep = vv.validate(spec, template=False, strict_inj=False)
    if rep.errors:
        rep.print_text()
        print("error: the specification must validate before planning", file=sys.stderr)
        return 1
    if args.status == "reviewed" and not args.reviewer:
        print("error: --status reviewed requires --reviewer", file=sys.stderr)
        return 1

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {n: out / n for n in ("requirements.csv", "traceability.csv", "traceability_table.md", "vplan.md", "plan_report.json")}
    for p in files.values():
        vc.refuse_overwrite(p)

    rows = build_plan(spec, args.status, args.reviewer)
    gaps = plan_gaps(rows)
    vc.write_csv(files["requirements.csv"], rows, vc.REQ_COLUMNS)
    vc.write_csv(files["traceability.csv"], rows, ["req_id", "chk_id", "cov_id", "seq_id", "inj_id", "test_pos", "test_neg", "status"])
    table_rows = trace_table(rows)
    header = ["| Req ID | Check ID | Cov ID | Sequence / injection | Test pos | Test neg | Status |",
              "|---|---|---|---|---|---|---|"]
    files["traceability_table.md"].write_text("\n".join(header + table_rows) + "\n", encoding="utf-8")
    write_vplan(files["vplan.md"], spec, rows, gaps)
    checks = [r for r in rows if r["check_type"] in ("SVA", "CLASS")]
    vc.write_json(files["plan_report.json"], {
        "spec": str(spec.path), "spec_sha256": vc.sha256_file(spec.path), "generated": vc.now_iso(),
        "requirements": len(rows), "checks": len(checks),
        "traces_per_variant": 2 * len(checks), "variants": len(spec.rows("variants")),
        "gaps": gaps, "warnings": rep.warnings,
    })
    if args.update_spec:
        dest = Path(args.update_spec)
        vc.refuse_overwrite(dest)
        replace_trace_section(spec, table_rows, dest)
    print(f"planned {len(rows)} requirement(s), {len(checks)} check(s); {len(gaps)} gap(s); output in {out}")
    for g in gaps:
        print(f"  gap: {g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
