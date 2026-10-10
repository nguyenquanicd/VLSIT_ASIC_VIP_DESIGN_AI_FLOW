#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the VLSIT ASIC VIP Design AI Flow scripts.

Standard library only. This module parses the VIP specification markdown
(front matter, numbered sections, machine-readable tables) and defines the
ID formats, table schemas, and the requirements.csv schema used by every
stage of the flow.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

# --------------------------------------------------------------------------
# Specification structure
# --------------------------------------------------------------------------

SPEC_SECTIONS = [
    (1, "Purpose, scope, and context"),
    (2, "Normative references and precedence"),
    (3, "Roles, profiles, and options"),
    (4, "Interface definition"),
    (5, "Protocol requirements"),
    (6, "VIP functional model"),
    (7, "VIP API and usability contract"),
    (8, "Checker requirements"),
    (9, "Coverage requirements"),
    (10, "Sequences and compliance tests"),
    (11, "Qualification plan"),
    (12, "Deliverables and packaging"),
    (13, "Traceability matrix"),
    (14, "Assumptions, dependencies, and decisions"),
    (15, "Glossary"),
    (16, "References used to shape this template"),
]

FRONT_MATTER_KEYS = [
    "document_type", "document_id", "title", "vip_name", "proto_tag", "version",
    "status", "spec_revision_locked", "language", "vip_rules", "rtl_rules",
]
DOCUMENT_TYPE = "asic_vip_specification"
STATUS_VALUES = ["Draft", "Review", "Approved", "Released"]

# kind -> (ordered column names, id regex or None)
TABLE_SCHEMAS: dict[str, dict] = {
    "references": {"columns": ["Ref ID", "Document and revision", "Applicable clauses", "Authority / notes"], "id": r"^REF-\d{3}$"},
    "compliance": {"columns": ["Standard", "Revision / profile", "Role implemented", "Options", "Deviations"], "id": None},
    "candidates": {"columns": ["Candidate", "Source", "Requirement coverage", "Decision", "Reason"], "id": None},
    "environment": {"columns": ["Item", "Specification"], "id": None},
    "roles": {"columns": ["Role ID", "Role", "Letter", "Drives", "Mode"], "id": r"^ROLE-\d{2}$"},
    "profiles": {"columns": ["Profile ID", "Profile", "Standard revision", "Included options", "Notes"], "id": r"^PROF-\d{2}$"},
    "options": {"columns": ["Option ID", "Optional feature", "Signals added", "Default", "Status"], "id": r"^OPT-\d{2}$"},
    "variants": {"columns": ["Variant ID", "Profile", "Options", "Parameter values", "Qualification target"], "id": r"^VAR-\d{2}$"},
    "clocks": {"columns": ["Domain", "Clock signal", "Reset signal", "Reset polarity", "Notes"], "id": None},
    "parameters": {"columns": ["Parameter", "Description", "Default", "Legal values", "Unit"], "id": r"^PARA_[A-Z0-9_]+$"},
    "signals": {"columns": ["Signal", "Width", "Driver", "Profile / option", "Reset / idle", "Description"], "id": r"^[a-z][a-z0-9_]*$"},
    "timing": {"columns": ["Cycle / event", "Condition", "Observable result"], "id": None},
    "checkexpr": {"columns": ["Req ID", "Operator", "Antecedent", "Consequent", "Message"], "id": None},
    "requirements": {"columns": ["Req ID", "Strength", "Role", "Kind", "Requirement", "Spec ref", "Profile", "Signals", "Rule key", "Check type", "Check ID", "Bound refs", "Notes"], "id": r"^VREQ-[A-Z0-9]+-\d{4}$"},
    "boundaries": {"columns": ["Bound ID", "Quantity", "Unit", "Valid min", "Valid max", "Invalid below", "Invalid above", "Derivation", "Source req"], "id": r"^BND-\d{3}$"},
    "items": {"columns": ["Item field", "Type", "Width", "Rand", "Description", "Roles"], "id": r"^[a-z][a-z0-9_]*$"},
    "caps": {"columns": ["Cap ID", "Role", "Capability", "Config knobs", "Sequence", "Requirements"], "id": r"^CAP-\d{3}$"},
    "injections": {"columns": ["Inj ID", "Role", "Violation to inject", "Mechanism", "Violated requirement", "Expected check"], "id": r"^INJ-\d{3}$"},
    "monitors": {"columns": ["Monitor ID", "Observed event", "Transaction produced", "Analysis port", "Notes"], "id": r"^MON-\d{3}$"},
    "knobs": {"columns": ["Knob", "Type", "Default", "Description", "Related"], "id": r"^[a-z][a-z0-9_]*$"},
    "contract": {"columns": ["Contract ID", "Topic", "Specification"], "id": r"^UC-\d{2}$"},
    "policy": {"columns": ["Policy ID", "Topic", "Specification"], "id": r"^CP-\d{2}$"},
    "covreq": {"columns": ["Cov Req ID", "Goal", "Requirements", "Bins / crosses", "Notes"], "id": r"^CVR-\d{3}$"},
    "seqs": {"columns": ["Seq ID", "Sequence", "Role", "Purpose", "Requirements"], "id": r"^SEQ-\d{3}$"},
    "qualplan": {"columns": ["Qual ID", "Topic", "Specification"], "id": r"^QP-\d{2}$"},
    "gates": {"columns": ["Gate", "Criteria"], "id": r"^VIP-[0-3]$"},
    "packaging": {"columns": ["Pkg ID", "Item", "Specification"], "id": r"^PK-\d{2}$"},
    "trace": {"columns": ["Req ID", "Check ID", "Cov ID", "Sequence / injection", "Test pos", "Test neg", "Status"], "id": None},
    "decisions": {"columns": ["Decision ID", "Type", "Statement", "Impact", "Resolution / status"], "id": r"^[A-Z]{3}-\d{3}$"},
    "glossary": {"columns": ["Term", "Definition"], "id": None},
}

