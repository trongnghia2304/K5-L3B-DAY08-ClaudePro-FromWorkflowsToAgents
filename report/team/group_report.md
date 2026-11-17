# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: ClaudePro
- Thành viên: xem `TEAM.md` (5 người: Nguyễn Đức Minh, Nguyễn Quang Huy, Nguyễn Nghiêm Khánh Tiệp, Tăng Nguyễn Hải Đăng, Nguyễn Trọng Nghĩa)
- Commit chốt (trùng `report/team/decision_adr.md`): `f5adbd9`
- Shape chọn cho cổng hidden: `workflow`

## 2. Mục tiêu và cách tiếp cận

**Bài toán.** Xử lý claim hoàn phí vận chuyển của LogiX-VN bằng bốn kiến trúc cùng chữ ký `run_claim`, rồi chọn kiến trúc **ít tự chủ nhất mà vẫn làm được việc** dựa trên số đo. Nhóm đọc đề theo ba nguyên tắc: (1) tiền, approval và chống ghi trùng do code quyết, model chỉ đọc và soạn chữ; (2) chữ trong ticket là dữ liệu người dùng, không phải lệnh hay nguồn sự thật; (3) trace là ranh giới bảo mật, chỉ ghi field đã qua allowlist.

**Chia việc.** Mỗi shape một người, cộng một người lo an toàn/tích hợp và một người lo đánh giá (chi tiết ở `TEAM.md`):

| Người                    | Phần việc                                                                   |
| ------------------------ | --------------------------------------------------------------------------- |
| Nguyễn Đức Minh          | Shape A `workflow` (CP2–CP3)                                                |
| Nguyễn Quang Huy         | Shape B `single` (CP2–CP3)                                                  |
| Nguyễn Nghiêm Khánh Tiệp | Shape C `orchestrator` + handoff (CP2–CP3)                                  |
| Tăng Nguyễn Hải Đăng     | Safety & Testing, audit nhánh, tích hợp, crash suite (CP1, CP4)             |
| Nguyễn Trọng Nghĩa       | Repo nhóm, benchmark, hidden self-check, ADR, research card, bonus B3 (CP5) |

**Thứ tự làm.** CP1: mọi người cài môi trường, chạy smoke và lấy baseline (54 host passed; ma trận student 186 failed, 62 passed vì ba shape còn là stub). CP2–CP3: ba shape viết song song trên ba nhánh riêng (`Workflow_CP2,3`, `nguyenquanghuy`, `feature/orchestrator`), mỗi nhánh phải đạt 62 student test của shape đó, T11 và T12 xanh. CP4: Đăng audit từng nhánh trong `git worktree` tạm trước khi merge qua pull request, rồi chạy crash suite trên nhánh tích hợp. CP5: sau khi cả ba shape đã ở `main`, chạy benchmark 4 shape × 5 seed, tự kiểm trên `student_drop/`, chọn shape và viết ADR. Swarm (D) dùng nguyên bản tham chiếu để đối chứng.

## 3. Giải pháp

Cả ba shape đi cùng một chuỗi tuần tự: đọc claim qua `get_claim_view` → thiếu `order_id` thì `needs_info` → `lookup_order` theo principal của claim (không thấy hoặc sai chủ thì `escalated`) → `compute_compensation` từ order row (quote 0 thì `denied`, không gọi host) → `durability.issue_refund(conn, claim_id, <quote đầy đủ>, crash_at=crash_at)` → ánh xạ kết quả host (`ok` → `resolved`, `conflict` → `failed`, bị từ chối → `denied`, `proposal_amount` vẫn là quote đầy đủ). Ba shape chỉ khác nhau ở **ai chọn bước tiếp theo**: code cố định (A), một vòng ReAct (B), hay orchestrator giao việc cho investigator (C). Ở cả ba, host là bên ghi duy nhất, `InjectedCrash` được ghi trace rồi `raise` lại, và mọi nhánh return đi qua `lab8.shapes.common.finish()` nên luôn có trace đúng contract.

### 3.1 Shape A — Workflow

