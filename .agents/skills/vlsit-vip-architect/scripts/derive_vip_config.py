#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Derive vip_config.json (schema vlsit_vip_config/1) for one profile.

Combines the validated VIP specification with requirements.csv from the plan
stage. The output is the machine-readable architecture that the generator
consumes. The architect reviews and may edit it; edits are re-checked by
`derive_vip_config.py --check CONFIG.json ...`.

Usage:
    python derive_vip_config.py --spec SPEC.md --requirements requirements.csv \
        --profile PROF-01 --out vip_config.json [--version 0.1.0]
    python derive_vip_config.py --spec SPEC.md --requirements requirements.csv \
        --profile PROF-01 --check vip_config.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402
import validate_vip_spec as vv  # noqa: E402


def applies(profile_cell: str, profile: str) -> bool:
    toks = vc.split_list(profile_cell)
    return not toks or any(t.lower() == "all" or t == profile for t in toks)


def macro_name(tag: str, param: str) -> str:
    return f"{tag.upper()}_VIP_{param[len('PARA_'):] if param.startswith('PARA_') else param}"


def width_value(w: str):
    w = w.strip()
    return int(w) if re.fullmatch(r"\d+", w) else w


def build(spec: vc.Spec, reqs: list[dict], profile_id: str, version: str) -> dict:
    tag = spec.tag
    prof = next((p for p in spec.rows("profiles") if p["profile_id"] == profile_id), None)
    if prof is None:
        raise SystemExit(f"error: profile {profile_id} is not defined in the specification")
    options = [o for o in vc.split_list(prof["included_options"]) if o.lower() != "none"]
    keep = {"all", profile_id, *options}

    signals = []
    for s in spec.rows("signals"):
        toks = {t if t.lower() != "all" else "all" for t in vc.split_list(s["profile_option"])}
        if toks & keep:
            signals.append({"name": s["signal"], "width": width_value(s["width"]), "driver": s["driver"],
                            "reset": s["reset_idle"], "description": s["description"]})
    clk = spec.rows("clocks")[0]
    clock = {"signal": clk["clock_signal"], "reset": clk["reset_signal"],
             "reset_active_low": clk["reset_polarity"] == "Active-low"}

    parameters = [{"name": p["parameter"], "default": width_value(p["default"]), "legal": p["legal_values"],
                   "unit": p["unit"], "description": p["description"], "macro": macro_name(tag, p["parameter"])}
                  for p in spec.rows("parameters")]

    app_reqs = [r for r in reqs if r["status"] != "withdrawn" and applies(r["profile"], profile_id)]
    app_ids = {r["req_id"] for r in app_reqs}
    chk_of = {r["req_id"]: r["chk_id"] for r in reqs}

    exprs = {e["req_id"]: e for e in spec.rows("checkexpr")}
    checks = []
    for i, r in enumerate(x for x in app_reqs if x["check_type"] in ("SVA", "CLASS")):
        e = exprs.get(r["req_id"])
        expr = ({"op": vc.CHECK_OPS[e["operator"]], "ante": vc.translate_expr(e["antecedent"]),
                 "cons": vc.translate_expr(e["consequent"]), "msg": e["message"]}
                if e and r["check_type"] == "SVA" else None)
        checks.append({"id": r["chk_id"], "type": r["check_type"], "role": r["role"], "strength": r["strength"],
                       "is_rec": "_REC" in r["chk_id"], "req_id": r["req_id"], "spec_ref": r["spec_ref"],
                       "text": r["text"], "signals": vc.split_list(r["signals"]), "cov_id": r["cov_id"], "index": i,
                       "expr": expr})

    bounds = {b["bound_id"]: {"id": b["bound_id"], "quantity": b["quantity"], "unit": b["unit"],
                              "valid_min": b["valid_min"], "valid_max": b["valid_max"],
                              "invalid_below": b["invalid_below"], "invalid_above": b["invalid_above"],
                              "source_req": b["source_req"]} for b in spec.rows("boundaries")}
    coverage = []
    for r in app_reqs:
        if r["cov_id"] not in ("-", ""):
            brefs = [b for b in vc.split_list(r["bound_refs"]) if b in bounds]
            coverage.append({"id": r["cov_id"], "req_id": r["req_id"], "kind": r["kind"],
                             "check": r["chk_id"] if r["chk_id"] != "-" else "", "bound": brefs[0] if brefs else None})

    caps = []
    for c in spec.rows("caps"):
        rids = [q for q in vc.split_list(c["requirements"]) if q in app_ids]
        if rids:
            caps.append({"id": c["cap_id"], "role": c["role"], "capability": c["capability"],
                         "knobs": [k for k in vc.split_list(c["config_knobs"]) if k.lower() != "none"],
                         "sequence": c["sequence"], "requirements": rids})
    injections = []
    for i in spec.rows("injections"):
        if i["violated_requirement"] in app_ids:
            exp = chk_of.get(i["violated_requirement"], "-") if i["expected_check"].lower() == "auto" else i["expected_check"]
            injections.append({"id": i["inj_id"], "role": i["role"], "violation": i["violation_to_inject"],
                               "mechanism": i["mechanism"], "requirement": i["violated_requirement"], "expected_check": exp})
    tests = []
    for ck in checks:
        pos, neg = vc.tests_for(ck["id"])
        tests.append({"name": pos, "kind": "pos", "check": ck["id"], "req_id": ck["req_id"]})
        tests.append({"name": neg, "kind": "neg", "check": ck["id"], "req_id": ck["req_id"]})
    for c in caps:
        tests.append({"name": vc.cap_test(c["id"]), "kind": "cap", "check": "", "req_id": ";".join(c["requirements"])})

    env = {r["item"]: r["specification"] for r in spec.rows("environment")}
    cand = spec.rows("candidates")
    cfg = {
        "schema": "vlsit_vip_config/1", "tag": tag, "vip_name": spec.front.get("vip_name", f"{tag}_vip"),
        "version": version, "spec_rev": spec.front.get("spec_revision_locked", ""),
        "spec_version": spec.front.get("version", ""), "profile": profile_id, "options": options,
        "clock": clock, "parameters": parameters, "signals": signals,
        "roles": [{"id": r["role_id"], "role": r["role"], "letter": r["letter"], "mode": r["mode"],
                   "drives": vc.split_list(r["drives"])} for r in spec.rows("roles")],
        "item_fields": [{"name": f["item_field"], "type": f["type"], "width": width_value(f["width"]), "rand": f["rand"],
                         "description": f["description"], "roles": vc.split_list(f["roles"])} for f in spec.rows("items")],
        "knobs": [{"name": k["knob"], "type": k["type"], "default": k["default"], "description": k["description"],
                   "related": k["related"]} for k in spec.rows("knobs")],
        "monitors": [{"id": m["monitor_id"], "event": m["observed_event"], "transaction": m["transaction_produced"],
                      "port": m["analysis_port"]} for m in spec.rows("monitors")],
        "caps": caps, "injections": injections,
        "sequences": [{"id": s["seq_id"], "name": s["sequence"], "role": s["role"], "purpose": s["purpose"]} for s in spec.rows("seqs")],
        "checks": checks, "coverage": coverage, "bounds": list(bounds.values()), "tests": tests,
        "architecture": {"base": "vlsit_vip_base_pkg", "uvm": env.get("UVM version", ""),
                         "build_or_reuse": cand[0]["decision"] if cand else ""},
    }
    return cfg


