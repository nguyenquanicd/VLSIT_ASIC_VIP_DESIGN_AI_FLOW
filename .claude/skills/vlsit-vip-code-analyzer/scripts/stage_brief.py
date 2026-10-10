#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Print a short brief for one stage of the VIP flow: what to do, with which commands,
which rule groups to look up, when the stage is done, and what the gate asks.

The brief replaces reading several reference documents at the start of a stage.
Look up rule text only for the groups it names (python3 rule_lookup.py <PREFIX>).

Usage:
    python stage_brief.py S4 [--run RUN_DIR]
    python stage_brief.py --all            one line per stage
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BRIEFS = {
"S0": {
 "title": "Scope and reuse (skill vlsit-vip-spec-intake)",
 "goal": "Fix the standard revision, roles, profiles, options, reuse decision, and tools.",
 "do": ["Ask in ONE question: standard file and exact revision, roles, profile, options in scope, output root, project, author, simulator/UVM, existing VIP to reuse.",
        "vip scaffold <tag> --title \"<name>\" --standard \"<id and revision>\" -o <spec.md>   (spec skeleton with all defaults filled)",
        "vip init <root> <tag> <spec.md>   (creates the numbered run directory)"],
 "rules": ["VSCP", "VNAM"],
 "done": "Sections 1 to 3 of the specification answered; run directory exists.",
 "gate": None},
"S1": {
 "title": "Requirement extraction (skill vlsit-vip-spec-intake)",
 "goal": "Fill the specification from the standard; every normative sentence classified; Gate 1.",
 "do": ["vip scan scan <standard.txt> --out normative_candidates.csv",
        "Fill Sections 4 to 12 and 14 (fill only the tables the scaffold marks with placeholders; use `vip query` to re-read, not the whole file).",
        "Write a check expression (Section 8.1) for every SVA requirement; add one INJ row for every MUST check.",
        "Classify candidates in normative_map.csv, then: vip scan report normative_map.csv --spec <spec>",
        "vip validate   (exit 0 required; grouped output, add --full for every finding)"],
 "rules": ["VNAM", "VCHK", "VQUA"],
 "done": "validate exits 0; scan report exits 0; extraction_report.md written.",
 "gate": "Do you approve specification <file> version N, including <roles, profiles, options> and the listed decisions? Reply APPROVE, REVISE, or STOP."},
"S2": {
 "title": "Verification plan (skill vlsit-vip-vplan)",
 "goal": "Derive IDs and the traceability for every requirement.",
 "do": ["vip plan   (validates, derives IDs, writes requirements.csv, vplan.md, traced spec)",
        "vip lint plan   (exit 0 required)",
        "Read the gaps printed by `vip plan`; a gap that needs a spec change reopens Gate 1."],
 "rules": ["VQUA", "VCHK"],
 "done": "lint plan exits 0 and the gap list is empty or explained.",
 "gate": None},
"S3": {
 "title": "Architecture and API (skill vlsit-vip-architect)",
 "goal": "Fix structure and API, derive vip_config.json, get Gate 2.",
 "do": ["vip config   (derives and checks vip_config.json for the profile in settings)",
        "Write vip_arch.md (template in the skill references): how each UC-01..UC-13 is met.",
        "Ask only for decisions the spec does not settle: profile, simulator and UVM, formal use, reuse."],
 "rules": ["VAPI", "VUVM", "VIFC"],
 "done": "vip config reports 0 problems; vip_arch.md written.",
 "gate": "Do you approve plan and architecture version N, including the listed files, profile, checks, tests, and variants? Reply APPROVE, REVISE, or STOP."},
"S4": {
 "title": "Generate and implement (skill vlsit-vip-generator)",
 "goal": "Generate the VIP tree and complete the stubs until VIP-1 holds.",
 "do": ["vip gen   (needs Gate 2; checks with a spec expression are already complete)",
        "vip worklist --n 5   (next stubs with their requirement context; add --show for the code region)",
        "vip impl-check --id <CHECK_ID> --op SAME|NEXT --ante \"...\" --cons \"...\" --msg \"...\"   (completes one SVA stub)",
        "Edit only the stubs the worklist names: monitor, drivers, sequences, cov sampling (patterns: references/implementation_guide.md).",
        "vip check-vip   (lint + UVM type-check, a few lines)",
        "vip lint impl"],
 "rules": ["VCHK", "VIFC", "VDRV", "VMON", "VSEQ", "VCOV", "VP"],
 "done": "check-vip passes, lint impl exits 0, MUST checks implemented. Qualification stubs may remain.",
 "gate": None},
"S5": {
 "title": "Qualification (skill vlsit-vip-qualifier)",
 "goal": "Evidence from logs that every check fires correctly and every capability works.",
 "do": ["vip qual-init   (matrix, every entry NOT_RUN)",
        "vip worklist --kind test   then implement the counterpart stimulus tasks (qual/<tag>_counterpart.sv)",
        "vip set build_cmd=\"...\" run_cmd=\"...\" seeds=N   then: vip qual-run   and: vip qual-collect",
        "vip check-vip --record   (records lint and compile evidence)",
        "vip lint qual   (exit 0 required)"],
 "rules": ["VQUA", "VP"],
 "done": "lint qual exits 0 with PASS evidence from logs on every variant.",
 "gate": "Do you approve the qualification evidence version N, including variants, seeds, and the listed waivers? Reply APPROVE, REVISE, or STOP."},
"S6": {
 "title": "Package and trial (skill vlsit-vip-release)",
 "goal": "README against the usability contract and a first-time-user trial.",
 "do": ["Complete doc/README.md (sections in references/release_checklist.md).",
        "Run the usability trial with a person who did not build the VIP; if none, record NOT_RUN."],
 "rules": ["VAPI", "VDOC"],
 "done": "README complete; trial recorded.",
 "gate": None},
"S7": {
 "title": "Release and maintenance (skill vlsit-vip-release)",
 "goal": "Manifest, release notes, final lint, Gate 4; diff on spec change.",
 "do": ["Set requirement statuses to qualified or waived in requirements.csv.",
        "vip manifest   then   vip lint release   (exit 0 required)",
        "On a spec change: vip diff <old> <new>"],
 "rules": ["VDOC", "VQUA"],
 "done": "lint release exits 0; release_notes.md written.",
 "gate": "Do you approve release <version> for <spec_rev>, including the listed files, variants, waivers, and limitations? Reply APPROVE, REVISE, or STOP."},
}

