# VLSIT Verification IP Design Rules (v1)

> **Purpose:** Default rules for SystemVerilog/UVM Verification IP (VIP) that checks, drives, and observes an ASIC interface protocol. Priority: accuracy against the protocol specification, requirement traceability, ease of use, and reuse across projects.
> **Repository:** VLSIT_ASIC_VIP_DESIGN_AI_FLOW
> **Language baseline:** IEEE 1800-2017 and UVM IEEE 1800.2-2020 (a UVM 1.2 profile is allowed when the project selects it in the VIP specification).
> **Companion files:** `VLSIT_ASIC_VIP_Specification_Template.md` (mandatory input format), `VLSIT_RTL_Design_Rule.md` (RTL rules v2, for design RTL only).

## 0. How to apply this document (for AI agents)

- **MUST / MUST NOT** = mandatory. **SHOULD** = default; a deviation needs a written reason in the file header or the review notes.
- Rule IDs carry the prefix `V` (for example `VNAM-01`) so they never collide with the RTL rule IDs (`NAM-01`, `SEQ-01`, ...). Both files can be cited in one report without ambiguity.
- Evidence states are `PASS`, `FAIL`, `NOT_RUN`, and `N/A`. `N/A` requires proof that the feature is absent. A missing tool or log is `NOT_RUN`, never `PASS`.
- Do not weaken this file to make a VIP pass. Resolve a conflict by changing the VIP specification or the implementation, or by asking the user.
- A rule that exists only in one place is stated only in that place. Cross-references use rule IDs.

## 1. Scope and relationship to the RTL rules v2

- **VSCP-01** Covers the verification source set of a VIP: SystemVerilog interface, checker code (SVA), UVM class library, qualification environment, examples, and documentation.
- **VSCP-02** VIP sources MUST NOT appear in a synthesis filelist (RTL v2 Section 11, source-set hygiene).
- **VSCP-03** The RTL rules v2 scope statement (SCP-01) excludes verification sources, so the RTL rules do not apply to VIP code unless this table says so. The table is the single place that resolves the relationship.

| RTL v2 rule | Treatment in VIP sources | Reason |
|---|---|---|
| FIL-01 header | Inherited, with the VIP header in VFIL-02 | Same authorship convention |
| FIL-03, P29 spaces only | Inherited (VFIL-04) | Same hygiene |
| CMT-01 to CMT-03, CMT-05 | Inherited (VCMT-01) | Same comment discipline, 100-character limit |
| NAM-01 zero-based index | Inherited | Same convention |
| NAM-02 external names keep external form | Inherited; protocol signals keep their lowercase mnemonic | Protocol authority |
| NAM-04, NAM-08 abbreviation table | Inherited (VNAM-04) | One abbreviation vocabulary |
| NAM-05 `_n` for active-low | Inherited | Same convention |
| NAM-07 30-character limit | **Replaced** by VNAM-08 | UVM class names are longer; limit set separately |
| PAR-01, PAR-02 parameters | Inherited for interface, checker, and class parameters (`PARA_` and the three comment lines); `logic [31:0]` typing applies to module/interface parameters, class parameters may be `int` or `type` | Same documentation of parameters |
| PRT-01 to PRT-04 protocol naming | Applies to DUT-facing ports in integration tops. VIP interfaces use the bare lowercase protocol mnemonic (VIFC-02) | The VIP interface is role-neutral; direction depends on the role |
| TYP-*, COM-*, ARI-*, SEQ-*, RST-*, CLK-*, HIE-*, ENM-* | Not applicable | Synthesis-only rules |
| P11 (package, interface) | **Permitted** in VIP sources | RTL v2 allows them in verification source sets |
| P14, P19 (system tasks, SVA) | **Permitted** in VIP sources, within VCHK and VP rules | Verification source set |
| P21, P22, P27 (two-state, signed, class, string, queue) | **Permitted** in UVM class code; hardware-facing interface signals remain 4-state `logic` (VIFC-01) | Class code is not hardware |
| P1 delay controls | Allowed only in the qualification counterpart and example top for clock generation (VP-08) | Clock generation |

## 2. Files and structure

