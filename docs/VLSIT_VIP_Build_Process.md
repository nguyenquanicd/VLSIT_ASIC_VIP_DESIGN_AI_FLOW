# VLSIT VIP-FLOW — Quy trình xây dựng Verification IP từ specification

Phiên bản 0.2 (draft) · 2026-10-10 · Phạm vi: VIP SystemVerilog/UVM cho giao thức hoặc chuẩn interface dùng trong ASIC.
Bản 0.2 thêm Phụ lục A: cách quy trình này được hiện thực thành skill, template, rule và script trong repository này. Cơ sở nghiên cứu chi tiết: [VIP_Research_Evidence.md](VIP_Research_Evidence.md).
Thuật ngữ kỹ thuật giữ tiếng Anh. Mục có nhãn **[Bằng chứng]** lấy từ nguồn ở Mục 11. Mục có nhãn **[Đề xuất]** là tổng hợp của tác giả, chưa có nguồn trực tiếp.

---

## 0. Tóm tắt một trang

**Mục tiêu:** từ spec của giao thức đến VIP dùng được, đúng spec, với bằng chứng truy vết cho từng yêu cầu, qua ít bước nhất.

**Ba ý chính rút ra từ nghiên cứu**

1. **Bắt đầu từ spec của giao thức, không bắt đầu từ ý tưởng của người viết VIP.** Nếu lấy spec của VIP làm điểm vào, những assertion bị bỏ sót sẽ không ai phát hiện. [Bằng chứng: Cerisier et al., DVCon]
2. **Viết checker một lần, dùng nhiều nơi.** Checker là SVA có ID, gắn với mục spec, phân biệt vai trò (master/slave), dùng được cho cả simulation và formal. [Bằng chứng: Venkataramanan & Kumari, DVCon; Arm DUI 0534B]
3. **VIP cũng là một DUT.** Mỗi checker phải có một trace đúng (không báo lỗi) và một trace sai (báo đúng một lỗi, đúng ID), kiểm bằng phía đối ứng độc lập. [Bằng chứng: Cerisier et al.; Venkataramanan & Kumari]

**Bảy bước, mỗi bước có artifact và gate**

| # | Bước | Artifact chính | Gate (Definition of Done) |
|---|---|---|---|
| S0 | Scope & Reuse | `vip_scope.yaml`, quyết định build/reuse | Spec + revision được khóa, vai trò và tính năng optional đã chọn |
| S1 | Trích yêu cầu | `requirements.csv`, `decision_log.md` | Mọi câu shall/must/should có một dòng; người khác review |
| S2 | vPlan & truy vết | `vplan` (cột check/cover/seq/test của bảng yêu cầu) | Mỗi yêu cầu MUST có đích: check, cover hoặc lý do "không kiểm được" |
| S3 | Kiến trúc & API | `vip_arch.md`, danh sách cfg | Hợp đồng dễ dùng (Mục 4) được điền đủ |
| S4 | Sinh skeleton & cài đặt | Thư mục VIP biên dịch sạch | Compile + lint sạch, quickstart loopback chạy |
| S5 | Qualification | Trace đúng/sai cho mọi checker, báo cáo coverage | Gate VIP-2 (Mục 7) |
| S6 | Đóng gói & dùng thử | README, example env, trace report | Người chưa biết VIP chạy được ví dụ chỉ bằng README |
| S7 | Sign-off & bảo trì | Release note, tag spec revision | Gate VIP-3, quy trình diff khi spec đổi |

```
 spec ──S0──▶ scope ──S1──▶ requirements.csv ──S2──▶ vPlan (truy vết)
                                   │                      │
                                   ▼                      ▼
                           S3 kiến trúc/API ──S4──▶ skeleton sinh tự động
                                                      │  (checker stub có ID, cover stub, neg-test stub)
                                                      ▼
                                   S5 qualification (VIP là DUT) ──▶ S6 đóng gói ──▶ S7 sign-off
                                          ▲                                              │
                                          └──────── spec đổi → diff yêu cầu ◀────────────┘
```

---

## 1. Nguyên tắc thiết kế và bằng chứng

| # | Nguyên tắc | Lý do / bằng chứng |
|---|---|---|
| N1 | Điểm vào là spec của giao thức; người phân tích spec nên khác người viết VIP | Nếu lấy spec của VIP làm điểm vào, assertion bị thiếu sẽ không ai phát hiện, và kết quả qualification vẫn trông tốt. Cerisier et al. nêu rõ giới hạn này: phân tích spec nên do người khác thực hiện. |
| N2 | Mỗi câu shall/must/should trong spec là một yêu cầu có ID ổn định | ChipVerify: coi mọi câu "shall" là yêu cầu kiểm chứng. Arm đặt ID cho từng assertion kèm cột tham chiếu mục spec. |
| N3 | Phân tích hai phía: điều kiện hợp lệ và điều kiện vi phạm | Cerisier et al.: phía hợp lệ loại bỏ false negative của checker, phía vi phạm loại bỏ false positive. Bài SENT lấy biên hợp lệ và biên vi phạm cho từng tham số. |
| N4 | Một property, hai vai trò: assert ở phía phát, assume ở phía nhận, cover cho hành vi mong muốn | Venkataramanan & Kumari: cùng một property là checker với master và là constraint với slave. Bảng của họ cho một checker IP AXI3 (số xấp xỉ) có 102 checker và 20 constraint cho master, 43 checker và 67 constraint cho slave. |
| N5 | Checker dùng chung cho sim và formal: bọc code UVM bằng macro, tránh construct formal không hỗ trợ | Venkataramanan & Kumari: action block dùng UVM report phải bị che với công cụ formal; chú ý `$past` trước chu kỳ đủ lịch sử. |
| N6 | UVM dùng tập con nhỏ | Sutherland & Fitzpatrick: UVM 1.2 có 357 class, 938 function, 99 task, 374 macro; tập con đề xuất gồm 11 class, 33 task/function, 7 macro. Nên tránh phase jumping và callback. |
| N7 | Agent là đơn vị đóng gói; luôn có monitor, driver và sequencer chỉ có khi active | ChipVerify, Sutherland, và OpenTitan `dv_base_agent` đều theo mẫu này. |
| N8 | Tự động hóa phần cơ học, giữ người cho phần phán đoán | Infineon: sinh vPlan, ánh xạ vPlan sang assertion/coverage/test, sinh skeleton testbench, chạy regression, đẩy kết quả về công cụ quản lý yêu cầu. Họ báo công sức mỗi cấu hình giảm từ 40 xuống 2 person-day (IP cấu hình được, không phải VIP). OpenTitan `uvmdvgen` sinh sẵn skeleton agent. |
| N9 | VIP cũng cần kiểm chứng, và kiểm chứng phải truy vết được | Cerisier et al. và Venkataramanan & Kumari: mỗi checker cần trace đúng và trace sai tự kiểm. Mutation testing chỉ chỉ ra checker thiếu, khó truy vết về yêu cầu. |
| N10 | VIP dễ dùng là VIP có mặc định đúng, ít việc cấu hình, tài liệu đủ | ChipVerify (cfg một object, README đủ mục), OpenTitan (cờ cfg thống nhất), VIP thương mại (coverage, test suite, error injection đi kèm). |

