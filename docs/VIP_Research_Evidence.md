# Bằng chứng nghiên cứu cho VLSIT VIP-FLOW

Phiên bản 0.1 · 2026-10-10 · Tài liệu bằng tiếng Việt, thuật ngữ kỹ thuật giữ tiếng Anh. Ghi lại cơ sở của quy trình trong [VLSIT_VIP_Build_Process.md](VLSIT_VIP_Build_Process.md): nguồn nào, đã đọc đến đâu, độ tin cậy, và thành phần nào của repository dựa vào nguồn đó.

## 1. Phương pháp và phạm vi

Câu hỏi nghiên cứu: phương pháp nào xây VIP ASIC bằng SystemVerilog chính xác, nhanh và dễ dùng, đi từ spec của standard hoặc protocol.

Cách làm: tìm trên Accellera/IEEE, DVCon, Verification Academy, OpenTitan, Arm, tài liệu hãng VIP; tải và trích text các bài báo PDF để đọc toàn văn khi có thể; đối chiếu với mã nguồn OpenTitan có sẵn trong repo (`opentitan/hw/dv/sv`). Nguồn nào không đọc được thì ghi rõ ở Mục 5.

Thang tin cậy: **A** = bài báo hoặc tài liệu kỹ thuật đã đọc toàn văn; **B** = tài liệu dự án hoặc trang web đọc qua bản trích xuất; **C** = chỉ đọc kết quả tìm kiếm hoặc trang tiếp thị; **D** = ý kiến diễn đàn.

## 2. Bảng nguồn