- **VFIL-01** One class, one interface, or one checker per `.sv` or `.svh` file; the file name equals the primary declaration name. Classes are included into the VIP package by `` `include ``; they are not compiled as separate compilation units.
- **VFIL-02** File header fields: Project, Author (`<USER_NAME> (user)`), AI Flow (`VLSIT ASIC VIP Design AI Flow`), AI Flow Page, Date, Description. The human user is the author; the AI flow is recorded separately.
- **VFIL-03** Directory layout of a delivered VIP `<tag>_vip/`:

| Directory | Content |
|---|---|
| `spec/` | Pinned VIP specification, `requirements.csv`, decision log |
| `rtl_if/` | `<tag>_if.sv`, `<tag>_checker.sv` (compilable without UVM) |
| `base/` | Shared VLSIT VIP base package (`vlsit_vip_base_pkg`) |
| `uvm/` | `<tag>_vip_pkg.sv`, agent classes, `seq_lib/` |
| `qual/` | Qualification package, counterpart model, `pos`/`neg` tests, run scripts |
| `example/` | Quickstart testbench (loopback) and an integration example |
| `doc/` | `README.md`, generated traceability report, release notes |
| `filelist/` | `<tag>_vip.f` and per-simulator notes |

- **VFIL-04** Indent and align with space characters only. No tab characters in any VIP source file. Use 2 spaces per indent level.
- **VFIL-05** Files use ANSI declaration style for interfaces, modules, and tasks. Every file begins with the header and, for files with a design unit, `` `timescale 1ns/1ps `` (simulation only).
- **VFIL-06** Every generated file records the specification revision (`spec_rev`) in the header Description or in the package, so a release can be traced to a standard revision.

## 3. Naming

Use lowercase snake_case for name portions unless the table says uppercase. `<tag>` is the lowercase protocol tag from the VIP specification (`apb`, `axi`, `axil`, ...).

| Object | Convention | Example |
|---|---|---|
| VIP name / directory | `<tag>_vip` | `apb_vip` |
| Interface | `<tag>_if` | `apb_if` |
| Checker | `<tag>_checker` | `apb_checker` |
| Package | `<tag>_vip_pkg` | `apb_vip_pkg` |
| Agent, cfg, item, monitor, driver, sequencer, coverage | `<tag>_agent`, `<tag>_agent_cfg`, `<tag>_item`, `<tag>_monitor`, `<tag>_driver_host`, `<tag>_driver_device`, `<tag>_sequencer`, `<tag>_agent_cov` | `apb_agent_cfg` |
| Sequence | `<tag>_<function>_seq` | `apb_wait_state_seq` |
| Requirement ID | `VREQ-<TAG>-<NNNN>` (uppercase tag, four digits, permanent) | `VREQ-APB-0002` |
| Check ID | `<TAG>_<ERR\|REC><M\|S\|B>_<SIGNAL>_<RULE>` uppercase | `APB_ERRM_PADDR_STABLE` |
| Coverage ID | `COV_<TAG>_<NNNN>` (number of the primary requirement) | `COV_APB_0002` |
| Qualification test | `qual_<check_id_lowercase>_pos` / `_neg`; `qual_<cap_id_lowercase>_cap` with `-` written as `_` | `qual_apb_errm_paddr_stable_neg`, `qual_cap_001_cap` |
| Parameter / localparam | `PARA_<UPPERCASE>` / `LPARA_<UPPERCASE>` | `PARA_ADDR_W` |
| Enum type / member | `<name>_e` / `<TAG>_<VALUE>` uppercase | `apb_resp_e`, `APB_RESP_OKAY` |
| Class member knob | lowercase snake_case, abbreviations per VNAM-04 | `host_delay_max` |
| Virtual interface handle | `vif` | `cfg.vif` |
| Process / block label | `p_<function>` | `p_drive_setup` |

- **VNAM-01** Replicated names use zero-based indices (RTL NAM-01).
- **VNAM-02** Protocol signal names in the interface keep the protocol mnemonic in lowercase and are never shortened (RTL NAM-02, PRT-01 intent).
- **VNAM-03** Check IDs, requirement IDs, and coverage IDs are permanent. They are never renumbered or reused after a release; a withdrawn requirement keeps its ID with status `withdrawn`.
- **VNAM-04** Where a word from RTL NAM-08 appears in a class member, knob, or sequence name, write the abbreviation. Words fixed by the protocol keep their external form. `int` and `config` are reserved words and appear only inside longer names.
- **VNAM-05** Any active-low non-reset signal or knob ends in `_n` (RTL NAM-05).
- **VNAM-06** The check ID suffix letter states which role must obey the requirement: `M` (master/host drives the signals), `S` (slave/device drives), `B` (bus-level rule observed on the bus). `ERR` marks a mandatory (`shall`) requirement, `REC` a recommendation (`should`) or an option (`may`) that is checked only when the option is used.
- **VNAM-07** A UVM message ID is the check ID for protocol checks and `<TAG>_VIP_<TOPIC>` (for example `APB_VIP_CFG`) for all other messages.
- **VNAM-08** Identifiers SHOULD NOT exceed 40 characters. Check IDs and test names are exempt because they are derived from requirement content.

