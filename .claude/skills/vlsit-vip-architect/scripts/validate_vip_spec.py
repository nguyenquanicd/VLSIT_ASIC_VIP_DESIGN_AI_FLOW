#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate a VLSIT ASIC VIP specification against the mandatory markdown template.

Checks the front matter, the numbered sections, the machine-readable tables,
ID formats and uniqueness, cross references, requirement semantics, boundary
consistency, and leftover placeholders. Standard library only.

Usage:
    python validate_vip_spec.py SPEC.md [--json REPORT.json] [--strict-inj]
    python validate_vip_spec.py TEMPLATE.md --template      # structure only

Exit status: 0 when no error is found, 1 otherwise.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402


def check_front_matter(spec: vc.Spec, rep: vc.Report, template: bool) -> None:
    fm = spec.front
    if not fm:
        rep.error("FM-01", "front matter block (--- ... ---) is missing")
        return
    for key in vc.FRONT_MATTER_KEYS:
        if key not in fm or not fm[key].strip():
            rep.error("FM-02", f"front matter key '{key}' is missing or empty")
    if fm.get("document_type") != vc.DOCUMENT_TYPE:
        rep.error("FM-03", f"document_type must be '{vc.DOCUMENT_TYPE}'")
    if template:
        return
    tag = fm.get("proto_tag", "")
    if not vc.TAG_RE.match(tag):
        rep.error("FM-04", f"proto_tag '{tag}' must be 2-8 lowercase alphanumerics starting with a letter")
        return
    if fm.get("document_id") != f"{tag.upper()}-VIP-SPEC":
        rep.error("FM-05", f"document_id must be '{tag.upper()}-VIP-SPEC'")
    if fm.get("vip_name") != f"{tag}_vip":
        rep.error("FM-06", f"vip_name must be '{tag}_vip'")
    if not re.match(r"^\d+\.\d+(\.\d+)?$", fm.get("version", "")):
        rep.error("FM-07", "version must look like 0.1 or 1.0.0")
    if fm.get("status") not in vc.STATUS_VALUES:
        rep.error("FM-08", f"status must be one of {vc.STATUS_VALUES}")


def check_sections(spec: vc.Spec, rep: vc.Report) -> None:
    top = {s.number: s for s in spec.sections if s.level == 2}
    last = 0
    for num, title in vc.SPEC_SECTIONS:
        s = top.get(str(num))
        if s is None:
            rep.error("SEC-01", f"section {num} '{title}' is missing")
            continue
        if s.title.strip().lower().rstrip(".") != title.lower():
            rep.warn("SEC-02", f"section {num} title is '{s.title}', expected '{title}'", s.line)
        if s.line < last:
            rep.error("SEC-03", f"section {num} is out of order", s.line)
        last = s.line


def check_tables(spec: vc.Spec, rep: vc.Report) -> None:
    by_first = {}
    for kind, schema in vc.TABLE_SCHEMAS.items():
        by_first.setdefault(schema["columns"][0].lower(), []).append(kind)
    for t in spec.tables:
        if t.kind is not None:
            continue
        head0 = t.header[0].strip().lower() if t.header else ""
        kinds = by_first.get(head0)
        if kinds:
            exp = " OR ".join(" | ".join(vc.TABLE_SCHEMAS[k]["columns"]) for k in kinds)
            rep.error("TBL-01", f"table '{t.header[0]}' has wrong columns; expected: {exp}", t.line)
    numbers = {s.number for s in spec.sections}
    for sec, kind in vc.SECTION_TABLES.items():
        if sec not in numbers:
            continue
        text = spec.section_text(sec)
        has_table = any(t.kind == kind and t.section == sec for t in spec.tables)
        if not has_table and not vc.has_na_paragraph(text):
            rep.error("TBL-02", f"section {sec} needs a '{kind}' table or an 'N/A: <reason>' paragraph")
    for kind in vc.REQUIRED_TABLES:
        if not spec.rows(kind):
            rep.error("TBL-03", f"required table '{kind}' has no rows anywhere in the document")
    for kind, ids in vc.FIXED_ID_TABLES.items():
        have = {r[vc.norm_key(vc.TABLE_SCHEMAS[kind]['columns'][0])] for r in spec.rows(kind)}
        for want in ids:
            if want not in have:
                rep.error("TBL-04", f"fixed row {want} is missing from the '{kind}' table")


