# vlsit-vip-generator — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VIP generation and implementation / Sinh và hiện thực VIP**

Generate the VIP source tree from the approved architecture and implement every stub under the VLSIT VIP design rules.

Sinh cây mã nguồn VIP từ kiến trúc đã duyệt và hiện thực mọi stub theo rule thiết kế VIP của VLSIT.

## Functions / Chức năng

- Generate the interface, UVM-free checker, package, agent, item, coverage, quickstart, qualification scaffolding, and filelists. / Sinh interface, checker không phụ thuộc UVM, package, agent, item, coverage, quickstart, khung qualification và filelist.
- Mark every stub with VIP_TODO and make it announce itself at run time. / Đánh dấu mọi stub bằng VIP_TODO và buộc stub tự báo khi chạy.
- Implement checks, monitor, drivers, sequences, and coverage sampling; lint after each step. / Hiện thực check, monitor, driver, sequence và lấy mẫu coverage; lint sau mỗi bước.
- Bundle the shared VLSIT VIP base library and the expected-error catcher. / Kèm thư viện base VIP dùng chung và expected-error catcher.
- Checks with a specification expression come out as complete assertions; `vip worklist` lists only what is left. / Check có biểu thức trong spec được sinh thành assertion hoàn chỉnh; `vip worklist` chỉ liệt kê phần còn lại.
- `vip check-vip` lints with Verilator and type-checks the UVM tree against the official UVM with slang in one command. / `vip check-vip` lint bằng Verilator và kiểm kiểu cây UVM với UVM chính thức bằng slang trong một lệnh.

## Inputs and outputs / Đầu vào và đầu ra

Input: `vip_config.json`, `requirements.csv`, output directory, project, author, tools. Output: the `<tag>_vip/` tree and `generation_report.md`.

Đầu vào: `vip_config.json`, `requirements.csv`, thư mục đầu ra, tên project, tác giả, công cụ. Đầu ra: cây `<tag>_vip/` và `generation_report.md`.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-generator Generate and implement the VIP from <RUN>/03_arch/vip_config.json. Output: <RUN>/04_vip. Project: <PROJECT>. Author: <NAME>.

Codex CLI:

    $vlsit-vip-generator Generate and implement the VIP from <RUN>/03_arch/vip_config.json. Output: <RUN>/04_vip. Project: <PROJECT>. Author: <NAME>.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/implementation_guide.md
- references/VLSIT_VIP_Design_Rule.md
- assets/base/ (VLSIT VIP base package)
- scripts/gen_vip_skeleton.py, vip_worklist.py, impl_check.py, vip_compile.py
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
