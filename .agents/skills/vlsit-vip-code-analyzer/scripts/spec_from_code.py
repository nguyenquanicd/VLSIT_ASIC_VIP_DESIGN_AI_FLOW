#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Draft the as-built VIP specification of an existing VIP from its inventory.

The draft is written in the mandatory template format. Everything that can be read from the code
is filled: signals, parameters, clocks, item fields, configuration knobs, sequences as
capabilities, monitors, and every labeled assertion as a requirement with a check expression
when its property is a single-cycle implication. Because the code is not the standard, every
derived cell carries the word UNVERIFIED and a CODE:<file>:<line>:<label> pointer. Gate 1 refuses
a specification that still contains UNVERIFIED (vip gate G1), so each item has to be confirmed
against the standard, corrected, or removed first.

Commands:
    draft   INVENTORY --tag T --title "..." --standard "ID rev" --out SPEC.md [--interface NAME]
            [--item CLASS] [--cfg CLASS] [--report as_built_report.md]
    verify  SPEC --root DIR       check that every CODE: pointer still matches the source (drift)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402
import spec_scaffold as sc  # noqa: E402

UNV = "UNVERIFIED"
MASTER_HINT = re.compile(r"mst|master|host|drv|driver|tx|req|init|source|src", re.I)
SLAVE_HINT = re.compile(r"slv|slave|device|resp|target|sink|rx|dev", re.I)


def para(name: str) -> str:
    n = re.sub(r"[^A-Za-z0-9]+", "_", name).upper().strip("_")
    return n if n.startswith("PARA_") else f"PARA_{n}"


def map_idents(expr: str, pmap: dict[str, str]) -> str:
    return re.sub(r"[A-Za-z_]\w*", lambda m: pmap.get(m.group(0), m.group(0)), expr)


def tidy(expr: str) -> str:
    """Spec form of an expression: OR for ||, single spaces, no redundant outer parentheses."""
    e = re.sub(r"\s*\|\|\s*", " OR ", expr.strip())
    e = re.sub(r"\s+", " ", e)
    while e.startswith("(") and e.endswith(")") and balanced_inner(e):
        e = e[1:-1].strip()
    return e


def balanced_inner(e: str) -> bool:
    depth = 0
    for i, c in enumerate(e):
        depth += (c == "(") - (c == ")")
        if depth == 0 and i < len(e) - 1:
            return False
    return depth == 0


def pick_interface(inv: dict, name: str | None) -> dict:
    ifs = [u for u in inv["units"] if u["kind"] == "interface"]
    if name:
        for u in ifs:
            if u["name"] == name:
                return u
        raise SystemExit(f"error: no interface named {name}; found: {', '.join(u['name'] for u in ifs)}")
    cands = [u for u in ifs if "checker" not in u["name"].lower()] or ifs
    if not cands:
        raise SystemExit("error: the inventory has no interface")
    return max(cands, key=lambda u: len(u.get("signals", [])))


def role_of_cb(name: str) -> str:
    if SLAVE_HINT.search(name) and not MASTER_HINT.search(name):
        return "S"
    if MASTER_HINT.search(name) and not SLAVE_HINT.search(name):
        return "M"
    return ""


def split_property(prop: str) -> tuple[str, str, str] | None:
    """Return (antecedent, operator, consequent) of a single-cycle implication, else None."""
    p = re.sub(r"^\s*@\s*\([^)]*\)\s*", "", prop)
    p = re.sub(r"^\s*disable\s+iff\s*\((?:[^()]|\([^()]*\))*\)\s*", "", p)
    depth, hits = 0, []
    for i, c in enumerate(p):
        depth += (c == "(") - (c == ")")
        if depth == 0 and p[i:i + 3] in ("|->", "|=>"):
            hits.append((i, p[i:i + 3]))
    if len(hits) != 1:
        return None
    i, op = hits[0]
    return p[:i].strip(), op, p[i + 3:].strip()


def rule_key(label: str, tag: str) -> str:
    k = re.sub(r"^(a|assert|chk|check|p|prop|ast)_", "", label, flags=re.I)
    k = re.sub(r"[^A-Za-z0-9]+", "_", k).upper().strip("_") or "RULE"
    return k if not k[0].isdigit() else "R" + k


