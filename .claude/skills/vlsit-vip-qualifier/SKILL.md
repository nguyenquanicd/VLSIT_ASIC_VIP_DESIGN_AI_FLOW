---
name: vlsit-vip-qualifier
description: Qualify a generated VIP as a design under test. The qualification tests are generated; the work is one stimulus task per trace in an independent counterpart. Run the traces on every variant and seed with the project simulator through command templates, collect pass or fail only from logs into the evidence matrix, close coverage, classify failures, and obtain Gate 3. Use as stage S5 after the VIP reaches VIP-1.
---

# VIP qualification (S5)

## Language convention

Use precise scientific and engineering English for skill instructions, technical clarifications, review gates, plans, reports, code comments, and script messages. Distinguish observed results from assumptions. Bilingual English–Vietnamese content is reserved for README files and documents explicitly designated as user guidelines.

`vip` means `python3 scripts/vip.py` in this skill folder.

## Rules

- Start only when VIP-1 holds and Gates 1 and 2 are approved and unchanged (`vip require S5`).
- Evidence comes from logs only: `PASS` needs the result line, a clean UVM summary, exit code 0, and the required seeds on every variant. A missing run is `NOT_RUN`. Never edit an evidence entry, a log, or an expected result.
- The counterpart is independent of the VIP checkers (VQUA-03). The VIP host connected to its own device is a smoke test, not qualification.
- Expected errors are declared per trace with ID, minimum, maximum, and window; never demote errors globally. The base test rejects vacuous traces.
- Classify every failure (VIP, trace, counterpart, specification, or environment defect) before fixing. A specification defect stops the stage and reopens Gate 1.
- No UVM simulator means simulation evidence is `NOT_RUN`; never fabricate results. `vip check-vip` evidence is a type-check and says so in its note.

## Workflow

1. `vip brief S5`; `vip qual-init` creates the matrix, every entry `NOT_RUN`.
2. The test classes are generated and complete. Implement only the counterpart stimulus tasks: `vip worklist --kind test --n 6 --show`, then write each task in `qual/<tag>_counterpart.sv` from the specification (patterns: `references/qualification_guide.md`). Each negative trace produces exactly one violation; each positive trace reaches the valid boundary.
3. `vip check-vip --record` records the lint and compile evidence with their logs.
4. `vip set build_cmd="..." run_cmd="..." seeds=N`, then `vip qual-run` (one log per run; it adds `+VLSIT_SEED`) and `vip qual-collect`.
5. Coverage: merge the databases of the runs, review unhit bins, add traces or justified exclusions (category and reason), record with `vip qual-item coverage --status PASS --log <report> --database <db> --summary "<text>"`.
6. Triage each `FAIL` by the class table of the guide; in a negative trace's log only the declared check ID may fire.
7. `vip lint qual` must exit 0. Write `qualification_report.md`: counts of `PASS`, `FAIL`, `NOT_RUN` per variant, failures with class and fix, coverage, waivers, tool versions, what was not run.
8. Gate 3 (`vip brief S5` has the prompt). Approval cannot turn `NOT_RUN` or `FAIL` into `PASS`.

Rule groups when needed: `vip rules VQUA VP`.

## Token discipline

Read the printed counts and the first failures only. Never open a whole simulator log; grep the result line and the first error. Implement stimulus tasks from the worklist context, not from the whole counterpart file.

## Final response

Evidence counts per variant and status, failures by class, coverage, lint and compile status, waivers, tool versions, what is `NOT_RUN` and why, and the Gate 3 prompt. Say what the traces do not cover.
