#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Lint requirement-to-evidence traceability for a VLSIT VIP.

Stages (each includes the checks of the previous one):
    plan     requirements.csv is complete and self-consistent
    impl     the generated VIP sources implement every check; hygiene rules hold
    qual     qualification evidence shows PASS for every trace on every variant
    release  every requirement is qualified or waived, and no stub remains

Usage:
    python trace_lint.py --requirements requirements.csv --stage plan [--spec SPEC.md]
    python trace_lint.py --requirements requirements.csv --stage impl --vip-dir DIR
    python trace_lint.py --requirements requirements.csv --stage qual --vip-dir DIR --spec SPEC.md --evidence qual_evidence.json
    python trace_lint.py ... [--json REPORT.json]

Exit status: 0 when no error is found, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402

STAGES = ["plan", "impl", "qual", "release"]
SRC_SUFFIXES = (".sv", ".svh", ".v", ".vh")


def stage_ge(stage: str, other: str) -> bool:
    return STAGES.index(stage) >= STAGES.index(other)


def lint_plan(rows: list[dict], rep: vc.Report, stage: str) -> None:
    seen_req: set[str] = set()
    seen_chk: dict[str, str] = {}
    for r in rows:
        rid = r["req_id"]
        if not vc.REQ_ID_RE.match(rid):
            rep.error("PL-01", f"{rid}: invalid requirement ID")
        if rid in seen_req:
            rep.error("PL-02", f"{rid}: duplicate requirement ID")
        seen_req.add(rid)
        if r["status"] not in vc.REQ_STATUS:
            rep.error("PL-03", f"{rid}: status '{r['status']}' must be one of {vc.REQ_STATUS}")
        if r["status"] == "withdrawn":
            continue
        ctype = r["check_type"]
        if ctype in ("SVA", "CLASS"):
            cid = r["chk_id"]
            if not vc.CHECK_ID_RE.match(cid):
                rep.error("PL-04", f"{rid}: invalid check ID '{cid}'")
            if cid in seen_chk:
                rep.error("PL-05", f"{rid}: check ID {cid} duplicates {seen_chk[cid]}")
            seen_chk[cid] = rid
            exp_pos, exp_neg = vc.tests_for(cid)
            if r["test_pos"] != exp_pos:
                rep.error("PL-06", f"{rid}: positive test must be {exp_pos}, found '{r['test_pos']}'")
            if r["test_neg"] != exp_neg:
                rep.error("PL-07", f"{rid}: negative test must be {exp_neg}, found '{r['test_neg']}'")
            if r["cov_id"] in ("", "-"):
                rep.error("PL-08", f"{rid}: check has no coverage ID (VCHK-07 needs an antecedent cover)")
            if r["strength"] == "MUST" and r["inj_id"] in ("", "-"):
                rep.error("PL-09", f"{rid}: MUST check has no error injection (VQUA-01)")
            if r["strength"] in ("MUST", "SHOULD") and not r["bound_refs"]:
                rep.error("PL-10", f"{rid}: bound refs must be '-' or BND IDs")
        else:
            if r["chk_id"] not in ("-", ""):
                rep.error("PL-11", f"{rid}: check ID must be '-' for check type {ctype}")
            if r["kind"] == "CAP" and ctype == "COV" and not r["test_pos"].endswith("_cap"):
                rep.error("PL-12", f"{rid}: capability requirement has no capability test")
            if r["kind"] == "CAP" and r["seq_id"] in ("", "-"):
                rep.error("PL-13", f"{rid}: capability requirement has no stimulus sequence")
        if stage != "plan" or r["status"] != "draft":
            pass
    if stage != "plan":
        for r in rows:
            if r["status"] in ("draft",):
                rep.error("PL-14", f"{r['req_id']}: status is still 'draft' at stage {stage}")
            elif r["status"] != "withdrawn" and not r["reviewer"].strip():
                rep.error("PL-15", f"{r['req_id']}: reviewer is not recorded (VQUA-07)")


