# Release checklist

Gate VIP-3 criteria and the usability trial. Rule IDs refer to `VLSIT_VIP_Design_Rule.md`. A check is `PASS` only with evidence; otherwise `NOT_RUN` or `FAIL`.

## 1. Entry conditions

1. Gates 1, 2, and 3 are `APPROVED` and their artifacts are unchanged since approval (`vip_state.py require --stage S7`).
2. `trace_lint.py --stage release` is the final check; run it again at the end of this stage.

## 2. Package content (VDOC-01)

| Item | Check |
|---|---|
| VIP sources | No `VIP_TODO` marker, no tab, no stub; `make_manifest.py` lists no file with `VIP_TODO` |
| `doc/README.md` | Complete (Section 3) |
| Quickstart | Runs and passes with the project simulator; log kept |
| `spec/requirements.csv` | Statuses are `qualified`, `waived`, or `withdrawn`; reviewer recorded |
| Trace report | One row per requirement: check, coverage, sequence or injection, positive trace, negative trace, result |
| Qualification report and evidence | Final, with logs and the coverage summary |
| Manifest | `vip_manifest.json` with version, `spec_rev`, and SHA-256 of every file |
| Release notes | Added, changed, and withdrawn requirements; waivers; known limitations; tool versions |

## 3. README sections (VAPI-05)

1. Three-step usage with code.
2. Parameters bound at compile time and their macros.
3. Configuration knobs with defaults and legal values.
4. `uvm_config_db` keys and paths used, and the virtual interface requirements.
5. TLM ports and transaction types.
6. Factory-overridable classes.
7. Clock and reset assumptions; behavior on reset at any time.
8. Checks: ID, requirement, severity; how to waive one with a reason; the REC group switch.
9. Quickstart: command and expected result.
10. Debug: message format, verbosity, transaction recording.
11. Known limitations and the specification revision implemented.

## 4. Usability trial (VAPI-01, VAPI-02)

A person who has not worked on this VIP does the trial with the README only.

1. Create the cfg, set the interface, create the agent, start a sequence (three steps). Count the extra steps the person needed.
2. Run the quickstart.
3. Switch the agent between host, device, and passive monitor.
4. Waive one check with a reason and see it in the report.
5. Change a width with a `+define` and recompile.
6. Record every question and every place the person was stuck. Each is a README or API defect and must be fixed, then the trial is repeated on that point.

The trial passes when steps 1 to 5 were done without help from the authors. Record the person, date, and findings in `release_notes.md`.

## 5. Gate VIP-3 criteria

| Criterion | Evidence |
|---|---|
| Multi-seed regression passes on every variant of every built profile | Evidence JSON and logs; seeds as set in the specification |
| Every MUST check has passing positive and negative traces | `trace_lint.py --stage release` |
| Coverage closed except waived items with reason | Coverage summary and exclusion list |
| Independent review recorded | Reviewer in `requirements.csv`; QP-02 satisfied |
| README complete; usability trial passed | Release notes |
| Version and `spec_rev` tagged; manifest written | `vip_manifest.json` |
| Waivers: each has a reason and a reviewer; a waived MUST check has the user's explicit approval | Release notes |

## 6. Specification change (VDOC-03)

When the standard or the specification changes:

```text
vip diff <old spec or requirements.csv> <new spec or requirements.csv>
```

The report lists added, removed, and changed requirements and the re-qualification scope. Added and behavior-changed requirements return to the planning stage (new run, new numbered directory); wording-only changes need a review of the spec reference. A removed requirement is kept with status `withdrawn`; the diff exits with status 1 until it is.

## 7. Gate 4

Present the release notes, the manifest, and the final trace-lint result. Ask:

- Do you approve release `<version>` for `<spec_rev>`, including the listed files, variants, waivers, and limitations? Reply APPROVE, REVISE, or STOP.
