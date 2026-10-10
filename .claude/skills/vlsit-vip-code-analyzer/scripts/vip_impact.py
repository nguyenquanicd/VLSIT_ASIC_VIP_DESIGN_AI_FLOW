#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Impact analysis of a change to a generated VIP: what must be re-qualified, and what need not be.

Compares a base VIP tree with the changed tree (or takes a list of files or IDs) and maps each
change to checks, requirements, and qualification tests.

Scopes of a changed file (generated layout, VFIL-03):
  selective   a check block in <tag>_checker.sv, a sequence in seq_lib, a counterpart stimulus
              task or a test in qual/: only the traces of the touched checks, capabilities, or
              tests are re-run
  shared      the interface, the check package, base/, the agent, drivers, monitor, item, cfg,
              sequencer, package, the counterpart outside a stimulus task, or any other class:
              every trace is re-run because all of them exercise that code
  coverage    the coverage class: coverage is re-collected; pass or fail evidence is not affected
  none        documents, filelists, spec copies, examples: nothing to re-run

Usage:
    python vip_impact.py --base DIR --new DIR [--requirements requirements.csv] [--out impact.json]
    python vip_impact.py --new DIR --files FILE... | --ids ID...
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402

NL = chr(10)
CHK_BLOCK = re.compile(r"^  `VLSIT_VIP_CHK_(?:ERR|REC|TODO)\(\s*([A-Z0-9_]+)\b")
STIM_TASK = re.compile(r"^  task\s+([A-Za-z0-9_]+)_stim\s*\(")
# generated registrations that grow with every check or injection: the count, the record mask, the index,
# the name lookup, and the injection enum members
REGISTRY_LINE = re.compile(r"LPARA_NCHK|LPARA_REC_MASK|CHK_IDX_|if \(id ==|^\s*[A-Z0-9]+_INJ_[A-Z0-9_]+,?\s*$")
VERSION_TEXT = re.compile(r'VIP version \d+\.\d+\.\d+|([A-Z0-9_]+_VERSION\s*=\s*)"[^"]*"')
TEST_INCLUDE = re.compile(r'^\s*`include\s+"tests/')
STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"')


