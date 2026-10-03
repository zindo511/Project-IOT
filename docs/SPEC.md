# SPEC — Smart Security MVP

**Version:** 0.1  
**Owner:** PM / Backend  
**Mốc demo:** 07/11/2026

## 1. Bài toán

Hệ thống theo dõi một lối tiếp cận cửa đã bố trí trước. Camera gửi ảnh về laptop; laptop theo dõi người qua vùng A/B và chỉ phát còi khi có đủ bằng chứng rằng một người không khớp gallery đang tiến từ A vào B.

Đây là demo trong môi trường kiểm soát, không phải sản phẩm an ninh thương mại. “Không khớp gallery” không đồng nghĩa người đó có ý xấu.

## 2. Phạm vi MVP

- Một ESP32-CAM, một cửa, một vùng A và một vùng B không chồng lấn.
- Một người được xử lý tin cậy tại một thời điểm.
- Gallery 3–5 người active.
- Hoạt động trong LAN, không phụ thuộc Internet.
- Dashboard trên laptop/điện thoại cùng LAN.
- Server restart luôn về `DISARMED`.

Không thuộc MVP: Telegram, khóa cửa, liveness, camera thứ hai, ban đêm/ngoài trời, nhận diện đám đông và bảo đảm an ninh tuyệt đối.

## 3. Khái niệm chung

- **Vùng A:** lối tiếp cận. Dùng để tạo track và chứng minh hướng đi.
- **Vùng B:** vị trí gần cửa, nơi mặt phải đủ rõ để so khớp.
- **Track:** ID tạm nối cùng một người qua nhiều frame.
- **Visit:** một lượt track ổn định đi vào B; event được chống lặp theo visit.
- **KNOWN:** mặt đủ rõ và khớp một người active.
- **UNKNOWN:** mặt đủ rõ nhưng không khớp gallery qua nhiều quan sát.
- **UNCERTAIN:** thiếu chất lượng, thiếu phiếu hoặc score ở vùng không chắc chắn.
- **INCOMING:** cùng track được xác nhận ở A trước khi được xác nhận ở B.

## 4. Luồng quyết định

1. Khi `ARMED`, thiết bị gửi frame định kỳ; PIR chỉ tăng nhịp chụp.
2. Vision phát hiện người/mặt, cập nhật track và vùng.
3. Chỉ khi track ở B mới dùng kết quả mặt để bỏ phiếu danh tính.
4. Policy yêu cầu tối thiểu 3 phiếu hợp lệ trong cửa sổ 5 quan sát.
5. `KNOWN + INCOMING` tạo `INFO`, không còi.
6. `UNKNOWN + INCOMING` tạo `ALARM` và một lệnh buzzer nếu không cooldown.
7. Mặt không rõ, xuất hiện thẳng ở B hoặc chiều không rõ tạo `WARNING`, không còi.
8. Mỗi loại event chỉ phát một lần trên cùng visit.

## 5. Trạng thái hệ thống

- `DISARMED`: không giám sát, không tạo alarm; STOP buzzer khi chuyển vào trạng thái này.
- `ARMED`: nhận frame, chạy vision/policy và có thể phát alarm.
- `PREVIEW`: xem ảnh để chỉnh camera, không tạo alarm.
- `ENROLLING`: thu mẫu cho đúng một hồ sơ, không tạo alarm.

## 6. Nghiệm thu MVP

| Tình huống | Kết quả bắt buộc |
|---|---|
| Known A → B | Một INFO, không còi |
| Unknown A → B, mặt rõ 3/5 | Một ALARM, một lệnh còi |
| Đi ngang A | Không còi |
| B → A | Không còi |
| Xuất hiện thẳng B | WARNING, không còi |
| Mặt mờ/quay lưng | WARNING hoặc chưa kết luận, không còi |
| Đứng lâu tại B | Không lặp event theo frame |
| Camera/AI offline | FAULT, không suy ra “không có người” |

Mỗi kịch bản phải chạy đạt ít nhất 5 lần; soak test 30–60 phút không có còi tự bật hoặc event spam.

## 7. Nguyên tắc riêng tư và an toàn

- Không commit dữ liệu sinh trắc học hoặc ảnh người thật.
- Ảnh evidence nằm trong thư mục runtime và phải có chính sách xóa.
- Còi luôn có hard cap tại firmware; server không phải lớp an toàn duy nhất.
- Thiếu bằng chứng thì không hú còi, nhưng lưu warning có lý do rõ.