Code: `src/lab8/shapes/workflow.py` (Nguyễn Đức Minh). Test riêng: `src/tests/test_workflow.py`.

**Luồng xử lý.** Bốn bước Python cố định: `get_claim_view` → `lookup_order` → `compute_compensation` → `issue_refund`. Hàm nội bộ `respond()` gom mọi nhánh return về `finish()`, và `finish()` đọc effect và số audit committed từ ledger thay vì tự gán. Kết nối SQLite luôn được đóng trong `finally`.

**Ranh giới code và model.** Workflow **không gọi MockLLM lần nào** (`mean_model_calls = 0` trong benchmark): mọi quyết định đều là code. Số ngày trễ trong ticket không bao giờ được đọc, nên T02 ("trễ 5 ngày" trong khi order trễ 2 ngày) luôn `denied` ở mọi seed.

**Trace.** Event `get_claim_view` (chỉ `found`), `lookup_order` (view đã qua allowlist `ORDER_FIELDS`), `quote`, `issue_refund` (proposal), `refund_outcome` (ok, reason, conflict), `decision`. Trace được ghi xuống đĩa ngay trước khi gọi host để vẫn còn dấu vết nếu crash thử nghiệm xảy ra.

**Kiểm chứng.** 62/62 student test workflow (gồm T11, T12); 3 test riêng: claim không tồn tại vẫn có trace hợp lệ và không đổi ledger; thiếu approval giữ quote đầy đủ nhưng không hoàn tiền và có `policy_denied`; quote đổi khi retry báo `amount_conflict` và giữ số cũ.

### 3.2 Shape B — Single agent

Code: `src/lab8/shapes/single.py` (Nguyễn Quang Huy). Test riêng: `src/tests/test_single.py`.

**Luồng xử lý.** Shape đọc claim view, xử lý `failed` / `needs_info` trước vòng lặp, rồi chạy `lab8.runtime.run_react` với `max_steps=8` và `worker=True` (runtime từ chối mọi tool ghi). Hàm `decide` là một máy trạng thái ba bước: chọn `lookup_order` → đọc kết quả (không thấy thì `final: escalated`) rồi chọn `compute_compensation` → đọc quote (0 thì `final: denied`, > 0 thì `final: ready_to_refund`). Vòng lặp dừng ở `final` sau 3 bước, không chạm trần. Sau vòng lặp, **code của shape** (không phải model) gọi `issue_refund` với quote đầy đủ và `crash_at`.

**Ranh giới code và model.** Mỗi bước `decide` là một model call (`purpose="react"`) được tính vào `Budget`, cộng 1 lần `draft`; trung bình 3.71 model call mỗi trial. Model không chọn số tiền: quote đến từ tool `compute_compensation` trên order row, và model không có quyền gọi `issue_refund`.

**Trace.** Event `claim`, `react_action` (chỉ tên tool), `react_observation` (visible, reason), `quote`, `decision`, `crash`. Không ghi args của tool (có order row) và không ghi ticket.

**Kiểm chứng.** 62/62 student test single (gồm T11, T12); 8 test riêng về tình huống biên, trần theo đơn, an toàn secret và phục hồi sau crash.

### 3.3 Shape C — Orchestrator

Code: `src/lab8/shapes/orchestrator.py`. Test riêng: `src/tests/test_orchestrator_own.py`.

**Luồng xử lý.** Orchestrator đọc claim row, rồi chia việc thành hai vai:

1. Claim không tồn tại thì `failed`. Thiếu `order_id` thì `needs_info` (không lấy mã đơn từ chữ trong ticket).
2. Orchestrator dựng handoff bằng `lab8.handoff.make_handoff` với `facts` rỗng và bốn tool chỉ đọc theo thứ tự `lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`. `lookup_order` đứng trước vì `compute_compensation` cần dữ liệu đơn.
3. Investigator chạy qua `run_readonly_investigators`. Investigator không có tool ghi và không thấy claim row.
4. Đơn không thấy hoặc sai chủ thì `escalated`. Quote bằng 0 thì `denied` và không gọi host.
5. Quote lớn hơn 0 thì **orchestrator** (không phải investigator) gọi `durability.issue_refund` với quote đầy đủ và `crash_at`. Host tự trừ phần đã hoàn trên cùng đơn, nên shape không tự trừ (T13, T14).
6. Kết quả host được ánh xạ: ghi được thì `resolved`; từ chối thì `denied`; xung đột số tiền thì `failed`. `proposal_amount` luôn là quote đầy đủ.

