#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-test of the VLSIT ASIC VIP Design AI Flow repository.

Runs the whole chain on the APB worked example in a temporary directory and reports
PASS, FAIL, or SKIP per step. Steps that need a tool that is not installed (Verilator,
slang, UVM) are SKIPped, never passed. The qualification run uses a synthetic stand-in
for a simulator; it checks the runner and collector logic only and produces no evidence.

Usage:
    python scripts/selftest.py [--keep] [--uvm-home DIR]
Exit status 0 when no step failed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIP = ROOT / ".claude" / "skills" / "vlsit-vip-flow" / "scripts" / "vip.py"
SHARED = ROOT / "shared" / "scripts"
EXAMPLE = ROOT / "examples" / "apb" / "APB_VIP_Specification.md"
TEMPLATE = ROOT / "spec_template" / "VLSIT_ASIC_VIP_Specification_Template.md"

FAKE_SIM = '''
import argparse, sys
ap = argparse.ArgumentParser()
ap.add_argument("cmd"); ap.add_argument("--test", default=""); ap.add_argument("--seed", type=int, default=0)
a, _ = ap.parse_known_args()
if a.cmd == "run":
    print(f"VLSIT_VIP_QUAL_RESULT test={a.test} seed={a.seed} status=PASS expected=1 unexpected=0 missing=0")
    print("UVM_ERROR :    0")
    print("UVM_FATAL :    0")
'''

NL = chr(10)
results: list[tuple[str, str, str]] = []


def step(name: str, ok: bool | None, note: str = "") -> None:
    results.append((name, "SKIP" if ok is None else ("PASS" if ok else "FAIL"), note))
    print(f"{results[-1][1]:5s} {name}" + (f"  ({note})" if note else ""))


def run(args: list[str], cwd: Path | None = None, env: dict | None = None) -> tuple[int, str]:
    r = subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env={**os.environ, **(env or {})})
    return r.returncode, r.stdout + r.stderr


def vip(run_dir: Path, *a: str, env: dict | None = None) -> tuple[int, str]:
    return run([str(VIP), "--run", str(run_dir), *a], env=env)


def last_line(out: str) -> str:
    lines = [x for x in out.strip().splitlines() if x.strip()]
    return lines[-1] if lines else ""


def new_run(tmp: Path, mode: str, base: Path, *extra: str) -> Path | None:
    rc, out = run([str(VIP), "init", str(tmp), "apb", "--mode", mode, "--base-run", str(base), *extra])
    return Path(last_line(out)) if rc == 0 else None


