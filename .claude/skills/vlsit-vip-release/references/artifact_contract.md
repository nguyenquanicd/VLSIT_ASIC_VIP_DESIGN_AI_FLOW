# VLSIT VIP flow artifact contract

This file defines the names, formats, and meanings of every artifact exchanged between the stages of the VLSIT ASIC VIP Design AI Flow. Every skill reads this contract and the scripts depend on it. Do not invent other formats. Vocabulary, IDs, and rules come from `VLSIT_VIP_Design_Rule.md` (rule IDs `V...`).

## 1. Run directory

One run builds one VIP for one specification. The flow creates a new numbered run directory and never reuses or overwrites an existing one.

```text
<OUTPUT_ROOT>/<tag>_vip_run_NNN/
  vip_state.json                 flow state and gate approvals
  01_spec/
    <tag>_vip_spec.md            specification approved at Gate 1 (copy; the source is never modified)
    validation_report.json       output of validate_vip_spec.py
    extraction_report.md         source-coverage report from the intake stage
  02_plan/
    requirements.csv             requirement and trace IDs (Section 3)
    traceability.csv             compact trace view
    traceability_table.md        body of specification Section 13
    vplan.md                     human-readable verification plan
    plan_report.json
  03_arch/
    vip_config.json              machine-readable architecture (Section 4)
    vip_arch.md                  architecture and API description for review
  04_vip/<tag>_vip/              generated VIP tree (layout of VFIL-03)
  05_qual/
    qual_evidence.json           evidence per trace and variant (Section 5)
    qualification_report.md
    logs/                        simulator and lint logs, one file per run
    run_summary.json
  06_release/
    release_notes.md
    vip_manifest.json            file list with SHA-256, version, spec_rev
    trace_report.md
```

`<OUTPUT_ROOT>/.vip_current` holds the path of the newest run, so `vip` finds it without arguments (it also searches upward from the current directory and honors `$VLSIT_VIP_RUN`). `05_qual/compile_logs/check_NNN/` holds the logs of `vip check-vip`. `<tag>` is the lowercase protocol tag from the specification front matter. When a specification has several profiles, each profile is a separate build: use `04_vip/<tag>_vip/` for the first profile and `04_vip_<profile>/<tag>_vip/` for the others, with one evidence file each (`05_qual/qual_evidence_<profile>.json`).

## 2. Status vocabulary

| Where | Values |
|---|---|
| Requirement status (`requirements.csv`) | `draft`, `reviewed`, `planned`, `implemented`, `qualified`, `waived`, `withdrawn` |
| Evidence status | `PASS`, `FAIL`, `NOT_RUN`, `N/A` (`N/A` needs a note with the reason) |
| Gate status | `PENDING`, `APPROVED`, `REJECTED` |
| Specification status (front matter) | `Draft`, `Review`, `Approved`, `Released` |

`PASS` requires a log reference. A missing tool, log, or run is `NOT_RUN`. User acceptance never converts `NOT_RUN` or `FAIL` into `PASS`.

## 3. requirements.csv

UTF-8, comma-separated, header row, one row per requirement. Written by `extract_requirements.py`; later stages update `status`, `reviewer`, and `notes` only.

| Column | Meaning |
|---|---|
| `req_id` | `VREQ-<TAG>-<NNNN>`; permanent, never reused (VNAM-03) |
| `strength` | `MUST`, `SHOULD`, or `MAY` |
| `role` | `M`, `S`, or `B` |
| `kind` | `SIG`, `SEQ`, `TXN`, `CFG`, or `CAP` |
| `text` | paraphrased requirement |
| `spec_ref` | `REF-nnn` plus clause |
| `profile` | `all` or `PROF-nn` list |
| `signals` | lowercase protocol mnemonics, comma-separated |
| `rule_key` | uppercase rule token |
| `check_type` | `SVA`, `CLASS`, `COV`, or `NONE` |
| `chk_id` | check ID `<TAG>_<ERR\|REC><M\|S\|B>_<SIGNAL>_<RULE>`, or `-` |
| `bound_refs` | `BND-nnn` list or `-` |
| `cov_id` | `COV_<TAG>_<NNNN>` or `-` |
| `seq_id` | stimulus sequence names from `CAP` rows, `;`-separated, or `-` |
| `inj_id` | `INJ-nnn` list from the injection table, `;`-separated, or `-` |
| `test_pos` / `test_neg` | `qual_<chk_id lowercase>_pos` / `_neg`; capability tests `qual_cap_nnn_cap`; or `-` |
| `status` | requirement status |
| `reviewer` | person who reviewed the requirement (VQUA-07) |
| `notes` | `NONE:`, `COV:`, or `waived:` reasons, free text |

## 4. vip_config.json

