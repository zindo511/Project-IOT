# CONTRACTS — Smart Security MVP

**Version API:** `v1`  
Mọi timestamp dùng ISO-8601 UTC. Enum viết hoa đúng như tài liệu. Field mới phải optional để giữ tương thích trong v1.

## 1. Device → Server: frame

`POST /api/v1/devices/{device_id}/frames` — `multipart/form-data`

| Field | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---:|---|
| `frame` | JPEG | Có | Ảnh mới nhất, không retry ảnh cũ vô hạn |
| `frame_id` | string | Có | ID tăng đơn điệu hoặc UUID |
| `captured_at` | datetime | Có | Thời điểm camera chụp |
| `pir_active` | boolean | Có | PIR chỉ là metadata tăng FPS |

Header tùy cấu hình: `X-Device-Token`.

Response:

```json
{"accepted": true, "frame_id": "42", "system_mode": "ARMED"}
```

## 2. Vision → Policy: observation

`POST /api/v1/observations`

```json
{
  "device_id": "door-01",
  "frame_id": "42",
  "captured_at": "2026-10-03T08:00:00Z",
  "track_id": "track-7",
  "zone": "B",
  "direction": "INCOMING",
  "face_quality": 0.84,
  "identity": "UNKNOWN",
  "person_id": null,
  "match_score": 0.22
}
```

Enums:

- `zone`: `OUTSIDE | A | B`
- `direction`: `UNKNOWN | INCOMING | OUTGOING`
- `identity`: `NOT_EVALUATED | KNOWN | UNKNOWN | UNCERTAIN`

Vision mô tả quan sát; không trực tiếp phát event hoặc điều khiển buzzer.

## 3. Policy → Store: event

```json
{
  "event_id": "uuid",
  "visit_id": "track-7",
  "device_id": "door-01",
  "level": "ALARM",
  "reason": "UNKNOWN_INCOMING_CONFIRMED",
  "identity": "UNKNOWN",
  "person_id": null,
  "occurred_at": "2026-10-03T08:00:01Z",
  "evidence_path": null,
  "acknowledged": false
}
```

Mức event: `INFO | WARNING | ALARM | FAULT`.

Reason chuẩn của MVP:

- `KNOWN_INCOMING_CONFIRMED`
- `UNKNOWN_INCOMING_CONFIRMED`
- `DIRECTION_UNCLEAR_AT_B`
- `FACE_QUALITY_INSUFFICIENT`
- `DEVICE_OFFLINE`
- `VISION_FAILURE`
- `STORAGE_FAILURE`

## 4. Server ↔ Device: buzzer command

Thiết bị poll `GET /api/v1/devices/{device_id}/commands?after_generation=N`.

```json
{
  "commands": [{
    "command_id": "uuid",
    "action": "START",
    "duration_ms": 2000,
    "expires_at": "2026-10-03T08:00:06Z",
    "generation": 12,
    "status": "PENDING"
  }]
}
```

ACK: `POST /api/v1/commands/{command_id}/ack`

```json
{"device_id": "door-01", "status": "ACKED"}
```

Quy tắc:

- Generation lớn hơn thắng generation cũ.
- `STOP` không có duration và phải thắng `START` cũ.
- Thiết bị từ chối lệnh hết hạn, vẫn ACK với `REJECTED_EXPIRED`.
- Mỗi START bị hard cap 3 giây tại firmware.
- Mất control quá 5 giây phải đưa buzzer về OFF.

## 5. Dashboard API

| Method/path | Chức năng |
|---|---|
| `GET /api/v1/system` | Trạng thái hệ thống |
| `POST /api/v1/system/mode` | Chuyển mode |
| `GET /api/v1/events` | Danh sách event mới nhất |
| `POST /api/v1/events/{id}/ack` | Đánh dấu đã xem |
| `POST /api/v1/system/silence` | Phát STOP và silence lượt hiện tại |
| `GET /api/v1/devices` | Trạng thái thiết bị |
| `GET /api/v1/devices/{id}/latest-frame` | Ảnh mới nhất |

## 6. Quy tắc thay đổi contract

- Sửa schema phải cập nhật tài liệu, Pydantic model, simulator, firmware/consumer và contract test.
- Không đổi nghĩa field mà giữ nguyên tên.
- Breaking change tạo `/api/v2`, không lén thay v1.