## 4. Interface and timing

- **VIFC-01** Interface signals are 4-state `logic`. Widths are interface parameters (`PARA_*`). The class library binds to the interface through one generated `typedef virtual` whose parameter values come from one macro per parameter (for example `APB_VIP_ADDR_W`) with a default in the generated defines file. A width change is a recompile with `+define+`, not an edit to VIP source. One compile supports one parameter set; other sets are separate variants.
- **VIFC-02** The interface lists every signal of the selected profile and its enabled options, named by the lowercase protocol mnemonic. Signals absent from the revision or profile are not declared (RTL PRT-03 intent).
- **VIFC-03** The interface has the protocol clock and reset as ports, named exactly as the protocol names them (RTL NAM-02). The reset polarity is documented in the header.
- **VIFC-04** Every timed drive and sample goes through a clocking block. The interface provides one clocking block for the host driver, one for the device driver, and one for the monitor. Skews are written explicitly; the default `#0` input skew is not used.
- **VIFC-05** Direct (non-clocking-block) assignments are limited to initialization and asynchronous reset handling, and are documented where used.
- **VIFC-06** Modports document direction per role. Modport direction checks are not relied on to detect errors (simulator support varies).
- **VIFC-07** The interface drives `'x` on payload signals while the qualifying signal (valid, select, enable) is inactive, so a consumer that samples early is exposed. Signals that must stay defined during reset are driven to their reset value.
- **VIFC-08** The interface provides no UVM dependency. It, and the checker, compile without `uvm_pkg` so they can be linted and reused in formal flows.
- **VIFC-09** A VIP MUST NOT use hierarchical references into the DUT or into another VIP instance. All access is through the virtual interface and the configuration object.

## 5. Checkers (assertions)

- **VCHK-01** Every protocol requirement with check type `SVA` has exactly one named property/assertion (or one documented group) whose label and message carry the check ID.
- **VCHK-02** A property is written once and used in the role that matches the requirement: `assert` for the role that drives the signals, `assume` for the role that receives them when the VIP is used in a formal flow, and `cover` for the desired behavior. The role selection is a parameter or a macro, not a copy of the property.
- **VCHK-03** Every property has `disable iff` on the protocol reset and no check evaluates before the history it uses exists (guard `$past` and `$rose`/`$fell` first-cycle behavior).
- **VCHK-04** A violation reports through UVM (`uvm_error` for `ERR`, `uvm_warning` for `REC`) with the message `[<check_id>] <requirement id> <spec reference>: <short text>`. Code that calls UVM is guarded by a macro so the checker still compiles for formal tools.
- **VCHK-05** Each checker is individually disable-able by check ID, with a recorded reason (waiver). `REC` checks can additionally be disabled as a group. Disabling never edits the checker source.
- **VCHK-06** An unimplemented checker stub MUST announce itself at time 0 with a message that carries its check ID. A stub never passes silently. A release MUST contain no stubs for `MUST` requirements.
- **VCHK-07** No property is vacuously true by construction. Each assertion has a paired `cover` of its antecedent so vacuity is visible in the coverage report.
- **VCHK-08** Protocol legality is checked by the checker, not by the driver. A driver may refuse to generate an illegal item only when the item is not marked for error injection.
- **VCHK-09** Data-correctness checks (end-to-end data comparison) belong to the project scoreboard, not to the VIP.
- **VCHK-10** Performance warnings (maximum wait cycles and similar) are `REC`-class checks with a knob for the limit.
- **VCHK-11** `[NEW]` When the specification gives a check expression for a requirement (Section 8.1 of the VIP specification), the checker implements exactly that expression, so the property that was reviewed at Gate 1 is the property that runs. A change to the property is a change to the specification.

## 6. UVM components

### 6.1 Subset and structure

- **VUVM-01** Use the practical UVM subset: component and object factory registration, `uvm_config_db`, analysis ports, sequence items and sequences, and phases `build`, `connect`, `run`, `report`. Avoid phase jumping and `uvm_callback`-based extension (see VP-03).
- **VUVM-02** Every component and object is factory-registered and created with `type_id::create`; `new()` is never called directly on a registered type.
- **VUVM-03** The VIP is built from the VLSIT VIP base package (`vlsit_vip_base_pkg`), so every VIP exposes the same base knobs, the same agent structure, and the same expected-error catcher.

