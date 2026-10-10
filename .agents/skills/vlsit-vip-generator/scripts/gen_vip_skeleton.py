#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the VIP source tree (layout VFIL-03) from vip_config.json.

Everything that follows from the specification is generated completely: the
interface with clocking blocks, the checker enable vector, parameter macros,
the package, configuration, item, covergroups for boundary bins, test files,
the quickstart example, filelists, and a README skeleton. Everything that needs
protocol understanding is generated as a stub that announces itself and carries
a `VIP_TODO(<id>)` marker: checker bodies, monitor collection, driver bodies,
sequence bodies, the qualification counterpart, and the qualification traces.

Usage:
    python gen_vip_skeleton.py --config vip_config.json --out-dir DIR/<tag>_vip \
        --author "NAME" --project "PROJECT" [--requirements requirements.csv] [--date YYYY-MM-DD]

The output directory must not exist. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from datetime import date
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SKILL_DIR / "assets" / "base"
FLOW_PAGE = "https://github.com/nguyenquanicd/VLSIT_ASIC_VIP_DESIGN_AI_FLOW"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

class Ctx:
    def __init__(self, cfg: dict, author: str, project: str, day: str):
        self.cfg, self.author, self.project, self.day = cfg, author, project, day
        self.tag = cfg["tag"]
        self.TAG = cfg["tag"].upper()
        self.rst = cfg["clock"]["reset"]
        self.clk = cfg["clock"]["signal"]
        self.param_names = [p["name"] for p in cfg["parameters"]]

    def hdr(self, desc: str) -> str:
        lines = textwrap.wrap(desc, 78) or [""]
        body = [f" * Description  : {lines[0]}"] + [f" *                {x}" for x in lines[1:]]
        return "\n".join([
            "/*", f" * Project      : {self.project}", f" * Author       : {self.author} (user)",
            " * AI Flow      : VLSIT ASIC VIP Design AI Flow", f" * AI Flow Page : {FLOW_PAGE}",
            f" * Date         : {self.day}", *body, " */"]) + "\n"


def cmt(text: str, indent: int = 0) -> str:
    pad = " " * indent
    out = []
    for para in text.split("\n"):
        for ln in (textwrap.wrap(para, 96 - indent) or [""]):
            out.append(f"{pad}// {ln}".rstrip())
    return "\n".join(out)


