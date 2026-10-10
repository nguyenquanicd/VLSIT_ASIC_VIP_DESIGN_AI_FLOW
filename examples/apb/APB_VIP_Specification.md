---
document_type: asic_vip_specification
document_id: "APB-VIP-SPEC"
title: "AMBA APB Verification IP Specification (worked example)"
vip_name: "apb_vip"
proto_tag: "apb"
version: "0.1"
status: "Draft"
spec_revision_locked: "IHI 0024C (AMBA APB Protocol Specification v2.0, APB4)"
language: "SystemVerilog IEEE 1800-2017; UVM IEEE 1800.2-2020"
vip_rules: "VLSIT_VIP_Design_Rule.md"
rtl_rules: "VLSIT_RTL_Design_Rule.md"
---

# AMBA APB Verification IP Specification (worked example)

> **Worked example.** This file shows how to fill `VLSIT_ASIC_VIP_Specification_Template.md` for the AMBA APB protocol. Clause references use the clause title, because the standard text was not supplied in the build session and clause numbers were not verified (DEC-001). Confirm every reference against the controlled copy before using this file for a release.

## 1. Purpose, scope, and context

### 1.1 Purpose and scope

This VIP verifies an AMBA APB interface. It drives and answers APB transfers, observes them, checks protocol rules, and collects functional coverage.

**Included:** host (requester) and device (completer) roles, a passive monitor, the APB4 profile with `pstrb` and `pprot`, the APB3 profile without them, wait states, error response, back-to-back transfers, protocol checks, coverage, and a loopback quickstart.

**Excluded:** multi-slave address decoding (one `psel` line), APB5 extensions (`pwakeup`, user signals, parity checks), power-down behavior, and data-correctness scoreboarding (project scoreboard).

### 1.2 Build-or-reuse decision

| Candidate | Source | Requirement coverage | Decision | Reason |
|---|---|---|---|---|
| none considered | not applicable | unknown | Build | Worked example that exercises the flow end to end |

### 1.3 Target environment

| Item | Specification |
|---|---|
| Simulator(s) for qualification | Not selected; the project selects one before gate VIP-1 |
| UVM version | IEEE 1800.2-2020 |
| Lint tool for interface and checker | Verilator 5.053, lint-only mode |
| Formal tool for checkers (optional) | Not used |
| Operating system and shell | Windows 11, Git Bash |
| Project name and human author | VLSIT APB example; author supplied by the user at generation time |

## 2. Normative references and precedence

### 2.1 Normative references

| Ref ID | Document and revision | Applicable clauses | Authority / notes |
|---|---|---|---|
| REF-001 | AMBA APB Protocol Specification, IHI 0024C (APB4) | Signals, operating states, write and read transfers, error response, protection and strobes | Protocol authority |
| REF-002 | VLSIT VIP Design Rules v1, VLSIT_VIP_Design_Rule.md | All | VIP coding, naming, qualification, and release rules |
| REF-003 | VLSIT RTL Design Rules v2, VLSIT_RTL_Design_Rule.md | Inherited items listed in VSCP-03 | Referenced for inherited conventions only |

### 2.2 Precedence and conflict handling

1. The selected protocol revision (REF-001) defines protocol behavior.
2. This specification defines the VIP contract: scope, interface, API, qualification, and delivery.
3. `VLSIT_VIP_Design_Rule.md` governs VIP code. A requirement that conflicts with it is revised; no local exception is created.
4. Resolve a conflict by an explicit decision in Section 14.

### 2.3 Compliance declaration

| Standard | Revision / profile | Role implemented | Options | Deviations |
|---|---|---|---|---|
| AMBA APB | IHI 0024C, APB4 and APB3 profiles | Host, device, passive monitor | pstrb, pprot | Single select line only (DEC-003) |

## 3. Roles, profiles, and options

### 3.1 Roles

| Role ID | Role | Letter | Drives | Mode |
|---|---|---|---|---|
| ROLE-01 | Host | M | paddr, psel, penable, pwrite, pwdata, pstrb, pprot | ACTIVE |
| ROLE-02 | Device | S | pready, prdata, pslverr | ACTIVE |
| ROLE-03 | Monitor | B | none | PASSIVE |

### 3.2 Profiles