def check_config(cfg: dict) -> list[str]:
    problems = []
    names = [s["name"] for s in cfg["signals"]]
    if len(names) != len(set(names)):
        problems.append("duplicate signal names")
    if cfg["clock"]["signal"] not in names or cfg["clock"]["reset"] not in names:
        problems.append("clock or reset signal is not in the signal list")
    idx = [c["index"] for c in cfg["checks"]]
    if idx != list(range(len(idx))):
        problems.append("check indices are not 0..N-1 in order")
    ids = [c["id"] for c in cfg["checks"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate check IDs")
    pnames = {p["name"] for p in cfg["parameters"]}
    for s in cfg["signals"]:
        if isinstance(s["width"], str):
            for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", s["width"]):
                if ident not in pnames:
                    problems.append(f"signal {s['name']} width uses undefined parameter {ident}")
    tests = {t["name"] for t in cfg["tests"]}
    for c in cfg["checks"]:
        for t in vc.tests_for(c["id"]):
            if t not in tests:
                problems.append(f"check {c['id']} lacks test {t}")
    for ck in cfg["checks"]:
        if ck["strength"] == "MUST" and not any(i["requirement"] == ck["req_id"] for i in cfg["injections"]):
            problems.append(f"MUST check {ck['id']} has no injection")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--requirements", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out")
    ap.add_argument("--check", help="re-check an existing (possibly edited) vip_config.json")
    ap.add_argument("--version", default="0.1.0")
    args = ap.parse_args()
    spec = vc.load_spec(args.spec)
    rep = vv.validate(spec, template=False, strict_inj=False)
    if rep.errors:
        rep.print_text()
        print("error: the specification must validate first", file=sys.stderr)
        return 1
    if args.check:
        cfg = json.loads(Path(args.check).read_text(encoding="utf-8"))
        problems = check_config(cfg)
        for p in problems:
            print(f"ERROR {p}")
        print(f"{len(problems)} problem(s)")
        return 1 if problems else 0
    if not args.out:
        ap.error("--out is required unless --check is used")
    vc.refuse_overwrite(args.out)
    cfg = build(spec, vc.read_csv(args.requirements), args.profile, args.version)
    problems = check_config(cfg)
    Path(args.out).write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(cfg['signals'])} signal(s), {len(cfg['checks'])} check(s), "
          f"{len(cfg['tests'])} test(s), {len(cfg['coverage'])} coverage item(s)")
    for p in problems:
        print(f"WARN {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
