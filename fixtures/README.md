# Shared contract fixtures

Các file JSON này mô tả phần thay đổi của observation qua một track. Producer và consumer phải dùng cùng fixture khi sửa contract. Test/runtime bổ sung các field bắt buộc như `device_id`, `frame_id`, `captured_at` và `track_id`.

- `known-incoming.json` phải kết thúc bằng một INFO và không có lệnh còi.
- `unknown-incoming.json` phải kết thúc bằng một ALARM và một lệnh còi nếu hết cooldown.

Không đặt ảnh hoặc embedding người thật trong thư mục này.