# Mode overrides: a run started with --mode reverse|bugfix|feature replaces the fields it names.
OVERRIDES = {
"reverse": {
"S0": {"title": "Inventory of the existing code (skill vlsit-vip-code-analyzer)",
       "goal": "A machine-made index of the code: interface, assertions, classes with roles, config, messages, TODOs.",
       "do": ["vip init <root> <tag> --mode reverse --code <dir>   (once)",
              "vip inventory   (lexical scan, no simulator; writes 00_code/inventory.json)",
              "vip inventory summary   then   vip inventory show assertion|class|covergroup --limit 20   as needed"],
       "rules": ["VNAM"], "done": "inventory.json exists; the summary shows the interface and the classes by role.", "gate": None},
"S1": {"title": "As-built specification (skill vlsit-vip-code-analyzer)",
       "goal": "Draft the specification from the code, then verify every inferred cell; Gate 1.",
       "do": ["vip from-code --title \"<name>\" --standard \"<id rev>\"   (draft; every inferred cell says UNVERIFIED and gives CODE:<file>:<line>)",
              "For each UNVERIFIED mark: open only the CODE region, confirm or correct the row, remove the mark. The code is the evidence, not the truth: a behavior that contradicts the standard is a finding, not a requirement.",
              "Fill what the code cannot show: standard references, strengths, roles, profiles, decisions DEC-nnn (open questions to the user).",
              "vip verify-code   (CODE pointers resolve; reports marks left)   then   vip validate"],
       "rules": ["VNAM", "VCHK"], "done": "verify-code and validate exit 0; no UNVERIFIED mark remains (or each is listed in the Gate note).",
       "gate": "Do you approve the as-built specification <file>, including the open decisions and the listed findings? Reply APPROVE, REVISE, or STOP."},
"S2": {"title": "Adopt the code (skill vlsit-vip-code-analyzer)",
       "goal": "Make the code the base tree of later bugfix and feature runs.",
       "do": ["vip adopt   (copies the code into 04_vip/<tag>_vip; never overwrites)",
              "Start the next run: vip init <root> <tag> --mode bugfix|feature --base-run <this run>"],
       "rules": [], "done": "04_vip/<tag>_vip exists.", "gate": None},
},
"bugfix": {
"S0": {"title": "Defect intake (skill vlsit-vip-bugfix)",
       "goal": "Every defect is a row in the bug log with a symptom and a severity.",
       "do": ["vip bug new --title \"...\" --symptom \"...\" --severity critical|major|minor [--found-in VER] [--req VREQ-..]",
              "vip bug list"],
       "rules": [], "done": "bug_log.csv has the defect(s).", "gate": None},
"S1": {"title": "Root cause and classification (skill vlsit-vip-bugfix)",
       "goal": "Find the cause before touching code; classify it; name what it affects.",
       "do": ["Reproduce with the smallest stimulus; read only the code the symptom points to (vip query get <VREQ>, then the CODE region).",
              "Decide the class: vip (VIP code), trace (wrong ID, expression, or evidence), counterpart (qual model), environment, dut (not a VIP bug: wontfix), spec (the spec is wrong: stop, start a feature run).",
              "vip bug set BUG-nnn class=... status=analyzed   then   req_ids=... files=... status=planned",
              "With the user's OK, carry the gates: vip carry-gates --by <NAME> (refused when an approved file differs)"],
       "rules": ["VCHK", "VQUA"], "done": "every live bug is planned and Gates 1-2 are carried (Gate 1 only for external code).",
       "gate": None},
"S4": {"title": "Test first, then fix (skill vlsit-vip-bugfix)",
       "goal": "A regression test that fails for the bug, a minimal fix, VIP-1 still true.",
       "do": ["Write the regression test (or counterpart stimulus) first and watch it fail; set regression_test=<name> only then.",
              "Fix the smallest region that explains the symptom; do not refactor; do not touch base/.",
              "vip check-vip ; vip lint impl   (external code: the project's own build)",
              "vip bug set BUG-nnn regression_test=<test> fix_summary=\"...\" status=fixed"],
       "rules": ["VCHK", "VCOV", "VP"], "done": "every live bug is fixed; check-vip and lint impl pass.", "gate": None},
"S5": {"title": "Selective re-qualification (skill vlsit-vip-bugfix)",
       "goal": "Re-run only the traces the fix can affect; carry the rest; close the bugs with evidence.",
       "do": ["vip impact   (what changed in 04_vip against the base: scope, checks, requirements, tests to re-run)",
              "vip carry   (evidence from the base: PASS entries of untouched traces carried, the rest NOT_RUN)",
              "vip qual-run --impacted ; vip qual-collect ; vip check-vip --record ; vip lint qual",
              "vip bug set BUG-nnn evidence_log=<log> status=verified   (closed when the regression test is in the tree)",
              "External code: run the project regression, write 05_qual/regression_report.md, same bug transitions."],
       "rules": ["VQUA"], "done": "lint qual exits 0 (or the regression report is complete); bugs verified.",
       "gate": "Do you approve the re-qualification evidence of <version>: <n> bug(s) fixed, <m> trace(s) re-run, <k> carried from <base>? Reply APPROVE, REVISE, or STOP."},
"S6": {"title": "Fix release notes (skill vlsit-vip-bugfix)", "goal": "Release notes list each fix with the test that guards it.",
       "do": ["vip bug report   (table for the notes)", "vip manifest ; vip lint release"], "rules": ["VDOC"],
       "done": "release_notes.md lists bugs, tests, carried and re-run counts, and the patch version.", "gate": None},
},
"feature": {
"S0": {"title": "Change request (skill vlsit-vip-feature)",
       "goal": "The user's new requirement written down with source and acceptance.",
       "do": ["Edit 00_change/change_request.md until no (fill) remains. Ask only what the base specification cannot answer.",
              "vip query outline ; vip query rows requirements   (find the rows the change touches)"],
       "rules": ["VSCP"], "done": "change_request.md complete.", "gate": None},
"S1": {"title": "Specification update (skill vlsit-vip-feature)",
       "goal": "The base specification, changed only where the request needs it; Gate 1 on the delta.",
       "do": ["Add rows with new IDs (never reuse an ID; mark a replaced requirement withdrawn); new SVA rows need a Section 8.1 expression and an INJ row if MUST.",
              "Default behavior must not change unless the request says so: a new option or knob defaults to the old behavior.",
              "vip validate ; vip delta   (rows added, removed, changed per table; suggested version bump)"],
       "rules": ["VNAM", "VCHK", "VAPI"], "done": "validate exits 0; the delta shows only what the request needs.",
       "gate": "Do you approve specification <file> version N with this delta (<added>, <changed>, <removed>)? Reply APPROVE, REVISE, or STOP."},
"S4": {"title": "Port and implement (skill vlsit-vip-feature)",
       "goal": "The implemented VIP carried to the new configuration; only the new stubs are open.",
       "do": ["vip port   (flow layout: skeletons of old and new configuration, three-way merge with your code; conflicts are marked)",
              "Resolve conflicts, then vip worklist --n 5 for the new stubs only; implement; vip check-vip ; vip lint impl",
              "External code: implement in the copied tree with its own build and style; vip impact --files <changed files>"],
       "rules": ["VCHK", "VIFC", "VDRV", "VMON", "VSEQ", "VCOV"], "done": "no conflict marker; check-vip and lint impl pass.", "gate": None},
"S5": {"title": "Selective re-qualification (skill vlsit-vip-feature)",
       "goal": "New traces run; touched traces re-run; the rest carried from the base evidence.",
       "do": ["vip impact ; vip carry", "vip worklist --kind test (new counterpart stimulus only)", "vip qual-run --impacted ; vip qual-collect ; vip check-vip --record ; vip lint qual"],
       "rules": ["VQUA", "VP"], "done": "lint qual exits 0.",
       "gate": "Do you approve the evidence of <version>: <n> new, <m> re-run, <k> carried from <base>? Reply APPROVE, REVISE, or STOP."},
},
}

