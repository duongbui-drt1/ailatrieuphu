# Ai Là Triệu Phú Desktop Suite

Bộ phần mềm điều khiển game show "Ai Là Triệu Phú" chạy trong mạng LAN, dành cho sân khấu nhỏ, lớp học, sự kiện nội bộ hoặc ghi hình thử nghiệm.

Phần mềm gồm 3 ứng dụng độc lập:

- **Ai Là Triệu Phú (Host)**: bảng điều khiển cho MC/kỹ thuật, đồng thời là server game.
- **Ai Là Triệu Phú (Người Chơi)**: màn hình thí sinh chọn đáp án và dùng trợ giúp.
- **Ai Là Triệu Phú (Khán Giả)**: màn hình trình chiếu cho viewer, bảng tiền thưởng, credit, nghỉ giải lao và poll.

Tác giả/phát triển: **Duli Production LLC.**

Bản quyền: **2020 - 2026 Duli Production LLC.**

## Trạng Thái Bản 2.0 Beta

Phiên bản hiện tại: **2.0.0-beta.1**.

> Cảnh báo anh em: đây là **pre-release beta**. Này, dùng beta mà lỗi lòi ra giữa buổi tổng duyệt thì đừng trách nhé. Bản này để test giao diện 2.0, timing âm thanh, trợ giúp và build desktop mới; chưa nên coi là bản ổn định cho show thật nếu chưa chạy thử đủ một lượt.

## Tải Bản Cài

Vào mục **Releases** trên GitHub và chọn đúng hệ điều hành.

### Windows

Tải file:

```text
AiLaTrieuPhu-Windows-Installer-windows_vX.Y.Z.zip
AiLaTrieuPhu-Windows-Installer-windows_v2.0.0-beta.1.zip
```

Giải nén rồi chạy:

```text
Install-AiLaTrieuPhu.cmd
```

Installer sẽ cho chọn một trong ba bản:

- Host
- Người Chơi
- Khán Giả

Sau khi chọn, installer chỉ tải đúng gói cần dùng từ GitHub Release để tránh bộ cài Windows quá nặng. Shortcut ngoài Desktop vẫn dùng tên tiếng Việt đầy đủ.

