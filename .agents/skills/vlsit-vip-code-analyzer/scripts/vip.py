#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""vip: one run-aware command for the whole VLSIT ASIC VIP Design AI Flow.

It finds the run directory, takes paths and settings from the run state, and calls the
right script. Commands stay short, so agents spend tokens on engineering, not on paths.

    python3 vip.py [--run RUN] <command> [args]

Run and settings   init ROOT TAG [SPEC] | status | next | brief [S#] | set k=v ... | get | doctor
Gates and stages   gate G# APPROVED|REJECTED|PENDING --by NAME | stage S# | require S# | check [S#]
Specification      scaffold TAG --title T --standard S -o FILE | validate [FILE] | query <sub> ... | scan scan|report ... | rules <ID|PREFIX>...
Plan, architecture plan | lint [plan|impl|qual|release] | config [--profile P]
Generate, build    gen | gen-profile --profile P | worklist [--n N --kind K --show] | impl-check ... | check-vip [--mode all|lint|uvm] [--record]
Qualify, release   qual-init | qual-run [--impacted] | qual-collect | qual-item lint|compile|coverage ... | manifest | diff OLD NEW
Existing code      init ROOT TAG --mode reverse --code DIR | inventory [summary|show KIND] | from-code --title T --standard S | verify-code | adopt
Fix a VIP          init ROOT TAG --mode bugfix --base-run RUN | bug new|list|show|set|report | carry-gates --by NAME | impact | carry
Add a feature      init ROOT TAG --mode feature --base-run RUN | delta | port | impact [--files F..] | carry | qual-run --impacted

Settings (vip set key=value): author, project, profile, reviewer, build_cmd, run_cmd, seeds, uvm_home, version.
Output is compact; scripts that print findings accept --full for every finding.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vip_state as vs  # noqa: E402

STATE_CMDS = {"status", "set", "get", "gate", "stage", "require", "next", "check", "carry-gates"}
FLOW_ONLY = {"plan", "lint", "config", "gen", "gen-profile", "worklist", "impl-check", "check-vip", "qual-init", "qual-run",
             "qual-collect", "qual-item", "manifest", "port", "carry"}
STAGE_OF_LINT = {"S0": "plan", "S1": "plan", "S2": "plan", "S3": "plan", "S4": "impl", "S5": "qual", "S6": "release", "S7": "release"}


def find_script(name: str) -> Path:
    if (HERE / name).is_file():
        return HERE / name
    for sib in sorted(HERE.parent.parent.glob("*/scripts")):
        if (sib / name).is_file():
            return sib / name
    raise SystemExit(f"error: {name} is not available; install the skill that bundles it (all vlsit-vip-* skills side by side)")


RUN_PREFIXES: list[str] = []


def shorten(text: str) -> str:
    """Replace the run directory path by <run> so long absolute paths do not cost tokens."""
    for pre in RUN_PREFIXES:
        text = text.replace(pre + "\\", "<run>/").replace(pre + "/", "<run>/").replace(pre, "<run>")
    return text


def call(script: str, args: list[str]) -> int:
    r = subprocess.run([sys.executable, str(find_script(script)), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    sys.stdout.write(shorten(r.stdout))
    sys.stderr.write(shorten(r.stderr))
    return r.returncode


def pop_opt(args: list[str], name: str, default: str | None = None) -> str | None:
    if name in args:
        i = args.index(name)
        val = args[i + 1] if i + 1 < len(args) else default
        del args[i:i + 2]
        return val
    return default


def need(st: dict, key: str, why: str) -> str:
    v = st["settings"].get(key, "")
    if not v:
        raise SystemExit(f"error: setting '{key}' is empty ({why}); run: vip set {key}=<value>")
    return v


def spec_profile(spec: Path, st: dict, given: str | None) -> str:
    if given:
        return given
    if st["settings"].get("profile"):
        return st["settings"]["profile"]
    import vip_common as vc
    profs = [p["profile_id"] for p in vc.load_spec(spec).rows("profiles")]
    if len(profs) == 1:
        return profs[0]
    raise SystemExit(f"error: choose a profile: vip set profile=<one of {', '.join(profs)}>")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # code under analysis may hold non-ASCII text; never crash on it
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    argv = sys.argv[1:]
    run_arg = pop_opt(argv, "--run")
    if not argv or argv[0] in ("help", "-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]

    # commands that need no run
    if cmd == "doctor":
        return call("check_env.py", rest)
    if cmd == "rules":
        return call("rule_lookup.py", rest)
    if cmd == "scaffold":
        if rest and not rest[0].startswith("-"):
            rest = ["--tag", rest[0], *rest[1:]]
        rest = ["--out" if x == "-o" else x for x in rest]
        return call("spec_scaffold.py", rest)
    if cmd == "init":
        return call("vip_state.py", ["init", *rest])

    if cmd == "brief":
        try:
            run = vs.resolve_run(run_arg)
            st = vs.load(run)
            stage = rest[0] if rest else st["stage"]
            return call("stage_brief.py", [stage, "--run", str(run)])
        except SystemExit:
            return call("stage_brief.py", rest or ["--all"])

    explicit_file = any(a.endswith(".md") for a in rest)
    if cmd in ("validate", "query", "scan") and explicit_file:
        try:
            run = vs.resolve_run(run_arg)
        except SystemExit:  # a file was given and no run exists: work on the file alone
            if cmd == "validate":
                return call("validate_vip_spec.py", rest)
            return call("spec_query.py" if cmd == "query" else "scan_normative.py", rest)
    run = vs.resolve_run(run_arg)
    RUN_PREFIXES.extend(sorted({str(run), run.as_posix(), str(run).replace("/", "\\")}, key=len, reverse=True))
    st = vs.load(run)
    p = vs.paths(run, st)
    tag, S = st["tag"], st["settings"]
    base = ["--run", str(run)]

    if cmd in STATE_CMDS:
        return call("vip_state.py", [*base, cmd, *rest])

    if vs.external(st) and cmd in FLOW_ONLY:
        raise SystemExit(f"error: vip {cmd} applies to VIPs generated by this flow; this run holds external code (layout external). "
                         "Use the project's own build and regression, vip bug, vip impact --files, and the regression report")

    if cmd == "inventory":
        inv = run / "00_code" / "inventory.json"
        if rest and rest[0] in ("summary", "show"):
            if not inv.is_file():
                raise SystemExit("error: run vip inventory first")
            return call("vip_inventory.py", [rest[0], str(inv), *rest[1:]])
        code = st.get("code_dir") or pop_opt(rest, "--code")
        if not code:
            raise SystemExit("error: no code directory; start the run with: vip init <root> <tag> --mode reverse --code <dir>")
        if inv.exists():
            print("inventory exists (outputs are never overwritten); use: vip inventory summary")
            return 0
        (run / "00_code").mkdir(exist_ok=True)
        return call("vip_inventory.py", ["scan", code, "--out", str(inv), *rest])
    if cmd == "from-code":
        inv = run / "00_code" / "inventory.json"
        if not inv.is_file():
            raise SystemExit("error: run vip inventory first")
        title, standard = pop_opt(rest, "--title"), pop_opt(rest, "--standard")
        if not title or not standard:
            raise SystemExit('usage: vip from-code --title "<name>" --standard "<id and revision>" [--interface NAME --item CLASS --cfg CLASS]')
        if p["spec"].exists():
            raise SystemExit(f"error: {p['spec'].name} exists; outputs are never overwritten")
        return call("spec_from_code.py", ["draft", str(inv), "--tag", tag, "--title", title, "--standard", standard,
                                          "--out", str(p["spec"]), "--report", str(run / "00_code" / "draft_report.md"), *rest])
    if cmd == "verify-code":
        return call("spec_from_code.py", ["verify", str(p["spec"]), "--root", st.get("code_dir") or str(p["vip"]), *rest])
    if cmd == "adopt":
        if not st.get("code_dir"):
            raise SystemExit("error: adopt is for reverse runs (--mode reverse --code DIR)")
        return call("vip_change.py", ["adopt", "--code", st["code_dir"], "--out", str(p["vip"])])
    if cmd == "bug":
        (run / "00_change").mkdir(exist_ok=True)
        return call("vip_bug.py", ["--log", str(run / "00_change" / "bug_log.csv"), "--vip-dir", str(p["vip"]), *rest])
    if cmd == "delta":
        if not st.get("base_run"):
            raise SystemExit("error: delta compares with the base run; start the run with --mode feature --base-run RUN")
        base_spec = Path(st["base_run"]) / "01_spec" / f"{tag}_vip_spec.md"
        out = run / "00_change" / "spec_delta.md"
        extra = ["--out", str(out)] if not out.exists() else []
        return call("vip_change.py", ["delta", str(base_spec), str(p["spec"]), *extra, *rest])
    if cmd == "impact":
        if not st.get("base_run"):
            raise SystemExit("error: impact compares with the base run; start the run with --mode bugfix|feature --base-run RUN")
        base_tree = Path(st["base_run"]) / "04_vip" / f"{tag}_vip"
        reqs = ["--requirements", str(p["reqs"])] if p["reqs"].is_file() else []
        if "--files" in rest or "--ids" in rest:
            args = ["--new", str(p["vip"]), *reqs, *rest]
        else:
            args = ["--base", str(base_tree), "--new", str(p["vip"]), *reqs, *rest]
        (run / "00_change").mkdir(exist_ok=True)
        out = run / "00_change" / "impact.json"
        n = 2
        while out.exists():
            out = run / "00_change" / f"impact_{n}.json"
            n += 1
        return call("vip_impact.py", [*args, "--out", str(out)])
    if cmd == "port":
        if st.get("mode") != "feature":
            raise SystemExit("error: port is for feature runs")
        base = Path(st["base_run"])
        base_tree = base / "04_vip" / f"{tag}_vip"
        if p["vip"].exists():
            raise SystemExit(f"error: {p['vip']} exists; porting never overwrites")
        if vs.cmd_stage(run, "S4", False) != 0:
            return 1
        return call("vip_port.py", ["--current", str(base_tree), "--old-config", str(base / "03_arch" / "vip_config.json"),
                                    "--new-config", str(p["config"]), "--out-dir", str(p["vip"]), "--requirements", str(p["reqs"]),
                                    "--report", str(run / "00_change" / "port_report.md"), *rest])
    if cmd == "carry":
        base = Path(st["base_run"]) if st.get("base_run") else None
        imp = sorted((run / "00_change").glob("impact*.json"))
        if base is None or not imp:
            raise SystemExit("error: run vip impact first (carry needs the impact of the change)")
        if p["evidence"]:
            raise SystemExit("error: evidence exists; carry creates it once")
        base_ev = sorted((base / "05_qual").glob("qual_evidence*.json"))
        if not base_ev:
            raise SystemExit("error: the base run has no qualification evidence to carry")
        profile = spec_profile(p["spec"], st, pop_opt(rest, "--profile"))
        out = p["qual"] / "qual_evidence.json"
        rc = call("create_qual_matrix.py", ["--requirements", str(p["reqs"]), "--spec", str(p["spec"]), "--profile", profile,
                                            "--vip", f"{tag}_vip", "--out", str(out)])
        if rc:
            return rc
        bug_log = run / "00_change" / "bug_log.csv"
        extra = ["--bug-log", str(bug_log)] if bug_log.is_file() else []
        return call("vip_change.py", ["carry", "--evidence", str(out), "--base-evidence", str(base_ev[0]), "--impact", str(imp[-1]),
                                      "--base-run", base.name, *extra, *rest])

    if cmd == "validate":
        spec = rest.pop(0) if rest and rest[0].endswith(".md") else str(p["spec"])
        return call("validate_vip_spec.py", [spec, *rest])
    if cmd == "query":
        if rest and rest[0] in ("outline", "rows", "get", "refs", "todo") and not (len(rest) > 1 and rest[1].endswith(".md")):
            rest.insert(1, str(p["spec"]))
        return call("spec_query.py", rest)
    if cmd == "scan":
        if rest and rest[0] == "report" and "--spec" not in rest:
            rest += ["--spec", str(p["spec"])]
        return call("scan_normative.py", rest)

    if cmd == "plan":
        if p["reqs"].exists():
            raise SystemExit("error: the plan exists. A changed specification needs a new run (vip init); outputs are never overwritten")
        reviewer = S.get("reviewer", "")
        args = [str(p["spec"]), "--out-dir", str(p["plan"]), "--update-spec", str(p["plan"] / f"{tag}_vip_spec_traced.md")]
        args += ["--status", "reviewed", "--reviewer", reviewer] if reviewer else ["--status", "draft"]
        return call("extract_requirements.py", [*args, *rest])
    if cmd == "lint":
        stage = rest.pop(0) if rest and rest[0] in ("plan", "impl", "qual", "release") else STAGE_OF_LINT[st["stage"]]
        args = ["--requirements", str(p["reqs"]), "--stage", stage, "--spec", str(p["spec"])]
        if stage != "plan":
            args += ["--vip-dir", str(p["vip"])]
        if stage in ("qual", "release"):
            for e in p["evidence"]:
                args += ["--evidence", str(e)]
        return call("trace_lint.py", [*args, *rest])
    if cmd == "config":
        profile = spec_profile(p["spec"], st, pop_opt(rest, "--profile"))
        cfg_path = p["config"] if profile == S.get("profile", profile) else run / "03_arch" / f"vip_config_{profile}.json"
        args = ["--spec", str(p["spec"]), "--requirements", str(p["reqs"]), "--profile", profile]
        if cfg_path.exists():
            return call("derive_vip_config.py", [*args, "--check", str(cfg_path)])
        rc = call("derive_vip_config.py", [*args, "--out", str(cfg_path), "--version", S.get("version", "0.1.0")])
        if rc == 0 and not S.get("profile"):
            vs.cmd_set(run, [f"profile={profile}"])
        return rc

    if cmd == "gen":
        if vs.cmd_stage(run, "S4", False) != 0:
            return 1
        if p["vip"].exists():
            raise SystemExit(f"error: {p['vip']} exists; generation never overwrites. Start a new run or use worklist/impl-check")
        author, project = need(st, "author", "file headers"), need(st, "project", "file headers")
        return call("gen_vip_skeleton.py", ["--config", str(p["config"]), "--out-dir", str(p["vip"]), "--author", author,
                                            "--project", project, "--requirements", str(p["reqs"]), *rest])
    if cmd == "gen-profile":
        # a further profile is a separate build: its own config, VIP tree, and evidence file
        profile = pop_opt(rest, "--profile")
        if not profile or profile == S.get("profile"):
            raise SystemExit("usage: vip gen-profile --profile <other PROF-nn>; the first profile uses vip gen")
        cfg_path = run / "03_arch" / f"vip_config_{profile}.json"
        if not cfg_path.is_file():
            raise SystemExit(f"error: run vip config --profile {profile} first")
        out = run / f"04_vip_{profile}" / f"{tag}_vip"
        return call("gen_vip_skeleton.py", ["--config", str(cfg_path), "--out-dir", str(out), "--author", need(st, "author", "file headers"),
                                            "--project", need(st, "project", "file headers"), "--requirements", str(p["reqs"]), *rest])
    if cmd == "worklist":
        return call("vip_worklist.py", ["--vip-dir", str(p["vip"]), *rest])
    if cmd == "impl-check":
        return call("impl_check.py", ["--vip-dir", str(p["vip"]), *rest])
    if cmd == "check-vip":
        args = ["--vip-dir", str(p["vip"]), "--log-dir", str(p["qual"] / "compile_logs")]
        if S.get("uvm_home"):
            args += ["--uvm-home", S["uvm_home"]]
        if "--record" in rest:
            rest.remove("--record")
            if not p["evidence"]:
                raise SystemExit("error: run vip qual-init first; --record updates qual_evidence.json")
            args += ["--record", str(p["evidence"][0])]
        return call("vip_compile.py", [*args, *rest])

    if cmd == "qual-init":
        profile = spec_profile(p["spec"], st, pop_opt(rest, "--profile"))
        out = p["qual"] / ("qual_evidence.json" if not (p["qual"] / "qual_evidence.json").exists() else f"qual_evidence_{profile}.json")
        return call("create_qual_matrix.py", ["--requirements", str(p["reqs"]), "--spec", str(p["spec"]), "--profile", profile,
                                              "--vip", f"{tag}_vip", "--out", str(out), *rest])
    if cmd == "qual-run":
        if not p["evidence"]:
            raise SystemExit("error: run vip qual-init first")
        n = 1
        while (p["qual"] / ("logs" if n == 1 else f"logs_{n}")).exists():
            n += 1
        logdir = p["qual"] / ("logs" if n == 1 else f"logs_{n}")
        if "--impacted" in rest:
            rest.remove("--impacted")
            todo = [e["test"] for e in json.loads(p["evidence"][0].read_text(encoding="utf-8"))["entries"] if e["status"] != "PASS"]
            if not todo:
                print("nothing to run: every trace is PASS (carried or already run)")
                return 0
            rest += ["--tests", "^(" + "|".join(sorted(set(todo))) + ")$"]
        args = ["--evidence", str(p["evidence"][0]), "--config", str(p["config"]), "--spec", str(p["spec"]),
                "--vip-dir", str(p["vip"]), "--log-dir", str(logdir), "--build-cmd", need(st, "build_cmd", "simulator build"),
                "--run-cmd", need(st, "run_cmd", "simulator run"), "--seeds", S.get("seeds", "1")]
        return call("run_qual.py", [*args, *rest])
    if cmd == "qual-collect":
        if not p["evidence"]:
            raise SystemExit("error: run vip qual-init first")
        sums = sorted(p["qual"].glob("logs*/run_summary.json"))
        if not sums:
            raise SystemExit("error: no run_summary.json; run vip qual-run first")
        return call("collect_qual_results.py", ["results", "--evidence", str(p["evidence"][0]), "--summary", str(sums[-1]),
                                                "--min-seeds", S.get("seeds", "1"), *rest])
    if cmd == "qual-item":
        if not p["evidence"] or len(rest) < 1 or rest[0] not in ("lint", "compile", "coverage"):
            raise SystemExit("usage: vip qual-item lint|compile|coverage --status PASS|FAIL|NOT_RUN [--log F] [--note T] [--database D] [--summary T]")
        return call("collect_qual_results.py", ["item", "--evidence", str(p["evidence"][0]), "--item", rest[0], *rest[1:]])
    if cmd == "manifest":
        out = p["release"] / "vip_manifest.json"
        args = ["--vip-dir", str(p["vip"]), "--out", str(out), "--requirements", str(p["reqs"])]
        for e in p["evidence"]:
            args += ["--evidence", str(e)]
        if (p["release"] / "release_notes.md").is_file():
            args += ["--release-notes", str(p["release"] / "release_notes.md")]
        return call("make_manifest.py", [*args, *rest])
    if cmd == "diff":
        if len(rest) < 2:
            raise SystemExit("usage: vip diff OLD NEW")
        return call("spec_diff.py", ["--old", rest[0], "--new", rest[1], "--out", str(p["release"] / "spec_diff.md")])

    raise SystemExit(f"error: unknown command '{cmd}'; run: vip help")


if __name__ == "__main__":
    sys.exit(main())
