---
name: vlsit-vip-release
description: Package a qualified VIP and release it with evidence. Complete the README against the usability contract, run a first-time-user trial, write the release notes, write the manifest with file hashes in one command, lint the final trace, tag the version and standard revision, and handle specification changes by requirement diff. Use as stages S6 and S7 after Gate 3, or to assess the impact of a changed specification.
---

# VIP packaging, release, and maintenance (S6 and S7)

## Language convention

Use precise scientific and engineering English for skill instructions, technical clarifications, review gates, plans, reports, code comments, and script messages. Distinguish observed results from assumptions. Bilingual English–Vietnamese content is reserved for README files and documents explicitly designated as user guidelines.

`vip` means `python3 scripts/vip.py` in this skill folder.

## Rules

- Release only after Gates 1, 2, and 3 are `APPROVED` and unchanged (`vip require S7`). The release is the user's decision at Gate 4.
- A release has no `VIP_TODO` marker, no stub, and no unexplained waiver. A waived MUST check needs the user's explicit approval and appears in the release notes (VDOC-04).
- The usability trial is done by a person who did not build the VIP, using the README only. With no such person the trial is `NOT_RUN`; do not simulate it.
- Put in the README only what was run; the quickstart output must come from an actual run.
- Never overwrite an earlier release; use a new directory per version.

## Workflow

1. `vip brief S6`. Complete `doc/README.md` with the sections of `references/release_checklist.md`.
2. Trial: run it with the named person; record every stumbling point; fix each README or API defect and repeat that point.
3. Write `release_notes.md`: version, `spec_rev`, requirements added, changed, withdrawn, waivers with reasons and reviewers, known limitations, tool versions, trial result. Write `trace_report.md` from `requirements.csv` and the evidence (one row per requirement).
4. Set requirement statuses to `qualified` or `waived` (the only fields later stages edit), then `vip manifest` and `vip lint release`; it must exit 0.
5. Gate 4 (`vip brief S7` has the prompt). Tag the version only after `APPROVE`; `vip gate G4 APPROVED --by "<NAME>"`.
6. Maintenance: `vip diff <old spec or csv> <new spec or csv>` lists added, removed, changed requirements and the re-qualification scope; start a new run for the affected requirements. A removed requirement stays as `withdrawn`.

Rule groups when needed: `vip rules VAPI VDOC`.

## Token discipline

Generate `trace_report.md` rows from `requirements.csv` fields, not by reading code. Report counts and exceptions.

## Final response

Release directory, version and `spec_rev`, trial result, `vip lint release` status, waivers, known limitations, and the Gate 4 prompt. State what was not verified.
