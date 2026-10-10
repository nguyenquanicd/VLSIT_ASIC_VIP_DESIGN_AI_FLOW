#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the qualification traces with a simulator command given by the user.

The script is simulator-agnostic: the build and run commands are templates.
For each variant it builds once, then runs every test for every seed, writing
one log per run. It does not decide PASS or FAIL; collect_qual_results.py does.

Placeholders
    --build-cmd   {defines} {builddir} {vipdir} {variant} {log}
    --run-cmd     {test} {seed} {builddir} {vipdir} {variant} {log}
    The runner appends +VLSIT_SEED=<seed>; give the simulator its own seed option in the template.
{defines} expands the variant parameter values to +define+<MACRO>=<value>
using the parameter macros of vip_config.json.

Example (illustrative; adapt to the installed simulator):
    --build-cmd "vcs -sverilog -full64 -f filelist/apb_vip.f {defines} -o {builddir}/simv"
    --run-cmd   "{builddir}/simv +UVM_TESTNAME={test} +ntb_random_seed={seed}"

Usage:
    python run_qual.py --evidence qual_evidence.json --config vip_config.json --spec SPEC.md \
        --vip-dir DIR --log-dir DIR/logs --build-cmd "..." --run-cmd "..." --seeds 3 [--variants VAR-01] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402


def variant_defines(spec: vc.Spec, cfg: dict, variant: str) -> str:
    row = next((v for v in spec.rows("variants") if v["variant_id"] == variant), None)
    if row is None:
        raise SystemExit(f"error: variant {variant} is not in the specification")
    macro = {p["name"]: p["macro"] for p in cfg["parameters"]}
    out = []
    for pair in re.split(r"[,;]\s*", row["parameter_values"]):
        pair = pair.strip()
        if not pair or pair.lower() == "none":
            continue
        k, _, v = pair.partition("=")
        k, v = k.strip(), v.strip()
        if k not in macro:
            raise SystemExit(f"error: variant {variant} sets unknown parameter {k}")
        out.append(f"+define+{macro[k]}={v}")
    return " ".join(out)


def sh(cmd: str, log: Path, dry: bool) -> tuple[int, float]:
    if dry:
        print(f"DRY {cmd}")
        return 0, 0.0
    t0 = time.time()
    with open(log, "w", encoding="utf-8", errors="replace") as fh:
        fh.write(f"# command: {cmd}\n")
        fh.flush()
        rc = subprocess.run(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT).returncode
    return rc, time.time() - t0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--vip-dir", required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--build-cmd", required=True)
    ap.add_argument("--run-cmd", required=True)
    ap.add_argument("--seeds", type=int, default=1, help="number of seeds per trace (seeds 1..N)")
    ap.add_argument("--seed-list", help="explicit comma-separated seeds; overrides --seeds")
    ap.add_argument("--variants", help="comma-separated subset of variants")
    ap.add_argument("--tests", help="regular expression selecting tests")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ev = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    spec = vc.load_spec(args.spec)
    seeds = [int(x) for x in args.seed_list.split(",")] if args.seed_list else list(range(1, args.seeds + 1))
    variants = args.variants.split(",") if args.variants else ev["variants"]
    log_dir = Path(args.log_dir)
    if not args.dry_run:
        log_dir.mkdir(parents=True, exist_ok=True)
    summary_path = log_dir / "run_summary.json"
    vc.refuse_overwrite(summary_path) if not args.dry_run else None
    tests = sorted({e["test"] for e in ev["entries"]})
    if args.tests:
        rx = re.compile(args.tests)
        tests = [t for t in tests if rx.search(t)]
    runs = []
    for v in variants:
        builddir = log_dir / f"build_{v}"
        defines = variant_defines(spec, cfg, v)
        if not args.dry_run:
            builddir.mkdir(parents=True, exist_ok=True)
        blog = log_dir / f"{v}__build.log"
        cmd = args.build_cmd.format(defines=defines, builddir=builddir.as_posix(), vipdir=Path(args.vip_dir).as_posix(),
                                    variant=v, log=blog.as_posix())
        rc, dt = sh(cmd, blog, args.dry_run)
        runs.append({"kind": "build", "variant": v, "cmd": cmd, "log": blog.name, "rc": rc, "seconds": round(dt, 1)})
        if rc != 0 and not args.dry_run:
            print(f"build of {v} failed (exit {rc}); see {blog}")
            continue
        for t in tests:
            for s in seeds:
                log = log_dir / f"{v}__{t}__seed{s}.log"
                if log.exists() and not args.dry_run:
                    raise SystemExit(f"error: log exists and will not be overwritten: {log}")
                cmd = args.run_cmd.format(test=t, seed=s, builddir=builddir.as_posix(),
                                          vipdir=Path(args.vip_dir).as_posix(), variant=v, log=log.as_posix())
                if "+VLSIT_SEED=" not in cmd:
                    cmd += f" +VLSIT_SEED={s}"  # the test base prints it in the result line
                rc, dt = sh(cmd, log, args.dry_run)
                runs.append({"kind": "run", "variant": v, "test": t, "seed": s, "cmd": cmd, "log": log.name,
                             "rc": rc, "seconds": round(dt, 1)})
    if not args.dry_run:
        vc.write_json(summary_path, {"created": vc.now_iso(), "seeds": seeds, "variants": variants, "runs": runs})
        print(f"{sum(1 for r in runs if r['kind'] == 'run')} run(s) executed; summary in {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
