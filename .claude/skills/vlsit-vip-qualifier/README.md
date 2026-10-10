# vlsit-vip-qualifier — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VIP qualification / Qualification VIP**

Qualify the VIP as a design under test: independent counterpart, positive, negative, and capability traces, runs on every variant and seed, evidence only from logs.

Qualify VIP như một thiết kế cần kiểm chứng: counterpart độc lập, trace đúng, trace sai và trace năng lực, chạy mọi variant và seed, bằng chứng chỉ lấy từ log.

## Functions / Chức năng

- Create the evidence matrix with every trace NOT_RUN. / Tạo ma trận bằng chứng với mọi trace ở NOT_RUN.
- Run the project simulator through build and run command templates; one log per run. / Chạy simulator của dự án qua command template build và run; mỗi lần chạy một log.
- Set PASS or FAIL only from the result line, the UVM summary, and the exit code. / Chỉ đặt PASS hoặc FAIL từ dòng kết quả, tóm tắt UVM và exit code.
- Classify failures, close coverage, and obtain Gate 3 approval. / Phân loại lỗi, đóng coverage và xin duyệt Gate 3.
- Qualification tests are generated; only one counterpart stimulus task per trace is written. / Test qualification được sinh sẵn; chỉ phải viết một task stimulus của counterpart cho mỗi trace.

## Inputs and outputs / Đầu vào và đầu ra

Input: the VIP tree, the plan, simulator commands, seed count. Output: `qual_evidence.json`, logs, `qualification_report.md`.

Đầu vào: cây VIP, kế hoạch, lệnh simulator, số seed. Đầu ra: `qual_evidence.json`, log, `qualification_report.md`.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-qualifier Qualify <RUN>/04_vip/<tag>_vip. Build: "<BUILD_CMD>". Run: "<RUN_CMD>". Seeds: <N>.

Codex CLI:

    $vlsit-vip-qualifier Qualify <RUN>/04_vip/<tag>_vip. Build: "<BUILD_CMD>". Run: "<RUN_CMD>". Seeds: <N>.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/qualification_guide.md
- references/VLSIT_VIP_Design_Rule.md
- scripts/create_qual_matrix.py, run_qual.py, collect_qual_results.py
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
