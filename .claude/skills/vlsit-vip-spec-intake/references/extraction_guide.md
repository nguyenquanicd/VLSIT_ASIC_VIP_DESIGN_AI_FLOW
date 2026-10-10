# Requirement extraction guide

How to turn a protocol or standard document into a VIP specification written in `VLSIT_ASIC_VIP_Specification_Template.md`. `vip` is `python3 scripts/vip.py`. Start with `vip scaffold <tag> --title "<name>" --standard "<ID rev>" -o <spec.md>`: every rule-driven table is prefilled, and `vip query todo <spec.md>` lists the cells left to fill. The worked example `assets/APB_VIP_Specification.md` shows a filled specification. Rule IDs refer to `VLSIT_VIP_Design_Rule.md`.

## 1. Prepare the source

1. Record the exact document title, document ID, revision, date, and the controlled location. Record known errata as separate references. Never cite "latest".
2. Convert the standard to text without changing the original. For a PDF, prefer `pdftotext -layout <pdf> <txt>`; if no converter is installed, ask the user for a text export. Record the converter and its version in `extraction_report.md`.
3. If the standard is large, ask which clauses, profiles, and roles are in scope. Record the scope in Section 1.1 and the excluded features in Section 3.3 with status `Out of scope`.
4. Do not copy standard text into the specification. Paraphrase each behavior and cite the clause.

## 2. Scan every normative sentence

```text
vip scan scan <standard.txt> --out normative_candidates.csv
```

The scan lists every sentence that contains shall, must, should, may, required, recommended, or a prohibition. Copy the file to `normative_map.csv` and classify each row: `mapped` (a requirement states it), `informative`, `out_of_scope`, or `duplicate`, each with a `ref`. Finish with:

```text
vip scan report normative_map.csv --spec <spec.md> --out normative_report.md
```

Exit status 0 means every candidate is classified and every mapped requirement exists. A requirement without a source sentence is a warning: confirm it comes from the standard and not from memory.

A scan is a safety net, not a substitute for reading. Tables, figures, timing diagrams, and state machines state requirements without modal verbs. Read them and extract those requirements too; cite the table or figure in `Spec ref`.

## 3. Decide each requirement row

One row states one normative behavior. Split a sentence that states several behaviors.

| Field | How to decide |
|---|---|
| Strength | `shall`, `must`, `shall not` give MUST. `should` gives SHOULD. `may`, "is permitted", and optional features give MAY. A sentence the standard marks as a recommendation is SHOULD even without the word. |
| Role | The role that drives the signals the rule constrains. A rule on request signals is `M`; a rule on response signals is `S`. A rule on the shared bus that no single role owns is `B`. |
| Kind | `SIG` for a value, stability, X, or timing rule on signals; `SEQ` for order and handshakes; `TXN` for transaction meaning; `CFG` for parameter and option rules; `CAP` for something the VIP must be able to do or observe. |
| Check type | `SVA` when the rule is decidable cycle by cycle from interface signals. `CLASS` when it needs state across transfers or data structures. `COV` when it only describes a behavior to cover. `NONE` with `NONE:<reason>` when nothing can be observed. A MUST or SHOULD rule is not `COV` or `NONE` unless it cannot be observed at the interface. |
| Signals | Lowercase protocol mnemonics, every signal the rule involves, the one that carries the rule first. |
| Rule key | An uppercase token: `STABLE`, `X`, `SETUP`, `HOLD`, `RANGE`, `ORDER`, ... Together with the first signal it makes the check ID `<TAG>_<ERR\|REC><M\|S\|B>_<SIGNAL>_<RULE>`. The same signal and rule key twice needs an explicit `Check ID`. |
| Profile | `all` or the profile IDs the rule applies to. |
| Bound refs | `BND-nnn` rows for every numeric quantity in the rule. |
| Check expression (Section 8.1) | For every SVA requirement, the property as an antecedent, a consequent, and the operator `SAME` or `NEXT`, over signals of Section 4.3. The generator turns it into a complete assertion and its paired cover, and Gate 1 reviews it. Write `OR` for `||`. |

Make rules orthogonal. Write each property so a single injected violation fires one check only. A check that also fires when another rule is violated makes the negative trace of that rule fail with an unexpected error. Typical technique: stability of a signal is checked only while the select signal is still high, and the select-hold rule is a separate row.

## 4. Boundaries

For every numeric quantity record the valid minimum, the valid maximum, and the first invalid value on each side that exists. If the standard states only one limit, state the other only when it follows from the standard, and write the derivation. A limit that the standard leaves open is a decision row (`DEC-nnn`), not a guess. If a side has no invalid value, write `-`.

## 5. VIP functional model, contract, and plan sections

1. **Item fields:** one per protocol field the VIP drives or observes, plus control fields for delays and error injection. Widths use `PARA_` names.
2. **Capabilities:** one per stimulus or behavior the protocol allows: delays, wait states, back-to-back transfers, errors, optional features. Each has a sequence name `<tag>_<function>_seq`.
3. **Error injections:** one per MUST check at least, mechanism through an item field or a sequence (VP-03 forbids callbacks). Each injection violates exactly one requirement and names it.
4. **Usability contract (UC-01 to UC-13):** propose an answer for each, following VAPI-01 to VAPI-07. Ask the user only where the answer is a project choice.
5. **Checker policy, qualification plan, gates, packaging:** start from the rule defaults. Ask for simulators and seed counts.
6. **Section 13** is generated later by `vlsit-vip-vplan`; leave the template row.

## 6. Decisions and independence

- Record every ambiguity, assumption, dependency, and open question as a row in Section 14 with its impact. An `Open` row that touches a requirement blocks Gate 1 for that requirement.
- Never resolve an ambiguity silently. Present the options and the evidence, recommend one, and ask.
- The specification analysis is reviewed by a person other than the implementer (VQUA-07). Put the review question to the user: who reviews, and by when? Record the answer in QP-02.

## 7. Validate and report

```text
vip validate <spec.md> --json validation_report.json
```

Fix every error. Review every warning. Then write `extraction_report.md` with: the source and revision, the converter, the scanned range, the classification totals, counts of requirements by strength, role, and check type, boundaries, open decisions, sections of the standard not read, and what a reviewer must check by hand. State clearly what was not verified.
