# Implementation guide

`vip gen` creates the whole VIP tree. Everything that follows from the specification is complete. Every SVA check that has a check expression in Section 8.1 of the specification is a complete assertion. What is left are stubs marked `VIP_TODO(<id>)` that need protocol understanding. This guide explains how to complete each kind under `VLSIT_VIP_Design_Rule.md`; `vip rules <PREFIX>` prints the exact rule text.

`vip` is `python3 scripts/vip.py`. `vip worklist` is the entry point: it lists the stubs that remain with their requirement context, so you open only the regions it names.

Verification status of the material here: the checker macros, the nine APB checks, the generated interface, checker, base library, agent, item, coverage, quickstart, and the 23 qualification test classes were linted with Verilator 5.053 (UVM-free part, simulation and `VLSIT_VIP_FORMAL` modes) and type-checked with slang 12.0.0 against the Accellera UVM 2020.3.1 reference implementation (`vip check-vip`). That proves the code parses, types, and uses the UVM API correctly. It does not prove run-time behavior: no simulation was run. The monitor and driver patterns below are patterns; a simulator run of the quickstart and the qualification traces is what proves them.

## 1. Stub inventory and order

| Order | Stub | Marker | File | How to finish |
|---|---|---|---|---|
| 1 | SVA check without an expression | `VIP_TODO(<check ID>)`, `VLSIT_VIP_CHK_TODO` | `rtl_if/<tag>_checker.sv` | `vip impl-check` (Section 2) |
| 2 | CLASS check | `VIP_TODO(<check ID>)` | `uvm/<tag>_monitor.sv` | Section 3 |
| 3 | Monitor `collect_trans` | `VIP_TODO(MON-nnn)` | `uvm/<tag>_monitor.sv` | Section 3 |
| 4 | Host and device drivers | `VIP_TODO(<tag>_driver_host)`, `..._device` | `uvm/` | Section 4 |
| 5 | Sequences | `VIP_TODO(CAP-nnn)` or `VIP_TODO(SEQ-nnn)` | `uvm/seq_lib/` | Section 5 |
| 6 | Covergroup sampling | `VIP_TODO(<COV ID>)` | `uvm/<tag>_agent_cov.sv` | Section 6 |
| 7 | Counterpart stimulus tasks | `VIP_TODO(<test name>)` | `qual/<tag>_counterpart.sv` | Qualifier stage |

After each group: `vip check-vip` then `vip lint impl`.

## 2. SVA checks

The preferred path is to put the property in the specification (Section 8.1) so it is reviewed at Gate 1, then regenerate. For a stub that remains, complete it from the command line:

```text
vip impl-check --id APB_ERRM_PADDR_STABLE --op NEXT --ante "psel && !(penable && pready)" --cons "!psel OR \$stable(paddr)" --msg "paddr changed before the transfer completed"
```

The tool checks the identifiers against the signals, replaces the stub with the complete macro call, keeps the requirement and coverage-ID comments, removes the markers, and prints the row to add to Section 8.1 of the specification so the specification and the code stay in step (VCHK-11).

Rules for a property (look up `vip rules VCHK`):

1. State the requirement and nothing else (orthogonality): a single violation fires a single check. Guard with `!psel OR ...` when the select-hold rule is a separate row.
2. Guard first-cycle history: `$past`, `$rose`, `$fell` need a previous cycle; the reset disable covers the cycles in reset.
3. Single-cycle boolean expressions only: `|->` (operator SAME) or `|=>` (operator NEXT); write `OR` for `||` in the specification.
4. The antecedent is the condition under which the property does real work; the paired cover shows the stimulus reached it (VCHK-07).

The generated `VLSIT_VIP_CHK_ERR` or `VLSIT_VIP_CHK_REC` call adds the clock, the reset and per-check enable disable, the UVM report, and the paired `cover`. In `VLSIT_VIP_FORMAL` mode the checks of the role that is not the DUT become assumptions.

Lint passing means the property parses and is consistent. Whether it is right is shown by the positive and negative traces of the qualification stage.

## 3. Monitor and class checks

`track_reset` is generated. Complete `collect_trans`: observe through `cfg.vif.mon_cb`, build one item per transfer, publish it. Pattern for a two-phase request and response protocol:

