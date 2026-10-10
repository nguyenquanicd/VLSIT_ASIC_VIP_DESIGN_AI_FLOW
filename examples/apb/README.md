# APB worked example / Ví dụ APB

**EN:** `APB_VIP_Specification.md` is a filled specification for the AMBA APB protocol. It shows how to fill the template and is the data used to test the scripts. Clause references use clause titles; clause numbers were not verified (DEC-001). Confirm every reference against the controlled standard before a release.

**VI:** `APB_VIP_Specification.md` là spec APB đã điền, dùng để minh họa cách điền template và để chạy thử script. Tham chiếu điều khoản dùng tên điều khoản vì chưa kiểm số điều khoản (DEC-001); phải đối chiếu với standard gốc trước khi phát hành.

## Run the chain with `vip` / Chạy cả chuỗi bằng lệnh `vip`

Run from the repository root with Python 3.11 or later. `vip` is `python3 .claude/skills/vlsit-vip-flow/scripts/vip.py` (Codex copy: `.agents/skills/...`). On Windows with the OSS CAD Suite, activate it first.

    vip doctor
    vip init <OUT> apb examples/apb/APB_VIP_Specification.md
    cd <OUT>/apb_vip_run_001        # or: export VLSIT_VIP_RUN=<that path>
    vip set author="<NAME>" project="<PROJECT>" reviewer="<NAME>" profile=PROF-01
    vip validate ; vip gate G1 APPROVED --by "<NAME>"
    vip plan ; vip lint plan ; vip config
    # write 03_arch/vip_arch.md, then: vip gate G2 APPROVED --by "<NAME>"
    vip gen ; vip worklist --n 5 ; vip check-vip ; vip lint impl

Result for profile PROF-01: 64 files, 9 checks generated complete from Section 8.1, 23 test classes, 14 coverage items. `vip check-vip` runs Verilator lint (simulation and formal) and a slang type-check of the quickstart and the qualification environment against UVM 2020.3.1. What remains are stubs for the monitor, the two drivers, five sequences, six covergroup samples, and the counterpart stimulus tasks; each carries `VIP_TODO` and warns or fails when run.

`python3 scripts/selftest.py` runs the same chain automatically. Use `vip gen-profile --profile PROF-02` after `vip config --profile PROF-02` for the APB3 build.
