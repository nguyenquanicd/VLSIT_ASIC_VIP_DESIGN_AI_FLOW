#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the Claude Code and Codex CLI skill folders from one source tree.

Authoring layout:
    .claude/skills/<skill>/        skill-specific files (SKILL.md, README.md, references, scripts, assets)
    shared/ and spec_template/     files that several skills bundle (single source of truth)

This script:
  1. copies each shared file into the skills that bundle it (see MANIFEST),
  2. writes references/BUNDLED_SHA256.txt in every skill (provenance of bundled files),
  3. mirrors .claude/skills/<skill>/ to .agents/skills/<skill>/ for Codex CLI.

Usage:
    python scripts/sync_skills.py            # update files
    python scripts/sync_skills.py --check    # report drift, change nothing (exit 1 on drift)
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE = ROOT / ".claude" / "skills"
CODEX = ROOT / ".agents" / "skills"

SHARED = {
    "vip_common": ("shared/scripts/vip_common.py", "scripts"),
    "validate": ("shared/scripts/validate_vip_spec.py", "scripts"),
    "trace_lint": ("shared/scripts/trace_lint.py", "scripts"),
    "check_env": ("shared/scripts/check_env.py", "scripts"),
    "spec_query": ("shared/scripts/spec_query.py", "scripts"),
    "rule_lookup": ("shared/scripts/rule_lookup.py", "scripts"),
    "stage_brief": ("shared/scripts/stage_brief.py", "scripts"),
    "vip_state": ("shared/scripts/vip_state.py", "scripts"),
    "spec_scaffold": ("shared/scripts/spec_scaffold.py", "scripts"),
    "vip_impact": ("shared/scripts/vip_impact.py", "scripts"),
    "vip_change": ("shared/scripts/vip_change.py", "scripts"),
    "vip": ("shared/scripts/vip.py", "scripts"),
    "template": ("spec_template/VLSIT_ASIC_VIP_Specification_Template.md", "references"),
    "rule": ("spec_template/VLSIT_VIP_Design_Rule.md", "references"),
    "contract": ("shared/references/artifact_contract.md", "references"),
    "overview": ("shared/references/flow_overview.md", "references"),
    "apb_example": ("examples/apb/APB_VIP_Specification.md", "assets"),
}

# Every skill carries the run-aware command line (vip.py) and the scripts it calls directly.
COMMON = ["vip_common", "validate", "trace_lint", "check_env", "spec_query", "rule_lookup", "stage_brief",
          "vip_state", "spec_scaffold", "vip_impact", "vip_change", "vip", "rule", "contract"]
MANIFEST = {
    "vlsit-vip-flow": COMMON + ["template", "overview"],
    "vlsit-vip-spec-intake": COMMON + ["template", "apb_example"],
    "vlsit-vip-vplan": COMMON + ["template"],
    "vlsit-vip-architect": COMMON + ["template"],
    "vlsit-vip-generator": COMMON,
    "vlsit-vip-qualifier": COMMON,
    "vlsit-vip-release": COMMON,
    "vlsit-vip-code-analyzer": COMMON + ["template"],
    "vlsit-vip-bugfix": COMMON + ["template"],
    "vlsit-vip-feature": COMMON + ["template"],
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def planned_bundled(skill: str) -> list[tuple[Path, Path]]:
    out = []
    for key in MANIFEST[skill]:
        src_rel, dest_dir = SHARED[key]
        src = ROOT / src_rel
        out.append((src, CLAUDE / skill / dest_dir / src.name))
    return out


def sums_text(skill: str) -> str:
    lines = ["# SHA-256 of files bundled from the repository source tree. Do not edit; run scripts/sync_skills.py."]
    for src, dest in planned_bundled(skill):
        lines.append(f"{sha(src)}  {dest.relative_to(CLAUDE / skill).as_posix()}  <- {src.relative_to(ROOT).as_posix()}")
    return "\n".join(lines) + "\n"


def tree(dirpath: Path) -> dict[str, bytes]:
    return {p.relative_to(dirpath).as_posix(): p.read_bytes()
            for p in sorted(dirpath.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report drift without changing files")
    args = ap.parse_args()
    drift: list[str] = []

    for skill in MANIFEST:
        sdir = CLAUDE / skill
        if not (sdir / "SKILL.md").is_file():
            drift.append(f"{skill}: SKILL.md is missing")
            continue
        for src, dest in planned_bundled(skill):
            if not src.is_file():
                drift.append(f"{skill}: shared source missing: {src.relative_to(ROOT)}")
                continue
            if not dest.is_file() or dest.read_bytes() != src.read_bytes():
                drift.append(f"{skill}: {dest.relative_to(CLAUDE)} differs from {src.relative_to(ROOT)}")
                if not args.check:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dest)
        sums = sdir / "references" / "BUNDLED_SHA256.txt"
        text = sums_text(skill)
        if not sums.is_file() or sums.read_text(encoding="utf-8") != text:
            drift.append(f"{skill}: references/BUNDLED_SHA256.txt is out of date")
            if not args.check:
                sums.parent.mkdir(parents=True, exist_ok=True)
                sums.write_text(text, encoding="utf-8", newline="\n")
        # mirror to Codex
        cdir = CODEX / skill
        a, b = tree(sdir), (tree(cdir) if cdir.is_dir() else {})
        for rel in sorted(set(a) | set(b)):
            if a.get(rel) != b.get(rel):
                drift.append(f"{skill}: Codex copy differs at {rel}")
                if not args.check:
                    target = cdir / rel
                    if rel in a:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(a[rel])
                    elif target.is_file():
                        target.unlink()

    # shared files must not be edited inside a skill
    for d in drift:
        print(("DRIFT " if args.check else "synced ") + d)
    if args.check:
        print(f"{len(drift)} difference(s)")
        return 1 if drift else 0
    print(f"sync complete: {len(drift)} change(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
