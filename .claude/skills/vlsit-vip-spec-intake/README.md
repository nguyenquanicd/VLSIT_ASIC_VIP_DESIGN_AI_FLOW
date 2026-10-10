# vlsit-vip-spec-intake — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VIP specification intake / Nhập spec VIP từ standard**

Convert a protocol or standard document into a validated VIP specification in the mandatory markdown template, with every normative sentence classified.

Chuyển tài liệu giao thức hoặc standard thành spec VIP theo template markdown bắt buộc, mọi câu quy phạm đều được phân loại.

## Functions / Chức năng

- Fix the standard revision, roles, profiles, options, and reuse decision. / Chốt revision của standard, vai trò, profile, option và quyết định tái dùng.
- List normative sentences and require each to be mapped, informative, out of scope, or duplicate. / Liệt kê câu quy phạm và bắt buộc phân loại: ánh xạ, thông tin, ngoài phạm vi hoặc trùng.
- Extract requirements with clause references, boundaries, injections, and decisions; paraphrase only. / Trích requirement kèm điều khoản, biên, injection và quyết định; chỉ diễn đạt lại, không chép nguyên văn.
- Validate the specification and obtain Gate 1 approval. / Kiểm hợp lệ spec và xin duyệt Gate 1.
- `vip scaffold` prefills every rule-driven table; `vip query` reads one table or row instead of the whole file. / `vip scaffold` điền sẵn mọi bảng theo rule; `vip query` đọc một bảng hoặc một dòng thay vì cả file.
- Check expressions (Section 8.1) put each property in the specification, reviewed at Gate 1. / Biểu thức check (Mục 8.1) đưa từng property vào spec để duyệt ở Gate 1.

## Inputs and outputs / Đầu vào và đầu ra

Input: the standard (PDF or text) with exact revision, scope answers. Output: `<tag>_vip_spec.md`, validation and extraction reports, normative map.

Đầu vào: standard (PDF hoặc text) với revision chính xác, câu trả lời về phạm vi. Đầu ra: `<tag>_vip_spec.md`, báo cáo kiểm hợp lệ và trích xuất, bảng ánh xạ câu quy phạm.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-spec-intake Create the VIP specification from <STANDARD_FILE>, revision <REVISION>. Roles: host and device. Profile: <PROFILE>. Output: <OUTPUT_DIR>.

Codex CLI:

    $vlsit-vip-spec-intake Create the VIP specification from <STANDARD_FILE>, revision <REVISION>. Roles: host and device. Profile: <PROFILE>. Output: <OUTPUT_DIR>.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/extraction_guide.md
- references/VLSIT_ASIC_VIP_Specification_Template.md
- references/VLSIT_VIP_Design_Rule.md
- assets/APB_VIP_Specification.md (worked example)
- scripts/spec_scaffold.py, scan_normative.py
- scripts/vip.py (run-aware command), vip_state.py, check_env.py, spec_query.py, rule_lookup.py, stage_brief.py, validate_vip_spec.py, trace_lint.py, vip_common.py

Shared files are copied from the repository source tree by `scripts/sync_skills.py`; their SHA-256 are in `references/BUNDLED_SHA256.txt`. Copy the whole skill folder when installing. / File dùng chung được `scripts/sync_skills.py` chép từ cây nguồn của repository; SHA-256 nằm trong `references/BUNDLED_SHA256.txt`. Khi cài, chép toàn bộ thư mục skill.

Instructions: [SKILL.md](SKILL.md). Flow overview and artifact contract: the repository [README](../../../README.md). / Hướng dẫn: [SKILL.md](SKILL.md). Tổng quan flow và hợp đồng artifact: [README](../../../README.md) của repository.

## Installation options / Các cách cài đặt

1. Open the repository in Claude Code or Codex CLI to use its project skills. / Mở repository trong Claude Code hoặc Codex CLI để dùng skill của project.
2. Copy this folder to `.claude/skills/<name>` (Claude Code) or `.agents/skills/<name>` (Codex CLI) in the target project. / Chép thư mục này vào `.claude/skills/<name>` (Claude Code) hoặc `.agents/skills/<name>` (Codex CLI) của project đích.
3. Copy it to `$HOME/.claude/skills/<name>` or `$HOME/.agents/skills/<name>` for personal use. Restart Codex if a new skill does not appear. / Chép vào `$HOME/.claude/skills/<name>` hoặc `$HOME/.agents/skills/<name>` để dùng cá nhân. Khởi động lại Codex nếu skill mới chưa xuất hiện.
4. Install all seven VIP skills together; the flow skill routes to the others. / Cài đủ bảy skill VIP; skill flow chuyển việc cho các skill còn lại.

## Language convention / Quy định ngôn ngữ

Skill instructions, technical references, code comments, plans, reports, and script outputs use precise scientific and engineering English. Only README files and explicitly designated user guidelines are bilingual English–Vietnamese.

Nội dung skill, tài liệu tham khảo kỹ thuật, comment code, kế hoạch, báo cáo và đầu ra script dùng tiếng Anh khoa học và kỹ thuật chuẩn. Chỉ README và tài liệu được xác định rõ là guideline cho người dùng sử dụng song ngữ Anh–Việt.
