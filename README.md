# Ai Là Triệu Phú Desktop Suite

Bộ phần mềm điều khiển game show "Ai Là Triệu Phú" chạy trong mạng LAN, dành cho lớp học, sân khấu nhỏ, sự kiện nội bộ, livestream thử nghiệm hoặc ghi hình không thương mại.

Dự án này không phải sản phẩm chính thức của bất kỳ đơn vị sở hữu format/trademark chương trình truyền hình nào. Khi dùng cho chương trình thật, hãy tự kiểm tra quyền sử dụng tên gọi, hình ảnh, âm thanh, format và các tài nguyên đi kèm. Đừng để buổi tổng duyệt biến thành buổi học luật bản quyền miễn phí.

- Tác giả/phát triển: **Duli Production LLC.**
- Phiên bản hiện tại: **2.0.0-beta.3**
- Bản quyền phần mềm: **2020 - 2026 Duli Production LLC.**
- License source code: **GPL-3.0**, xem [LICENSE](LICENSE).

> Cảnh báo beta: bản 2.0 đang là **pre-release**. Có nhiều thay đổi về giao diện, âm thanh, trợ giúp, build desktop và release macOS/Windows. Hãy chạy thử đủ một lượt trước khi đem vào show thật. Dùng beta giữa chương trình mà lỗi phát nổ thì đừng trách phần mềm quá thành thật.

## Ứng Dụng Gồm Những Gì

- **Ai Là Triệu Phú (Host)**: bảng điều khiển cho MC/kỹ thuật, đồng thời là server game.
- **Ai Là Triệu Phú (Người Chơi)**: màn hình thí sinh chọn đáp án, xác nhận sẵn sàng và dùng trợ giúp.
- **Ai Là Triệu Phú (Khán Giả)**: màn hình trình chiếu cho viewer, bảng tiền thưởng, credit, nghỉ giải lao, poll và trạng thái chương trình.

Luồng chuẩn là mở Host trước, sau đó Người Chơi và Khán Giả kết nối vào Host qua mạng LAN.

## Cài Đặt Nhanh

Vào mục **Releases** trên GitHub, chọn đúng hệ điều hành và đúng phiên bản.

### Windows

Tải file selector:

```text
AiLaTrieuPhu-Windows-Installer-windows_vX.Y.Z.zip
AiLaTrieuPhu-Windows-Installer-windows_v2.0.0-beta.3.zip
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

Nếu app bị Windows SmartScreen cảnh báo, chọn **More info** rồi **Run anyway** nếu bạn tin nguồn tải. Bản hiện tại chưa ký code-signing thương mại.

### macOS

Tải file selector:

```text
AiLaTrieuPhu-macOS-DMG-Selector-macos_vX.Y.Z.zip
AiLaTrieuPhu-macOS-DMG-Selector-macos_v2.0.0-beta.3.zip
```

Giải nén rồi chạy:

```text
Install-AiLaTrieuPhu.command
```

Selector sẽ tự nhận máy Apple Silicon hoặc Intel, sau đó tải đúng file `.dmg` của Host, Người Chơi hoặc Khán Giả. Mở DMG rồi kéo app vào biểu tượng **Applications** trong cửa sổ vừa hiện.

Ứng dụng hiện chưa ký Developer ID, nên macOS có thể cảnh báo app tải từ Internet. Cách mở thủ công: kéo app vào Applications, right-click app, chọn **Open**, sau đó xác nhận mở.

## Hướng Dẫn Sử Dụng

### Kết Nối LAN

1. Mở **Host** trước.
2. Host sẽ hiển thị IP LAN và port `65432`.
3. Mở **Người Chơi**, nhập tên thí sinh và IP của máy Host.
4. Mở một hoặc nhiều **Khán Giả**, nhập cùng IP Host.

Giới hạn phiên chạy:

- Host chỉ nên chạy 1 instance.
- Người Chơi chỉ nên chạy 1 instance trên một máy.
- Khán Giả có thể mở nhiều máy hoặc nhiều màn hình.

Nếu máy khác không kết nối được, kiểm tra cùng mạng Wi-Fi/LAN, Windows Firewall, IP Host và port `65432`.

### Luồng Game Chính

- Câu 1 đến 5 chạy liên tục, không cần bấm sẵn sàng giữa các câu.
- Từ câu 6 trở đi, Người Chơi cần xác nhận sẵn sàng; Host vẫn có nút ép bắt đầu nếu client bị kẹt.
- Từ câu 6, đáp án được chọn sẽ hiện cho viewer trước, nhưng Host là người công bố đúng/sai.
- Host có nút **Give Up** từ câu 6. Sau khi give up, thí sinh vẫn được chọn đáp án để "tiếc nuối", rồi Host unlock đáp án và kết màn hình.
- Nếu give up, tiền thưởng là số tiền đã trả lời đúng trước đó, không phải mốc tiền của câu đang hỏi.
- Nếu trả lời đúng cả 15 câu, màn hình kết thúc dùng lời chúc mừng riêng: **CHÚC MỪNG TRIỆU PHÚ**.

### Mốc Tiền Thưởng

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

### Trợ Giúp

- **50:50**: phát `lifeline_click`, chờ 5 giây, sau đó phát `lifeline_5050` đồng thời loại hai đáp án sai.
- **Khán Giả**: Host mở popup ngay sau khi người chơi bấm trợ giúp. Popup chờ hiệu ứng 5 giây rồi mới cho MC bấm bắt đầu vòng 30 giây.
- **Gọi Điện**: Host có ô nhập gợi ý đáp án. Nhạc và vòng 30 giây bắt đầu khi MC bấm **Bắt đầu 30 giây**.
- **Tư Vấn / Nhà Thông Thái**: ẩn trước câu 6, từ câu 6 mới hiện. Host nhập gợi ý sau vòng 30 giây; không còn tự trả lời đúng 100%.

Các popup trợ giúp trên Host không cho chốt sớm nếu chưa qua 5 giây hiệu ứng và chưa bắt đầu vòng 30 giây. Logic audio đã tách để tránh chồng âm khi dùng trợ giúp liên tiếp.

### Pack Câu Hỏi

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

### Những Điều Nên Nhớ Khi Chạy Show

- Chạy thử cả 3 app trước ngày diễn, không thử lần đầu trước mặt khán giả.
- Đặt máy Host ở mạng ổn định nhất, ưu tiên LAN hoặc Wi-Fi mạnh.
- Chuẩn bị sẵn người kỹ thuật nhìn Host, đừng bắt MC vừa dẫn vừa debug.
- Kiểm tra audio trước: nhạc nền, chọn đáp án, đúng/sai, trợ giúp, nghỉ giải lao và kết thúc chương trình.
- Nếu dùng tài nguyên tự tải ngoài, tự chịu trách nhiệm về bản quyền tài nguyên đó.

## Tài Nguyên Ảnh Và Âm Thanh

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

## Hướng Dẫn Cho Coder Vọc

### Cấu Trúc Dự Án

```text
host_gui.py          # giao diện Host và server điều khiển
client_gui.py        # giao diện Người Chơi
viewer.py            # giao diện Khán Giả
server.py            # protocol/server state
client.py            # client network layer
question_packs.py    # quản lý pack câu hỏi
ui_assets.py         # asset UI dùng chung
audio_backend.py     # phát/tắt/loop audio
resources.py         # resolve tài nguyên khi chạy source hoặc build
single_instance.py   # giới hạn số instance theo role
app_info.py          # version, tác giả, metadata app
packaging/           # build scripts Windows/macOS/release
```

### Chạy Từ Source

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

### Build Từ Source

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

### Tạo Release

Version nằm trong [app_info.py](app_info.py).

Quy ước version:

- `1.x.x`: bản lớn, thay đổi nhiều.
- `x.1.x`: bản vừa hoặc fix ổn định.
- `x.x.1`: bản vá nhỏ.
- `x.y.z-beta.n`: bản thử nghiệm/pre-release, cần test kỹ trước show thật.

Tag có chữ `alpha`, `beta`, `rc` hoặc `pre` sẽ được GitHub Actions tạo dưới dạng **pre-release**.

Tạo release Windows:

```bash
git tag windows_v2.0.0-beta.3
git push origin windows_v2.0.0-beta.3
```

Tạo release macOS:

```bash
git tag macos_v2.0.0-beta.3
git push origin macos_v2.0.0-beta.3
```

Workflow sẽ upload:

- Windows installer selector.
- Windows role zip cho Host/Người Chơi/Khán Giả.
- macOS DMG selector.
- macOS role DMG kéo-thả cho Apple Silicon và Intel.

### Ghi Chú Build

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

## Quy Tắc Và Quy Định Sử Dụng

### Phạm Vi Khuyến Nghị

Phần mềm được thiết kế cho:

- Sự kiện phi thương mại.
- Lớp học, câu lạc bộ, workshop, sân khấu nội bộ.
- Truyền hình nội bộ, ghi hình thử nghiệm, rehearsal hoặc demo không bán vé.
- Hoạt động cá nhân hoặc cộng đồng không dùng để thu phí trực tiếp từ format chương trình.

Nếu bạn muốn dùng cho chương trình thương mại, phát sóng công khai, sự kiện có tài trợ, bán vé, sản phẩm truyền thông hoặc gói dịch vụ có thu tiền, hãy liên hệ Duli Production LLC trước để trao đổi quyền sử dụng, hỗ trợ kỹ thuật và trách nhiệm pháp lý liên quan.

### Những Việc Không Nên Làm

- Không dùng phần mềm để giả mạo sản phẩm chính thức của đơn vị sở hữu format/trademark "Ai Là Triệu Phú" hoặc "Who Wants To Be A Millionaire".
- Không bán lại bản build, asset pack hoặc bộ cài như một sản phẩm độc quyền nếu chưa có thỏa thuận riêng.
- Không nhúng tài nguyên âm thanh, hình ảnh, logo, câu hỏi có bản quyền vào show công khai nếu bạn không có quyền sử dụng.
- Không xóa thông tin tác giả, license hoặc thông tin liên hệ khi phân phối lại bản sửa đổi.
- Không dùng bản beta cho show quan trọng mà chưa test kỹ. Đây không phải mê tín, đây là kinh nghiệm xương máu.

### Về Source Code Và License

Source code trong repo được phát hành theo GPL-3.0. Bạn có thể học, sửa, build và phân phối lại theo điều kiện của GPL-3.0. Khi phân phối bản sửa đổi, hãy giữ thông tin license và công bố source tương ứng theo đúng yêu cầu license.

Các tài nguyên bên ngoài do người dùng tự thêm vào `audio/` và `images/` có thể có quyền sở hữu riêng. License của source code không tự động cấp quyền sử dụng các tài nguyên đó cho mục đích thương mại hoặc phát sóng.

## Liên Hệ

Liên hệ phát triển, hỗ trợ, xin phép sử dụng thương mại hoặc trao đổi hợp tác:

```text
Email: dulicontact.ctme@gmail.com
Phone/Zalo: +84 0855403255
Đơn vị phát triển: Duli Production LLC.
```

Khi báo lỗi, nên gửi kèm:

- Hệ điều hành và phiên bản app.
- Bạn đang chạy Host, Người Chơi hay Khán Giả.
- Ảnh chụp lỗi hoặc log terminal nếu có.
- Các bước tái hiện lỗi càng ngắn càng tốt.