### 6.2 Configuration (`<tag>_agent_cfg`)

- **VCFG-01** One configuration object holds every knob, including the virtual interface `vif`. The user sets one object and one interface; nothing else is required.
- **VCFG-02** The base configuration provides `is_active`, `en_monitor`, `en_cov`, `if_mode` (host or device), `has_driver`, `ok_to_end_delay_ns`, `in_reset`, `zero_delays`, and `rec_on`. `en_monitor` only gates publishing on the analysis port; the monitor itself always exists (VAGT-01). Protocol knobs extend the base.
- **VCFG-03** Default knob values yield legal, useful traffic with bounded random delays. A `zero_delays` knob sets all delays to zero for fast debug.
- **VCFG-04** The agent passes the cfg handle to its driver, monitor, sequencer, and coverage component. No separate per-component configuration classes exist.
- **VCFG-05** The agent fails with `uvm_fatal` if the configuration object or the virtual interface is missing.

### 6.3 Agent, driver, monitor, sequencer, coverage

- **VAGT-01** The monitor is always created. The sequencer and driver are created only when `is_active` is set (and `has_driver` for the driver). The driver class is selected by `if_mode`.
- **VAGT-02** The monitor's analysis port is exposed at agent level. Components communicate by TLM ports and the cfg handle; `uvm_top.find` is not used (VP-04).
- **VDRV-01** A driver drives only through the clocking block, applies reset values on reset, and tolerates reset asserted at any cycle (including mid-transaction) by abandoning the item and returning the sequencer handshake.
- **VDRV-02** The host driver generates traffic from the item and the cfg. The device driver is reactive: it answers the DUT using the cfg response knobs and a response source documented in the VIP README.
- **VDRV-03** Error injection is selected by an item field or a sequence (VP-03). The injected violation and the expected check ID are recorded in the item.
- **VMON-01** The monitor observes the interface, builds one transaction per protocol transfer, and publishes it on the analysis port. It maintains `in_reset`, supports passive use with no driver, and never drives a signal.
- **VMON-02** The monitor raises and drops an objection so the run phase does not end mid-transfer (`ok_to_end_delay_ns`).
- **VSEQ-01** A base sequence and a sequence list are provided. Each stimulus capability in the VIP specification has a named sequence. Values that vary per test are `rand` fields with constraints; no test value is hard-coded.
- **VCOV-01** Functional coverage is collected by a subscriber, gated by `en_cov`. Coverpoints cover both valid and invalid boundary bins from the boundary analysis; invalid bins are marked as such, not as ordinary bins.
- **VCOV-02** Every covergroup, coverpoint, and cover property carries its coverage ID in the name or an option comment so reports trace to requirements.

## 7. API and usability contract

- **VAPI-01** Instantiating the VIP takes three steps: create the cfg and set `vif`, create the agent, optionally start a sequence. A VIP that needs more steps does not satisfy this rule.
- **VAPI-02** The VIP ships a quickstart test that passes without DUT-specific code (host connected to device of the same VIP).
- **VAPI-03** Reset can occur at any time. The VIP recovers without restarting the simulation.
- **VAPI-04** Widths come from interface parameters bound by macros (VIFC-01); optional behavior and every runtime option come from the cfg. A recompile is required only to change a width; never to change a runtime option.
- **VAPI-05** The VIP README documents: cfg fields and legal values, required `uvm_config_db` keys and path strings, TLM ports and transaction types, factory-overridable classes, interface requirements, and clock/reset assumptions.
- **VAPI-06** The VIP records transactions for waveform debug (`begin_tr`/`end_tr` or equivalent) and every item implements `convert2string`.
- **VAPI-07** The VIP pins the specification revision it implements (`spec_rev`) and a semantic version.

## 8. Qualification of the VIP

- **VQUA-01** Treat the VIP as a design under test. Every `MUST` check has one positive trace (legal at the boundary; no error) and one negative trace (one unit beyond the boundary; exactly one error carrying the check ID).
- **VQUA-02** Every `SHOULD` check has a positive trace and a negative trace that expects exactly one warning with the check ID.
- **VQUA-03** The counterpart that exercises the VIP is independent: a behavioral model of the protocol that can emit valid and invalid items on demand. Master and slave sides of the same VIP are connected to each other only when the two sides share no checker code and were written by different engineers.
- **VQUA-04** Expected errors are declared before the negative stimulus with the expected check ID, minimum count, maximum count, and the observation window (`vlsit_vip_expect_catcher`). An unexpected error fails the test; a missing expected error fails the test.
- **VQUA-05** No test passes by ignoring or demoting every error. Demotion applies only to declared check IDs inside a declared window.
- **VQUA-06** Qualification runs on every variant listed in the VIP specification, across the seeds fixed by the qualification plan. Seeds are recorded.
- **VQUA-07** The specification analysis is reviewed by a person who did not implement the VIP. The reviewer is recorded in `requirements.csv`.
- **VQUA-08** Evidence is the simulator log and the coverage database. A check with no log evidence is `NOT_RUN`.

