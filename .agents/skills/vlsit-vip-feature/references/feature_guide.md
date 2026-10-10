# Feature guide

## 1. From a user requirement to specification rows

Write `00_change/change_request.md` first: the requirement in the user's words, its source (standard clause, project need, bug), acceptance (what a VIP user observes), and compatibility. Then express it in the specification copy of the run. Typical changes:

| Request | Rows to add or change |
|---|---|
| A new protocol rule | Requirement row (new `VREQ` ID, never a reused one) in 5.2 to 5.5; Section 8.1 expression for an SVA check; INJ row for a MUST check; boundary row if a value limit is involved |
| A new optional feature of the standard | Option row (3.3), a profile or variant that includes it (3.2, 3.4), the signals it adds (4.3), requirements with that profile or option |
| A new capability | CAP row (6.2), sequence row (10), coverage row (9), item fields (6.1) and knobs (7.1) it needs |
| A new API knob | Knob row (7.1) whose default keeps the old behavior; contract rows are unchanged unless usability changes |
| A new standard revision | Update the front matter `spec_revision_locked`, references (2.1), and every requirement whose clause changed; replaced requirements become `withdrawn` and new rows get new IDs |
| A removed rule | Keep the row with status `withdrawn` (IDs are permanent) |

Rules: new IDs only; a changed requirement keeps its ID when the rule is the same rule, and gets a new ID when the rule is different; a changed interface (signal, parameter, knob, item field removed or changed) bumps the major version and must be shown to the user before Gate 1.

## 2. The delta

`vip delta` compares the run's specification with the base specification table by table and prints the counts (`requirements +1 -0 ~0; checkexpr +1; injections +1`) and a suggested bump: `major` when a requirement, signal, parameter, or knob is removed or a signal changed; `minor` when something is added or a behavior row changed; `patch` otherwise. The full delta is written to `00_change/spec_delta.md` for Gate 1. A removed requirement row prints a warning (mark it `withdrawn` instead).

## 3. Plan, configuration, port

`vip plan` and `vip config` run as in a new VIP; the base run's plan and configuration are not edited. `vip port` then rebuilds the VIP tree in three steps:

1. Regenerate the skeleton of the **old** configuration (the base run's `vip_config.json` with the author, project, and date in the base tree's `spec/vip_generation.json`): this is the common ancestor.
2. Regenerate the skeleton of the **new** configuration.
3. For each file merge `current` (the base tree with the hand-written code), `base` (old skeleton), `new` (new skeleton):

| Case | Result |
|---|---|
| current equals base: nothing was written by hand | the new skeleton |
| new equals base: the change does not touch the file | the current file (hand-written code kept) |
| all three differ | `git merge-file`: hand-written code kept, new skeleton lines merged; overlapping edits become conflict markers |
| file only in the new skeleton | added |
| file removed from the skeleton | dropped when untouched, kept and reported when it was modified |
| `base/` and `spec/` | always the new version |

`00_change/port_report.md` lists the files per case. Conflicts are marked with lines that start with seven less-than signs; `vip lint impl` fails (HY-09) until none is left. Resolve a conflict by keeping the hand-written implementation and adding the new generated lines.

The port needs `spec/vip_generation.json`. Without it (external code) edit in place and use `vip impact --files`.

## 4. Implement only what is new

After the port `vip worklist --n 5` lists only the stubs the change introduced (the hand-implemented ones are untouched). Implement them as for a new VIP: checks with a Section 8.1 expression are already complete; monitor, driver, sequence, coverage, and counterpart stimulus are written from the worklist. Then `vip check-vip` and `vip lint impl`.

## 5. Impact, carry, re-run

`vip impact` compares the ported tree with the base tree (see the scope table of the bugfix guide). Adding one check typically gives a selective scope: the new positive and negative traces only, with the registration lines (check count, index, injection enum members, test includes) recognized as generated growth. `vip carry` copies PASS entries of the base evidence for traces outside the re-run set, `vip qual-run --impacted` runs the rest, `vip qual-collect` and `vip lint qual` close the evidence. A new variant or profile has no base entries and is run in full.

## 6. Compatibility checklist for Gate 1 and Gate 4

- Defaults: every new option and knob defaults to the old behavior.
- Existing checks: unchanged IDs, unchanged messages, unchanged severities (a change is a bug fix or a changed requirement and is listed).
- API: no removed or renamed public symbol without a major bump and a migration note.
- Evidence: counts of new, re-run, and carried traces; anything not run is `NOT_RUN`.

## 7. Release

Version: the base version plus a minor step (major when `vip delta` says so). Release notes carry the delta, the compatibility statement, and the counts. `vip manifest`, `vip lint release`, Gate 4. `vip diff <old spec> <new spec>` gives the requirement-level change list.

## 8. External code (layout external)

Only Gates 1, 3, and 4 apply. Edit the copied tree in its own style and build, record the changed files with `vip impact --files`, run the project's regression, write `05_qual/regression_report.md`, and write the release notes from `vip delta`.