# Tables that must contain at least one row in a filled specification.
REQUIRED_TABLES = [
    "references", "roles", "profiles", "signals", "requirements", "items",
    "caps", "contract", "policy", "qualplan", "gates", "packaging",
]
FIXED_ID_TABLES = {
    "contract": [f"UC-{i:02d}" for i in range(1, 14)],
    "policy": [f"CP-{i:02d}" for i in range(1, 8)],
    "qualplan": [f"QP-{i:02d}" for i in range(1, 8)],
    "gates": [f"VIP-{i}" for i in range(0, 4)],
    "packaging": [f"PK-{i:02d}" for i in range(1, 6)],
}

# Sections that must hold a table of the given kind or an "N/A:" paragraph.
SECTION_TABLES = {
    "1.2": "candidates", "1.3": "environment", "2.1": "references", "2.3": "compliance",
    "3.1": "roles", "3.2": "profiles", "3.3": "options", "3.4": "variants",
    "4.1": "clocks", "4.2": "parameters", "4.3": "signals", "4.4": "timing",
    "5.2": "requirements", "5.3": "requirements", "5.4": "requirements", "5.5": "requirements",
    "5.6": "boundaries", "8.1": "checkexpr", "6.1": "items", "6.2": "caps", "6.3": "injections", "6.4": "monitors",
    "7.1": "knobs", "7.2": "contract", "8": "policy", "9": "covreq", "10": "seqs",
    "11": "qualplan", "12": "packaging", "13": "trace", "14": "decisions", "15": "glossary",
}

