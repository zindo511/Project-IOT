# Phân công tuần 1 — Smart Security MVP

**Thời gian:** 04/10/2026–10/10/2026  
**Mục tiêu tuần:** chạy ổn định một vertical slice bằng simulator:

```text
Simulator gửi JPEG
→ Backend nhận frame
→ Vision stub trả Observation
→ Policy tạo Event
→ Dashboard hiển thị
→ Simulator nhận và ACK BuzzerCommand
```

AI thật và ESP32-CAM thật **không phải điều kiện hoàn thành tuần 1**. Tuần này tập trung khóa contract, điểm ghép và quy trình làm việc.

## 1. Quy tắc làm việc chung

Trước khi bắt đầu một task:

```powershell
git switch main
git pull --ff-only origin main
git switch -c <ten-nhanh>
```

Khi hoàn thành:

```powershell
git status
git diff
python -m pytest
git add <cac-file-lien-quan>
git commit -m "<type>: <mo-ta-ngan>"
git push -u origin <ten-nhanh>
```

- Không làm trực tiếp trên `main`.
- Mỗi nhánh chỉ xử lý một issue và nên được merge trong 0,5–2 ngày.
- Mỗi PR cần ít nhất một approval và test/log chứng minh.
- Tác giả được bấm merge sau khi người khác approve và toàn bộ comment đã resolve.
- Không tự ý thay đổi `schemas.py`, `config/default.yaml` hoặc `CONTRACTS.md`. Mọi thay đổi contract phải được PM chốt và merge trước implementation.
- Sau khi PR merge, xóa nhánh và tạo nhánh mới từ `main` mới nhất.

## 2. Ranh giới ownership

| Khu vực | Owner | Reviewer chính |
|---|---|---|
| `app.py`, `database.py`, `policy.py`, `web/`, API tests | PM/Backend | AI khi liên quan Observation; Firmware khi liên quan Command |
| `src/smart_security/vision/`, vision tests, model manifest | AI/Data | PM/Backend |
| `firmware/`, `simulator/`, simulator tests, BOM/wiring | Firmware/Hardware | PM/Backend |
| `schemas.py`, `default.yaml`, `CONTRACTS.md` | PM quản lý | Cả AI và Firmware khi contract liên quan |

AI sở hữu và định nghĩa `VisionService`; Backend chỉ gọi interface đó. Firmware không gọi AI hoặc database trực tiếp. Backend là điểm điều phối duy nhất.

## 3. Thành viên 1 — PM kiêm Backend/Dashboard

### Trách nhiệm tuần

- Quản lý GitHub Issues/PR và branch protection.
- Bổ sung CI chạy test cho mỗi PR.
- Hoàn thiện event/evidence, command status và dashboard nền.
- Tích hợp `VisionService` sau khi PR interface của AI đã merge.
- Điều phối buổi demo nội bộ cuối tuần.

### Các nhánh và PR

#### `chore/pm-01-ci`

- Tạo GitHub Actions chạy `python -m pytest`.
- Dùng Python 3.11 hoặc 3.12.
- Job phải có tên ổn định `tests` để chọn làm required status check.
- Cập nhật README nếu lệnh CI khác lệnh local.

**DoD:** Workflow chạy xanh trên PR và status check `tests` xuất hiện trong GitHub.

#### `feature/be-01-event-evidence`

- Khi policy tạo event, sao chép frame liên quan sang `runtime/evidence/`.
- Lưu `evidence_path` vào SQLite.
- Nếu ghi evidence lỗi nhưng DB còn hoạt động, vẫn lưu event và thể hiện evidence bị thiếu.
- Bổ sung API/test lấy ảnh evidence an toàn.

**DoD:** Event trả đúng evidence; test bao phủ trường hợp có và thiếu ảnh.

#### `feature/be-02-command-dashboard`

- Dashboard hiển thị trạng thái command: `PENDING`, `ACKED`, `REJECTED_EXPIRED`, `FAILED`.
- Giữ acknowledge event khác với silence còi.
- Kiểm tra `DISARMED` phát STOP và reset policy.
- Bổ sung API integration test: unknown A→B sinh đúng một START.

