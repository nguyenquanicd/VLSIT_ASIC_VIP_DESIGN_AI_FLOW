/*
 * Project      : VLSIT ASIC VIP Design AI Flow
 * Author       : <USER_NAME> (user)
 * AI Flow      : VLSIT ASIC VIP Design AI Flow
 * AI Flow Page : https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW
 * Date         : 2026-10-10
 * Description  : Expected-error catcher for VIP qualification (VQUA-04, VQUA-05). UVM has no
 *                notion of an expected error. A negative trace declares the check ID, the
 *                minimum and maximum count, and the observation window. Inside the window a
 *                matching error is demoted to a warning; every other error stays an error.
 *                The demotion applies only to declared IDs in a declared window (VP-11).
 */
// SPDX-License-Identifier: Apache-2.0

// One declared expectation.
class vlsit_vip_expect_entry;
  string       id;
  int unsigned min_cnt;
  int unsigned max_cnt;
  int unsigned seen;

  function new(string id, int unsigned min_cnt, int unsigned max_cnt);
    this.id      = id;
    this.min_cnt = min_cnt;
    this.max_cnt = max_cnt;
    this.seen    = 0;
  endfunction
endclass

class vlsit_vip_expect_catcher extends uvm_report_catcher;

  protected static vlsit_vip_expect_catcher m_inst;

  protected vlsit_vip_expect_entry m_entries[$];
  protected bit          m_window_open;
  protected int unsigned m_unexpected;
  protected int unsigned m_missing;
  protected int unsigned m_overflow;
  protected int unsigned m_expected_seen;

  function new(string name = "vlsit_vip_expect_catcher");
    super.new(name);
  endfunction

  // Returns the single catcher and registers it with the report system on first use.
  static function vlsit_vip_expect_catcher get();
    if (m_inst == null) begin
      m_inst = new("vlsit_vip_expect_catcher");
      uvm_report_cb::add(null, m_inst);
    end
    return m_inst;
  endfunction

  // Forgets every declaration and counter; call at the start of a test.
  function void clear();
    m_entries.delete();
    m_window_open   = 1'b0;
    m_unexpected    = 0;
    m_missing       = 0;
    m_overflow      = 0;
    m_expected_seen = 0;
  endfunction

  function int unsigned num_entries();
    return m_entries.size();
  endfunction

  // Declares that the check ID must fire at least min_cnt and at most max_cnt times in the window.
  function void expect_error(string id, int unsigned min_cnt = 1, int unsigned max_cnt = 1);
    vlsit_vip_expect_entry e = new(id, min_cnt, max_cnt);
    m_entries.push_back(e);
  endfunction

  // Opens the observation window and zeroes the per-entry counters.
  function void start_window();
    m_window_open = 1'b1;
    foreach (m_entries[i]) begin
      m_entries[i].seen = 0;
    end
  endfunction

  // Closes the window, prints one summary line per entry, and reports a missing expected error.
  function void end_window();
    m_window_open = 1'b0;
    foreach (m_entries[i]) begin
      string status = "OK";
      if (m_entries[i].seen < m_entries[i].min_cnt) begin
        status = "FAIL";
        m_missing++;
        uvm_pkg::uvm_report_error("VLSIT_VIP_CATCHER",
          $sformatf("expected error %s was seen %0d time(s), minimum is %0d",
                    m_entries[i].id, m_entries[i].seen, m_entries[i].min_cnt),
          uvm_pkg::UVM_NONE, `__FILE__, `__LINE__);
      end else if (m_entries[i].seen > m_entries[i].max_cnt) begin
        status = "FAIL";
      end
      uvm_pkg::uvm_report_info("VLSIT_VIP_CATCHER",
        $sformatf("VLSIT_VIP_CATCHER id=%s min=%0d max=%0d seen=%0d status=%s",
                  m_entries[i].id, m_entries[i].min_cnt, m_entries[i].max_cnt,
                  m_entries[i].seen, status),
        uvm_pkg::UVM_NONE, `__FILE__, `__LINE__);
    end
  endfunction

  // Prints the machine-readable result line parsed by collect_qual_results.py.
  function void final_report(string test_name, int unsigned seed);
    uvm_report_server svr = uvm_report_server::get_server();
    int unsigned errs = svr.get_severity_count(UVM_ERROR) + svr.get_severity_count(UVM_FATAL);
    string status = (errs == 0 && m_missing == 0 && m_overflow == 0) ? "PASS" : "FAIL";
    uvm_pkg::uvm_report_info("VLSIT_VIP_CATCHER",
      $sformatf("VLSIT_VIP_QUAL_RESULT test=%s seed=%0d status=%s expected=%0d unexpected=%0d missing=%0d",
                test_name, seed, status, m_expected_seen, m_unexpected, m_missing),
      uvm_pkg::UVM_NONE, `__FILE__, `__LINE__);
  endfunction

  // Called for every report. Only errors and warnings are considered.
  virtual function action_e catch();
    uvm_severity sev = get_severity();
    string       id  = get_id();
    if (id == "VLSIT_VIP_CATCHER") begin
      return THROW;
    end
    if (sev != UVM_ERROR && sev != UVM_FATAL && sev != UVM_WARNING) begin
      return THROW;
    end
    if (m_window_open) begin
      foreach (m_entries[i]) begin
        if (m_entries[i].id == id) begin
          m_entries[i].seen++;
          m_expected_seen++;
          if (m_entries[i].seen > m_entries[i].max_cnt) begin
            // Above the declared maximum: leave it as reported, the test fails.
            m_overflow++;
            return THROW;
          end
          if (sev == UVM_ERROR) begin
            set_severity(UVM_WARNING);
          end
          return THROW;
        end
      end
    end
    if (sev == UVM_ERROR || sev == UVM_FATAL) begin
      m_unexpected++;
    end
    return THROW;
  endfunction

endclass
