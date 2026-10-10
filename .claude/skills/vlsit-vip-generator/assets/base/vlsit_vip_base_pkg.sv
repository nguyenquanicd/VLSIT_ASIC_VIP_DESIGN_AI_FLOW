/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : VLSIT VIP base package: base configuration, agent, driver, monitor,
 *                sequencer, coverage, expected-error catcher, and qualification test base.
 *                Compile after uvm_pkg. Protocol VIPs extend these classes (VUVM-03).
 */
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps

`include "uvm_macros.svh"

package vlsit_vip_base_pkg;

  import uvm_pkg::*;

  `include "vlsit_vip_defs.svh"
  `include "vlsit_vip_agent_cfg.sv"
  `include "vlsit_vip_driver_base.sv"
  `include "vlsit_vip_monitor_base.sv"
  `include "vlsit_vip_sequencer_base.sv"
  `include "vlsit_vip_cov_base.sv"
  `include "vlsit_vip_agent_base.sv"
  `include "vlsit_vip_expect_catcher.sv"
  `include "vlsit_vip_qual_test_base.sv"

endpackage
