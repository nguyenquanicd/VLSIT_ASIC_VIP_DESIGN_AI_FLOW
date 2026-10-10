---
name: vlsit-vip-architect
description: Fix the VIP architecture and user-facing API before any code exists. Select the profile, record build-or-reuse and tool decisions, derive and check the machine-readable vip_config.json with one command, write vip_arch.md showing how every usability-contract item is met, and obtain Gate 2 approval of plan and architecture. Use as stage S3 after the plan, before code generation.
---

# VIP architecture and API (S3)

## Language convention

Use precise scientific and engineering English for skill instructions, technical clarifications, review gates, plans, reports, and script messages. Distinguish observed results from assumptions. Bilingual English–Vietnamese content is reserved for README files and documents explicitly designated as user guidelines.

`vip` means `python3 scripts/vip.py` in this skill folder.

## Rules

- Use the default architecture of `references/architecture_guide.md` unless the specification records a decision for a deviation. No rule exceptions; change the specification or ask.
- Generate no VIP code here. The outputs are `vip_config.json` and `vip_arch.md`.
- Do not edit a requirement, a check, or a trace in `vip_config.json`; that belongs to the specification and reopens Gate 1.
- Gate 2 is the user's decision.

## Workflow

1. `vip brief S3`. Confirm the profile (`vip set profile=PROF-nn`); a specification with several profiles needs one build per profile, plan the first now.
2. Resolve the decisions of the guide's Section 2 table; ask the user only for project choices (simulator and UVM version, formal use, reuse of an existing VIP).
3. `vip config` derives `vip_config.json` for the profile and checks it; run it again after any edit (it then checks the existing file). It must report 0 problems.
4. Review using the counts that `vip config` prints and `vip query`; the checklist is in the guide's Section 3.
5. Write `vip_arch.md` from `references/vip_arch_template.md`: structure, interface, check inventory, how each of UC-01..UC-13 is met, qualification structure, risks. Keep it to what a reviewer needs.
6. Gate 2: present `vplan.md`, `vip_config.json`, and `vip_arch.md` with versions, profile, and the numbers of checks, tests, and variants (`vip brief S3` has the prompt). Wait for `APPROVE`; then `vip gate G2 APPROVED --by "<NAME>"`.

Rule groups when needed: `vip rules VAPI VUVM VIFC`.

## Token discipline

Do not paste `vip_config.json` into the chat; report counts and the exceptions you found.

## Final response

Paths, `vip config` result, architecture decisions and who made them, risks, and the Gate 2 prompt. State that no code has been generated.
