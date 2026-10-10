#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run directory, settings, gate, and next-step bookkeeping of the VLSIT ASIC VIP flow.

Commands
    init    ROOT TAG [SPEC]        create <tag>_vip_run_NNN (never reuses a number); remembers it in ROOT/.vip_current
    status                         one line per gate
    set     key=value ...          store settings (author, project, profile, reviewer, build_cmd, run_cmd, seeds, uvm_home)
    get                            print the settings
    gate    G1 APPROVED --by NAME [--note T] [--artifact REL ...]
    stage   S3                     move to a stage after checking prerequisites
    require S4                     exit 1 when a prerequisite gate is not approved or an approved artifact changed
    next                           the next action and the command to run
    check   [S1..S7]               run the exit check of the current (or given) stage

The run is found from --run, then $VLSIT_VIP_RUN, then by walking up from the current
directory for vip_state.json, then through a .vip_current pointer file. A gate is recorded
as APPROVED only after the user replied APPROVE in chat to the presented version; the
approval stores the SHA-256 of the approved artifacts and a changed artifact reopens it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402

SUBDIRS = ["01_spec", "02_plan", "03_arch", "04_vip", "05_qual", "06_release"]
STAGES = [f"S{i}" for i in range(8)]
GATES = {
    "G1": "specification approval (VIP-0)",
    "G2": "plan and architecture approval",
    "G3": "qualification evidence review (VIP-2)",
    "G4": "release approval (VIP-3)",
}
REQUIRES = {
    "S0": [], "S1": [], "S2": ["G1"], "S3": ["G1"], "S4": ["G1", "G2"], "S5": ["G1", "G2"],
    "S6": ["G1", "G2", "G3"], "S7": ["G1", "G2", "G3"],
}
GATE_NEEDS = {"G2": ["G1"], "G3": ["G1", "G2"], "G4": ["G1", "G2", "G3"]}
DEFAULT_ARTIFACTS = {
    "G1": lambda tag: [f"01_spec/{tag}_vip_spec.md"],
    "G2": lambda tag: ["02_plan/requirements.csv", "02_plan/vplan.md", "03_arch/vip_config.json", "03_arch/vip_arch.md"],
    "G3": lambda tag: ["05_qual/qualification_report.md"],
    "G4": lambda tag: ["06_release/release_notes.md", "06_release/vip_manifest.json"],
}
SETTING_KEYS = ["author", "project", "profile", "reviewer", "build_cmd", "run_cmd", "seeds", "uvm_home", "version"]


# ---------------------------------------------------------------- run resolution and state

def resolve_run(explicit: str | None = None) -> Path:
    cands: list[str] = [explicit] if explicit else []
    if os.environ.get("VLSIT_VIP_RUN"):
        cands.append(os.environ["VLSIT_VIP_RUN"])
    for c in cands:
        if (Path(c) / "vip_state.json").is_file():
            return Path(c).resolve()
    here = Path.cwd().resolve()
    for d in [here, *here.parents]:
        if (d / "vip_state.json").is_file():
            return d
        ptr = d / ".vip_current"
        if ptr.is_file():
            p = Path(ptr.read_text(encoding="utf-8").strip())
            if (p / "vip_state.json").is_file():
                return p.resolve()
    raise SystemExit("error: no run found; use --run, set VLSIT_VIP_RUN, or run from a run directory (vip init ...)")


def load(run: Path) -> dict:
    p = run / "vip_state.json"
    if not p.is_file():
        raise SystemExit(f"error: no vip_state.json in {run}")
    st = json.loads(p.read_text(encoding="utf-8"))
    st.setdefault("settings", {})
    return st


def save(run: Path, st: dict) -> None:
    (run / "vip_state.json").write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def log(st: dict, event: str, detail: str = "") -> None:
    st["history"].append({"time": vc.now_iso(), "event": event, "detail": detail})