**DoD:** Dashboard xem được event/command và các scenario không tạo command lặp.

#### `feature/be-03-vision-hook`

Chỉ tạo nhánh này **sau khi** `feature/ai-01-vision-interface` đã merge.

- Backend gọi `VisionService.analyze(...)` sau khi nhận frame.
- Vision exception tạo `VISION_FAILURE`, không được biến thành `UNKNOWN`.
- Cho phép chọn `stub` hoặc implementation thật bằng config.
- Không đặt logic detect/recognize trong `app.py`.

**DoD:** Upload một frame qua simulator có thể đi xuyên Vision stub → Policy → Event.

### Không thuộc tuần 1

- Hoàn thiện enrollment và gallery thật.
- Authentication người dùng đầy đủ.
- Telegram hoặc triển khai Internet.

## 4. Thành viên 2 — AI/Data

### Trách nhiệm tuần

- Tạo interface vision duy nhất cho backend sử dụng.
- Tạo stub có hành vi xác định để integration không phụ thuộc model.
- Chuẩn hóa zone và face quality.
- Chuẩn bị manifest cho NanoDet, YuNet và SFace.

### Các nhánh và PR

#### `feature/ai-01-vision-interface`

Tạo cấu trúc:

```text
src/smart_security/vision/
├── __init__.py
├── service.py
├── stub.py
└── types.py
```

Interface bắt buộc:

```python
def analyze(
    image_bytes: bytes,
    device_id: str,
    frame_id: str,
    captured_at: datetime,
) -> list[Observation]:
    ...
```

- Stub trả output theo các fixture `known`, `unknown`, `direct-b`, `outgoing` và `low-quality`.
- Output chỉ dùng enum/schema đang có.
- Vision không tạo Event hoặc BuzzerCommand.

**DoD:** Contract tests chứng minh mọi output validate được bằng Pydantic `Observation`.

#### `feature/ai-02-zone-quality`

- Decode JPEG bằng OpenCV trong implementation riêng; model thiếu phải báo lỗi rõ.
- Chuẩn hóa bbox và tọa độ về `[0.0, 1.0]`.
- Xác định tâm bbox thuộc `OUTSIDE`, `A` hoặc `B`.
- Kiểm tra polygon A/B hợp lệ và không chồng lấn.
- Face quality thấp phải trả `UNCERTAIN`, không trả `UNKNOWN`.

**DoD:** Có unit test cho biên vùng, ngoài vùng và quality dưới/trên threshold.

#### `chore/ai-03-model-manifest`

- Ghi rõ tên, nguồn, version, SHA-256 và input/output của ba model.
- Model ONNX không commit vào Git.
- Viết load/smoke test; nếu artifact chưa có thì test skip với lý do rõ.
- Không chốt threshold nhận diện bằng suy đoán trong tuần này.

**DoD:** Người khác đọc manifest có thể tải đúng artifact và biết cách kiểm hash.

### Không thuộc tuần 1

- Calibration threshold bằng dữ liệu người thật.
- Gallery 3–5 người và enrollment hai lượt hoàn chỉnh.
- Tracking đa người hoặc tối ưu accuracy.

## 5. Thành viên 3 — Firmware/Hardware

### Trách nhiệm tuần

- Biến simulator thành thiết bị chuẩn dùng cho integration.
- Hoàn thiện semantics generation, expiry và ACK.
- Chuẩn bị PlatformIO, BOM và sơ đồ dây cho tuần có board.

### Các nhánh và PR

#### `feature/fw-01-simulator-command`

- Simulator gửi đúng multipart frame contract.
- Nhận server URL, device ID và token từ argument/environment.
- Poll command bằng `after_generation`.
- Không thực thi lại generation cũ.
- Kiểm tra `expires_at` trước khi giả lập bật còi.
- Gửi `ACKED` hoặc `REJECTED_EXPIRED` đúng trường hợp.

**DoD:** Unknown scenario nhận đúng một START; command hết hạn không được thực thi.

#### `feature/fw-02-fault-scenarios`

Bổ sung khả năng mô phỏng:

