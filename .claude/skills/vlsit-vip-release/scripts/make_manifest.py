#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Write the release manifest of a VIP: version, spec_rev, and the SHA-256 of every file.

Usage:
    python make_manifest.py --vip-dir DIR/<tag>_vip --out vip_manifest.json [--evidence qual_evidence.json ...]
        [--requirements requirements.csv] [--release-notes release_notes.md]

The output file must not exist. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vip_common as vc  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vip-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence", action="append", default=[])
    ap.add_argument("--requirements")
    ap.add_argument("--release-notes")
    args = ap.parse_args()
    vc.refuse_overwrite(args.out)
    root = Path(args.vip_dir)
    cfg_path = root / "spec" / "vip_config.json"
    if not cfg_path.is_file():
        raise SystemExit(f"error: {cfg_path} not found; is this a generated VIP directory?")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    files = {p.relative_to(root).as_posix(): vc.sha256_file(p)
             for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
    extra = {}
    for label, path in [("requirements", args.requirements), ("release_notes", args.release_notes)] + \
            [(f"evidence_{i}", e) for i, e in enumerate(args.evidence)]:
        if path:
            extra[label] = {"path": Path(path).name, "sha256": vc.sha256_file(path)}
    todo = [rel for rel in files if (root / rel).suffix in (".sv", ".svh") and "VIP_TODO" in (root / rel).read_text(encoding="utf-8", errors="replace")]
    manifest = {"schema": "vlsit_vip_manifest/1", "vip": cfg["vip_name"], "version": cfg["version"],
                "spec_rev": cfg["spec_rev"], "profile": cfg["profile"], "created": vc.now_iso(),
                "file_count": len(files), "files": files, "attachments": extra,
                "files_with_VIP_TODO": todo}
    vc.write_json(args.out, manifest)
    print(f"wrote {args.out}: {len(files)} file(s), version {cfg['version']}, spec_rev {cfg['spec_rev']}")
    if todo:
        print(f"WARNING: {len(todo)} file(s) still contain VIP_TODO; a release must have none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