CHECK_OPS = {"SAME": "|->", "NEXT": "|=>"}
SVA_FUNCS = {"$stable", "$past", "$rose", "$fell", "$changed", "$onehot", "$onehot0", "$isunknown", "$countones"}
SVA_WORDS = {"inside"}
STRENGTHS = ["MUST", "SHOULD", "MAY"]
ROLE_LETTERS = ["M", "S", "B"]
KINDS = ["SIG", "SEQ", "TXN", "CFG", "CAP"]
CHECK_TYPES = ["SVA", "CLASS", "COV", "NONE"]
DRIVERS = ["M", "S", "CLK", "RST"]
RESET_POLARITY = ["Active-low", "Active-high"]
RAND_VALUES = ["rand", "randc", "none"]
OPTION_STATUS = ["In scope", "Out of scope"]
DECISION_TYPES = ["Assumption", "Dependency", "Decision", "Open"]
ROLE_MODES = ["ACTIVE", "PASSIVE"]
MODAL = {"MUST": re.compile(r"\b(shall|must)\b", re.I),
         "SHOULD": re.compile(r"\bshould\b", re.I),
         "MAY": re.compile(r"\bmay\b", re.I)}

CHECK_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*_(ERR|REC)[MSB]_[A-Z0-9]+(?:_[A-Z0-9]+)*$")
REQ_ID_RE = re.compile(r"^VREQ-([A-Z0-9]+)-(\d{4})$")
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^<>\n]{0,78}>")
TAG_RE = re.compile(r"^[a-z][a-z0-9]{1,7}$")

REQ_COLUMNS = [
    "req_id", "strength", "role", "kind", "text", "spec_ref", "profile", "signals",
    "rule_key", "check_type", "chk_id", "bound_refs", "cov_id", "seq_id", "inj_id",
    "test_pos", "test_neg", "status", "reviewer", "notes",
]
REQ_STATUS = ["draft", "reviewed", "planned", "implemented", "qualified", "waived", "withdrawn"]


def translate_expr(text: str) -> str:
    """Spec check expressions avoid the pipe character (it splits markdown cells): OR means ||."""
    return re.sub(r"\s+OR\s+", " || ", text.strip())


_LITERAL_RE = re.compile(r"\d*'[sS]?[bBoOdDhH][0-9a-fA-F_xXzZ?]+|'[01xXzZ]|\d[\d_]*")


def expr_identifiers(text: str) -> tuple[set[str], list[str]]:
    """Return (identifiers, problems) of a check expression after OR translation."""
    problems: list[str] = []
    t = translate_expr(text)
    if t.count("(") != t.count(")"):
        problems.append("unbalanced parentheses")
    stripped = _LITERAL_RE.sub(" ", re.sub(r'"[^"]*"', " ", t))
    funcs = set(re.findall(r"\$[A-Za-z_][A-Za-z0-9_]*", stripped))
    for f in funcs - SVA_FUNCS:
        problems.append(f"system function {f} is not allowed")
    stripped = re.sub(r"\$[A-Za-z_][A-Za-z0-9_]*", " ", stripped)
    rest = re.sub(r"\|\|", " ", stripped)
    if "|" in rest or "##" in rest or "[*" in rest or ";" in rest:
        problems.append("only single-cycle boolean expressions are allowed (no |, ##, [*, ;)")
    idents = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", rest)) - SVA_WORDS
    return idents, problems


def norm_key(header: str) -> str:
    """Convert a table header to a snake_case dictionary key."""
    return re.sub(r"[^a-z0-9]+", "_", header.lower()).strip("_")


# --------------------------------------------------------------------------
# Markdown parsing
# --------------------------------------------------------------------------

@dataclass
class Section:
    number: str
    title: str
    line: int
    level: int
    end: int = 0


@dataclass
class Table:
    kind: str | None
    header: list[str]
    rows: list[list[str]]
    line: int
    section: str

    def dict_rows(self) -> list[dict]:
        keys = [norm_key(h) for h in self.header]
        out = []
        for i, row in enumerate(self.rows):
            d = {k: (row[j] if j < len(row) else "") for j, k in enumerate(keys)}
            d["_line"] = self.line + 2 + i
            d["_section"] = self.section
            out.append(d)
        return out


