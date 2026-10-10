#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Create a VIP specification skeleton in the mandatory template format.

Everything that follows from the VLSIT rules is already filled: the front matter, the
usability contract UC-01..UC-13, the checker policy, the qualification plan, the gates,
the packaging rows, the three standard roles, the build-or-reuse row, and the empty
traceability row. Only protocol-specific cells carry a placeholder such as <fill ...>.
The validator lists what is left, and `spec_query.py todo` groups the open cells by
section, so the agent writes only protocol facts.

Usage:
    python spec_scaffold.py --tag apb --title "AMBA APB" --standard "IHI 0024C (APB4)" --out apb_spec.md
        [--no-guidance]

The output file must not exist. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402


_ROWS: dict[str, list[list[str]]] = {}
_TEXT: dict[str, str] = {}


def table(kind: str, rows: list[list[str]]) -> str:
    rows = _ROWS.get(kind, rows)
    cols = vc.TABLE_SCHEMAS[kind]["columns"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def req_section(key: str, na_default: str) -> str:
    """A requirements table when rows are supplied for this section, else the N/A paragraph."""
    rows = _ROWS.get(key)
    return table("requirements", rows) if rows else na_default


def build(tag: str, title: str, standard: str, guidance: bool, rows: dict[str, list[list[str]]] | None = None,
          text: dict[str, str] | None = None) -> str:
    """Build the skeleton. `rows` maps a table kind (or requirements_5.2 .. requirements_5.5) to rows that
    replace the default rows; `text` maps 'purpose' to replacement prose for Section 1.1."""
    _ROWS.clear()
    _ROWS.update(rows or {})
    _TEXT.clear()
    _TEXT.update(text or {})
    T = tag.upper()
    g = (lambda s: f"\n{s}\n") if guidance else (lambda s: "")
    fm = f'''---
document_type: asic_vip_specification
document_id: "{T}-VIP-SPEC"
title: "{title} Verification IP Specification"
vip_name: "{tag}_vip"
proto_tag: "{tag}"
version: "0.1"
status: "Draft"
spec_revision_locked: "{standard}"
language: "SystemVerilog IEEE 1800-2017; UVM IEEE 1800.2-2020"
vip_rules: "VLSIT_VIP_Design_Rule.md"
rtl_rules: "VLSIT_RTL_Design_Rule.md"
---
'''
    req_row = [f"VREQ-{T}-0001", "MUST", "M", "SIG", "<fill: The host shall ...>", "REF-001 <fill: clause>", "all",
               "<fill: signal>", "<fill: RULE>", "SVA", "auto", "-", "<fill: note or ->"]
    sections = [fm, f"# {title} Verification IP Specification",
                g("> Scaffold. Format and column meaning: see the template (`spec_template/VLSIT_ASIC_VIP_Specification_Template.md`). "
                  "Replace every `<fill ...>` cell; run `vip validate` and `vip query todo` to see what is left. Paraphrase the standard; cite clauses."),
                "## 1. Purpose, scope, and context", "### 1.1 Purpose and scope",
                _TEXT.get("purpose", "<fill: purpose, roles served, and what the VIP provides>") + "\n\n**Included:** <fill: roles, profiles, options, checking, coverage>\n\n**Excluded:** <fill: unsupported features and why>",
                "### 1.2 Build-or-reuse decision",
                table("candidates", [["none considered", "not applicable", "unknown", "Build", "<fill: reason>"]]),
                "### 1.3 Target environment",
                table("environment", [["Simulator(s) for qualification", "<fill: name and version>"],
                                      ["UVM version", "IEEE 1800.2-2020 (Accellera UVM 2020.3.1)"],
                                      ["Lint tool for interface and checker", "<fill: Verilator or slang, version>"],
                                      ["Formal tool for checkers (optional)", "Not used"],
                                      ["Operating system and shell", "<fill: OS and shell>"],
                                      ["Project name and human author", "<fill: project; author>"]]),
                "## 2. Normative references and precedence", "### 2.1 Normative references",
                table("references", [["REF-001", f"<fill: title, ID, and revision of {standard}>", "<fill: clauses>", "Protocol authority"],
                                      ["REF-002", "VLSIT VIP Design Rules v1, VLSIT_VIP_Design_Rule.md", "All", "VIP coding, naming, qualification, and release rules"],
                                      ["REF-003", "VLSIT RTL Design Rules v2, VLSIT_RTL_Design_Rule.md", "Inherited items listed in VSCP-03", "Referenced for inherited conventions only"]]),
                "### 2.2 Precedence and conflict handling",
                "1. The selected protocol revision (REF-001) defines protocol behavior.\n2. This specification defines the VIP contract.\n"
                "3. `VLSIT_VIP_Design_Rule.md` governs VIP code; no local exception is created.\n4. Resolve a conflict by an explicit decision in Section 14.",
                "### 2.3 Compliance declaration",
                table("compliance", [["<fill: protocol>", "<fill: revision and profile>", "<fill: host, device, monitor>", "<fill: options>", "None"]]),
                "## 3. Roles, profiles, and options", "### 3.1 Roles",
                table("roles", [["ROLE-01", "Host", "M", "<fill: signals driven by the host>", "ACTIVE"],
                                ["ROLE-02", "Device", "S", "<fill: signals driven by the device>", "ACTIVE"],
                                ["ROLE-03", "Monitor", "B", "none", "PASSIVE"]]),
                "### 3.2 Profiles",
                table("profiles", [["PROF-01", "<fill: profile name>", standard, "none", "<fill: notes>"]]),
                "### 3.3 Optional features",
                table("options", [["OPT-01", "<fill: optional feature>", "<fill: signals or none>", "<fill: on/off>", "In scope"]]),
                "### 3.4 Variants for qualification",
                table("variants", [["VAR-01", "PROF-01", "none", "<fill: PARA_NAME=value list>", "<fill: why this variant>"]]),
                "## 4. Interface definition", "### 4.1 Clocks and resets",
                table("clocks", [["<fill: domain>", "<fill: clock signal>", "<fill: reset signal>", "Active-low", "<fill: notes>"]]),
                "### 4.2 Parameters",
                table("parameters", [[f"PARA_<fill: NAME>", "<fill: purpose>", "<fill: default>", "<fill: legal values>", "<fill: unit>"]]),
                "### 4.3 Signals",
                table("signals", [["<fill: clock>", "1", "CLK", "all", "not applicable", "<fill: meaning>"],
                                  ["<fill: reset>", "1", "RST", "all", "not applicable", "<fill: meaning>"],
                                  ["<fill: signal>", "<fill: width>", "M", "all", "<fill: idle value>", "<fill: meaning>"]]),
                "### 4.4 Timing relationships",
                table("timing", [["<fill: cycle or event>", "<fill: condition>", "<fill: observable result>"]]),
                "## 5. Protocol requirements",
                g("Requirement conventions: see the template Section 5.1. One behavior per row; the modal verb matches Strength."),
                "### 5.2 Signal-level requirements", table("requirements", _ROWS.get("requirements_5.2") or [req_row]),
                "### 5.3 Sequence and handshake requirements", req_section("requirements_5.3", "N/A: <fill: reason, or replace with a requirements table>"),
                "### 5.4 Transaction-level requirements", req_section("requirements_5.4", "N/A: <fill: reason, or replace with a requirements table>"),
                "### 5.5 Configuration, option, and capability requirements", req_section("requirements_5.5", "N/A: <fill: reason, or replace with a requirements table>"),
                "### 5.6 Boundary analysis",
                table("boundaries", [["BND-001", "<fill: quantity>", "<fill: unit>", "<fill: min>", "<fill: max>", "<fill: min - 1 or ->",
                                      "<fill: max + 1 or ->", "<fill: spec statement or derivation>", f"VREQ-{T}-0001"]]),
                "## 6. VIP functional model", "### 6.1 Transaction item fields",
                table("items", [["<fill: field>", "logic", "<fill: width>", "rand", "<fill: meaning>", "M,S"]]),
                "### 6.2 Stimulus capabilities",
                table("caps", [["CAP-001", "M", "<fill: capability>", "none", f"{tag}_<fill: function>_seq", f"VREQ-{T}-0001"]]),
                "### 6.3 Error injection",
                table("injections", [["INJ-001", "M", "<fill: violation>", "item field inj_kind = <fill: ENUM_MEMBER>", f"VREQ-{T}-0001", "auto"]]),
                "### 6.4 Monitor and collector",
                table("monitors", [["MON-001", "<fill: event that completes a transfer>", f"{tag}_item", "ap", "<fill: notes>"]]),
                "## 7. VIP API and usability contract", "### 7.1 Configuration knobs",
                table("knobs", [["<fill: knob>", "int unsigned", "0", "<fill: effect>", "CAP-001"]]),
                "### 7.2 Usability contract",
                table("contract", [
                    ["UC-01", "Package and import", f"Package {tag}_vip_pkg; the single import line is import {tag}_vip_pkg::*;"],
                    ["UC-02", "Instantiation steps", f"Create {tag}_agent_cfg and set its vif; create {tag}_agent with that cfg; start any sequence on the agent sequencer"],
                    ["UC-03", "Default behavior", "Legal random traffic with bounded random delays and no errors"],
                    ["UC-04", "Mode knobs", "The base knobs is_active, if_mode, and has_driver select host, device, or passive monitor; protocol knobs adjust traffic"],
                    ["UC-05", "Width and option control", f"Widths come from the PARA_ parameters through one {T}_VIP_ macro per parameter (VIFC-01); options follow the profile"],
                    ["UC-06", "Checker control", "cfg.disable_check with a check ID and a reason; cfg.rec_on disables all REC checks together"],
                    ["UC-07", "Message format", "Message ID is the check ID; the text starts with the requirement ID and the spec reference"],
                    ["UC-08", "Quickstart", f"Test {tag}_quickstart_test connects a host and a device of this VIP on one interface and passes with no error"],
                    ["UC-09", "Reset behavior", "Reset may assert at any cycle; drivers abandon the item, drive reset values, and resume after release"],
                    ["UC-10", "X policy", "Payload signals are driven X while their qualifying signal is inactive (VIFC-07)"],
                    ["UC-11", "Error injection selection", "Set the inj_kind item field in a sequence; no callbacks"],
                    ["UC-12", "Documentation set", "README with cfg fields, config_db keys, TLM ports, overridable classes, interface and clock assumptions"],
                    ["UC-13", "Versioning", f"Semantic version plus the spec_rev tag {standard}"]]),
                "## 8. Checker requirements",
                table("policy", [
                    ["CP-01", "Severity mapping", "ERR checks report with uvm_error; REC checks report with uvm_warning"],
                    ["CP-02", "Role handling", "Simulation asserts every check; a formal run assumes the checks of the role that does not belong to the DUT"],
                    ["CP-03", "Waiver mechanism", "cfg.disable_check with a check ID and a mandatory reason; the reason is printed in the report phase"],
                    ["CP-04", "Formal compatibility", "Code that calls UVM is guarded by the VLSIT_VIP_UVM macro; the VLSIT_VIP_FORMAL macro removes reporting"],
                    ["CP-05", "Performance knobs", "<fill: maximum wait or latency knob and default, or not applicable>"],
                    ["CP-06", "Unimplemented stub behavior", "A stub reports a warning with its check ID at time 0 and at the end of simulation"],
                    ["CP-07", "Vacuity control", "Each assertion has a cover of its antecedent with the same check ID"]]),
                "### 8.1 Check expressions",
                g("Single-cycle boolean expressions; write OR for ||. SAME is |->, NEXT is |=>."),
                table("checkexpr", [[f"VREQ-{T}-0001", "NEXT", "<fill: antecedent>", "<fill: consequent>", "<fill: violation text>"]]),
                "## 9. Coverage requirements",
                table("covreq", [["CVR-001", "<fill: goal>", f"VREQ-{T}-0001", "<fill: bins and crosses>", "<fill: notes>"]]),
                "## 10. Sequences and compliance tests",
                table("seqs", [["SEQ-001", f"{tag}_base_seq", "M", "Base sequence and common helpers", "-"]]),
                "## 11. Qualification plan",
                table("qualplan", [
                    ["QP-01", "Counterpart model", "A behavioral model of the protocol that drives and answers valid and invalid transfers cycle by cycle, written separately from the VIP checkers"],
                    ["QP-02", "Independence", "The standard analysis is reviewed by a person who does not implement the VIP; the reviewer is recorded in requirements.csv"],
                    ["QP-03", "Expected-error mechanism", "vlsit_vip_expect_catcher declares the expected check ID, minimum, maximum, and window before each negative trace"],
                    ["QP-04", "Variants and seeds", "Every variant of Section 3.4 with <fill: seeds per variant> seeds; seeds are recorded in the logs"],
                    ["QP-05", "Simulators", "<fill: simulators and command templates>"],
                    ["QP-06", "Coverage closure", "All valid bins closed; exclusions need a category and a reason"],
                    ["QP-07", "Lint and formal", "Verilator lint of the interface and checker without UVM; slang type-check of the UVM tree; formal use of the checkers is not planned"]]),
                table("gates", [["VIP-0", "Defaults of VLSIT_VIP_Design_Rule.md Section 11"], ["VIP-1", "Defaults of VLSIT_VIP_Design_Rule.md Section 11"],
                                ["VIP-2", "Defaults of VLSIT_VIP_Design_Rule.md Section 11"], ["VIP-3", "Defaults of Section 11, with <fill: N> seeds per variant"]]),
                "## 12. Deliverables and packaging",
                table("packaging", [
                    ["PK-01", "Directory layout", "Follows VFIL-03 with no deviation"],
                    ["PK-02", "Package and filelist", f"{tag}_vip_pkg.sv and filelist/{tag}_vip.f"],
                    ["PK-03", "Documentation", "README, traceability report, qualification report, release notes"],
                    ["PK-04", "Versioning", f"Semantic version; spec_rev tag {standard}"],
                    ["PK-05", "License and attribution", "Project license of the user; the VLSIT VIP base package carries Apache-2.0"]]),
                "## 13. Traceability matrix", table("trace", [["(generated)", "-", "-", "-", "-", "-", "not generated"]]),
                "## 14. Assumptions, dependencies, and decisions",
                table("decisions", [["DEC-001", "Assumption", "<fill: statement>", "<fill: impact>", "<fill: resolution or status>"]]),
                "## 15. Glossary", table("glossary", [["<fill: term>", "<fill: definition>"]]),
                "## 16. References used to shape this template",
                "This specification follows `VLSIT_ASIC_VIP_Specification_Template.md`; the practice behind it is in `docs/VLSIT_VIP_Build_Process.md`."]
    return "\n\n".join(s.strip("\n") for s in sections if s) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--standard", required=True, help="standard document ID and revision, for example 'IHI 0024C (APB4)'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-guidance", action="store_true")
    a = ap.parse_args()
    if not vc.TAG_RE.match(a.tag):
        raise SystemExit("error: --tag must be 2-8 lowercase alphanumerics starting with a letter")
    vc.refuse_overwrite(a.out)
    Path(a.out).write_text(build(a.tag, a.title, a.standard, not a.no_guidance), encoding="utf-8", newline="\n")
    n = len(re.findall(r"<fill", Path(a.out).read_text(encoding="utf-8")))
    print(f"wrote {a.out}: {n} cell(s) to fill; run: spec_query.py todo {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