def lc(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def sv_str(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def if_range(w) -> str:
    if isinstance(w, int):
        return "" if w == 1 else f"[{w - 1}:0]"
    return f"[({w})-1:0]"


def macro_expr(ctx: Ctx, w) -> str:
    """Width expression for class code: PARA_X becomes `<TAG>_VIP_X."""
    if isinstance(w, int):
        return str(w)
    def rep(m):
        name = m.group(0)
        return f"(`{ctx.TAG}_VIP_{name[len('PARA_'):]})" if name.startswith("PARA_") else name
    return re.sub(r"[A-Za-z_][A-Za-z0-9_]*", rep, w)


def class_range(ctx: Ctx, w) -> str:
    if isinstance(w, int):
        return "" if w == 1 else f"[{w - 1}:0]"
    return f"[({macro_expr(ctx, w)})-1:0]"


def reset_literal(val: str, w) -> str:
    v = val.strip().lower()
    if v in ("0", "'0", "0x0"):
        return "'0"
    if v in ("x", "z"):
        return "'x"
    if v == "1" and (isinstance(w, int) and w == 1):
        return "1'b1"
    if v.isdigit():
        return v
    return "'0"


def sig_by_driver(cfg: dict, letter: str) -> list[dict]:
    return [s for s in cfg["signals"] if s["driver"] == letter]


def chk_pkg_name(ctx: Ctx) -> str:
    return f"{ctx.tag}_chk_pkg"


def param_decl(p: dict, last: bool, indent: str = "  ") -> str:
    lines = [
        f"{indent}// Parameter Description: {p['description']}",
        f"{indent}// Parameter values: legal values are {p['legal']}; default is {p['default']}.",
        f"{indent}// Parameter unit: {p['unit']}",
    ]
    wrapped = []
    for ln in lines:
        wrapped.extend(textwrap.wrap(ln, 98, subsequent_indent=indent + "//   ") or [ln])
    wrapped.append(f"{indent}parameter logic [31:0] {p['name']} = {p['default']}{'' if last else ','}")
    return "\n".join(wrapped)


# --------------------------------------------------------------------------
# rtl_if
# --------------------------------------------------------------------------

def gen_defines(c: Ctx) -> str:
    cfg = c.cfg
    guard = f"{c.TAG}_VIP_DEFINES_SVH"
    out = [c.hdr(f"Parameter macros of the {c.tag} VIP. They bind the UVM class library to the interface "
                 f"parameters (VIFC-01). Override one with +define+<MACRO>=<value> at compile time."),
           f"`ifndef {guard}", f"`define {guard}", ""]
    for p in cfg["parameters"]:
        out += [cmt(f"{p['name']}: {p['description']} Unit: {p['unit']}. Legal values: {p['legal']}."),
                f"`ifndef {p['macro']}", f"  `define {p['macro']} {p['default']}", "`endif", ""]
    out += [cmt(f"Specification revision implemented by this VIP (spec_rev)."),
            f"`define {c.TAG}_VIP_SPEC_REV \"{sv_str(cfg['spec_rev'])}\"", "", "`endif", ""]
    return "\n".join(out)


def gen_chk_pkg(c: Ctx) -> str:
    cfg = c.cfg
    checks = cfg["checks"]
    n = max(1, len(checks))
    mask = "".join("1" if (checks[i]["is_rec"] if i < len(checks) else False) else "0" for i in reversed(range(n)))
    out = [c.hdr(f"Check enable indices of the {c.tag} checker. UVM-free so lint and formal can use it."),
           "`timescale 1ns/1ps", "", f"package {chk_pkg_name(c)};", "",
           f"  // Number of checks, which is the width of the enable vector i_chk_en.",
           f"  localparam int unsigned LPARA_NCHK = {n};", "",
           "  // Bit i is 1 when check i is a recommendation (REC) check.",
           f"  localparam bit [LPARA_NCHK-1:0] LPARA_REC_MASK = {n}'b{mask};", ""]
    for ck in checks:
        out.append(f"  localparam int unsigned CHK_IDX_{ck['id']} = {ck['index']};")
    out += ["", "  // Returns the enable-vector index of a check ID, or -1 for an unknown ID.",
            f"  function automatic int {c.tag}_chk_index(string id);"]
    for ck in checks:
        out.append(f"    if (id == \"{ck['id']}\") return {ck['index']};")
    out += ["    return -1;", "  endfunction", "",
            "  // Returns 1 when the check at idx is a recommendation (REC) check.",
            f"  function automatic bit {c.tag}_chk_is_rec(int unsigned idx);",
            "    return (idx < LPARA_NCHK) ? LPARA_REC_MASK[idx] : 1'b0;", "  endfunction", "",
            "endpackage", ""]
    return "\n".join(out)


def port_list(cfg: dict, indent: str = "  ") -> list[str]:
    ports = []
    for s in cfg["signals"]:
        r = if_range(s["width"])
        ports.append(f"{indent}input logic {r + ' ' if r else ''}{s['name']}")
    return ports


def emit_check(ck: dict, macro: str) -> str:
    """One complete check macro call from a check expression (Section 8.1 of the specification)."""
    ex = ck["expr"]
    msg = sv_str(ex["msg"])
    lines = [f"  `{macro}({ck['id']}, {ck['role']}, \"{ck['req_id']}\", \"{msg}\",",
             f"    ({ex['ante']}) {ex['op']} ({ex['cons']}),",
             f"    {ex['ante']})"]
    return "\n".join(lines)


def gen_checker(c: Ctx) -> str:
    cfg = c.cfg
    params = cfg["parameters"]
    out = [c.hdr(f"Protocol checker of the {c.tag} VIP, one assertion per requirement with check type SVA. "
                 f"UVM-free (VIFC-08). Every check has its own enable bit and a paired cover (VCHK-07)."),
           "`timescale 1ns/1ps", "", '`include "vlsit_vip_chk_macros.svh"', "",
           f"interface {c.tag}_checker #("]
    plist = [param_decl(p, False) for p in params]
    plist.append(param_decl({"name": "PARA_DUT_ROLE", "default": 0, "unit": "none",
                             "description": "role of the DUT in a formal run: 0 none (every check is asserted), "
                                            "1 DUT is the host, 2 DUT is the device.",
                             "legal": "0, 1, or 2"}, True))
    out += ["\n".join(plist), ") ("]
    ports = port_list(cfg)
    ports.append(f"  input logic [{chk_pkg_name(c)}::LPARA_NCHK-1:0] i_chk_en")
    out += [",\n".join(ports), ");", "", f"  import {chk_pkg_name(c)}::*;", "",
            cmt("Roles whose checks become assumptions in a formal run (VCHK-02).", 2),
            "  localparam bit LPARA_ASSUME_M = (PARA_DUT_ROLE == 2);",
            "  localparam bit LPARA_ASSUME_S = (PARA_DUT_ROLE == 1);",
            "  localparam bit LPARA_ASSUME_B = 1'b0;", "",
            cmt("Clock and reset used by every check.", 2),
            f"  wire w_clk = {c.clk};",
            f"  wire w_rst_active = {'~' if cfg['clock']['reset_active_low'] else ''}{c.rst};", ""]
    for ck in cfg["checks"]:
        if ck["type"] != "SVA":
            continue
        out.append(cmt(f"{ck['req_id']} ({ck['strength']}, role {ck['role']}): {ck['text']}", 2))
        out.append(cmt(f"Spec reference: {ck['spec_ref']}", 2))
        macro = "VLSIT_VIP_CHK_REC" if ck["is_rec"] else "VLSIT_VIP_CHK_ERR"
        ex = ck.get("expr")
        if ex:
            out.append(cmt(f"Coverage ID {ck['cov_id']}: cover of the antecedent (label c_{ck['id']}).", 2))
            out.append(cmt("Property from the specification Section 8.1.", 2))
            out.append(emit_check(ck, macro))
        else:
            out.append(cmt(f"Coverage ID {ck['cov_id']}: cover of the antecedent. VIP_TODO({ck['cov_id']})", 2))
            out.append(cmt(f"VIP_TODO({ck['id']}): replace the stub with the implemented check:", 2))
            out.append(cmt(f"`{macro}({ck['id']}, {ck['role']}, \"{ck['req_id']}\", \"<message>\", <property>, <antecedent>)", 2))
            out.append(f"  `VLSIT_VIP_CHK_TODO({ck['id']}, \"{ck['req_id']}\")")
        out.append("")
    out += ["endinterface", ""]
    return "\n".join(out)


def gen_if(c: Ctx) -> str:
    cfg = c.cfg
    params = cfg["parameters"]
    sigs = cfg["signals"]
    hostdrv = [s for s in sigs if s["driver"] == "M"]
    devdrv = [s for s in sigs if s["driver"] == "S"]
    data = [s for s in sigs if s["driver"] in ("M", "S")]
    out = [c.hdr(f"Interface of the {c.tag} VIP: signals, clocking blocks per role, modports, and the "
                 f"embedded checker. Reset polarity: {'active-low' if cfg['clock']['reset_active_low'] else 'active-high'}."),
           "`timescale 1ns/1ps", "", f"interface {c.tag}_if #("]
    if params:
        out.append("\n".join(param_decl(p, i == len(params) - 1) for i, p in enumerate(params)))
    else:
        out.append("  parameter logic [31:0] PARA_UNUSED = 0")
    out += [") (", f"  input logic {c.clk},", f"  input logic {c.rst}", ");", "",
            f"  import {chk_pkg_name(c)}::*;", "", cmt("Protocol signals (VIFC-02).", 2)]
    for s in sigs:
        if s["driver"] in ("CLK", "RST"):
            continue
        r = if_range(s["width"])
        out.append(f"  logic {r + ' ' if r else ''}{s['name']};  // driven by {'host' if s['driver'] == 'M' else 'device'}")
    out += ["", cmt("Enable bit per check; the agent clears bits for waivers (VCHK-05).", 2),
            f"  logic [LPARA_NCHK-1:0] chk_en = '1;", ""]

    def clocking(name: str, outs: list[dict], ins: list[dict], skew_out: bool) -> list[str]:
        L = [f"  clocking {name} @(posedge {c.clk});"]
        L.append("    default input #1step output #1;" if skew_out else "    default input #1step;")
        if outs:
            L.append("    output " + ", ".join(s["name"] for s in outs) + ";")
        if ins:
            L.append("    input " + ", ".join(s["name"] for s in ins) + ";")
        L.append("  endclocking")
        return L
    out += [cmt("Clocking blocks per role (VIFC-04). Output skew is 1 time unit; input is sampled at 1step.", 2)]
    out += clocking("host_cb", hostdrv, devdrv, True) + [""]
    out += clocking("device_cb", devdrv, hostdrv, True) + [""]
    out += clocking("mon_cb", [], data, False) + [""]
    out += [cmt("Modports document the direction per role (VIFC-06).", 2),
            f"  modport host_mp (clocking host_cb, input {c.clk}, input {c.rst});",
            f"  modport device_mp (clocking device_cb, input {c.clk}, input {c.rst});",
            f"  modport mon_mp (clocking mon_cb, input {c.clk}, input {c.rst});", "",
            cmt("Embedded protocol checker (VIFC-08: UVM-free).", 2),
            f"  {c.tag}_checker #("]
    conn = [f"    .{p['name']}({p['name']})" for p in params] + ["    .PARA_DUT_ROLE(0)"]
    out += [",\n".join(conn), "  ) u_checker ("]
    pc = [f"    .{s['name']}({s['name']})" for s in sigs] + ["    .i_chk_en(chk_en)"]
    out += [",\n".join(pc), "  );", "", "endinterface", ""]
    return "\n".join(out)


# --------------------------------------------------------------------------
# uvm
# --------------------------------------------------------------------------

def knob_decl(k: dict) -> str:
    t = k["type"].strip()
    d = k["default"].strip()
    return f"  {t} {k['name']} = {d};"


def gen_cfg(c: Ctx) -> str:
    cfg = c.cfg
    out = [c.hdr(f"Configuration of the {c.tag} agent: base knobs from vlsit_vip_agent_cfg, the virtual "
                 f"interface, and the protocol knobs of the specification (VCFG-01)."),
           f"class {c.tag}_agent_cfg extends vlsit_vip_agent_cfg;", "",
           cmt("Virtual interface of the agent; set it before the agent is built (VCFG-05).", 2),
           f"  {c.tag}_vif_t vif;", ""]
    for k in cfg["knobs"]:
        out.append(cmt(f"{k['description']}", 2))
        out.append(knob_decl(k))
    out += ["", f"  `uvm_object_utils({c.tag}_agent_cfg)", "",
            f"  function new(string name = \"{c.tag}_agent_cfg\");", "    super.new(name);",
            f"    spec_rev = `{c.TAG}_VIP_SPEC_REV;", "  endfunction", "", "endclass", ""]
    return "\n".join(out)


def inj_members(c: Ctx) -> list[tuple[str, str]]:
    members = []
    for i in c.cfg["injections"]:
        m = re.search(r"=\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", i["mechanism"].strip())
        name = m.group(1) if m else f"{c.TAG}_INJ_{i['id'].split('-')[-1]}"
        members.append((name, i["id"]))
    return members


def item_type(c: Ctx, f: dict) -> str:
    t = f["type"].strip()
    if t.startswith("enum:"):
        return t.split(":", 1)[1]
    if t.startswith("logic") or t.startswith("bit"):
        base = t.split()[0]
        r = class_range(c, f["width"])
        return f"{base} {r}".strip()
    return t


def gen_item(c: Ctx) -> str:
    cfg = c.cfg
    out = [c.hdr(f"Transaction item of the {c.tag} VIP: one protocol transfer."), ""]
    enums = sorted({f["type"].split(":", 1)[1] for f in cfg["item_fields"] if f["type"].startswith("enum:")})
    for e in enums:
        if e.endswith("_inj_e"):
            mem = inj_members(c)
            names = [f"{c.TAG}_INJ_NONE"] + [m for m, _ in mem]
            out.append(cmt("Error injection kinds, one per INJ row of the specification (VCHK-08, UC-11)."))
            out.append(f"typedef enum int unsigned {{")
            out.append(",\n".join(f"  {n}" + (f" = {i}" if i == 0 else "") for i, n in enumerate(names)))
            out.append(f"}} {e};")
        else:
            out.append(cmt(f"VIP_TODO(item-enum-{e}): define the enum type {e} from the specification."))
            out.append(f"typedef enum int unsigned {{ {e.upper()}_UNSPECIFIED = 0 }} {e};")
        out.append("")
    out.append(f"class {c.tag}_item extends uvm_sequence_item;")
    out.append("")
    for f in cfg["item_fields"]:
        rnd = "" if f["rand"] == "none" else f["rand"] + " "
        out.append(cmt(f["description"], 2))
        out.append(f"  {rnd}{item_type(c, f)} {f['name']};")
    out += ["", f"  `uvm_object_utils({c.tag}_item)", "",
            f"  function new(string name = \"{c.tag}_item\");", "    super.new(name);", "  endfunction", ""]

    def fmt(f):
        t = f["type"]
        return ("%s", f"{f['name']}.name()") if t.startswith("enum:") else (
            ("%0h", f["name"]) if t.startswith("logic") or t.startswith("bit") else ("%0d", f["name"]))
    fm = [fmt(f) for f in cfg["item_fields"]]
    fmt_s = " ".join(f"{f['name']}={fm[i][0]}" for i, f in enumerate(cfg["item_fields"]))
    args = ", ".join(a for _, a in fm)
    out += ["  virtual function string convert2string();",
            f"    return $sformatf(\"{fmt_s}\",", f"                     {args});", "  endfunction", "",
            "  virtual function void do_copy(uvm_object rhs);", f"    {c.tag}_item r;",
            "    super.do_copy(rhs);", "    if (!$cast(r, rhs)) begin",
            f"      `uvm_fatal(\"{c.TAG}_VIP_ITEM\", \"do_copy: rhs is not a {c.tag}_item\")", "    end"]
    for f in cfg["item_fields"]:
        out.append(f"    {f['name']} = r.{f['name']};")
    out += ["  endfunction", "", "  virtual function bit do_compare(uvm_object rhs, uvm_comparer comparer);",
            f"    {c.tag}_item r;", "    if (!$cast(r, rhs)) begin", "      return 1'b0;", "    end",
            "    return super.do_compare(rhs, comparer)"]
    for f in cfg["item_fields"]:
        out.append(f"        && ({f['name']} === r.{f['name']})")
    out += ["        ;", "  endfunction", "", "endclass", ""]
    return "\n".join(out)


def gen_monitor(c: Ctx) -> str:
    cfg = c.cfg
    rst = c.rst
    out = [c.hdr(f"Monitor of the {c.tag} VIP: publishes one {c.tag}_item per transfer and tracks the reset."),
           f"class {c.tag}_monitor extends vlsit_vip_monitor_base #({c.tag}_item, {c.tag}_agent_cfg);", "",
           f"  `uvm_component_utils({c.tag}_monitor)", "",
           "  function new(string name, uvm_component parent);", "    super.new(name, parent);", "  endfunction", "",
           cmt("Maintains cfg.in_reset from the protocol reset (VMON-01, VAPI-03).", 2),
           "  virtual task track_reset();",
           f"    cfg.in_reset = ({'cfg.vif.' + rst} === 1'b{'0' if cfg['clock']['reset_active_low'] else '1'});",
           "    forever begin", f"      @(cfg.vif.{rst});",
           f"      cfg.in_reset = ({'cfg.vif.' + rst} === 1'b{'0' if cfg['clock']['reset_active_low'] else '1'});",
           "    end", "  endtask", ""]
    for ck in cfg["checks"]:
        if ck["type"] == "CLASS":
            lid = lc(ck["id"])
            out += [cmt(f"{ck['req_id']} ({ck['strength']}, role {ck['role']}): {ck['text']} Spec reference: {ck['spec_ref']}. "
                        f"Coverage ID {ck['cov_id']}. VIP_TODO({ck['id']}): call check_{lid}(item) from collect_trans "
                        f"and report a violation with uvm_error using the ID {ck['id']}.", 2),
                    f"  protected function void check_{lid}({c.tag}_item item);",
                    f"    `uvm_warning(\"{ck['id']}\", \"VIP_TODO class check is not implemented\")", "  endfunction", ""]
    mons = cfg.get("monitors", []) or [{"id": "MON-001", "event": "transfer complete"}]
    out += ["  virtual task collect_trans();"]
    for m in mons:
        out.append(cmt(f"VIP_TODO({m['id']}): {m.get('event', 'observe the interface')}. Sample through "
                       f"cfg.vif.mon_cb, build one {c.tag}_item, call transfer_started and transfer_ended around it, "
                       f"then call publish(item).", 4))
    out += [f"    `uvm_warning(\"{c.TAG}_VIP_MON\", \"VIP_TODO monitor collect_trans is not implemented\")",
            "    forever begin", "      @(cfg.vif.mon_cb);", "    end", "  endtask", "", "endclass", ""]
    return "\n".join(out)


def drive_resets(c: Ctx, letter: str) -> list[str]:
    L = []
    for s in sig_by_driver(c.cfg, letter):
        L.append(f"    cfg.vif.{s['name']} = {reset_literal(s['reset'], s['width'])};")
    return L or ["    // No signal is driven by this role."]


def gen_driver(c: Ctx, host: bool) -> str:
    letter = "M" if host else "S"
    name = f"{c.tag}_driver_{'host' if host else 'device'}"
    cb = "host_cb" if host else "device_cb"
    out = [c.hdr(f"{'Host' if host else 'Device'} driver of the {c.tag} VIP. "
                 f"{'Starts transfers from items.' if host else 'Reactive: answers the DUT with the cfg response knobs (VDRV-02).'}"),
           f"class {name} extends vlsit_vip_driver_base #({c.tag}_item, {c.tag}_agent_cfg);", "",
           f"  `uvm_component_utils({name})", "",
           "  function new(string name, uvm_component parent);", "    super.new(name, parent);", "  endfunction", "",
           cmt("Drives every signal of this role to its reset value (VDRV-01). Values: specification Section 4.3.", 2),
           "  virtual task reset_signals();"]
    out += drive_resets(c, letter)
    out += ["  endtask", "",
            cmt(f"VIP_TODO({name}): pull an item, drive it through cfg.vif.{cb} only (VIFC-04), set "
                f"item_in_flight between get_next_item and item_done, and honor the cfg delay knobs "
                f"and zero_delays. The stub completes the item without driving so sequences finish.", 2),
            "  virtual task get_and_drive();",
            f"    `uvm_warning(\"{c.TAG}_VIP_DRV\", \"VIP_TODO {name} get_and_drive is not implemented\")",
            "    seq_item_port.get_next_item(req);", "    item_in_flight = 1'b1;", f"    @(cfg.vif.{cb});",
            "    seq_item_port.item_done();", "    item_in_flight = 1'b0;", "  endtask", "", "endclass", ""]
    return "\n".join(out)


def gen_sequencer(c: Ctx) -> str:
    return "\n".join([
        c.hdr(f"Sequencer of the {c.tag} VIP."),
        f"class {c.tag}_sequencer extends vlsit_vip_sequencer_base #({c.tag}_item, {c.tag}_agent_cfg);", "",
        f"  `uvm_component_utils({c.tag}_sequencer)", "",
        "  function new(string name, uvm_component parent);", "    super.new(name, parent);", "  endfunction", "",
        "endclass", ""])


def bin_values(b: dict) -> list[str]:
    def num(x):
        x = x.strip()
        return None if x in ("-", "") else x
    bins = []
    vmin, vmax = num(b["valid_min"]), num(b["valid_max"])
    if vmin is not None and vmax is not None:
        bins.append(f"bins valid_range = {{[{vmin}:{vmax}]}};" if vmin != vmax else f"bins valid_value = {{{vmin}}};")
    if num(b["invalid_below"]) is not None:
        bins.append(f"bins inv_below = {{{num(b['invalid_below'])}}};")
    if num(b["invalid_above"]) is not None:
        bins.append(f"bins inv_above = {{{num(b['invalid_above'])}}};")
    return bins


def gen_cov(c: Ctx) -> str:
    cfg = c.cfg
    bounds = {b["id"]: b for b in cfg["bounds"]}
    groups = []
    out = [c.hdr(f"Functional coverage of the {c.tag} VIP: one covergroup per coverage ID that is not an "
                 f"assertion antecedent. Valid and invalid boundary bins are separate (VCOV-01, VCOV-02)."),
           f"class {c.tag}_agent_cov extends vlsit_vip_cov_base #({c.tag}_item, {c.tag}_agent_cfg);", "",
           f"  `uvm_component_utils({c.tag}_agent_cov)", ""]
    for cv in cfg["coverage"]:
        if cv["check"] and cv["bound"] is None:
            continue
        gname = f"cg_{lc(cv['id'])}"
        groups.append((gname, cv))
        if cv["bound"]:
            b = bounds[cv["bound"]]
            out += [cmt(f"{cv['id']} for {cv['req_id']}: {b['quantity']} ({b['unit']}) from {b['id']}.", 2),
                    f"  covergroup {gname} with function sample(int unsigned value);",
                    "    option.per_instance = 1;", f"    option.name = \"{cv['id']}\";",
                    "    cp_value : coverpoint value {"]
            out += [f"      {x}" for x in bin_values(b)]
            out += ["    }", "  endgroup", ""]
        else:
            out += [cmt(f"{cv['id']} for {cv['req_id']}: the scenario was observed at least once.", 2),
                    f"  covergroup {gname} with function sample(bit seen);",
                    "    option.per_instance = 1;", f"    option.name = \"{cv['id']}\";",
                    "    cp_seen : coverpoint seen { bins hit = {1'b1}; }", "  endgroup", ""]
    out += ["  function new(string name, uvm_component parent);", "    super.new(name, parent);"]
    out += [f"    {g} = new();" for g, _ in groups]
    out += ["  endfunction", "", f"  virtual function void write({c.tag}_item t);"]
    for g, cv in groups:
        arg = "<value>" if cv["bound"] else "1'b1"
        out.append(cmt(f"VIP_TODO({cv['id']}): call {g}.sample({arg}) when t shows the scenario of {cv['req_id']}.", 4))
    if not groups:
        out.append("    // No covergroup in this class.")
    out += ["  endfunction", "", "endclass", ""]
    return "\n".join(out)


def gen_agent(c: Ctx) -> str:
    t = c.tag
    return "\n".join([
        c.hdr(f"Agent of the {t} VIP (VAGT-01). It builds the monitor always, and the sequencer and a host or "
              f"device driver only when active. Waivers and the REC switch of the cfg are applied here."),
        f"class {t}_agent extends vlsit_vip_agent_base #({t}_agent_cfg, {t}_item, {t}_driver_host,",
        f"                                          {t}_driver_device, {t}_sequencer, {t}_monitor, {t}_agent_cov);", "",
        f"  `uvm_component_utils({t}_agent)", "",
        "  function new(string name, uvm_component parent);", "    super.new(name, parent);", "  endfunction", "",
        "  virtual function void build_phase(uvm_phase phase);", "    super.build_phase(phase);",
        "    if (cfg.vif == null) begin",
        f"      `uvm_fatal(\"{c.TAG}_VIP_CFG\", \"cfg.vif is not set; set the virtual interface before building the agent\")",
        "    end", "  endfunction", "",
        cmt("Applies the REC group switch and the waivers to the shared enable vector. Bits are only cleared, so "
            "several agents on one interface do not undo each other.", 2),
        "  virtual function void apply_check_controls();", "    string ids[$];", "    int    idx;",
        f"    for (int unsigned i = 0; i < {chk_pkg_name(c)}::LPARA_NCHK; i++) begin",
        f"      if ({chk_pkg_name(c)}::{t}_chk_is_rec(i)) begin",
        "        cfg.vif.chk_en[i] = cfg.vif.chk_en[i] & cfg.rec_on;", "      end", "    end",
        "    cfg.get_disabled_checks(ids);", "    foreach (ids[i]) begin",
        f"      idx = {chk_pkg_name(c)}::{t}_chk_index(ids[i]);", "      if (idx < 0) begin",
        f"        `uvm_error(\"{c.TAG}_VIP_CFG\", $sformatf(\"disable_check: unknown check ID %s\", ids[i]))",
        "      end else begin", "        cfg.vif.chk_en[idx] = 1'b0;", "      end", "    end", "  endfunction", "",
        "endclass", ""])


def seq_names(c: Ctx) -> list[tuple[str, str]]:
    names: dict[str, str] = {}
    for s in c.cfg["sequences"]:
        names.setdefault(s["name"], s["id"])
    for cp in c.cfg["caps"]:
        names.setdefault(cp["sequence"], cp["id"])
    base = f"{c.tag}_base_seq"
    return [(n, i) for n, i in names.items() if n != base]


def gen_base_seq(c: Ctx) -> str:
    t = c.tag
    return "\n".join([
        c.hdr(f"Base sequence of the {t} VIP: sends a number of random items."),
        f"class {t}_base_seq extends uvm_sequence #({t}_item);", "",
        cmt("Number of items the sequence sends.", 2), "  rand int unsigned num_items = 1;", "",
        "  constraint c_num_items { num_items inside {[1:64]}; }", "",
        f"  `uvm_object_utils({t}_base_seq)", "",
        f"  function new(string name = \"{t}_base_seq\");", "    super.new(name);", "  endfunction", "",
        "  virtual task body();", "    repeat (num_items) begin", f"      {t}_item item = {t}_item::type_id::create(\"item\");",
        "      start_item(item);", "      if (!item.randomize()) begin",
        f"        `uvm_error(\"{c.TAG}_VIP_SEQ\", \"randomization of the item failed\")", "      end",
        "      finish_item(item);", "    end", "  endtask", "", "endclass", ""])


def gen_seq(c: Ctx, name: str, sid: str) -> str:
    t = c.tag
    purpose = next((s["purpose"] for s in c.cfg["sequences"] if s["name"] == name),
                   next((cp["capability"] for cp in c.cfg["caps"] if cp["sequence"] == name), name))
    return "\n".join([
        c.hdr(f"Sequence {name}: {purpose}."),
        f"class {name} extends {t}_base_seq;", "",
        f"  `uvm_object_utils({name})", "",
        f"  function new(string name = \"{name}\");", "    super.new(name);", "  endfunction", "",
        "  virtual task body();",
        cmt(f"VIP_TODO({sid}): constrain the items so they exercise: {purpose}. Use item fields and cfg knobs; "
            f"no hard-coded protocol constants (VP-09).", 4),
        f"    `uvm_warning(\"{c.TAG}_VIP_SEQ\", \"VIP_TODO {name} is not implemented; sending default items\")",
        "    super.body();", "  endtask", "", "endclass", ""])


def gen_pkg(c: Ctx, seqs: list[tuple[str, str]]) -> str:
    t = c.tag
    params = ", ".join(f".{p['name']}(`{p['macro']})" for p in c.cfg["parameters"])
    out = [c.hdr(f"Package of the {t} VIP. Compile after uvm_pkg and vlsit_vip_base_pkg. "
                 f"spec_rev = {c.cfg['spec_rev']}; VIP version {c.cfg['version']}."),
           "`timescale 1ns/1ps", "", '`include "uvm_macros.svh"', f'`include "{t}_vip_defines.svh"', "",
           f"package {t}_vip_pkg;", "", "  import uvm_pkg::*;", "  import vlsit_vip_base_pkg::*;",
           f"  import {chk_pkg_name(c)}::*;", "",
           cmt("spec_rev: the standard revision this VIP implements (VFIL-06, VAPI-07).", 2),
           f"  localparam string {c.TAG}_VIP_SPEC_REV_STR = `{c.TAG}_VIP_SPEC_REV;",
           f"  localparam string {c.TAG}_VIP_VERSION = \"{c.cfg['version']}\";", "",
           cmt("Virtual interface type bound to the parameter macros (VIFC-01).", 2),
           f"  typedef virtual {t}_if #({params}) {t}_vif_t;" if params else f"  typedef virtual {t}_if {t}_vif_t;", "",
           f'  `include "{t}_item.sv"', f'  `include "{t}_agent_cfg.sv"', f'  `include "{t}_sequencer.sv"',
           f'  `include "{t}_monitor.sv"', f'  `include "{t}_driver_host.sv"', f'  `include "{t}_driver_device.sv"',
           f'  `include "{t}_agent_cov.sv"', f'  `include "{t}_agent.sv"', f'  `include "seq_lib/{t}_seq_list.sv"', "",
           "endpackage", ""]
    return "\n".join(out)


def gen_seq_list(c: Ctx, seqs: list[tuple[str, str]]) -> str:
    out = [c.hdr(f"Includes every sequence of the {c.tag} VIP (included inside the package).")]
    out.append(f'`include "seq_lib/{c.tag}_base_seq.sv"')
    out += [f'`include "seq_lib/{n}.sv"' for n, _ in seqs]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# qual, example, docs
# --------------------------------------------------------------------------

def trace_doc(c: Ctx, t: dict) -> str:
    if t["kind"] == "neg":
        inj = next((i for i in c.cfg["injections"] if i["requirement"] == t["req_id"]), None)
        return (f"Produce exactly one violation for {t['check']}"
                + (f" with {inj['id']}: {inj['violation']}." if inj else ".")
                + " Nothing else may violate the protocol.")
    if t["kind"] == "pos":
        return f"Drive legal traffic that reaches the valid boundary of {t['check']}, so its antecedent is true and the property holds."
    return f"Show the capability of {t['req_id']}: generate or present it so the VIP monitor reports it."


def gen_counterpart(c: Ctx) -> str:
    t = c.tag
    out = [c.hdr(f"Independent counterpart of the {t} VIP for qualification (VQUA-03, QP-01). It must not "
                 f"share checker code with the VIP. It drives valid and invalid traffic cycle by cycle."),
           f"class {t}_counterpart extends uvm_object;", "", f"  {t}_vif_t vif;", "",
           f"  `uvm_object_utils({t}_counterpart)", "",
           f"  function new(string name = \"{t}_counterpart\");", "    super.new(name);", "  endfunction", "",
           "  // Waits for n clocks of the monitor clocking block.", "  task wait_cycles(int unsigned n);",
           "    repeat (n) begin", "      @(vif.mon_cb);", "    end", "  endtask", "",
           cmt("One stimulus task per qualification trace. Each stub fails until it is implemented. Write the "
               "stimulus from the specification, not from the VIP checkers (VQUA-03).", 2), ""]
    for tr in c.cfg["tests"]:
        out += [cmt(f"VIP_TODO({tr['name']}): {trace_doc(c, tr)}", 2),
                f"  task {tr['name']}_stim();",
                f"    `uvm_error(\"VLSIT_VIP_QUAL\", \"VIP_TODO {tr['name']} stimulus is not implemented\")",
                "  endtask", ""]
    out += ["endclass", ""]
    return "\n".join(out)


def gen_qual_pkg(c: Ctx, tests: list[dict]) -> str:
    t = c.tag
    out = [c.hdr(f"Qualification package of the {t} VIP: counterpart, base test, and one test per trace."),
           "`timescale 1ns/1ps", "", '`include "uvm_macros.svh"', "", f"package {t}_qual_pkg;", "",
           "  import uvm_pkg::*;", "  import vlsit_vip_base_pkg::*;", f"  import {t}_vip_pkg::*;", "",
           f'  `include "{t}_counterpart.sv"', f'  `include "{t}_qual_test_base.sv"']
    out += [f'  `include "tests/{x["name"]}.sv"' for x in tests]
    out += ["", "endpackage", ""]
    return "\n".join(out)


def gen_qual_base(c: Ctx) -> str:
    t = c.tag
    return "\n".join([
        c.hdr(f"Base test of the {t} qualification environment: a passive VIP agent under qualification and "
              f"the independent counterpart on the same interface."),
        f"class {t}_qual_test_base extends vlsit_vip_qual_test_base;", "",
        f"  {t}_agent_cfg    vip_cfg;", f"  {t}_agent        vip_agent;", f"  {t}_counterpart  counterpart;", "",
        f"  `uvm_component_utils({t}_qual_test_base)", "",
        "  function new(string name, uvm_component parent);", "    super.new(name, parent);", "  endfunction", "",
        cmt("Tests override this hook to select the VIP role under qualification (default: passive monitor).", 2),
        f"  virtual function void configure_vip({t}_agent_cfg c);", "    c.is_active = 1'b0;", "  endfunction", "",
        "  virtual function void build_phase(uvm_phase phase);", "    super.build_phase(phase);",
        f"    vip_cfg = {t}_agent_cfg::type_id::create(\"vip_cfg\");",
        f"    counterpart = {t}_counterpart::type_id::create(\"counterpart\");",
        f"    if (!uvm_config_db #({t}_vif_t)::get(this, \"\", \"vif\", vip_cfg.vif)) begin",
        f"      `uvm_fatal(\"{c.TAG}_VIP_QUAL\", \"virtual interface vif not found in uvm_config_db\")", "    end",
        "    counterpart.vif = vip_cfg.vif;", "    configure_vip(vip_cfg);",
        f"    uvm_config_db #({t}_agent_cfg)::set(this, \"vip_agent\", \"cfg\", vip_cfg);",
        f"    vip_agent = {t}_agent::type_id::create(\"vip_agent\", this);", "  endfunction", "", "endclass", ""])


def gen_qual_test(c: Ctx, t: dict) -> str:
    name, kind, chk = t["name"], t["kind"], t["check"]
    body = []
    if kind == "neg":
        body += [f"    m_catcher.expect_error(\"{chk}\", 1, 1);", "    m_catcher.start_window();"]
    body += [f"    counterpart.{name}_stim();", "    counterpart.wait_cycles(4);"]
    if kind == "neg":
        body += ["    m_catcher.end_window();"]
    return "\n".join([
        c.hdr(f"Qualification test {name}: {trace_doc(c, t)}"),
        f"class {name} extends {c.tag}_qual_test_base;", "", f"  `uvm_component_utils({name})", "",
        "  function new(string name, uvm_component parent);", "    super.new(name, parent);", "  endfunction", "",
        "  virtual task run_phase(uvm_phase phase);", f"    phase.raise_objection(this, \"{name}\");", *body,
        f"    phase.drop_objection(this, \"{name}\");", "  endtask", "", "endclass", ""])


def gen_qual_top(c: Ctx) -> str:
    t = c.tag
    params = ", ".join(f".{p['name']}(`{p['macro']})" for p in c.cfg["parameters"])
    return "\n".join([
        c.hdr(f"Qualification testbench top of the {t} VIP: clock, reset, interface, and the test selected "
              f"with +UVM_TESTNAME."),
        "`timescale 1ns/1ps", "", f'`include "{t}_vip_defines.svh"', "", f"module {t}_qual_tb_top;", "", "  import uvm_pkg::*;", f"  import {t}_vip_pkg::*;",
        f"  import {t}_qual_pkg::*;", "", f"  logic {c.clk};", f"  logic {c.rst};", "",
        cmt("Clock generation is the only place where a delay is allowed (VP-08).", 2),
        f"  initial {c.clk} = 1'b0;", f"  always #5 {c.clk} = ~{c.clk};", "",
        "  initial begin", f"    {c.rst} = 1'b{'0' if c.cfg['clock']['reset_active_low'] else '1'};",
        f"    repeat (5) @(posedge {c.clk});", f"    {c.rst} <= 1'b{'1' if c.cfg['clock']['reset_active_low'] else '0'};",
        "  end", "", f"  {t}_if #({params}) u_if (.{c.clk}({c.clk}), .{c.rst}({c.rst}));" if params else
        f"  {t}_if u_if (.{c.clk}({c.clk}), .{c.rst}({c.rst}));", "",
        "  initial begin", f"    uvm_config_db #({t}_vif_t)::set(null, \"uvm_test_top\", \"vif\", u_if);",
        "    run_test();", "  end", "", "endmodule", ""])


def gen_quickstart(c: Ctx) -> str:
    t = c.tag
    return "\n".join([
        c.hdr(f"Quickstart of the {t} VIP: a host and a device of this VIP on one interface (UC-08)."),
        "`timescale 1ns/1ps", "", '`include "uvm_macros.svh"', "", f"package {t}_quickstart_pkg;", "",
        "  import uvm_pkg::*;", "  import vlsit_vip_base_pkg::*;", f"  import {t}_vip_pkg::*;", "",
        f"  class {t}_quickstart_test extends uvm_test;", "",
        f"    {t}_agent_cfg host_cfg;", f"    {t}_agent_cfg device_cfg;", f"    {t}_agent     host;",
        f"    {t}_agent     device;", "", f"    `uvm_component_utils({t}_quickstart_test)", "",
        "    function new(string name, uvm_component parent);", "      super.new(name, parent);", "    endfunction", "",
        "    virtual function void build_phase(uvm_phase phase);", "      super.build_phase(phase);",
        f"      host_cfg   = {t}_agent_cfg::type_id::create(\"host_cfg\");",
        f"      device_cfg = {t}_agent_cfg::type_id::create(\"device_cfg\");",
        f"      if (!uvm_config_db #({t}_vif_t)::get(this, \"\", \"vif\", host_cfg.vif)) begin",
        f"        `uvm_fatal(\"{c.TAG}_VIP_CFG\", \"virtual interface vif not found in uvm_config_db\")", "      end",
        "      device_cfg.vif     = host_cfg.vif;", "      host_cfg.if_mode   = VIP_HOST;",
        "      device_cfg.if_mode = VIP_DEVICE;",
        f"      uvm_config_db #({t}_agent_cfg)::set(this, \"host\", \"cfg\", host_cfg);",
        f"      uvm_config_db #({t}_agent_cfg)::set(this, \"device\", \"cfg\", device_cfg);",
        f"      host   = {t}_agent::type_id::create(\"host\", this);",
        f"      device = {t}_agent::type_id::create(\"device\", this);", "    endfunction", "",
        "    virtual task run_phase(uvm_phase phase);", f"      {t}_base_seq seq = {t}_base_seq::type_id::create(\"seq\");",
        "      phase.raise_objection(this, \"quickstart\");", "      seq.num_items = 16;", "      seq.start(host.sequencer);",
        "      phase.drop_objection(this, \"quickstart\");", "    endtask", "", "  endclass", "", "endpackage", ""])


def gen_example_top(c: Ctx) -> str:
    t = c.tag
    params = ", ".join(f".{p['name']}(`{p['macro']})" for p in c.cfg["parameters"])
    return "\n".join([
        c.hdr(f"Example top of the {t} VIP: clock, reset, interface, and the quickstart test."),
        "`timescale 1ns/1ps", "", f'`include "{t}_vip_defines.svh"', "", f"module {t}_example_top;", "", "  import uvm_pkg::*;", f"  import {t}_vip_pkg::*;",
        f"  import {t}_quickstart_pkg::*;", "", f"  logic {c.clk};", f"  logic {c.rst};", "",
        cmt("Clock generation is the only place where a delay is allowed (VP-08).", 2),
        f"  initial {c.clk} = 1'b0;", f"  always #5 {c.clk} = ~{c.clk};", "",
        "  initial begin", f"    {c.rst} = 1'b{'0' if c.cfg['clock']['reset_active_low'] else '1'};",
        f"    repeat (5) @(posedge {c.clk});", f"    {c.rst} <= 1'b{'1' if c.cfg['clock']['reset_active_low'] else '0'};",
        "  end", "", f"  {t}_if #({params}) u_if (.{c.clk}({c.clk}), .{c.rst}({c.rst}));" if params else
        f"  {t}_if u_if (.{c.clk}({c.clk}), .{c.rst}({c.rst}));", "",
        "  initial begin", f"    uvm_config_db #({t}_vif_t)::set(null, \"uvm_test_top\", \"vif\", u_if);",
        f"    run_test(\"{t}_quickstart_test\");", "  end", "", "endmodule", ""])


def gen_filelists(c: Ctx, tests: list[dict]) -> dict[str, str]:
    t = c.tag
    hdr = ["// Run the simulator from the VIP root directory. Paths are relative to it.", ""]
    inc = ["+incdir+base", "+incdir+rtl_if", "+incdir+uvm", "+incdir+uvm/seq_lib", "+incdir+qual",
           "+incdir+qual/tests", "+incdir+example", ""]
    core = ["base/vlsit_vip_base_pkg.sv", f"rtl_if/{t}_chk_pkg.sv", f"rtl_if/{t}_checker.sv", f"rtl_if/{t}_if.sv",
            f"uvm/{t}_vip_pkg.sv"]
    full = hdr + inc + ["// Define VLSIT_VIP_UVM so the checker reports through UVM.", "+define+VLSIT_VIP_UVM", ""] + core + [
        "", "// Quickstart", f"example/{t}_quickstart_pkg.sv", f"example/{t}_example_top.sv", "",
        "// Qualification", f"qual/{t}_qual_pkg.sv", f"qual/{t}_qual_tb_top.sv", ""]
    lint = hdr + ["+incdir+base", "+incdir+rtl_if", "",
                  "// Interface and checker only: no UVM needed (VIFC-08).",
                  f"rtl_if/{t}_chk_pkg.sv", f"rtl_if/{t}_checker.sv", f"rtl_if/{t}_if.sv", ""]
    return {f"filelist/{t}_vip.f": "\n".join(full), f"filelist/{t}_vip_lint.f": "\n".join(lint)}


def gen_readme(c: Ctx) -> str:
    cfg = c.cfg
    t = c.tag
    L = [f"# {cfg['vip_name']}: user guide", "",
         f"Verification IP for {cfg['spec_rev']}, profile {cfg['profile']}. VIP version {cfg['version']}.",
         "Generated skeleton: the sections marked **TODO** are completed in the release stage.", "",
         "## 1. Use it in three steps", "",
         "```systemverilog", f"import {t}_vip_pkg::*;", "",
         f"{t}_agent_cfg cfg = {t}_agent_cfg::type_id::create(\"cfg\");   // 1. create the cfg",
         "cfg.vif = vif;                                                 //    and set the interface",
         f"uvm_config_db #({t}_agent_cfg)::set(this, \"agent\", \"cfg\", cfg);",
         f"{t}_agent agent = {t}_agent::type_id::create(\"agent\", this);  // 2. create the agent",
         f"{t}_base_seq seq = {t}_base_seq::type_id::create(\"seq\");      // 3. start a sequence",
         "seq.start(agent.sequencer);", "```", "",
         "Set `cfg.if_mode = VIP_DEVICE` for a device, or `cfg.is_active = 0` for a passive monitor.", "",
         "## 2. Parameters bound at compile time", "", "| Macro | Parameter | Default | Legal values | Unit |", "|---|---|---|---|---|"]
    for p in cfg["parameters"]:
        L.append(f"| `{p['macro']}` | `{p['name']}` | {p['default']} | {p['legal']} | {p['unit']} |")
    L += ["", "Override with `+define+<MACRO>=<value>`. One compile supports one set of values.", "",
          "## 3. Configuration knobs", "", "Base knobs: `is_active`, `en_monitor`, `en_cov`, `if_mode`, `has_driver`, "
          "`ok_to_end_delay_ns`, `in_reset` (read only), `zero_delays`, `rec_on`.", "", "| Knob | Type | Default | Description |", "|---|---|---|---|"]
    for k in cfg["knobs"]:
        L.append(f"| `{k['name']}` | {k['type']} | {k['default']} | {k['description']} |")
    L += ["", "## 4. Checks", "",
          "Disable one check with `cfg.disable_check(\"<CHECK_ID>\", \"<reason>\")`. Disable all recommendations with "
          "`cfg.rec_on = 0`.", "", "| Check ID | Requirement | Strength | Role |", "|---|---|---|---|"]
    for ck in cfg["checks"]:
        L.append(f"| `{ck['id']}` | {ck['req_id']} | {ck['strength']} | {ck['role']} |")
    L += ["", "## 5. TODO for the release stage", "",
          "- TLM ports and `uvm_config_db` keys (agent cfg key `cfg`; interface key `vif` in the examples)",
          "- Factory-overridable classes", "- Interface requirements: clock and reset assumptions",
          "- Quickstart result and known limitations", ""]
    return "\n".join(L)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def build(cfg: dict, author: str, project: str, day: str) -> dict[str, str]:
    c = Ctx(cfg, author, project, day)
    t = c.tag
    seqs = seq_names(c)
    tests = cfg["tests"]
    files: dict[str, str] = {
        f"rtl_if/{t}_vip_defines.svh": gen_defines(c),
        f"rtl_if/{t}_chk_pkg.sv": gen_chk_pkg(c),
        f"rtl_if/{t}_checker.sv": gen_checker(c),
        f"rtl_if/{t}_if.sv": gen_if(c),
        f"uvm/{t}_vip_pkg.sv": gen_pkg(c, seqs),
        f"uvm/{t}_agent_cfg.sv": gen_cfg(c),
        f"uvm/{t}_item.sv": gen_item(c),
        f"uvm/{t}_monitor.sv": gen_monitor(c),
        f"uvm/{t}_driver_host.sv": gen_driver(c, True),
        f"uvm/{t}_driver_device.sv": gen_driver(c, False),
        f"uvm/{t}_sequencer.sv": gen_sequencer(c),
        f"uvm/{t}_agent_cov.sv": gen_cov(c),
        f"uvm/{t}_agent.sv": gen_agent(c),
        f"uvm/seq_lib/{t}_base_seq.sv": gen_base_seq(c),
        f"uvm/seq_lib/{t}_seq_list.sv": gen_seq_list(c, seqs),
        f"qual/{t}_counterpart.sv": gen_counterpart(c),
        f"qual/{t}_qual_test_base.sv": gen_qual_base(c),
        f"qual/{t}_qual_pkg.sv": gen_qual_pkg(c, tests),
        f"qual/{t}_qual_tb_top.sv": gen_qual_top(c),
        f"example/{t}_quickstart_pkg.sv": gen_quickstart(c),
        f"example/{t}_example_top.sv": gen_example_top(c),
        "doc/README.md": gen_readme(c),
        "spec/vip_config.json": json.dumps(cfg, indent=2) + "\n",
        "spec/vip_generation.json": json.dumps({"schema": "vlsit_vip_generation/1", "author": author, "project": project,
                                                "date": day, "version": cfg["version"], "profile": cfg["profile"]}, indent=2) + "\n",
    }
    for n, sid in seqs:
        files[f"uvm/seq_lib/{n}.sv"] = gen_seq(c, n, sid)
    for tst in tests:
        files[f"qual/tests/{tst['name']}.sv"] = gen_qual_test(c, tst)
    files.update(gen_filelists(c, tests))
    for p in sorted(BASE_DIR.iterdir()):
        text = p.read_text(encoding="utf-8").replace("<USER_NAME>", author)
        text = re.sub(r"Date         : \d{4}-\d{2}-\d{2}", f"Date         : {day}", text)
        files[f"base/{p.name}"] = text
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out-dir", required=True, help="VIP root directory to create (must not exist)")
    ap.add_argument("--author", required=True, help="human author for the file headers")
    ap.add_argument("--project", required=True)
    ap.add_argument("--requirements", help="requirements.csv to copy into spec/")
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()
    out = Path(args.out_dir)
    if out.exists():
        raise SystemExit(f"error: output directory exists and will not be overwritten: {out}")
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if cfg.get("schema") != "vlsit_vip_config/1":
        raise SystemExit("error: unsupported config schema")
    files = build(cfg, args.author, args.project, args.date)
    for rel, text in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text.replace("\t", "  "), encoding="utf-8", newline="\n")
    if args.requirements:
        (out / "spec").mkdir(exist_ok=True)
        (out / "spec" / "requirements.csv").write_bytes(Path(args.requirements).read_bytes())
    print(f"generated {len(files)} file(s) in {out}")
    print(f"  checks: {len(cfg['checks'])}, tests: {len(cfg['tests'])}, coverage items: {len(cfg['coverage'])}")
    print("  stubs carry VIP_TODO markers; run trace_lint.py --stage impl to list them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
