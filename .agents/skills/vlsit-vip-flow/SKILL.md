---
name: vlsit-vip-flow
description: Orchestrate the VLSIT ASIC VIP Design AI Flow end to end with the run-aware `vip` command. Create a numbered run directory, route each stage to its skill, enforce the four sign-off gates, and report honest evidence. Four modes: build a new SystemVerilog/UVM Verification IP from a protocol or standard specification (new), recover a specification from existing VIP code (reverse), fix VIP bugs with selective re-qualification (bugfix), and add features from a user requirement with a port of the implemented VIP (feature).
---

# VLSIT ASIC VIP Design AI Flow (orchestrator)

## Language convention

Use precise scientific and engineering English for skill instructions, technical clarifications, review gates, plans, reports, code comments, and script messages. Distinguish observed results from assumptions. Bilingual English–Vietnamese content is reserved for README files and documents explicitly designated as user guidelines.

`vip` below means `python3 scripts/vip.py` in this skill folder (use its full path from elsewhere). It finds the run, takes paths and settings from the run state, and prints short output.

## Rules

- The input is a VIP specification in the mandatory template. A specification that fails `vip validate` is never used downstream. If only a standard exists, use `vlsit-vip-spec-intake` first.
- Apply the rules of `references/VLSIT_VIP_Design_Rule.md` (rule IDs `V...`). Look rules up with `vip rules <ID or PREFIX>`; the file is authoritative and is never weakened. MUST has no waivers.
- A result is `PASS` only with a log. A missing tool, log, or run is `NOT_RUN`. User acceptance never converts `NOT_RUN` or `FAIL` into `PASS`.
- Never guess a missing input; ask once, concisely. Never overwrite an input, an earlier run, or a user change.
- Stop at each gate and wait for an explicit `APPROVE`. Record it with `vip gate` only after the user replied.

## Choose the mode

| The user has | Mode | Skill | Start |
|---|---|---|---|
| a standard or a VIP specification, no VIP yet | `new` | the stage skills below | `vip init <root> <tag> <spec.md>` |
| VIP code and no (or a stale) specification | `reverse` | `vlsit-vip-code-analyzer` | `vip init <root> <tag> --mode reverse --code <dir>` |
| a finished VIP (a run, or adopted code) with defects | `bugfix` | `vlsit-vip-bugfix` | `vip init <root> <tag> --mode bugfix --base-run <run>` |
| a finished VIP and a new requirement | `feature` | `vlsit-vip-feature` | `vip init <root> <tag> --mode feature --base-run <run>` |

A defect that turns out to be a specification error is a feature run. A VIP that was not built by this flow is first brought in by a reverse run; its later runs have layout `external` (no plan, no generated tree; the evidence is the project's regression report; Gate 2 does not apply). `vip next` and `vip brief` follow the mode of the run; the Loop below applies to all modes.

## Start (mode new)

Ask only for what is missing, in one question: the specification (or the standard with roles and profile), the output root, project name, human author, simulator and UVM version, profile to build first, and existing VIP to reuse. Then:

1. `vip doctor` (tools found: slang, Verilator, UVM).
2. `vip init <root> <tag> <spec.md>` (a standard only: `vip scaffold <tag> --title ... --standard ... -o <spec.md>` first, and follow `vlsit-vip-spec-intake`).
3. `vip set author="..." project="..." reviewer="..." profile=PROF-01`.

## Loop

Repeat until `vip next` says done:

1. `vip next` gives the next action and the command; `vip brief` gives the stage brief (goal, commands, rule groups, exit check, gate prompt).
2. Do the stage with its skill: S0 and S1 `vlsit-vip-spec-intake`, S2 `vlsit-vip-vplan`, S3 `vlsit-vip-architect`, S4 `vlsit-vip-generator`, S5 `vlsit-vip-qualifier`, S6 and S7 `vlsit-vip-release` (Claude Code `/vlsit-vip-<stage>`, Codex `$vlsit-vip-<stage>`; otherwise read that skill's `SKILL.md`).
3. `vip check` runs the exit check of the stage. Do not move on while it fails.
4. At a gate present the exact artifacts and ask: "Do you approve `<artifact>` version N, including `<scope>`? Reply APPROVE, REVISE, or STOP." After `APPROVE`: `vip gate G# APPROVED --by "<NAME>" --note "<version>"`. A changed approved artifact reopens the gate and every later gate.

Gates: G1 specification, G2 plan and architecture, G3 qualification evidence, G4 release. VIP-1 (end of S4) is an automatic check, not a gate.

## Failures

Classify before fixing: specification, plan, VIP, trace, counterpart, or environment defect. A specification defect reopens Gate 1. Never edit an expected result, an evidence entry, or a log to make a run pass.

## Token discipline

Read the output of `vip` commands; do not open generated files; use `vip query` for specification facts and `vip rules` for rule text; open a file region only when `vip worklist --show` or an error names it; pass `--full` only when the grouped output is not enough.

## Final response

Run directory, `vip status` line, counts of `PASS`, `FAIL`, `NOT_RUN`, tools run with versions, open decisions, waivers, and the next action. State what was not verified.
