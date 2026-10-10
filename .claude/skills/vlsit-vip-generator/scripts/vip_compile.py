#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One-command compile feedback for a generated VIP: lint, UVM type-check, evidence.

lint   Verilator lint of the UVM-free interface and checker in simulation mode and in
       VLSIT_VIP_FORMAL mode (slang is used when Verilator is missing).
uvm    slang type-check of the whole UVM tree against the UVM reference implementation:
       the quickstart (example/) and the qualification environment (qual/), each as its
       own build. This checks types, class hierarchy, and UVM API use. It is not a
       simulation and not a simulator compile; the evidence note says so.

The output is a few lines. Full tool output goes to a log file; the first lines of the
VIP's own errors are echoed. UVM-source warnings are ignored; warnings in VIP files count.

Usage:
    python vip_compile.py --vip-dir DIR/<tag>_vip [--mode all|lint|uvm] [--uvm-home DIR]
        [--log-dir DIR] [--record qual_evidence.json] [--show 5]

Exit status 0 when every selected check passes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_env as ce  # noqa: E402
import vip_common as vc  # noqa: E402


def sh(cmd: list[str], cwd: Path, env: dict | None = None, timeout: int = 600) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout + r.stderr
    except Exception as exc:
        return 99, f"error running {cmd[0]}: {exc}"


def parse_filelist(path: Path) -> tuple[list[str], list[str], list[str]]:
    incs, defs, files = [], [], []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.split("//")[0].strip()
        if not s:
            continue
        if s.startswith("+incdir+"):
            incs.append(s[len("+incdir+"):])
        elif s.startswith("+define+"):
            defs.append(s[len("+define+"):])
        else:
            files.append(s)
    return incs, defs, files


def new_log_dir(base: Path) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    n = 1
    while (base / f"check_{n:03d}").exists():
        n += 1
    d = base / f"check_{n:03d}"
    d.mkdir()
    return d


def vip_lines(out: str, uvm_home: str | None, pattern: str, limit: int) -> tuple[int, list[str]]:
    """Count and sample findings whose first line points into the VIP, not into UVM."""
    hits = []
    for ln in out.splitlines():
        if re.search(pattern, ln):
            norm = ln.replace("\\", "/")
            if uvm_home and uvm_home.replace("\\", "/") in norm:
                continue
            if "unknown-escape-code" in ln:
                continue
            hits.append(ln.strip())
    return len(hits), hits[:limit]


def lint_checks(vip: Path, tag: str, logdir: Path, show: int) -> list[dict]:
    res = []
    ver = ce.find_verilator()
    slang = ce.find_slang()
    flist = vip / "filelist" / f"{tag}_vip_lint.f"
    for mode, define in (("sim", []), ("formal", ["-DVLSIT_VIP_FORMAL"])):
        log = logdir / f"lint_{mode}.log"
        if ver["found"]:
            env = dict(os.environ)
            if "VERILATOR_ROOT" not in env:
                share = Path(ver["path"]).resolve().parent.parent / "share" / "verilator"
                if share.is_dir():
                    env["VERILATOR_ROOT"] = str(share)
            cmd = [ver["path"], "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSEDSIGNAL", "-Wno-UNUSEDPARAM",
                   "--timing", *define, "-f", str(flist), "--top-module", f"{tag}_if"]
            rc, out = sh(cmd, vip, env)
            n, sample = vip_lines(out, None, r"%Warning|%Error", show)
            tool = ver["version"].split(" rev")[0]
            ok = rc == 0 and n == 0
        elif slang["found"]:
            incs, defs, files = parse_filelist(flist)
            cmd = [slang["path"], *[f"-I{i}" for i in incs], *[f"-D{d}" for d in defs], *define, "--timescale", "1ns/1ps",
                   *files, "--top", f"{tag}_if"]
            rc, out = sh(cmd, vip)
            n, sample = vip_lines(out, None, r": (error|warning):", show)
            tool = "slang " + slang["version"].split()[2] if slang["version"] else "slang"
            ok = rc == 0 and n == 0
        else:
            log.write_text("no lint tool found\n", encoding="utf-8")
            res.append({"name": f"lint {mode}", "status": "NOT_RUN", "tool": "none", "log": str(log), "detail": "no Verilator or slang"})
            continue
        log.write_text(f"# {' '.join(cmd)}\n{out}", encoding="utf-8")
        res.append({"name": f"lint {mode}", "status": "PASS" if ok else "FAIL", "tool": tool, "log": str(log),
                    "detail": f"{n} finding(s)", "sample": sample})
    return res


