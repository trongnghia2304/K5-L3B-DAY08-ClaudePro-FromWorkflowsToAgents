# Team

## Thông tin nhóm

- Tên nhóm: ClaudePro
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY08-ClaudePro-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/trongnghia2304/K5-L3B-DAY08-ClaudePro-FromWorkflowsToAgents, nhánh `main`, commit chốt (trùng `report/team/decision_adr.md`): `f5adbd9`

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Nguyễn Đức Minh | 2A202603765 | 26ai.minhnd5@vinuni.edu.vn | miao1114 | Workflow (Shape A) |
|   2 | Nguyễn Quang Huy | 2A202603768 | 26ai.huynq13@vinuni.edu.vn | nguyenquanghuy091204 | Single agent (Shape B) |
|   3 | Nguyễn Nghiêm Khánh Tiệp | 2A202603863 | tiepnnk04@gmail.com | tiepnnk01-10 | Orchestrator (Shape C) + handoff |
|   4 | Tăng Nguyễn Hải Đăng | 2A202603916 | haidangg.work@gmail.com | haidangwork1411 | Safety & Testing, tích hợp |
|   5 | Nguyễn Trọng Nghĩa | 2A202603835 | nghiatrongnguyen2304@gmail.com | trongnghia2304 | Evaluation (CP5), ADR, research card, bonus B3 |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Đức Minh | Workflow (`src/lab8/shapes/workflow.py`) | `5cbc99e`, `3ea6a00` | `src/tests/test_workflow.py` (3 test, marker `student`); 62 student test workflow xanh |
| Nguyễn Quang Huy | Single agent (`src/lab8/shapes/single.py`) | `069a071`, `cabceb8` | `src/tests/test_single.py` (8 test); 62 student test single xanh |
| Nguyễn Nghiêm Khánh Tiệp | Orchestrator (`src/lab8/shapes/orchestrator.py`) | `906e466` | `src/tests/test_orchestrator_own.py` (16 test); 62 student test orchestrator xanh |
| Tăng Nguyễn Hải Đăng | Safety & Testing | `733745d` | `src/tests/test_safety_approval_invariant.py` (1 test); invariant duyệt refund host, tích hợp test ma trận & crash suite |
| Nguyễn Trọng Nghĩa | Evaluation CP5 + bonus B3 (`src/bonus/`) | `5e1d8bf`, `e492c52`, `f5adbd9` | `src/tests/test_bonus_swarm_verified.py` (29 test); benchmark, hidden self-check, ADR, research card, bonus report |