def read_sources(vip_dir: Path) -> dict[Path, str]:
    out: dict[Path, str] = {}
    for p in sorted(vip_dir.rglob("*")):
        if p.is_file() and p.suffix in SRC_SUFFIXES:
            out[p] = p.read_text(encoding="utf-8", errors="replace")
    return out


def strip_uvm_guarded(text: str) -> str:
    """Remove `ifdef VLSIT_VIP_UVM ... `else/`endif regions (UVM-only code)."""
    out, depth, skip_depth = [], 0, None
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"`ifn?def\b", s):
            depth += 1
            if re.match(r"`ifdef\s+VLSIT_VIP_UVM\b", s) and skip_depth is None:
                skip_depth = depth
                continue
        elif re.match(r"`else\b", s) and skip_depth == depth:
            skip_depth = None
            continue
        elif re.match(r"`endif\b", s):
            if skip_depth == depth:
                skip_depth = None
                depth -= 1
                continue
            depth -= 1
        if skip_depth is None:
            out.append(line)
    return "\n".join(out)


def todo_marker(cid: str) -> re.Pattern:
    """Matches the VIP_TODO(<id>) comment marker and the VLSIT_VIP_CHK_TODO(<id>, ...) stub macro."""
    e = re.escape(cid)
    return re.compile(r"VIP_TODO\(\s*" + e + r"\s*\)|VLSIT_VIP_CHK_TODO\(\s*" + e + r"\s*,")


