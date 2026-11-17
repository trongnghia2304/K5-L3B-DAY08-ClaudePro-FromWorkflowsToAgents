# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: f5adbd9
- Run id dẫn chứng: R-workflow-C-002-s55 (workflow denied đúng nơi swarm fail ở R-swarm-C-002-s55), R-workflow-C-014-s11 (T14 chỉ hoàn phần chênh lệch); nguồn src/reports/benchmark.json
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000000 (70 trial = 14 claim × seed 11,22,33,44,55)
- Cost per success (mô phỏng, VND): 34.29 (0 model call, 3.43 tool call/trial; gồm 10 VND đếm cho lần gọi issue_refund mà single/orchestrator/swarm không đếm, bỏ phần này còn ≈ 27.86)
- Crash safety: 20/20 (src/reports/crash.json)
- Secret leak / approval bypass: 0 / 0 trên 70 trial public (trial_pass quét forbid_substrings và approval; mọi trial ok); hidden do giảng viên chấm

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

Trên cùng corpus (14 claim public), cùng 5 seed `11,22,33,44,55`, cùng bảng giá mô phỏng và cùng evaluator (`src/reports/benchmark.json`), ba shape nhóm viết đều đạt pass rate 1.000, pass^5 1.000, variance 0; swarm đạt 0.986, pass^5 0.929, variance 0.000816 vì fail C-002 ở seed 55 (tin số ngày trễ trong ticket thay vì dòng order). Khi chất lượng ngang nhau, nhóm chọn shape **ít tự chủ nhất**: workflow không gọi model lần nào (mean_model_calls = 0), mọi quyết định về tiền, approval và ghi ledger nằm trong code, nên không có đường nào để chữ trong ticket ảnh hưởng tới số tiền. Về cost, workflow (34.29 VND/success) đắt hơn single (29.72) nhưng rẻ hơn orchestrator (56.87) và swarm (49.57). Khoảng chênh với single là do cách đếm, không do kiến trúc: workflow cộng 10 VND tool cost cho lần gọi `issue_refund` của host, ba shape còn lại không cộng. Bỏ khoản này (9/14 claim có gọi host) thì workflow còn ≈ 27.86 VND/success, rẻ nhất trong bốn shape.

## Có đáng đổi lấy multi-agent không

Không. Trên bộ public, orchestrator và swarm không pass cao hơn workflow, mà cost/success cao hơn 1.4–1.7 lần; swarm còn có variance theo seed. Single và orchestrator chỉ đạt 1.000 vì `decide` và investigator được viết để làm đúng các bước workflow, tức là phần "agent" không thêm năng lực, chỉ thêm model call và bề mặt rủi ro (prompt injection qua ticket, handoff lộ secret). Quyết định sẽ đảo lại nếu: (1) claim cần đọc hiểu chữ tự do mà rule cố định không xử lý được (ví dụ ticket không có order_id nhưng mô tả đủ để tra đơn), khi đó workflow sẽ `needs_info` quá nhiều và single có thể pass cao hơn; (2) có nhiều nguồn dữ liệu độc lập cần tra song song với latency thật, khi đó orchestrator có lợi về critical path; (3) hidden set có pass rate workflow < 0.75 trong khi shape khác vượt ngưỡng với cùng safety counts bằng 0.

## Trace và bằng chứng

Trace workflow (`src/traces/<run_id>.json`, đúng Trace contract v1, mọi nhánh return đi qua `finish()`) ghi các event: `get_claim_view` (chỉ `found`), `lookup_order` (kết quả đã qua allowlist `ORDER_FIELDS`: order_id, status, delay_days, shipping_fee_vnd, paid_vnd, damage_verified, carrier; hoặc `visible=false` + reason), `quote` (amount_vnd, reason, clause_ids, parts), `issue_refund` (proposal_amount), `refund_outcome` (ok, reason, conflict) và `decision` (status, reason). Trace được ghi xuống đĩa ngay trước khi gọi host để vẫn còn dấu vết khi crash thử nghiệm. Cố ý **không** ghi: ticket (dữ liệu người dùng, có thể chứa lệnh injection), claim row thô (có `parent_secret`, `raw_headers`), order row thô (có SĐT, địa chỉ, tên hàng, ghi chú nội bộ), principal_id và approval_id. Bằng chứng không lộ: `trial_pass` quét trace_path và mọi file `<run_id>*` theo `forbid_substrings` của từng claim, cả 70 trial workflow đều `ok`; test riêng của nhóm kiểm lại trace của các claim public không có `CANARY_SECRET_` hay PII. Shape không ghi file nào ngoài thư mục trace và không in ra stdout, nên không có log nằm ngoài vùng scanner quét.

## Giới hạn

Commit chấm là `f5adbd9` (có đủ ba shape, `src/bonus/` và mọi report). `src/reports/benchmark.json` được sinh ở `5e1d8bf`; từ `5e1d8bf` đến `f5adbd9` không có thay đổi nào trong `src/lab8/`, `src/config/` hay `src/data/`, nên chạy lại benchmark ở `f5adbd9` ra cùng số liệu. MockLLM không phải model sản xuất: cost là VND mô phỏng theo `config/pricing.yaml`, không phải hoá đơn API, và kết quả của single/orchestrator/swarm không cho biết model thật sẽ hành xử thế nào. Latency để `unavailable`. Corpus public chỉ 14 claim nên pass rate 1.000 chưa chứng minh kết quả hidden (40 claim × 5 seed); số hidden do giảng viên chạy. Cách đếm tool call cho lần gọi host chưa thống nhất giữa các shape (xem dòng Cost per success). Không sửa JSON cho đủ 0.75: mọi số ở trên lấy nguyên từ `src/reports/benchmark.json` và `src/reports/crash.json` do công cụ sinh ra.
