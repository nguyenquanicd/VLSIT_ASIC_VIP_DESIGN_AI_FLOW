/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Base monitor. Publishes one transaction per protocol transfer, tracks the
 *                protocol reset in cfg.in_reset, and keeps the run phase alive during a
 *                transfer (VMON-01, VMON-02). Never drives a signal.
 */
// SPDX-License-Identifier: Apache-2.0

class vlsit_vip_monitor_base #(type ITEM_T = uvm_sequence_item,
                               type CFG_T  = vlsit_vip_agent_cfg) extends uvm_monitor;

  CFG_T cfg;

  // Run phase handle used to raise and drop objections around a transfer.
  protected uvm_phase m_run_phase;

  uvm_analysis_port #(ITEM_T) ap;

  `uvm_component_param_utils(vlsit_vip_monitor_base #(ITEM_T, CFG_T))

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    ap = new("ap", this);
  endfunction

  // Maintains cfg.in_reset from the protocol reset. Implemented by the protocol monitor.
  virtual task track_reset();
  endtask

  // Observes the interface, builds one item per transfer, calls transfer_started and
  // transfer_ended around it, and calls publish. Implemented by the protocol monitor.
  virtual task collect_trans();
  endtask

  // Publishes a completed transaction when cfg.en_monitor is set.
  function void publish(ITEM_T item);
    if (cfg.en_monitor) begin
      ap.write(item);
    end
  endfunction

  // Call when a transfer begins so the simulation does not end mid-transfer.
  function void transfer_started();
    if (m_run_phase != null) begin
      m_run_phase.raise_objection(this, "transfer in flight");
    end
  endfunction

  // Call when a transfer completes. The objection is dropped after ok_to_end_delay_ns.
  function void transfer_ended();
    if (m_run_phase != null) begin
      fork
        begin
          #(cfg.ok_to_end_delay_ns * 1ns);
          m_run_phase.drop_objection(this, "transfer done");
        end
      join_none
    end
  endfunction

  virtual task run_phase(uvm_phase phase);
    m_run_phase = phase;
    fork
      track_reset();
      collect_trans();
    join
  endtask

endclass
