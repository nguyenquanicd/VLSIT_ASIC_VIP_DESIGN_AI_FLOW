# vlsit-vip-vplan — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VIP verification plan / Kế hoạch kiểm chứng VIP**

Turn the approved specification into requirements.csv, the verification plan, and the requirement traceability, and lint the trace.

Biến spec đã duyệt thành requirements.csv, kế hoạch kiểm chứng và bảng truy vết requirement, rồi lint truy vết.

## Functions / Chức năng

- Derive check, coverage, injection, sequence, and test IDs for every requirement. / Sinh ID check, coverage, injection, sequence và test cho mọi requirement.
- Write requirements.csv, vplan.md, and the Section 13 traceability table. / Ghi requirements.csv, vplan.md và bảng truy vết Mục 13.
- Find plan gaps such as a MUST check without an injection. / Tìm lỗ hổng kế hoạch, ví dụ check MUST chưa có injection.
- One command, `vip plan`, validates, derives, and lints; output is grouped and short. / Một lệnh `vip plan` kiểm hợp lệ, sinh ID và lint; đầu ra được gom nhóm và ngắn.

## Inputs and outputs / Đầu vào và đầu ra

Input: the approved specification and the reviewer name. Output: `requirements.csv`, `vplan.md`, `traceability.csv`, traced specification copy.

Đầu vào: spec đã duyệt và tên người review. Đầu ra: `requirements.csv`, `vplan.md`, `traceability.csv`, bản spec đã điền bảng truy vết.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-vplan Plan the verification of <SPEC_FILE>. Reviewer: <NAME>. Output: <RUN>/02_plan.

Codex CLI:

    $vlsit-vip-vplan Plan the verification of <SPEC_FILE>. Reviewer: <NAME>. Output: <RUN>/02_plan.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/plan_guide.md
- references/VLSIT_ASIC_VIP_Specification_Template.md
- references/VLSIT_VIP_Design_Rule.md
- scripts/extract_requirements.py
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
