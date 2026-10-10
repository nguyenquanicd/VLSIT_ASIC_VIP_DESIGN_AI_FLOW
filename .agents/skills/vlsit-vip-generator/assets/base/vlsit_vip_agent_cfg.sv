/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Base configuration object of every VLSIT VIP agent (VCFG-01, VCFG-02).
 */
// SPDX-License-Identifier: Apache-2.0

class vlsit_vip_agent_cfg extends uvm_object;

  // True when the agent has a sequencer and a driver; false makes it a passive monitor.
  bit is_active = 1'b1;

  // True when the monitor publishes transactions on its analysis port. The monitor itself
  // always exists because it tracks the protocol reset (VAGT-01).
  bit en_monitor = 1'b1;

  // True when the agent creates its functional coverage subscriber.
  bit en_cov = 1'b1;

  // Role of the agent on the bus: host starts transfers, device answers them.
  vlsit_vip_if_mode_e if_mode = VIP_HOST;

  // True when the agent has its own driver attached to the sequencer.
  bit has_driver = 1'b1;

  // Time in ns that the monitor keeps its objection after a transfer ends (VMON-02).
  int unsigned ok_to_end_delay_ns = 1000;

  // True while the protocol reset is asserted. The monitor maintains it (VMON-01).
  bit in_reset;

  // True sets every random delay to zero for fast debug (VCFG-03).
  bit zero_delays;

  // False disables every recommendation (REC) check as a group (VCHK-05).
  bit rec_on = 1'b1;

  // Specification revision implemented by the VIP; set by the generated protocol cfg.
  string spec_rev;

  protected bit    m_chk_disabled[string];
  protected string m_chk_reason[string];

  `uvm_object_utils(vlsit_vip_agent_cfg)

  function new(string name = "vlsit_vip_agent_cfg");
    super.new(name);
  endfunction

  // Waives one check by ID. A waiver without a reason is a fatal error (VCHK-05, VDOC-04).
  function void disable_check(string chk_id, string reason);
    if (reason == "") begin
      `uvm_fatal("VLSIT_VIP_CFG", $sformatf("waiver of check %s needs a reason", chk_id))
    end
    m_chk_disabled[chk_id] = 1'b1;
    m_chk_reason[chk_id]   = reason;
  endfunction

  function bit is_check_disabled(string chk_id);
    return m_chk_disabled.exists(chk_id);
  endfunction

  function string waiver_reason(string chk_id);
    return m_chk_reason.exists(chk_id) ? m_chk_reason[chk_id] : "";
  endfunction

  // Returns the IDs of all waived checks.
  function void get_disabled_checks(ref string ids[$]);
    foreach (m_chk_disabled[k]) begin
      ids.push_back(k);
    end
  endfunction

  virtual function string convert2string();
    return $sformatf("is_active=%0b en_monitor=%0b en_cov=%0b if_mode=%s has_driver=%0b zero_delays=%0b rec_on=%0b spec_rev=%s",
                     is_active, en_monitor, en_cov, if_mode.name(), has_driver, zero_delays, rec_on, spec_rev);
  endfunction

endclass
