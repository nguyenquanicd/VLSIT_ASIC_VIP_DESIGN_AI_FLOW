---
name: vlsit-vip-spec-intake
description: Convert a protocol or standard document into a validated VIP specification in the mandatory VLSIT markdown template. Scaffold the specification, extract every normative requirement with clause references, boundaries, error injections, and check expressions, classify every normative sentence, validate, and obtain Gate 1. Use as the first stage of VIP design, or when a VIP specification is missing, incomplete, or fails validation.
---

# VIP specification intake (S0 and S1)

## Language convention

Use precise scientific and engineering English for skill instructions, technical clarifications, review gates, plans, reports, and script messages. Distinguish observed results from assumptions. Bilingual English–Vietnamese content is reserved for README files and documents explicitly designated as user guidelines.

`vip` means `python3 scripts/vip.py` in this skill folder.

## Rules

- The standard is the authority. Extract a requirement only with a clause, table, or figure reference; never from memory. Never invent a limit or a clause number. A statement you cannot ground is an `Open` decision.
- Paraphrase; never copy standard text into the specification, the report, or the chat.
- Never resolve an ambiguity silently: record a decision row with its impact and ask.
- Keep template column names and order; the scripts parse them. Tables fixed by the rules (UC-01..13, CP, QP, gates, PK) are prefilled by `vip scaffold`; change them only for a stated reason.
- The analysis is reviewed by a person other than the implementer (VQUA-07); ask who.
- Never modify the standard or an existing specification; write a new file.

## Inputs (ask once)

The standard (PDF or text) with exact ID and revision; roles, profile, optional features in scope; clauses in scope for a large standard; output location, project, author; simulator and UVM version; existing VIP to reuse.

## Workflow

1. `vip brief S0`, then `vip scaffold <tag> --title "<name>" --standard "<ID rev>" -o <spec.md>`. Convert the standard to text with a recorded tool (`pdftotext -layout`); keep the original.
2. `vip scan scan <standard.txt> --out normative_candidates.csv`.
3. Fill only the open cells: `vip query todo <spec.md>` lists them by section. Follow `references/extraction_guide.md` for how to decide strength, role, kind, check type, rule key, boundaries, injections, and the Section 8.1 check expression of every SVA requirement. Re-read facts with `vip query rows|get|refs`, not by opening the file.
4. Classify every candidate in `normative_map.csv` (mapped, informative, out_of_scope, duplicate). Read tables, figures, and state diagrams yourself; they carry requirements without modal verbs.
5. `vip validate <spec.md>` must exit 0, and `vip scan report normative_map.csv --spec <spec.md>` must exit 0. Review every warning; use `--full` only when the grouped output is not enough.
6. Write `extraction_report.md`: source and revision, converter, scanned range, classification totals, requirement counts, boundaries and derivations, open decisions, what was not read, what the reviewer checks by hand.
7. In a run: `vip init <root> <tag> <spec.md>`, then Gate 1 (see `vip brief S1`). Do not plan before `APPROVE`.

Rule groups to look up when needed: `vip rules VNAM VCHK VQUA`. Worked example: `assets/APB_VIP_Specification.md`.

## Token discipline

Never print the whole specification or the standard. Write table rows, not prose. Use the prefilled defaults. Let the scripts count and cross-check.

## Final response

Specification path, validation exit status, classification totals, requirement counts, open decisions, what was not read or verified, and the Gate 1 prompt. Do not call the specification complete while a candidate is unclassified or an `Open` decision touches a requirement.