| # | Nguồn | Đọc | Tin cậy | Phát hiện chính | Dùng trong repository |
|---|---|---|---|---|---|
| S1 | Cerisier, Carmagnat, Basili, Curchod, *Qualification of a Verification IP under Requirement Based Verification standards* (DVCon) | Toàn văn | A | Bắt đầu từ spec của giao thức, không từ spec của VIP; phân tích biên hợp lệ và vi phạm; VIP là DUT; phía đối ứng độc lập; thư viện expected-error trên `uvm_report_catcher`; phân tích spec do người khác làm; qualification phát hiện assertion thiếu và assertion không được gọi đủ trường hợp | VQUA-01 đến VQUA-08, `vlsit_vip_expect_catcher`, bảng BND, template Mục 5.6 và 11 |
| S2 | Venkataramanan, Kumari, *Architecting Checker IP for AMBA protocols* (DVCon) | Toàn văn | A | Một property là assert ở phía phát và assume ở phía nhận; assert/assume/cover cùng bộ; `interface` làm container; che code UVM bằng macro cho formal; cẩn thận `$past`; unit test từng assertion bằng trace đúng và sai; khoảng 102 checker và 20 constraint cho master AXI3 (số xấp xỉ) | VCHK-02 đến VCHK-07, VIFC-08, `vlsit_vip_chk_macros.svh`, checker nhúng trong interface |
| S3 | Arm, *AMBA 4 AXI4, AXI4-Lite and AXI4-Stream Protocol Assertions User Guide* (DUI 0534B) | Cấu trúc, ID, tham số | B | ID assertion kèm cột tham chiếu mục spec; phân loại lỗi và khuyến nghị (`ERRM`, `ERRS`, `RECM`, `RECS`); tham số đặc tính interface; công tắc `RecommendOn`; ngưỡng `MAXWAITS` | Quy ước `chk_id`, VNAM-06, `rec_on`, VCHK-05, VCHK-10 |
| S4 | Sutherland, Fitzpatrick, *UVM Rapid Adoption: A Practical Subset of UVM* (DVCon, slide) | Toàn văn | A | UVM 1.2 có 357 class, 938 function, 99 task, 374 macro; tập con đề xuất 11 class, 33 task/function, 7 macro; nên tránh phase jumping và callback | VUVM-01, VP-03, thiết kế base package |
| S5 | Zhang, Radulovic, Dworzak (Infineon), *Fully Automated Verification Framework for Configurable IPs* (arXiv 2510.15902) | Toàn văn | A | Luồng yêu cầu, vPlan, ánh xạ sang SV, skeleton testbench, regression, báo cáo về công cụ yêu cầu; công sức mỗi cấu hình giảm từ 40 xuống 2 person-day (cho IP cấu hình được, không phải VIP) | Cấu trúc `requirements.csv`, `trace_lint.py`, sinh skeleton, báo cáo truy vết |
| S6 | OpenTitan, `uvmdvgen` | Trích xuất | B | Sinh agent skeleton: interface, item, cfg, cov, monitor, driver, base sequence, package, core file; người dùng điền sáu chỗ | Bộ sinh `gen_vip_skeleton.py`, danh sách stub |
| S7 | OpenTitan, DV methodology | Trích xuất | B | Mốc V1, V2, V3; testplan ánh xạ test với tính năng; exclusion cần thẻ phân loại và lý do; interface đẩy X lên kênh không hợp lệ; sign-off 100 seed | Gate VIP-0 đến VIP-3, VIFC-07, VQUA-06, chính sách exclusion |
| S8 | OpenTitan trong repo, `dv_base_agent`, `push_pull_agent` | Mã nguồn | A | Agent tạo monitor luôn, sequencer và driver khi active, driver host hoặc device theo `if_mode`; cfg một object chứa `vif`; cờ chuẩn; núm trễ `zero_delays`; clocking block theo vai trò | `vlsit_vip_agent_base`, `vlsit_vip_agent_cfg`, VCFG, VAGT, VDRV |
| S9 | ChipVerify, *Reusable verification components* | Trích xuất | B | Gói cfg một object; luật active/passive; protocol check ở VIP, data check ở scoreboard; mục README cần có; khuyên định nghĩa callback | VAPI-05, VCHK-09, `release_checklist.md` (callback bị bác bỏ, xem Mục 4) |
| S10 | ChipVerify, *Verification plan* | Kết quả tìm kiếm | C | Mỗi câu "shall" là một yêu cầu kiểm chứng | Quy tắc trích requirement |
| S11 | Hãng VIP: Siemens Questa VIP, Synopsys VC VIP, Cadence VIP | Kết quả tìm kiếm | C | VIP thương mại kèm protocol check, coverage model, test suite dạng source, kế hoạch kiểm chứng liên kết với coverage, error injection | Danh mục tính năng "dễ dùng" của hợp đồng UC; chỉ để tham chiếu, không dùng làm số liệu |
| S12 | AssertLLM (arXiv 2402.00386, 2411.14436); DVCon Europe 2024, *Enhanced VLSI Assertion Generation ... RAG* | Kết quả tìm kiếm và tóm tắt | C | LLM sinh được SVA từ spec; một thiết kế đạt 89% assertion đúng cú pháp và chức năng; RAG kèm bounded model checking giảm ảo giác | Quy tắc "đầu ra AI chỉ là nháp cho đến khi qua qualification" |
| S13 | Diễn đàn Verification Academy và Accellera (SVA trong interface hay bind; clocking block và modport) | Kết quả tìm kiếm | D | Ý kiến chia rẽ; nhiều bài từ 2012 đến 2013 | VIFC-04, VIFC-06; không dùng làm căn cứ chính |
| S14 | Accellera, thông báo IEEE 1800.2-2020 | Kết quả tìm kiếm | C | Chuẩn UVM 2020 miễn phí qua IEEE GET | Lựa chọn UVM version mặc định |

## 3. Phát hiện theo chủ đề

### 3.1 Bắt đầu từ spec của giao thức
S1 chỉ ra rằng lấy spec của VIP làm điểm vào thì assertion thiếu sẽ không ai phát hiện, vì cả quá trình qualification vẫn trông tốt. Hệ quả cho flow: stage intake đi từ standard, ánh xạ mọi câu quy phạm (`scan_normative.py`), cảnh báo requirement không có câu nguồn, và yêu cầu người review khác người cài đặt.

### 3.2 Truy vết và ID
S3 đặt ID cho từng assertion kèm tham chiếu điều khoản; S5 nối yêu cầu với vPlan, assertion, coverage, test và kết quả; S10 coi mỗi câu "shall" là một yêu cầu. Hệ quả: `requirement ID` vĩnh viễn, `chk_id` dẫn xuất theo quy tắc cố định, `trace_lint.py` ở bốn stage.

