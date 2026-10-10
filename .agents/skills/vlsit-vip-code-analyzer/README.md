# vlsit-vip-code-analyzer — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VIP code analysis / Phân tích code VIP thành spec**

Analyze existing VIP code (SystemVerilog and UVM) and write its as-built specification in the mandatory template. Every row derived from code is marked UNVERIFIED with a CODE pointer until a person checks it against the standard.

Phân tích code VIP có sẵn (SystemVerilog và UVM) và viết spec as-built theo template bắt buộc. Mọi dòng suy ra từ code đều có dấu UNVERIFIED và con trỏ CODE cho đến khi người dùng đối chiếu với standard.

## Functions / Chức năng

- Inventory the code lexically (no simulator): interface signals, parameters, assertions, covergroups, classes by role, configuration, messages, TODOs. / Kiểm kê code bằng quét từ vựng (không cần simulator): tín hiệu interface, tham số, assertion, covergroup, class theo vai trò, cấu hình, message, TODO.
- Draft the specification: signals, requirements from labeled assertions with Section 8.1 expressions, capabilities, knobs, monitors, open decisions. / Soạn spec: tín hiệu, requirement từ assertion có nhãn kèm biểu thức Mục 8.1, capability, knob, monitor, quyết định còn mở.
- Mark every inferred cell UNVERIFIED with `CODE:<file>:<line>:<label>`; Gate 1 refuses the specification while a mark remains. / Đánh dấu mọi ô suy ra là UNVERIFIED kèm `CODE:<file>:<line>:<label>`; Gate 1 từ chối spec còn dấu này.
- List findings where the code is stricter, weaker, or silent against the standard; never change the code. / Liệt kê phát hiện khi code chặt hơn, lỏng hơn hoặc bỏ sót so với standard; không sửa code.
- Detect drift between specification and code (`vip verify-code`) and adopt the code as the base of bugfix and feature runs (`vip adopt`). / Phát hiện lệch giữa spec và code (`vip verify-code`) và nhận code làm nền cho run bugfix và feature (`vip adopt`).

## Inputs and outputs / Đầu vào và đầu ra

Input: the code directory, the VIP tag, the standard and revision. Output: `00_code/inventory.json`, `<tag>_vip_spec.md` (as-built), `draft_report.md`, the adopted tree `04_vip/<tag>_vip`.

Đầu vào: thư mục code, tag VIP, standard và revision. Đầu ra: `00_code/inventory.json`, `<tag>_vip_spec.md` (as-built), `draft_report.md`, cây code đã nhận `04_vip/<tag>_vip`.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-code-analyzer Analyze the VIP code in <CODE_DIR> and write its specification. Tag: <TAG>. Standard: <STANDARD, REVISION>. Output root: <OUTPUT_ROOT>.

Codex CLI:

    $vlsit-vip-code-analyzer Analyze the VIP code in <CODE_DIR> and write its specification. Tag: <TAG>. Standard: <STANDARD, REVISION>. Output root: <OUTPUT_ROOT>.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/reverse_guide.md
- references/VLSIT_ASIC_VIP_Specification_Template.md
- references/VLSIT_VIP_Design_Rule.md
- scripts/vip_inventory.py, spec_from_code.py
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
