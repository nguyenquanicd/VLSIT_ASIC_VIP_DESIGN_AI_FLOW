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
        gates = " ".join(f"{g}:{i['status'][:4]}" for g, i in s["gates"].items())
        print(f"run {s['run']}  stage {s['stage']}  gates {gates}")
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
