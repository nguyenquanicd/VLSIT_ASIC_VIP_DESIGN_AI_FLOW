#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read a VIP specification without loading the whole file into the context.

Commands (output is compact tab-separated text):
    outline SPEC                         sections with their tables and row counts
    kinds                                table kinds and their column keys
    rows SPEC KIND [--fields a,b] [--where key=value] [--limit N]
    get SPEC ID [--deep]                 one row by its ID; --deep adds linked rows of a requirement
    refs SPEC ID                         every row that mentions the ID
    todo SPEC                            open placeholder cells grouped by section

Examples:
    python spec_query.py outline spec.md
    python spec_query.py rows spec.md requirements --fields req_id,strength,role,check_type --where role=M
    python spec_query.py get spec.md VREQ-APB-0004 --deep
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402

DEFAULT_FIELDS = {
    "requirements": ["req_id", "strength", "role", "kind", "check_type", "signals", "rule_key"],
    "signals": ["signal", "width", "driver", "profile_option", "reset_idle"],
    "boundaries": ["bound_id", "quantity", "valid_min", "valid_max", "invalid_below", "invalid_above"],
    "caps": ["cap_id", "role", "capability", "sequence", "requirements"],
    "injections": ["inj_id", "role", "violated_requirement", "expected_check"],
    "decisions": ["decision_id", "type", "statement", "resolution_status"],
}


def cell(v: str, width: int = 120) -> str:
    v = " ".join(v.split())
    return v if len(v) <= width else v[:width - 1] + "…"


def id_key(kind: str) -> str:
    return vc.norm_key(vc.TABLE_SCHEMAS[kind]["columns"][0])


def cmd_outline(spec: vc.Spec) -> None:
    print(f"{spec.path.name}  tag={spec.tag}  status={spec.front.get('status')}  version={spec.front.get('version')}"
          f"  revision={spec.front.get('spec_revision_locked')}")
    for s in spec.sections:
        tabs = [t for t in spec.tables if t.section == s.number]
        desc = ", ".join(f"{t.kind or '?'}:{len(t.rows)}" for t in tabs)
        print(f"{s.number}\t{s.title}\t{desc}")


def cmd_kinds() -> None:
    for k, sch in vc.TABLE_SCHEMAS.items():
        print(f"{k}\t{', '.join(vc.norm_key(c) for c in sch['columns'])}")


def cmd_rows(spec: vc.Spec, kind: str, fields: str | None, where: list[str], limit: int) -> int:
    if kind not in vc.TABLE_SCHEMAS:
        print(f"error: unknown kind '{kind}'; run: kinds", file=sys.stderr)
        return 1
    rows = spec.rows(kind)
    keys = fields.split(",") if fields else DEFAULT_FIELDS.get(kind) or [vc.norm_key(c) for c in vc.TABLE_SCHEMAS[kind]["columns"]]
    for w in where:
        k, _, v = w.partition("=")
        rows = [r for r in rows if r.get(k, "").strip().lower() == v.strip().lower()]
    print("\t".join(keys))
    for r in rows[:limit]:
        print("\t".join(cell(r.get(k, "")) for k in keys))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more row(s); raise --limit")
    return 0


def find_row(spec: vc.Spec, rid: str):
    for t in spec.tables:
        if t.kind and t.rows:
            key = vc.norm_key(t.header[0])
            for r in t.dict_rows():
                if r.get(key, "").strip() == rid:
                    return t.kind, r
    return None, None


def show(kind: str, row: dict) -> None:
    print(f"[{kind}]")
    for k, v in row.items():
        if not k.startswith("_") and v.strip():
            print(f"{k}\t{cell(v, 400)}")


def cmd_get(spec: vc.Spec, rid: str, deep: bool) -> int:
    kind, row = find_row(spec, rid)
    if row is None:
        print(f"error: no row with ID {rid}", file=sys.stderr)
        return 1
    show(kind, row)
    if deep and kind == "requirements":
        for b in vc.split_list(row["bound_refs"]):
            k2, r2 = find_row(spec, b)
            if r2:
                show(k2, r2)
        for k2 in ("checkexpr", "injections", "caps"):
            for r2 in spec.rows(k2):
                if rid in (r2.get("req_id"), r2.get("violated_requirement")) or rid in vc.split_list(r2.get("requirements", "")):
                    show(k2, r2)
    return 0


def cmd_refs(spec: vc.Spec, rid: str) -> int:
    n = 0
    for t in spec.tables:
        if not t.kind:
            continue
        key = vc.norm_key(t.header[0])
        for r in t.dict_rows():
            if r.get(key, "").strip() == rid:
                continue
            if any(rid in vc.split_list(v) or rid in v for k, v in r.items() if not k.startswith("_")):
                print(f"{t.kind}\t{r.get(key, '')}\tline {r['_line']}")
                n += 1
    if n == 0:
        print("no references")
    return 0


def cmd_todo(spec: vc.Spec) -> int:
    found = vc.find_placeholders(spec)
    if not found:
        print("no open placeholders")
        return 0
    sec_of = lambda line: next((s.number for s in reversed(spec.sections) if s.line <= line), "front")
    groups: dict[str, list[tuple[int, str]]] = {}
    for line, tok in found:
        groups.setdefault(sec_of(line), []).append((line, tok))
    for sec, items in groups.items():
        lines = sorted({ln for ln, _ in items})
        shown = ",".join(str(x) for x in lines[:8]) + (f",+{len(lines) - 8}" if len(lines) > 8 else "")
        print(f"{sec}\t{len(items)} open\tlines {shown}")
    print(f"total {len(found)} open placeholder(s) on {len({ln for ln, _ in found})} line(s)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("outline")
    o.add_argument("spec")
    sub.add_parser("kinds")
    r = sub.add_parser("rows")
    r.add_argument("spec")
    r.add_argument("kind")
    r.add_argument("--fields")
    r.add_argument("--where", action="append", default=[])
    r.add_argument("--limit", type=int, default=60)
    g = sub.add_parser("get")
    g.add_argument("spec")
    g.add_argument("id")
    g.add_argument("--deep", action="store_true")
    t = sub.add_parser("todo")
    t.add_argument("spec")
    f = sub.add_parser("refs")
    f.add_argument("spec")
    f.add_argument("id")
    a = ap.parse_args()
    if a.cmd == "kinds":
        cmd_kinds()
        return 0
    spec = vc.load_spec(a.spec)
    if a.cmd == "outline":
        cmd_outline(spec)
        return 0
    if a.cmd == "rows":
        return cmd_rows(spec, a.kind, a.fields, a.where, a.limit)
    if a.cmd == "todo":
        return cmd_todo(spec)
    if a.cmd == "get":
        return cmd_get(spec, a.id, a.deep)
    return cmd_refs(spec, a.id)


if __name__ == "__main__":
    sys.exit(main())
