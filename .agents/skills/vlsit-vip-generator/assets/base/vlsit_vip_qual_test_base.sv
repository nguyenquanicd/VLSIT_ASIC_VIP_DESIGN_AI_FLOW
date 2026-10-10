/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Base class of every qualification test. Resets the expected-error catcher,
 *                prints the VLSIT_VIP_QUAL_RESULT line, and rejects vacuous traces: a negative
 *                trace must declare an expected error and a positive trace must declare none.
 */
// SPDX-License-Identifier: Apache-2.0

class vlsit_vip_qual_test_base extends uvm_test;

  protected vlsit_vip_expect_catcher m_catcher;

  // Seed of the run, taken from +VLSIT_SEED=<n> (set by run_qual.py); 0 when absent.
  protected int unsigned m_seed;

  `uvm_component_utils(vlsit_vip_qual_test_base)

  function new(string name = "vlsit_vip_qual_test_base", uvm_component parent = null);
    super.new(name, parent);
  endfunction

  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    m_catcher = vlsit_vip_expect_catcher::get();
    m_catcher.clear();
    if (!$value$plusargs("VLSIT_SEED=%d", m_seed)) begin
      m_seed = 0;
    end
  endfunction

  // Returns true when the test name ends with the given suffix.
  protected function bit name_ends_with(string suffix);
    string n = get_type_name();
    int    nl = n.len();
    int    sl = suffix.len();
    return (nl >= sl) && (n.substr(nl - sl, nl - 1) == suffix);
  endfunction

  virtual function void report_phase(uvm_phase phase);
    super.report_phase(phase);
    if (name_ends_with("_neg") && m_catcher.num_entries() == 0) begin
      `uvm_error("VLSIT_VIP_QUAL", "negative trace declared no expected error (vacuous trace)")
    end
    if (name_ends_with("_pos") && m_catcher.num_entries() != 0) begin
      `uvm_error("VLSIT_VIP_QUAL", "positive trace declared an expected error")
    end
    m_catcher.final_report(get_type_name(), m_seed);
  endfunction

endclass
