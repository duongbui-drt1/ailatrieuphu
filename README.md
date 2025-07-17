🎮 AI LÀ TRIỆU PHÚ CODE
Chào mừng bạn đến với AI LÀ TRIỆU PHÚ CODE – phiên bản tương tác của game show huyền thoại “Ai Là Triệu Phú”, hỗ trợ chạy trên mạng LAN với giao diện host, client (thí sinh) và viewer (khán giả)!

Bạn có thể tổ chức một buổi chơi vui nhộn ngay tại lớp học, văn phòng hay trong buổi tụ họp bạn bè.

🚀 Tính năng chính
✅ Host – Người điều khiển game, chọn câu hỏi, kiểm soát tiến trình, phát nhạc hiệu.
✅ Client – Thí sinh trả lời câu hỏi, chọn trợ giúp, xem tiến trình của mình.
✅ Viewer – Khán giả theo dõi trực tiếp diễn biến của thí sinh, điểm số và hiệu ứng sống động.
✅ Chạy trên LAN – Không cần internet, chỉ cần kết nối chung một mạng nội bộ.
✅ Nhạc nền & hiệu ứng như game show thật.
✅ Giao diện trực quan và dễ thao tác.

📂 Cấu trúc thư mục
AI-LA-TRIEU-PHU/
│
├─ host/         # Giao diện điều khiển của MC/host
├─ client/       # Giao diện thí sinh
└─ viewer/       # Giao diện người xem
🛠 Yêu cầu hệ thống
Python 3.10+ (hoặc Node.js nếu dùng bản web)
Các thư viện hỗ trợ (Flask/FastAPI, WebSocket, hoặc socket.io)
Tất cả máy tham gia phải chung một mạng LAN

⚡ Cách chạy nhanh nhất
Kết nối tất cả máy vào cùng mạng LAN
Có thể dùng WiFi chung hoặc tạo mạng LAN ảo (Hotspot).
Khởi chạy Host
cd host
python app.py
→ Host sẽ hiển thị IP LAN (ví dụ: 192.168.1.10:5000)

Khởi chạy Client (Thí sinh)
cd client
python app.py --host-ip 192.168.1.10
→ Nhập tên thí sinh, kết nối đến host.

Khởi chạy Viewer (Khán giả)
cd viewer
python app.py --host-ip 192.168.1.10
→ Viewer sẽ thấy toàn bộ tiến trình.

🎯 Cách chơi
Host chọn câu hỏi → Thí sinh nhận câu hỏi trên Client
Thí sinh trả lời bằng giao diện Client
Kết quả hiển thị trên Viewer với hiệu ứng, nhạc nền và điểm số
Host có thể dừng, bỏ qua câu hỏi hoặc sử dụng trợ giúp (50:50, hỏi khán giả, gọi điện thoại)

🔥 Tip để trải nghiệm mượt mà
Dùng PC/laptop làm Host, các thiết bị khác làm Client & Viewer.
Nếu mạng WiFi yếu, hãy tạo mạng LAN ảo để ổn định kết nối.
Mở loa ngoài để mọi người nghe được nhạc hiệu!
