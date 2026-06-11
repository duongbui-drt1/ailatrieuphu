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
  lifeline_click.wav hoặc lifeline_click.mp3
  lifeline_5050.mp3 hoặc lifeline_5050.wav
  audience_countdown.mp3 hoặc audience_countdown.wav
  lifeline_call.mp3 hoặc lifeline_call.wav
  lifeline_wise_man.mp3 hoặc lifeline_wise_man.wav
  win.mp3
  complete.mp3 hoặc complete.wav
  program_end.mp3 hoặc program_end.wav
  end_buzzer.wav hoặc end_buzzer.mp3
  viewer_game.mp3 hoặc viewer_game.wav
  viewer_prize.mp3 hoặc viewer_prize.wav
  viewer_break.mp3 hoặc viewer_break.wav
  viewer_technical.mp3 hoặc viewer_technical.wav
  viewer_blank.wav hoặc viewer_blank.mp3
  viewer_stats.mp3 hoặc viewer_stats.wav
  viewer_credits.mp3 hoặc viewer_credits.wav
  viewer_mini_quiz.mp3 hoặc viewer_mini_quiz.wav
  viewer_poll.mp3 hoặc viewer_poll.wav
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
- Mỗi lần bấm trợ giúp sẽ chạy hiệu ứng âm thanh trước, sau 5 giây mới mở/trả kết quả trợ giúp.
- Trợ giúp `Khán Giả` có giới hạn 30 giây trên bảng host, mở sau 2 giây để nhạc hiệu chạy hết nốt; hết giờ sẽ tự chốt dữ liệu đang nhập.

## Scene Và Phím Điều Khiển

Ghi chú cập nhật:

- Từ câu 1 đến câu 5, game tự chạy liên tục, không hiện nút sẵn sàng giữa các câu.
- Từ câu 6 trở đi mới giữ bước xác nhận sẵn sàng và host có thể bấm `Bắt đầu câu` nếu client bị đơ phím.
- Cây tiền thưởng hiện theo mốc 2026: cao nhất `500.000.000 VNĐ`, mốc an toàn sau câu 5 là `5.000.000 VNĐ`, sau câu 10 là `22.000.000 VNĐ`.
- Trợ giúp `Tư Vấn` gợi ý theo xác suất 50/50 thay vì luôn đúng.
- Nếu trả lời sai ở câu 1-5 nhận `0 VNĐ`, câu 6-10 nhận `5.000.000 VNĐ`, câu 11-15 nhận `22.000.000 VNĐ`.
- Màn kết thúc không dùng popup thắng/thua nữa, mà hiện trực tiếp tên thí sinh và số tiền nhận được.

Host có thêm các scene cho viewer:

- `Game`: quay lại câu hỏi hiện tại, đề xuất `viewer_game.wav` là một sting ngắn.
- `Bảng thưởng`: hiện bảng tiền thưởng, đề xuất `viewer_prize.mp3` là nhạc bảng tiền.
- `Nghỉ 5 phút`: màn giải lao có countdown, đề xuất `viewer_break.mp3` là nhạc chờ loop.
- `Technical`: màn chờ kỹ thuật, đề xuất `viewer_technical.mp3` là nhạc nền nhẹ loop.
- `Blank`: màn đen khẩn cấp, đề xuất `viewer_blank.wav` là tiếng cắt tín hiệu ngắn.
- `Stats`: thống kê lượt chơi hiện tại, đề xuất `viewer_stats.wav` là sting dữ liệu ngắn.
- `Credits`: slide credit/sponsor, đề xuất `viewer_credits.mp3` là nhạc credit loop.
- `Mini quiz`: nội dung tương tác nhẹ, đề xuất `viewer_mini_quiz.wav`.
- `Poll`: dự đoán khán giả, đề xuất `viewer_poll.wav`.

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

## Build Desktop

Script đóng gói nằm trong [`packaging/`](packaging/README.md).

Windows:

```powershell
.\packaging\build_windows.bat
```

macOS:

```bash
bash packaging/build_macos.sh
```

Windows sẽ sinh `.exe` trong `dist/`. macOS sẽ sinh `.app` và `.pkg` trong `dist/`. Các build này tự gom `audio/`, `images/` và `questions_*.json`.

Nếu không có máy Mac, dùng GitHub Actions workflow `Build desktop apps` để build macOS artifact trực tiếp trên GitHub.

Để tạo GitHub Release tự động, push tag dạng `v1.0.0`:

```bash
git tag v1.0.0
git push origin v1.0.0
```