def tree(root: Path) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts:
            out[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8", errors="replace").replace("\r\n", NL)
    return out


def macro_end(lines: list[str], i: int) -> int:
    """Index of the line where the parentheses opened on line i are balanced (strings ignored)."""
    depth = 0
    for j in range(i, len(lines)):
        s = STRING_RE.sub('""', lines[j])
        depth += s.count("(") - s.count(")")
        if depth <= 0:
            return j
    return i


def check_blocks(text: str) -> tuple[dict[str, str], str]:
    """Split a checker file into one block per check (comment lines above plus the macro call) and the rest."""
    lines = text.split(NL)
    out, used = {}, set()
    for i, ln in enumerate(lines):
        m = CHK_BLOCK.match(ln)
        if not m:
            continue
        s = i
        while s > 0 and lines[s - 1].strip() != "":
            s -= 1
        e = macro_end(lines, i)
        out[m.group(1)] = NL.join(lines[s:e + 1])
        used.update(range(s, e + 1))
    return out, NL.join(ln for i, ln in enumerate(lines) if i not in used)


def task_blocks(text: str) -> tuple[dict[str, str], str]:
    """Counterpart: one block per `<test>_stim` task (with the comment lines above it)."""
    lines = text.split(NL)
    out, used = {}, set()
    i = 0
    while i < len(lines):
        m = STIM_TASK.match(lines[i])
        if m:
            s = i
            while s > 0 and lines[s - 1].lstrip().startswith("//"):
                s -= 1
            e = i
            while e < len(lines) and not lines[e].startswith("  endtask"):
                e += 1
            out[m.group(1)] = NL.join(lines[s:e + 1])
            used.update(range(s, e + 1))
            i = e
        i += 1
    return out, NL.join(ln for j, ln in enumerate(lines) if j not in used)


def squeeze(text: str) -> str:
    """Compare text without blank lines and trailing blanks."""
    return NL.join(ln.rstrip() for ln in text.split(NL) if ln.strip())


def drop_test_includes(text: str) -> str:
    return NL.join(ln for ln in text.split(NL) if not TEST_INCLUDE.match(ln))


def norm_version(text: str) -> str:
    """The generated version strings change in every release and are not behavior."""
    return VERSION_TEXT.sub(lambda m: (m.group(1) + '"0"') if m.group(1) else "VIP version 0", text)


def drop_registry(text: str) -> str:
    return NL.join(ln for ln in text.split(NL) if not REGISTRY_LINE.search(ln))


def classify(rel: str, tag: str) -> str:
    if rel.startswith(("doc/", "filelist/", "spec/")):
        return "none"
    if rel.startswith("example/"):
        return "example"
    if rel == f"rtl_if/{tag}_checker.sv":
        return "checker"
    if rel.startswith("uvm/seq_lib/"):
        return "sequence"
    if rel == f"uvm/{tag}_agent_cov.sv":
        return "coverage"
    if rel.startswith("qual/tests/"):
        return "test"
    if rel == f"qual/{tag}_counterpart.sv":
        return "counterpart"
    if rel == f"qual/{tag}_qual_pkg.sv":
        return "qualpkg"
    if rel in (f"rtl_if/{tag}_chk_pkg.sv", f"uvm/{tag}_item.sv"):
        return "registry"
    return "shared"


def analyze(base: dict[str, str] | None, new: dict[str, str], tag: str, reqs: list[dict],
            files: list[str] | None, ids: list[str] | None) -> dict:
    changed: dict[str, str] = {}
    if files:
        changed = {f: "changed" for f in files}
    elif base is not None:
        for f in sorted(set(base) | set(new)):
            if f not in base:
                changed[f] = "added"
            elif f not in new:
                changed[f] = "removed"
            elif base[f] != new[f]:
                changed[f] = "changed"
    res = {"files": changed, "shared": [], "checks": set(), "sequences": set(), "tests": set(), "coverage": False,
           "example": False, "reasons": []}
    for f in changed:
        kind = classify(f, tag)
        if kind == "none":
            continue
        if kind == "example":
            res["example"] = True
        elif kind == "coverage":
            res["coverage"] = True
        elif kind == "sequence":
            res["sequences"].add(Path(f).stem)
        elif kind == "test":
            res["tests"].add(Path(f).stem)
        elif kind in ("checker", "counterpart") and base is not None and f in base and f in new:
            split = check_blocks if kind == "checker" else task_blocks
            ob, orest = split(base[f])
            nb, nrest = split(new[f])
            if squeeze(orest) != squeeze(nrest):
                res["shared"].append(f"{f} (outside the per-check or per-task blocks)")
            for k in sorted(set(ob) | set(nb)):
                if ob.get(k) != nb.get(k):
                    (res["checks"] if kind == "checker" else res["tests"]).add(k)
        elif kind == "qualpkg" and base is not None and f in base and f in new:
            if squeeze(drop_test_includes(base[f])) != squeeze(drop_test_includes(new[f])):
                res["shared"].append(f"{f} (outside the test include list)")
        elif kind == "registry" and base is not None and f in base and f in new:
            if squeeze(drop_registry(base[f])) != squeeze(drop_registry(new[f])):
                res["shared"].append(f"{f} (outside the generated registrations)")
        elif base is not None and f in base and f in new and norm_version(base[f]) == norm_version(new[f]):
            continue
        else:
            res["shared"].append(f)
    for i in ids or []:
        if i.startswith("VREQ-"):
            for r in reqs:
                if r["req_id"] == i and r["chk_id"] != "-":
                    res["checks"].add(r["chk_id"])
        elif vc.CHECK_ID_RE.match(i):
            res["checks"].add(i)
        elif i.startswith("qual_"):
            res["tests"].add(i)
    req_ids, tests = set(), set(res["tests"])
    for r in reqs:
        if r["status"] == "withdrawn":
            continue
        hit = r["chk_id"] in res["checks"] or any(s in r["seq_id"].split(";") for s in res["sequences"])
        hit = hit or r["test_pos"] in tests or r["test_neg"] in tests
        if hit:
            req_ids.add(r["req_id"])
            tests.update(t for t in (r["test_pos"], r["test_neg"]) if t not in ("-", ""))
    all_tests = sorted({t for r in reqs if r["status"] != "withdrawn" for t in (r["test_pos"], r["test_neg"]) if t not in ("-", "")} | set(res["tests"]))
    res["requirements"] = sorted(req_ids)
    res["scope"] = "full" if res["shared"] else "selective"
    res["tests_to_run"] = all_tests if res["scope"] == "full" else sorted(tests)
    res["total_tests"] = len(all_tests)
    if res["coverage"] and res["scope"] == "selective":
        res["reasons"].append("the coverage class changed: re-collect coverage over every trace (pass or fail evidence is not affected)")
    res["checks"], res["sequences"], res["tests"] = sorted(res["checks"]), sorted(res["sequences"]), sorted(res["tests"])
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base")
    ap.add_argument("--new", required=True)
    ap.add_argument("--requirements")
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--out")
    a = ap.parse_args()
    new_root = Path(a.new)
    cfg_p = new_root / "spec" / "vip_config.json"
    tag = json.loads(cfg_p.read_text(encoding="utf-8"))["tag"] if cfg_p.is_file() else new_root.name.removesuffix("_vip")
    reqs_p = Path(a.requirements) if a.requirements else new_root / "spec" / "requirements.csv"
    reqs = vc.read_csv(reqs_p) if reqs_p.is_file() else []
    res = analyze(tree(Path(a.base)) if a.base else None, tree(new_root), tag, reqs, a.files, a.ids)
    kinds: dict[str, int] = {}
    for f in res["files"]:
        kinds[classify(f, tag)] = kinds.get(classify(f, tag), 0) + 1
    print(f"changed files: {len(res['files'])} (" + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) + ")")
    why = f" because {len(res['shared'])} shared file(s) changed: " + ", ".join(res["shared"][:3]) if res["shared"] else ""
    print(f"scope: {res['scope'].upper()}{why}")
    print(f"checks: {', '.join(res['checks']) or '-'}")
    print(f"sequences: {', '.join(res['sequences']) or '-'}")
    print(f"requirements: {', '.join(res['requirements']) or '-'}")
    n = len(res["tests_to_run"])
    tail = f": {', '.join(res['tests_to_run'][:6])}{' ...' if n > 6 else ''}" if res["scope"] == "selective" else ""
    print(f"re-run {n} of {res['total_tests']} trace(s){tail}")
    for r in res["reasons"]:
        print(f"note: {r}")
    if res["example"]:
        print("note: example/ changed: re-run the quickstart")
    if a.out:
        vc.refuse_overwrite(a.out)
        vc.write_json(a.out, res)
        print(f"impact written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