@dataclass
class Spec:
    path: Path
    lines: list[str]
    front: dict[str, str]
    front_end: int
    sections: list[Section]
    tables: list[Table]

    def rows(self, kind: str) -> list[dict]:
        out: list[dict] = []
        for t in self.tables:
            if t.kind == kind:
                out.extend(t.dict_rows())
        return out

    def tables_of(self, kind: str) -> list[Table]:
        return [t for t in self.tables if t.kind == kind]

    def section_text(self, number: str) -> str:
        for s in self.sections:
            if s.number == number:
                return "\n".join(self.lines[s.line:s.end])
        return ""

    @property
    def tag(self) -> str:
        return self.front.get("proto_tag", "").strip()


_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_HEAD_RE = re.compile(r"^(#{2,4})\s+(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$")


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    s = s.replace("\\|", "\u0001")
    return [c.replace("\u0001", "|").strip() for c in s.split("|")]


def parse_front_matter(lines: list[str]) -> tuple[dict[str, str], int]:
    front: dict[str, str] = {}
    if not lines or lines[0].strip() != "---":
        return front, 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return front, i + 1
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", lines[i])
        if m:
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            front[m.group(1)] = v
    return front, 0


def classify_table(header: list[str]) -> str | None:
    norm = [h.strip().lower() for h in header]
    for kind, schema in TABLE_SCHEMAS.items():
        if norm == [c.lower() for c in schema["columns"]]:
            return kind
    return None


def load_spec(path: str | Path) -> Spec:
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines()
    front, front_end = parse_front_matter(lines)
    sections: list[Section] = []
    tables: list[Table] = []
    in_fence = False
    fence_mark = ""
    current = ""
    i = front_end
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            mark = stripped[:3]
            if not in_fence:
                in_fence, fence_mark = True, mark
            elif mark == fence_mark:
                in_fence = False
            i += 1
            continue
        if in_fence:
            i += 1
            continue
        m = _HEAD_RE.match(line)
        if m:
            sections.append(Section(m.group(2), m.group(3), i + 1, len(m.group(1))))
            current = m.group(2)
            i += 1
            continue
        if (stripped.startswith("|") and i + 1 < len(lines)
                and _SEP_RE.match(lines[i + 1]) and "|" in lines[i + 1]):
            header = split_row(line)
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            tables.append(Table(classify_table(header), header, rows, i + 1, current))
            i = j
            continue
        i += 1
    for k, s in enumerate(sections):
        s.end = sections[k + 1].line - 1 if k + 1 < len(sections) else len(lines)
    return Spec(p, lines, front, front_end, sections, tables)


def strip_inline_code(line: str) -> str:
    return re.sub(r"`[^`]*`", "", line)


def find_placeholders(spec: Spec) -> list[tuple[int, str]]:
    """Return (line, token) for angle-bracket placeholders outside code and quotes."""
    found: list[tuple[int, str]] = []
    in_fence = False
    for n, line in enumerate(spec.lines, start=1):
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence or s.startswith(">"):
            continue
        for tok in PLACEHOLDER_RE.findall(strip_inline_code(line)):
            found.append((n, tok))
    return found


def has_na_paragraph(text: str) -> bool:
    return bool(re.search(r"^\s*(\*\*)?N/A:?(\*\*)?:?\s*\S+", text, re.M))


# --------------------------------------------------------------------------
# IDs and conversions
# --------------------------------------------------------------------------

def split_list(cell: str) -> list[str]:
    """Split a comma/semicolon/space separated cell, dropping '-' and empties."""
    parts = re.split(r"[,;\s]+", cell.strip())
    return [p for p in parts if p and p != "-"]


def derive_check_id(tag: str, strength: str, role: str, signals: str, rule_key: str) -> str:
    prefix = "ERR" if strength.upper() == "MUST" else "REC"
    sigs = split_list(signals)
    sig = re.sub(r"[^A-Za-z0-9]+", "_", sigs[0]).upper().strip("_") if sigs else "BUS"
    rule = re.sub(r"[^A-Za-z0-9]+", "_", rule_key).upper().strip("_")
    return f"{tag.upper()}_{prefix}{role.upper()}_{sig}_{rule}"


