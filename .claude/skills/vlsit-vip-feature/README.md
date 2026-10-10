# vlsit-vip-feature — Claude Code and Codex CLI / Dùng cho Claude Code và Codex CLI

**VIP feature update / Cập nhật tính năng VIP**

Add features to an existing VIP from a user requirement: change request, specification delta approved at Gate 1, port of the implemented VIP by a three-way merge, implementation of only the new stubs, and selective re-qualification.

Thêm tính năng cho VIP hiện có theo yêu cầu của người dùng: change request, delta spec được duyệt ở Gate 1, port VIP đã cài đặt bằng merge ba chiều, chỉ cài đặt các stub mới và qualify lại có chọn lọc.

## Functions / Chức năng

- Turn the user requirement into specification rows with new permanent IDs, expressions, injections, capabilities, and knobs whose defaults keep the old behavior. / Biến yêu cầu của người dùng thành các dòng spec với ID mới cố định, biểu thức, injection, capability và knob có mặc định giữ hành vi cũ.
- `vip delta` lists rows added, removed, and changed per table and suggests the version bump; Gate 1 approves the delta. / `vip delta` liệt kê dòng thêm, bỏ, đổi theo từng bảng và gợi ý mức tăng version; Gate 1 duyệt delta.
- `vip port` regenerates the old and the new skeleton and merges them with your code (`git merge-file`); conflicts are marked and fail `lint impl` until resolved. / `vip port` sinh lại skeleton cũ và mới rồi merge với code của bạn (`git merge-file`); xung đột được đánh dấu và làm `lint impl` fail cho đến khi giải quyết.
- `vip worklist` then shows only the new stubs. / `vip worklist` khi đó chỉ hiện các stub mới.
- `vip impact`, `vip carry`, `vip qual-run --impacted`: new and touched traces run, the rest of the base evidence is carried. / `vip impact`, `vip carry`, `vip qual-run --impacted`: trace mới và trace bị đụng được chạy, phần còn lại của bằng chứng gốc được mang sang.

## Inputs and outputs / Đầu vào và đầu ra

Input: a base run (`--base-run`), the user requirement. Output: `00_change/change_request.md`, `spec_delta.md`, `port_report.md`, `impact.json`, the ported tree in `04_vip`, evidence, minor release.

Đầu vào: run gốc (`--base-run`), yêu cầu của người dùng. Đầu ra: `00_change/change_request.md`, `spec_delta.md`, `port_report.md`, `impact.json`, cây đã port trong `04_vip`, bằng chứng, bản minor.

## Use / Cách gọi

Replace the tokens in angle brackets with your values. / Thay các token trong dấu ngoặc nhọn bằng giá trị của bạn.

Claude Code:

    /vlsit-vip-feature Add this requirement to the VIP of <BASE_RUN>: <REQUIREMENT>. Output root: <OUTPUT_ROOT>. Stop at each gate for my approval.

Codex CLI:

    $vlsit-vip-feature Add this requirement to the VIP of <BASE_RUN>: <REQUIREMENT>. Output root: <OUTPUT_ROOT>. Stop at each gate for my approval.

`vip` in the skill text is `python3 scripts/vip.py` in the skill folder (run `python3 scripts/vip.py help`). Both tools may also select the skill from the request text; /skills lists loaded skills. / Cả hai công cụ có thể tự chọn skill theo nội dung yêu cầu. Dùng /skills để xem skill đã nạp.

## Bundled files / File đi kèm

- references/feature_guide.md
- references/VLSIT_ASIC_VIP_Specification_Template.md
- references/VLSIT_VIP_Design_Rule.md
- scripts/vip_port.py
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
