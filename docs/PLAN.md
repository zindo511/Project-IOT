# PLAN — MVP đến 07/11/2026

## Ownership

| Mảng | Owner | Reviewer bắt buộc |
|---|---|---|
| Backend, dashboard, policy, tích hợp | PM/Backend | AI hoặc Firmware theo interface |
| Vision, tracking, enrollment, calibration | AI/Data | PM/Backend |
| Simulator, firmware, phần cứng, HIL | Firmware/Hardware | PM/Backend |
| Dataset và nghiệm thu | Cả nhóm | Người không viết chức năng |

## Backlog

| ID | Công việc | Owner | Phụ thuộc | Definition of Done | Trạng thái |
|---|---|---|---|---|---|
| PM-01 | Khóa SPEC/CONTRACTS/config | PM | — | Ba thành viên review | READY |
| BE-01 | FastAPI + SQLite + dashboard base | PM | PM-01 | Chạy được bằng simulator | DONE-BASE |
| BE-02 | State/mode/event/command policy | PM | BE-01 | Policy tests pass | DONE-BASE |
| FW-01 | Simulator theo contract | Firmware | PM-01 | Chạy 4 scenario | DONE-BASE |
| FW-02 | Camera bring-up và JPEG upload | Firmware | Có board | Soak 30 phút | BLOCKED-HARDWARE |
| FW-03 | PIR + buzzer fail-safe + ACK | Firmware | FW-02 | Reset/mất Wi-Fi còi OFF | BLOCKED-HARDWARE |
| AI-01 | Khóa model artifact và manifest/hash | AI | — | Model load test | TODO |
| AI-02 | Person/face detection + quality | AI | AI-01 | Output observation fixture | TODO |
| AI-03 | Tracking + A/B + direction | AI | AI-02 | Scenario video tests | TODO |
| AI-04 | SFace gallery + 2-pass enrollment | AI | AI-02 | 3–5 active identities | TODO |
| AI-05 | Threshold calibration | AI | AI-04 | Báo cáo FAR/FRR holdout | TODO |
| INT-01 | Ghép board → AI → policy → buzzer | Cả nhóm | FW-03, AI-04 | 8 scenario pass | TODO |
| QA-01 | Soak, lỗi mạng/restart/storage | Cả nhóm | INT-01 | Không alarm sai do fault | TODO |
| DOC-01 | Hướng dẫn lắp, vận hành, demo | Cả nhóm | INT-01 | Người thứ hai chạy lại được | TODO |

## Mốc

- **03–06/10:** khóa contract, repo, simulator, đặt phần cứng.
- **07–13/10:** vertical slice giả chạy xuyên suốt.
- **14–20/10:** AI nền và board thật.
- **21–27/10:** tích hợp, vùng A/B và calibration.
- **28/10–03/11:** nghiệm thu, soak, video dự phòng.
- **04–07/11:** buffer, báo cáo; không thêm tính năng.

## Quy trình issue/PR

Mỗi issue ghi rõ input, output, contract liên quan, test và reviewer. PR nhỏ, không giữ nhánh cá nhân dài. Nếu một thay đổi đụng cả producer và consumer, dùng fixture chung và merge theo thứ tự đã ghi trong issue.

