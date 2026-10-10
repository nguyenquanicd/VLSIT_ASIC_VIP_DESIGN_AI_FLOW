#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Report the tools the VIP flow can use, and optionally install the pinned UVM.

Reports Python, git, slang (type-checks SystemVerilog and UVM without a simulator),
Verilator (lint of the UVM-free interface and checker), and the UVM reference
implementation. Prints one short line per tool. Nothing is installed unless
--install-uvm is given.

Discovery order
    slang      $VLSIT_SLANG, then PATH (slang, slang.exe)
    Verilator  $VLSIT_VERILATOR, then PATH (verilator_bin, verilator_bin.exe, verilator)
    UVM        --uvm-home, $VLSIT_UVM_HOME, then C:/Tools/uvm-core, ~/uvm-core, /opt/uvm-core

Usage:
    python check_env.py [--uvm-home DIR] [--json]
    python check_env.py --install-uvm DIR      # git clone of the pinned tag; DIR must not exist
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

UVM_REPO = "https://github.com/accellera-official/uvm-core.git"
UVM_TAG = "2020.3.1"
UVM_COMMIT = "78c06547a2a0a29b3dc9dcafae62b75b2ff61544"
UVM_VERSION_STRING = "Accellera:1800.2:UVM:2020.3.1"
UVM_CANDIDATES = ["C:/Tools/uvm-core", str(Path.home() / "uvm-core"), "/opt/uvm-core"]


def run(cmd: list[str], timeout: int = 20) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except Exception as exc:  # tool missing or not runnable
        return f"error: {exc}"


def which_any(env_var: str, names: list[str]) -> str | None:
    p = os.environ.get(env_var)
    if p and Path(p).exists():
        return p
    for n in names:
        found = shutil.which(n)
        if found:
            return found
    return None


def find_slang() -> dict:
    p = which_any("VLSIT_SLANG", ["slang", "slang.exe", "slang-driver"])
    if not p:
        return {"found": False}
    ver = run([p, "--version"]).splitlines()[0] if p else ""
    return {"found": True, "path": p, "version": ver}


def find_verilator() -> dict:
    p = which_any("VLSIT_VERILATOR", ["verilator_bin", "verilator_bin.exe", "verilator"])
    if not p:
        return {"found": False}
    env = dict(os.environ)
    ver = run([p, "--version"]).splitlines()[0]
    note = ""
    if "error" in ver.lower() or "VERILATOR_ROOT" in ver:
        note = "set VERILATOR_ROOT to the share/verilator directory of the installation"
    return {"found": True, "path": p, "version": ver, "note": note}


def uvm_version(home: Path) -> str:
    f = home / "src" / "base" / "uvm_version.svh"
    if f.is_file():
        m = re.search(r'UVM_VERSION_STRING\s*=\s*"([^"]+)"', f.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return ""


def find_uvm(arg: str | None) -> dict:
    for cand in [arg, os.environ.get("VLSIT_UVM_HOME"), *UVM_CANDIDATES]:
        if cand and (Path(cand) / "src" / "uvm_pkg.sv").is_file():
            home = Path(cand)
            v = uvm_version(home)
            return {"found": True, "home": str(home), "version": v,
                    "pinned": v == UVM_VERSION_STRING}
    return {"found": False}


def install_uvm(dest: str) -> int:
    d = Path(dest)
    if d.exists():
        print(f"error: {d} exists; it will not be overwritten", file=sys.stderr)
        return 1
    if not shutil.which("git"):
        print("error: git is required to install UVM", file=sys.stderr)
        return 1
    print(f"cloning {UVM_REPO} tag {UVM_TAG} into {d}")
    r = subprocess.run(["git", "clone", "--depth", "1", "--branch", UVM_TAG, UVM_REPO, str(d)])
    if r.returncode != 0:
        return r.returncode
    got = run(["git", "-C", str(d), "rev-parse", "HEAD"])
    if got != UVM_COMMIT:
        print(f"WARNING: commit {got} differs from the pinned {UVM_COMMIT}", file=sys.stderr)
    print(f"installed UVM {uvm_version(d)}; set VLSIT_UVM_HOME={d} or pass --uvm-home")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uvm-home")
    ap.add_argument("--install-uvm", metavar="DIR")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.install_uvm:
        return install_uvm(args.install_uvm)
    info = {
        "python": {"found": True, "version": sys.version.split()[0], "path": sys.executable},
        "git": {"found": bool(shutil.which("git"))},
        "slang": find_slang(), "verilator": find_verilator(), "uvm": find_uvm(args.uvm_home),
    }
    if args.json:
        print(json.dumps(info, indent=2))
        return 0
    py = info["python"]
    print(f"python     {py['version']}")
    print(f"git        {'found' if info['git']['found'] else 'missing (needed only to install UVM)'}")
    s = info["slang"]
    print("slang      " + (f"{s['version']}" if s["found"] else "missing: UVM compile check (vip.py check-vip) cannot run"))
    v = info["verilator"]
    print("verilator  " + ((v["version"] + (f" ({v['note']})" if v["note"] else "")) if v["found"]
                           else "missing: interface/checker lint falls back to slang"))
    u = info["uvm"]
    if u["found"]:
        print(f"uvm        {u['version']} at {u['home']}" + ("" if u["pinned"] else f" (pinned is {UVM_VERSION_STRING})"))
    else:
        print(f"uvm        missing: python3 check_env.py --install-uvm <DIR>  (tag {UVM_TAG})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