- Camera offline.
- Gửi trùng `frame_id`.
- ACK chậm hoặc không ACK.
- Mất kết nối server.
- PIR HIGH/LOW.

Các chế độ lỗi phải bật bằng argument, không sửa code cho từng lần demo.

**DoD:** Backend có thể dùng simulator để kiểm thử ít nhất bốn fault scenario lặp lại được.

#### `docs/fw-03-bom-wiring`

- Chốt BOM, số lượng, giá dự kiến và link tham khảo nội bộ.
- Vẽ bảng đấu dây dự kiến GPIO13/GPIO14 và GND chung.
- Ghi checklist camera → PIR → buzzer.
- Cài PlatformIO và build skeleton firmware.
- Nếu chưa build được, ghi log/blocker cụ thể; không báo DONE chung chung.

**DoD:** BOM được PM duyệt và firmware compile hoặc có blocker có thể hành động.

### Không thuộc tuần 1

- Kiểm thử board thật khi linh kiện chưa về.
- Tinh chỉnh chất lượng ảnh ngoài trời/ban đêm.
- Điều khiển khóa cửa hoặc thiết bị công suất.

## 6. Lịch phối hợp từng ngày

| Ngày | PM/Backend | AI/Data | Firmware/Hardware | Điểm kiểm tra chung |
|---|---|---|---|---|
| 04/10 | Tạo issue, protection, xác nhận baseline | Chạy baseline, đọc schema | Chạy simulator, đọc command contract | 7 test pass trên cả ba máy |
| 05/10 | PR CI | Bắt đầu AI-01 | Bắt đầu FW-01 | Không đổi contract ngoài PR |
| 06/10 | BE-01 | Mở PR AI-01 | Mở PR FW-01 | Review chéo trong ngày |
| 07/10 | Merge AI-01, bắt đầu BE-03 | Bắt đầu AI-02 | Bắt đầu FW-02 | Upload frame đi qua vision stub |
| 08/10 | BE-02/BE-03 | Test zone/quality | Fault scenarios | Chạy known/unknown/direct-B/outgoing |
| 09/10 | Integration tests và dashboard | Review backend semantics | Build firmware/BOM | Toàn bộ PR nhỏ đã merge hoặc có blocker |
| 10/10 | Điều phối demo | Chạy test và giải thích output | Chạy simulator/command ACK | Tag bản tuần `v0.1-week1` nếu pass |

## 7. Thứ tự merge

```text
PM-01 CI
   ↓
AI-01 Vision interface       FW-01 Simulator command       BE-01 Evidence
   ↓                              ↓                            ↓
AI-02 Zone/quality           FW-02 Fault scenarios          BE-02 Dashboard
   └──────────────────────┬───────┴────────────────────────────┘
                          ↓
                 BE-03 Vision integration
                          ↓
                 Integration/fix PR nhỏ
```

Các PR trên cùng hàng có thể làm song song. PR `BE-03` phải chờ `AI-01` để tránh Backend và AI cùng tạo interface.

## 8. Kịch bản nghiệm thu ngày 10/10

1. Server khởi động ở `DISARMED`.
2. Gửi frame khi disarmed không tạo alarm.
3. Chuyển `ARMED`.
4. `known`: tạo một INFO, không có START.
5. `unknown`: tạo một ALARM và đúng một START 2000 ms.
6. `direct-b`: WARNING, không START.
7. `outgoing`: không START.
8. `low-quality`: WARNING/UNCERTAIN, không START.
9. Silence tạo STOP generation mới hơn.
10. Simulator ACK và dashboard hiển thị trạng thái.
11. Restart server trở về `DISARMED`.
12. Toàn bộ test và required status check `tests` đều xanh.

## 9. Mẫu cập nhật hằng ngày

Mỗi người cập nhật trong issue trước khi kết thúc ngày:

```text
Đã làm:
Đang làm:
Blocker:
PR/commit:
Test hoặc log chứng minh:
Có đề xuất đổi contract không:
```

Nếu blocker ảnh hưởng contract hoặc ngăn integration quá nửa ngày, báo ngay trong ngày; không chờ họp cuối tuần.