def req_number(req_id: str) -> str:
    m = REQ_ID_RE.match(req_id)
    return m.group(2) if m else ""


def parse_number(text: str):
    """Parse an int, hex, or decimal value; return Decimal or None."""
    t = text.strip().replace("_", "")
    if not t or t == "-":
        return None
    try:
        if re.fullmatch(r"[+-]?0[xX][0-9a-fA-F]+", t):
            return Decimal(int(t, 16))
        return Decimal(t)
    except (InvalidOperation, ValueError):
        return None


def lower_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def tests_for(chk_id: str) -> tuple[str, str]:
    base = lower_id(chk_id)
    return f"qual_{base}_pos", f"qual_{base}_neg"


def cap_test(cap_id: str) -> str:
    return f"qual_{lower_id(cap_id)}_cap"


# --------------------------------------------------------------------------
# requirements.csv
# --------------------------------------------------------------------------

def spec_requirements(spec: Spec) -> list[dict]:
    """Build requirements.csv rows (authoring fields only) from the spec."""
    rows = []
    for r in spec.rows("requirements"):
        row = {c: "" for c in REQ_COLUMNS}
        row.update({
            "req_id": r["req_id"], "strength": r["strength"].upper(), "role": r["role"].upper(),
            "kind": r["kind"].upper(), "text": r["requirement"], "spec_ref": r["spec_ref"],
            "profile": r["profile"], "signals": r["signals"], "rule_key": r["rule_key"],
            "check_type": r["check_type"].upper(), "chk_id": r["check_id"],
            "bound_refs": r["bound_refs"], "notes": r["notes"], "status": "draft",
        })
        rows.append(row)
    return rows


def write_csv(path: str | Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def read_csv(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

@dataclass
class Finding:
    severity: str  # ERROR, WARN, INFO
    code: str
    message: str
    line: int = 0


@dataclass
class Report:
    title: str
    source: str
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str, line: int = 0) -> None:
        self.findings.append(Finding(severity, code, message, line))

    def error(self, code: str, message: str, line: int = 0) -> None:
        self.add("ERROR", code, message, line)

    def warn(self, code: str, message: str, line: int = 0) -> None:
        self.add("WARN", code, message, line)

    def info(self, code: str, message: str, line: int = 0) -> None:
        self.add("INFO", code, message, line)

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "ERROR")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARN")

    def print_text(self, stream=None, full: bool = False, per_code: int = 3) -> None:
        """Print a compact report: findings are grouped by code and each code shows at most
        `per_code` examples, then a count of the rest. `full=True` prints every finding."""
        stream = stream or sys.stdout
        print(f"{self.title}: {self.source}", file=stream)
        shown: dict[str, int] = {}
        hidden: dict[tuple[str, str], int] = {}
        for f in self.findings:
            n = shown.get(f.code, 0)
            if not full and n >= per_code:
                key = (f.severity, f.code)
                hidden[key] = hidden.get(key, 0) + 1
                continue
            shown[f.code] = n + 1
            loc = f" (line {f.line})" if f.line else ""
            print(f"  {f.severity:5s} {f.code}{loc}: {f.message}", file=stream)
        for (sev, code), k in hidden.items():
            print(f"  {sev:5s} {code}: ... and {k} more of the same code (use --full)", file=stream)
        print(f"  summary: {self.errors} error(s), {self.warnings} warning(s)", file=stream)

    def to_json(self) -> dict:
        return {
            "title": self.title, "source": self.source,
            "errors": self.errors, "warnings": self.warnings,
            "findings": [f.__dict__ for f in self.findings],
        }


def write_json(path: str | Path, data) -> None:
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def refuse_overwrite(path: str | Path) -> None:
    if Path(path).exists():
        raise SystemExit(f"error: output exists and will not be overwritten: {path}")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
