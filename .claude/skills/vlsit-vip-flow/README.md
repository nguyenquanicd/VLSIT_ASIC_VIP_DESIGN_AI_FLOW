# vlsit-vip-flow — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VLSIT VIP Flow orchestrator / Điều phối quy trình VIP**

Run the whole VLSIT ASIC VIP Design AI Flow: create a numbered run directory, route each stage to its skill, enforce four sign-off gates, and report honest evidence.

Chạy toàn bộ quy trình VLSIT ASIC VIP Design AI Flow: tạo thư mục run đánh số, chuyển từng stage cho skill phụ trách, giữ bốn gate duyệt và báo cáo bằng chứng trung thực.

## Functions / Chức năng

- Create and track a run directory with stage and gate state. / Tạo và theo dõi thư mục run cùng trạng thái stage và gate.
- Require a VIP specification in the mandatory markdown template; route a raw standard to the intake skill. / Bắt buộc có spec VIP theo template markdown; chuyển standard thô cho skill intake.
- Check stage prerequisites and reopen a gate when an approved artifact changes. / Kiểm điều kiện vào từng stage và mở lại gate khi artifact đã duyệt bị đổi.
- Report evidence counts and what was not run. / Báo số lượng bằng chứng và những gì chưa chạy.
- `vip next` names the next action and command; `vip brief` prints a one-screen stage brief; `vip check` runs the exit check. / `vip next` nêu việc tiếp theo và lệnh; `vip brief` in brief một màn hình cho stage; `vip check` chạy kiểm tra thoát stage.

## Inputs and outputs / Đầu vào và đầu ra

Input: a VIP specification (or a standard), output root, project, author, tools. Output: the run directory with `vip_state.json` and one folder per stage.

Đầu vào: spec VIP (hoặc standard), thư mục đầu ra, tên project, tác giả, công cụ. Đầu ra: thư mục run với `vip_state.json` và một thư mục cho mỗi stage.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-flow Build a VIP from <SPEC_FILE>. Output root: <OUTPUT_ROOT>. Project: <PROJECT>. Author: <NAME>. Stop at each gate for my approval.

Codex CLI:

    $vlsit-vip-flow Build a VIP from <SPEC_FILE>. Output root: <OUTPUT_ROOT>. Project: <PROJECT>. Author: <NAME>. Stop at each gate for my approval.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/flow_overview.md
- references/artifact_contract.md
- references/stage_checklists.md
- references/VLSIT_ASIC_VIP_Specification_Template.md
- references/VLSIT_VIP_Design_Rule.md
- scripts/vip.py (run-aware command), vip_state.py, vip_impact.py, vip_change.py, check_env.py, spec_query.py, rule_lookup.py, stage_brief.py, validate_vip_spec.py, trace_lint.py, vip_common.py

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
