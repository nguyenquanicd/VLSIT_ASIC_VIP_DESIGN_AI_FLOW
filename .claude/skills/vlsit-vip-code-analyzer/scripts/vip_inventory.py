#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inventory of an existing SystemVerilog/UVM VIP source tree (read-only).

Scans .sv/.svh/.v/.vh files and records what a specification needs: design units, interface
signals, ports, parameters, clocking blocks, assertions (with their messages), covergroups,
UVM classes by role (agent, driver, monitor, sequencer, item, config, coverage, sequence,
test, ...), configuration fields, item fields, config_db keys, UVM message IDs, TODO markers,
and compile-time defines. The source tree is never modified.

The scan is lexical (regular expressions after comments are blanked). It works without
compiling the code and without its dependencies, and it can miss constructs that are produced
by macros or generate blocks. Every fact carries file and line so it can be checked.

Usage:
    python vip_inventory.py scan DIR --out inventory.json [--max-files N]
    python vip_inventory.py show inventory.json KIND [--grep TEXT] [--limit N]
    python vip_inventory.py summary inventory.json
KIND: files, units, classes, interfaces, signals, parameters, assertions, covergroups, messages,
      config_db, config_fields, item_fields, todos, defines
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", "obj_dir", "work", "sim_build", "build", ".cache"}
EXTS = {".sv", ".svh", ".v", ".vh"}
MAX_BYTES = 1_500_000

UVM_BASE_KIND = {
    "uvm_agent": "agent", "uvm_driver": "driver", "uvm_monitor": "monitor", "uvm_sequencer": "sequencer",
    "uvm_push_sequencer": "sequencer", "uvm_sequence_item": "item", "uvm_transaction": "item",
    "uvm_sequence": "sequence", "uvm_env": "env", "uvm_scoreboard": "scoreboard", "uvm_subscriber": "coverage",
    "uvm_test": "test", "uvm_reg_adapter": "reg_adapter", "uvm_reg_block": "reg_block", "uvm_component": "component",
    "uvm_object": "object",
}
SEVERITIES = ("info", "warning", "error", "fatal")


# ---------------------------------------------------------------- lexical helpers

