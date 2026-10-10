/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Base agent (VAGT-01). The monitor is always created. The sequencer and the
 *                driver exist only when cfg.is_active (and cfg.has_driver); if_mode selects the
 *                host or the device driver. Coverage is a subscriber on the monitor port.
 */
// SPDX-License-Identifier: Apache-2.0

class vlsit_vip_agent_base #(type CFG_T      = vlsit_vip_agent_cfg,
                             type ITEM_T     = uvm_sequence_item,
                             type DRV_HOST_T = uvm_driver #(ITEM_T),
                             type DRV_DEV_T  = DRV_HOST_T,
                             type SQR_T      = uvm_sequencer #(ITEM_T),
                             type MON_T      = uvm_monitor,
                             type COV_T      = uvm_component) extends uvm_agent;

  CFG_T       cfg;
  COV_T       cov;
  DRV_HOST_T  drv_host;
  DRV_DEV_T   drv_dev;
  SQR_T       sequencer;
  MON_T       monitor;

  // Analysis port of the monitor, exposed at agent level (VAGT-02).
  uvm_analysis_port #(ITEM_T) ap;

  `uvm_component_param_utils(vlsit_vip_agent_base #(CFG_T, ITEM_T, DRV_HOST_T, DRV_DEV_T, SQR_T, MON_T, COV_T))

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // Applies the waivers and the REC group switch of the cfg to the checker enable vector.
  // The generated protocol agent overrides it because it knows the interface type.
  virtual function void apply_check_controls();
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (!uvm_config_db #(CFG_T)::get(this, "", "cfg", cfg)) begin
      `uvm_fatal("VLSIT_VIP_AGT", "failed to get the agent cfg from uvm_config_db with key cfg")
    end
    `uvm_info("VLSIT_VIP_AGT", {"cfg: ", cfg.convert2string()}, UVM_HIGH)

    monitor = MON_T::type_id::create("monitor", this);
    monitor.cfg = cfg;
    if (cfg.en_cov) begin
      cov = COV_T::type_id::create("cov", this);
      cov.cfg = cfg;
    end
    if (cfg.is_active) begin
      sequencer = SQR_T::type_id::create("sequencer", this);
      sequencer.cfg = cfg;
      if (cfg.has_driver) begin
        if (cfg.if_mode == VIP_HOST) begin
          drv_host = DRV_HOST_T::type_id::create("driver", this);
          drv_host.cfg = cfg;
        end else begin
          drv_dev = DRV_DEV_T::type_id::create("driver", this);
          drv_dev.cfg = cfg;
        end
      end
    end
  endfunction

  virtual function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    ap = monitor.ap;
    if (cfg.en_cov) begin
      monitor.ap.connect(cov.analysis_export);
    end
    if (cfg.is_active && cfg.has_driver) begin
      if (cfg.if_mode == VIP_HOST) begin
        drv_host.seq_item_port.connect(sequencer.seq_item_export);
      end else begin
        drv_dev.seq_item_port.connect(sequencer.seq_item_export);
      end
    end
  endfunction

  virtual function void start_of_simulation_phase(uvm_phase phase);
    super.start_of_simulation_phase(phase);
    apply_check_controls();
  endfunction

  // Prints every waiver with its reason so a release review sees them (VDOC-04).
  virtual function void report_phase(uvm_phase phase);
    string ids[$];
    super.report_phase(phase);
    cfg.get_disabled_checks(ids);
    foreach (ids[i]) begin
      `uvm_info("VLSIT_VIP_AGT", $sformatf("check %s is waived: %s", ids[i], cfg.waiver_reason(ids[i])), UVM_LOW)
    end
  endfunction

endclass