def draft(inv: dict, tag: str, title: str, standard: str, iface_name: str | None, item_name: str | None,
          cfg_name: str | None) -> tuple[str, dict]:
    T = tag.upper()
    iface = pick_interface(inv, iface_name)
    stats = {"interface": iface["name"], "requirements": 0, "expressions": 0, "signals": 0}
    rows: dict[str, list[list[str]]] = {}

    # parameters
    pmap: dict[str, str] = {}
    prow = []
    for p in iface.get("params", []):
        if p["kind"] == "parameter":
            pmap[p["name"]] = para(p["name"])
            prow.append([pmap[p["name"]], f"inferred from the interface parameter {p['name']}; {UNV}", p["default"],
                         f"<fill: legal values; code default only>", "<fill: unit>"])
    rows["parameters"] = prow or [["PARA_<fill: NAME>", "<fill: purpose>", "<fill: default>", "<fill: legal values>", "<fill: unit>"]]

    # clocks, resets, signals
    clk_ports = [p for p in iface.get("ports", []) if re.search(r"clk|clock", p["name"], re.I)]
    rst_ports = [p for p in iface.get("ports", []) if re.search(r"rst|reset", p["name"], re.I)]
    sig_rows = []
    for p in clk_ports[:1]:
        sig_rows.append([p["name"], "1", "CLK", "all", "not applicable", f"clock port of the interface; {UNV}"])
    for p in rst_ports[:1]:
        sig_rows.append([p["name"], "1", "RST", "all", "not applicable", f"reset port of the interface; {UNV}"])
    outputs: dict[str, set[str]] = {}
    for cb in iface.get("clocking", []):
        role = role_of_cb(cb["name"])
        for s in cb.get("output", []):
            outputs.setdefault(s, set()).add(role or "?")
    names = set()
    for s in inv["signals"]:
        if s.get("interface") != iface["name"] or s["name"] in names:
            continue
        names.add(s["name"])
        roles = outputs.get(s["name"], set()) - {"?"}
        driver = next(iter(roles)) if len(roles) == 1 else "M"
        basis = "from the clocking block outputs" if len(roles) == 1 else "assumed host; no clocking block names the driver"
        width = s["width"] if re.fullmatch(r"\d+", s["width"]) else tidy(map_idents(s["width"], pmap))
        sig_rows.append([s["name"], width, driver, "all", f"unknown ({UNV})", f"driver {basis}; declared at {s['file']}:{s['line']}; {UNV}"])
    stats["signals"] = len(sig_rows)
    if sig_rows:
        rows["signals"] = sig_rows
    if clk_ports and rst_ports:
        low = bool(re.search(r"n$|_n|resetn|rstn|aresetn", rst_ports[0]["name"], re.I))
        rows["clocks"] = [["main", clk_ports[0]["name"], rst_ports[0]["name"], "Active-low" if low else "Active-high",
                           f"inferred from the port names; {UNV}"]]

    # items, knobs
    items = [c for c in inv["classes"] if c["role"] == "item" and c.get("fields")]
    item = next((c for c in items if c["name"] == item_name), None) if item_name else (max(items, key=lambda c: len(c["fields"])) if items else None)
    if item:
        irows = []
        for f in item["fields"]:
            nm = re.sub(r"[^a-z0-9_]", "_", f["name"].lower())
            w = "32" if f["type"].startswith("int") else (width_from_type(f["type"]) or "1")
            irows.append([nm, f["type"].split("[")[0].strip() or "logic", map_idents(w, pmap), f["rand"] if f["rand"] in ("rand", "randc") else "none",
                          f"item field of {item['name']} at {item['file']}; {UNV}", "M,S"])
        rows["items"] = irows
    cfgs = [c for c in inv["classes"] if c["role"] == "config" and c.get("fields")]
    cfg = next((c for c in cfgs if c["name"] == cfg_name), None) if cfg_name else (max(cfgs, key=lambda c: len(c["fields"])) if cfgs else None)
    if cfg:
        krows = []
        for f in cfg["fields"]:
            if "virtual" in f["type"] or f["name"] in ("vif", "m_vif"):
                continue
            krows.append([re.sub(r"[^a-z0-9_]", "_", f["name"].lower()), f["type"], f["default"] or "0",
                          f"configuration field of {cfg['name']} at {cfg['file']}; {UNV}", "-"])
        if krows:
            rows["knobs"] = krows

    # sequences as capabilities
    reqs52, reqs53, reqs55, exprs, caps, seqs, mons = [], [], [], [], [], [], []
    n = 0
    def next_id() -> str:
        nonlocal n
        n += 1
        return f"VREQ-{T}-{n:04d}"
    explicit: set[str] = set()
    derived: set[str] = set()
    allowed = {s[0] for s in sig_rows} | set(pmap.values())
    for a in inv["assertions"]:
        if a["directive"] not in ("assert", "assume") or not a["label"] or a.get("form") == "vlsit_stub":
            continue
        rid = next_id()
        sev = a["severity"] or "error"
        strength = "SHOULD" if sev == "warning" else "MUST"
        label = a["label"]
        role = a.get("role", "B") if a.get("role") in ("M", "S", "B") else "B"
        prop = a["property"]
        parts = split_property(map_idents(prop, {}))
        kind = "SEQ" if ("|=>" in prop or "##" in prop) else "SIG"
        idents = [i for i in re.findall(r"[A-Za-z_]\w*", prop) if i in allowed]
        sigs = list(dict.fromkeys(idents))[:3]
        text = (f"The interface {'shall' if strength == 'MUST' else 'should'} satisfy the rule checked by {label}"
                + (f": {a['message']}" if a["message"] else "") + ".")
        key = rule_key(label, tag)
        want = f"{T}_{'ERR' if strength == 'MUST' else 'REC'}{role}_{(sigs[0].upper() if sigs else 'BUS')}_{key}"
        if vc.CHECK_ID_RE.match(label) and label.startswith(T + "_"):
            cid = label
        else:
            cid = want
            if cid in explicit | derived:
                k = 2
                while f"{cid}_{k}" in explicit | derived:
                    k += 1
                cid = f"{cid}_{k}"
        explicit.add(cid)
        row = [rid, strength, role, kind, text, f'REF-001 "{UNV}: code-derived, locate the clause" ', "all", ", ".join(sigs) or "-", key,
               "SVA", cid, "-", f"CODE:{a['file']}:{a['line']}:{label}; {UNV}"]
        (reqs53 if kind == "SEQ" else reqs52).append(row)
        stats["requirements"] += 1
        if parts and a.get("form") != "macro":
            ante, op, cons = (parts[0], parts[1], parts[2])
        elif a.get("form") == "vlsit_macro" and parts:
            ante, op, cons = (parts[0], parts[1], parts[2])
        else:
            ante = None
        if ante is not None:
            mapped = [map_idents(x, pmap) for x in (ante, cons)]
            ok = True
            for x in mapped:
                ids, problems = vc.expr_identifiers(x.replace("||", " OR "))
                if problems or ids - allowed:
                    ok = False
            if ok:
                exprs.append([rid, "SAME" if op == "|->" else "NEXT", tidy(mapped[0]), tidy(mapped[1]),
                              a["message"] or f"{label} violated"])
                stats["expressions"] += 1
    seq_classes = [c for c in inv["classes"] if c["role"] == "sequence"]
    for i, c in enumerate(seq_classes, 1):
        rid = next_id()
        sname = re.sub(r"[^a-z0-9_]", "_", c["name"].lower())
        reqs55.append([rid, "MAY", "M", "CAP", f"The VIP may exercise the capability of the sequence {c['name']}.",
                       f'REF-001 "{UNV}: code-derived, locate the clause" ', "all", "-", "CAPABILITY", "COV", "-", "-",
                       f"CODE:{c['file']}:{c['line']}:{c['name']}; {UNV}"])
        caps.append([f"CAP-{i:03d}", "M", f"sequence {c['name']} ({UNV})", "none", sname, rid])
        seqs.append([f"SEQ-{i:03d}", sname, "M", f"code-derived from {c['file']}; {UNV}", rid])
    for i, c in enumerate([c for c in inv["classes"] if c["role"] == "monitor"][:6], 1):
        mons.append([f"MON-{i:03d}", f"transfer observed by {c['name']} ({UNV})", "<fill: item class>", "ap", f"{c['file']}:{c['line']}"])
    rows["requirements_5.2"] = reqs52
    if reqs53:
        rows["requirements_5.3"] = reqs53
    if reqs55:
        rows["requirements_5.5"] = reqs55
    if exprs:
        rows["checkexpr"] = exprs
    if caps:
        rows["caps"] = caps
        rows["seqs"] = [["SEQ-000", f"{tag}_base_seq", "M", "Base sequence and common helpers", "-"]] + seqs if False else seqs
    if mons:
        rows["monitors"] = mons
    rows["decisions"] = [
        ["DEC-001", "Open", f"This specification was derived from the code of the existing VIP ({inv['root']}), not from the standard", "Every cell marked UNVERIFIED must be confirmed against the standard, corrected, or removed before Gate 1", "Open"],
        ["DEC-002", "Open", "Driver roles, requirement strengths and roles, and check expressions were inferred from names and clocking blocks", "Wrong inference changes the generated checks", "Open"],
        ["DEC-003", "Assumption", "The scan is lexical; checks produced by macros, generate blocks, or included code that was not scanned are not listed", "Missing requirements are possible", "Open: compare with the standard"],
    ]
    text = {"purpose": f"As-built specification of an existing VIP, derived from its source at {inv['root']} ({UNV}: confirm against the standard)"}
    return sc.build(tag, title, standard, False, rows, text), stats