def paths(run: Path, st: dict) -> dict[str, Path]:
    tag = st["tag"]
    q = run / "05_qual"
    return {
        "spec": run / "01_spec" / f"{tag}_vip_spec.md", "plan": run / "02_plan", "reqs": run / "02_plan" / "requirements.csv",
        "config": run / "03_arch" / "vip_config.json", "arch": run / "03_arch" / "vip_arch.md",
        "vip": run / "04_vip" / f"{tag}_vip", "qual": q, "evidence": sorted(q.glob("qual_evidence*.json")),
        "release": run / "06_release",
    }


# ---------------------------------------------------------------- commands

def cmd_init(a: argparse.Namespace) -> int:
    if not vc.TAG_RE.match(a.tag):
        raise SystemExit("error: TAG must be 2-8 lowercase alphanumerics starting with a letter")
    root = Path(a.root)
    root.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for d in root.iterdir() if (m := re.fullmatch(rf"{a.tag}_vip_run_(\d{{3}})", d.name))]
    run = root / f"{a.tag}_vip_run_{(max(nums) + 1 if nums else 1):03d}"
    run.mkdir()
    for s in SUBDIRS:
        (run / s).mkdir()
    st = {"schema": "vlsit_vip_state/1", "tag": a.tag, "run": run.name, "created": vc.now_iso(), "spec": {},
          "stage": "S0", "settings": {}, "history": [],
          "gates": {g: {"status": "PENDING", "by": "", "date": "", "note": "", "artifacts": {}} for g in GATES}}
    if a.spec:
        src = Path(a.spec)
        if not src.is_file():
            raise SystemExit(f"error: specification not found: {src}")
        shutil.copyfile(src, run / "01_spec" / f"{a.tag}_vip_spec.md")
        st["spec"] = {"source": str(src), "sha256": vc.sha256_file(src)}
    log(st, "init", f"run created for tag {a.tag}")
    save(run, st)
    (root / ".vip_current").write_text(str(run.resolve()) + "\n", encoding="utf-8")
    print(run.resolve())
    return 0


def drift(run: Path, st: dict) -> list[str]:
    out = []
    for g, info in st["gates"].items():
        if info["status"] != "APPROVED":
            continue
        for rel, digest in info["artifacts"].items():
            p = run / rel
            if not p.is_file():
                out.append(f"{g}: approved artifact missing: {rel}")
            elif vc.sha256_file(p) != digest:
                out.append(f"{g}: approved artifact changed after approval: {rel}")
    return out


def reopen_changed(run: Path, st: dict) -> list[str]:
    msgs = drift(run, st)
    for m in msgs:
        g = m.split(":")[0]
        if st["gates"][g]["status"] == "APPROVED":
            st["gates"][g]["status"] = "PENDING"
            log(st, "gate_reopened", m)
    order = list(GATES)
    for i, g in enumerate(order):
        if st["gates"][g]["status"] != "APPROVED":
            for later in order[i + 1:]:
                if st["gates"][later]["status"] == "APPROVED":
                    st["gates"][later]["status"] = "PENDING"
                    log(st, "gate_reopened", f"{later}: earlier gate {g} is not approved")
                    msgs.append(f"{later}: reopened because {g} is not approved")
            break
    return msgs


def cmd_status(run: Path) -> int:
    st = load(run)
    reopen_changed(run, st)
    st["stage"] = next_action(run, st)[0]
    save(run, st)
    gates = "  ".join(f"{g}={i['status']}" for g, i in st["gates"].items())
    print(f"{st['run']}  stage {st['stage']}  {gates}")
    for m in drift(run, st):
        print(f"DRIFT {m}")
    return 0


def cmd_set(run: Path, pairs: list[str]) -> int:
    st = load(run)
    for p in pairs:
        k, sep, v = p.partition("=")
        if not sep or k not in SETTING_KEYS:
            raise SystemExit(f"error: use key=value with key in {SETTING_KEYS}")
        st["settings"][k] = v
    log(st, "settings", ",".join(p.split("=")[0] for p in pairs))
    save(run, st)
    print("ok")
    return 0


def cmd_get(run: Path) -> int:
    st = load(run)
    for k in SETTING_KEYS:
        print(f"{k}={st['settings'].get(k, '')}")
    return 0


