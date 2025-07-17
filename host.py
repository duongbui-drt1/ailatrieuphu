import socket
import json
import random
import time
import threading

# --- CẤU HÌNH SERVER ---
HOST = '0.0.0.0'
PORT = 65432
BUFFER_SIZE = 4096

# --- DỮ LIỆU GAME ---
QUESTIONS = []
PRIZE_LEVELS = [
    "200.000", "400.000", "600.000", "1.000.000", "2.000.000", "3.000.000", 
    "6.000.000", "10.000.000", "14.000.000", "22.000.000", "30.000.000", 
    "40.000.000", "60.000.000", "85.000.000", "150.000.000"
]

# --- BIẾN TOÀN CỤC ĐỂ QUẢN LÝ ---
client_connection = None
stop_thread_flag = False

def load_questions():
    global QUESTIONS
    try:
        with open('questions.json', 'r', encoding='utf-8') as f:
            QUESTIONS = json.load(f)
        print(f"[INFO] Đã tải thành công {len(QUESTIONS)} câu hỏi.")
    except Exception as e:
        print(f"[ERROR] Lỗi khi tải câu hỏi: {e}")
        exit()

def send_data(conn, data):
    if conn:
        try:
            conn.sendall(json.dumps(data).encode('utf-8'))
        except socket.error as e:
            print(f"[ERROR] Lỗi khi gửi dữ liệu: {e}")

def receive_data(conn):
    try:
        raw_data = conn.recv(BUFFER_SIZE)
        if not raw_data: return None
        return json.loads(raw_data.decode('utf-8'))
    except (socket.error, json.JSONDecodeError):
        return None

def handle_host_commands():
    global client_connection, stop_thread_flag
    print("[HOST] Gõ lệnh và nhấn Enter để điều khiển client (vd: /mute, /beta on)")
    while not stop_thread_flag:
        try:
            command = input()
            if not client_connection:
                print("[HOST] Chưa có người chơi nào kết nối.")
                continue
            if command.lower() == '/mute':
                print("[HOST] Đã gửi lệnh TẮT NHẠC cho người chơi.")
                send_data(client_connection, {'type': 'set_mute', 'value': True})
            elif command.lower() == '/unmute':
                print("[HOST] Đã gửi lệnh MỞ NHẠC cho người chơi.")
                send_data(client_connection, {'type': 'set_mute', 'value': False})
            elif command.lower() == '/beta on':
                print("[HOST] Đã BẬT chế độ BETA cho người chơi.")
                send_data(client_connection, {'type': 'set_beta', 'value': True})
            elif command.lower() == '/beta off':
                print("[HOST] Đã TẮT chế độ BETA cho người chơi.")
                send_data(client_connection, {'type': 'set_beta', 'value': False})
            else:
                print("[HOST] Lệnh không hợp lệ. Dùng: /mute, /unmute, /beta on, /beta off")
        except (EOFError, KeyboardInterrupt):
            break

def handle_lifeline_5050(question):
    correct_answer = question['answer']
    incorrect_keys = [k for k in question['options'] if k != correct_answer]
    to_remove = random.sample(incorrect_keys, 2)
    new_options = question['options'].copy()
    for key in to_remove: new_options[key] = ""
    return new_options

def handle_lifeline_audience(question):
    keys = list(question['options'].keys())
    probs = {key: random.randint(5, 15) for key in keys}
    probs[question['answer']] += 100 - sum(probs.values())
    return probs