**Ranh giới code và model.** Số tiền do `compute_compensation` tính từ dòng order trong database. Ngày trễ trong ticket không được dùng, nên shape không có điểm yếu "tin ticket" như swarm tham chiếu. MockLLM chỉ được gọi hai lần mỗi claim (`plan`, `draft`) để soạn chữ, không quyết định tiền, approval hay ghi ledger.

**Handoff và trace.** Handoff đi qua allowlist trong code (`ALLOWED_FIELDS`, `FACT_KEYS`), không dùng tóm tắt bằng LLM làm bước lọc. Trace chỉ ghi handoff đã sanitize, kết quả `lookup_order`, số policy, quote và quyết định (event `handoff`, `investigator`, `quote`, `decision`, `error`, `crash`). Không ghi claim row, ticket hay parent context. Mọi nhánh return đều đi qua `finish()` nên luôn có trace hợp lệ.

**Crash.** `crash_at` được truyền vào `issue_refund`. `InjectedCrash` chỉ ghi trace rồi `raise` lại, không bị bắt.

**Kiểm chứng (chạy ngày 2026-11-17).**

- `pytest -q -m student -o addopts= -k orchestrator`: 62 passed (gồm T11 gọi lại cùng claim, T12 crash rồi resume).
- `pytest -q` (cổng host): xanh.
- `test_orchestrator_own.py` (16 test): trace và kết quả của 14 claim public không có `CANARY_SECRET_` hay thông tin cá nhân; handoff không có `parent_secret`, `raw_headers` hay tool ghi; crash vẫn ném `InjectedCrash`.
- Benchmark CP5 (`src/reports/benchmark.json`): pass rate 1.000, pass^5 1.000, variance 0, cost/success 56.87 VND, trung bình 1.79 model call và 5.57 tool call mỗi trial (đắt nhất trong bốn shape vì investigator gọi thêm `lookup_policy`, `lookup_refund_history`, `compute_compensation`).

### 3.4 Đảm bảo an toàn, Durability và Kiểm thử tích hợp (Safety & Testing)

Người phụ trách: Tăng Nguyễn Hải Đăng (Thành viên 4). Commit test an toàn chính: `733745d` (`src/tests/test_safety_approval_invariant.py`).

**Cổng duyệt Approval & Host Policy:**

- Kiểm thử bất biến an toàn (`src/tests/test_safety_approval_invariant.py`): Giả lập claim có đơn hàng hợp lệ (`O-107`, trễ 4 ngày, đủ điều kiện hoàn 35.000 VND, chính chủ `P-100`) nhưng approval gắn kèm có trạng thái `rejected` (`A-TEST-REJECTED`). Khi gọi `durability.issue_refund`, cổng host từ chối (`outcome["ok"] is False`, lý do `approval_rejected`, `effect is None`), không tạo dòng hoàn tiền nào trong `refund_ledger` (`get_refund is None`, số dòng ledger giữ nguyên), đồng thời ghi nhận sự kiện `policy_denied` vào `audit_events`.
- Kết hợp với các test host có sẵn (`test_authorization.py`, `test_order_cap_and_approval_binding.py`), hệ thống chặn các trường hợp approval hết hạn, thiếu approval hoặc approval bị mượn từ claim khác.

**Idempotency, Ledger và Audit Trails:**

