# Báo cáo cá nhân — Nguyễn Trọng Nghĩa — 2A202603835

## 1. Thông tin thành viên

- Họ tên: Nguyễn Trọng Nghĩa
- MSSV: 2A202603835
- Email: nghiatrongnguyen2304@gmail.com
- GitHub: trongnghia2304

## 2. Phần việc phụ trách

Vai trò: **Evaluation, quyết định kiến trúc (CP5) và bonus B3**.

- **CP5 — Benchmark và quyết định kiến trúc:** chạy benchmark 4 shape × 5 seed trên bộ public, tự kiểm 3 shape trên `student_drop/` (bộ hidden không nhãn), chọn shape bằng số đo và điền `report/team/decision_adr.md`, `report/team/research_card.md`.
- **Bonus B3 — Verifier/aggregator chống khuếch đại lỗi:** viết biến thể `swarm_verified` trong `src/bonus/`, bộ 12 claim đối kháng có nhãn viết tay, test bonus, report `src/reports/bonus_b3*.json` và `report/team/bonus_report.md`.
- Repo nhóm do tôi - leader tạo (`trongnghia2304/K5-L3B-DAY08-ClaudePro-FromWorkflowsToAgents`); nhánh làm việc: `feat/cp5-benchmark-bonus`.

## 3. Đóng góp cụ thể

### A. CP5 — Benchmark, hidden self-check, ADR, research card

- **Commit `5e1d8bf`** — `Create benchmark.json`: `src/reports/benchmark.json` do `lab8.benchmark` sinh (4 shape × 14 claim × seed `11,22,33,44,55`, 280 trial).
- **Commit `e492c52`** — `feat: Add decision_adr & research_card`.
- **Hidden self-check:** `src/reports/hidden_selfcheck.json` (workflow, single, orchestrator × 40 claim × 5 seed).
- **Quyết định kỹ thuật:**
  - **Chọn `workflow`.** Ba shape nhóm viết cùng đạt pass 1.000, pass^5 1.000, variance 0; swarm 0.986 / 0.929 vì fail `R-swarm-C-002-s55` (tin "trễ 5 ngày" trong ticket thay vì order trễ 2 ngày). Khi chất lượng ngang nhau thì chọn shape ít tự chủ nhất: workflow không gọi model lần nào, tiền/approval/ledger đều do code quyết.
  - **Phát hiện cost chưa so ngang:** single (29.72 VND/success) có vẻ rẻ hơn workflow (34.29) chỉ vì workflow đếm lần gọi `issue_refund` của host là 1 tool call (10 VND) còn single, orchestrator, swarm thì không. Tôi ghi rõ điều này trong ADR thay vì kết luận "single rẻ hơn"; đếm cùng luật thì workflow ≈ 27.86, rẻ nhất.
  - **Research card chọn R1 · Scaling:** ablation workflow → orchestrator (chỉ đổi topology, giữ cố định model, tool, seed, corpus, giá, evaluator). Kết quả: pass giữ 1.000, cost/success tăng 34.29 → 56.87 VND (+65.9%), đúng hypothesis "task tuần tự thì thêm agent chỉ thêm chi phí". Phần "giảm chất lượng 39–70%" của nguồn không tái hiện vì tiền do code quyết và investigator tất định.

### B. Bonus B3 — `swarm_verified`

- **Code:** `src/bonus/swarm_verified.py` giữ nguyên flow, model call và REFERENCE_WEAKNESS của swarm; chỉ thêm `verify_facts()` trước `issue_refund`: đối chiếu `delay_days`, `status`, `damage_verified` với order có cấu trúc, lệch thì quote lại 1 vòng từ order và ghi event `verifier_override`. Đăng ký bằng `--extra-shape`, không sửa `lab8/shapes/__init__.py` hay file thước đo.
- **Case đối kháng:** `src/bonus/build_cases.py` sinh `src/bonus/cases.jsonl` và `src/bonus/world.json` gồm 12 claim: nói quá (C-B01, C-B09, C-B10), nói thiếu (C-B02), nói dối hỏng hàng (C-B03), nhiều con số (C-B04), injection + clause cũ (C-B05), đơn `in_transit` / `cancelled` (C-B06, C-B07), ship và damage cùng đủ (C-B08), sai chủ đơn (C-B11), thiếu mã đơn (C-B12). Nhãn viết tay theo `docs/business_rules.md`, không sinh bằng `compensation.quote`; mỗi claim có trường `why`.
- **Đếm can thiệp:** `src/bonus/verifier_report.py` đọc hai report benchmark và trace, ghi `src/reports/bonus_b3.json`.
- **Test đã thêm:** `src/tests/test_bonus_swarm_verified.py` (29 test): verifier sửa đúng C-002 seed 55 (20.000 → 0); không can thiệp khi dữ kiện khớp; 12 claim đối kháng × 5 seed pass cho workflow và swarm_verified; crash vẫn ném `InjectedCrash` và resume chỉ 1 refund; file case khớp với builder viết tay.
- **Commit bonus:** `f5adbd9` — `feat: Complete group report`, gồm toàn bộ `src/bonus/`, `src/tests/test_bonus_swarm_verified.py`, `src/reports/bonus_b3*.json`, `src/reports/hidden_selfcheck.json`, `report/team/bonus_report.md`, `report/team/group_report.md` và `TEAM.md`. Đây là commit chốt ghi trong ADR.