def width_from_type(t: str) -> str | None:
    m = re.search(r"\[(\d+):(\d+)\]", t)
    return str(abs(int(m.group(1)) - int(m.group(2))) + 1) if m else None


def report(inv: dict, stats: dict, spec_path: str) -> str:
    asserts = [a for a in inv["assertions"] if a["label"]]
    unlabeled = [a for a in inv["assertions"] if not a["label"]]
    covered_msgs = {a["message_id"] for a in asserts}
    other_msgs = sorted({m["id"] for m in inv["messages"] if m["severity"] in ("error", "fatal", "warning") and m.get("literal", True)
                         and m["id"] not in covered_msgs})[:15]
    L = [f"# As-built report", "", f"Specification draft: `{spec_path}`. Source: `{inv['root']}`.", "",
         "## What was derived", "",
         f"- Interface modeled: `{stats['interface']}` with {stats['signals']} signal row(s).",
         f"- Requirements from labeled assertions: {stats['requirements']} (check expressions written: {stats['expressions']}).",
         f"- Classes by role: " + ", ".join(f"{k} {sum(1 for c in inv['classes'] if c['role'] == k)}" for k in sorted({c['role'] for c in inv['classes']})),
         "", "## What could not be derived (the reviewer must supply it)", "",
         "- The standard document and revision (REF-001) and the clause of every requirement.",
         "- Valid and invalid boundaries (Section 5.6), error injections (Section 6.3), reset and idle values, legal parameter values and units.",
         f"- {len(unlabeled)} assertion(s) without a label were not turned into requirements: "
         + ", ".join(f"{a['file']}:{a['line']}" for a in unlabeled[:6]) + (" ..." if len(unlabeled) > 6 else ""),
         f"- UVM error or warning IDs that no assertion label explains (class-level checks?): {', '.join(other_msgs) or 'none'}",
         f"- {len(inv['todos'])} TODO/FIXME marker(s) in the source.", "",
         "## Next steps", "",
         "1. Locate the standard and replace every UNVERIFIED cell with a cited clause, or remove the item.",
         "2. Run `vip validate` and `vip query todo` until clean; Gate 1 refuses UNVERIFIED.",
         "3. Run `vip verify-code` after any change to the source to detect drift between the specification and the code."]
    return "\n".join(L) + "\n"


