# VIP specification template and rules / Template spec VIP và rule

**VI:** Thư mục này chứa mẫu spec đầu vào bắt buộc của flow VIP và bộ rule thiết kế VIP. Sao chép template cho từng VIP rồi điền theo standard; mọi bảng được script đọc nên giữ nguyên tên cột và thứ tự.

**EN:** This folder holds the mandatory input template of the VIP flow and the VIP design rules. Copy the template per VIP and fill it from the standard; scripts parse the tables, so keep column names and order.

## Files

- [VLSIT_ASIC_VIP_Specification_Template.md](VLSIT_ASIC_VIP_Specification_Template.md) — the input format: front matter, 16 sections, machine-readable tables. / Định dạng đầu vào.
- [VLSIT_VIP_Design_Rule.md](VLSIT_VIP_Design_Rule.md) — rules for VIP code, naming, checkers, qualification, and release; rule IDs start with `V` so they never collide with the RTL rule IDs. / Rule cho code, đặt tên, checker, qualification và phát hành VIP.

## Relationship to the RTL rules / Quan hệ với rule RTL

**EN:** `VLSIT_RTL_Design_Rule.md` (v2) covers synthesizable RTL only (SCP-01). The VIP design rule states in Section 1, in one table, which RTL rules it inherits (file header, spaces only, comment length, abbreviations, parameter comments), which it replaces (the 30-character name limit), and which it does not apply (synthesis rules). It permits package, interface, SVA, and class constructs that the RTL rules reserve for verification source sets. No VIP rule weakens an RTL rule.

**VI:** Rule RTL v2 chỉ áp dụng cho RTL tổng hợp được. Mục 1 của rule VIP nêu trong một bảng: rule RTL nào được kế thừa, rule nào được thay thế và rule nào không áp dụng. Không có rule VIP nào làm yếu rule RTL.

## Fill and validate / Điền và kiểm

    python3 shared/scripts/validate_vip_spec.py <your_spec.md>

Placeholders in angle brackets, `TBD` in a requirement, unknown IDs, a modal verb that does not match the strength, and inconsistent boundaries are errors. A section that does not apply is replaced by a paragraph that starts with `N/A:` and gives the reason.
