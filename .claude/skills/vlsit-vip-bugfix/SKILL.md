---
name: vlsit-vip-bugfix
description: Fix defects of an existing or released VIP under the VLSIT flow. Each defect is a row in a bug log with a gated life cycle (open, analyzed, planned, fixed, verified, closed); the regression test is written before the fix; an impact analysis names the checks, requirements, and traces the change touches, so only those are re-run and the rest of the base evidence is carried over; the result is a patch release. Use when the user reports a VIP bug, a false failure or a missed violation, or a wrong coverage result.
---

# VIP bug fix (bugfix run)

## Language convention

Use precise scientific and engineering English for skill instructions, technical clarifications, review gates, plans, reports, VIP code comments, and script messages. Distinguish observed results from assumptions. Bilingual English–Vietnamese content is reserved for README files and documents explicitly designated as user guidelines.

`vip` means `python3 scripts/vip.py` in this skill folder.

## Rules

- Start from a finished base run (`vip init <root> <tag> --mode bugfix --base-run <run>`): the base is never modified. The new run copies the specification, plan, architecture, and VIP tree and bumps the patch version.
- Test first: the regression test exists and fails for the bug before the fix. The log refuses `fixed` without a named regression test, `verified` without a log file, and `closed` without the test in the tree.
- Fix the smallest region that explains the symptom. No refactoring, no style changes, no edits to `base/` (change the shared base library in the flow repository instead).
- Classify before fixing: `vip` (VIP code), `trace` (wrong ID, expression, or evidence), `counterpart` (qualification model), `environment`, `dut` (not a VIP bug: `wontfix` with the reason), `spec` (the specification is wrong: stop and start a feature run, because a specification change needs Gate 1).
- Claim only what ran. Evidence carried from the base is labelled `carried`; anything not re-run stays `NOT_RUN`.
- Carrying Gates 1 and 2 needs the user's OK in chat and byte-identical approved files (`vip carry-gates` checks the hashes).

## Workflow

1. `vip next` and `vip brief` show the state and the stage brief. Record each defect: `vip bug new --title ... --symptom ... --severity critical|major|minor [--found-in VER] [--req VREQ-..]`.
2. Reproduce with the smallest stimulus and find the cause. Read only what the symptom points to: `vip query get <VREQ>` for the requirement and the check expression, then the CODE region. `vip bug set BUG-001 class=vip status=analyzed`, then `req_ids=... files=... status=planned`.
3. With the user's OK: `vip carry-gates --by <NAME>` (Gate 1 and Gate 2 of the base apply unchanged).
4. Write the regression test or counterpart stimulus first; watch it fail; fix; `vip check-vip` and `vip lint impl`; `vip bug set BUG-001 regression_test=<test> fix_summary="..." status=fixed`.
5. `vip impact` compares the new tree with the base: scope SELECTIVE (a check block, a sequence, a stimulus task, a test) or FULL (interface, base, agent, drivers, monitor, item, config, package), the checks and requirements touched, and the traces to re-run. `vip carry` creates the evidence from the base: PASS entries of untouched traces are carried, the rest are NOT_RUN, and the regression test of each fixed bug becomes an evidence entry (kind `reg`). `vip qual-run --impacted`, `vip qual-collect`, `vip check-vip --record`, `vip lint qual`.
6. `vip bug set BUG-001 evidence_log=<log> status=verified`; `closed` when the test is in the tree. Gate 3 with the user: bugs fixed, traces re-run, traces carried.
7. `vip bug report` for the release notes, `vip manifest`, `vip lint release`, Gate 4.

External code (no `spec/vip_generation.json`, layout external): plan, architecture, `check-vip`, and the evidence matrix do not apply. Use the project's own build and regression, `vip impact --files <changed files>`, a `05_qual/regression_report.md` with commands, logs, and results, and the same bug transitions; Gates 1, 3, 4.

## Token discipline

`vip bug list` and `vip impact` print a few lines; do not paste logs. Quote the bug ID, the check ID, the first failing line, and the file and line of the fix.

## Final response

Bugs with class, status, and regression test; files changed; impact scope and the counts re-run and carried; `check-vip` and `lint` results with tool versions; evidence logs; gate status; `NOT_RUN` items.
