---
name: vlsit-vip-vplan
description: Turn an approved VIP specification into the verification plan and requirement traceability with one command. Derive check, coverage, injection, sequence, and test IDs, write requirements.csv, vplan.md, and the traceability table, report plan gaps, and lint the trace. Use as stage S2 after Gate 1, or to regenerate the plan for a changed specification.
---

# VIP verification plan and traceability (S2)

## Language convention

Use precise scientific and engineering English for skill instructions, technical clarifications, review gates, plans, reports, and script messages. Distinguish observed results from assumptions. Bilingual English–Vietnamese content is reserved for README files and documents explicitly designated as user guidelines.

`vip` means `python3 scripts/vip.py` in this skill folder.

## Rules

- Plan only a specification that passes `vip validate` and whose Gate 1 is `APPROVED` (`vip require S2`).
- Do not change the specification here. A gap that needs a change goes to the user and reopens Gate 1.
- IDs come from the script, never typed by hand. Requirement IDs are permanent. Outputs are never overwritten; a changed specification needs a new run.
- The reviewer name is recorded for VQUA-07; ask for it, do not invent one.

## Workflow

1. `vip brief S2`; make sure `vip set reviewer="<NAME>"` is set.
2. `vip plan` validates, derives IDs, and writes `requirements.csv`, `vplan.md`, `traceability_table.md`, and the traced specification copy. It prints the counts and the gaps.
3. `vip lint plan` must exit 0.
4. Repair gaps by the table in `references/plan_guide.md` (a MUST check needs an injection, a capability needs a sequence, a derived ID collision needs an explicit Check ID). A repair edits the specification: ask the user to approve the new version, then start a new run.
5. Check orthogonality of the checks: one injected violation must fire one check. Report any pair that can fire together. Use `vip query rows checkexpr` and `vip query get <REQ> --deep` instead of reading the specification.
6. Summarize: requirements, checks by type and strength, traces per variant, capabilities, variants, gaps, open decisions. The plan is presented with the architecture at Gate 2; do not generate code.

Rule groups when needed: `vip rules VQUA VCHK`.

## Token discipline

Do not open `requirements.csv` or `vplan.md` in full; use `vip query` for the specification and read the printed summary. Quote IDs, not text.

## Final response

Plan directory, `vip lint plan` exit status, counts, gaps and repairs, orthogonality findings, and "Awaiting Gate 2 with the architecture".