def cmd_gate(run: Path, a: argparse.Namespace) -> int:
    st = load(run)
    if a.gate not in GATES:
        raise SystemExit(f"error: gate must be one of {list(GATES)}")
    if a.decision == "APPROVED":
        if not a.by:
            raise SystemExit("error: --by is required to record an approval")
        for need in GATE_NEEDS.get(a.gate, []):
            if st["gates"][need]["status"] != "APPROVED":
                raise SystemExit(f"error: {a.gate} cannot be approved before {need}")
        rels = list(a.artifact or DEFAULT_ARTIFACTS[a.gate](st["tag"]))
        if a.gate == "G3":
            rels += [p.relative_to(run).as_posix() for p in (run / "05_qual").glob("qual_evidence*.json")]
        arts = {}
        for rel in rels:
            if not (run / rel).is_file():
                raise SystemExit(f"error: artifact to approve does not exist: {rel}")
            arts[rel] = vc.sha256_file(run / rel)
        st["gates"][a.gate] = {"status": "APPROVED", "by": a.by, "date": vc.now_iso(), "note": a.note, "artifacts": arts}
    else:
        st["gates"][a.gate].update({"status": a.decision, "by": a.by, "date": vc.now_iso(), "note": a.note, "artifacts": {}})
    log(st, f"gate_{a.decision.lower()}", f"{a.gate} {a.note}".strip())
    save(run, st)
    print(f"{a.gate} {a.decision}")
    return 0


def blockers(run: Path, st: dict, stage: str) -> list[str]:
    reopen_changed(run, st)
    return [f"{g} is {st['gates'][g]['status']} ({GATES[g]})" for g in REQUIRES[stage] if st["gates"][g]["status"] != "APPROVED"]


def cmd_stage(run: Path, stage: str, move: bool) -> int:
    st = load(run)
    if stage not in STAGES:
        raise SystemExit(f"error: stage must be one of {STAGES}")
    missing = blockers(run, st, stage)
    if missing:
        save(run, st)
        for m in missing:
            print(f"blocked: {m}")
        return 1
    if move:
        st["stage"] = stage
        log(st, "stage", stage)
    save(run, st)
    print(f"stage {stage}" if move else f"{stage} prerequisites satisfied")
    return 0


def count_todo(vip: Path) -> int:
    if not vip.is_dir():
        return 0
    n = 0
    for f in vip.rglob("*"):
        if f.is_file() and f.suffix in (".sv", ".svh"):
            t = f.read_text(encoding="utf-8", errors="replace")
            n += len(re.findall(r"VIP_TODO\(", t)) + len(re.findall(r"`VLSIT_VIP_CHK_TODO\(", t))
    return n


def next_action(run: Path, st: dict) -> tuple[str, str, str]:
    """Return (stage, action, command) for the first step that is not yet done."""
    p = paths(run, st)
    g = {k: v["status"] == "APPROVED" for k, v in st["gates"].items()}
    tag = st["tag"]
    if not p["spec"].is_file():
        return "S0", "create the specification skeleton", f"vip scaffold {tag} --title \"<name>\" --standard \"<id rev>\" -o <spec.md> ; vip init <root> {tag} <spec.md>"
    if not g["G1"]:
        return "S1", "complete the specification, validate, get Gate 1", "vip validate ; vip query todo ; (user APPROVE) vip gate G1 APPROVED --by <NAME>"
    if not p["reqs"].is_file():
        return "S2", "derive the verification plan", "vip plan"
    if not p["config"].is_file() or not p["arch"].is_file():
        return "S3", "derive vip_config.json and write vip_arch.md", "vip config"
    if not g["G2"]:
        return "S3", "Gate 2: present plan and architecture", "(user APPROVE) vip gate G2 APPROVED --by <NAME>"
    if not p["vip"].is_dir():
        return "S4", "generate the VIP", "vip gen"
    todo = count_todo(p["vip"])
    if todo and not p["evidence"]:
        return "S4", f"{todo} stub marker(s) remain; implement the worklist", "vip worklist --n 5 ; vip check-vip ; vip lint impl"
    if not p["evidence"]:
        return "S5", "create the qualification matrix", "vip qual-init"
    if not g["G3"]:
        return "S5", "finish qualification, then Gate 3", "vip qual-run ; vip qual-collect ; vip check-vip --record ; vip lint qual ; (user APPROVE) vip gate G3 APPROVED --by <NAME>"
    if not (p["release"] / "vip_manifest.json").is_file():
        return "S6", "README, trial, release notes, manifest", "vip manifest ; vip lint release"
    if not g["G4"]:
        return "S7", "Gate 4: present the release", "(user APPROVE) vip gate G4 APPROVED --by <NAME>"
    return "S7", "done: the release is approved", "vip diff <old> <new> on a specification change"


