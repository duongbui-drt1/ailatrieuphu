import socket
import json
import random
import time
import threading
import os

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

# --- BIẾN TOÀN CỤC ---
player_conn = None
viewer_sockets = []
game_update_callback = None 
connections_lock = threading.Lock()
is_game_paused = False
current_game_state_packet = None

def set_game_update_callback(callback):
    global game_update_callback
    game_update_callback = callback

def update_host_gui(data):
    if game_update_callback:
        game_update_callback(data)

def broadcast(data):
    with connections_lock:
        all_conns = ([player_conn] if player_conn else []) + list(viewer_sockets)
        if not all_conns: return
        encoded_data = (json.dumps(data) + '\n').encode('utf-8')
        failed_conns = []
        for conn in all_conns:
            try:
                conn.sendall(encoded_data)
            except (socket.error, BrokenPipeError):
                failed_conns.append(conn)
        for conn in failed_conns:
            if conn in viewer_sockets:
                viewer_sockets.remove(conn)

def send_to_one(conn, data):
    try:
        encoded_data = (json.dumps(data) + '\n').encode('utf-8')
        conn.sendall(encoded_data)
    except (socket.error, BrokenPipeError):
        pass

def load_random_question_pack():
    global QUESTIONS
    try:
        question_files = [f for f in os.listdir('.') if f.startswith('questions_') and f.endswith('.json')]
        if not question_files:
            if os.path.exists('questions.json'):
                question_files.append('questions.json')
            else:
                update_host_gui({'type': 'log', 'message': "LỖI: Không tìm thấy gói câu hỏi nào."})
                return False
        
        chosen_pack = random.choice(question_files)
        with open(chosen_pack, 'r', encoding='utf-8') as f:
            QUESTIONS = json.load(f)
        update_host_gui({'type': 'log', 'message': f"Đã tải ngẫu nhiên gói câu hỏi: '{chosen_pack}'."})
        return True
    except Exception as e:
        update_host_gui({'type': 'log', 'message': f"LỖI: Không thể tải gói câu hỏi. Lý do: {e}"})
        return False

def handle_lifeline_5050(question):
    correct_answer = question['answer']
    incorrect_keys = [k for k in question['options'] if k != correct_answer]
    to_remove = random.sample(incorrect_keys, 2)
    new_options = question['options'].copy()
    for key in to_remove:
        new_options[key] = ""
    return new_options