- Khóa duy nhất `refund:{claim_id}` trong SQLite giúp ghi nhận đúng một lần (exactly-once): gọi lại cùng claim nhiều lần không tạo thêm dòng ledger, trả về `idempotent_replay` và giữ đúng 1 sự kiện `refund_committed`. Nếu quote thay đổi khi retry, hệ thống báo xung đột (`amount_conflict`) và giữ nguyên số tiền đã commit trước đó.
- Xử lý trần hoàn tiền theo đơn (per-order cap): Cả 4 shape đều chuyển quote đầy đủ để host tự trừ phần đã hoàn trước đó (T13 từ chối vì đã hoàn đủ, T14 chỉ hoàn phần chênh lệch).

**Crash Safety & Khôi phục sau sự cố:**

- Cả 3 shape mới viết đều chuyển tiếp tham số `crash_at` vào host và không nuốt `InjectedCrash`.
- Kết quả chạy lệnh `python -m lab8.crash_test --count 20 --out reports/crash.json` đạt `crash_safety: 20/20`. Bộ test kiểm tra 20 kịch bản gồm crash trước khi ghi ledger (`before_effect`), sau khi ghi ledger nhưng trước checkpoint (`after_effect_before_checkpoint`), sau checkpoint, xung đột retry và retry không approval. Khi resume sau crash, hệ thống không thanh toán trùng (không double-pay).

**Bảo mật Trace và Vùng cách ly Handoff:**

- Handoff của Orchestrator được lọc qua allowlist bằng `make_handoff`; investigator chỉ đọc không có tool ghi và không tiếp cận thông tin nhạy cảm.
- Bộ 16 test rà soát trace (`src/tests/test_orchestrator_own.py`) và test Single (`src/tests/test_single.py`) xác nhận trace và kết quả của 14 claim public không chứa `CANARY_SECRET_*`, token Bearer, số điện thoại, địa chỉ hay ghi chú nội bộ.

**Kết quả kiểm thử tích hợp (chạy thực tế trên nhánh tích hợp):**

> Thời điểm chạy: ngày 2026-11-17, trên nhánh `feat/dang-safety-testing` sau merge commit `07202ef` (11:04), trước khi thêm benchmark CP5 và bonus B3. Sau khi thêm `src/tests/test_bonus_swarm_verified.py` (29 test), cổng host `python -m pytest -q` trên nhánh `feat/cp5-benchmark-bonus` là **108 passed**; ma trận student và crash suite không đổi.

- **Smoke test:** `lab8.smoke pass`.
- **Cổng host:** `79 passed` (54 test host ban đầu, 16 test orchestrator, 8 test single, 1 test safety invariant).
- **Ma trận student cả 4 shape:** `251 passed` (248 test ma trận T01–T14 × 5 seed cho 4 shape + 3 test workflow), 0 failed.

**Giới hạn xác minh:**

- Toàn bộ kết quả kiểm thử trên được xác minh trên bộ dữ liệu public (T01–T14). Đây là bằng chứng an toàn và tính đúng đắn tích hợp của hệ thống, chưa phải số liệu benchmark hay đánh giá trên bộ dữ liệu ẩn (hidden test suite CP5).

## 4. Kết quả

**Benchmark bộ public** (`src/reports/benchmark.json`, commit `5e1d8bf`; 14 claim × seed `11,22,33,44,55` = 70 trial mỗi shape; MockLLM, `config/pricing.yaml`, SQLite mới cho mỗi trial):

| Shape          | Pass rate | pass^5 | Seed min–max | Variance | Cost/success (VND) | Model calls TB | Tool calls TB | Steps TB / p95 |
| -------------- | --------: | -----: | ------------ | -------: | -----------------: | -------------: | ------------: | -------------- |
| A workflow     |     1.000 |  1.000 | 1.000–1.000  |        0 |              34.29 |           0.00 |          3.43 | 5.07 / 6       |
| B single       |     1.000 |  1.000 | 1.000–1.000  |        0 |              29.72 |           3.71 |          2.79 | 4.93 / 6       |
| C orchestrator |     1.000 |  1.000 | 1.000–1.000  |        0 |              56.87 |           1.79 |          5.57 | 2.86 / 3       |
| D swarm        |     0.986 |  0.929 | 0.929–1.000  | 0.000816 |              49.57 |           3.00 |          4.66 | 2.80 / 3       |

