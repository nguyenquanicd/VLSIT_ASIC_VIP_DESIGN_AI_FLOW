# vlsit-vip-release — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VIP release and maintenance / Phát hành và bảo trì VIP**

Package the qualified VIP: complete the README, run the first-time-user trial, write the trace report, release notes, and manifest, and handle specification changes by diff.

Đóng gói VIP đã qualify: hoàn thiện README, chạy thử với người dùng lần đầu, viết trace report, release notes, manifest và xử lý thay đổi spec bằng diff.

## Functions / Chức năng

- Complete the README against the usability contract. / Hoàn thiện README theo hợp đồng dễ dùng.
- Run the usability trial and record every stumbling point. / Chạy thử khả năng dùng và ghi mọi chỗ vướng.
- Write the manifest with SHA-256 of every file and the release notes. / Ghi manifest với SHA-256 từng file và release notes.
- Compare two specification revisions and list the re-qualification scope. / So sánh hai revision của spec và liệt kê phạm vi qualify lại.
- `vip manifest` and `vip lint release` finish the release in two commands. / `vip manifest` và `vip lint release` hoàn tất phát hành trong hai lệnh.

## Inputs and outputs / Đầu vào và đầu ra

Input: the qualified VIP and evidence, version, trial person. Output: README, `trace_report.md`, `release_notes.md`, `vip_manifest.json`, `spec_diff.md`.

Đầu vào: VIP và bằng chứng đã qualify, version, người chạy thử. Đầu ra: README, `trace_report.md`, `release_notes.md`, `vip_manifest.json`, `spec_diff.md`.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-release Release <RUN>/04_vip/<tag>_vip as version <X.Y.Z>. Trial person: <NAME>.

Codex CLI:

    $vlsit-vip-release Release <RUN>/04_vip/<tag>_vip as version <X.Y.Z>. Trial person: <NAME>.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/release_checklist.md
- references/VLSIT_VIP_Design_Rule.md
- scripts/make_manifest.py, spec_diff.py
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
