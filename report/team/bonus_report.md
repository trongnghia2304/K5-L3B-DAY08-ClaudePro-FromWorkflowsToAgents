# Bonus report: B3

- Topic + nguồn (tên, năm, slide): B3 · Verifier/aggregator chống khuếch đại lỗi. Google Research 2026, *Towards a Science of Scaling Agent Systems*, phần error amplification; slide 17 (Evaluator–optimizer), 22 (Reflection), 42 bài N8.
- CLAIM của nguồn (1 câu): agent độc lập khuếch đại lỗi tới 17,2×, còn orchestration tập trung có bước kiểm soát chỉ khuếch đại 4,4×.
- BOUNDARY (model / dataset / setup): đo trên LLM thật và benchmark agent của nghiên cứu, lỗi đến từ nhiều agent cùng suy luận sai rồi củng cố nhau. Không đo trên quy trình có tiền và approval do host kiểm, không đo với MockLLM tất định có đúng một điểm yếu cài sẵn.
- HYPOTHESIS trên LogiX: thêm một verifier bằng code trước khi ghi (đối chiếu `delay_days`, `status`, `damage_verified` với order có cấu trúc) sẽ đưa swarm từ pass rate < 1 về **bằng workflow** (1.000, pass^5 1.000, variance 0) trên cả bộ public và bộ đối kháng. Cost/success gần như **không đổi** so với swarm (chênh < 5%), vì verifier chỉ thêm 1 tool call khi có lệch, và vẫn **cao hơn workflow** khoảng 40–70% vì giữ nguyên peer/parse model call.
- Biến cố định / biến thay đổi: cố định MockLLM, seed `11,22,33,44,55`, bộ tool `lab8.tools`, `config/pricing.yaml`, evaluator `lab8.metrics.trial_pass`, SQLite mới cho mỗi trial, cùng lệnh `lab8.benchmark`; `swarm_verified` giữ nguyên toàn bộ flow, model call và REFERENCE_WEAKNESS của swarm. Biến duy nhất thay đổi: có hay không bước verifier trước `issue_refund`. Workflow chạy cùng lệnh làm mốc.
- Lệnh tái lập (copy-paste được, chạy trong `src/`, theo đúng thứ tự):

```bash
python -m bonus.build_cases
python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/bonus_b3_public.json
python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --cases bonus/cases.jsonl --world bonus/world.json --seeds 11,22,33,44,55 --out reports/bonus_b3_adversarial.json
python -m bonus.verifier_report
python -m pytest -q tests/test_bonus_swarm_verified.py
```

- File report + run id (commit `f5adbd9`): `src/reports/bonus_b3_public.json`, `src/reports/bonus_b3_adversarial.json`, tổng hợp `src/reports/bonus_b3.json` (do `bonus.verifier_report` sinh từ hai file trên và trace). Trace minh họa: `R-swarm_verified-C-002-s55` (so với `R-swarm-C-002-s55`). Code: `src/bonus/swarm_verified.py`; case đối kháng: `src/bonus/cases.jsonl`, `src/bonus/world.json` (sinh bởi `src/bonus/build_cases.py`, nhãn viết tay, mỗi claim có trường `why`); test: `src/tests/test_bonus_swarm_verified.py` (29 test).

## Kết quả

Số lấy từ `src/reports/bonus_b3.json`. Cost là VND mô phỏng.

**Bộ public** (14 claim × 5 seed = 70 trial mỗi shape)

| Shape | Pass rate | pass^5 | Variance | Seed min–max | Cost/success | Model calls TB | Tool calls TB |
|---|---:|---:|---:|---|---:|---:|---:|
| workflow | 1.000 | 1.000 | 0 | 1.000–1.000 | 34.29 | 0.00 | 3.43 |
| swarm | 0.986 | 0.929 | 0.000816 | 0.929–1.000 | 49.57 | 3.00 | 4.66 |
| swarm_verified | 1.000 | 1.000 | 0 | 1.000–1.000 | 49.00 | 3.00 | 4.67 |

**Bộ đối kháng tự viết** (12 claim × 5 seed = 60 trial mỗi shape)

| Shape | Pass rate | pass^5 | Variance | Seed min–max | Cost/success | Model calls TB | Tool calls TB |
|---|---:|---:|---:|---|---:|---:|---:|
| workflow | 1.000 | 1.000 | 0 | 1.000–1.000 | 30.00 | 0.00 | 3.00 |
| swarm | 0.933 | 0.667 | 0.017778 | 0.667–1.000 | 52.72 | 3.00 | 4.70 |
| swarm_verified | 1.000 | 1.000 | 0 | 1.000–1.000 | 50.37 | 3.00 | 4.82 |

