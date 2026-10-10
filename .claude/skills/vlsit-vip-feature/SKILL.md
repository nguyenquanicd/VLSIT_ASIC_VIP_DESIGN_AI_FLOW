---
name: vlsit-vip-feature
description: Add features to an existing VIP from a user requirement under the VLSIT flow. The requirement becomes a change request and a specification delta (new or changed rows with permanent IDs), the delta is approved at Gate 1, the implemented VIP is ported to the new configuration with a three-way merge that keeps hand-written code, only the new stubs are implemented, and an impact analysis limits re-qualification to the new and touched traces while carrying the rest of the base evidence. Use when the user wants the current VIP to support a new option, mode, check, capability, API knob, or standard revision.
---

# VIP feature update (feature run)

## Language convention

Use precise scientific and engineering English for skill instructions, technical clarifications, review gates, plans, reports, VIP code comments, and script messages. Distinguish observed results from assumptions. Bilingual English–Vietnamese content is reserved for README files and documents explicitly designated as user guidelines.

`vip` means `python3 scripts/vip.py` in this skill folder.

## Rules

- Start from a finished base run (`vip init <root> <tag> --mode feature --base-run <run>`): the base is never modified. The new run copies the base specification for editing and bumps the minor version (a removed or changed interface bumps the major version; `vip delta` suggests the bump).
- The user's requirement comes first in `00_change/change_request.md` (requirement, source, acceptance, compatibility). Ask only what the base specification cannot answer, in one question.
- IDs are permanent: never reuse or renumber an ID; a replaced requirement is marked `withdrawn`. Default behavior stays as it was: a new option or knob defaults to the old behavior, and an interface change is called out to the user before Gate 1.
- A new check needs a Section 8.1 expression and, for MUST, an injection row; a new capability needs a sequence and a coverage row. Apply the same rules as for a new VIP (`vip rules <PREFIX>`).
- Port, never regenerate over: `vip port` writes a new tree. Conflict markers must be resolved before `vip lint impl` passes (HY-09).
- Claim only what ran; evidence carried from the base is labelled `carried`.

## Workflow

1. `vip next`, `vip brief`. Fill `00_change/change_request.md`.
2. Read only the rows the change touches: `vip query outline`, `vip query rows requirements`, `vip query get <ID>`.
3. Edit the specification copy in `01_spec/`: new rows with new IDs, signals, parameters, knobs, items, capabilities, injections, coverage, sequences. `vip validate`, then `vip delta` (added, removed, changed rows per table; the suggested version bump).
4. Gate 1 with the user on the delta: present the delta, the compatibility statement, and the open decisions.
5. `vip plan` and `vip config` (the architecture file is updated for the change only), Gate 2.
6. `vip port` produces `04_vip/<tag>_vip`: the skeleton of the old and of the new configuration are regenerated and merged with the current tree (`git merge-file`); `00_change/port_report.md` lists new skeleton files, merged files, hand-written files kept, and conflicts. Resolve conflicts, then `vip worklist --n 5` shows only the new stubs. Implement them; `vip check-vip` and `vip lint impl`.
7. `vip impact` (scope, touched checks and requirements, traces to re-run), `vip carry` (evidence from the base for untouched traces), `vip qual-run --impacted`, `vip qual-collect`, `vip check-vip --record`, `vip lint qual`. Gate 3.
8. Release notes with the delta, `vip manifest`, `vip lint release`, Gate 4. `vip diff <old> <new>` lists the requirement-level changes.

External code (layout external, from a reverse run): plan, architecture, port, and the evidence matrix do not apply. Edit the copied tree in its own style and build, `vip impact --files <changed files>`, a `05_qual/regression_report.md`, Gates 1, 3, 4.

## Token discipline

Read the delta, not the specification. The port report and the worklist name the files and the lines to edit; do not open merged files that report no conflict and no stub.

## Final response

Change request summary; delta counts and version bump; compatibility statement; port report counts and conflicts; stubs implemented; impact scope with traces new, re-run, and carried; tool versions and results; gate status; `NOT_RUN` items.