---

## 2. Quy trình chi tiết

### S0 — Scope & Reuse
**Mục đích:** chốt đúng cái cần xây, tránh làm lại cái đã có.

- Ghi tên spec, mã tài liệu, **revision**, và các erratum đã biết.
- Chọn vai trò cần mô hình hóa: master/host, slave/device, monitor thụ động. Nếu có cả master và slave, hai phía **không được dùng chung code của checker** (xem S5).
- Chọn tính năng optional và profile (ví dụ AXI4-Lite so với AXI4 đầy đủ). Mọi tính năng ngoài phạm vi ghi vào `out_of_scope`.
- Chọn mục tiêu công cụ: simulator nào, có tái dùng cho formal không, UVM version (IEEE 1800.2-2020 hay 1.2).
- **Build hay reuse:** kiểm tra VIP đã có (commercial hoặc open-source, ví dụ các agent trong `opentitan/hw/dv/sv`) và so với bảng yêu cầu ở S1 trước khi quyết định. [Đề xuất]

**Artifact:** `vip_scope.yaml`. **DoD:** revision spec khóa; vai trò, profile, mục tiêu công cụ đã ghi.

### S1 — Trích yêu cầu
**Mục đích:** biến spec thành danh sách yêu cầu có thể kiểm.

- Quét toàn bộ spec; mỗi câu shall/must/should/may tạo một dòng trong `requirements.csv` (schema ở Mục 5).
- Phần mơ hồ hoặc không nói rõ (ví dụ giá trị tối đa không được nêu) ghi vào `decision_log.md` cùng suy luận và người quyết định. Bài SENT cho thấy ví dụ: suy ra giá trị tối đa từ các phần khác của spec.
- Với mỗi tham số số học, ghi cả **biên hợp lệ** và **biên vi phạm** ngay trong cột ghi chú. Đây là đầu vào trực tiếp cho coverage (S5) và trace sai.
- Tách yêu cầu theo vai trò (M/S/cả hai) vì phía nào phát thì phía đó assert.
- **Người review khác người trích.** [Bằng chứng: Cerisier et al.]

**Artifact:** `requirements.csv`, `decision_log.md`. **DoD:** không còn câu shall/must/should nào của spec chưa có dòng; review xong; mục mơ hồ đã có quyết định hoặc cờ `OPEN`.

### S2 — vPlan và truy vết
**Mục đích:** mỗi yêu cầu có đích kiểm chứng rõ ràng trước khi viết code.

Với mỗi dòng yêu cầu điền: `chk_id` (assertion hoặc class check), `cov_id` (coverpoint hoặc cover property), `seq_id` (sequence phát sinh tình huống), `test_pos`, `test_neg`. Yêu cầu không kiểm được ghi `check_type = NONE` kèm lý do.

Cadence mô tả cách làm tương tự: verification plan chạy được, nối với coverage model và test suite. OpenTitan giữ testplan (Hjson) gồm danh sách test ánh xạ theo tính năng và kế hoạch functional coverage.

**Artifact:** các cột truy vết trong `requirements.csv` (hoặc file vPlan sinh từ đó). **DoD:** `trace_lint` báo không có yêu cầu MUST nào thiếu đích.

### S3 — Kiến trúc và API
**Mục đích:** cố định hình dạng VIP trước khi cài đặt, để người dùng không phải học lại cho mỗi giao thức.

- Dùng kiến trúc ở Mục 3 làm mặc định; chỉ lệch khi giao thức bắt buộc (ví dụ giao thức nhiều lớp cần nhiều agent).
- Điền **Hợp đồng dễ dùng** (Mục 4) trước, kể cả danh sách cờ cfg, TLM port, các class cho phép factory override.
- Chọn base class: dùng thư viện base có sẵn của dự án (ví dụ pattern `dv_base_agent`) hoặc tạo bộ base tối thiểu; không tự phát minh lại cho từng VIP.

**Artifact:** `vip_arch.md`. **DoD:** mọi mục Hợp đồng dễ dùng có giá trị hoặc lý do "không áp dụng".

### S4 — Sinh skeleton và cài đặt
**Mục đích:** để máy sinh phần lặp lại, để người điền phần giao thức.

**Tự động sinh từ `requirements.csv` và `vip_arch.md`:**
- skeleton thư mục, filelist/core file, package, agent/cfg/item/monitor/driver/sequencer/cov/seq_lib theo base class;
- checker stub trong interface hoặc module `bind`, mỗi stub mang `chk_id` và `req_id`, để body trống;
- covergroup stub từ cột biên hợp lệ/vi phạm;
- negative-test stub (`qual_<chk_id>_neg`) và positive-test stub (`qual_<chk_id>_pos`).

OpenTitan `uvmdvgen` cho thấy mức này khả thi: nó sinh interface rỗng, item, cfg, cov, monitor, driver, base sequence, package và core file; người dùng điền sáu chỗ (tín hiệu interface, field của item, `collect_trans()`, giá trị reset, `get_and_drive()`, sequence).