def uvm_checks(vip: Path, tag: str, uvm_home: str | None, logdir: Path, show: int) -> list[dict]:
    slang, uvm = ce.find_slang(), ce.find_uvm(uvm_home)
    if not slang["found"] or not uvm["found"]:
        why = "slang missing" if not slang["found"] else "UVM not found (python3 check_env.py --install-uvm <DIR>)"
        return [{"name": f"uvm {n}", "status": "NOT_RUN", "tool": "none", "log": "", "detail": why} for n in ("quickstart", "qual env")]
    incs, defs, files = parse_filelist(vip / "filelist" / f"{tag}_vip.f")
    src = Path(uvm["home"]) / "src"
    core = [f for f in files if not f.startswith(("example/", "qual/"))]
    builds = [("quickstart", [f for f in files if f.startswith("example/")], f"{tag}_example_top"),
              ("qual env", [f for f in files if f.startswith("qual/")], f"{tag}_qual_tb_top")]
    res = []
    for name, extra, top in builds:
        cmd = [slang["path"], "-I", str(src), *[f"-I{i}" for i in incs], "-DUVM_NO_DPI", *[f"-D{d}" for d in defs],
               "--timescale", "1ns/1ps", str(src / "uvm_pkg.sv"), *core, *extra, "--top", top]
        rc, out = sh(cmd, vip)
        log = logdir / f"uvm_{name.replace(' ', '_')}.log"
        log.write_text(f"# {' '.join(cmd)}\n{out}", encoding="utf-8")
        ne, es = vip_lines(out, uvm["home"], r"\berror:", show)
        nw, ws = vip_lines(out, uvm["home"], r"\bwarning:", show)
        ok = "Build succeeded" in out and ne == 0 and nw == 0
        tool = f"slang {slang['version'].split()[2]} + UVM {uvm['version'].rsplit(':', 1)[-1]}"
        res.append({"name": f"uvm {name}", "status": "PASS" if ok else "FAIL", "tool": tool, "log": str(log),
                    "detail": f"{ne} error(s), {nw} VIP warning(s)", "sample": es + ws})
    return res


def record(evidence: Path, results: list[dict]) -> None:
    ev = json.loads(evidence.read_text(encoding="utf-8"))
    def agg(prefix: str) -> dict | None:
        rs = [r for r in results if r["name"].startswith(prefix)]
        if not rs:
            return None
        st = "PASS" if all(r["status"] == "PASS" for r in rs) else ("NOT_RUN" if any(r["status"] == "NOT_RUN" for r in rs) else "FAIL")
        return {"status": st, "log": ";".join(r["log"] for r in rs if r["log"]),
                "note": "; ".join(f"{r['name']}: {r['tool']}" for r in rs)
                        + ("; slang type-check against UVM, not a simulator compile or simulation" if prefix == "uvm" else "")}
    for key, prefix in (("lint", "lint"), ("compile", "uvm")):
        a = agg(prefix)
        if a:
            ev[key].update(a)
            ev.setdefault("history", []).append({"time": vc.now_iso(), "event": f"item_{key}", "detail": a["status"]})
    evidence.write_text(json.dumps(ev, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vip-dir", required=True)
    ap.add_argument("--mode", default="all", choices=["all", "lint", "uvm"])
    ap.add_argument("--uvm-home")
    ap.add_argument("--log-dir", help="default: <vip-dir>/../compile_logs")
    ap.add_argument("--record", help="qual_evidence.json whose lint and compile items are updated")
    ap.add_argument("--show", type=int, default=5, help="VIP findings echoed per build")
    args = ap.parse_args()
    vip = Path(args.vip_dir).resolve()
    cfg = json.loads((vip / "spec" / "vip_config.json").read_text(encoding="utf-8"))
    tag = cfg["tag"]
    logdir = new_log_dir(Path(args.log_dir) if args.log_dir else vip.parent / "compile_logs")
    results: list[dict] = []
    if args.mode in ("all", "lint"):
        results += lint_checks(vip, tag, logdir, args.show)
    if args.mode in ("all", "uvm"):
        results += uvm_checks(vip, tag, args.uvm_home, logdir, args.show)
    for r in results:
        print(f"{r['name']:14s} {r['status']:7s} {r['detail']} [{r['tool']}]")
        for ln in r.get("sample", [])[:args.show]:
            print(f"    {ln[:150]}")
    print(f"logs: {logdir}")
    if args.record:
        record(Path(args.record), results)
        print(f"recorded in {args.record}")
    return 0 if all(r["status"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
