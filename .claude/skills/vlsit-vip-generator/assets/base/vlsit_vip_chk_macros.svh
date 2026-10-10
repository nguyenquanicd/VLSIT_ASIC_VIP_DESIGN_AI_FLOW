/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Checker macros shared by every generated VIP checker. UVM-free (VIFC-08).
 *                Use `define VLSIT_VIP_UVM to report through UVM, `define VLSIT_VIP_FORMAL
 *                to remove reporting and to map the checks of the non-DUT role to assume.
 */
// SPDX-License-Identifier: Apache-2.0
`ifndef VLSIT_VIP_CHK_MACROS_SVH
`define VLSIT_VIP_CHK_MACROS_SVH

// Reporting actions (VCHK-04). UVM calls are guarded so formal tools never see them.
`ifdef VLSIT_VIP_UVM
  `define VLSIT_VIP_REPORT_ERR(ID, MSG) \
    uvm_pkg::uvm_report_error(ID, MSG, uvm_pkg::UVM_NONE, `__FILE__, `__LINE__)
  `define VLSIT_VIP_REPORT_WARN(ID, MSG) \
    uvm_pkg::uvm_report_warning(ID, MSG, uvm_pkg::UVM_NONE, `__FILE__, `__LINE__)
`else
  `define VLSIT_VIP_REPORT_ERR(ID, MSG) $error("[%s] %s", ID, MSG)
  `define VLSIT_VIP_REPORT_WARN(ID, MSG) $warning("[%s] %s", ID, MSG)
`endif

// Unimplemented check stub (VCHK-06): announces itself at time 0 and at the end of simulation.
// Remove the stub and the VIP_TODO marker comment only when the check is implemented.
`ifdef VLSIT_VIP_FORMAL
  `define VLSIT_VIP_CHK_TODO(ID, REQ)
`else
  `define VLSIT_VIP_CHK_TODO(ID, REQ) \
    initial begin : g_todo_start_``ID \
      `VLSIT_VIP_REPORT_WARN(`"ID`", {REQ, " VIP_TODO check is not implemented"}); \
    end \
    final begin : g_todo_end_``ID \
      `VLSIT_VIP_REPORT_WARN(`"ID`", {REQ, " VIP_TODO check is not implemented"}); \
    end
`endif

// ERR / REC check macros. Arguments:
//   ID    check ID without quotes, also the suffix of the enable index CHK_IDX_<ID>
//   ROLE  M, S, or B: the role that must obey the requirement (selects assert or assume in formal)
//   REQ   requirement ID string, MSG message string (spec reference and short text)
//   PROP  property expression without clock and disable condition
//   ANTE  antecedent expression for the paired cover (VCHK-07)
// The enclosing checker defines w_clk, w_rst_active, i_chk_en, and LPARA_ASSUME_M/S/B.
`ifdef VLSIT_VIP_FORMAL
  `define VLSIT_VIP_CHK_ERR(ID, ROLE, REQ, MSG, PROP, ANTE) \
    if (LPARA_ASSUME_``ROLE) begin : g_chk_``ID \
      m_``ID : assume property (@(posedge w_clk) disable iff (w_rst_active || !i_chk_en[CHK_IDX_``ID]) PROP); \
    end else begin : g_chk_``ID``_a \
      a_``ID : assert property (@(posedge w_clk) disable iff (w_rst_active || !i_chk_en[CHK_IDX_``ID]) PROP); \
    end \
    c_``ID : cover property (@(posedge w_clk) disable iff (w_rst_active) ANTE);
  `define VLSIT_VIP_CHK_REC(ID, ROLE, REQ, MSG, PROP, ANTE) \
    `VLSIT_VIP_CHK_ERR(ID, ROLE, REQ, MSG, PROP, ANTE)
`else
  `define VLSIT_VIP_CHK_ERR(ID, ROLE, REQ, MSG, PROP, ANTE) \
    a_``ID : assert property (@(posedge w_clk) disable iff (w_rst_active || !i_chk_en[CHK_IDX_``ID]) PROP) \
      else `VLSIT_VIP_REPORT_ERR(`"ID`", {REQ, " ", MSG}); \
    c_``ID : cover property (@(posedge w_clk) disable iff (w_rst_active) ANTE);
  `define VLSIT_VIP_CHK_REC(ID, ROLE, REQ, MSG, PROP, ANTE) \
    a_``ID : assert property (@(posedge w_clk) disable iff (w_rst_active || !i_chk_en[CHK_IDX_``ID]) PROP) \
      else `VLSIT_VIP_REPORT_WARN(`"ID`", {REQ, " ", MSG}); \
    c_``ID : cover property (@(posedge w_clk) disable iff (w_rst_active) ANTE);
`endif

`endif
