# <VIP name> architecture and API (version N)

Status: Awaiting user sign-off (Gate 2). Specification: `<spec file>` version `<n>`, revision `<standard revision>`. Profile: `<PROF-nn>`. Date: `<YYYY-MM-DD>`.

## 1. Summary

State in five lines: what protocol and profile, which roles, how many requirements and checks, how many qualification traces per variant, and the build decision.

## 2. Structure

List the components of the default architecture (architecture guide, Section 1) and any deviation with its reason and decision ID.

## 3. Interface and timing

| Item | Decision |
|---|---|
| Signals and widths | `<from vip_config.json>` |
| Parameters and macros | `<name, macro, default>` |
| Clocking blocks | `<host_cb, device_cb, mon_cb: skews>` |
| Reset polarity and handling | `<polarity; how in_reset is maintained; behavior at mid-transfer reset>` |
| X policy | `<which signals are X when>` |

## 4. Check inventory

| Index | Check ID | Requirement | Strength | Role | Type | Injection |
|---|---|---|---|---|---|---|
| 0 | `<id>` | `<req>` | `<MUST/SHOULD>` | `<M/S/B>` | `<SVA/CLASS>` | `<INJ-nnn>` |

## 5. Usability contract

For each contract row UC-01 to UC-13, state how this VIP satisfies it and where (file or class).

## 6. Qualification structure

State the counterpart model, the independence arrangement, the expected-error mechanism, variants, seeds, and simulators, as in Section 11 of the specification.

## 7. Risks and open questions

List what could invalidate the architecture: unsupported simulator features, ambiguous requirements, missing counterpart capability, tool availability (lint, compile, coverage).

## 8. Approval

Do you approve architecture version N, including the listed files, profile, checks, tests, and variants? Reply APPROVE, REVISE, or STOP.