- Swarm fail đúng một trial: `R-swarm-C-002-s55` (`status resolved != denied`). Ở seed 55 swarm tin "trễ 5 ngày" trong ticket thay vì order trễ 2 ngày và trả 20.000 VND. Ba shape nhóm viết đều `denied` đúng ở trial này.
- **Cost chưa so ngang hoàn toàn:** workflow đếm lần gọi `issue_refund` của host là 1 tool call (10 VND), ba shape còn lại không đếm. Bỏ khoản này thì workflow còn ≈ 27.86 VND/success, rẻ nhất. Model call chỉ tốn khoảng 0.3 VND mỗi lần nên cost gần như do số tool call quyết định.
- `steps` đếm số event trong trace, nên phụ thuộc vào việc mỗi shape ghi trace chi tiết đến đâu, không so trực tiếp được số bước suy luận giữa các shape.

**Crash safety:** `python -m lab8.crash_test --count 20 --out reports/crash.json` → `crash_safety 20/20` (`src/reports/crash.json`).

**Tự kiểm trên `student_drop/`** (`src/reports/hidden_selfcheck.json`, 40 claim × 5 seed × 3 shape = 600 trial, không có nhãn): 0 trial `error`, 0 `leak_suspect`; cả ba shape cho **cùng status ở mọi (claim, seed)** (mỗi shape: 95 `denied`, 90 `resolved`, 10 `escalated`, 5 `needs_info`). Không có nhãn nên đây không phải pass rate; điểm hidden chính thức do grader của giảng viên chấm.

**Quyết định:** chọn `workflow`. Khi chất lượng ngang nhau trên cùng corpus và seed, nhóm chọn shape ít tự chủ nhất: không gọi model, không có đường để chữ trong ticket ảnh hưởng tới số tiền, variance 0. Chi tiết và điều kiện đảo quyết định: `report/team/decision_adr.md`. Phiếu nghiên cứu R1 (ablation workflow → orchestrator: pass giữ 1.000, cost/success +65.9%): `report/team/research_card.md`.

**Bonus B3** (`report/team/bonus_report.md`): thêm verifier bằng code trước bước ghi của swarm (`src/bonus/swarm_verified.py`). Pass rate public 0.986 → 1.000; trên 12 claim đối kháng tự viết có nhãn tay 0.933 → 1.000 (pass^5 0.667 → 1.000), cost/success gần như không đổi so với swarm và vẫn cao hơn workflow. Verifier can thiệp 8 lần, 5 lần đổi số tiền, đúng 5 trial swarm gốc fail.

## 5. Khó khăn và cách xử lý