## 9. Documentation and release

- **VDOC-01** Release content: sources, README, quickstart example, `requirements.csv`, traceability report, qualification report, manifest with file hashes, and release notes.
- **VDOC-02** The traceability report lists, for every requirement, its check, coverage item, stimulus sequence or injection, positive trace, negative trace, and result.
- **VDOC-03** A specification change is handled by comparing `requirements.csv` between revisions (added, removed, changed IDs). Only affected items return to qualification.
- **VDOC-04** Waivers carry a rationale and a reviewer. A waived `MUST` check requires the user's explicit approval and appears in the release notes.

## 10. Prohibited constructs

| ID | Prohibited | Use instead |
|---|---|---|
| VP-01 | `$display`, `$write`, `$finish` in UVM code (outside the example top) | `uvm_info`, `uvm_warning`, `uvm_error`, `uvm_fatal` |
| VP-02 | `new()` on a factory-registered type | `type_id::create` |
| VP-03 | `uvm_callback` extension points of the VIP and phase jumping. The UVM report catcher of `vlsit_vip_expect_catcher` is qualification infrastructure, not a VIP extension point, and is permitted | cfg knobs, item fields, factory overrides, sequences |
| VP-04 | `uvm_top.find`, `uvm_root` traversal, and absolute-path `uvm_config_db` keys | TLM ports, cfg handle, relative paths |
| VP-05 | Hierarchical references into the DUT or another VIP instance | Virtual interface and cfg (VIFC-09) |
| VP-06 | Timed drive or sample outside a clocking block, or a `#` delay in a driver | Clocking block events (VIFC-04) |
| VP-07 | Reading the interface in a constructor or from a package-level variable | `uvm_config_db` in `build_phase` |
| VP-08 | `#` delay outside clock/reset generation in the example top or qualification counterpart | Clocking block, event control |
| VP-09 | Magic numbers for protocol constants in sequences and drivers | Parameters, enums, cfg knobs |
| VP-10 | An always-true or empty assertion, or a checker that reports nothing | VCHK-06, VCHK-07 |
| VP-11 | Demoting, catching, or ignoring errors globally | VQUA-04, VQUA-05 |
| VP-12 | `force`/`release` of DUT or interface signals | Driver through the clocking block |
| VP-13 | `$random`, `$urandom` seeded manually, or randomization without UVM seeding | `randomize()` through UVM so the simulator seed controls it |
| VP-14 | Static or global mutable state shared between agent instances | Per-instance members |
| VP-15 | Commented-out code and TODO markers in a release for `MUST` checks | Remove; keep history in version control |
| VP-16 | Tab characters | Spaces (VFIL-04) |

## 11. Release gates

Criteria for each maturity gate. Thresholds are defaults; the VIP specification (qualification plan) may tighten them.

| Gate | Criteria |
|---|---|
| **VIP-0 Spec locked** | VIP specification validated; requirements reviewed by a person other than the author; revision locked; no open decision blocks implementation |
| **VIP-1 Functional** | Interface and checker lint clean; UVM library compiles on the target simulator; quickstart passes; every `MUST` signal/sequence requirement has an implemented check; trace lint passes |
| **VIP-2 Qualified** | Every `MUST` check has passing positive and negative traces; counterpart regression passes; coverage model closed except waived items with a reason; no unexpected error in any log |
| **VIP-3 Release** | Multi-seed regression passes on all variants; README complete and a first-time user reproduced the quickstart; independent review recorded; version and `spec_rev` tagged; release notes written |

## 12. Comments

- **VCMT-01** Every file, class, task/function, property, and covergroup has a concise comment that states its purpose and the requirement ID it implements. Comments describe intent and assumptions, not a paraphrase of the statement. A comment line does not exceed 100 characters (RTL CMT-05).
- **VCMT-02** The three parameter comment lines of RTL PAR-02 apply to every interface and checker parameter.
- **VCMT-03** Keep comments synchronized with the implementation.
