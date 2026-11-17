# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R1 · Scaling |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Google Research 2026, *Towards a Science of Scaling Agent Systems* (thư viện tham khảo slide 68–69; slide 15, 24, 33, 41 bài N8). Loại bằng chứng: benchmark có kiểm soát trên nhiều cấu hình agent |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Multi-agent chỉ có lợi khi task chia song song được; với task tuần tự, các biến thể multi-agent trong nghiên cứu giảm hiệu năng khoảng 39–70% so với single agent |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Đo trên LLM thật và các benchmark agent của nghiên cứu, nơi lỗi phối hợp giữa agent (mất ngữ cảnh, giao việc sai) làm giảm chất lượng. Không đo trên quy trình có tiền và approval do code quyết, không đo với MockLLM tất định |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Claims flow là chuỗi tuần tự (claim → order → quote → refund; quote phụ thuộc order). Đổi workflow (A) → orchestrator (C), tức thêm tầng investigator chỉ đọc: pass rate **không tăng** (giữ 1.000); cost/success **tăng ít nhất 40%** do thêm handoff, tool call của investigator và model call; không có lợi ích song song để bù |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Cố định: MockLLM, bộ tool `lab8.tools`, seed 11,22,33,44,55, corpus `data/public_claims.jsonl` (14 claim), `config/pricing.yaml`, evaluator `lab8.metrics.trial_pass`, SQLite mới cho mỗi trial, cùng lệnh `lab8.benchmark`. Biến duy nhất được thay đổi: topology, A `workflow` (một luồng code) so với C `orchestrator` (orchestrator + investigator chỉ đọc qua handoff allowlist) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: chi phí phối hợp không mang lại chất lượng (coordination overhead). Đo bằng cost/success và mean tool/model calls; kiểm thêm pass rate, pass^5, seed variance để chắc không có giảm chất lượng, và leak/bypass qua `trial_pass` để chắc handoff không làm lộ secret |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json` (chạy trong `src/`, commit `5e1d8bf`)
- Run id / file report: `src/reports/benchmark.json`, mục `by_shape.workflow` và `by_shape.orchestrator`; ví dụ cặp trial `R-workflow-C-001-s11` (4 tool, 0 model call, 40 VND) và `R-orchestrator-C-001-s11` (6 tool, 2 model call, 61.32 VND)
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Đúng.** Pass rate 1.000 → 1.000, pass^5 1.000 → 1.000, seed variance 0 → 0: không tăng chất lượng. Cost/success 34.29 → 56.87 VND (**+65.9%**); mean tool calls 3.43 → 5.57, mean model calls 0 → 1.79; tổng cost 70 trial 2400.0 → 3980.8 VND. Workflow có tính 10 VND cho lần gọi `issue_refund` còn orchestrator thì không, nên nếu đếm cùng luật thì chênh lệch còn lớn hơn (≈ 27.86 → 56.87, khoảng gấp đôi). Phần paper nói về **giảm** chất lượng 39–70% thì **không tái hiện**: orchestrator không mất điểm vì tiền, approval và ghi ledger do code quyết, investigator tất định và chỉ đọc. Kết luận không vượt dữ liệu: trên task tuần tự này, thêm agent chỉ tăng chi phí, không tăng hay giảm pass rate
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`. Vì latency không đo, không kiểm được phần "song song giảm critical path" của nguồn. Corpus public chỉ 14 claim; với LLM thật, lỗi phối hợp giữa orchestrator và investigator có thể làm pass rate giảm như paper mô tả. Kết luận sẽ đảo nếu có các bước tra cứu độc lập chạy song song được với latency thật (xem bonus B1).

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