## 4. Bằng chứng

Mọi lệnh chạy trong `src/`.

| Kiểm tra                 | Lệnh                                                                                                                                                                                                                                            | Kết quả                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Benchmark public 4 shape | `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json`                                                                                     | workflow / single / orchestrator 1.000; swarm 0.986, pass^5 0.929               |
| Hidden self-check        | `python -m lab8.benchmark --shapes workflow,single,orchestrator --cases student_drop/hidden_claims.jsonl --world student_drop/hidden_world_state.json --out reports/hidden_selfcheck.json`                                                      | 600 trial, 0 `error`, 0 `leak_suspect`; 3 shape cùng status ở mọi (claim, seed) |
| Bonus B3 public          | `python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/bonus_b3_public.json`                        | swarm 0.986 → swarm_verified 1.000; cost/success 49.57 → 49.00                  |
| Bonus B3 đối kháng       | `python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --cases bonus/cases.jsonl --world bonus/world.json --seeds 11,22,33,44,55 --out reports/bonus_b3_adversarial.json` | swarm 0.933, pass^5 0.667 → swarm_verified 1.000, pass^5 1.000                  |
| Đếm can thiệp            | `python -m bonus.verifier_report`                                                                                                                                                                                                               | 8 lần can thiệp, 5 lần đổi số tiền, đúng 5 trial swarm gốc fail                 |
| Test bonus               | `python -m pytest -q tests/test_bonus_swarm_verified.py`                                                                                                                                                                                        | 29 passed                                                                       |
| Cổng host                | `python -m pytest -q`                                                                                                                                                                                                                           | 108 passed                                                                      |
| Điều kiện nộp            | `python -m lab8.check_submission`                                                                                                                                                                                                               | 0 FAIL                                                                          |

Run id dẫn chứng: `R-workflow-C-002-s55`, `R-swarm-C-002-s55`, `R-swarm_verified-C-002-s55`, `R-workflow-C-001-s11`, `R-orchestrator-C-001-s11`.

## 5. Công cụ AI đã dùng

- **Công cụ:** Claude Code.
- **Dùng vào việc gì:** đọc đề, rubric, contract và code host; chạy benchmark và hidden self-check; tóm tắt số liệu từ file report; soạn nháp ADR, research card; viết case đối kháng và test cho bonus B3.
- **Cách kiểm tra:**
  - Kiểm tra mọi số trong ADR, research card và bonus report lấy từ file JSON do `lab8.benchmark` / `bonus.verifier_report` sinh.
  - Chạy lại toàn bộ chuỗi lệnh tái lập của bonus từ đầu, số liệu không đổi; `pytest -q` xanh và `check_submission` 0 FAIL sau khi thêm bonus.
  - Đối chiếu nhãn của 12 claim đối kháng với từng dòng trong `docs/business_rules.md` (trường `why`), và kiểm tra workflow, vốn đúng luật trên bộ public, cũng pass toàn bộ 12 claim.
  - Kiểm tra lại điểm bất thường "single rẻ hơn workflow" bằng cách đọc code đếm tool của từng shape trước khi viết kết luận.

## 6. Tự đánh giá

**Phần làm tốt**

- Chọn shape bằng số đo trên cùng corpus, cùng seed, cùng giá; có run id và commit hash; nêu rõ chỗ số liệu chưa so ngang (cách đếm tool) thay vì kết luận vượt dữ liệu.
- Bonus B3 có đủ ba mức: chạy được (code + 29 test + lệnh tái lập), đo công bằng (cùng claim × seed, đủ pass rate, pass^5, variance, cost/success, safety counts từ file report), phân tích có giới hạn (CLAIM, BOUNDARY, ủng hộ một phần, điều kiện đảo ngược).

**Phần còn hạn chế**

- Hidden self-check không có nhãn nên không biết pass rate thật; gate bonus (hidden ≥ 0.80) chỉ grader của giảng viên xác nhận được.
- Case đối kháng do tôi tự viết và thiết kế quanh điểm yếu đã biết của swarm, nên có thiên kiến của người viết case.
- Không đo được latency và hệ số khuếch đại lỗi như nguồn, vì MockLLM chỉ có một điểm yếu tất định.

**Điều học được**

- Kiến trúc là giả thuyết, benchmark là bằng chứng: multi-agent không thắng trên task tuần tự mà chỉ tăng chi phí.
- Một verifier bằng code đặt ngay trước bước ghi tiền chặn được lỗi suy luận của model, nhưng khi verifier đã ghi đè mọi dữ kiện thì phần agent phía trước không còn đóng góp gì.
- So cost giữa các shape phải kiểm cách đếm trước khi kết luận.
