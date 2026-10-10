# Verification plan guide

The plan stage turns the approved specification into `requirements.csv`, `vplan.md`, and the traceability table. All identifiers are derived by `extract_requirements.py`; this guide explains the derivation, how to repair gaps, and how to review the plan.

## 1. Derived identifiers

| Field | Rule |
|---|---|
| `chk_id` | Explicit `Check ID` from the specification, else `<TAG>_<ERR\|REC><role>_<FIRST SIGNAL>_<RULE KEY>`. `ERR` for MUST; `REC` for SHOULD and MAY. Only for check type SVA or CLASS; `-` otherwise. |
| `cov_id` | `COV_<TAG>_<NNNN>` with the number of the requirement; `-` only for check type NONE. For an SVA requirement it names the paired cover of the antecedent. For a boundary requirement it names the covergroup with valid and invalid bins. For a capability it names a covergroup of the scenario. |
| `inj_id` | The `INJ` rows whose violated requirement is this one. |
| `seq_id` | The sequence names of the `CAP` rows that list this requirement. |
| `test_pos`, `test_neg` | `qual_<chk_id lowercase>_pos` and `_neg`. Capability requirements get `qual_cap_nnn_cap` as `test_pos`. |
| `status` | `draft` by default; `reviewed` only with `--status reviewed --reviewer NAME` after Gate 1. |

## 2. Run

```text
vip set reviewer="<NAME>"
vip plan
vip lint plan
```

`vip plan` validates the specification first and refuses to plan when it has errors. It never overwrites an output; a changed specification needs a new run. It also writes a copy of the specification with Section 13 filled (`02_plan/<tag>_vip_spec_traced.md`); the approved specification is not modified.

## 3. Repair gaps

| Gap reported | Repair |
|---|---|
| MUST check without an injection | Add an `INJ` row in Section 6.3 naming one violation of that requirement. If the violation cannot be produced by the VIP itself, name the counterpart as the injector and say so in the mechanism. |
| Capability requirement without a sequence | Add a `CAP` row in Section 6.2 that lists the requirement and names a sequence. |
| Derived check ID collision | Give one requirement an explicit `Check ID`, or a distinct rule key. |
| Requirement with check type SVA but not observable at the interface | Change the check type to `CLASS`, `COV`, or `NONE` with the reason. |

A repair edits the specification, so it reopens Gate 1: report the change, ask the user to approve the new version, then re-run the plan into a new directory.

## 4. Review the plan

Check by hand, then present the plan with the architecture at Gate 2:

1. Every MUST requirement is checked or has a stated reason why not.
2. Each check is orthogonal: one injected violation fires one check (see the extraction guide, Section 3).
3. Every numeric quantity has valid and invalid bins, or a stated reason for a missing side.
4. The counts in `vplan.md` match expectations: checks, traces per variant, capabilities, variants.
5. Open decisions are listed and none blocks a requirement that is planned.

## 5. Handoff

`requirements.csv` is the single list of requirements for all later stages. Later stages update only `status`, `reviewer`, and `notes`. Requirement IDs are permanent. A requirement withdrawn in a later specification revision keeps its row with status `withdrawn`.
