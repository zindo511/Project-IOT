# Smart Security MVP

Code base chung cho demo giám sát một lối tiếp cận cửa:

```text
ESP32-CAM -> FastAPI -> Vision/Tracking -> Policy -> SQLite -> Dashboard -> Buzzer
```

Repository này cố ý bắt đầu bằng một **vertical slice có simulator**. AI thật và board thật được gắn vào các contract đã khóa, thay vì mỗi thành viên tự tạo format riêng.

## Phạm vi hiện tại

- FastAPI khởi động ở trạng thái `DISARMED`.
- Nhận frame JPEG từ thiết bị và lưu ảnh mới nhất trong `runtime/`.
- Nhận observation từ vision worker theo schema chung.
- Policy mẫu phân biệt `INFO`, `WARNING`, `ALARM`, chống tạo event lặp trên cùng track.
- SQLite lưu event, trạng thái đã xem và lệnh buzzer.
- Dashboard tối giản để arm/disarm, xem sự kiện và silence.
- Simulator chạy các kịch bản `known`, `unknown`, `direct-b`, `outgoing`.
- Firmware PlatformIO có sẵn cấu trúc và giao thức để thành viên phần cứng tiếp tục.

AI thật (NanoDet/YuNet/SFace), enrollment embedding và hiệu chỉnh threshold là backlog có owner rõ trong [PLAN](docs/PLAN.md), chưa được coi là hoàn tất. Công việc và nhánh cụ thể của từng thành viên trong tuần đầu nằm tại [WEEK-01-ASSIGNMENTS](docs/WEEK-01-ASSIGNMENTS.md).

## Chạy trên Windows

Yêu cầu Python 3.11–3.13 (khuyến nghị 3.11/3.12 để đồng nhất máy nhóm).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn smart_security.app:app --reload
```

Mở <http://127.0.0.1:8000>. Ở terminal khác:

```powershell
.\.venv\Scripts\Activate.ps1
python simulator/device_simulator.py --scenario unknown
```

Chạy kiểm thử:

```powershell
python -m pytest
```

## Cấu trúc

```text
config/       Cấu hình duy nhất cho vùng, policy, vision và buzzer
docs/         SPEC, CONTRACTS và PLAN dùng chung
firmware/     PlatformIO base cho ESP32-CAM
simulator/    Thiết bị + vision giả để tích hợp khi chưa có board/model
src/          FastAPI, schema, database và policy
tests/        Contract/policy/API tests
```

## Quy tắc làm việc

1. Đọc `docs/SPEC.md` và phần liên quan trong `docs/CONTRACTS.md` trước khi code.
2. Không đổi JSON/API một phía. Contract change phải sửa fixture, producer, consumer và test trong cùng PR hoặc chuỗi PR có thứ tự.
3. Mọi threshold nằm trong `config/default.yaml`, không hard-code rải rác.
4. Không commit secret, ảnh enrollment, embedding thật hay model ONNX.
5. `main` phải luôn chạy được với simulator.