def handle_client(conn, addr):
    global client_connection
    client_connection = conn
    player_name, player_id = "N/A", "N/A"
    
    try:
        player_info = receive_data(conn)
        player_name = player_info.get('name', 'Ẩn danh')
        player_id = player_info.get('id', 'N/A')
        print(f"\n[CONNECTION] Kết nối mới từ {addr} | Tên: {player_name} | ID: {player_id}")

        game_state = {
            'level': 0,
            'lifelines': {'5050': True, 'audience': True, 'call': True, 'wise_man': True},
            'prize': "0", 'milestone_prize': "0", 'is_beta': False
        }

        while game_state['level'] < len(QUESTIONS):
            current_level = game_state['level']
            question_data = QUESTIONS[current_level]
            
            packet_to_client = {
                'type': 'question', 'question': question_data['question'],
                'options': question_data['options'], 'level': current_level + 1,
                'prize': PRIZE_LEVELS[current_level], 'lifelines': game_state['lifelines']
            }
            send_data(conn, packet_to_client)
            
            client_response = receive_data(conn)
            if not client_response: break

            action = client_response.get('action')
            if action == 'lifeline':
                lifeline_type = client_response.get('value')
                if lifeline_type == '5050' and game_state['lifelines']['5050']:
                    game_state['lifelines']['5050'] = False
                    packet_to_client['options'] = handle_lifeline_5050(question_data)
                elif lifeline_type == 'audience' and game_state['lifelines']['audience']:
                    game_state['lifelines']['audience'] = False
                    send_data(conn, {'type': 'audience_poll', 'poll_data': handle_lifeline_audience(question_data)})
                    time.sleep(0.1)
                elif lifeline_type == 'call' and game_state['lifelines']['call']:
                    game_state['lifelines']['call'] = False
                    advice = f"Chuyên gia khuyên chọn đáp án {question_data['answer']}" if random.random() > 0.15 else "Chuyên gia không chắc chắn lắm."
                    send_data(conn, {'type': 'info', 'message': advice})
                    time.sleep(0.1)
                elif lifeline_type == 'wise_man' and game_state['lifelines']['wise_man'] and game_state['level'] >= 4:
                    game_state['lifelines']['wise_man'] = False
                    print("\n" + "="*50)
                    print("!!! NGƯỜI CHƠI YÊU CẦU TRỢ GIÚP TỪ NHÀ THÔNG THÁI (HOST) !!!")
                    print(f"Câu hỏi: {question_data['question']}\nĐáp án đúng là: {question_data['answer']}")
                    suggestion = input("-> Nhập gợi ý của bạn cho người chơi: ")
                    send_data(conn, {'type': 'info', 'message': f"Nhà thông thái gợi ý: {suggestion}"})
                    print("="*50 + "\n")
                    time.sleep(0.1)
                continue

            player_answer = client_response.get('value')
            correct_answer = question_data['answer']
            is_correct = player_answer and player_answer.upper() == correct_answer
            ping = (time.time() - client_response.get('timestamp', time.time())) * 1000

            print(f"\n[GAME] Câu {current_level + 1}: {player_name} trả lời '{player_answer}'.")
            print(f"       -> Đáp án đúng: '{correct_answer}'. Kết quả: {'ĐÚNG' if is_correct else 'SAI'}.")
            print(f"       -> Tiền thưởng hiện tại: {game_state['prize']} VNĐ.")

            if is_correct:
                game_state['prize'] = PRIZE_LEVELS[current_level]
                if current_level + 1 in [5, 10, 15]: game_state['milestone_prize'] = game_state['prize']
                game_state['level'] += 1
                send_data(conn, {'type': 'result', 'correct': True, 'correct_answer': correct_answer, 'prize': game_state['prize'], 'ping': ping})
                if game_state['level'] == len(QUESTIONS):
                    send_data(conn, {'type': 'win', 'prize': PRIZE_LEVELS[-1]})
                    print(f"\n[WINNER] {player_name} ĐÃ CHIẾN THẮNG!!!")
                    break
                time.sleep(3)
            else:
                send_data(conn, {'type': 'result', 'correct': False, 'correct_answer': correct_answer, 'prize': game_state['milestone_prize'], 'ping': ping})
                print(f"[GAME OVER] {player_name} đã thua cuộc.")
                break
    except (ConnectionResetError, BrokenPipeError, json.JSONDecodeError):
        print(f"\n[CONNECTION] Người chơi {player_name} đã ngắt kết nối.")
    finally:
        print(f"[CONNECTION] Đóng kết nối với {player_name}.")
        conn.close()
        client_connection = None

def main():
    global stop_thread_flag
    load_questions()
    host_thread = threading.Thread(target=handle_host_commands, daemon=True)
    host_thread.start()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname_ex(hostname)[-1][-1] if socket.gethostbyname_ex(hostname)[-1] else "127.0.0.1"

        print("+" + "-"*60 + "+")
        print(f"| {'SERVER AI LÀ TRIỆU PHÚ 3.0':^60} |")
        print(f"| {'Lắng nghe trên:':<15} {local_ip}:{PORT}{'':>29} |")
        print("+" + "-"*60 + "+")
        print("[INFO] Đang chờ người chơi kết nối...")

        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()
    except OSError as e:
        print(f"[ERROR] Lỗi khi khởi động server: {e}")
    finally:
        stop_thread_flag = True
        print("\n[INFO] Đang đóng server... Nhấn Enter để thoát.")
        server_socket.close()

if __name__ == "__main__":
    main()