def unique_ids(rows: list[dict], key: str, kind: str, rep: vc.Report, pattern: str | None) -> set[str]:
    seen: dict[str, int] = {}
    rx = re.compile(pattern) if pattern else None
    for r in rows:
        v = r.get(key, "").strip()
        if rx and not rx.match(v):
            rep.error("ID-01", f"{kind}: ID '{v}' does not match {pattern}", r["_line"])
        if v in seen:
            rep.error("ID-02", f"{kind}: duplicate ID '{v}' (first at line {seen[v]})", r["_line"])
        seen.setdefault(v, r["_line"])
    return set(seen)


def tokens(cell: str) -> list[str]:
    return vc.split_list(cell)


def check_rows(spec: vc.Spec, rep: vc.Report, strict_inj: bool) -> None:
    tag = spec.tag.upper()
    ids: dict[str, set[str]] = {}
    for kind, schema in vc.TABLE_SCHEMAS.items():
        rows = spec.rows(kind)
        if not rows or kind in ("compliance", "candidates", "environment", "timing", "trace", "glossary"):
            ids[kind] = set()
            continue
        key = vc.norm_key(schema["columns"][0])
        ids[kind] = unique_ids(rows, key, kind, rep, schema["id"])

    params = ids["parameters"]
    refs, profs, opts = ids["references"], ids["profiles"], ids["options"]
    sigs = ids["signals"]
    bnds, caps = ids["boundaries"], ids["caps"]

    # roles
    letters = []
    for r in spec.rows("roles"):
        if r["letter"] not in vc.ROLE_LETTERS:
            rep.error("ROL-01", f"role letter '{r['letter']}' must be one of {vc.ROLE_LETTERS}", r["_line"])
        if r["mode"] not in vc.ROLE_MODES:
            rep.error("ROL-02", f"role mode '{r['mode']}' must be one of {vc.ROLE_MODES}", r["_line"])
        if r["letter"] == "B" and r["mode"] != "PASSIVE":
            rep.error("ROL-03", "role letter B (bus observer) must have mode PASSIVE", r["_line"])
        letters.append(r["letter"])
    for d in {x for x in letters if letters.count(x) > 1}:
        rep.warn("ROL-04", f"several roles use letter {d}")

    # options, variants
    for r in spec.rows("options"):
        if r["status"] not in vc.OPTION_STATUS:
            rep.error("OPT-01", f"option status '{r['status']}' must be one of {vc.OPTION_STATUS}", r["_line"])
    for r in spec.rows("variants"):
        if r["profile"] not in profs:
            rep.error("VAR-01", f"variant profile '{r['profile']}' is not defined in the profiles table", r["_line"])
        for o in tokens(r["options"]):
            if o.lower() != "none" and o not in opts:
                rep.error("VAR-02", f"variant option '{o}' is not defined", r["_line"])
    for r in spec.rows("profiles"):
        for o in tokens(r["included_options"]):
            if o.lower() != "none" and o not in opts:
                rep.error("PRF-01", f"profile option '{o}' is not defined", r["_line"])

    # clocks and signals
    for r in spec.rows("clocks"):
        if r["reset_polarity"] not in vc.RESET_POLARITY:
            rep.error("CLK-01", f"reset polarity '{r['reset_polarity']}' must be one of {vc.RESET_POLARITY}", r["_line"])
    sig_rows = {r["signal"]: r for r in spec.rows("signals")}
    for r in sig_rows.values():
        if r["driver"] not in vc.DRIVERS:
            rep.error("SIG-01", f"signal '{r['signal']}' driver '{r['driver']}' must be one of {vc.DRIVERS}", r["_line"])
        w = r["width"].strip()
        if not re.fullmatch(r"\d+", w):
            for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", w):
                if ident not in params:
                    rep.error("SIG-02", f"signal '{r['signal']}' width uses undefined parameter '{ident}'", r["_line"])
            if not re.fullmatch(r"[A-Za-z0-9_+\-*/() ]+", w):
                rep.error("SIG-03", f"signal '{r['signal']}' width '{w}' is not a number or parameter expression", r["_line"])
        for tok in tokens(r["profile_option"]):
            if tok.lower() != "all" and tok not in profs and tok not in opts:
                rep.error("SIG-04", f"signal '{r['signal']}' references undefined '{tok}'", r["_line"])
    for r in spec.rows("clocks"):
        for col, drv in (("clock_signal", "CLK"), ("reset_signal", "RST")):
            s = sig_rows.get(r[col])
            if s is None:
                rep.error("CLK-02", f"{col} '{r[col]}' is not listed in the signals table", r["_line"])
            elif s["driver"] != drv:
                rep.error("CLK-03", f"signal '{r[col]}' must have driver {drv}", s["_line"])

    # requirements
    derived: dict[str, str] = {}
    req_rows = spec.rows("requirements")
    for r in req_rows:
        line = r["_line"]
        rid = r["req_id"]
        m = vc.REQ_ID_RE.match(rid)
        if m and m.group(1) != tag:
            rep.error("REQ-01", f"{rid}: tag '{m.group(1)}' differs from proto_tag '{tag}'", line)
        strength, role, kind, ctype = r["strength"], r["role"], r["kind"], r["check_type"]
        if strength not in vc.STRENGTHS:
            rep.error("REQ-02", f"{rid}: strength '{strength}' must be one of {vc.STRENGTHS}", line)
        if role not in vc.ROLE_LETTERS:
            rep.error("REQ-03", f"{rid}: role '{role}' must be one of {vc.ROLE_LETTERS}", line)
        if kind not in vc.KINDS:
            rep.error("REQ-04", f"{rid}: kind '{kind}' must be one of {vc.KINDS}", line)
        if ctype not in vc.CHECK_TYPES:
            rep.error("REQ-05", f"{rid}: check type '{ctype}' must be one of {vc.CHECK_TYPES}", line)
        text = r["requirement"]
        if strength in vc.MODAL and not vc.MODAL[strength].search(text):
            rep.error("REQ-06", f"{rid}: text lacks the modal verb that matches strength {strength}", line)
        if re.search(r"\bTBD\b", text):
            rep.error("REQ-07", f"{rid}: 'TBD' is not allowed in a requirement; add a decision instead", line)
        sref = r["spec_ref"]
        m2 = re.match(r"^(REF-\d{3})\b\s*(.*)$", sref)
        if not m2 or not m2.group(2).strip():
            rep.error("REQ-08", f"{rid}: spec ref must be 'REF-nnn <clause>', found '{sref}'", line)
        elif m2.group(1) not in refs:
            rep.error("REQ-09", f"{rid}: spec ref {m2.group(1)} is not in the references table", line)
        for p in tokens(r["profile"]):
            if p.lower() != "all" and p not in profs:
                rep.error("REQ-10", f"{rid}: profile '{p}' is not defined", line)
        for s in tokens(r["signals"]):
            if s not in sigs:
                rep.error("REQ-11", f"{rid}: signal '{s}' is not in the signals table", line)
        rk = r["rule_key"].strip()
        if ctype in ("SVA", "CLASS") and not re.fullmatch(r"[A-Z][A-Z0-9_]*", rk):
            rep.error("REQ-12", f"{rid}: rule key '{rk}' must be an uppercase token", line)
        for b in tokens(r["bound_refs"]):
            if b not in bnds:
                rep.error("REQ-13", f"{rid}: bound ref '{b}' is not defined", line)
        cid, notes = r["check_id"].strip(), r["notes"].strip()
        if ctype in ("SVA", "CLASS"):
            if cid.lower() == "auto":
                if role in vc.ROLE_LETTERS and strength in vc.STRENGTHS and rk:
                    d = vc.derive_check_id(tag, strength, role, r["signals"], rk)
                    if d in derived:
                        rep.error("REQ-14", f"{rid}: derived check ID {d} collides with {derived[d]}; give an explicit Check ID or a distinct rule key", line)
                    derived.setdefault(d, rid)
            elif not vc.CHECK_ID_RE.match(cid):
                rep.error("REQ-15", f"{rid}: Check ID '{cid}' must be 'auto' or match <TAG>_<ERR|REC><M|S|B>_<SIGNAL>_<RULE>", line)
            else:
                if not cid.startswith(tag + "_"):
                    rep.error("REQ-16", f"{rid}: Check ID '{cid}' must start with {tag}_", line)
                want = "ERR" if strength == "MUST" else "REC"
                body = cid[len(tag) + 1:]
                if not body.startswith(want + role):
                    rep.error("REQ-17", f"{rid}: Check ID '{cid}' must carry {want}{role} for strength {strength}, role {role}", line)
                if cid in derived:
                    rep.error("REQ-14", f"{rid}: Check ID {cid} collides with {derived[cid]}", line)
                derived.setdefault(cid, rid)
        else:
            if cid not in ("-", ""):
                rep.error("REQ-18", f"{rid}: Check ID must be '-' when check type is {ctype}", line)
            if ctype == "NONE" and not re.match(r"^NONE:\s*\S", notes):
                rep.error("REQ-19", f"{rid}: check type NONE needs 'NONE:<reason>' in Notes", line)
            if ctype == "COV" and strength in ("MUST", "SHOULD") and not re.match(r"^COV:\s*\S", notes):
                rep.error("REQ-20", f"{rid}: {strength} requirement with check type COV needs 'COV:<reason>' in Notes", line)
        if kind == "CAP" and ctype in ("SVA", "CLASS"):
            rep.warn("REQ-21", f"{rid}: a capability requirement normally uses check type COV or NONE", line)

    if not req_rows:
        rep.error("REQ-00", "no requirement rows found")

    # boundaries
    for r in spec.rows("boundaries"):
        line = r["_line"]
        if r["source_req"] not in ids["requirements"]:
            rep.error("BND-01", f"{r['bound_id']}: source req '{r['source_req']}' is not defined", line)
        vmin, vmax = vc.parse_number(r["valid_min"]), vc.parse_number(r["valid_max"])
        ibel, iabv = vc.parse_number(r["invalid_below"]), vc.parse_number(r["invalid_above"])
        if vmin is None or vmax is None:
            rep.warn("BND-02", f"{r['bound_id']}: valid limits are not numeric; qualification must resolve them", line)
            continue
        if vmin > vmax:
            rep.error("BND-03", f"{r['bound_id']}: valid min is greater than valid max", line)
        if ibel is not None and not ibel < vmin:
            rep.error("BND-04", f"{r['bound_id']}: invalid-below must be less than valid min", line)
        if iabv is not None and not iabv > vmax:
            rep.error("BND-05", f"{r['bound_id']}: invalid-above must be greater than valid max", line)
        if ibel is None and r["invalid_below"].strip() != "-":
            rep.error("BND-06", f"{r['bound_id']}: invalid-below must be numeric or '-'", line)
        if iabv is None and r["invalid_above"].strip() != "-":
            rep.error("BND-06", f"{r['bound_id']}: invalid-above must be numeric or '-'", line)

    # items, caps, injections
    for r in spec.rows("items"):
        if r["rand"] not in vc.RAND_VALUES:
            rep.error("ITM-01", f"item '{r['item_field']}' rand '{r['rand']}' must be one of {vc.RAND_VALUES}", r["_line"])
        for x in tokens(r["roles"]):
            if x not in vc.ROLE_LETTERS:
                rep.error("ITM-02", f"item '{r['item_field']}' role '{x}' must be M, S, or B", r["_line"])
    cap_reqs: set[str] = set()
    for r in spec.rows("caps"):
        if r["role"] not in vc.ROLE_LETTERS:
            rep.error("CAP-01", f"{r['cap_id']}: role '{r['role']}' must be one of {vc.ROLE_LETTERS}", r["_line"])
        if not re.fullmatch(r"[a-z][a-z0-9_]*", r["sequence"].strip()):
            rep.error("CAP-02", f"{r['cap_id']}: sequence name '{r['sequence']}' must be lowercase snake_case", r["_line"])
        for q in tokens(r["requirements"]):
            cap_reqs.add(q)
            if q not in ids["requirements"]:
                rep.error("CAP-03", f"{r['cap_id']}: requirement '{q}' is not defined", r["_line"])
    for r in req_rows:
        if r["kind"] == "CAP" and r["req_id"] not in cap_reqs:
            rep.warn("CAP-04", f"{r['req_id']}: capability requirement is not referenced by any CAP row", r["_line"])
    injected: set[str] = set()
    for r in spec.rows("injections"):
        q = r["violated_requirement"]
        injected.add(q)
        if q not in ids["requirements"]:
            rep.error("INJ-01", f"{r['inj_id']}: violated requirement '{q}' is not defined", r["_line"])
        if r["role"] not in vc.ROLE_LETTERS:
            rep.error("INJ-02", f"{r['inj_id']}: role '{r['role']}' must be one of {vc.ROLE_LETTERS}", r["_line"])
        ec = r["expected_check"].strip()
        if ec.lower() != "auto" and not vc.CHECK_ID_RE.match(ec):
            rep.error("INJ-03", f"{r['inj_id']}: expected check must be 'auto' or a check ID", r["_line"])
    for r in req_rows:
        if r["strength"] == "MUST" and r["check_type"] in ("SVA", "CLASS") and r["req_id"] not in injected:
            msg = f"{r['req_id']}: MUST check has no error injection (INJ row); VQUA-01 needs a way to produce one violation"
            (rep.error if strict_inj else rep.warn)("INJ-04", msg, r["_line"])

    # check expressions
    sva_reqs = {r["req_id"]: r for r in req_rows if r["check_type"] == "SVA"}
    allowed = set(sigs) | params
    seen_expr: set[str] = set()
    for r in spec.rows("checkexpr"):
        line, rid = r["_line"], r["req_id"]
        if rid not in sva_reqs:
            rep.error("EXP-01", f"{rid}: check expression needs a requirement with check type SVA", line)
        if rid in seen_expr:
            rep.error("EXP-02", f"{rid}: more than one check expression", line)
        seen_expr.add(rid)
        if r["operator"] not in vc.CHECK_OPS:
            rep.error("EXP-03", f"{rid}: operator '{r['operator']}' must be one of {list(vc.CHECK_OPS)}", line)
        for col in ("antecedent", "consequent"):
            if not r[col].strip():
                rep.error("EXP-04", f"{rid}: {col} is empty", line)
                continue
            idents, problems = vc.expr_identifiers(r[col])
            for p in problems:
                rep.error("EXP-05", f"{rid}: {col}: {p}", line)
            for i in sorted(idents - allowed):
                rep.error("EXP-06", f"{rid}: {col} uses unknown identifier '{i}' (not a signal or PARA_ name)", line)
        if not r["message"].strip():
            rep.error("EXP-07", f"{rid}: message is empty", line)
    missing = [rid for rid, r in sva_reqs.items() if rid not in seen_expr]
    if spec.rows("checkexpr") and missing:
        rep.warn("EXP-08", f"{len(missing)} SVA requirement(s) have no check expression and stay stubs: {', '.join(missing[:6])}")

    # coverage, sequences, decisions
    for r in spec.rows("covreq"):
        for q in tokens(r["requirements"]):
            if q not in ids["requirements"]:
                rep.error("CVR-01", f"{r['cov_req_id']}: requirement '{q}' is not defined", r["_line"])
    for r in spec.rows("seqs"):
        for q in tokens(r["requirements"]):
            if q not in ids["requirements"]:
                rep.error("SEQ-01", f"{r['seq_id']}: requirement '{q}' is not defined", r["_line"])
    open_count = 0
    for r in spec.rows("decisions"):
        if r["type"] not in vc.DECISION_TYPES:
            rep.error("DEC-01", f"{r['decision_id']}: type '{r['type']}' must be one of {vc.DECISION_TYPES}", r["_line"])
        if r["type"] == "Open":
            open_count += 1
    if open_count:
        rep.warn("DEC-02", f"{open_count} open decision(s); each blocks gate VIP-0 for the requirements it affects")

    # variants cover the parameter table
    if spec.rows("parameters") and not spec.rows("variants"):
        rep.warn("VAR-03", "parameters exist but no qualification variant is defined")