**Thứ tự cài đặt (nhanh nhất để có phản hồi sớm):**
1. Interface + clocking block + checker (đã chạy được với trace đơn giản).
2. Monitor (thấy được transaction ngay từ DUT thật hoặc từ loopback).
3. Driver phía host, rồi phía device (reactive).
4. Sequence cơ bản, rồi sequence cho tình huống biên và lỗi.
5. Coverage.
6. Adapter RAL nếu là bus thanh ghi.

**DoD:** compile và lint sạch trên simulator mục tiêu; quickstart loopback (host nối device của chính VIP) chạy qua.

### S5 — Qualification (VIP là DUT)
Chi tiết ở Mục 6. **DoD:** gate VIP-2.

### S6 — Đóng gói và dùng thử
**Mục đích:** chứng minh VIP dễ dùng bằng cách người khác dùng thật.

- README đủ các mục ở Mục 4.
- Example env tối thiểu, đã chạy trong CI hoặc regression của VIP.
- Một người chưa từng dùng VIP này chạy ví dụ từ README; mọi chỗ họ vấp phải là lỗi tài liệu hoặc API và phải được sửa. [Đề xuất]
- Trace report sinh tự động: yêu cầu → check → test → kết quả → coverage.

**DoD:** người dùng thử chạy được ví dụ không cần hỏi.

### S7 — Sign-off và bảo trì
- Gate VIP-3 (Mục 7).
- Gắn tag `spec_rev` và semantic version cho VIP.
- Khi spec đổi: diff `requirements.csv` giữa hai revision; chỉ phần thay đổi đi lại S1 đến S5. Đây là lý do ID yêu cầu phải ổn định và không tái sử dụng.

---

## 3. Kiến trúc chuẩn

```
<proto>_vip/
  spec/       requirements.csv  decision_log.md  vip_scope.yaml
  rtl_if/     <proto>_if.sv          # interface: tín hiệu, clocking block, modport
              <proto>_checker.sv     # checker IP: assert / assume / cover, có ID
  uvm/        <proto>_agent_pkg.sv   # cfg, item, monitor, driver (host/device),
              seq_lib/                # sequencer, cov, agent
  qual/       trace đúng/sai, expect-error catcher, qual env (sinh stub từ bảng yêu cầu)
  example/    quickstart tb (loopback), ví dụ tích hợp
  doc/        README.md  trace_report (sinh tự động)
  scripts/    gen_skeleton  trace_lint
```

**Ai chịu trách nhiệm kiểm cái gì**

| Loại kiểm | Đặt ở đâu | Lý do |
|---|---|---|
| Luật protocol theo chu kỳ (handshake, ổn định, thứ tự, reset, giá trị X) | SVA trong interface hoặc module/interface bind | Đúng thời gian, không cần class; dùng lại được cho formal |
| Luật protocol cần gom nhiều dữ liệu hoặc hiếm | Class check trong monitor | Dễ viết hơn SVA khi cần cấu trúc dữ liệu |
| Đúng dữ liệu end-to-end | Scoreboard của dự án, **không** nằm trong VIP | Phụ thuộc DUT cụ thể (ChipVerify) |
| Functional coverage của giao thức | Subscriber coverage, bật bằng `en_cov` | Dùng chung giữa các dự án |

**Nguồn ủng hộ:** ChipVerify (protocol check ở VIP, data check ở scoreboard); thảo luận trên diễn đàn Verification Academy (luật theo chu kỳ ở bound checker hoặc interface SVA, scoreboard dữ liệu ở class). Phần diễn đàn là ý kiến cộng đồng, không phải chuẩn.

**Container cho checker:** dùng `interface` để chứa checker nếu muốn gắn vào interface của VIP, vì interface có thể chứa interface nhưng không chứa module. Construct `checker` gọn nhưng một số tool chưa hỗ trợ tốt. [Bằng chứng: Venkataramanan & Kumari]

**Pattern agent (tham chiếu OpenTitan `dv_base_agent`)**
- `build_phase`: luôn tạo monitor; chỉ tạo sequencer và driver khi `is_active` (và `has_driver`); chọn driver host hoặc device theo `if_mode`; coverage tạo khi `en_cov`.
- `connect_phase`: nối `seq_item_port` với sequencer chỉ khi active.
- Một cfg object chứa mọi cờ và `vif`.

---

## 4. Hợp đồng "dễ dùng"

Các mục này là điều kiện để VIP qua S3 và S6. Mục có nguồn được ghi kèm; còn lại là [Đề xuất].

| # | Điều khoản | Chi tiết |
|---|---|---|
| U1 | Một package, một cfg, một agent | Dùng VIP = import package, tạo cfg, gán `vif`, tạo agent. Ba bước, không thêm bước phụ. [ChipVerify: gom mọi tham số vào một object] |
| U2 | Mặc định hợp lệ và chạy được | cfg mặc định tạo ra traffic hợp lệ với độ trễ ngẫu nhiên có ràng buộc; có công tắc đặt mọi trễ về 0 cho debug nhanh (`zero_delays` trong OpenTitan push_pull). |
| U3 | Bộ cờ chế độ chuẩn | `is_active`, `en_monitor`, `en_cov`, `if_mode` (host/device), `has_driver`, `ok_to_end_delay`, `in_reset`. [OpenTitan `dv_base_agent_cfg`] |
| U4 | Độ rộng và tính năng optional qua tham số | Tham số của interface cho độ rộng; cfg cho tính năng chọn lúc chạy. Arm dùng tham số cho đặc tính interface và một tham số cho kiểm tra hiệu năng (`MAXWAITS`). |
| U5 | Checker bật sẵn, tắt theo ID | Tắt từng checker phải qua ID và có lý do (waiver). Luật loại REC có thể tắt gộp (như `RecommendOn` của Arm). |
| U6 | Thông báo lỗi tự giải thích | Mỗi lỗi mang `chk_id`, `req_id`, tham chiếu mục spec, thời điểm. Báo cáo cuối test tóm tắt checker đã chạm. |
| U7 | Quickstart tự chạy | Có test loopback chạy đạt mà không cần code đặc thù DUT. Vendor lớn giao test suite kèm source (Synopsys, Siemens). |
| U8 | Reset giữa chừng | Xử lý reset không đồng bộ giữa transaction; cờ `in_reset` do monitor duy trì. [OpenTitan] |
| U9 | Interface sạch | Interface đẩy X lên các kênh không hợp lệ để lộ lỗi lái nhầm. [OpenTitan X-prop]. Mọi lái tín hiệu có thời gian đi qua clocking block. |
| U10 | Tiêm lỗi qua item hoặc sequence | Lỗi được chọn bằng field của item hoặc sequence theo `req_id`; **không dùng callback**. Xem Mục 9. |
| U11 | Tài liệu tối thiểu | Field cfg và miền hợp lệ; mục `uvm_config_db` bắt buộc cùng đường dẫn; TLM port và kiểu transaction; class cho phép override; yêu cầu về virtual interface; giả định clock và reset. [ChipVerify] |
| U12 | Debug | Transaction có `convert2string`, ghi/record transaction để xem trên waveform, verbosity có cấp. Công cụ protocol analyzer là tính năng của vendor, ngoài phạm vi. |
| U13 | Phiên bản | Gắn `spec_rev` và semver; release note liệt kê yêu cầu đã thêm/đổi. |