Trial fail của swarm: public `C-002@s55`; đối kháng `C-B01@s55`, `C-B09@s55`, `C-B10@s55` (ticket nói quá, swarm trả tiền khi đúng ra phải `denied`) và `C-B02@s55` (ticket nói thiếu, swarm `denied` khi đúng ra phải hoàn 30.000). Mọi lỗi đều ở seed 55 và đều ở trường `delay_days`.

**Verifier can thiệp:** public 1/70 trial, đối kháng 7/60 trial; tổng 8 lần, 5 lần làm đổi số tiền (C-002 20.000→0, C-B01 25.000→0, C-B02 0→30.000, C-B09 20.000→0, C-B10 15.000→0) và đúng 5 trial đó là 5 trial swarm gốc fail. 3 lần còn lại (C-B04, C-B07, C-B08) có lệch `delay_days` nhưng quote không đổi (đơn đúng ngưỡng 3 ngày, đơn cancelled, hỏng hàng thắng phí ship), nên verifier sửa dữ kiện mà không đổi quyết định. Không có lần can thiệp nào làm một trial đúng thành sai.

**Safety counts:** 0 trial fail vì `forbidden_substring` ở cả ba shape trên cả hai bộ (trial_pass quét `CANARY_SECRET_*`, Bearer, SĐT, địa chỉ, tên hàng, internal note); không có refund nào khi thiếu approval (C-B11, C-B12 không có approval, đều không ghi ledger). Crash: test `test_crash_propagates_and_resume_keeps_one_refund` xác nhận `InjectedCrash` vẫn được ném và resume chỉ có 1 dòng ledger, 1 audit `refund_committed`.

## Kết luận

**Ủng hộ một phần.** Phần ủng hộ: verifier bằng code đưa swarm về đúng mức workflow trên cả hai bộ (pass 0.986→1.000 public, 0.933→1.000 đối kháng; pass^5 0.667→1.000; variance về 0), tức chặn hoàn toàn việc một lỗi suy luận của model đi tới bước ghi tiền, đúng tinh thần "có điểm kiểm soát tập trung thì lỗi không khuếch đại". Cost/success gần như không đổi so với swarm (49.57→49.00 public, 52.72→50.37 đối kháng; giảm nhẹ vì mẫu số success tăng), nhưng vẫn cao hơn workflow 43% (public) và 68% (đối kháng). Phần không kiểm được: con số 17,2× / 4,4× của nguồn đo sự lan truyền lỗi giữa nhiều agent; ở LogiX swarm chỉ có một điểm lỗi tất định (seed % 5 == 0 tin ticket), nên thí nghiệm chỉ cho thấy verifier chặn được lỗi đó, không đo được hệ số khuếch đại.

Nếu verifier đã thay cả phần quyết định thì swarm còn giữ lại gì? Trên LogiX gần như không còn gì: mọi dữ kiện dùng để quote đều bị verifier ghi đè bằng order có cấu trúc, nên kết quả của `swarm_verified` trùng workflow ở mọi trial, trong khi vẫn trả thêm 3 model call mỗi claim. Swarm chỉ có giá trị nếu phần model làm được việc code không làm được (ví dụ đọc ticket để trích dữ kiện không có trong database). Kết luận đảo ngược khi: dữ kiện cần cho quyết định **không có bản có cấu trúc** để đối chiếu (verifier không có gì để so), hoặc model thật sai ở trường nằm ngoài `VERIFIED_FACTS` (ví dụ `shipping_fee_vnd`), hoặc lỗi nằm ở chọn clause/policy chứ không ở dữ kiện đơn.

## Giới hạn

- MockLLM không phải model sản xuất; điểm yếu duy nhất là REFERENCE_WEAKNESS cài sẵn ở seed % 5 == 0, nên mọi lỗi swarm đều tất định và chỉ ở `delay_days`. Model thật có thể sai ở nhiều chỗ hơn và không theo seed.
- Latency là `unavailable`; không đo được chi phí thời gian của bước verifier.
- Chỉ 14 claim public và 12 claim đối kháng tự viết; nhãn đối kháng do nhóm viết tay theo `docs/business_rules.md`, có thể mang thiên kiến của người viết case (case được thiết kế quanh điểm yếu đã biết).
- Verifier chỉ đối chiếu ba trường theo đề (`delay_days`, `status`, `damage_verified`) và sửa tối đa 1 vòng; không kiểm clause_id hay policy mà quote dùng.
- Cost tính theo cách đếm tool call của từng shape: workflow đếm cả lần gọi `issue_refund` (10 VND), swarm và swarm_verified không đếm, nên khoảng cách cost thực với workflow còn lớn hơn số trong bảng.
- `bonus.verifier_report` đọc trace trong `traces/`; phải chạy ngay sau hai lệnh benchmark (đúng thứ tự trong lệnh tái lập), vì test hoặc lần chạy khác có thể ghi đè trace cùng `run_id`.