Nếu Windows chặn script, mở PowerShell tại thư mục installer và chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-AiLaTrieuPhu.ps1
```

### macOS

Tải file:

```text
AiLaTrieuPhu-macOS-Installer-macos_vX.Y.Z.zip
AiLaTrieuPhu-macOS-Installer-macos_v2.0.0-beta.1.zip
```

Giải nén rồi chạy:

```text
Install-AiLaTrieuPhu.command
```

Installer sẽ tự nhận máy Apple Silicon hoặc Intel, sau đó tải đúng file `.pkg` của Host, Người Chơi hoặc Khán Giả.

Ứng dụng hiện chưa ký Developer ID, nên macOS có thể cảnh báo app tải từ Internet. Cách mở thủ công: right-click app hoặc installer, chọn **Open**, sau đó xác nhận mở.

## Kết Nối LAN

1. Mở **Host** trước.
2. Host sẽ hiển thị IP LAN và port `65432`.
3. Mở **Người Chơi**, nhập tên thí sinh và IP của máy Host.
4. Mở một hoặc nhiều **Khán Giả**, nhập cùng IP Host.

Giới hạn phiên chạy:

- Host chỉ nên chạy 1 instance.
- Người Chơi chỉ nên chạy 1 instance trên một máy.
- Khán Giả có thể mở nhiều máy/màn hình.

Nếu máy khác không kết nối được, kiểm tra cùng mạng Wi-Fi/LAN, Windows Firewall, IP Host và port `65432`.

## Luồng Game Chính

- Câu 1 đến 5 chạy liên tục, không cần bấm sẵn sàng giữa các câu.
- Từ câu 6 trở đi, Người Chơi cần xác nhận sẵn sàng; Host vẫn có nút ép bắt đầu nếu client bị kẹt.
- Từ câu 6, đáp án được chọn sẽ hiện cho viewer trước, nhưng Host là người công bố đúng/sai.
- Host có nút **Give Up** từ câu 6. Sau khi give up, thí sinh vẫn được chọn đáp án để "tiếc nuối", rồi Host unlock đáp án và kết màn hình.
- Nếu give up, tiền thưởng là số tiền đã trả lời đúng trước đó, không phải mốc tiền của câu đang hỏi.
- Nếu trả lời đúng cả 15 câu, màn hình kết thúc dùng lời chúc mừng riêng: **CHÚC MỪNG TRIỆU PHÚ**.

## Mốc Tiền Thưởng

Cây tiền thưởng hiện dùng format mới:

```text
15 - 500.000.000 VNĐ
14 - 250.000.000 VNĐ
13 - 120.000.000 VNĐ
12 - 60.000.000 VNĐ
11 - 30.000.000 VNĐ
10 - 22.000.000 VNĐ
09 - 14.000.000 VNĐ
08 - 10.000.000 VNĐ
07 - 8.000.000 VNĐ
06 - 6.000.000 VNĐ
05 - 5.000.000 VNĐ
04 - 4.000.000 VNĐ
03 - 3.000.000 VNĐ
02 - 2.000.000 VNĐ
01 - 1.000.000 VNĐ
```

Luật tiền thưởng:

- Trả lời sai từ câu 1 đến câu 5: nhận `0 VNĐ`.
- Trả lời sai từ câu 6 trở đi: nhận `2.000.000 VNĐ`.
- Give up từ câu 6 trở đi: nhận số tiền đã trả lời đúng trước đó.
- Đúng cả 15 câu: nhận `500.000.000 VNĐ`.

## Trợ Giúp

Các trợ giúp hiện có:

- **50:50**: loại hai đáp án sai. Trình tự âm thanh là `lifeline_click`, chờ 5 giây, sau đó phát `lifeline_5050` đồng thời xóa hai đáp án sai.
- **Khán Giả**: Host mở popup ngay sau khi người chơi bấm trợ giúp. Popup chờ hiệu ứng 5 giây rồi mới cho MC bấm bắt đầu vòng 30 giây.
- **Gọi Điện**: Host có ô nhập gợi ý đáp án, nhạc/vòng 30 giây bắt đầu ngay khi MC bấm **Bắt đầu 30 giây**.
- **Tư Vấn / Nhà Thông Thái**: ẩn trước câu 6, từ câu 6 mới hiện. Host nhập gợi ý sau vòng 30 giây; không còn tự trả lời đúng 100%.

Các popup trợ giúp trên Host không cho chốt sớm nếu chưa qua 5 giây hiệu ứng và chưa bắt đầu vòng 30 giây. Logic audio đã tách để tránh chồng âm khi dùng trợ giúp liên tiếp.

## Pack Câu Hỏi

Các pack đề nằm ở root repo theo dạng:

```text
questions_pack1.json
questions_pack2.json
questions_pack3.json
...
```

Host có tab kỹ thuật để:

- Xem pack.
- Import pack JSON mới.
- Lưu trữ pack.
- Kích hoạt lại pack.
- Xóa pack.

Sau mỗi lượt chơi, hệ thống tự shuffle/chọn pack cho người chơi tiếp theo. Pack có counter số lần dùng; nếu vượt ngưỡng dùng quá nhiều, pack sẽ chuyển sang lưu trữ để tránh lặp câu.

Poll khán giả dùng câu hỏi từ pack riêng. Khi Host công bố một câu poll, câu đó sẽ bị đánh dấu đã dùng. Nếu không đổi đáp án sau thời gian chờ hoặc Host chốt, hệ thống chọn người chơi backup theo đáp án đúng.

## Tài Nguyên

Đặt tài nguyên trong các thư mục:

```text
audio/
images/
```

Các file ảnh quan trọng:

```text
images/logo.png
images/background.png
images/app.ico       # tùy chọn cho Windows
images/app.icns      # tùy chọn cho macOS
images/lifeline_5050.png
images/lifeline_5050_used.png
images/lifeline_call.png
images/lifeline_call_used.png
images/lifeline_audience.png
images/lifeline_audience_used.png
images/lifeline_wise_man.png
images/lifeline_wise_man_used.png
images/timer_30.png ... images/timer_00.png
```

Các file âm thanh nên có:

```text
audio/welcome.mp3
audio/ready.mp3
audio/wait_1_5.mp3
audio/wait_6_10.mp3
audio/wait_11_15.mp3
audio/lifeline_click.mp3
audio/lifeline_5050.mp3
audio/audience_countdown.mp3
audio/lifeline_call.mp3
audio/lifeline_wise_man.mp3
audio/wise_man_countdown.mp3
audio/viewer_break.mp3
audio/viewer_poll.mp3
audio/program_end.mp3
audio/end_buzzer.mp3
audio/correct.wav
audio/wrong.wav
audio/selected.wav
```

Nếu thiếu file âm thanh, app vẫn chạy nhưng sẽ bỏ qua hiệu ứng tương ứng.

## Chạy Từ Source

Yêu cầu:

- Python 3.10+
- Pillow
- Pygame

Cài thư viện:

```powershell
pip install -r requirements.txt
```

Chạy không hiện terminal trên Windows:

```text
run_host.pyw
run_client.pyw
run_viewer.pyw
```

Chạy có log/debug:

```powershell
python host_gui.py
python client_gui.py
python viewer.py
```

## Build Từ Source

Windows:

```powershell
.\packaging\build_windows.bat
```

macOS:

```bash
bash packaging/build_macos.sh
```

Build một role:

```powershell
.\packaging\build_windows.bat -Target host
.\packaging\build_windows.bat -Target client
.\packaging\build_windows.bat -Target viewer
```

Chi tiết build nằm ở [packaging/README.md](packaging/README.md).

## Tạo Release

Version nằm trong [app_info.py](app_info.py).

Quy ước version:

- `1.x.x`: bản lớn, thay đổi nhiều.
- `x.1.x`: bản vừa hoặc fix ổn định.
- `x.x.1`: bản vá nhỏ.
- `x.y.z-beta.n`: bản thử nghiệm/pre-release, có thể lỗi và cần test kỹ trước show thật.

Tag có chữ `alpha`, `beta`, `rc` hoặc `pre` sẽ được GitHub Actions tạo dưới dạng **pre-release**.

Tạo release Windows:

```bash
git tag windows_v2.0.0-beta.1
git push origin windows_v2.0.0-beta.1
```

Tạo release macOS:

```bash
git tag macos_v2.0.0-beta.1
git push origin macos_v2.0.0-beta.1
```

Workflow sẽ upload:

- Windows installer selector.
- Windows role zip cho Host/Người Chơi/Khán Giả.
- macOS installer selector.
- macOS role pkg cho Apple Silicon và Intel.

## Ghi Chú Phát Hành

Các app build ra dùng tên kỹ thuật không dấu để tránh lỗi Unicode trong Windows/GitHub Actions:

```text
AiLaTrieuPhu-Host
AiLaTrieuPhu-Client
AiLaTrieuPhu-Viewer
```

Tên hiển thị với người dùng vẫn là:

```text
Ai Là Triệu Phú (Host)
Ai Là Triệu Phú (Người Chơi)
Ai Là Triệu Phú (Khán Giả)
```

Đây là chủ ý để bản Win/mac dễ build, dễ tải, nhưng ngoài Desktop/Applications vẫn nhìn đúng tên chương trình.
