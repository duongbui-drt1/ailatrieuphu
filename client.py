import socket
import json
import os
import sys
import time

# --- CẤU HÌNH ---
PORT = 65432      # Port để kết nối, PHẢI GIỐNG VỚI SERVER
BUFFER_SIZE = 4096

# --- MÃ MÀU CHO GIAO DIỆN THÂN THIỆN ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_screen():
    """Xóa màn hình console."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_welcome():
    """Hiển thị màn hình chào mừng."""
    clear_screen()
    print(Colors.HEADER + Colors.BOLD + "*" * 60)
    print(" " * 18 + "CHÀO MỪNG BẠN ĐẾN VỚI" + " " * 18)
    print(" " * 20 + "AI LÀ TRIỆU PHÚ" + " " * 23)
    print("*" * 60 + Colors.ENDC)
    print("\n")

def send_data(s, data):
    """Gửi dữ liệu đã được mã hóa JSON đến server."""
    try:
        s.sendall(json.dumps(data).encode('utf-8'))
    except socket.error:
        print(Colors.FAIL + "Lỗi: Mất kết nối đến server." + Colors.ENDC)
        sys.exit()

def receive_data(s):
    """Nhận và giải mã dữ liệu JSON từ server."""
    try:
        raw_data = s.recv(BUFFER_SIZE)
        if not raw_data:
            return None
        return json.loads(raw_data.decode('utf-8'))
    except (socket.error, json.JSONDecodeError):
        return None

def display_question(data):
    """Hiển thị câu hỏi và các thông tin liên quan."""
    clear_screen()
    print(Colors.CYAN + f"Câu hỏi số {data['level']} - Mức tiền thưởng: {Colors.BOLD}{data['prize']} VNĐ{Colors.ENDC}")
    print("-" * 50)
    print(Colors.WARNING + Colors.BOLD + f"\n{data['question']}\n" + Colors.ENDC)

    options = data['options']
    for key, value in options.items():
        if value: # Chỉ hiển thị các phương án không bị 50:50 loại bỏ
            print(f"  {Colors.BLUE}{key}:{Colors.ENDC} {value}")

    print("\n" + "-" * 50)
    print(Colors.GREEN + "Các quyền trợ giúp còn lại:" + Colors.ENDC)
    lifelines_text = []
    if data['lifelines']['5050']: lifelines_text.append(f"{Colors.BOLD}'5050'{Colors.ENDC} (50:50)")
    if data['lifelines']['audience']: lifelines_text.append(f"{Colors.BOLD}'khanphong'{Colors.ENDC} (Khán phòng)")
    if data['lifelines']['call']: lifelines_text.append(f"{Colors.BOLD}'goi'{Colors.ENDC} (Gọi điện thoại)")
    
    if not lifelines_text:
        print("  (Không còn)")
    else:
        print("  " + " | ".join(lifelines_text))

def get_player_input(valid_options):
    """Lấy và xác thực lựa chọn của người chơi."""
    while True:
        prompt = f"\n{Colors.BOLD}Nhập lựa chọn của bạn (A, B, C, D) hoặc tên trợ giúp: {Colors.ENDC}"
        choice = input(prompt).upper().strip()

        if choice in ['A', 'B', 'C', 'D']:
            if valid_options[choice]: # Kiểm tra xem lựa chọn có bị 50:50 loại bỏ không
                return {'action': 'answer', 'value': choice}
            else:
                print(Colors.FAIL + "Lựa chọn này đã bị loại bỏ. Vui lòng chọn lại." + Colors.ENDC)
        elif choice in ['5050', 'KHANPHONG', 'GOI']:
            lifeline_map = {'5050': '5050', 'KHANPHONG': 'audience', 'GOI': 'call'}
            return {'action': 'lifeline', 'value': lifeline_map[choice]}
        else:
            print(Colors.FAIL + "Lựa chọn không hợp lệ. Vui lòng nhập lại." + Colors.ENDC)

def main():
    print_welcome()
    server_ip = input("Nhập địa chỉ IP của server: ").strip()
    if not server_ip:
        print("Địa chỉ IP không được để trống. Thoát chương trình.")
        return

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"\nĐang kết nối đến server tại {server_ip}...")
        client_socket.connect((server_ip, PORT))
        print(Colors.GREEN + "Kết nối thành công! Trò chơi bắt đầu." + Colors.ENDC)
        time.sleep(2)
    except socket.gaierror:
        print(Colors.FAIL + f"Lỗi: Không thể tìm thấy địa chỉ IP '{server_ip}'. Vui lòng kiểm tra lại." + Colors.ENDC)
        return
    except ConnectionRefusedError:
        print(Colors.FAIL + "Lỗi: Kết nối bị từ chối. Đảm bảo server đang chạy và không bị tường lửa chặn." + Colors.ENDC)
        return
    except Exception as e:
        print(Colors.FAIL + f"Đã xảy ra lỗi khi kết nối: {e}" + Colors.ENDC)
        return

    game_running = True
    while game_running:
        server_data = receive_data(client_socket)
        
        if not server_data:
            print(Colors.FAIL + "\nMất kết nối với server. Trò chơi kết thúc." + Colors.ENDC)
            break
        
        msg_type = server_data.get('type')

        if msg_type == 'question':
            display_question(server_data)
            player_choice = get_player_input(server_data['options'])
            send_data(client_socket, player_choice)

        elif msg_type == 'result':
            if server_data['correct']:
                print(Colors.GREEN + "\nChính xác! Bạn nhận được " + Colors.BOLD + f"{server_data['prize']} VNĐ." + Colors.ENDC)
                time.sleep(2) # Chờ để người chơi đọc
            # Phần trả lời sai được xử lý bởi 'game_over'
            
        elif msg_type == 'info':
            print(Colors.CYAN + f"\n[Thông tin từ Server]: {server_data['message']}" + Colors.ENDC)
            time.sleep(3)
            
        elif msg_type == 'audience_poll':
            print(Colors.CYAN + "\n[Kết quả từ khán phòng]:" + Colors.ENDC)
            for option, percent in server_data['poll_data'].items():
                print(f"  - Phương án {option}: {percent}%")
            time.sleep(3)

        elif msg_type == 'game_over':
            clear_screen()
            print(Colors.FAIL + Colors.BOLD + "\nRất tiếc! Bạn đã trả lời sai." + Colors.ENDC)
            print(f"Đáp án đúng là: {Colors.GREEN}{server_data['correct_answer']}{Colors.ENDC}")
            print(f"Bạn ra về với số tiền thưởng là: {Colors.BOLD}{server_data['prize']} VNĐ{Colors.ENDC}")
            game_running = False

        elif msg_type == 'win':
            clear_screen()
            print(Colors.HEADER + Colors.BOLD + "\n" + "*"*50)
            print("CHÚC MỪNG! BẠN ĐÃ TRỞ THÀNH TRIỆU PHÚ!".center(60))
            print(f"BẠN LÀ NGƯỜI CHIẾN THẮNG VỚI GIẢI THƯỞNG {server_data['prize']} VNĐ!".center(60))
            print("*"*50 + Colors.ENDC)
            game_running = False
    
    client_socket.close()
    print("\nCảm ơn bạn đã tham gia chương trình!")

if __name__ == "__main__":
    main()