| Profile ID | Profile | Standard revision | Included options | Notes |
|---|---|---|---|---|
| PROF-01 | APB4 | IHI 0024C | OPT-01, OPT-02 | Full signal set of this VIP |
| PROF-02 | APB3 | IHI 0024C | none | No pstrb and no pprot |

### 3.3 Optional features

| Option ID | Optional feature | Signals added | Default | Status |
|---|---|---|---|---|
| OPT-01 | Write strobes | pstrb | on | In scope |
| OPT-02 | Protection control | pprot | on | In scope |
| OPT-03 | Wake-up and user signals (APB5) | pwakeup, user signals | off | Out of scope |

### 3.4 Variants for qualification

| Variant ID | Profile | Options | Parameter values | Qualification target |
|---|---|---|---|---|
| VAR-01 | PROF-01 | OPT-01, OPT-02 | PARA_ADDR_W=32, PARA_DATA_W=32 | Widest legal configuration |
| VAR-02 | PROF-01 | OPT-01, OPT-02 | PARA_ADDR_W=12, PARA_DATA_W=8 | Narrowest data width, byte strobe |
| VAR-03 | PROF-02 | none | PARA_ADDR_W=32, PARA_DATA_W=32 | APB3 signal set |

## 4. Interface definition

### 4.1 Clocks and resets

| Domain | Clock signal | Reset signal | Reset polarity | Notes |
|---|---|---|---|---|
| apb | pclk | presetn | Active-low | One clock; all signals sampled on the rising edge |

### 4.2 Parameters

| Parameter | Description | Default | Legal values | Unit |
|---|---|---|---|---|
| PARA_ADDR_W | Width of the address bus paddr | 32 | 1 to 32 | bit |
| PARA_DATA_W | Width of the data buses pwdata and prdata; also sets the pstrb width | 32 | 8, 16, or 32 | bit |

### 4.3 Signals

| Signal | Width | Driver | Profile / option | Reset / idle | Description |
|---|---|---|---|---|---|
| pclk | 1 | CLK | all | not applicable | APB clock |
| presetn | 1 | RST | all | not applicable | APB reset, active-low |
| paddr | PARA_ADDR_W | M | all | 0 | Transfer address |
| psel | 1 | M | all | 0 | Select for the device |
| penable | 1 | M | all | 0 | Marks the access phase |
| pwrite | 1 | M | all | 0 | 1 for write, 0 for read |
| pwdata | PARA_DATA_W | M | all | 0 | Write data |
| pstrb | PARA_DATA_W/8 | M | OPT-01 | 0 | Write byte strobes |
| pprot | 3 | M | OPT-02 | 0 | Protection type |
| pready | 1 | S | all | 0 | Device extends the access phase while low |
| prdata | PARA_DATA_W | S | all | 0 | Read data |
| pslverr | 1 | S | all | 0 | Transfer error indication |

### 4.4 Timing relationships

| Cycle / event | Condition | Observable result |
|---|---|---|
| SETUP cycle | psel high, penable low | Address, direction, and write data are presented |
| ACCESS cycle | psel and penable high | Transfer completes in the first ACCESS cycle with pready high |
| Wait cycle | psel and penable high, pready low | The access phase is extended; the host holds all signals |
| Completion cycle | psel, penable, and pready high | prdata and pslverr are valid for the transfer |

## 5. Protocol requirements

### 5.1 Conventions

The conventions of the template apply unchanged. Every row states one behavior of REF-001 in the author's words.

### 5.2 Signal-level requirements

| Req ID | Strength | Role | Kind | Requirement | Spec ref | Profile | Signals | Rule key | Check type | Check ID | Bound refs | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VREQ-APB-0001 | MUST | M | SIG | The host shall keep paddr stable from the SETUP cycle until the transfer completes. | REF-001 "Operating states: SETUP and ACCESS" | all | paddr | STABLE | SVA | auto | - | Applies while psel is high and until pready completes the transfer |
| VREQ-APB-0002 | MUST | M | SIG | The host shall keep pwrite stable from the SETUP cycle until the transfer completes. | REF-001 "Operating states: SETUP and ACCESS" | all | pwrite | STABLE | SVA | auto | - | Same window as the address |
| VREQ-APB-0003 | MUST | M | SIG | The host shall keep pwdata stable during a write transfer from the SETUP cycle until it completes. | REF-001 "Write transfers" | all | pwdata | STABLE | SVA | auto | - | Write transfers only |
| VREQ-APB-0004 | MUST | M | SIG | The host shall drive pstrb low for every read transfer. | REF-001 "Write strobes" | PROF-01 | pstrb, pwrite | RD_LOW | SVA | auto | BND-002 | Option OPT-01 |
| VREQ-APB-0005 | SHOULD | S | SIG | The device should drive pslverr low in every cycle that is not the completion cycle of a transfer. | REF-001 "Error response" | all | pslverr | LOW_IDLE | SVA | auto | - | pslverr is only meaningful in the completion cycle |