### 3.3 Checker IP
S2 cho thấy checker tách khỏi stimulus dùng được cho cả simulation và formal nếu property viết một lần, phân biệt vai trò, và code UVM được che. Hệ quả: checker là `interface` không phụ thuộc UVM, macro `VLSIT_VIP_CHK_ERR/REC`, vector enable theo check, `PARA_DUT_ROLE`, cover của antecedent đi kèm.

### 3.4 Kiến trúc UVM và dễ dùng
S4 và S8 cho kiến trúc agent và tập con UVM; S9 cho các mục README; S7 cho việc interface đẩy X. Hệ quả: một cfg object, ba bước dùng, `quickstart` loopback, thông báo mang ID, waiver theo ID có lý do, `zero_delays`.

### 3.5 Qualification
S1 và S2 cùng đi đến: mỗi checker cần trace đúng và trace sai tự kiểm, trace sai phải khai báo lỗi mong đợi, phía đối ứng độc lập. Mutation testing chỉ ra checker thiếu nhưng khó truy vết về yêu cầu. Hệ quả: `vlsit_vip_expect_catcher`, `vlsit_vip_qual_test_base` (từ chối trace rỗng), dòng kết quả `VLSIT_VIP_QUAL_RESULT`, ma trận bằng chứng chỉ cập nhật từ log.

### 3.6 Tự động hóa
S5 và S6 cho thấy phần cơ học (ID, skeleton, báo cáo) tự động hóa được, còn nội dung giao thức cần người. Hệ quả: máy sinh ID, skeleton, stub chủ động báo, bảng truy vết; AI soạn nháp và người duyệt.

## 4. Mâu thuẫn giữa các nguồn và quyết định

| Vấn đề | Quan điểm | Quyết định |
|---|---|---|
| Callback | S4 khuyên tránh; S9 khuyên định nghĩa `pre_drive`, `post_drive`, `pre_reset`, `post_reset` | Tránh. Dùng cờ cfg, field của item, factory override và sequence (VP-03). Report catcher của qualification được miễn vì không phải điểm mở rộng của VIP |
| Truyền cfg xuống thành phần con | Giữ cfg ở agent rồi chép biến; hay truyền handle | Truyền handle (như S8), một nguồn sự thật |
| `en_monitor` | S8 mô tả là bật monitor | Monitor luôn tồn tại vì theo dõi reset; `en_monitor` chỉ điều khiển việc publish |
| Độ rộng và virtual interface | Class parameterized theo độ rộng; hay interface tối đa; hay macro | Macro mỗi tham số với giá trị mặc định cho `typedef virtual`; đổi độ rộng là biên dịch lại, ghi rõ trong VIFC-01. Lý do: virtual interface có tham số không đổi độ rộng lúc chạy |
| Container của checker | Module, bind, interface, `checker` | Interface (S2: interface chứa được interface, module thì không); `checker` construct bị công cụ hỗ trợ không đều |

## 5. Những gì không đọc được hoặc chưa kiểm

- UVM Cookbook và các session VIP, EZ-VIP trên Verification Academy nằm sau đăng nhập; chỉ đọc được phần tóm tắt.
- Toàn văn IEEE 1800.2-2020 và UVM User Guide chưa đọc.
- Spec APB (IHI 0024) chưa đọc; ví dụ APB dùng tên điều khoản, chưa kiểm số điều khoản.
- Tài liệu hãng VIP là tài liệu tiếp thị, không dùng làm số liệu.
- Kết quả AssertLLM và bài RAG mới đọc phần tóm tắt; con số 89% chỉ trên một thiết kế.
- Phát biểu cũ về assertion đồng thời trong class (khoảng 2013) chưa kiểm với LRM hiện hành; thiết kế tránh phụ thuộc vào nó.

## 5a. Bằng chứng từ việc xây dựng (không phải từ tài liệu)

Khi hiện thực, hai điều đã được kiểm bằng công cụ chứ không dựa vào nguồn: (1) `$get_initial_random_seed` mà tôi dùng ban đầu không thuộc IEEE 1800 (mở rộng của một hãng), được slang chỉ ra khi biên dịch với UVM 2020.3.1, và đã thay bằng plusarg `+VLSIT_SEED`; (2) lint theo profile cần biết profile của bản build, được phát hiện khi build APB3. Bài học: kiểm kiểu bằng slang với UVM chính thức bắt được lỗi API mà đọc code không thấy.