| Khó khăn                                        | Biểu hiện                                                                                                                                                                       | Cách xử lý                                                                                                                                                               |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Lệnh `python` mặc định không chạy, thiếu pytest | Máy của Minh không chạy được `python -m pytest`                                                                                                                                 | Dùng `uv run` với Python 3.12; các máy còn lại dùng `src/.venv` theo `src/README.md`. Mọi số liệu đều chạy lại trên `.venv` của nhánh tích hợp                           |
| `-k single` lọc nhầm                            | `python -m pytest -q -m student -o addopts= -k single` ra "60 failed" khi orchestrator còn là stub, vì `-k single` khớp cả tên hàm `test_public_single_run_cases` của mọi shape | Đếm theo tham số `[single]` trong output `-rA`, hoặc dùng `-k "single and not workflow and not orchestrator and not swarm"`                                              |
| Hiểu nhầm demo lỗi                              | `python -m lab8.demo.buggy_workflow` in `unsafe refund rows: 2`                                                                                                                 | Đây là kết quả mong đợi: demo cố ý cho thấy checkpoint một mình không chống được ghi trùng. Ledger của host khoá theo `refund:{claim_id}` nên vẫn 1 dòng (T11, T12 xanh) |
| `lab8.crash_test` không chọn được shape         | `--shape workflow` báo `unrecognized arguments`                                                                                                                                 | Crash suite chạy bằng lệnh mặc định (20/20); hành vi crash của từng shape được kiểm riêng bằng T11, T12 trong ma trận student và test riêng của mỗi người                |
| Nhánh single thiếu test và tài liệu             | Lần audit đầu của Đăng trên nhánh `nguyenquanghuy` không thấy test riêng                                                                                                        | Huy bổ sung `test_single.py` (8 test) ở `cabceb8`; Đăng audit lại rồi mới merge (PR #3)                                                                                  |
| Cost của single "rẻ hơn" workflow               | Benchmark ra 29.72 so với 34.29 VND/success                                                                                                                                     | Đọc lại code đếm `Budget` của từng shape, phát hiện workflow đếm cả lần gọi host; ghi rõ trong ADR thay vì kết luận "single rẻ hơn"                                      |
| Gói `student_drop` lồng thư mục                 | File zip giải nén thành `student_drop/student_drop/` kèm `__MACOSX/`                                                                                                            | Chép hai file `hidden_claims.jsonl`, `hidden_world_state.json` vào `src/student_drop/` (đã có trong `.gitignore`, không commit)                                          |

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân trong `report/team/`:

- `2A202603765_NguyenDucMinh.md`: workflow, commit `5cbc99e`, `3ea6a00`; `test_workflow.py`.
- `2A202603768_NguyenQuangHuy.md`: single, commit `069a071`, `cabceb8`; `test_single.py`.
- `2A202603863_NguyenNghiemKhanhTiep.md`: orchestrator, commit `906e466`; `test_orchestrator_own.py`.
- `2A202603916_TangNguyenHaiDang.md`: safety & testing, commit `733745d`; `test_safety_approval_invariant.py`.
- `2A202603835_NguyenTrongNghia.md`: benchmark, ADR, research card, bonus B3, commit `5e1d8bf`, `e492c52`, `f5adbd9`; `test_bonus_swarm_verified.py`.

## 7. Hạn chế và hướng cải thiện

- **MockLLM không phải model sản xuất.** Cost là VND mô phỏng, latency là `unavailable`. Điểm yếu duy nhất của swarm là lỗi tất định cài sẵn ở seed % 5 == 0; với model thật, single và orchestrator có thể sai ở những chỗ mà benchmark này không đo được, và swarm có thể sai nhiều hơn.
- **Corpus nhỏ.** Chỉ 14 claim public (và 12 claim đối kháng tự viết cho bonus); pass rate 1.000 trên public chưa chứng minh kết quả hidden. Bộ hidden tự kiểm không có nhãn.
- **Đo chưa đồng nhất.** Cách đếm tool call cho lần gọi host khác nhau giữa các shape; `steps` phụ thuộc độ chi tiết của trace. Hướng cải thiện: thống nhất một quy ước đếm (ví dụ không đếm lần gọi host ở mọi shape) rồi chạy lại benchmark.
- **Single và orchestrator không thêm năng lực.** `decide` và investigator được viết để làm đúng các bước của workflow, nên phần "agent" chỉ thêm model call. Kết luận chọn workflow sẽ đảo lại nếu: claim cần đọc hiểu chữ tự do mà rule cố định không xử lý được (workflow sẽ `needs_info` quá nhiều); có nhiều nguồn tra cứu độc lập chạy song song được với latency thật (orchestrator có lợi về critical path); hoặc hidden cho workflow < 0.75 trong khi shape khác vượt ngưỡng với cùng safety counts.
- **Chưa kiểm tải đồng thời** ngoài các ca có sẵn trong host (hai claim cùng đơn ghi cùng lúc).

## 8. Tài liệu tham khảo

- Đề bài và tài liệu của lab: `README.md`, `CHECKPOINTS.md`, `RUBRIC.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/architecture.md`, `docs/metrics.md`, `docs/bonus_topics.md`.
- Code tham chiếu: `src/lab8/shapes/swarm_reference.py`, `src/lab8/durability.py`, `src/lab8/handoff.py`, `src/lab8/runtime.py`.
