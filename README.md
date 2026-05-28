# AI LÀ TRIỆU PHÚ CODE

Ứng dụng chơi "Ai Là Triệu Phú" trên mạng LAN, gồm 3 màn hình:

- `host_gui.py`: bảng điều khiển cho MC/host, đồng thời chạy server socket.
- `client_gui.py`: màn hình thí sinh, có ảnh nút trả lời và nhạc hiệu.
- `viewer.py`: màn hình khán giả theo dõi câu hỏi, đáp án và tiến trình.

## Yêu cầu

- Python 3.10+
- Pillow để load/resize ảnh giao diện.
- Pygame là tùy chọn. Nếu không có Pygame, bản Windows sẽ tự phát MP3/WAV bằng audio backend hệ thống.

Cài thư viện:

```powershell
pip install -r requirements.txt
```

## Tài nguyên

Đặt tài nguyên ở đúng cấu trúc này:

```text
audio/
  welcome.mp3
  ready.mp3
  wait_1_5.mp3
  wait_6_10.mp3
  wait_11_15.mp3
  lifeline.mp3
  lifeline_5050.mp3 hoặc lifeline_5050.wav
  audience_countdown.mp3 hoặc audience_countdown.wav
  lifeline_wise_man.mp3 hoặc lifeline_wise_man.wav
  win.mp3
  complete.mp3 hoặc complete.wav
  selected.wav
  correct.wav
  wrong.wav
  end_game.wav
images/
  background.png hoặc background.jpg
  logo.png
  button_normal.png
  button_selected.png
  button_correct.png
  button_wrong.png
questions_pack1.json
questions_pack2.json
...
```

Code hiện dùng đường dẫn theo thư mục repo, nên có thể chạy script từ nơi khác mà vẫn tìm được `audio/`, `images/` và các gói câu hỏi.

## Chạy nhanh

Trên Windows, nên double-click các file `.pyw` để chạy không hiện cửa sổ terminal:

```text
run_host.pyw
run_client.pyw
run_viewer.pyw
```

Nếu muốn xem log/debug trong terminal, chạy trực tiếp các file `.py` bên dưới.

Trên máy host:

```powershell
python host_gui.py
```

Host sẽ hiển thị IP LAN và port `65432` trong nhật ký server.

Trên máy thí sinh:

```powershell
python client_gui.py
```

Nhập tên thí sinh và IP server.

Trên máy khán giả:

```powershell
python viewer.py
```

Nhập IP server. Viewer có thể mở trước hoặc sau client; server sẽ phân loại đúng viewer/thí sinh qua gói định danh đầu tiên.

## Cách chơi

Host mở `host_gui.py`, thí sinh mở `client_gui.py`, khán giả mở `viewer.py`. Mỗi lượt chơi dùng ngẫu nhiên một file `questions_pack*.json`. Thí sinh có các trợ giúp `50:50`, `Khán Giả`, `Gọi Điện`, và `Tư Vấn` từ câu 6 trở đi.

## Luồng điều khiển Host

- Host có nút `Bắt đầu câu` để ép chuyển sang câu hỏi khi client không bấm được nút sẵn sàng.
- Từ câu 1 đến câu 5, đáp án được công bố tự động sau khi thí sinh chọn.
- Từ câu 6 trở đi, thí sinh chọn đáp án trước, viewer thấy đáp án đó ngay, nhưng host phải bấm `Công bố đáp án` để reveal đúng/sai.
- Trợ giúp `Gọi Điện` chỉ còn độ tin cậy 50/50.
- Trợ giúp `Khán Giả` có giới hạn 60 giây trên bảng host; hết giờ sẽ tự chốt dữ liệu đang nhập.

## Scene Và Phím Điều Khiển

Ghi chú cập nhật:

- Từ câu 1 đến câu 5, game tự chạy liên tục, không hiện nút sẵn sàng giữa các câu.
- Từ câu 6 trở đi mới giữ bước xác nhận sẵn sàng và host có thể bấm `Bắt đầu câu` nếu client bị đơ phím.
- Trợ giúp `Tư Vấn` gợi ý theo xác suất 50/50 thay vì luôn đúng.
- Nếu thí sinh sai từ câu 10 trở đi, màn kết thúc hiển thị mức nhận được mặc định `2.000.000 VNĐ`; trước câu 10 hiển thị đúng số tiền đã qua.
- Màn kết thúc không dùng popup thắng/thua nữa, mà hiện trực tiếp tên thí sinh và số tiền nhận được.

Host có thêm các scene cho viewer:

- `Game`: quay lại câu hỏi hiện tại.
- `Bảng thưởng`: hiện bảng tiền thưởng.
- `Nghỉ 5 phút`: màn giải lao có countdown.
- `Technical`: màn chờ kỹ thuật.
- `Blank`: màn đen khẩn cấp.
- `Stats`: thống kê lượt chơi hiện tại.
- `Credits`: slide credit/sponsor.
- `Mini quiz` và `Poll`: nội dung tương tác nhẹ cho khán giả lúc nghỉ.

Host có thêm nút kỹ thuật:

- `Hủy chốt đáp án`: cho phép thí sinh chọn lại trước khi công bố.
- `Resend`: phát lại trạng thái hiện tại cho client/viewer.
- `Sửa câu hiện tại`: sửa nhanh câu hỏi, 4 phương án và đáp án đúng.
- `Đổi câu`: lấy câu dự phòng cùng level từ các gói câu hỏi.
- `Nhạc căng` / `Dừng nhạc`: điều khiển nhạc client thủ công.

Hotkey:

- `Enter`: bắt đầu câu khi đang chờ ready.
- `Space`: công bố đáp án đang chốt.
- `P`: tạm dừng / tiếp tục.
- `M`: tắt / bật nhạc client.
- `R`: resend trạng thái.
- `B`: màn nghỉ 5 phút.
- `Esc`: blank screen.