def change_runs(tmp: Path, base: Path) -> None:
    """Bugfix, feature, and reverse runs on top of the finished APB base run (synthetic simulator)."""
    (base / "05_qual" / "qualification_report.md").write_text("selftest placeholder" + NL, encoding="utf-8")
    vip(base, "gate", "G3", "APPROVED", "--by", "selftest")
    tree = base / "04_vip" / "apb_vip"
    # a hand-written line in the base tree must survive a feature port
    drv = tree / "uvm" / "apb_driver_host.sv"
    drv.write_text(drv.read_text(encoding="utf-8").replace("endclass", "  // HAND-WRITTEN selftest marker" + NL + "endclass", 1),
                   encoding="utf-8", newline=NL)

    # ---- bugfix
    bf = new_run(tmp, "bugfix", base)
    step("bugfix run starts from the base run (patch version bumped)", bf is not None)
    if bf is None:
        return
    rc, out = vip(bf, "bug", "new", "--title", "pstrb message", "--symptom", "wrong message", "--severity", "minor", "--req", "VREQ-APB-0004")
    rc2, out2 = vip(bf, "bug", "set", "BUG-001", "status=planned")
    step("bug log refuses a state skip and an unclassified bug", rc == 0 and rc2 == 1)
    vip(bf, "bug", "set", "BUG-001", "class=vip", "status=analyzed")
    vip(bf, "bug", "set", "BUG-001", "files=rtl_if/apb_checker.sv", "status=planned")
    rc, out = vip(bf, "bug", "set", "BUG-001", "status=fixed")
    step("bug log refuses fixed without a regression test", rc == 1 and "regression test" in out)
    rc, out = vip(bf, "carry-gates", "--by", "selftest")
    step("Gates 1 and 2 carried to the bugfix run (files identical)", rc == 0 and "G1, G2" in out, last_line(out))
    chk = bf / "04_vip" / "apb_vip" / "rtl_if" / "apb_checker.sv"
    text = chk.read_text(encoding="utf-8")
    chk.write_text(text.replace("pstrb is not low during a read transfer", "pstrb is not zero during a read transfer"), encoding="utf-8", newline=NL)
    tests = bf / "04_vip" / "apb_vip" / "qual" / "tests"
    shutil.copyfile(tests / "qual_apb_errm_pstrb_rd_low_neg.sv", tests / "qual_bug001_msg.sv")
    vip(bf, "bug", "set", "BUG-001", "regression_test=qual_bug001_msg", "fix_summary=message", "status=fixed")
    rc, out = vip(bf, "impact")
    step("impact of a fixed check message and its regression test: selective, 3 of 24 traces", rc == 0 and "SELECTIVE" in out and "re-run 3 of 24" in out, last_line(out)[:70])
    rc, out = vip(bf, "carry")
    step("evidence carried: 42 PASS carried, 6 to run (4 impacted + 2 regression-test entries)", rc == 0 and "carried 42" in out and "2 regression-test" in out, last_line(out)[:70])
    rc, out = vip(bf, "qual-run", "--impacted")
    rc2, out2 = vip(bf, "qual-collect")
    step("only the impacted traces re-run; evidence complete (48 PASS)", rc == 0 and "12 run" in out and rc2 == 0 and "'PASS': 48" in out2, last_line(out)[:60])
    log = next((bf / "05_qual" / "logs").glob("*.log"), None)
    rc, out = vip(bf, "bug", "set", "BUG-001", f"evidence_log={log.relative_to(bf).as_posix()}", "status=verified") if log else (1, "no log")
    rc2, out2 = vip(bf, "bug", "set", "BUG-001", "status=closed")
    step("bug verified from a log and closed with its regression test in the tree", rc == 0 and rc2 == 0, last_line(out2))

    # ---- feature
    ft = new_run(tmp, "feature", base)
    step("feature run starts from the base run (minor version bumped)", ft is not None)
    if ft is None:
        return
    rc, out = vip(ft, "next")
    step("feature run asks for the change request first", rc == 0 and "change request" in out)
    (ft / "00_change" / "change_request.md").write_text(
        "# Change request" + NL + "## Title" + NL + "penable needs psel" + NL + "## Requirement from the user" + NL + "Flag penable while psel is low." + NL
        + "## Motivation and source" + NL + "APB operating states." + NL + "## Acceptance" + NL + "A new MUST check." + NL
        + "## Compatibility" + NL + "Defaults unchanged." + NL, encoding="utf-8")
    spec = ft / "01_spec" / "apb_vip_spec.md"
    s = spec.read_text(encoding="utf-8")
    row = ('| VREQ-APB-0016 | MUST | M | SEQ | The host shall keep psel high in every cycle in which penable is high. | '
           'REF-001 "Operating states: SETUP and ACCESS" | all | penable, psel | PENABLE_PSEL | SVA | auto | - | - |' + NL)
    i = s.index("| VREQ-APB-0009 | MUST | M | SEQ |")
    j = s.index(NL, i)
    s = s[:j + 1] + row + s[j + 1:]
    s = s.replace("| VREQ-APB-0009 | NEXT |", "| VREQ-APB-0016 | SAME | penable | psel | penable is high while psel is low |" + NL + "| VREQ-APB-0009 | NEXT |", 1)
    s = s.replace("| INJ-009 |", "| INJ-010 | M | Assert penable while psel is low | item field inj_kind = APB_INJ_PENABLE_NOPSEL | VREQ-APB-0016 | auto |" + NL + "| INJ-009 |", 1)
    spec.write_text(s, encoding="utf-8", newline=NL)
    rc, out = vip(ft, "validate")
    step("updated specification validates", rc == 0, last_line(out))
    rc, out = vip(ft, "delta")
    step("spec delta: 1 requirement, 1 expression, 1 injection added; bump minor", rc == 0 and "requirements +1" in out and "checkexpr +1" in out and "minor" in out, last_line(out)[:70])
    vip(ft, "gate", "G1", "APPROVED", "--by", "selftest")
    rc, out = vip(ft, "plan")
    rc2, out2 = vip(ft, "config")
    (ft / "03_arch" / "vip_arch.md").write_text("selftest placeholder" + NL, encoding="utf-8")
    vip(ft, "gate", "G2", "APPROVED", "--by", "selftest")
    step("feature plan and configuration: 16 requirements, 10 checks", rc == 0 and "16 requirement" in out and rc2 == 0 and "10 check" in out2)
    rc, out = vip(ft, "port")
    step("port keeps hand-written code and adds the new skeleton without conflict", rc == 0 and "conflict" not in out.replace("conflict 0", ""), last_line(out)[:70])
    kept = (ft / "04_vip" / "apb_vip" / "uvm" / "apb_driver_host.sv").read_text(encoding="utf-8")
    step("hand-written line survived the port", "HAND-WRITTEN selftest marker" in kept)
    rc, out = vip(ft, "lint", "impl")
    step("no merge conflict marker left (HY-09 clean)", "HY-09" not in out)
    rc, out = vip(ft, "impact")
    step("impact of a new check: selective, 2 of 25 traces", rc == 0 and "SELECTIVE" in out and "re-run 2 of 25" in out, last_line(out)[:70])
    rc, out = vip(ft, "carry")
    step("evidence carried from the base for untouched traces", rc == 0 and "carried 46" in out, last_line(out)[:70])
    rc, out = vip(ft, "qual-run", "--impacted")
    rc2, out2 = vip(ft, "qual-collect")
    step("only the 4 new entries run; evidence has 50 PASS", rc == 0 and "8 run" in out and "'PASS': 50" in out2, last_line(out)[:60])

    # ---- reverse (the generated tree is read as if it were external code) and external bugfix
    rv = tmp / "reverse_root"
    rc, out = run([str(VIP), "init", str(rv), "apb", "--mode", "reverse", "--code", str(tree)])
    rvr = Path(last_line(out)) if rc == 0 else None
    step("reverse run starts on a code directory", rvr is not None)
    if rvr is None:
        return
    rc, out = vip(rvr, "inventory")
    step("inventory scan: 9 assertions found", rc == 0 and "assertions 9" in out, "lexical scan")
    rc, out = vip(rvr, "from-code", "--title", "APB", "--standard", "AMBA APB (revision to confirm)")
    step("draft specification: 13 signals, 9 requirements, 9 expressions", rc == 0 and "13 signal" in out and "9 requirement" in out and "9 check expression" in out, last_line(out)[:90])
    rc, out = vip(rvr, "verify-code")
    step("CODE pointers resolve (no drift)", rc == 0, last_line(out)[:70])
    rc, out = vip(rvr, "gate", "G1", "APPROVED", "--by", "selftest")
    step("Gate 1 refuses a specification with UNVERIFIED marks", rc == 1 and "UNVERIFIED" in out)
    vip(rvr, "gate", "G1", "APPROVED", "--by", "selftest", "--allow-unverified", "--note", "selftest only")
    rc, out = vip(rvr, "adopt")
    step("code adopted as the base tree (layout external)", rc == 0 and "external" in out, last_line(out)[-40:])
    eb = new_run(tmp, "bugfix", rvr)
    step("bugfix run on external code starts", eb is not None)
    if eb is not None:
        rc, out = vip(eb, "lint", "impl")
        step("generated-layout commands are refused for external code", rc != 0 and "external" in out)
        rc, out = vip(eb, "status")
        step("Gate 2 does not apply to external code", rc == 0 and "G2" not in out, last_line(out)[:70])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", action="store_true", help="keep the temporary directory")
    ap.add_argument("--uvm-home")
    args = ap.parse_args()
    env = {"PYTHONDONTWRITEBYTECODE": "1"}
    if args.uvm_home:
        env["VLSIT_UVM_HOME"] = args.uvm_home
    tmp = Path(tempfile.mkdtemp(prefix="vipselftest_"))

    rc, out = run([str(ROOT / "scripts" / "sync_skills.py"), "--check"])
    step("skill folders are in sync (Claude and Codex)", rc == 0, out.strip().splitlines()[-1] if out.strip() else "")
    rc, out = run([str(SHARED / "validate_vip_spec.py"), str(TEMPLATE), "--template"])
    step("template structure validates", rc == 0)
    rc, out = run([str(SHARED / "validate_vip_spec.py"), str(EXAMPLE)])
    step("APB example validates", rc == 0)
    bad = tmp / "bad.md"
    bad.write_text(EXAMPLE.read_text(encoding="utf-8").replace("The host shall keep paddr stable", "The host keeps paddr stable"), encoding="utf-8")
    rc, out = run([str(SHARED / "validate_vip_spec.py"), str(bad)])
    step("validator rejects a requirement without its modal verb", rc == 1 and "REQ-06" in out)
    scaf = tmp / "scaf.md"
    rc, out = run([str(VIP), "scaffold", "xyz", "--title", "Example", "--standard", "XYZ-1 rev A", "-o", str(scaf)])
    rc2, out2 = run([str(SHARED / "validate_vip_spec.py"), str(scaf), "--template"])
    step("scaffold writes a structurally valid skeleton", rc == 0 and rc2 == 0)
    rc, out = run([str(SHARED / "rule_lookup.py"), "VCHK-02", "VP-03"])
    step("rule lookup prints rule text", rc == 0 and "VCHK-02" in out and "VP-03" in out)

    rc, out = run([str(VIP), "init", str(tmp), "apb", str(EXAMPLE)])
    runp = Path(out.strip().splitlines()[-1]) if rc == 0 else tmp
    step("run directory created", rc == 0)
    if rc != 0:
        return 1
    vip(runp, "set", "author=Selftest", "project=Selftest", "reviewer=Selftest", "profile=PROF-01")
    rc, out = vip(runp, "stage", "S2")
    step("a stage is blocked before its gate", rc == 1)
    vip(runp, "gate", "G1", "APPROVED", "--by", "selftest")
    rc, out = vip(runp, "plan")
    step("plan derives 15 requirements and 9 checks", rc == 0 and "15 requirement" in out and "9 check" in out, out.strip().splitlines()[0][:60])
    rc, out = vip(runp, "lint", "plan")
    step("trace lint (plan) clean", rc == 0)
    rc, out = vip(runp, "config")
    step("vip_config.json derived and checked", rc == 0)
    (runp / "03_arch" / "vip_arch.md").write_text("selftest placeholder\n", encoding="utf-8")
    vip(runp, "gate", "G2", "APPROVED", "--by", "selftest")
    rc, out = vip(runp, "gen")
    step("VIP generated (65 files)", rc == 0 and "65 file" in out)
    rc, out = vip(runp, "lint", "impl")
    step("trace lint (impl): 0 errors with checks generated from the specification", rc == 0, "stubs remain as warnings")
    vip(runp, "qual-init")
    sim = tmp / "fake_sim.py"
    sim.write_text(FAKE_SIM, encoding="utf-8")
    py = Path(sys.executable).as_posix()
    vip(runp, "set", f'build_cmd={py} {sim.as_posix()} build --defines "{{defines}}" --builddir {{builddir}}',
        f"run_cmd={py} {sim.as_posix()} run --test {{test}} --seed {{seed}}", "seeds=2")
    rc, out = vip(runp, "qual-run")
    step("qualification runner executes 92 runs (synthetic simulator)", rc == 0 and "92 run" in out)
    rc, out = vip(runp, "qual-collect")
    step("collector sets PASS only from logs (46 entries)", rc == 0 and "'PASS': 46" in out)
    rc, out = vip(runp, "lint", "qual")
    step("qual lint still fails while stubs and evidence items are missing", rc == 1)
    change_runs(tmp, runp)

    rc, out = run([str(SHARED / "check_env.py"), "--json", *(["--uvm-home", args.uvm_home] if args.uvm_home else [])], env=env)
    info = json.loads(out) if rc == 0 else {}
    have_slang, have_uvm, have_verilator = (info.get(k, {}).get("found") for k in ("slang", "uvm", "verilator"))
    if have_slang or have_verilator:
        vipdir = runp / "04_vip" / "apb_vip"
        mode = "all" if (have_slang and have_uvm) else "lint"
        rc, out = run([str(ROOT / ".claude" / "skills" / "vlsit-vip-generator" / "scripts" / "vip_compile.py"), "--vip-dir", str(vipdir),
                       "--mode", mode, *(["--uvm-home", args.uvm_home] if args.uvm_home else [])], env=env)
        step(f"check-vip ({mode}): lint" + (" and UVM type-check" if mode == "all" else ""), rc == 0, out.strip().splitlines()[-2][:70] if out.strip() else "")
        if mode == "lint":
            step("UVM type-check", None, "slang or UVM not found; run python3 shared/scripts/check_env.py")
    else:
        step("check-vip lint and UVM type-check", None, "neither Verilator nor slang found")

    if not args.keep:
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print(f"kept: {tmp}")
    n_fail = sum(1 for _, s, _ in results if s == "FAIL")
    print(f"\n{sum(1 for _, s, _ in results if s == 'PASS')} passed, {n_fail} failed, {sum(1 for _, s, _ in results if s == 'SKIP')} skipped")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
