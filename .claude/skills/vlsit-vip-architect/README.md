# vlsit-vip-architect — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VIP architecture and API / Kiến trúc và API của VIP**

Fix the VIP architecture and the user-facing API before any code exists, derive vip_config.json, and obtain Gate 2 approval of plan and architecture.

Chốt kiến trúc và API người dùng của VIP trước khi có code, sinh vip_config.json và xin duyệt Gate 2 cho kế hoạch và kiến trúc.

## Functions / Chức năng

- Select the profile and record build-or-reuse, simulator, UVM, and formal decisions. / Chọn profile và ghi quyết định build/reuse, simulator, UVM và formal.
- Derive and check vip_config.json for the selected profile. / Sinh và kiểm vip_config.json cho profile đã chọn.
- Write vip_arch.md showing how every usability-contract item is met. / Viết vip_arch.md chỉ ra từng mục hợp đồng dễ dùng được đáp ứng ra sao.

## Inputs and outputs / Đầu vào và đầu ra

Input: approved specification and plan. Output: `vip_config.json`, `vip_arch.md`. No code is generated.

Đầu vào: spec và kế hoạch đã duyệt. Đầu ra: `vip_config.json`, `vip_arch.md`. Không sinh code.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-architect Design the architecture for profile <PROF-nn> from <RUN>/02_plan. Output: <RUN>/03_arch.

Codex CLI:

    $vlsit-vip-architect Design the architecture for profile <PROF-nn> from <RUN>/02_plan. Output: <RUN>/03_arch.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/architecture_guide.md
- references/vip_arch_template.md
- references/VLSIT_ASIC_VIP_Specification_Template.md
- references/VLSIT_VIP_Design_Rule.md
- scripts/derive_vip_config.py
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