### 5.3 Sequence and handshake requirements

| Req ID | Strength | Role | Kind | Requirement | Spec ref | Profile | Signals | Rule key | Check type | Check ID | Bound refs | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VREQ-APB-0006 | MUST | M | SEQ | The host shall keep penable low in the SETUP cycle, the first cycle in which psel is high for a transfer. | REF-001 "Operating states: SETUP and ACCESS" | all | penable, psel | SETUP | SVA | auto | - | - |
| VREQ-APB-0007 | MUST | M | SEQ | The host shall assert penable in the cycle that follows the SETUP cycle, with psel still high. | REF-001 "Operating states: SETUP and ACCESS" | all | penable, psel | ACCESS | SVA | auto | - | - |
| VREQ-APB-0008 | MUST | M | SEQ | The host shall keep psel high from the SETUP cycle until the completion cycle of the transfer. | REF-001 "Operating states: SETUP and ACCESS" | all | psel | HOLD | SVA | auto | - | - |
| VREQ-APB-0009 | MUST | M | SEQ | The host shall keep penable high in every ACCESS cycle in which pready is low. | REF-001 "Wait states" | all | penable, pready | WAIT_HOLD | SVA | auto | - | - |

### 5.4 Transaction-level requirements

N/A: APB defines no transaction semantics beyond the signal-level and sequence-level rules of Sections 5.2 and 5.3.

### 5.5 Configuration, option, and capability requirements

| Req ID | Strength | Role | Kind | Requirement | Spec ref | Profile | Signals | Rule key | Check type | Check ID | Bound refs | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VREQ-APB-0010 | MAY | S | CAP | The device may extend the access phase by holding pready low for any number of cycles. | REF-001 "Wait states" | all | pready | WAIT | COV | - | BND-001 | - |
| VREQ-APB-0011 | MAY | S | CAP | The device may signal a failed transfer by driving pslverr high in the completion cycle. | REF-001 "Error response" | all | pslverr | ERR | COV | - | - | - |
| VREQ-APB-0012 | MAY | M | CAP | The host may start a new transfer in the cycle that follows a completion cycle without an idle cycle. | REF-001 "Operating states" | all | psel, penable | BACK2BACK | COV | - | - | - |
| VREQ-APB-0013 | MAY | M | CAP | The host may use any combination of write byte strobes for a write transfer. | REF-001 "Write strobes" | PROF-01 | pstrb | STROBE | COV | - | - | Option OPT-01 |
| VREQ-APB-0014 | MAY | M | CAP | The host may use any value of pprot for a transfer. | REF-001 "Protection control" | PROF-01 | pprot | PROT | COV | - | - | Option OPT-02 |
| VREQ-APB-0015 | MAY | B | CFG | The interface may omit pstrb and pprot in the APB3 profile. | REF-001 "Signal list" | PROF-02 | pstrb, pprot | PROFILE | NONE | - | - | NONE: profile selection is a build-time choice, nothing to observe at run time |

### 5.6 Boundary analysis

| Bound ID | Quantity | Unit | Valid min | Valid max | Invalid below | Invalid above | Derivation | Source req |
|---|---|---|---|---|---|---|---|---|
| BND-001 | Device wait cycles in one transfer | cycle | 0 | 16 | - | - | The standard sets no upper limit; the VIP supports 0 to 16 (DEC-002) | VREQ-APB-0010 |
| BND-002 | pstrb value during a read transfer | value | 0 | 0 | - | 1 | Reads require pstrb low; any non-zero value violates VREQ-APB-0004 | VREQ-APB-0004 |

## 6. VIP functional model

### 6.1 Transaction item fields

