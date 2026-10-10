/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Base functional-coverage subscriber, gated by cfg.en_cov (VCOV-01).
 */
// SPDX-License-Identifier: Apache-2.0

class vlsit_vip_cov_base #(type ITEM_T = uvm_sequence_item,
                           type CFG_T  = vlsit_vip_agent_cfg) extends uvm_subscriber #(ITEM_T);

  CFG_T cfg;

  `uvm_component_param_utils(vlsit_vip_cov_base #(ITEM_T, CFG_T))

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

  // The protocol coverage class overrides write to sample its covergroups.
  virtual function void write(ITEM_T t);
  endfunction

endclass