---

## 5. Bảng yêu cầu và quy tắc đặt ID

**Schema `requirements.csv`**

| Cột | Ý nghĩa |
|---|---|
| `req_id` | `<PROTO>-<NNNN>`, ổn định, không tái sử dụng kể cả khi xóa |
| `spec_ref` | Mã tài liệu + revision + mục/bảng/hình |
| `strength` | MUST / SHOULD / MAY (từ shall/should/may) |
| `role` | M (master/host) / S (slave/device) / B (cả hai) |
| `kind` | SIG (tín hiệu: ổn định, X, thời gian), SEQ (thứ tự/handshake), TXN (ngữ nghĩa transaction), CFG (tham số/tính năng optional), CAP (khả năng phát stimulus mà VIP phải có) |
| `check_type` | SVA / CLASS / COV / NONE (kèm lý do) |
| `chk_id` | `<PROTO>_<ERR\|REC><M\|S>_<TÍN HIỆU>_<LUẬT>` |
| `cov_id`, `seq_id`, `test_pos`, `test_neg` | Đích truy vết |
| `bound_valid`, `bound_invalid` | Biên hợp lệ và biên vi phạm cho tham số số học |
| `status` | draft / reviewed / implemented / qualified / waived |
| `reviewer` | Người review (khác người cài đặt) |
| `note` | Liên kết `decision_log.md` nếu mơ hồ |

**Quy tắc đặt `chk_id`** (theo mẫu của Arm, kiểm tra trên DUI 0534B: tiền tố ERRM, ERRS, RECM, RECS; bảng có cột tham chiếu mục spec): ERR là vi phạm yêu cầu bắt buộc, REC là khuyến nghị; M/S là phía chịu trách nhiệm. Ví dụ AXI: `AXI4_ERRM_AWID_STABLE`.

**Ví dụ minh họa cho APB.** Số mục spec chưa được đối chiếu với IHI0024; cột `spec_ref` giữ chỗ.

| req_id | spec_ref | strength | role | kind | chk_id | Nội dung |
|---|---|---|---|---|---|---|
| APB-0001 | IHI0024 §? | MUST | M | SEQ | `APB_ERRM_PENABLE_SETUP` | PENABLE phải thấp ở chu kỳ SETUP; PSEL lên trước PENABLE một chu kỳ |
| APB-0002 | IHI0024 §? | MUST | M | SIG | `APB_ERRM_PADDR_STABLE` | PADDR, PWRITE, PWDATA giữ ổn định từ SETUP sang ACCESS và trong wait state |
| APB-0003 | IHI0024 §? | SHOULD | S | SIG | `APB_RECS_PSLVERR_LOW` | PSLVERR chỉ có nghĩa ở chu kỳ cuối của transfer; nên giữ thấp ở chu kỳ khác |

---

## 6. Qualification — kiểm chứng chính VIP (S5)

**Nguyên tắc [Bằng chứng: Cerisier et al.]:** coi VIP là DUT. Điều kiện hợp lệ phải không gây lỗi; điều kiện vi phạm phải gây đúng lỗi mong đợi.

**Ma trận test bắt buộc**

| Loại yêu cầu | Trace đúng (pos) | Trace sai (neg) |
|---|---|---|
| MUST, kind SIG/SEQ, check SVA | Đúng tại biên hợp lệ: không có `uvm_error` | Vượt biên vi phạm một đơn vị: đúng **một** lỗi mang `chk_id` |
| SHOULD (REC) | Không cảnh báo | Đúng một cảnh báo mang `chk_id` |
| CAP (khả năng phát stimulus) | Driver phát được; monitor thu lại khớp | Không áp dụng |
| CFG (tham số) | Chạy với từng giá trị đại diện và biên của tham số | Giá trị ngoài miền bị từ chối |

Ví dụ biên từ bài SENT: một xung dữ liệu hợp lệ dài 12 đến 27 tick; phải tạo trace với 12 và 27 (không lỗi) và với 11 và 28 (lỗi). Tương tự cho thời gian mức thấp.

**Môi trường qualification**
- VIP được nối với **phía đối ứng độc lập**: một mô hình hành vi nhỏ của giao thức, có thể phát khung hợp lệ và khung lỗi với điều khiển từng mốc thời gian (như bộ mô hình SENT). Không nối master và slave của cùng VIP với nhau trừ khi hai phía do hai người viết, không dùng chung code, đặc biệt phần checker. [Bằng chứng: Cerisier et al.]
- Mỗi test neg khai báo trước lỗi nào được kỳ vọng, số lần tối thiểu và tối đa, cửa sổ thời gian, và hành động khi bắt được (hạ xuống `UVM_WARNING` để test đạt). Cerisier et al. làm bằng class mở rộng `uvm_report_catcher`; Venkataramanan & Kumari dùng `uvm_report_mock` của SVUnit. Cần thư viện loại này vì UVM không có khái niệm lỗi "được mong đợi". Hạn chế: chỉ bắt được thông báo UVM, nên checker của VIP phải báo qua `uvm_error`.
- Trace cho từng assertion chạy ở mức đơn vị, không cần dựng env UVM đầy đủ (Venkataramanan & Kumari dùng khung Go2UVM).