| Item field | Type | Width | Rand | Description | Roles |
|---|---|---|---|---|---|
| addr | logic | PARA_ADDR_W | rand | Transfer address | M |
| write | logic | 1 | rand | 1 for write, 0 for read | M |
| data | logic | PARA_DATA_W | rand | Write data from the host, or read data from the device | M,S |
| strb | logic | PARA_DATA_W/8 | rand | Write byte strobes | M |
| prot | logic | 3 | rand | Protection type | M |
| slverr | logic | 1 | rand | Error response from the device | S |
| wait_states | int unsigned | 32 | rand | Wait cycles the device inserts | S |
| idle_cycles | int unsigned | 32 | rand | Idle cycles the host inserts before the transfer | M |
| inj_kind | enum:apb_inj_e | 8 | none | Error injection selected for this transfer | M,S |

### 6.2 Stimulus capabilities

| Cap ID | Role | Capability | Config knobs | Sequence | Requirements |
|---|---|---|---|---|---|
| CAP-001 | S | Insert wait states | device_wait_min, device_wait_max | apb_wait_state_seq | VREQ-APB-0010 |
| CAP-002 | S | Return an error response | slverr_pct | apb_slave_error_seq | VREQ-APB-0011 |
| CAP-003 | M | Issue back-to-back transfers | host_idle_min, host_idle_max | apb_back2back_seq | VREQ-APB-0012 |
| CAP-004 | M | Write with any strobe pattern | none | apb_strobe_seq | VREQ-APB-0013 |
| CAP-005 | M | Transfer with any protection value | default_prot | apb_prot_seq | VREQ-APB-0014 |

### 6.3 Error injection

| Inj ID | Role | Violation to inject | Mechanism | Violated requirement | Expected check |
|---|---|---|---|---|---|
| INJ-001 | M | Change paddr in the access phase | item field inj_kind = APB_INJ_PADDR_CHANGE | VREQ-APB-0001 | auto |
| INJ-002 | M | Change pwrite in the access phase | item field inj_kind = APB_INJ_PWRITE_CHANGE | VREQ-APB-0002 | auto |
| INJ-003 | M | Change pwdata in the access phase of a write | item field inj_kind = APB_INJ_PWDATA_CHANGE | VREQ-APB-0003 | auto |
| INJ-004 | M | Drive a non-zero pstrb on a read | item field inj_kind = APB_INJ_PSTRB_READ | VREQ-APB-0004 | auto |
| INJ-005 | S | Drive pslverr high in a non-completion cycle | item field inj_kind = APB_INJ_PSLVERR_EARLY | VREQ-APB-0005 | auto |
| INJ-006 | M | Assert penable in the SETUP cycle | item field inj_kind = APB_INJ_PENABLE_SETUP | VREQ-APB-0006 | auto |
| INJ-007 | M | Skip the ACCESS cycle after SETUP | item field inj_kind = APB_INJ_NO_ACCESS | VREQ-APB-0007 | auto |
| INJ-008 | M | Drop psel before the completion cycle | item field inj_kind = APB_INJ_PSEL_DROP | VREQ-APB-0008 | auto |
| INJ-009 | M | Drop penable during a wait cycle | item field inj_kind = APB_INJ_PENABLE_DROP | VREQ-APB-0009 | auto |

### 6.4 Monitor and collector

| Monitor ID | Observed event | Transaction produced | Analysis port | Notes |
|---|---|---|---|---|
| MON-001 | Completion cycle: psel, penable, and pready high | apb_item | ap | One item per completed transfer; wait cycles are counted into wait_states |

## 7. VIP API and usability contract

### 7.1 Configuration knobs

| Knob | Type | Default | Description | Related |
|---|---|---|---|---|
| device_wait_min | int unsigned | 0 | Minimum wait cycles the device inserts | CAP-001 |
| device_wait_max | int unsigned | 4 | Maximum wait cycles the device inserts; at most 16 | CAP-001 |
| slverr_pct | int unsigned | 0 | Percentage of transfers that complete with an error response | CAP-002 |
| host_idle_min | int unsigned | 0 | Minimum idle cycles between transfers | CAP-003 |
| host_idle_max | int unsigned | 3 | Maximum idle cycles between transfers | CAP-003 |
| default_prot | logic [2:0] | 0 | Protection value used when a sequence does not set one | CAP-005 |
| max_wait_warn | int unsigned | 16 | Wait cycles above which the performance check warns | VREQ-APB-0010 |