def lint_impl(rows: list[dict], vip_dir: Path, tag: str, rep: vc.Report, stage: str) -> None:
    if not vip_dir.is_dir():
        rep.error("IM-00", f"VIP directory not found: {vip_dir}")
        return
    srcs = read_sources(vip_dir)
    all_text = "\n".join(srcs.values())
    checker_files = [p for p in srcs if p.parent.name == "rtl_if" and "checker" in p.name]
    checker_text = "\n".join(srcs[p] for p in checker_files)
    uvm_text = "\n".join(t for p, t in srcs.items() if p.parent.parts[-1] in ("uvm", "seq_lib"))
    final = stage in ("qual", "release")
    cfg_path = vip_dir / "spec" / "vip_config.json"
    built = json.loads(cfg_path.read_text(encoding="utf-8")).get("profile", "") if cfg_path.is_file() else ""
    for r in rows:
        if r["status"] == "withdrawn" or (built and not req_applies(r["profile"], built)):
            continue  # a requirement outside the built profile has no check in this build
        cid, ctype = r["chk_id"], r["check_type"]
        if ctype in ("SVA", "CLASS"):
            haystack = checker_text if ctype == "SVA" else uvm_text
            if not re.search(r"\b" + re.escape(cid) + r"\b", haystack):
                rep.error("IM-01", f"{r['req_id']}: check {cid} is absent from the {'checker' if ctype == 'SVA' else 'UVM'} sources")
            elif todo_marker(cid).search(all_text):
                sev = rep.error if (r["strength"] == "MUST" or final) else rep.warn
                sev("IM-02", f"{r['req_id']}: check {cid} is still a stub (VIP_TODO)")
            for t in (r["test_pos"], r["test_neg"]):
                if not (vip_dir / "qual" / "tests" / f"{t}.sv").is_file():
                    rep.error("IM-03", f"{r['req_id']}: test file qual/tests/{t}.sv is missing")
                elif final and todo_marker(t).search(all_text):
                    rep.error("IM-04", f"{r['req_id']}: test {t} is still a stub (VIP_TODO)")
        cov = r["cov_id"]
        if cov not in ("-", ""):
            if not re.search(r"\b" + re.escape(cov) + r"\b", all_text):
                rep.error("IM-05", f"{r['req_id']}: coverage item {cov} is absent from the sources")
            elif todo_marker(cov).search(all_text):
                (rep.error if final else rep.warn)("IM-06", f"{r['req_id']}: coverage item {cov} is still a stub (VIP_TODO)")
    leftover = sorted(set(re.findall(r"VIP_TODO\(\s*([A-Za-z0-9_\-]+)\s*\)", all_text)))
    stub_macros = sorted(set(re.findall(r"`VLSIT_VIP_CHK_TODO\(\s*([A-Za-z0-9_]+)", all_text)))
    leftover = sorted(set(leftover) | set(stub_macros))
    if leftover:
        shown = ", ".join(leftover[:8]) + (f", ... ({len(leftover)} in total)" if len(leftover) > 8 else "")
        (rep.error if final else rep.warn)("IM-09", f"{len(leftover)} VIP_TODO stub(s) remain: {shown}")
    pkg = vip_dir / "uvm" / f"{tag}_vip_pkg.sv"
    if not pkg.is_file():
        rep.error("IM-07", f"package file uvm/{tag}_vip_pkg.sv is missing")
    elif "spec_rev" not in srcs.get(pkg, ""):
        rep.error("IM-08", "package does not record spec_rev (VFIL-06)")
    # hygiene
    for p, t in srcs.items():
        rel = p.relative_to(vip_dir).as_posix()
        if "\t" in t:
            rep.error("HY-01", f"{rel}: tab character found (VFIL-04, VP-16)")
        for n, line in enumerate(t.splitlines(), 1):
            m = re.match(r"^\s*//(.*)$", line)
            if m and len(line.rstrip()) > 100:
                rep.error("HY-02", f"{rel}:{n}: comment line exceeds 100 characters (VCMT-01)")
        in_rtl_if = p.parent.name == "rtl_if"
        in_uvm = p.parent.name in ("uvm", "seq_lib", "base")
        if in_rtl_if and re.search(r"\buvm_|`uvm_", strip_uvm_guarded(t)):
            rep.error("HY-03", f"{rel}: UVM reference outside a VLSIT_VIP_UVM guard (VIFC-08)")
        if in_uvm:
            for pat, code, msg in (
                (r"\$display\b|\$write\b|\$finish\b", "HY-04", "$display/$write/$finish in UVM code (VP-01)"),
                (r"\buvm_top\s*\.\s*find|\buvm_root::get\(\)\.find", "HY-05", "uvm_top.find (VP-04)"),
                (r"\buvm_callback\b|`uvm_register_cb|`uvm_do_callbacks", "HY-06", "callback extension (VP-03)"),
                (r"\$random\b", "HY-07", "$random (VP-13)"),
                (r"\bforce\b|\brelease\b", "HY-08", "force/release (VP-12)"),
            ):
                code_lines = "\n".join(l for l in t.splitlines() if not l.strip().startswith("//"))
                if re.search(pat, code_lines):
                    rep.error(code, f"{rel}: {msg}")


def req_applies(profile_cell: str, built_profile: str) -> bool:
    toks = vc.split_list(profile_cell)
    return not toks or any(t.lower() == "all" or t == built_profile for t in toks)


def lint_qual(rows: list[dict], evidences: list[dict], spec_variants: list[str], rep: vc.Report, stage: str) -> None:
    covered: set[str] = set()
    for ev in evidences:
        built = ev.get("profile", "")
        variants = ev.get("variants", [])
        if not variants:
            rep.error("QU-00", f"evidence for profile '{built}' lists no variants")
        covered.update(variants)
        idx = {(e.get("test"), e.get("variant")): e for e in ev.get("entries", [])}
        for r in rows:
            if r["status"] == "withdrawn" or not req_applies(r["profile"], built):
                continue
            tests = [t for t in (r["test_pos"], r["test_neg"]) if t not in ("-", "")]
            for t in tests:
                for v in variants:
                    e = idx.get((t, v))
                    if e is None:
                        rep.error("QU-01", f"{r['req_id']}: no evidence entry for {t} on {v}")
                        continue
                    st = e.get("status", "NOT_RUN")
                    if st == "N/A":
                        if not e.get("note"):
                            rep.error("QU-06", f"{r['req_id']}: {t} on {v} is N/A without a reason")
                    elif st != "PASS":
                        rep.error("QU-02", f"{r['req_id']}: {t} on {v} is {st}")
                    elif not e.get("log"):
                        rep.error("QU-03", f"{r['req_id']}: {t} on {v} is PASS without a log reference (VQUA-08)")
        for key, label in (("lint", "interface/checker lint"), ("compile", "UVM compile"), ("coverage", "coverage")):
            st = ev.get(key, {}).get("status", "NOT_RUN")
            if st != "PASS":
                rep.error("QU-04", f"profile {built}: {label} evidence is {st}")
    for v in spec_variants:
        if v not in covered:
            rep.error("QU-05", f"variant {v} has no qualification evidence (build and qualify its profile)")
    if stage == "release":
        for r in rows:
            if r["status"] not in ("qualified", "waived", "withdrawn"):
                rep.error("RL-01", f"{r['req_id']}: status '{r['status']}' is not qualified, waived, or withdrawn")
            if r["status"] == "waived" and not r["notes"].strip().lower().startswith("waived:"):
                rep.error("RL-02", f"{r['req_id']}: waived requirement needs a 'waived:<reason>' note (VDOC-04)")


