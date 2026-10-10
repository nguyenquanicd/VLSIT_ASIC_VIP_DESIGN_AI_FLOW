# VLSIT ASIC VIP Design AI Flow: overview

The flow turns a protocol or standard specification into a qualified, documented, easy-to-use SystemVerilog/UVM Verification IP (VIP). It is built from seven skills. Each skill owns one stage, reads the artifacts of the previous stage, and writes its own, as defined in `artifact_contract.md`. All skills share one run-aware command, `vip` (`python3 scripts/vip.py`).

## 1. Principles

1. **Protocol specification first.** The VIP specification is derived from the standard. A person other than the implementer reviews the extracted requirements.
2. **One input format.** Every run starts from a VIP specification in `VLSIT_ASIC_VIP_Specification_Template.md`. A raw standard is converted by `vlsit-vip-spec-intake`. A specification that fails `vip validate` is never used downstream.
3. **Every requirement is traceable.** Requirement to check, coverage item, stimulus or injection, positive trace, negative trace, and result; `vip lint` enforces it at every stage.
4. **The property is reviewed before it runs.** The check expression of each SVA requirement is in the specification (Section 8.1), so Gate 1 reviews the property that the generated checker implements.
5. **The VIP is a design under test.** Each check has a passing positive trace and a negative trace that produces exactly one declared error, against an independent counterpart.
6. **Evidence, not assertions.** A result is `PASS` only with a log. Missing tools, runs, or logs are `NOT_RUN`. User acceptance never changes a result.
7. **The user decides at gates.** The flow stops at four sign-off gates and never assumes approval.
8. **Never guess; never overwrite.** Ask for a missing input; record each ambiguity as a decision; every run uses a new numbered directory.

## 2. Stages, skills, and gates

| Stage | Skill | Writes | Gate or check at the end |
|---|---|---|---|
| S0 Scope and reuse | `vlsit-vip-spec-intake` | specification skeleton | none |
| S1 Requirement extraction | `vlsit-vip-spec-intake` | `<tag>_vip_spec.md`, extraction report | **Gate 1** (VIP-0) |
| S2 vPlan and traceability | `vlsit-vip-vplan` | `requirements.csv`, `vplan.md` | `vip lint plan` |
| S3 Architecture and API | `vlsit-vip-architect` | `vip_config.json`, `vip_arch.md` | **Gate 2** |
| S4 Generate and implement | `vlsit-vip-generator` | `04_vip/<tag>_vip/` | **VIP-1** automatic: `vip check-vip`, `vip lint impl` |
| S5 Qualification | `vlsit-vip-qualifier` | evidence, logs, report | **Gate 3** (VIP-2) |
| S6 Package and trial | `vlsit-vip-release` | README, trial record | trial |
| S7 Sign-off and maintenance | `vlsit-vip-release` | release notes, manifest | **Gate 4** (VIP-3) |

`vlsit-vip-flow` creates the run, tracks `vip_state.json`, checks prerequisites, and routes the stages. Each stage skill also works alone when its inputs exist.

## 3. Gate approval protocol

At a gate present the version and the evidence summary, then ask: "Do you approve `<artifact>` version N, including `<scope>`? Reply APPROVE, REVISE, or STOP." Record `APPROVED` with `vip gate` only after an explicit APPROVE in chat. An approval covers exactly the listed artifacts and scope; their hashes are stored and a changed artifact reopens the gate and every later gate.

## 4. Inputs the flow asks for

Ask only for what is missing, in one concise question: the specification (or the standard with roles and profile); the output root; project name and human author; simulator(s) and UVM version, lint tool, and formal use; the profile to build first; existing VIP to reuse.

## 5. Invocation

| Tool | Orchestrator | Single stage |
|---|---|---|
| Claude Code | `/vlsit-vip-flow ...` | `/vlsit-vip-vplan ...` |
| Codex CLI | `$vlsit-vip-flow ...` | `$vlsit-vip-vplan ...` |

The skills are identical for both tools; only the folder differs (`.claude/skills`, `.agents/skills`).

## 6. The `vip` command

| Group | Commands |
|---|---|
| Run | `init ROOT TAG [SPEC]`, `status`, `next`, `brief [S#]`, `set k=v`, `get`, `doctor` |
| Gates | `gate G# APPROVED --by NAME`, `stage S#`, `require S#`, `check [S#]` |
| Specification | `scaffold TAG ...`, `validate`, `query outline|rows|get|refs|todo`, `scan scan|report`, `rules ID|PREFIX` |
| Plan, architecture | `plan`, `lint [stage]`, `config` |
| Generate, build | `gen`, `worklist`, `impl-check`, `check-vip` |
| Qualify, release | `qual-init`, `qual-run`, `qual-collect`, `qual-item`, `manifest`, `diff` |

Scripts use only the Python standard library and never overwrite an output. Tools they use when present: slang and Verilator (`vip doctor` shows what was found), and the Accellera UVM reference implementation for the compile check (`python3 scripts/check_env.py --install-uvm <DIR>` installs the pinned tag).

## 7. Token efficiency

The flow is built so that an agent spends tokens on engineering, not on reading and retyping.

| Feature | Effect |
|---|---|
| `vip` finds the run and holds paths and settings | Commands are a few words; no long paths |
| Compact output: findings grouped by code, three examples each, the rest counted; run path shortened to `<run>` | A lint with hundreds of findings prints about ten lines; `--full` shows all |
| `vip scaffold` prefills every rule-driven table | The agent writes only protocol facts |
| `vip query` (outline, rows, get, refs, todo) | Read one row or table instead of the whole specification |
| `vip rules <PREFIX>` prints exact rule text by group | Read the groups a task touches instead of the whole rule file |
| `vip brief` per stage | One screen replaces several reference documents |
| Check expressions in the specification (Section 8.1) | Assertions are generated complete and reviewed at Gate 1; no hand editing of the checker |
| Complete generated tests | Qualification needs only one stimulus task per trace in the counterpart |
| `vip worklist` | Lists the remaining stubs with requirement context and the code region; the agent opens nothing else |
| `vip impl-check` | Completes one SVA stub from an expression and prints the specification row to add |
| `vip check-vip` | Lint and UVM type-check in one command, a few lines out, full output in a log |
| `vip next`, `vip check` | The next action and the exit check without reasoning over state |

SKILL.md files are short; details live in references that are opened on demand.
