/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Base driver. Handles reset at any time (VDRV-01): the in-flight item is
 *                abandoned, the sequencer handshake is returned, signals return to reset values.
 */
// SPDX-License-Identifier: Apache-2.0

class vlsit_vip_driver_base #(type ITEM_T = uvm_sequence_item,
                              type CFG_T  = vlsit_vip_agent_cfg) extends uvm_driver #(ITEM_T);

  CFG_T cfg;

  // Set by get_and_drive between get_next_item and item_done so reset can return the handshake.
  protected bit item_in_flight;

  `uvm_component_param_utils(vlsit_vip_driver_base #(ITEM_T, CFG_T))

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // Drives every signal of this role to its reset value. Implemented by the protocol driver.
  virtual task reset_signals();
  endtask

  // Pulls one item from the sequencer, drives it, and returns the handshake. Implemented by
  // the protocol driver. It sets item_in_flight after get_next_item and clears it after item_done.
  virtual task get_and_drive();
  endtask

  // Blocks until the protocol reset is asserted; the monitor maintains cfg.in_reset.
  virtual task wait_reset_assert();
    wait (cfg.in_reset == 1'b1);
  endtask

  // Blocks until the protocol reset is released.
  virtual task wait_reset_release();
    wait (cfg.in_reset == 1'b0);
  endtask

  virtual task run_phase(uvm_phase phase);
    forever begin
      reset_signals();
      wait_reset_release();
      fork
        begin : p_drive_loop
          forever begin
            get_and_drive();
          end
        end
        begin : p_reset_watch
          wait_reset_assert();
        end
      join_any
      disable fork;
      if (item_in_flight) begin
        // Reset interrupted a transfer: abandon the item and release the sequencer.
        seq_item_port.item_done();
        item_in_flight = 1'b0;
        `uvm_info("VLSIT_VIP_DRV", "reset abandoned the transfer in flight", UVM_MEDIUM)
      end
    end
  endtask

endclass