def lint(requirements: str, stage: str, spec: str | None = None, vip_dir: str | None = None,
         tag: str | None = None, evidences: list[str] | None = None) -> vc.Report:
    """Run the trace lint of one stage and return the report (also used by vip.py and vip_state.py)."""
    import json
    rows = vc.read_csv(requirements)
    rep = vc.Report(f"VIP trace lint ({stage})", requirements)
    missing = [c for c in vc.REQ_COLUMNS if rows and c not in rows[0]]
    if missing:
        rep.error("PL-00", f"requirements.csv lacks columns: {', '.join(missing)}")
        return rep
    lint_plan(rows, rep, stage)
    spec_obj = vc.load_spec(spec) if spec else None
    if spec_obj:
        want = {r["req_id"] for r in spec_obj.rows("requirements")}
        have = {r["req_id"] for r in rows}
        for x in sorted(want - have):
            rep.error("SP-01", f"{x} is in the specification but not in requirements.csv")
        for x in sorted(have - want):
            rep.error("SP-02", f"{x} is in requirements.csv but not in the specification")
    if not tag:
        tag = spec_obj.tag if spec_obj else (
            vc.REQ_ID_RE.match(rows[0]["req_id"]).group(1).lower() if rows and vc.REQ_ID_RE.match(rows[0]["req_id"]) else "")
    if stage_ge(stage, "impl"):
        if not vip_dir:
            rep.error("CL-01", "--vip-dir is required from stage impl")
        else:
            lint_impl(rows, Path(vip_dir), tag, rep, stage)
    if stage_ge(stage, "qual"):
        if not evidences:
            rep.error("CL-02", "--evidence is required from stage qual")
        else:
            evs = [json.loads(Path(e).read_text(encoding="utf-8")) for e in evidences]
            spec_vars = [v["variant_id"] for v in spec_obj.rows("variants")] if spec_obj else []
            lint_qual(rows, evs, spec_vars, rep, stage)
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--requirements", required=True)
    ap.add_argument("--stage", required=True, choices=STAGES)
    ap.add_argument("--spec", help="VIP specification; requirement IDs must match")
    ap.add_argument("--vip-dir", help="generated VIP directory (stage impl and later)")
    ap.add_argument("--tag", help="protocol tag (default: from --spec or the requirement IDs)")
    ap.add_argument("--evidence", action="append", help="qualification evidence JSON (stage qual and later); repeat once per built profile")
    ap.add_argument("--full", action="store_true", help="print every finding (default: grouped, 3 per code)")
    ap.add_argument("--json", help="write the report as JSON to this new file")
    args = ap.parse_args()
    rep = lint(args.requirements, args.stage, args.spec, args.vip_dir, args.tag, args.evidence)
    rep.print_text(full=args.full)
    if args.json:
        vc.refuse_overwrite(args.json)
        vc.write_json(args.json, rep.to_json())
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