def handle_client(conn, addr):
    global player_conn, current_game_state_packet
    player_name, player_id = "N/A", "N/A"
    
    try:
        player_info = json.loads(conn.recv(BUFFER_SIZE).decode('utf-8'))
        player_name = player_info.get('name', 'Ẩn danh')
        player_id = player_info.get('id', 'N/A')
        update_host_gui({'type': 'connect', 'name': player_name, 'id': player_id, 'addr': addr})

        game_state = {'level': 0, 'lifelines': {'5050': True, 'audience': True, 'call': True, 'wise_man': True}, 'prize': "0", 'milestone_prize': "0"}

        while game_state['level'] < len(QUESTIONS):
            while is_game_paused:
                time.sleep(0.5)

            current_level = game_state['level']
            q_data = QUESTIONS[current_level]
            current_q_options = q_data['options'].copy()
            update_host_gui({'type': 'game_state', 'level': current_level + 1, 'prize': game_state['prize']})
            
            broadcast({'type': 'ask_ready', 'level': current_level + 1})
            ready_response_data = conn.recv(BUFFER_SIZE)
            if not ready_response_data: raise ConnectionError("Client ngắt kết nối khi chờ sẵn sàng")
            ready_response = json.loads(ready_response_data.decode('utf-8'))
            if not ready_response.get('ready'): raise ConnectionError("Client không sẵn sàng")

            while True: 
                current_game_state_packet = {
                    'type': 'question', 'question': q_data['question'], 'options': current_q_options,
                    'level': current_level + 1, 'prize': PRIZE_LEVELS[current_level], 'lifelines': game_state['lifelines']
                }
                broadcast(current_game_state_packet)
                
                response_data = conn.recv(BUFFER_SIZE)
                if not response_data: raise ConnectionError("Client ngắt kết nối khi đang chơi")
                response = json.loads(response_data.decode('utf-8'))
                
                action = response.get('action')
                if action == 'answer':
                    break
                elif action == 'lifeline':
                    lifeline_type = response.get('value')
                    update_host_gui({'type': 'log', 'message': f"Người chơi dùng trợ giúp: {lifeline_type.upper()}"})
                    
                    if lifeline_type == '5050' and game_state['lifelines']['5050']:
                        game_state['lifelines']['5050'] = False
                        current_q_options = handle_lifeline_5050(q_data)
                    elif lifeline_type == 'audience' and game_state['lifelines']['audience']:
                        game_state['lifelines']['audience'] = False
                        update_host_gui({'type': 'audience_request'})
                    elif lifeline_type == 'call' and game_state['lifelines']['call']:
                        game_state['lifelines']['call'] = False
                        advice = f"Chuyên gia khuyên chọn đáp án {q_data['answer']}" if random.random() > 0.15 else "Chuyên gia không chắc chắn lắm."
                        broadcast({'type': 'lifeline_result', 'lifeline': 'call', 'message': advice})
                    elif lifeline_type == 'wise_man' and game_state['lifelines']['wise_man'] and game_state['level'] >= 5:
                        game_state['lifelines']['wise_man'] = False
                        update_host_gui({'type': 'wise_man_request', 'question': q_data['question'], 'answer': q_data['answer']})
            
            player_answer = response.get('value')
            correct_answer = q_data['answer']
            is_correct = player_answer and player_answer.upper() == correct_answer
            ping = (time.time() - response.get('timestamp', time.time())) * 1000
            
            update_host_gui({'type': 'answer', 'player_answer': player_answer, 'correct_answer': correct_answer, 'is_correct': is_correct})
            broadcast({'type': 'result', 'correct': is_correct, 'correct_answer': correct_answer, 'player_answer': player_answer, 'ping': ping})

            if is_correct:
                game_state['prize'] = PRIZE_LEVELS[current_level]
                if current_level + 1 in [5, 10, 15]:
                    game_state['milestone_prize'] = game_state['prize']
                game_state['level'] += 1
                if game_state['level'] == len(QUESTIONS):
                    time.sleep(4)
                    broadcast({'type': 'win', 'prize': PRIZE_LEVELS[-1]})
                    update_host_gui({'type': 'log', 'message': f"{player_name} ĐÃ TRỞ THÀNH TRIỆU PHÚ!"})
                    break
                time.sleep(4)
            else:
                time.sleep(4)
                broadcast({'type': 'game_over', 'prize': game_state['milestone_prize']})
                update_host_gui({'type': 'log', 'message': f"{player_name} đã thua cuộc."})
                break
    except (ConnectionError, ConnectionResetError, BrokenPipeError, json.JSONDecodeError, AttributeError) as e:
        update_host_gui({'type': 'log', 'message': f"Người chơi '{player_name}' đã ngắt kết nối: {e}"})
    finally:
        broadcast({'type': 'game_ended_waiting'})
        update_host_gui({'type': 'disconnect'})
        if conn:
            conn.close()
        with connections_lock:
            player_conn = None
            current_game_state_packet = None

def start_server_logic():
    global player_conn
    if not load_random_question_pack():
        return
        
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname_ex(hostname)[-1][-1]
        except:
            local_ip = "127.0.0.1"
        update_host_gui({'type': 'log', 'message': f"Server đang lắng nghe trên {local_ip}:{PORT}"})

        while True:
            conn, addr = server_socket.accept()
            with connections_lock:
                if not player_conn:
                    player_conn = conn
                    client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                    client_thread.start()
                else:
                    viewer_sockets.append(conn)
                    update_host_gui({'type': 'log', 'message': f"Khán giả mới đã kết nối từ {addr}"})
                    if current_game_state_packet:
                        send_to_one(conn, current_game_state_packet)
    except OSError as e:
        update_host_gui({'type': 'log', 'message': f"LỖI SERVER: {e}."})
    finally:
        update_host_gui({'type': 'log', 'message': "Server đã đóng."})
        server_socket.close()