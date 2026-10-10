---
name: vlsit-vip-generator
description: Generate the VIP source tree from the approved architecture and finish it under the VLSIT VIP design rules. One command generates the interface, UVM-free checker with every check that has a specification expression already complete, package, agent, item, coverage, quickstart, and qualification scaffolding. A worklist then lists only the stubs left, and one command lints and type-checks the UVM tree against the official UVM. Use as stage S4 after Gate 2.
---

# VIP generation and implementation (S4)

## Language convention

Use precise scientific and engineering English for skill instructions, technical clarifications, review gates, plans, reports, VIP code comments, and script messages. Distinguish observed results from assumptions. Bilingual English–Vietnamese content is reserved for README files and documents explicitly designated as user guidelines.

`vip` means `python3 scripts/vip.py` in this skill folder.

## Rules

- Generate only after Gate 2 is `APPROVED` and unchanged (`vip gen` checks it). Never overwrite an existing VIP tree.
- Follow `references/VLSIT_VIP_Design_Rule.md`: look up the groups you touch with `vip rules <PREFIX>` (see the list in `vip brief S4`). MUST has no waivers; a conflict with a requirement is documented and asked, never hidden.
- Never leave a silent stub: a stub announces itself at run time and carries `VIP_TODO(<id>)`. Remove a marker only when the item is implemented.
- Do not edit `base/` of a generated VIP; change `assets/base` in this skill and regenerate.
- Claim only what ran. `vip check-vip` is lint plus a `slang` type-check against the official UVM: it is not a simulation. Mark anything else `NOT_RUN`.

## Workflow

1. `vip brief S4`; `vip set author="<NAME>" project="<PROJECT>"`.
2. `vip gen`. Every check with a Section 8.1 expression is already a complete assertion; the rest are stubs.
3. `vip worklist --n 5` lists the next stubs with their requirement context (`--kind check|mon|drv|seq|cov`, `--show` prints the code region of the first). Work through them in the order shown, following `references/implementation_guide.md`.
4. A remaining SVA stub: `vip impl-check --id <CHECK_ID> --op SAME|NEXT --ante "..." --cons "..." --msg "..."` completes it and prints the row to add to Section 8.1 of the specification. Monitor, drivers, sequences, and covergroup sampling are edited by hand at the lines the worklist gives.
5. After each group: `vip check-vip` (Verilator lint in simulation and formal modes, then slang UVM type-check of the quickstart and of the qualification environment; a few lines) and `vip lint impl`.
6. VIP-1 holds when `check-vip` passes, every MUST signal and sequence check is implemented, and `vip lint impl` has no error. Qualification stubs may remain for S5.
7. Write `generation_report.md` in the run: stubs completed and remaining, tools and versions, `NOT_RUN` items.

## Token discipline

Never read the generated tree; read worklist items and the region of the file you edit. Do not re-read a file after an edit; run `vip check-vip`. Report counts, not code.

## Final response

VIP root, files generated, stubs completed and remaining, `check-vip` result with tool versions, `vip lint impl` result, `NOT_RUN` items, VIP-1 status. Do not call the VIP functional until the quickstart ran in a simulator.