def blank_comments(text: str) -> str:
    """Replace comments by spaces (newlines kept) so line numbers stay valid; strings are preserved."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_close(text: str, open_idx: int, op: str = "(", cl: str = ")") -> int:
    depth, i, n = 0, open_idx, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif c == op:
            depth += 1
        elif c == cl:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def squash(s: str, limit: int = 400) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= limit else s[:limit - 1] + "…"


def split_top(s: str, sep: str = ",") -> list[str]:
    parts, depth, cur, i = [], 0, [], 0
    while i < len(s):
        c = s[i]
        if c == '"':
            j = i + 1
            while j < len(s) and s[j] != '"':
                j += 2 if s[j] == "\\" else 1
            cur.append(s[i:j + 1])
            i = j + 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == sep and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def width_of(rng: str | None) -> str:
    """Width of a packed range like [31:0] as a number when numeric, else the expression text."""
    if not rng:
        return "1"
    m = re.fullmatch(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", rng.strip())
    if m:
        return str(abs(int(m.group(1)) - int(m.group(2))) + 1)
    m = re.fullmatch(r"\[\s*([^:\]]+?)\s*-\s*1\s*:\s*0\s*\]", rng.strip())
    if m:
        return m.group(1)
    return squash(rng, 80)


# ---------------------------------------------------------------- per-file scan

class FileScan:
    def __init__(self, root: Path, path: Path, raw: str):
        self.rel = path.relative_to(root).as_posix()
        self.raw = raw
        self.text = blank_comments(raw)
        self.nl = [m.start() for m in re.finditer("\n", self.text)]

    def line(self, pos: int) -> int:
        return bisect.bisect_right(self.nl, pos - 1) + 1


UNIT_RE = re.compile(r"^[ \t]*(?:(virtual)\s+)?(interface|module|package|program|checker)\s+(?:automatic\s+|static\s+)?([A-Za-z_]\w*)", re.M)
CLASS_RE = re.compile(r"^[ \t]*(?:(virtual)\s+)?class\s+(?:(?:static|automatic)\s+)?([A-Za-z_]\w*)\s*(#\s*\()?", re.M)
END_OF = {"interface": "endinterface", "module": "endmodule", "package": "endpackage", "program": "endprogram", "checker": "endchecker"}


def parse_params(header: str) -> list[dict]:
    out = []
    for part in split_top(header):
        m = re.match(r"(?:(parameter|localparam)\s+)?(?:(?:type|int|integer|string|bit|logic|real|byte|shortint|longint|unsigned|signed)\s*)*(?:\[[^\]]*\]\s*)*([A-Za-z_]\w*)\s*=\s*(.+)$", part.strip(), re.S)
        if m and (m.group(1) or "parameter" in part or "=" in part):
            out.append({"kind": m.group(1) or "parameter", "name": m.group(2), "default": squash(m.group(3), 120)})
    return out


def scan_units(fs: FileScan, inv: dict) -> None:
    t = fs.text
    for m in UNIT_RE.finditer(t):
        kind, name = m.group(2), m.group(3)
        start = m.end()
        end_kw = END_OF[kind]
        e = re.search(r"\b" + end_kw + r"\b", t[start:])
        end = start + e.start() if e else len(t)
        header_end = t.find(";", start)
        header = t[start:header_end if header_end >= 0 else start]
        params, ports = [], []
        ph = re.match(r"\s*#\s*\(", header)
        if ph:
            close = match_close(t, start + ph.end() - 1)
            params = parse_params(t[start + ph.end():close]) if close > 0 else []
            rest_start = close + 1 if close > 0 else start
        else:
            rest_start = start
        pm = re.match(r"\s*\(", t[rest_start:])
        if pm and header_end and header_end > rest_start:
            close = match_close(t, rest_start + pm.end() - 1)
            if close > 0:
                for part in split_top(t[rest_start + pm.end():close]):
                    q = re.match(r"(input|output|inout)\s+(?:(?:var|wire|logic|reg|bit|tri)\s+)*(?:(?:signed|unsigned)\s+)?(\[[^\]]+\]\s*)?([A-Za-z_]\w*)", part.strip())
                    if q:
                        ports.append({"dir": q.group(1), "name": q.group(3), "width": width_of(q.group(2))})
        body = t[start:end]
        unit = {"kind": kind, "name": name, "file": fs.rel, "line": fs.line(m.start()), "params": params, "ports": ports}
        inv["units"].append(unit)
        if kind in ("interface", "checker", "module"):
            scan_unit_body(fs, inv, unit, body, start)


def strip_blocks(body: str, pairs: list[tuple[str, str]]) -> str:
    for a, b in pairs:
        body = re.sub(r"\b" + a + r"\b.*?\b" + b + r"\b", lambda m: re.sub(r"[^\n]", " ", m.group(0)), body, flags=re.S)
    return body


def scan_unit_body(fs: FileScan, inv: dict, unit: dict, body: str, base: int) -> None:
    kind, name = unit["kind"], unit["name"]
    decl_body = strip_blocks(body, [("clocking", "endclocking"), ("task", "endtask"), ("function", "endfunction"),
                                    ("property", "endproperty"), ("sequence", "endsequence"), ("class", "endclass"),
                                    ("covergroup", "endgroup"), ("generate", "endgenerate")])
    if kind == "interface":
        sigs = []
        for m in re.finditer(r"^[ \t]*(?:(?:rand|var|const)\s+)?(logic|wire|reg|bit|tri|wor|wand|byte|int|integer|shortint)\s*(?:signed\s+|unsigned\s+)?((?:\[[^\]]+\]\s*)+)?([A-Za-z_]\w*(?:\s*\[[^\]]*\])?(?:\s*(?:=[^,;]*)?\s*,\s*[A-Za-z_]\w*(?:\s*\[[^\]]*\])?(?:\s*=[^,;]*)?)*)\s*(?:=[^;]*)?;", decl_body, re.M):
            rng = (m.group(2) or "").strip()
            first = re.match(r"\[[^\]]+\]", rng)
            for nm in re.findall(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*(?:=[^,;]*)?(?:,|$)", m.group(3) + ","):
                if nm not in ("logic", "wire", "reg", "bit"):
                    sigs.append({"name": nm, "type": m.group(1), "width": width_of(first.group(0) if first else None),
                                 "line": fs.line(base + m.start()), "interface": name})
        inv["signals"].extend(dict(s, file=fs.rel) for s in sigs)
        clk = []
        for m in re.finditer(r"\bclocking\s+([A-Za-z_]\w*)\s*@\s*\(([^)]*)\)\s*;(.*?)\bendclocking\b", body, re.S):
            dirs: dict[str, list[str]] = {"input": [], "output": [], "inout": []}
            for d in re.finditer(r"\b(input|output|inout)\b([^;]*);", m.group(3)):
                items = [x for x in re.findall(r"[A-Za-z_]\w*", re.sub(r"#\s*\w+", " ", d.group(2))) if x not in ("posedge", "negedge")]
                dirs[d.group(1)].extend(items)
            clk.append({"name": m.group(1), "event": squash(m.group(2), 60), **dirs})
        unit["clocking"] = clk
        unit["modports"] = [m.group(1) for m in re.finditer(r"\bmodport\s+([A-Za-z_]\w*)", body)]
        for p in unit["params"]:
            inv["parameters"].append(dict(p, scope=name, file=fs.rel, line=unit["line"]))
        for m in re.finditer(r"\b(parameter|localparam)\s+(?:(?:type|int|integer|string|bit|logic|real)\s+)?(?:\[[^\]]*\]\s*)?([A-Za-z_]\w*)\s*=\s*([^;,]+)", decl_body):
            inv["parameters"].append({"kind": m.group(1), "name": m.group(2), "default": squash(m.group(3), 120), "scope": name,
                                      "file": fs.rel, "line": fs.line(base + m.start())})
        unit["signals"] = [s["name"] for s in sigs]
    scan_assertions(fs, inv, name, body, base)
    scan_covergroups(fs, inv, name, body, base)


MSG_RE = re.compile(r"`uvm_(error|warning|fatal)\s*\(\s*(\"[^\"]*\"|[`\w]+)\s*,\s*(\"(?:[^\"\\]|\\.)*\"|[^;]*)|uvm_report_(error|warning|fatal)\s*\(\s*(\"[^\"]*\"|\w+)\s*,\s*(\"(?:[^\"\\]|\\.)*\"|[^;]*)|\$(error|warning|fatal)\s*\(\s*(\"(?:[^\"\\]|\\.)*\")?")


def scan_assertions(fs: FileScan, inv: dict, scope: str, body: str, base: int) -> None:
    t = fs.text
    props = {}
    for m in re.finditer(r"\bproperty\s+([A-Za-z_]\w*)\s*(?:\([^)]*\))?\s*;(.*?)\bendproperty\b", body, re.S):
        props[m.group(1)] = squash(m.group(2), 500)
    for m in re.finditer(r"(?:\b([A-Za-z_]\w*)\s*:\s*)?\b(assert|assume|cover)\s+property\s*\(", body):
        op = m.end() - 1
        close = match_close(body, op)
        if close < 0:
            continue
        prop = squash(body[op + 1:close], 500)
        action = body[close + 1:close + 500]
        sev, mid, msg = "", "", ""
        a = re.match(r"\s*(?:else\s+(.*?)(?:;|$))?", action, re.S)
        if a and a.group(1):
            mm = MSG_RE.search(a.group(1))
            if mm:
                sev = (mm.group(1) or mm.group(4) or mm.group(7) or "").lower()
                mid = (mm.group(2) or mm.group(5) or "").strip('"')
                msg = squash((mm.group(3) or mm.group(6) or mm.group(8) or "").strip('"'), 160)
        expanded = props.get(re.match(r"\s*([A-Za-z_]\w*)\s*(?:\(|$)", prop).group(1)) if re.match(r"\s*([A-Za-z_]\w*)\s*(?:\(|$)", prop) else None
        inv["assertions"].append({"label": m.group(1) or "", "directive": m.group(2), "property": prop,
                                  "expanded": expanded or "", "severity": sev, "message_id": mid, "message": msg,
                                  "scope": scope, "file": fs.rel, "line": fs.line(base + m.start()), "form": "sva"})
    for m in re.finditer(r"`VLSIT_VIP_CHK_(ERR|REC)\s*\(", body):
        op = m.end() - 1
        close = match_close(body, op)
        args = split_top(body[op + 1:close]) if close > 0 else []
        if len(args) >= 6:
            inv["assertions"].append({"label": args[0], "directive": "assert", "property": squash(args[4], 500),
                                      "ante": squash(args[5], 300), "expanded": "", "severity": "error" if m.group(1) == "ERR" else "warning",
                                      "message_id": args[0], "message": squash(args[3].strip('"'), 160), "role": args[1],
                                      "req_id": args[2].strip('"'), "scope": scope, "file": fs.rel,
                                      "line": fs.line(base + m.start()), "form": "vlsit_macro"})
    for m in re.finditer(r"`VLSIT_VIP_CHK_TODO\s*\(\s*([A-Za-z_]\w*)", body):
        inv["assertions"].append({"label": m.group(1), "directive": "stub", "property": "", "expanded": "", "severity": "",
                                  "message_id": "", "message": "", "scope": scope, "file": fs.rel,
                                  "line": fs.line(base + m.start()), "form": "vlsit_stub"})
    for m in re.finditer(r"`([A-Z][A-Z0-9_]*(?:ASSERT|ASSUME|COVER)[A-Z0-9_]*)\s*\(", body):
        op = m.end() - 1
        close = match_close(body, op)
        if close < 0:
            continue
        args = split_top(body[op + 1:close])
        inv["assertions"].append({"label": args[0] if args else "", "directive": "assert" if "ASSERT" in m.group(1) else
                                  ("assume" if "ASSUME" in m.group(1) else "cover"), "property": squash(" , ".join(args[1:]), 500),
                                  "expanded": "", "severity": "", "message_id": "", "message": "", "macro": m.group(1),
                                  "args": [squash(a, 200) for a in args], "scope": scope, "file": fs.rel,
                                  "line": fs.line(base + m.start()), "form": "macro"})


def scan_covergroups(fs: FileScan, inv: dict, scope: str, body: str, base: int) -> None:
    for m in re.finditer(r"\bcovergroup\s+([A-Za-z_]\w*)(.*?)\bendgroup\b", body, re.S):
        cps = re.findall(r"\b([A-Za-z_]\w*)\s*:\s*coverpoint\s+([^{;]+?)\s*(?:iff|\{|;)", m.group(2))
        crosses = re.findall(r"\b([A-Za-z_]\w*)\s*:\s*cross\s+([^{;]+?)\s*(?:iff|\{|;)", m.group(2))
        inv["covergroups"].append({"name": m.group(1), "scope": scope, "file": fs.rel, "line": fs.line(base + m.start()),
                                   "coverpoints": [{"name": a, "expr": squash(b, 80)} for a, b in cps],
                                   "crosses": [{"name": a, "items": squash(b, 80)} for a, b in crosses]})


def scan_classes(fs: FileScan, inv: dict) -> None:
    t = fs.text
    for m in CLASS_RE.finditer(t):
        name = m.group(2)
        pos = m.end()
        if m.group(3):
            close = match_close(t, m.end() - 1)
            pos = close + 1 if close > 0 else pos
        hm = re.match(r"\s*(?:extends\s+([A-Za-z_]\w*)(?:\s*#\s*\()?)?", t[pos:])
        base = hm.group(1) if hm else None
        e = re.search(r"\bendclass\b", t[pos:])
        end = pos + e.start() if e else len(t)
        body = t[pos:end]
        cls = {"name": name, "base": base or "", "file": fs.rel, "line": fs.line(m.start()), "virtual": bool(m.group(1)),
               "has_covergroup": bool(re.search(r"\bcovergroup\b", body)), "tasks": re.findall(r"\btask\s+(?:automatic\s+)?(?:\w+::)?([A-Za-z_]\w*)", body)[:30],
               "functions": re.findall(r"\bfunction\s+(?:automatic\s+)?(?:[\w:#()\[\]]+\s+)?(?:\w+::)?([A-Za-z_]\w*)\s*\(", body)[:30]}
        inv["classes"].append(cls)
        fields_body = strip_blocks(body, [("function", "endfunction"), ("task", "endtask"), ("constraint", r"\}"), ("covergroup", "endgroup")])
        fields = []
        for fm in re.finditer(r"^[ \t]*(?:(?:local|protected|static|const)\s+)*(rand|randc)?\s*((?:bit|logic|int|integer|byte|shortint|longint|string|real|time)(?:\s+(?:unsigned|signed))?|[A-Za-z_]\w*_e|[A-Za-z_]\w*_t|[A-Za-z_]\w*_type|[A-Za-z_]\w*_enum)\s*((?:\[[^\]]+\]\s*)+)?([A-Za-z_]\w*)(?:\s*\[[^\]]*\])?\s*(?:=\s*([^;]+))?;", fields_body, re.M):
            fields.append({"name": fm.group(4), "type": squash(fm.group(2) + (" " + fm.group(3).strip() if fm.group(3) else ""), 60),
                           "rand": fm.group(1) or "none", "default": squash(fm.group(5) or "", 60), "line": fs.line(m.start() + (fm.start() if False else 0))})
        cls["fields"] = fields


def scan_misc(fs: FileScan, inv: dict) -> None:
    for m in re.finditer(r"typedef\s+(?:virtual\s+)?([A-Za-z_]\w*)\s*(?:#\s*\()?[^;]*?([A-Za-z_]\w*)\s*;", fs.text):
        if m.group(1) not in ("enum", "struct", "union", "class", "interface", "logic", "bit", "int", "byte", "string", "reg", "wire", "type"):
            inv["aliases"].append({"alias": m.group(2), "target": m.group(1), "file": fs.rel, "line": fs.line(m.start())})
    for m in MSG_RE.finditer(fs.text):
        sev = (m.group(1) or m.group(4) or m.group(7) or "")
        raw_id = (m.group(2) or m.group(5) or m.group(8) or "")
        inv["messages"].append({"severity": sev, "id": raw_id.strip('"'), "literal": raw_id.startswith('"'),
                                "file": fs.rel, "line": fs.line(m.start())})
    for m in re.finditer(r"`uvm_(info)\s*\(\s*(\"[^\"]*\"|[`\w]+)", fs.text):
        inv["messages"].append({"severity": "info", "id": m.group(2).strip('"'), "file": fs.rel, "line": fs.line(m.start())})
    for m in re.finditer(r"uvm_config_db\s*#\s*\(([^)]*(?:\([^)]*\))?[^)]*)\)\s*::\s*(set|get)\s*\(", fs.text):
        op = m.end() - 1
        close = match_close(fs.text, op)
        args = split_top(fs.text[op + 1:close]) if close > 0 else []
        inv["config_db"].append({"type": squash(m.group(1), 80), "op": m.group(2), "field": args[2].strip('"') if len(args) > 2 else "",
                                 "inst": args[1].strip('"') if len(args) > 1 else "", "file": fs.rel, "line": fs.line(m.start())})
    for m in re.finditer(r"\b(TODO|FIXME|XXX|HACK|BUG)\b[:\s]*([^\n]{0,100})", fs.raw):
        inv["todos"].append({"tag": m.group(1), "text": squash(m.group(2), 100), "file": fs.rel,
                             "line": fs.raw.count("\n", 0, m.start()) + 1})
    for m in re.finditer(r"`(ifdef|ifndef|elsif)\s+([A-Za-z_]\w*)", fs.text):
        inv["defines"].append({"name": m.group(2), "use": m.group(1), "file": fs.rel, "line": fs.line(m.start())})
    for m in re.finditer(r"`define\s+([A-Za-z_]\w*)", fs.text):
        inv["defines"].append({"name": m.group(1), "use": "define", "file": fs.rel, "line": fs.line(m.start())})
    for m in re.finditer(r"\brun_test\s*\(\s*\"([^\"]*)\"", fs.text):
        inv["run_test"].append({"test": m.group(1), "file": fs.rel, "line": fs.line(m.start())})


NAME_ROLES = [("scoreboard", "scoreboard"), ("sequencer", "sequencer"), ("agent", "agent"), ("driver", "driver"),
              ("monitor", "monitor"), ("coverage", "coverage"), ("_cov", "coverage"), ("seq_item", "item"), ("item", "item"),
              ("transaction", "item"), ("_trans", "item"), ("sequence", "sequence"), ("_seq", "sequence"), ("configuration", "config"),
              ("config", "config"), ("_cfg", "config"), ("test", "test"), ("env", "env"), ("adapter", "reg_adapter")]


def name_role(name: str) -> str:
    n = name.lower()
    return next((r for k, r in NAME_ROLES if k in n), "other")


def classify(inv: dict) -> None:
    by = {c["name"]: c for c in inv["classes"]}
    for a in inv.get("aliases", []):
        by.setdefault(a["alias"], by.get(a["target"], {"name": a["alias"], "base": a["target"]}))
    def kind_of(name: str, seen: set) -> str:
        if name in UVM_BASE_KIND:
            return UVM_BASE_KIND[name]
        c = by.get(name)
        if not c or name in seen:
            return "other"
        seen.add(name)
        return kind_of(c["base"], seen) if c["base"] else "other"
    for c in inv["classes"]:
        k = kind_of(c["base"], {c["name"]}) if c["base"] else "other"
        c["role_basis"] = "base"
        if k == "other":
            k = name_role(c["name"])
            c["role_basis"] = "name" if k != "other" else "unknown"
        if k in ("object", "component") or k == "other":
            n = c["name"].lower()
            if re.search(r"(cfg|config|configuration)", n):
                k = "config" if k != "component" else k
            elif k == "component" and c["has_covergroup"]:
                k = "coverage"
        if c["has_covergroup"] and k in ("component", "other", "object"):
            k = "coverage"
        c["role"] = k


def scan_tree(root: Path, max_files: int) -> dict:
    inv = {"schema": "vlsit_vip_inventory/1", "root": str(root), "files": [], "units": [], "signals": [], "parameters": [],
           "assertions": [], "covergroups": [], "classes": [], "messages": [], "config_db": [], "todos": [], "defines": [],
           "run_test": [], "skipped": [], "meta": [], "aliases": []}
    files = []
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts[:-1]):
            continue
        if p.is_file() and p.suffix.lower() in EXTS:
            files.append(p)
        elif p.is_file() and p.name.lower() in ("makefile", "cmakelists.txt", "readme.md", "readme") and len(p.relative_to(root).parts) <= 3:
            inv["meta"].append(p.relative_to(root).as_posix())
        elif p.is_file() and p.suffix.lower() in (".f", ".core", ".vc") and len(p.relative_to(root).parts) <= 4:
            inv["meta"].append(p.relative_to(root).as_posix())
    for p in files[:max_files]:
        if p.stat().st_size > MAX_BYTES:
            inv["skipped"].append({"file": p.relative_to(root).as_posix(), "reason": "larger than 1.5 MB"})
            continue
        raw = p.read_text(encoding="utf-8", errors="replace")
        fs = FileScan(root, p, raw)
        inv["files"].append({"file": fs.rel, "lines": raw.count("\n") + 1})
        scan_units(fs, inv)
        scan_classes(fs, inv)
        scan_misc(fs, inv)
    if len(files) > max_files:
        inv["skipped"].append({"file": "(more files)", "reason": f"{len(files) - max_files} file(s) beyond --max-files"})
    classify(inv)
    return inv


def summary(inv: dict) -> str:
    roles: dict[str, int] = {}
    for c in inv["classes"]:
        roles[c["role"]] = roles.get(c["role"], 0) + 1
    ifs = [u for u in inv["units"] if u["kind"] == "interface"]
    lines = [f"root {inv['root']}", f"{len(inv['files'])} file(s), {sum(f['lines'] for f in inv['files'])} line(s)",
             f"units: " + ", ".join(f"{k} {sum(1 for u in inv['units'] if u['kind'] == k)}" for k in ("interface", "module", "package", "program", "checker") if any(u['kind'] == k for u in inv["units"])),
             f"classes {len(inv['classes'])}: " + ", ".join(f"{k} {v}" for k, v in sorted(roles.items(), key=lambda x: -x[1])),
             f"interfaces: " + ", ".join(f"{u['name']}({len(u.get('signals', []))} sig)" for u in ifs[:8]) + (" ..." if len(ifs) > 8 else ""),
             f"assertions {len(inv['assertions'])} (labeled {sum(1 for a in inv['assertions'] if a['label'])}, with message {sum(1 for a in inv['assertions'] if a['message_id'] or a['message'])}); "
             f"covergroups {len(inv['covergroups'])}; parameters {len(inv['parameters'])}; config_db keys {len({c['field'] for c in inv['config_db']})}; "
             f"message IDs {len({m['id'] for m in inv['messages']})}; TODO markers {len(inv['todos'])}"]
    if inv["skipped"]:
        lines.append(f"skipped: {len(inv['skipped'])} ({inv['skipped'][0]['reason']})")
    return "\n".join(lines)


def cmd_show(inv: dict, kind: str, grep: str | None, limit: int) -> int:
    if kind not in inv and kind + "s" in inv:
        kind += "s"  # singular form: assertion, class, signal, ...
    if kind == "class":
        kind = "classes"

    def rows():
        if kind == "files":
            return inv["files"]
        if kind == "config_fields":
            return [dict(f, cls=c["name"]) for c in inv["classes"] if c["role"] == "config" for f in c.get("fields", [])]
        if kind == "item_fields":
            return [dict(f, cls=c["name"]) for c in inv["classes"] if c["role"] == "item" for f in c.get("fields", [])]
        if kind == "interfaces":
            return [u for u in inv["units"] if u["kind"] == "interface"]
        if kind in inv:
            return inv[kind]
        raise SystemExit(f"error: unknown kind {kind}")
    out = [r for r in rows() if not grep or grep.lower() in json.dumps(r).lower()]
    for r in out[:limit]:
        keys = [k for k in r if k not in ("params", "ports", "clocking", "modports", "fields", "tasks", "functions", "signals", "args") or kind == "interfaces"]
        print("\t".join(f"{k}={squash(str(r[k]), 90)}" for k in keys if r[k] not in ("", [], None)))
    if len(out) > limit:
        print(f"... {len(out) - limit} more (raise --limit or use --grep)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("dir")
    s.add_argument("--out", required=True)
    s.add_argument("--max-files", type=int, default=3000)
    sh = sub.add_parser("show")
    sh.add_argument("inventory")
    sh.add_argument("kind")
    sh.add_argument("--grep")
    sh.add_argument("--limit", type=int, default=40)
    sm = sub.add_parser("summary")
    sm.add_argument("inventory")
    a = ap.parse_args()
    if a.cmd == "scan":
        out = Path(a.out)
        if out.exists():
            raise SystemExit(f"error: {out} exists and will not be overwritten")
        root = Path(a.dir).resolve()
        if not root.is_dir():
            raise SystemExit(f"error: not a directory: {root}")
        inv = scan_tree(root, a.max_files)
        out.write_text(json.dumps(inv, indent=1) + "\n", encoding="utf-8")
        print(summary(inv))
        print(f"inventory written to {out}")
        return 0
    inv = json.loads(Path(a.inventory).read_text(encoding="utf-8"))
    if a.cmd == "summary":
        print(summary(inv))
        return 0
    return cmd_show(inv, a.kind, a.grep, a.limit)


if __name__ == "__main__":
    sys.exit(main())