def cmd_next(run: Path) -> int:
    st = load(run)
    reopen_changed(run, st)
    save(run, st)
    stage, action, cmd = next_action(run, st)
    if st["stage"] != stage:
        st["stage"] = stage
        log(st, "stage", stage)
        save(run, st)
    print(f"{st['run']}  stage {st['stage']}")
    print(f"next: {action}")
    print(f"run : {cmd}")
    return 0


def cmd_check(run: Path, stage: str | None) -> int:
    import trace_lint as tl
    import validate_vip_spec as vv
    st = load(run)
    stage = (stage or st["stage"]).upper()
    p = paths(run, st)
    rep = None
    if stage in ("S0", "S1"):
        if not p["spec"].is_file():
            print("S1 check: specification missing")
            return 1
        rep = vv.validate(vc.load_spec(p["spec"]), template=(stage == "S0"), strict_inj=False)
    elif stage == "S2":
        rep = tl.lint(str(p["reqs"]), "plan", str(p["spec"]))
    elif stage == "S3":
        rep = vc.Report("S3 architecture check", str(p["config"]))
        if not p["config"].is_file():
            rep.error("AR-01", "vip_config.json is missing")
        else:
            cfg = json.loads(p["config"].read_text(encoding="utf-8"))
            if cfg.get("schema") != "vlsit_vip_config/1":
                rep.error("AR-02", "unsupported config schema")
            if [c["index"] for c in cfg.get("checks", [])] != list(range(len(cfg.get("checks", [])))):
                rep.error("AR-03", "check indices are not 0..N-1 in order")
        if not p["arch"].is_file():
            rep.error("AR-04", "vip_arch.md is missing")
    elif stage == "S4":
        rep = tl.lint(str(p["reqs"]), "impl", str(p["spec"]), str(p["vip"]))
    elif stage == "S5":
        rep = tl.lint(str(p["reqs"]), "qual", str(p["spec"]), str(p["vip"]), None, [str(e) for e in p["evidence"]])
    else:
        rep = tl.lint(str(p["reqs"]), "release", str(p["spec"]), str(p["vip"]), None, [str(e) for e in p["evidence"]])
    rep.print_text()
    return 1 if rep.errors else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("root")
    i.add_argument("tag")
    i.add_argument("spec", nargs="?")
    sub.add_parser("status")
    s = sub.add_parser("set")
    s.add_argument("pairs", nargs="+")
    sub.add_parser("get")
    g = sub.add_parser("gate")
    g.add_argument("gate")
    g.add_argument("decision", choices=["APPROVED", "REJECTED", "PENDING"])
    g.add_argument("--by", default="")
    g.add_argument("--note", default="")
    g.add_argument("--artifact", action="append")
    t = sub.add_parser("stage")
    t.add_argument("stage")
    q = sub.add_parser("require")
    q.add_argument("stage")
    sub.add_parser("next")
    c = sub.add_parser("check")
    c.add_argument("stage", nargs="?")
    a = ap.parse_args()
    if a.cmd == "init":
        return cmd_init(a)
    run = resolve_run(a.run)
    return {"status": lambda: cmd_status(run), "set": lambda: cmd_set(run, a.pairs), "get": lambda: cmd_get(run),
            "gate": lambda: cmd_gate(run, a), "stage": lambda: cmd_stage(run, a.stage, True),
            "require": lambda: cmd_stage(run, a.stage, False), "next": lambda: cmd_next(run),
            "check": lambda: cmd_check(run, a.stage)}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
