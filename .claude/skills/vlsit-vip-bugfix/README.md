# vlsit-vip-bugfix — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VIP bug fix / Sửa lỗi VIP**

Fix defects of a released or adopted VIP: a bug log with gated states, the regression test written before the fix, an impact analysis, and re-qualification of only the traces the fix can affect.

Sửa lỗi của VIP đã phát hành hoặc đã nhận: nhật ký lỗi có trạng thái bị chặn theo bằng chứng, test hồi quy viết trước khi sửa, phân tích tác động và chỉ qualify lại các trace mà bản sửa có thể ảnh hưởng.

## Functions / Chức năng

- Record each defect with symptom and severity; classify it (vip, trace, counterpart, environment, dut, spec) before touching code. / Ghi từng lỗi kèm triệu chứng và mức độ; phân loại (vip, trace, counterpart, environment, dut, spec) trước khi sửa code.
- Gate the bug states: `fixed` needs a named regression test, `verified` an existing log, `closed` the test in the tree. / Chặn trạng thái lỗi theo bằng chứng: `fixed` cần test hồi quy có tên, `verified` cần log tồn tại, `closed` cần test nằm trong cây.
- Carry Gates 1 and 2 from the base run when the approved files are identical (`vip carry-gates`). / Mang Gate 1 và 2 từ run gốc khi file đã duyệt giống hệt (`vip carry-gates`).
- `vip impact` names the checks, requirements, and traces a fix touches (selective or full scope); `vip carry` keeps the PASS evidence of the rest; `vip qual-run --impacted` re-runs only what is left. / `vip impact` nêu check, requirement và trace bị ảnh hưởng (phạm vi chọn lọc hoặc toàn bộ); `vip carry` giữ bằng chứng PASS của phần còn lại; `vip qual-run --impacted` chỉ chạy lại phần còn thiếu.
- Write the bug report for the release notes and release a patch version. / Viết báo cáo lỗi cho release notes và phát hành bản vá.

## Inputs and outputs / Đầu vào và đầu ra

Input: a base run (`--base-run`), the defect report. Output: `00_change/bug_log.csv`, `impact.json`, the fixed tree in `04_vip`, carried and re-run evidence, patch release.

Đầu vào: run gốc (`--base-run`), báo cáo lỗi. Đầu ra: `00_change/bug_log.csv`, `impact.json`, cây đã sửa trong `04_vip`, bằng chứng mang sang và chạy lại, bản vá.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-bugfix Fix this VIP defect in <BASE_RUN>: <SYMPTOM>. Output root: <OUTPUT_ROOT>. Write the regression test first.

Codex CLI:

    $vlsit-vip-bugfix Fix this VIP defect in <BASE_RUN>: <SYMPTOM>. Output root: <OUTPUT_ROOT>. Write the regression test first.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/bugfix_guide.md
- references/VLSIT_ASIC_VIP_Specification_Template.md
- references/VLSIT_VIP_Design_Rule.md
- scripts/vip_bug.py
- scripts/vip.py (run-aware command), vip_state.py, vip_impact.py, vip_change.py, spec_scaffold.py, check_env.py, spec_query.py, rule_lookup.py, stage_brief.py, validate_vip_spec.py, trace_lint.py, vip_common.py

Shared files are copied from the repository source tree by `scripts/sync_skills.py`; their SHA-256 are in `references/BUNDLED_SHA256.txt`. Copy the whole skill folder when installing. / File dùng chung được `scripts/sync_skills.py` chép từ cây nguồn của repository; SHA-256 nằm trong `references/BUNDLED_SHA256.txt`. Khi cài, chép toàn bộ thư mục skill.

Instructions: [SKILL.md](SKILL.md). Flow overview and artifact contract: the repository [README](../../../README.md). / Hướng dẫn: [SKILL.md](SKILL.md). Tổng quan flow và hợp đồng artifact: [README](../../../README.md) của repository.

## Installation options / Các cách cài đặt

1. Open the repository in Claude Code or Codex CLI to use its project skills. / Mở repository trong Claude Code hoặc Codex CLI để dùng skill của project.
2. Copy this folder to `.claude/skills/<name>` (Claude Code) or `.agents/skills/<name>` (Codex CLI) in the target project. / Chép thư mục này vào `.claude/skills/<name>` (Claude Code) hoặc `.agents/skills/<name>` (Codex CLI) của project đích.
3. Copy it to `$HOME/.claude/skills/<name>` or `$HOME/.agents/skills/<name>` for personal use. Restart Codex if a new skill does not appear. / Chép vào `$HOME/.claude/skills/<name>` hoặc `$HOME/.agents/skills/<name>` để dùng cá nhân. Khởi động lại Codex nếu skill mới chưa xuất hiện.
4. Install all ten VIP skills together; the flow skill routes to the others. / Cài đủ mười skill VIP; skill flow chuyển việc cho các skill còn lại.

## Language convention / Quy định ngôn ngữ

Skill instructions, technical references, code comments, plans, reports, and script outputs use precise scientific and engineering English. Only README files and explicitly designated user guidelines are bilingual English–Vietnamese.

Nội dung skill, tài liệu tham khảo kỹ thuật, comment code, kế hoạch, báo cáo và đầu ra script dùng tiếng Anh khoa học và kỹ thuật chuẩn. Chỉ README và tài liệu được xác định rõ là guideline cho người dùng sử dụng song ngữ Anh–Việt.