DISCIPLINE = ("Token discipline: run `vip` commands and read their short output; use `vip query` and `vip rules` instead of "
              "opening whole files; open a file region only when the worklist names it; do not echo generated files; "
              "never edit generated bundled files (base/).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", nargs="?")
    ap.add_argument("--run")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all or not a.stage:
        for k, b in BRIEFS.items():
            print(f"{k}\t{b['title']}\tgate: {'yes' if b['gate'] else 'no'}")
        return 0
    st = a.stage.upper()
    if st not in BRIEFS:
        print(f"error: stage must be one of {list(BRIEFS)}", file=sys.stderr)
        return 1
    b = BRIEFS[st]
    if a.run and (Path(a.run) / "vip_state.json").is_file():
        s = json.loads((Path(a.run) / "vip_state.json").read_text(encoding="utf-8"))
        mode = s.get("mode", "new")
        light = s.get("layout", "flow") == "external"
        gates = " ".join(f"{g}:{i['status'][:4]}" for g, i in s["gates"].items() if not (light and g == "G2"))
        print(f"run {s['run']}  mode {mode}  stage {s['stage']}  gates {gates}")
        b = {**b, **OVERRIDES.get(mode, {}).get(st, {})}
    print(f"{st}  {b['title']}")
    print(f"Goal: {b['goal']}")
    print("Do:")
    for i, d in enumerate(b["do"], 1):
        print(f"  {i}. {d}")
    print("Rules to look up (vip rules <PREFIX>): " + ", ".join(b["rules"]))
    print(f"Done when: {b['done']}")
    if b["gate"]:
        print(f"Gate prompt: {b['gate']}")
    print(DISCIPLINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