def check_placeholders(spec: vc.Spec, rep: vc.Report) -> None:
    found = vc.find_placeholders(spec)
    for line, tok in found[:20]:
        rep.error("PH-01", f"unreplaced placeholder {tok}", line)
    if len(found) > 20:
        rep.error("PH-02", f"{len(found) - 20} further placeholder(s) not listed")


def validate(spec: vc.Spec, template: bool, strict_inj: bool) -> vc.Report:
    rep = vc.Report("VIP specification validation", str(spec.path))
    check_front_matter(spec, rep, template)
    check_sections(spec, rep)
    check_tables(spec, rep)
    if not template:
        check_rows(spec, rep, strict_inj)
        check_placeholders(spec, rep)
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="VIP specification markdown")
    ap.add_argument("--template", action="store_true", help="check structure only (allow placeholders)")
    ap.add_argument("--strict-inj", action="store_true", help="a MUST check without an INJ row is an error")
    ap.add_argument("--full", action="store_true", help="print every finding (default: grouped, 3 per code)")
    ap.add_argument("--json", help="write the report as JSON to this new file")
    args = ap.parse_args()
    spec = vc.load_spec(args.spec)
    rep = validate(spec, args.template, args.strict_inj)
    rep.print_text(full=args.full)
    if args.json:
        vc.refuse_overwrite(args.json)
        vc.write_json(args.json, rep.to_json())
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