```systemverilog
virtual task collect_trans();
  <tag>_item item;
  bit        in_transfer;
  forever begin
    @(cfg.vif.mon_cb);
    if (cfg.in_reset) begin
      if (in_transfer) begin
        transfer_ended();          // reset abandoned the transfer: release the objection
        in_transfer = 1'b0;
      end
      continue;
    end
    if (!in_transfer && <start condition on cfg.vif.mon_cb.*>) begin
      item = <tag>_item::type_id::create("item");
      item.<field> = cfg.vif.mon_cb.<signal>;      // capture request fields
      transfer_started();
      in_transfer = 1'b1;
    end else if (in_transfer && <completion condition>) begin
      item.<field> = cfg.vif.mon_cb.<signal>;      // capture response fields
      check_<id>(item);                            // class checks, if any
      publish(item);
      transfer_ended();
      in_transfer = 1'b0;
    end
  end
endtask
```

A class check reports with `uvm_error` (ERR) or `uvm_warning` (REC) using the check ID as the message ID, so the expected-error catcher can match it. A monitor never drives a signal.

## 4. Drivers

Drive only through the clocking block (`host_cb` or `device_cb`, VIFC-04). `reset_signals` is generated. Complete `get_and_drive`:

```systemverilog
virtual task get_and_drive();
  seq_item_port.get_next_item(req);
  item_in_flight = 1'b1;
  repeat (<idle cycles from req or the cfg knobs, zero when cfg.zero_delays>) @(cfg.vif.host_cb);
  cfg.vif.host_cb.<signal> <= req.<field>;       // present the request
  @(cfg.vif.host_cb);
  // ... remaining phases, one clocking-block event per cycle ...
  seq_item_port.item_done();
  item_in_flight = 1'b0;
endtask
```

1. Set `item_in_flight` right after `get_next_item` and clear it right after `item_done`, so reset can return the handshake (VDRV-01).
2. Randomize delays inside the knob range; `cfg.zero_delays` forces zero.
3. Error injection reads the item field named in the specification and produces exactly the violation of the injection row (VDRV-03). The driver does not decide legality (VCHK-08).
4. The device driver is reactive: it observes the request, decides the response from the cfg knobs, and may take an override item with `seq_item_port.try_next_item`.
5. No `#` delays, no `$display`, no `force` (`vip rules VP`).

## 5. Sequences and 6. Covergroups

Each capability sequence constrains the items to exercise its capability using item fields and cfg knobs; no hard-coded protocol constants (VP-09). Wire each generated covergroup in `write()`: `cg_<cov id lowercase>.sample(<value>)` for bounds, `.sample(<condition>)` for scenarios. Invalid bins are hit only by negative traces. Remove the `VIP_TODO` comments when done.

## 7. Check the result

```text
vip check-vip      # Verilator lint (simulation and formal), slang UVM type-check of quickstart and qualification environment
vip lint impl      # traceability, stubs, hygiene
```

`vip check-vip` writes full tool output to a log and prints a few lines. VIP-1 holds when it passes, every MUST signal and sequence check is implemented, and `vip lint impl` has no error. A simulator compile and the quickstart run remain `NOT_RUN` until a UVM simulator runs them.

## 8. Base library API

| Class | Use |
|---|---|
| `vlsit_vip_agent_cfg` | `is_active`, `en_monitor` (publish gate), `en_cov`, `if_mode`, `has_driver`, `ok_to_end_delay_ns`, `in_reset`, `zero_delays`, `rec_on`, `disable_check(id, reason)` |
| `vlsit_vip_agent_base` | Builds the monitor, optional coverage, and the sequencer and one driver when active; `apply_check_controls` hook |
| `vlsit_vip_driver_base` | `reset_signals`, `get_and_drive`, `item_in_flight`; reset handling in `run_phase` |
| `vlsit_vip_monitor_base` | `track_reset`, `collect_trans`, `publish`, `transfer_started`, `transfer_ended` |
| `vlsit_vip_sequencer_base`, `vlsit_vip_cov_base` | cfg handle; `write` for coverage |
| `vlsit_vip_expect_catcher` | `get`, `clear`, `expect_error(id, min, max)`, `start_window`, `end_window`, `final_report` |
| `vlsit_vip_qual_test_base` | Resets the catcher, reads `+VLSIT_SEED`, rejects vacuous traces, prints the `VLSIT_VIP_QUAL_RESULT` line |

Do not edit `base/` of a generated VIP. Improve the base library in the skill's `assets/base`, so every VIP benefits, and regenerate.
