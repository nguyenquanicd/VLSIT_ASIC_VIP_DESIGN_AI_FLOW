# Qualification guide

Qualification treats the VIP as a design under test (VQUA-01). The goal is evidence that every protocol check fires for a violation and stays silent for legal traffic, and that the VIP can generate and observe every capability. Rule IDs refer to `VLSIT_VIP_Design_Rule.md`. The method follows Cerisier et al. (DVCon), Venkataramanan and Kumari (DVCon), and the process in `docs/VLSIT_VIP_Build_Process.md`.

## 1. Evidence rules

1. An entry is `PASS` only from logs: a `VLSIT_VIP_QUAL_RESULT ... status=PASS` line for the test, a UVM summary with zero `UVM_ERROR` and `UVM_FATAL`, and exit code 0, for every required seed on every variant (VQUA-06, VQUA-08).
2. A missing log is `NOT_RUN`. A log without a result line is `FAIL`. Lint, compile, and coverage evidence are separate items with their own logs.
3. Never edit an expected result, a log, or an evidence entry to make a test pass. Fix the VIP, the trace, or the specification, record why, and re-run.
4. User acceptance does not change an evidence status.

## 2. The independent counterpart (VQUA-03)

The counterpart is a small behavioral model of the protocol that can emit valid and invalid traffic with cycle-level control. It lives in `qual/<tag>_counterpart.sv` and is written from the specification, not from the VIP checkers. It shares no checker code with the VIP.

- The counterpart plays the role that produces the violation (host for `M` checks, device for `S` checks) and the VIP observes with its monitor and embedded checker.
- To qualify the VIP's own driver and responder, run the VIP in active mode against the counterpart of the opposite role (`configure_vip` hook of the qualification base test).
- Connecting the VIP host to the VIP device is only a smoke test. It is not qualification unless the two sides were written by different engineers and share no checker code.
- Each injection of the specification becomes one counterpart task that produces exactly one violation.

## 3. Trace patterns

| Trace | Content | Result |
|---|---|---|
| Positive (`_pos`) | Legal traffic that reaches the valid boundary of the check: the antecedent is true and the property holds. Declare no expected error. | No `uvm_error`; the paired cover of the check is hit |
| Negative (`_neg`) | One violation, one unit beyond the boundary, produced by the injection of the requirement. Declare the expected error before the stimulus. | Exactly one error carrying the check ID, demoted inside the window |
| Capability (`_cap`) | The VIP generates or observes the capability and the monitor reports it. | No error; the capability coverage item is hit |

Negative trace pattern:

```systemverilog
virtual task run_phase(uvm_phase phase);
  phase.raise_objection(this, "<test name>");
  m_catcher.expect_error("<CHECK_ID>", 1, 1);   // ID, minimum, maximum
  m_catcher.start_window();
  counterpart.<injection task>();                // exactly one violation
  counterpart.wait_cycles(<enough cycles to observe the check>);
  m_catcher.end_window();                        // reports a missing expected error
  phase.drop_objection(this, "<test name>");
endtask
```

Declare an expected error for a `REC` check the same way; the warning is counted and not demoted. Remove the stub error and the `VIP_TODO` marker from a trace only when it is implemented. The base test fails a negative trace that declares nothing and a positive trace that declares something (vacuous trace guard).

For every numeric boundary of the specification produce traces at the valid minimum, the valid maximum, one below, and one above. Each invalid value is a negative trace of the check that owns the boundary.

## 4. Orthogonality check

For each negative trace read the log: only the declared check ID may fire. Another check firing means either the property is not orthogonal (fix the property and the specification note) or the injection violates two rules (fix the injection). Do not add the second ID to the expected list unless the specification says both rules are violated.

## 5. Coverage

1. Compile with coverage enabled and merge the runs of all variants and seeds.
2. Every valid bin of the boundary covergroups and every capability covergroup must be hit; every antecedent cover must be hit by a positive trace.
3. Invalid bins are hit only by negative traces; their hit shows the boundary was crossed.
4. Each exclusion carries a category (`UNR`, `NON_RTL`, `UNSUPPORTED`, `EXTERNAL`, or `LOW_RISK`) and a reason, and the reviewer signs it.
5. Record the database path and a summary with `collect_qual_results.py item --item coverage`.

## 6. Run the regression

```text
vip qual-init
vip set build_cmd="<build command>" run_cmd="<run command>" seeds=<N>
vip check-vip --record     # lint and UVM type-check evidence
vip qual-run               # one log per run; +VLSIT_SEED=<seed> is appended to the run command
vip qual-collect
vip lint qual
```

The build and run commands are the project's own; the runner appends `+VLSIT_SEED=<seed>` to the run command, and the test base prints it in the result line. Illustrative templates (not verified in this repository; confirm the flags against the installed simulator):

| Simulator | Build | Run |
|---|---|---|
| Synopsys VCS | `vcs -sverilog -full64 -ntb_opts uvm -timescale=1ns/1ps -f filelist/<tag>_vip.f {defines} -o {builddir}/simv` | `{builddir}/simv +UVM_TESTNAME={test} +ntb_random_seed={seed}` |
| Cadence Xcelium | `xrun -elaborate -uvm -f filelist/<tag>_vip.f {defines} -xmlibdirname {builddir}/xm` | `xrun -R -xmlibdirname {builddir}/xm +UVM_TESTNAME={test} -svseed {seed}` |
| Siemens Questa | `vlog -sv -f filelist/<tag>_vip.f {defines} -work {builddir}/work` | `vsim -c -work {builddir}/work <top> +UVM_TESTNAME={test} -sv_seed {seed} -do "run -all; quit"` |

The qualification top is `<tag>_qual_tb_top`. Add the simulator's coverage options to the commands. The checker is built with `+define+VLSIT_VIP_UVM` (already in the filelist).

## 7. Triage a failure

Classify before fixing, and record the classification in `qualification_report.md`:

| Class | Signs | Action |
|---|---|---|
| VIP defect | A positive trace shows a check error, a negative trace shows none, the driver breaks the protocol | Fix the VIP; re-run the affected traces and every trace that shares the code |
| Trace defect | The stimulus does not reach the boundary, the wrong injection, a vacuous pass | Fix the trace |
| Counterpart defect | The counterpart violates the protocol where it should not | Fix the counterpart independently of the VIP |
| Specification defect | The requirement is wrong, ambiguous, or incomplete | Stop; edit the specification; Gate 1 reopens |
| Environment defect | Tool, license, or script error | Fix the environment; the evidence stays `NOT_RUN` until the run is valid |

## 8. Gate 3

Present `qualification_report.md` with: counts of PASS, FAIL, NOT_RUN by variant; every FAIL with its class; coverage summary and exclusions; lint and compile status; waivers; and the exact tool versions. Ask:

- Do you approve the qualification evidence version N, including variants `<list>`, seeds `<N>`, and the waivers listed? Reply APPROVE, REVISE, or STOP.
