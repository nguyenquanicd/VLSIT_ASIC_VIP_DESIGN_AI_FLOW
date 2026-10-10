# Stage checklists

Entry and exit checks of each stage. `vip` is `python3 scripts/vip.py`. `vip next` names the next action, `vip brief [S#]` prints the brief of a stage, and `vip check [S#]` runs the exit check of the stage (compact output).

| Stage | Entry check | Exit check |
|---|---|---|
| S0 | A request to build a VIP; the standard or a draft specification exists | Sections 1 to 3 of the specification answered; `vip init` done |
| S1 | S0 done; the standard converted to text | `vip validate` exits 0; `vip scan report` exits 0; `extraction_report.md` written; **Gate 1 approved** |
| S2 | `vip require S2` | `vip plan` ran; `vip lint plan` exits 0 |
| S3 | `vip require S3`; plan exists | `vip config` reports 0 problems; `vip_arch.md` written; **Gate 2 approved** |
| S4 | `vip require S4` (Gates 1 and 2 approved and unchanged) | `vip check-vip` passes (lint and UVM type-check); `vip lint impl` exits 0 (VIP-1) |
| S5 | `vip require S5`; VIP-1 reached | `vip qual-init`, `vip qual-run`, `vip qual-collect` done; `vip lint qual` exits 0; **Gate 3 approved** |
| S6 | `vip require S6` (Gate 3 approved) | README complete; usability trial recorded |
| S7 | Same as S6 | `vip manifest` done; `vip lint release` exits 0; release notes written; **Gate 4 approved** |

## State commands

| Command | Use |
|---|---|
| `vip init <root> <tag> <spec.md>` | Create the numbered run; it is remembered, so later commands need no path |
| `vip set key=value ...` / `vip get` | author, project, profile, reviewer, build_cmd, run_cmd, seeds, uvm_home, version |
| `vip status` | One line: stage and gates |
| `vip gate G1 APPROVED --by "<NAME>" --note "<version>"` | Record an approval, only after the user replied APPROVE |
| `vip stage S4` / `vip require S4` | Move to a stage / check prerequisites without moving |

A gate approval stores the SHA-256 of the approved artifacts. `vip require`, `vip stage`, `vip status`, and `vip next` reopen a gate whose approved artifact changed, and every later gate with it.

## Status report

Every report to the user states: the `vip status` line; the commands run and their exit status for the current stage; evidence counts (`PASS`, `FAIL`, `NOT_RUN`); open decisions; blockers; the next action and its owner. Use scientific English. Distinguish what ran from what is assumed.