### 7.2 Usability contract

| Contract ID | Topic | Specification |
|---|---|---|
| UC-01 | Package and import | Package apb_vip_pkg; the single import line is import apb_vip_pkg::*; |
| UC-02 | Instantiation steps | Create apb_agent_cfg and set its vif; create apb_agent with that cfg; start any sequence on the agent sequencer |
| UC-03 | Default behavior | Legal random transfers with 0 to 3 idle cycles and 0 to 4 device wait cycles, no errors |
| UC-04 | Mode knobs | The base knobs is_active, if_mode, and has_driver select host, device, or passive monitor; protocol knobs adjust traffic |
| UC-05 | Width and option control | Widths come from PARA_ADDR_W and PARA_DATA_W through the APB_VIP_ADDR_W and APB_VIP_DATA_W macros; options follow the profile |
| UC-06 | Checker control | cfg.disable_check with a check ID and a reason; cfg.rec_on disables all REC checks together |
| UC-07 | Message format | Message ID is the check ID; the text starts with the requirement ID and the spec reference |
| UC-08 | Quickstart | Test apb_quickstart_test connects a host and a device of this VIP on one interface and passes with no error |
| UC-09 | Reset behavior | Reset may assert at any cycle; drivers abandon the item, drive reset values, and resume after release |
| UC-10 | X policy | The host drives X on paddr, pwdata, and pstrb while psel is low; the device drives X on prdata while it is not completing a read |
| UC-11 | Error injection selection | Set the inj_kind item field in a sequence; no callbacks |
| UC-12 | Documentation set | README with cfg fields, config_db keys, TLM ports, overridable classes, interface and clock assumptions |
| UC-13 | Versioning | Semantic version plus the spec_rev tag IHI 0024C |

## 8. Checker requirements

| Policy ID | Topic | Specification |
|---|---|---|
| CP-01 | Severity mapping | ERR checks report with uvm_error; REC checks report with uvm_warning |
| CP-02 | Role handling | Simulation asserts every check; a formal run assumes the checks of the role that does not belong to the DUT |
| CP-03 | Waiver mechanism | cfg.disable_check with a check ID and a mandatory reason; the reason is printed in the report phase |
| CP-04 | Formal compatibility | Code that calls UVM is guarded by the VLSIT_VIP_UVM macro; the VLSIT_VIP_FORMAL macro removes reporting |
| CP-05 | Performance knobs | max_wait_warn raises a REC-class warning when a transfer waits longer |
| CP-06 | Unimplemented stub behavior | A stub reports a warning with its check ID at time 0 and in the report phase |
| CP-07 | Vacuity control | Each assertion has a cover of its antecedent with the same check ID |

### 8.1 Check expressions

| Req ID | Operator | Antecedent | Consequent | Message |
|---|---|---|---|---|
| VREQ-APB-0001 | NEXT | psel && !(penable && pready) | !psel OR $stable(paddr) | paddr changed before the transfer completed |
| VREQ-APB-0002 | NEXT | psel && !(penable && pready) | !psel OR $stable(pwrite) | pwrite changed before the transfer completed |
| VREQ-APB-0003 | NEXT | psel && pwrite && !(penable && pready) | !psel OR !pwrite OR $stable(pwdata) | pwdata changed during a write transfer |
| VREQ-APB-0004 | SAME | psel && !pwrite | pstrb == '0 | pstrb is not low during a read transfer |
| VREQ-APB-0005 | SAME | !(psel && penable && pready) | !pslverr | pslverr is high outside the completion cycle |
| VREQ-APB-0006 | SAME | psel && (!$past(psel) OR $past(psel && penable && pready)) | !penable | penable is high in the SETUP cycle |
| VREQ-APB-0007 | NEXT | psel && !penable | !psel OR penable | penable was not asserted after the SETUP cycle |
| VREQ-APB-0008 | NEXT | psel && !(penable && pready) | psel | psel dropped before the completion cycle |
| VREQ-APB-0009 | NEXT | psel && penable && !pready | !psel OR penable | penable dropped during a wait cycle |

## 9. Coverage requirements