Written by `derive_vip_config.py` from the validated specification, `requirements.csv`, and one selected profile. The architect reviews and may edit it; the generator reads it. Schema `vlsit_vip_config/1`.

| Key | Content |
|---|---|
| `schema`, `tag`, `vip_name`, `version`, `spec_rev` | identity; `version` is the VIP semantic version, `spec_rev` the locked standard revision |
| `profile`, `options` | selected profile ID and its option IDs |
| `clock` | `signal`, `reset`, `reset_active_low` |
| `parameters` | list of `name`, `default`, `legal`, `unit`, `description`, `macro` (the define that binds the class library, for example `APB_VIP_ADDR_W`) |
| `signals` | list of `name`, `width` (number or expression), `driver` (`M`, `S`, `CLK`, `RST`), `reset`, `description` |
| `roles` | list of `id`, `letter`, `mode`, `drives` |
| `item_fields`, `knobs`, `caps`, `injections`, `sequences` | rows of the corresponding specification tables |
| `checks` | list of `id`, `type`, `role`, `strength`, `is_rec`, `req_id`, `spec_ref`, `text`, `signals`, `cov_id`, `index` (position in the checker enable vector), `expr` (`op`, `ante`, `cons`, `msg` from Section 8.1, or null for a stub) |
| `monitors` | rows of the monitor table |
| `coverage` | list of `id`, `req_id`, `bound` (a `bounds` entry or null) |
| `bounds` | rows of the boundary table with numeric limits |
| `tests` | list of `name`, `kind` (`pos`, `neg`, `cap`), `check`, `req_id` |
| `architecture` | `base` package, `uvm` version, build-or-reuse decision |

## 5. qual_evidence.json

Written by `create_qual_matrix.py` (all `NOT_RUN`) and updated only by `collect_qual_results.py` from logs. Schema `vlsit_vip_qual_evidence/1`.

```json
{
  "schema": "vlsit_vip_qual_evidence/1",
  "vip": "apb_vip", "profile": "PROF-01", "spec_rev": "...",
  "variants": ["VAR-01", "VAR-02"],
  "lint":     {"status": "NOT_RUN", "log": ""},
  "compile":  {"status": "NOT_RUN", "log": ""},
  "coverage": {"status": "NOT_RUN", "database": "", "summary": ""},
  "entries": [
    {"test": "qual_apb_errm_paddr_stable_pos", "variant": "VAR-01", "kind": "pos",
     "req_id": "VREQ-APB-0001", "chk_id": "APB_ERRM_PADDR_STABLE",
     "status": "NOT_RUN", "seeds": [], "log": "", "note": ""}
  ]
}
```

## 6. vip_state.json

Written only by `vip_state.py`. Schema `vlsit_vip_state/1`.

| Key | Content |
|---|---|
| `tag`, `run`, `created` | identity |
| `settings` | author, project, profile, reviewer, build_cmd, run_cmd, seeds, uvm_home, version (`vip set`, `vip get`) |
| `spec` | `source` path and `sha256` at run creation |
| `stage` | current stage `S0` to `S7` |
| `gates` | `G1` spec, `G2` plan and architecture, `G3` qualification evidence, `G4` release; each has `status`, `by`, `date`, `note`, `artifacts` (file to SHA-256) |
| `history` | time-stamped events |

A gate is `APPROVED` only after the user replied APPROVE in chat to the presented version. The approval records the hashes of the approved artifacts; if an artifact changes afterwards, the gate is reopened.

## 7. Log line conventions

| Producer | Line |
|---|---|
| Protocol check (UVM) | `UVM_ERROR ... [<check_id>] <req_id> <spec_ref>: <text>` for ERR checks; `UVM_WARNING` for REC checks |
| Unimplemented check | `UVM_WARNING ... [<check_id>] VIP_TODO check is not implemented` |
| Qualification test result | `VLSIT_VIP_QUAL_RESULT test=<name> seed=<n> status=<PASS\|FAIL> expected=<n> unexpected=<n> missing=<n>`; the seed comes from `+VLSIT_SEED=<n>`, which the runner appends to the run command |
| Expected-error catcher | `VLSIT_VIP_CATCHER id=<check_id> min=<n> max=<n> seen=<n> status=<OK\|FAIL>` |

`collect_qual_results.py` parses only the `VLSIT_VIP_QUAL_RESULT` and `VLSIT_VIP_CATCHER` lines. A test with no result line is `NOT_RUN`.

## 8. Source markers

| Marker | Meaning |
|---|---|
| `VIP_TODO(<id>)` | A stub of check, coverage item, or test `<id>` that is not implemented. `trace_lint.py` finds stubs by this marker. Remove the marker only when the item is implemented. |
| `spec_rev` | String in the VIP package that records the locked standard revision (VFIL-06) |