## 6. Từ phát hiện đến thành phần

| Phát hiện | Rule | Skill | Script hoặc asset |
|---|---|---|---|
| Spec giao thức trước, review độc lập | VQUA-07, VDOC-04 | `vlsit-vip-spec-intake` | `scan_normative.py`, `validate_vip_spec.py` |
| Mỗi câu quy phạm là yêu cầu có ID | VNAM-03, VNAM-06 | `vlsit-vip-spec-intake`, `vlsit-vip-vplan` | `extract_requirements.py`, template Mục 5 |
| Biên hợp lệ và vi phạm | VQUA-01, VCOV-01 | `vlsit-vip-spec-intake`, `vlsit-vip-qualifier` | bảng BND, `gen_cov` |
| Property một lần, vai trò, formal | VCHK-02, VCHK-04, VIFC-08 | `vlsit-vip-generator` | `vlsit_vip_chk_macros.svh`, `gen_checker` |
| Tập con UVM, agent chuẩn | VUVM-01, VAGT-01 | `vlsit-vip-architect`, `vlsit-vip-generator` | `assets/base` |
| Expected-error, trace rỗng | VQUA-04, VQUA-05, VP-11 | `vlsit-vip-qualifier` | `vlsit_vip_expect_catcher.sv`, `vlsit_vip_qual_test_base.sv` |
| Bằng chứng chỉ từ log | VQUA-08 | `vlsit-vip-qualifier` | `collect_qual_results.py` |
| Gate trưởng thành | Mục 11 của rule | `vlsit-vip-flow` | `vip_state.py` |
| Sinh skeleton | VFIL-03 | `vlsit-vip-generator` | `gen_vip_skeleton.py` |
| AI chỉ soạn nháp | VCHK-06, VQUA-01 | tất cả | `trace_lint.py` |

## 7. Danh sách liên kết

- Cerisier et al. (DVCon): https://dvcon-proceedings.org/wp-content/uploads/qualification-of-a-verification-ip-under-requirement-based-verification-standards-an-approach-to-the-verification-of-the-verification.pdf
- Venkataramanan và Kumari (DVCon): https://dvcon-proceedings.org/wp-content/uploads/architecting-checker-ip-for-amba-protocols.pdf
- Arm DUI 0534B: https://documentation-service.arm.com/static/5f106bd90daa596235e808ed
- Sutherland và Fitzpatrick (DVCon): https://dvcon-proceedings.org/wp-content/uploads/uvm-rapid-adoption-a-practical-subset-of-uvm.pdf
- Infineon (arXiv): https://arxiv.org/pdf/2510.15902
- OpenTitan `uvmdvgen`: https://opentitan.org/book/util/uvmdvgen
- OpenTitan DV methodology: https://opentitan.org/book/doc/contributing/dv/methodology/
- ChipVerify, reusable verification components: https://chipverify.com/uvm/reusable-verification-components
- ChipVerify, verification plan: https://www.chipverify.com/verification/verification-plan
- AssertLLM: https://arxiv.org/html/2411.14436v1 và https://arxiv.org/pdf/2402.00386
- DVCon Europe 2024, RAG: https://dvcon-proceedings.org/wp-content/uploads/195-Enhanced-VLSI-Assertion-Generation-Conforming-to-High-Level-Specifications-and-Reducing-LLM-Hallucinations-with-RAG.pdf
- Siemens Questa VIP: https://resources.sw.siemens.com/en-US/fact-sheet-questa-verification-ip
- Synopsys VC VIP test suites: https://origin-www.synopsys.com/verification/verification-ip/verification-test-suites.html
- Cadence VIP, qua Electronic Design: https://www.electronicdesign.com/products/reusable-verification-ip-fits-overall-automation-planning
- Accellera, IEEE 1800.2-2020: https://www.eejournal.com/industry_news/uvm-reference-implementation-aligned-with-ieee-1800-2-2020-standard
