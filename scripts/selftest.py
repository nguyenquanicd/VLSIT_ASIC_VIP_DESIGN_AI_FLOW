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
    step("VIP generated (64 files)", rc == 0 and "64 file" in out)
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
