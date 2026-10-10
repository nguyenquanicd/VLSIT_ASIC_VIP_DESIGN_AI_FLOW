---
document_type: asic_vip_specification
document_id: "<TAG>-VIP-SPEC"
title: "<Protocol or standard> Verification IP Specification"
vip_name: "<tag>_vip"
proto_tag: "<tag>"
version: "0.1"
status: "Draft"
spec_revision_locked: "<standard document ID and revision, e.g. IHI 0024E>"
language: "SystemVerilog IEEE 1800-2017; UVM IEEE 1800.2-2020"
vip_rules: "VLSIT_VIP_Design_Rule.md"
rtl_rules: "VLSIT_RTL_Design_Rule.md"
---

# <Protocol or Standard> Verification IP Specification

> **Purpose:** The mandatory input to the VLSIT ASIC VIP Design AI Flow. It turns a protocol or standard specification into a reviewed, machine-checkable contract for building, qualifying, and releasing a Verification IP (VIP).
>
> **How to fill it:** Replace every angle-bracket placeholder. A section that does not apply is replaced by a paragraph that starts with `N/A:` and gives the reason. Never silently omit a decision. Record every ambiguity or assumption as a row in [Section 14](#14-assumptions-dependencies-and-decisions); do not leave `TBD` in a requirement.
>
> **Machine-readable tables:** The tables below are parsed by `validate_vip_spec.py` and the later flow stages. Keep the column names and order exactly as written. One row per fact. Do not merge cells.
>
> **Requirement terms:** `shall` / `shall not` = MUST (mandatory), `should` = SHOULD (recommended), `may` = MAY (optional). Each requirement row states one normative behavior of the protocol, in your own words, with a spec reference. Do not copy standard text; paraphrase and cite the clause.
>
> **Rules:** the VIP built from this specification obeys `VLSIT_VIP_Design_Rule.md`. Cite rule IDs (`VNAM-01`, `VCHK-02`, ...) in decisions.

## Document map

1. [Purpose, scope, and context](#1-purpose-scope-and-context)
2. [Normative references and precedence](#2-normative-references-and-precedence)
3. [Roles, profiles, and options](#3-roles-profiles-and-options)
4. [Interface definition](#4-interface-definition)
5. [Protocol requirements](#5-protocol-requirements)
6. [VIP functional model](#6-vip-functional-model)
7. [VIP API and usability contract](#7-vip-api-and-usability-contract)
8. [Checker requirements](#8-checker-requirements)
9. [Coverage requirements](#9-coverage-requirements)
10. [Sequences and compliance tests](#10-sequences-and-compliance-tests)
11. [Qualification plan](#11-qualification-plan)
12. [Deliverables and packaging](#12-deliverables-and-packaging)
13. [Traceability matrix](#13-traceability-matrix)
14. [Assumptions, dependencies, and decisions](#14-assumptions-dependencies-and-decisions)
15. [Glossary](#15-glossary)
16. [References used to shape this template](#16-references-used-to-shape-this-template)

## 1. Purpose, scope, and context

### 1.1 Purpose and scope

State which protocol or standard this VIP verifies, which DUT roles it serves, and what the VIP provides (stimulus, checking, coverage, debug).

**Included:** <roles, profiles, options, checking, coverage, sequences>

**Excluded:** <unsupported options and features, with the reason>

### 1.2 Build-or-reuse decision

List the existing VIP (commercial or open-source) that was considered and why the decision was made. If none was considered, add one row stating that and the reason.

| Candidate | Source | Requirement coverage | Decision | Reason |
|---|---|---|---|---|
| <existing VIP or "none considered"> | <vendor, repository, or path> | <share of the requirements in Section 5 it covers, or unknown> | Build / Reuse / Extend | <reason> |

### 1.3 Target environment

| Item | Specification |
|---|---|
| Simulator(s) for qualification | <name and version> |
| UVM version | <IEEE 1800.2-2020 or 1.2, with library release> |
| Lint tool for interface and checker | <name and version> |
| Formal tool for checkers (optional) | <name and version, or "not used"> |
| Operating system and shell | <...> |
| Project name and human author | <...> |

## 2. Normative references and precedence

### 2.1 Normative references

Record the exact title, document ID, revision, and controlled location of every standard used. Do not cite an unspecified "latest" revision. Record known errata as separate rows.

| Ref ID | Document and revision | Applicable clauses | Authority / notes |
|---|---|---|---|
| REF-001 | <protocol specification, ID, and revision> | <clauses> | Protocol authority |
| REF-002 | VLSIT VIP Design Rules v1, VLSIT_VIP_Design_Rule.md | All | VIP coding, naming, qualification, and release rules |
| REF-003 | VLSIT RTL Design Rules v2, VLSIT_RTL_Design_Rule.md | Inherited items listed in VSCP-03 | Referenced for inherited conventions only |

### 2.2 Precedence and conflict handling

1. The selected protocol revision (REF-001) defines protocol behavior.
2. This specification defines the VIP contract: scope, interface, API, qualification, and delivery.
3. `VLSIT_VIP_Design_Rule.md` governs VIP code. A requirement that conflicts with it is revised; no local exception is created.
4. Resolve a conflict by an explicit decision in Section 14. Do not guess or weaken a requirement.

### 2.3 Compliance declaration

| Standard | Revision / profile | Role implemented | Options | Deviations |
|---|---|---|---|---|
| <protocol> | <revision and profile> | <host / device / monitor> | <options in scope> | None / <list> |

## 3. Roles, profiles, and options

### 3.1 Roles

A role is a behavior the VIP can take. `Letter` is `M` (host or master side drives the request signals), `S` (device or slave side drives the response signals), or `B` (bus-level passive observer). `Mode` is `ACTIVE` (driver present) or `PASSIVE` (monitor only).

| Role ID | Role | Letter | Drives | Mode |
|---|---|---|---|---|
| ROLE-01 | Host | M | <signals driven by the host> | ACTIVE |
| ROLE-02 | Device | S | <signals driven by the device> | ACTIVE |
| ROLE-03 | Monitor | B | none | PASSIVE |

### 3.2 Profiles

A profile fixes the protocol revision and the signal set. One VIP build targets one profile at a time; several profiles may be listed if the VIP supports them.

| Profile ID | Profile | Standard revision | Included options | Notes |
|---|---|---|---|---|
| PROF-01 | <profile name> | <revision> | <OPT-IDs or none> | <...> |

### 3.3 Optional features

| Option ID | Optional feature | Signals added | Default | Status |
|---|---|---|---|---|
| OPT-01 | <feature> | <signals or none> | <on/off> | In scope |

`Status` is `In scope` or `Out of scope`. Every optional feature of the standard appears here, including those excluded.

### 3.4 Variants for qualification

A variant is a parameter and option combination that the qualification regression must run (Section 11).

| Variant ID | Profile | Options | Parameter values | Qualification target |
|---|---|---|---|---|
| VAR-01 | PROF-01 | <OPT-IDs or none> | <PARA_NAME=value list> | <why this variant> |

## 4. Interface definition

### 4.1 Clocks and resets

| Domain | Clock signal | Reset signal | Reset polarity | Notes |
|---|---|---|---|---|
| <domain> | <protocol clock mnemonic, lowercase> | <protocol reset mnemonic, lowercase> | Active-low | <...> |

`Reset polarity` is `Active-low` or `Active-high`. Clock and reset signal names follow the protocol (VIFC-03).

### 4.2 Parameters

Every width or limit that varies between integrations is an interface parameter (VIFC-01). Name them `PARA_<NAME>`. Write `N/A:` instead of the table if all widths are fixed.

| Parameter | Description | Default | Legal values | Unit |
|---|---|---|---|---|
| PARA_<NAME> | <purpose, dependencies, restrictions> | <default> | <legal values or range> | <bit / byte / count / none> |

### 4.3 Signals

List every signal of the selected profile and its options, in the lowercase protocol mnemonic. `Driver` is `M`, `S`, `CLK`, or `RST`. `Width` is a number or an expression of `PARA_` names.

| Signal | Width | Driver | Profile / option | Reset / idle | Description |
|---|---|---|---|---|---|
| <signal> | <width> | M | PROF-01 | <reset or idle value> | <meaning> |

### 4.4 Timing relationships

Describe sampling edge, setup/hold intent, and the relationship between signals that the requirements in Section 5 depend on. Use cycle tables where prose is ambiguous.

| Cycle / event | Condition | Observable result |
|---|---|---|
| <t0> | <...> | <...> |

## 5. Protocol requirements

### 5.1 Conventions

- One requirement row states one normative behavior of the protocol, paraphrased. The requirement text contains the modal verb that matches `Strength`: `shall` or `shall not` for MUST, `should` for SHOULD, `may` for MAY.
- `Role` is the letter of the role that must obey the requirement: `M`, `S`, or `B`.
- `Kind` is `SIG` (signal-level: stability, X, value range, timing), `SEQ` (sequence or handshake order), `TXN` (transaction-level meaning), `CFG` (parameter or option rule), or `CAP` (a capability the VIP must offer to stimulate or observe the protocol).
- `Spec ref` is `REF-nnn` followed by the clause, table, or figure: `REF-001 §<clause>`.
- `Signals` lists the lowercase mnemonics involved. `Rule key` is an uppercase token that names the rule, used to derive the check ID (`STABLE`, `X`, `SETUP`, `RANGE`, ...).
- `Check type` is `SVA`, `CLASS` (check in the monitor class), `COV` (coverage only), or `NONE`. `NONE` requires `NONE:<reason>` in `Notes`. A MUST or SHOULD requirement is not `COV` or `NONE` unless it cannot be observed at the interface.
- `Check ID` is `auto` (derived by the flow as `<TAG>_<ERR|REC><M|S|B>_<SIGNAL>_<RULE>`) or an explicit ID of that form. `ERR` is for MUST, `REC` for SHOULD.
- `Bound refs` lists `BND-nnn` rows from Section 5.6, or `-` when the requirement has no numeric boundary.
- Requirement IDs are `VREQ-<TAG>-<NNNN>`, permanent, and never reused.

Every requirement table uses these columns, in this order.

### 5.2 Signal-level requirements

| Req ID | Strength | Role | Kind | Requirement | Spec ref | Profile | Signals | Rule key | Check type | Check ID | Bound refs | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VREQ-<TAG>-0001 | MUST | M | SIG | <The host shall ...> | REF-001 §<clause> | PROF-01 | <signal> | <RULE> | SVA | auto | - | <...> |

### 5.3 Sequence and handshake requirements

| Req ID | Strength | Role | Kind | Requirement | Spec ref | Profile | Signals | Rule key | Check type | Check ID | Bound refs | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VREQ-<TAG>-0002 | MUST | M | SEQ | <...> | REF-001 §<clause> | PROF-01 | <signals> | <RULE> | SVA | auto | - | <...> |

### 5.4 Transaction-level requirements

Write `N/A:` and a reason if the protocol has no transaction-level rule beyond Sections 5.2 and 5.3.

| Req ID | Strength | Role | Kind | Requirement | Spec ref | Profile | Signals | Rule key | Check type | Check ID | Bound refs | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VREQ-<TAG>-0003 | SHOULD | S | TXN | <...> | REF-001 §<clause> | PROF-01 | <signals> | <RULE> | CLASS | auto | - | <...> |

### 5.5 Configuration, option, and capability requirements

| Req ID | Strength | Role | Kind | Requirement | Spec ref | Profile | Signals | Rule key | Check type | Check ID | Bound refs | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VREQ-<TAG>-0004 | MAY | M | CAP | <The host may ...> | REF-001 §<clause> | PROF-01 | <signals> | <RULE> | COV | - | - | <...> |

### 5.6 Boundary analysis

For every numeric quantity in Section 5, record the valid limits and the first invalid value on each side. These rows drive the positive and negative qualification traces and the coverage bins. If a limit is not stated by the standard, derive it, record the derivation, and add a decision in Section 14.

| Bound ID | Quantity | Unit | Valid min | Valid max | Invalid below | Invalid above | Derivation | Source req |
|---|---|---|---|---|---|---|---|---|
| BND-001 | <quantity> | <unit> | <min> | <max> | <min - 1> | <max + 1> | <spec statement or derived reason> | VREQ-<TAG>-0001 |

Write `-` in `Invalid below` or `Invalid above` if the side does not exist.

## 6. VIP functional model

### 6.1 Transaction item fields

| Item field | Type | Width | Rand | Description | Roles |
|---|---|---|---|---|---|
| <field> | logic | <width> | rand | <meaning> | M,S |

`Type` is a SystemVerilog type name or `enum:<name>`. `Rand` is `rand`, `randc`, or `none`.

### 6.2 Stimulus capabilities

Every stimulus the VIP must be able to generate or every behavior it must offer, so the protocol can be exercised at its limits. Each capability has one named sequence.

| Cap ID | Role | Capability | Config knobs | Sequence | Requirements |
|---|---|---|---|---|---|
| CAP-001 | M | <capability> | <knob names or none> | <tag>_<function>_seq | VREQ-<TAG>-0004 |

### 6.3 Error injection

Each mandatory check needs a way to produce exactly one violation (VQUA-01). Describe the injection, the mechanism, and the check expected to fire.

| Inj ID | Role | Violation to inject | Mechanism | Violated requirement | Expected check |
|---|---|---|---|---|---|
| INJ-001 | M | <violation> | item field `<field>` / sequence `<name>` | VREQ-<TAG>-0001 | <check ID or auto> |

Write `auto` in `Expected check` to use the check ID derived for the violated requirement.

### 6.4 Monitor and collector

| Monitor ID | Observed event | Transaction produced | Analysis port | Notes |
|---|---|---|---|---|
| MON-001 | <event that completes a transfer> | <tag>_item | ap | <...> |

## 7. VIP API and usability contract

### 7.1 Configuration knobs

Protocol-specific knobs on top of the base knobs of VCFG-02 (`is_active`, `en_monitor`, `en_cov`, `if_mode`, `has_driver`, `ok_to_end_delay_ns`, `in_reset`).

| Knob | Type | Default | Description | Related |
|---|---|---|---|---|
| <knob> | <type> | <default> | <effect> | CAP-001 |

### 7.2 Usability contract

Fill the value for every row. These rows implement VAPI-01 to VAPI-07; each row states how this VIP satisfies the topic.

| Contract ID | Topic | Specification |
|---|---|---|
| UC-01 | Package and import | <package name and the single import line> |
| UC-02 | Instantiation steps | <the three steps, VAPI-01> |
| UC-03 | Default behavior | <what the VIP does with default cfg: traffic, delay range> |
| UC-04 | Mode knobs | <how base and protocol knobs select roles and modes> |
| UC-05 | Width and option control | <interface parameters versus cfg, VAPI-04> |
| UC-06 | Checker control | <disable by check ID with reason; group disable for REC> |
| UC-07 | Message format | <ID, requirement ID, spec reference, verbosity levels> |
| UC-08 | Quickstart | <loopback test name and what it proves> |
| UC-09 | Reset behavior | <reset at any time, VAPI-03> |
| UC-10 | X policy | <payload X while qualifier inactive, VIFC-07> |
| UC-11 | Error injection selection | <item field or sequence; no callbacks> |
| UC-12 | Documentation set | <README sections, VAPI-05> |
| UC-13 | Versioning | <semantic version and spec_rev tag, VAPI-07> |

## 8. Checker requirements

| Policy ID | Topic | Specification |
|---|---|---|
| CP-01 | Severity mapping | <ERR checks use uvm_error; REC checks use uvm_warning> |
| CP-02 | Role handling | <assert/assume/cover selection by role and mode, VCHK-02> |
| CP-03 | Waiver mechanism | <disable by check ID, reason recorded where> |
| CP-04 | Formal compatibility | <guard macro name, constructs avoided, VCHK-04> |
| CP-05 | Performance knobs | <maximum wait or latency knob and default, VCHK-10> |
| CP-06 | Unimplemented stub behavior | <message and severity at time 0, VCHK-06> |
| CP-07 | Vacuity control | <cover property paired with each assertion, VCHK-07> |

The checker inventory (one check per requirement) is generated into Section 13; it is not listed here.

### 8.1 Check expressions

Optional, and the main way to cut implementation effort. For each requirement with check type `SVA`, state the property as two single-cycle boolean expressions over the signals of Section 4.3 (and `PARA_` names). The generator composes the complete assertion and the paired cover of the antecedent; the property is reviewed here, at Gate 1, before any code exists. A requirement without a row stays a stub.

- `Operator`: `SAME` means `antecedent |-> consequent` (consequent in the same cycle); `NEXT` means `antecedent |=> consequent` (consequent in the next cycle).
- Write `OR` for `||` (the pipe character splits markdown cells). `&&`, `!`, `==`, `!=`, `<`, `>`, `inside`, and `$stable`, `$past`, `$rose`, `$fell`, `$changed`, `$onehot`, `$onehot0`, `$isunknown`, `$countones` are allowed. No `|`, `##`, `[*`, or other system functions.
- Make the property orthogonal: it must not fire when another requirement is the one violated (for example guard with `!psel OR ...`).
- `Message` is the short violation text printed with the check ID, the requirement ID, and the spec reference.

| Req ID | Operator | Antecedent | Consequent | Message |
|---|---|---|---|---|
| VREQ-<TAG>-0001 | NEXT | <antecedent expression> | <consequent expression> | <short violation text> |

## 9. Coverage requirements

Derived coverage (valid and invalid bins for every boundary in Section 5.6, one coverage item per requirement with a check) is generated by the flow. Add here only extra goals, such as crosses.

| Cov Req ID | Goal | Requirements | Bins / crosses | Notes |
|---|---|---|---|---|
| CVR-001 | <goal> | VREQ-<TAG>-0001 | <bins and crosses> | <...> |

## 10. Sequences and compliance tests

| Seq ID | Sequence | Role | Purpose | Requirements |
|---|---|---|---|---|
| SEQ-001 | <tag>_base_seq | M | Base sequence and common helpers | - |

## 11. Qualification plan

| Qual ID | Topic | Specification |
|---|---|---|
| QP-01 | Counterpart model | <independent behavioral model that emits valid and invalid items on demand> |
| QP-02 | Independence | <who analyzed the standard, who implemented, who reviews, VQUA-07> |
| QP-03 | Expected-error mechanism | <vlsit_vip_expect_catcher usage and window policy, VQUA-04> |
| QP-04 | Variants and seeds | <VAR-IDs and seed policy, count and recording, VQUA-06> |
| QP-05 | Simulators | <simulators and command templates used for qualification> |
| QP-06 | Coverage closure | <closure target and exclusion categories with reasons> |
| QP-07 | Lint and formal | <lint scope; formal use of checkers, or "not used"> |

| Gate | Criteria |
|---|---|
| VIP-0 | <use the defaults of VLSIT_VIP_Design_Rule.md Section 11, or tighten them here> |
| VIP-1 | <...> |
| VIP-2 | <...> |
| VIP-3 | <...> |

## 12. Deliverables and packaging

| Pkg ID | Item | Specification |
|---|---|---|
| PK-01 | Directory layout | <follows VFIL-03, deviations listed> |
| PK-02 | Package and filelist | <package file and filelist format> |
| PK-03 | Documentation | <README, traceability report, qualification report, release notes> |
| PK-04 | Versioning | <semantic version, spec_rev tag> |
| PK-05 | License and attribution | <license of the VIP and attribution of any reused base code> |

## 13. Traceability matrix

This table is generated and maintained by `vlsit-vip-vplan` and updated by later stages. Do not fill it by hand.

| Req ID | Check ID | Cov ID | Sequence / injection | Test pos | Test neg | Status |
|---|---|---|---|---|---|---|
| (generated) | - | - | - | - | - | not generated |

## 14. Assumptions, dependencies, and decisions

Record every ambiguity, assumption, dependency, and open question. `Type` is `Assumption`, `Dependency`, `Decision`, or `Open`. An `Open` row that affects a requirement blocks Gate VIP-0 for that requirement.

| Decision ID | Type | Statement | Impact | Resolution / status |
|---|---|---|---|---|
| DEC-001 | Assumption | <statement> | <affected requirement, interface, qualification, or integration> | <resolution or status> |

## 15. Glossary

| Term | Definition |
|---|---|
| <term> | <definition> |

## 16. References used to shape this template

This template follows the structure of `VLSIT_ASIC_IP_Design_Specification_Template.md` and the VIP process in `docs/VLSIT_VIP_Build_Process.md`. Sources of the underlying practice:

1. Cerisier et al., *Qualification of a Verification IP under Requirement Based Verification standards*, DVCon: protocol-specification-first analysis; valid and invalid boundaries; the VIP as a DUT.
2. Venkataramanan and Kumari, *Architecting Checker IP for AMBA protocols*, DVCon: role-aware assert/assume/cover, unit tests per assertion.
3. Arm, *AMBA 4 AXI4, AXI4-Lite, and AXI4-Stream Protocol Assertions User Guide*, DUI 0534B: check IDs with specification references; parameters and recommendation switches.
4. Sutherland and Fitzpatrick, *UVM Rapid Adoption: A Practical Subset of UVM*, DVCon: UVM subset.
5. OpenTitan, `uvmdvgen` and the DV methodology: generated agent skeleton, base agent configuration, maturity gates.
6. Zhang, Radulovic, and Dworzak, *Fully Automated Verification Framework for Configurable IPs*: requirement-to-vPlan-to-result traceability.
