/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Base sequencer; holds the agent configuration so sequences can read the knobs.
 */
// SPDX-License-Identifier: Apache-2.0

class vlsit_vip_sequencer_base #(type ITEM_T = uvm_sequence_item,
                                 type CFG_T  = vlsit_vip_agent_cfg) extends uvm_sequencer #(ITEM_T);

  CFG_T cfg;

  `uvm_component_param_utils(vlsit_vip_sequencer_base #(ITEM_T, CFG_T))

  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction

endclass