def cmd_verify(spec_path: str, root: str) -> int:
    spec = vc.load_spec(spec_path)
    rootp = Path(root)
    bad = n = 0
    for r in spec.rows("requirements") + spec.rows("monitors"):
        note = r.get("notes", "") or r.get("notes", "")
        m = re.search(r"CODE:([^:;]+):(\d+):([^;\s]+)", note)
        if not m:
            continue
        n += 1
        f = rootp / m.group(1)
        if not f.is_file():
            print(f"DRIFT {r.get('req_id', '')}: file {m.group(1)} is missing")
            bad += 1
            continue
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        ln = int(m.group(2))
        window = "\n".join(lines[max(0, ln - 6):ln + 6])
        if m.group(3) not in window:
            print(f"DRIFT {r.get('req_id', '')}: label {m.group(3)} is no longer near {m.group(1)}:{ln}")
            bad += 1
    left = Path(spec_path).read_text(encoding="utf-8", errors="replace").count(UNV)
    print(f"{n} CODE pointer(s) checked, {bad} drifted; {left} {UNV} mark(s) remain" + (" (Gate 1 refuses them)" if left else ""))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft")
    d.add_argument("inventory")
    d.add_argument("--tag", required=True)
    d.add_argument("--title", required=True)
    d.add_argument("--standard", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--interface")
    d.add_argument("--item")
    d.add_argument("--cfg")
    d.add_argument("--report")
    v = sub.add_parser("verify")
    v.add_argument("spec")
    v.add_argument("--root", required=True)
    a = ap.parse_args()
    if a.cmd == "verify":
        return cmd_verify(a.spec, a.root)
    if not vc.TAG_RE.match(a.tag):
        raise SystemExit("error: --tag must be 2-8 lowercase alphanumerics starting with a letter")
    vc.refuse_overwrite(a.out)
    inv = json.loads(Path(a.inventory).read_text(encoding="utf-8"))
    text, stats = draft(inv, a.tag, a.title, a.standard, a.interface, a.item, a.cfg)
    Path(a.out).write_text(text, encoding="utf-8", newline="\n")
    if a.report:
        vc.refuse_overwrite(a.report)
        Path(a.report).write_text(report(inv, stats, a.out), encoding="utf-8", newline="\n")
    print(f"draft {a.out}: interface {stats['interface']}, {stats['signals']} signal(s), {stats['requirements']} requirement(s), "
          f"{stats['expressions']} check expression(s); {len(re.findall(UNV, text))} UNVERIFIED mark(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
