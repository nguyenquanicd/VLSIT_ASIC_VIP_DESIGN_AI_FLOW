# Architecture guide

The architect fixes the shape of the VIP before any code exists, so every VIP has the same structure and the same user-facing API (VUVM-03, VAPI-01). The default architecture is the one below; a deviation needs a decision row in the specification.

## 1. Default architecture

```text
<tag>_if            interface: signals, clocking blocks host_cb / device_cb / mon_cb, modports, chk_en
  <tag>_checker     embedded UVM-free checker interface: assert / assume / cover per check, enable vector
<tag>_chk_pkg       check enable indices, REC mask, index lookup
<tag>_vip_pkg       typedef virtual <tag>_if (macros bind widths), classes below
  <tag>_agent_cfg   extends vlsit_vip_agent_cfg: vif and protocol knobs
  <tag>_item        transaction item, injection enum
  <tag>_sequencer   extends vlsit_vip_sequencer_base
  <tag>_monitor     extends vlsit_vip_monitor_base: tracks reset, publishes items
  <tag>_driver_host / <tag>_driver_device   extend vlsit_vip_driver_base
  <tag>_agent_cov   extends vlsit_vip_cov_base: covergroups
  <tag>_agent       extends vlsit_vip_agent_base: waivers and REC switch applied here
  seq_lib/          base sequence and one sequence per capability
vlsit_vip_base_pkg  shared base classes and the expected-error catcher
```

Roles map as follows: `ROLE` letter `M` becomes `if_mode = VIP_HOST`, `S` becomes `VIP_DEVICE`, `B` becomes a passive agent (`is_active = 0`).

## 2. Decisions to make and record

| Decision | Default | Ask the user when |
|---|---|---|
| Profile to build first | The first profile in the specification | Several profiles exist. Each profile is a separate build (artifact contract, Section 1) |
| Build, reuse, or extend | As recorded in Section 1.2 | An existing VIP covers more than half of the requirements |
| UVM version | IEEE 1800.2-2020 | The project simulator supports only UVM 1.2. The base library uses only the common subset (VUVM-01) |
| Width binding | Parameter macros with defaults (VIFC-01) | A testbench needs two widths at once; this needs a second compile unit, and is rare |
| Checker container | `interface` embedded in `<tag>_if` | The project wants the checker bound to a DUT; the same checker interface can be bound |
| Formal use of checkers | Not used | The project plans formal; then `PARA_DUT_ROLE` and the `VLSIT_VIP_FORMAL` macro apply |
| Base library | `vlsit_vip_base_pkg` from the generator skill | The project already has a base library; map the same API or extend |
| Variants | From the specification | Variants imply different profiles; each profile needs its own build and evidence |

## 3. Derive and review the configuration

```text
vip set profile=<PROF-nn> version=0.1.0
vip config        # derives the file; run again after an edit to check it
```

The configuration filters signals, checks, capabilities, injections, and tests to the selected profile. Review it:

1. The signal list, widths, drivers, and reset values equal Section 4.3 for that profile.
2. Every parameter has a macro name `<TAG>_VIP_<NAME>` and a default.
3. Check indices run 0 to N-1 in order, and `is_rec` is true exactly for `REC` checks.
4. Every MUST check has an injection; every capability has a sequence.
5. Item fields cover every field a driver sets and a monitor reads.

Edit `vip_config.json` only for architecture choices the specification does not state (for example item field order). Re-run `--check` after an edit. A change that alters a requirement, a check, or a trace belongs in the specification, not here.

## 4. Write `vip_arch.md`

Use `references/vip_arch_template.md`. It must let a reviewer judge the design without opening the code: structure, interface and clocking, check inventory, API contract fulfillment (UC-01 to UC-13), usability, qualification structure, and risks.

## 5. Gate 2

Present `vplan.md`, `vip_config.json`, and `vip_arch.md` together. The prompt names the exact versions, files, profile, and the checks, tests, and variants in scope. Approval covers those items only.