**Coverage của VIP**
- Mỗi yêu cầu có cover tương ứng: coverpoint cho giá trị/biên (hợp lệ và vi phạm), cover property cho chuỗi/handshake, cross cho tổ hợp đáng kể.
- Mọi loại trừ có nhãn lý do. OpenTitan yêu cầu mỗi exclusion có thẻ phân loại (UNR, NON_RTL, UNSUPPORTED, EXTERNAL, LOW_RISK) và lý do; làm tương tự.

**Điều đã thấy khi qualify một VIP thật [Bằng chứng: Cerisier et al.]:** một số assertion bị thiếu và chỉ lộ ra nhờ phân tích spec độc lập; một số assertion không được gọi trong mọi trường hợp lỗi mà nó phải kiểm. Khoảng một nửa số test của regression kiểm tra điều kiện vi phạm, nên bộ bắt lỗi mong đợi giúp tiết kiệm nhiều công đọc log.

---

## 7. Gate

Khung gate mượn từ OpenTitan (V1/V2/V3). Ngưỡng cụ thể bên dưới là [Đề xuất]; OpenTitan dùng khoảng 80% coverage cho V2, và "verification complete" yêu cầu 100% test pass, mỗi test constrained-random chạy 100 seed.

| Gate | Điều kiện |
|---|---|
| **VIP-0 Spec-locked** | `vip_scope.yaml` xong; `requirements.csv` review bởi người độc lập; `decision_log` không còn mục `OPEN` chặn việc |
| **VIP-1 Functional** | Compile và lint sạch trên simulator mục tiêu; quickstart loopback đạt; 100% yêu cầu MUST kind SIG/SEQ có checker cài đặt; `trace_lint` sạch |
| **VIP-2 Qualified** | Mọi checker MUST có trace đúng và trace sai đạt; test với phía đối ứng độc lập đạt; coverage mô hình của VIP đóng 100% trừ mục waived có lý do; không có `uvm_error` ngoài mong đợi |
| **VIP-3 Release** | Regression nhiều seed đạt 100% (số seed do dự án chọn, tham khảo 100); README đủ và người dùng thử chạy được; review cuối bởi người không cài đặt; tag `spec_rev` và semver; release note |

---

## 8. Tự động hóa và vai trò của AI

| Việc | Máy làm (xác định) | AI làm (nháp) | Người làm (duyệt) |
|---|---|---|---|
| Quét spec tìm shall/must/should | | Trích câu, đề xuất `strength`, `role`, `kind` | Duyệt từng dòng, quyết định mơ hồ |
| Cấp ID, kiểm trùng, diff giữa revision | ✔ | | |
| Skeleton VIP, stub checker/cover/test | ✔ (từ bảng yêu cầu) | | |
| Viết thân SVA và covergroup | | Nháp từ yêu cầu và biên | Duyệt; **chỉ đạt khi qua qualification** |
| Trace đúng/sai | Sinh stub | Nháp thân trace | Duyệt |
| `trace_lint` (mỗi MUST có đích, mỗi checker có pos+neg) | ✔ | | |
| Báo cáo truy vết | ✔ | | |

**Quy tắc cho nội dung do AI sinh [Đề xuất, dựa trên bằng chứng bên dưới]:** mọi checker do AI viết có trạng thái `draft` cho đến khi qua trace đúng và trace sai; không tin AI cho việc quyết định mơ hồ của spec.