| Cov Req ID | Goal | Requirements | Bins / crosses | Notes |
|---|---|---|---|---|
| CVR-001 | Wait states crossed with transfer direction | VREQ-APB-0010 | wait_states bins 0, 1, 2 to 4, 5 to 16; cross with write | Valid bins only |
| CVR-002 | Write strobe patterns | VREQ-APB-0013 | each strobe bit; all-ones; sparse patterns | Option OPT-01 |

## 10. Sequences and compliance tests

| Seq ID | Sequence | Role | Purpose | Requirements |
|---|---|---|---|---|
| SEQ-001 | apb_base_seq | M | Base sequence and common helpers | - |
| SEQ-002 | apb_wait_state_seq | S | Exercise device wait states | VREQ-APB-0010 |
| SEQ-003 | apb_slave_error_seq | S | Exercise the error response | VREQ-APB-0011 |
| SEQ-004 | apb_back2back_seq | M | Exercise back-to-back transfers | VREQ-APB-0012 |

## 11. Qualification plan

| Qual ID | Topic | Specification |
|---|---|---|
| QP-01 | Counterpart model | A small behavioral APB model that drives and answers valid and invalid transfers cycle by cycle, written separately from the VIP checkers |
| QP-02 | Independence | The standard analysis is reviewed by a person who does not implement the VIP; the reviewer is recorded in requirements.csv |
| QP-03 | Expected-error mechanism | vlsit_vip_expect_catcher declares the expected check ID, minimum, maximum, and window before each negative trace |
| QP-04 | Variants and seeds | VAR-01 to VAR-03, each with the seed count fixed in the gate table; seeds are recorded in the logs |
| QP-05 | Simulators | Command templates are set per simulator in the run script; Verilator lint covers the interface and the checker |
| QP-06 | Coverage closure | All valid bins of Section 9 and Section 5.6 closed; exclusions need a category and a reason |
| QP-07 | Lint and formal | Verilator lint of the interface and checker without UVM; formal use of the checkers is not planned |

| Gate | Criteria |
|---|---|
| VIP-0 | Defaults of VLSIT_VIP_Design_Rule.md Section 11 |
| VIP-1 | Defaults of VLSIT_VIP_Design_Rule.md Section 11 |
| VIP-2 | Defaults of VLSIT_VIP_Design_Rule.md Section 11 |
| VIP-3 | Defaults of Section 11, with 20 seeds per variant |

## 12. Deliverables and packaging

| Pkg ID | Item | Specification |
|---|---|---|
| PK-01 | Directory layout | Follows VFIL-03 with no deviation |
| PK-02 | Package and filelist | apb_vip_pkg.sv and filelist/apb_vip.f |
| PK-03 | Documentation | README, traceability report, qualification report, release notes |
| PK-04 | Versioning | Semantic version; spec_rev tag IHI 0024C |
| PK-05 | License and attribution | Project license of the user; the VLSIT VIP base package carries the license of this repository |

## 13. Traceability matrix

| Req ID | Check ID | Cov ID | Sequence / injection | Test pos | Test neg | Status |
|---|---|---|---|---|---|---|
| (generated) | - | - | - | - | - | not generated |

## 14. Assumptions, dependencies, and decisions

| Decision ID | Type | Statement | Impact | Resolution / status |
|---|---|---|---|---|
| DEC-001 | Assumption | Spec references cite clause titles because clause numbers were not verified against the standard text | Every spec ref must be confirmed before release | Open until confirmed against the controlled copy |
| DEC-002 | Decision | The device wait limit is 16 cycles because the standard sets no upper limit | BND-001 and the max_wait_warn knob | Closed |
| DEC-003 | Decision | One psel line is modeled; address decoding across several devices is out of scope | Compliance deviation in Section 2.3 | Closed |
| DEC-004 | Decision | pslverr is present in both profiles and tied low by an integrator that has no error response | Signals table | Closed |
| DEC-005 | Dependency | The VLSIT VIP base package supplies the agent base classes and the expected-error catcher | Section 6 and Section 11 | Closed |

## 15. Glossary

| Term | Definition |
|---|---|
| APB | Advanced Peripheral Bus of the AMBA family |
| Host | The side that starts transfers (requester, master) |
| Device | The side that answers transfers (completer, slave) |
| SETUP, ACCESS | The two phases of an APB transfer |

## 16. References used to shape this template

This example follows `VLSIT_ASIC_VIP_Specification_Template.md`. The practice behind it is described in `docs/VLSIT_VIP_Build_Process.md` of this repository.