**Bằng chứng về AI sinh assertion:** AssertLLM (đa LLM, sinh SVA từ spec, kể cả từ waveform) báo 89% assertion vừa đúng cú pháp vừa đúng chức năng trên một thiết kế đầy đủ gồm 23 tín hiệu I/O (số liệu của phiên bản v3 trên arXiv 2402.00386; các phiên bản khác nhau về tác giả và cách trình bày, nên trích dẫn bản ASP-DAC '25 khi cần); kết quả chỉ trên một thiết kế. Bài DVCon Europe 2024 dùng RAG để giảm ảo giác và kiểm assertion bằng bounded model checking với RTL chuẩn trên AXI4-Lite. Hai nguồn này không cho thấy bước kiểm tra tính vô nghĩa (vacuity), nên cần giữ cổng qualification của VIP-FLOW. Tôi mới đọc phần tóm tắt, chưa đọc toàn văn.

---

## 9. Xung đột giữa các nguồn và quyết định

| Vấn đề | Quan điểm khác nhau | Quyết định của VIP-FLOW |
|---|---|---|
| Truyền cfg xuống driver/monitor | Một nhóm giữ cfg ở agent rồi chép biến xuống thành phần con; nhóm khác truyền handle cfg xuống thẳng. | Truyền handle cfg (như OpenTitan: `driver.cfg = cfg`), để một nguồn sự thật. Không tạo class cfg riêng cho từng thành phần con. |
| Callback | Sutherland & Fitzpatrick khuyên tránh. ChipVerify khuyên định nghĩa callback cho `pre_drive`, `post_drive`, `pre_reset`, `post_reset`. | Tránh callback. Dùng cờ cfg, field của item, factory override và sequence. Điều chỉnh reset qua cfg. Có thể xem lại nếu một giao thức thật sự cần. |
| Clocking block và modport | Forum Accellera cho thấy các VIP mẫu khác nhau, một số dùng, một số không; modport từng bị simulator kiểm không đủ. | Dùng clocking block cho mọi lái tín hiệu có thời gian (OpenTitan `push_pull_if` có clocking block theo vai trò). Dùng modport để làm tài liệu, không dựa vào chúng để bắt lỗi. |
| SVA trong interface hay bind | Interface thuận tiện cho UVM; bind truy cập tín hiệu nội bộ DUT. | Luật protocol đặt trong interface hoặc checker bind được cho cả hai; phần checker cho tín hiệu nội bộ DUT không thuộc VIP. |
| Kiểm chứng VIP: mutation hay qualification | Mutation testing tự động nhưng khó truy vết và khó đánh giá chất lượng assertion. | Qualification theo yêu cầu (Mục 6) là chính. Mutation có thể bổ sung sau. |

---

## 10. Giới hạn của nghiên cứu và việc tiếp theo

**Không đọc được hoặc chưa đọc**
- Verification Academy: UVM Cookbook, các session VIP và EZ-VIP nằm sau đăng nhập; chỉ đọc được phần tóm tắt. Các nội dung về VIP trong Cookbook chưa được kiểm.
- Toàn văn IEEE 1800.2-2020 và UVM User Guide của Accellera chưa đọc; chỉ xác nhận chuẩn có sẵn miễn phí qua IEEE GET.
- Spec APB (IHI0024) chưa đọc kỹ; ví dụ APB trong Mục 5 chỉ để minh họa. Tài liệu assertion AXI của Arm (DUI 0534B, 2012) đã đọc phần cấu trúc, ID và tham số.
- Tài liệu vendor (Synopsys, Siemens, Cadence, Avery) là tài liệu tiếp thị; chỉ dùng để xác nhận tính năng gì được coi là "chuẩn" của VIP thương mại, không dùng làm số liệu.
- Các bài trên forum về clocking block và SVA có từ 2012 đến 2013; cần kiểm lại với simulator thực tế. Phát biểu "assertion đồng thời không được đặt trong class" cũng từ thời đó, cần kiểm với LRM hiện hành.

**Việc tiếp theo đề xuất**
1. **Thí điểm trên APB** với DUT sẵn có trong repo (`APB-CSR-Generator`, `APB-DEC-Generator`): chạy S0 đến S5 để hiệu chỉnh quy trình.
2. Viết `gen_skeleton` và `trace_lint` (hai script nhỏ, xác định) từ schema ở Mục 5.
3. Đóng gói quy trình thành skill (`vlsit-vip-builder`) khi thí điểm xong, để AI chạy cùng quy trình.
4. Khóa các lựa chọn còn mở: simulator mục tiêu, UVM version, thư viện base class dùng chung.

---

## 11. Nguồn

**Bài báo (đã đọc toàn văn sau khi chuyển PDF sang text)**
- Cerisier, Carmagnat, Basili, Curchod — [Qualification of a Verification IP under Requirement Based Verification standards](https://dvcon-proceedings.org/wp-content/uploads/qualification-of-a-verification-ip-under-requirement-based-verification-standards-an-approach-to-the-verification-of-the-verification.pdf), DVCon.
- Venkataramanan, Kumari — [Architecting "Checker IP" for AMBA protocols](https://dvcon-proceedings.org/wp-content/uploads/architecting-checker-ip-for-amba-protocols.pdf), DVCon.
- Sutherland, Fitzpatrick — [UVM Rapid Adoption: A Practical Subset of UVM](https://dvcon-proceedings.org/wp-content/uploads/uvm-rapid-adoption-a-practical-subset-of-uvm.pdf), DVCon (slide).
- Zhang, Radulovic, Dworzak (Infineon) — [Fully Automated Verification Framework for Configurable IPs](https://arxiv.org/pdf/2510.15902).

**Đã đọc phần liên quan**
- Arm — [AMBA 4 AXI4, AXI4-Lite and AXI4-Stream Protocol Assertions User Guide, DUI 0534B](https://documentation-service.arm.com/static/5f106bd90daa596235e808ed): đọc cấu trúc, ID, tham số; không đọc từng assertion.
- OpenTitan trong repo cục bộ (`opentitan/hw/dv/sv/dv_base_agent`, `push_pull_agent`): đọc mã nguồn trực tiếp.
- OpenTitan — [uvmdvgen](https://opentitan.org/book/util/uvmdvgen) và [DV methodology](https://opentitan.org/book/doc/contributing/dv/methodology/): đọc qua bản trích xuất của công cụ fetch, không đọc nguyên trang.
- ChipVerify — [Reusable verification components](https://chipverify.com/uvm/reusable-verification-components): đọc qua bản trích xuất của công cụ fetch.

**Chỉ đọc kết quả tìm kiếm hoặc tóm tắt**
- ChipVerify — [Verification plan](https://www.chipverify.com/verification/verification-plan) (câu "mọi shall là yêu cầu").
- AssertLLM / Spec2SVA — [arXiv 2402.00386](https://arxiv.org/pdf/2402.00386), [arXiv 2411.14436](https://arxiv.org/html/2411.14436v1); DVCon Europe 2024 — [Enhanced VLSI Assertion Generation … RAG](https://dvcon-proceedings.org/wp-content/uploads/195-Enhanced-VLSI-Assertion-Generation-Conforming-to-High-Level-Specifications-and-Reducing-LLM-Hallucinations-with-RAG.pdf).
- Verification Academy forum — [SVA trong interface hay bind](https://verificationacademy.com/forums/t/is-using-interfaces-for-svas-instead-of-a-simple-bind-file-a-good-idea/37287); Accellera forum — [clocking block và modport trong UVM interface](https://forums.accellera.org/topic/672-clocking-blocks-and-modports-in-uvm-interfaces/).
- Tính năng VIP thương mại — [Siemens Questa VIP](https://resources.sw.siemens.com/en-US/fact-sheet-questa-verification-ip), [Synopsys VC VIP test suites](https://origin-www.synopsys.com/verification/verification-ip/verification-test-suites.html), [Cadence (qua Electronic Design)](https://www.electronicdesign.com/products/reusable-verification-ip-fits-overall-automation-planning).
- IEEE 1800.2-2020 — [thông báo Accellera](https://www.eejournal.com/industry_news/uvm-reference-implementation-aligned-with-ieee-1800-2-2020-standard).

---

## Phụ lục A. Hiện thực trong repository này

Quy trình ở các mục trên đã được hiện thực thành bộ skill cho Claude Code và Codex CLI. Bảng dưới ánh xạ bước quy trình sang thành phần.

| Bước | Skill | Script chính | Gate |
|---|---|---|---|
| S0 Scope và reuse | `vlsit-vip-spec-intake` | — | — |
| S1 Trích yêu cầu | `vlsit-vip-spec-intake` | `scan_normative.py`, `validate_vip_spec.py` | Gate 1 (VIP-0) |
| S2 vPlan và truy vết | `vlsit-vip-vplan` | `extract_requirements.py`, `trace_lint.py` | — |
| S3 Kiến trúc và API | `vlsit-vip-architect` | `derive_vip_config.py` | Gate 2 |
| S4 Sinh và hiện thực | `vlsit-vip-generator` | `gen_vip_skeleton.py`, `trace_lint.py` | VIP-1 kiểm tự động |
| S5 Qualification | `vlsit-vip-qualifier` | `create_qual_matrix.py`, `run_qual.py`, `collect_qual_results.py` | Gate 3 (VIP-2) |
| S6 Đóng gói | `vlsit-vip-release` | `make_manifest.py` | — |
| S7 Sign-off và bảo trì | `vlsit-vip-release` | `spec_diff.py`, `trace_lint.py` | Gate 4 (VIP-3) |
| Điều phối | `vlsit-vip-flow` | `vip_state.py` | tất cả |

**Spec đầu vào bắt buộc** là file markdown theo `spec_template/VLSIT_ASIC_VIP_Specification_Template.md`, kiểm bằng `validate_vip_spec.py`. **Rule VIP** nằm ở `spec_template/VLSIT_VIP_Design_Rule.md`, ID bắt đầu bằng chữ `V` để không trùng ID của rule RTL.

### Điểm khác so với mô tả ở các mục trên

| Chủ đề | Mô tả ở Mục 2 đến 7 | Hiện thực | Lý do |
|---|---|---|---|
| Gate | VIP-0 đến VIP-3 là tiêu chí trưởng thành | Bốn gate duyệt của người dùng (Gate 1 đến 4) trùng với VIP-0, plan và architecture, VIP-2, VIP-3; VIP-1 là kiểm tự động cuối S4 | Gate cần quyết định của người dùng; VIP-1 là kiểm kỹ thuật |
| Độ rộng interface | "Tham số interface" | Tham số interface, class library ràng buộc qua macro cho `typedef virtual`; đổi độ rộng là biên dịch lại | Virtual interface có tham số không đổi độ rộng lúc chạy |
| `en_monitor` | Cờ bật monitor | Monitor luôn tồn tại để theo dõi reset; cờ chỉ điều khiển việc publish | Driver cần `in_reset` từ monitor |
| Callback | Tránh callback | Giữ nguyên; report catcher của qualification được miễn | Catcher không phải điểm mở rộng của VIP |
| Profile | Chưa nêu | Mỗi lần build một profile, mỗi profile một file bằng chứng | Tập tín hiệu khác nhau giữa các profile |
| Stub | "Stub báo ở time 0" | Mọi stub mang `VIP_TODO(<id>)` và tự báo khi chạy; stub của trace chủ động fail | Stub không được pass âm thầm |

### Trạng thái kiểm chứng của hiện thực

Đã chạy (2026-10-10; Python 3.11, Verilator 5.053, slang 12.0.0, Accellera UVM 2020.3.1): validator trên template và ví dụ APB (kèm biến thể sai cố ý); chuỗi plan, config, generate, gate và phát hiện thay đổi artifact đã duyệt; lệnh `vip` nhận biết run; lint Verilator `-Wall` cho interface và checker (không UVM) ở chế độ simulation và `VLSIT_VIP_FORMAL`; **kiểm kiểu toàn bộ cây UVM đã sinh với UVM 2020.3.1 bằng slang** (thư viện base, agent, driver, monitor, coverage, sequence, quickstart, 23 lớp test qualification; lỗi API cố ý đều bị bắt); build cho APB4, APB3 và một biến thể có check `CLASS`; runner và collector với simulator giả (chỉ kiểm logic script); lint qual và release, manifest, spec diff. `python3 scripts/selftest.py` chạy lại các kiểm tra này.

Chưa chạy (`NOT_RUN`): **mô phỏng** các class UVM (không có simulator UVM trên máy); hành vi lúc chạy của các property SVA; formal. Kiểm kiểu chứng minh code biên dịch đúng với UVM chính thức, không chứng minh hành vi lúc chạy.

### Tính năng giảm token (đã thêm ở bản 0.2)

Lệnh `vip` nhận biết run; đầu ra gọn mặc định (gom theo mã, ba ví dụ mỗi mã, rút gọn đường dẫn run); `vip scaffold` điền sẵn các bảng theo rule; `vip query` đọc theo bảng hoặc ID; `vip rules` in đúng nhóm rule; `vip brief` cho mỗi stage; biểu thức check nằm trong spec (Mục 8.1) nên assertion được sinh hoàn chỉnh và được duyệt ở Gate 1; test qualification được sinh hoàn chỉnh, chỉ phải viết task stimulus của counterpart; `vip worklist` và `vip impl-check`; `vip check-vip`. Đo trên ví dụ APB: lượng văn bản đọc ở đầu stage giảm khoảng 84% (303 K còn 50 K ký tự). Chi tiết trong README của repository.


## Phụ lục B. Vòng đời sau phát hành: reverse, bugfix, feature

Các Mục 2 đến 7 mô tả việc xây một VIP mới. Phụ lục này mô tả ba quy trình bổ sung, nằm trong cùng flow (cùng thư mục run, lệnh `vip`, gate và quy tắc bằng chứng): phân tích code VIP có sẵn để sinh spec (**reverse**), sửa lỗi VIP (**bugfix**) và thêm tính năng theo yêu cầu của người dùng (**feature**). Chọn chế độ bằng `vip init <root> <tag> --mode new|reverse|bugfix|feature`.

### B.1 Bốn chế độ

| Chế độ | Điểm xuất phát | Kết quả | Gate |
|---|---|---|---|
| `new` | Spec VIP hoặc standard | VIP đã phát hành | G1, G2, G3, G4 |
| `reverse` | Thư mục code VIP (`--code`) | Spec as-built và code được nhận làm cây nền | G1 |
| `bugfix` | Run gốc (`--base-run`) | Bản vá (patch +1), bằng chứng được mang sang cho trace không bị ảnh hưởng | G1, G2 mang từ run gốc; G3, G4 |
| `feature` | Run gốc (`--base-run`) | Bản minor (hoặc major), delta spec, port, re-qualify chọn lọc | G1 (delta), G2, G3, G4 |

Run gốc không bao giờ bị sửa. Run thay đổi chép những gì nó cần và ghi thêm `00_change/`, `00_base/base.json`, hoặc `00_code/`.

### B.2 Reverse: từ code sang spec

1. `vip inventory` quét từ vựng (không cần simulator, không sửa code): signal, tham số, assertion, covergroup, class theo vai trò (agent, driver, monitor, sequencer, item, config, sequence, ...), field cấu hình, message, TODO.
2. `vip from-code` soạn spec theo template: bảng signal, tham số, item, knob, capability, monitor, và mỗi assertion có nhãn thành một requirement kèm biểu thức Mục 8.1.
3. Mọi ô suy ra từ code ghi **UNVERIFIED** và con trỏ `CODE:<file>:<line>:<label>`. Code là bằng chứng về điều VIP đang làm, không phải về điều standard yêu cầu: hành vi trái standard là *phát hiện* (finding), không phải requirement.
4. Người review đối chiếu từng dòng với standard, điền điều khoản, strength, biên, injection, quyết định; bỏ chữ UNVERIFIED nhưng giữ con trỏ CODE để `vip verify-code` phát hiện lệch về sau.
5. Gate 1 từ chối spec còn UNVERIFIED (`--allow-unverified` cần ghi chú liệt kê phần còn lại). `vip adopt` nhận code làm cây nền cho các run sau. Code không do flow sinh có layout `external`: không có plan, kiến trúc, cây sinh tự động; Gate 2 không áp dụng; bằng chứng là báo cáo regression của project.

### B.3 Bugfix

1. Mỗi lỗi là một dòng trong `00_change/bug_log.csv`: triệu chứng, mức độ, lớp (`vip`, `trace`, `counterpart`, `environment`, `dut`, `spec`).
2. Trạng thái `open → analyzed → planned → fixed → verified → closed` chỉ chuyển khi có bằng chứng: lớp lỗi, requirement/file bị ảnh hưởng, **test hồi quy có tên (viết trước khi sửa)**, file log tồn tại, test nằm trong cây. Lỗi lớp `dut` là `wontfix`; lỗi lớp `spec` chuyển sang run feature.
3. `vip carry-gates` mang Gate 1 và 2 từ run gốc khi file đã duyệt giống hệt (so SHA-256) và người dùng đồng ý.
4. Sửa nhỏ nhất đủ giải thích triệu chứng; không refactor; không sửa `base/`.
5. `vip impact` so cây đã sửa với cây gốc; `vip carry` giữ PASS của trace không bị ảnh hưởng; `vip qual-run --impacted` chỉ chạy phần còn lại; test hồi quy của lỗi trở thành một entry bằng chứng (`kind: reg`).

### B.4 Feature

1. `00_change/change_request.md`: yêu cầu, nguồn, tiêu chí chấp nhận, tương thích.
2. Sửa bản chép spec trong run: dòng mới với ID mới (không dùng lại ID; requirement bị thay là `withdrawn`), biểu thức Mục 8.1, INJ cho check MUST, capability, knob có mặc định giữ hành vi cũ.
3. `vip delta` liệt kê dòng thêm, bỏ, đổi theo từng bảng và gợi ý bump version (major nếu bỏ hoặc đổi interface; minor nếu thêm). Người dùng duyệt **delta** ở Gate 1, không phải cả spec mới.
4. `vip plan`, `vip config`, Gate 2; rồi `vip port`: sinh lại skeleton của cấu hình cũ (tổ tiên chung) và của cấu hình mới, merge ba chiều với cây hiện tại bằng `git merge-file`: code viết tay được giữ, phần sinh mới được thêm, chồng lấn thành dấu xung đột (kiểm HY-09).
5. Chỉ cài đặt các stub mới (`vip worklist`), rồi `vip impact`, `vip carry`, `vip qual-run --impacted`, Gate 3 và Gate 4.

### B.5 Phạm vi tác động (`vip impact`)

| File thay đổi | Phạm vi | Chạy lại |
|---|---|---|
| Một khối check trong `<tag>_checker.sv` | Chọn lọc | trace đúng và sai của check đó |
| Một sequence trong `seq_lib/` | Chọn lọc | trace của requirement dùng sequence |
| Một task stimulus trong counterpart, hoặc một test | Chọn lọc | test đó |
| Class coverage | Coverage | thu lại coverage; bằng chứng pass/fail không đổi |
| Interface, check package, `base/`, agent, driver, monitor, item, config, package, hoặc code ngoài các khối trên | Toàn bộ | mọi trace |
| Tài liệu, filelist, bản chép spec, chuỗi version; phần đăng ký sinh tự động chỉ tăng thêm (số check, chỉ số, enum injection, include test) | Không / chọn lọc | không có / chỉ phần mới |

Đo trên ví dụ APB: thêm một check MUST mới cho 2 trace chạy lại trên 25; sửa một thông điệp check cho 3 trace (có test hồi quy) trên 24; thay đổi ở lớp dùng chung chạy lại tất cả.

### B.6 Trạng thái kiểm chứng của phần bổ sung

Đã chạy (`python3 scripts/selftest.py`, simulator giả cho phần chạy): bug log và các chặn chuyển trạng thái; mang gate; impact chọn lọc; carry bằng chứng; chạy lại chỉ trace bị ảnh hưởng; delta spec; port giữ code viết tay và thêm skeleton mới không xung đột; inventory, draft spec, verify-code và từ chối Gate 1 khi còn UNVERIFIED trên cây APB đã sinh; quét `tvip-axi` (101 file, 132 class) bằng inventory và draft; layout `external`. Chạy tay (ngoài selftest): `check-vip` (Verilator lint ở hai chế độ và kiểm kiểu UVM bằng slang với UVM 2020.3.1) trên cây APB đã port: PASS, 0 lỗi; một sửa tay chạm đúng dòng mà skeleton mới đổi tạo ra dấu xung đột, `vip port` thoát mã 1 và `lint impl` báo HY-09.

Chưa chạy (`NOT_RUN`): mô phỏng bằng simulator UVM thật; port trên VIP lớn nhiều chỉnh sửa tay; phân tích code có macro hoặc generate phức tạp (quét từ vựng có thể bỏ sót); suy diễn spec từ class-level check (cần đọc tay).
