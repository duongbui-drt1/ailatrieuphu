import socket
import json
import random
import time
import threading

from resources import question_pack_paths

# --- CẤU HÌNH SERVER ---
HOST = '0.0.0.0'
PORT = 65432
BUFFER_SIZE = 4096

# --- DỮ LIỆU GAME ---
QUESTIONS = []
PRIZE_LEVELS = [
    "1.000.000", "2.000.000", "3.000.000", "4.000.000", "5.000.000",
    "6.000.000", "8.000.000", "10.000.000", "14.000.000", "22.000.000",
    "30.000.000", "60.000.000", "120.000.000", "250.000.000", "500.000.000"
]
READY_REQUIRED_FROM_LEVEL = 6
LOSS_GUARANTEE_FROM_LEVEL_6 = "5.000.000"
LOSS_GUARANTEE_FROM_LEVEL_11 = "22.000.000"

# --- BIẾN TOÀN CỤC ---
player_conn = None
viewer_sockets = []
game_update_callback = None
connections_lock = threading.Lock()
is_game_paused = False
current_game_state_packet = None
current_viewer_scene_packet = None
current_question_index = None
active_question_pack_path = None
current_stats = {
    'questions_seen': 0,
    'correct_answers': 0,
    'wrong_answers': 0,
    'lifelines_used': 0,
    'fastest_ping': None,
}
host_ready_event = threading.Event()
host_answer_confirm_event = threading.Event()
host_control_lock = threading.Lock()
waiting_for_ready_level = 0
pending_answer = None
pending_answer_level = 0

CREDIT_LINES = [
    "CHƯƠNG TRÌNH ĐƯỢC ĐẦU TƯ VÀ SẢN XUẤT BỞI DULI PRODUCTION LLC.",
    "",
    "Đạo diễn chương trình: Duong Bui",
    "",
    "Dẫn chương trình: MC Hải Dương",
    "",
    "Kỹ thuật hình ảnh - âm thanh - mạng LAN: Duli Production Team, Duli Studio",
    "",
    "Biên tập câu hỏi và kiểm duyệt nội dung: Duli Production Team",
    "",
    "Đội ngũ hỗ trợ kỹ thuật và vận hành: Hoàng Long",
    "",
    "Đội ngũ thiết kế đồ họa và hiệu ứng: Duli Studio",
    "",
    "Âm nhạc nền: Bùi Công Duy, Nguyễn Hữu Phúc, Nguyễn Văn Huy",
    "",
    "Đội ngũ truyền thông và marketing: Duli Production Team",
    "",
    "Đội ngũ sản xuất và hậu kỳ: Duli Production Team",
    "",
    "Đặc biệt cảm ơn sự ủng hộ của khán giả và người chơi đã làm nên thành công của chương trình Ai Là Triệu Phú!",
    "",
    "Mọi thắc mắc về chương trình và đăng ký tham gia xin vui lòng liên hệ:",
    "",
    "Email: dulicontact.ctme@gmail.com",
    "",
    "Fanpage: https://www.facebook.com/duliproduction",
    "",
    "Copyright © 2026 Duli Production LLC & Sony Pictures. All rights reserved.",
]

def set_game_update_callback(callback):
    global game_update_callback
    game_update_callback = callback

def update_host_gui(data):
    if data.get('type') == 'ready_waiting' and not needs_ready_confirmation(data.get('level', 0)):
        return
    if game_update_callback:
        game_update_callback(data)

def broadcast(data):
    if data.get('type') == 'ask_ready' and not needs_ready_confirmation(data.get('level', 0)):
        return
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

def broadcast_to_viewers(data):
    with connections_lock:
        failed_conns = []
        encoded_data = (json.dumps(data) + '\n').encode('utf-8')
        for conn in list(viewer_sockets):
            try:
                conn.sendall(encoded_data)
            except (socket.error, BrokenPipeError):
                failed_conns.append(conn)
        for conn in failed_conns:
            if conn in viewer_sockets:
                viewer_sockets.remove(conn)

def force_ready_from_host():
    with host_control_lock:
        can_force = waiting_for_ready_level > 0
    if can_force:
        host_ready_event.set()
    return can_force

def confirm_locked_answer_from_host():
    with host_control_lock:
        can_confirm = pending_answer is not None and pending_answer_level >= 6
    if can_confirm:
        host_answer_confirm_event.set()
    return can_confirm

def cancel_locked_answer_from_host():
    with host_control_lock:
        can_cancel = pending_answer is not None
        level = pending_answer_level
    if can_cancel:
        clear_pending_answer()
        broadcast({'type': 'answer_unlocked', 'level': level})
        update_host_gui({'type': 'log', 'message': f"Host đã hủy đáp án đã chốt ở câu {level}."})
    return can_cancel

def resend_current_state_from_host():
    resent = False
    if current_game_state_packet:
        broadcast(current_game_state_packet)
        resent = True
    with host_control_lock:
        answer = pending_answer
        level = pending_answer_level
    if answer:
        broadcast({
            'type': 'answer_locked',
            'player_answer': answer,
            'level': level,
            'requires_host_confirm': level >= 6,
        })
        resent = True
    if current_viewer_scene_packet:
        broadcast_to_viewers(current_viewer_scene_packet)
        resent = True
    return resent

def set_viewer_scene(scene, title="", message="", countdown_seconds=0, payload=None, sound=None, sound_loop=False):
    global current_viewer_scene_packet
    current_viewer_scene_packet = {
        'type': 'viewer_scene',
        'scene': scene,
        'title': title,
        'message': message,
        'countdown_seconds': countdown_seconds,
        'payload': payload or {},
        'sound': sound,
        'sound_loop': sound_loop,
        'stats': current_stats,
        'timestamp': time.time(),
    }
    broadcast_to_viewers(current_viewer_scene_packet)
    return True

def show_game_scene_from_host():
    global current_viewer_scene_packet
    current_viewer_scene_packet = None
    if current_game_state_packet:
        broadcast_to_viewers({'type': 'viewer_scene', 'scene': 'game', 'sound': 'viewer_game', 'sound_loop': False})
        return True
    set_viewer_scene('standby', 'AI LÀ TRIỆU PHÚ', 'Đang chờ thí sinh bắt đầu...')
    return False

def reset_viewers_from_host():
    global current_viewer_scene_packet
    current_viewer_scene_packet = None
    broadcast_to_viewers({'type': 'viewer_reset'})
    return True

def play_client_music_from_host(name):
    broadcast({'type': 'play_music', 'name': name, 'loop': True})
    return True

def stop_client_music_from_host():
    broadcast({'type': 'stop_music'})
    return True

def play_effect_from_host(name):
    broadcast({'type': 'play_effect', 'name': name})
    return True

def end_program_from_host():
    global is_game_paused
    is_game_paused = True
    broadcast({'type': 'game_paused', 'paused': True, 'reason': 'program_end'})
    set_viewer_scene(
        'credits',
        'AI LÀ TRIỆU PHÚ',
        '',
        payload={'lines': CREDIT_LINES, 'mode': 'program_end'},
        sound='viewer_credits',
        sound_loop=True,
    )
    return True

def get_current_question_snapshot():
    if current_question_index is None or current_game_state_packet is None:
        return None
    question = QUESTIONS[current_question_index]
    return {
        'index': current_question_index,
        'level': current_question_index + 1,
        'question': question.get('question', ''),
        'options': question.get('options', {}).copy(),
        'answer': question.get('answer', ''),
        'prize': current_game_state_packet.get('prize', ''),
    }

def update_current_question_from_host(question, options, answer):
    global current_game_state_packet
    if current_question_index is None or current_game_state_packet is None:
        return False
    normalized_answer = answer.strip().upper()
    if normalized_answer not in ['A', 'B', 'C', 'D']:
        return False

    updated_question = {
        'level': current_question_index + 1,
        'question': question.strip(),
        'options': {key: options[key].strip() for key in ['A', 'B', 'C', 'D']},
        'answer': normalized_answer,
    }
    QUESTIONS[current_question_index].clear()
    QUESTIONS[current_question_index].update(updated_question)
    current_game_state_packet = {
        **current_game_state_packet,
        'question': QUESTIONS[current_question_index]['question'],
        'options': QUESTIONS[current_question_index]['options'].copy(),
    }
    broadcast(current_game_state_packet)
    update_host_gui({'type': 'log', 'message': f"Host đã cập nhật câu {current_question_index + 1}."})
    return True

def swap_current_question_from_host():
    if current_question_index is None:
        return False
    level = current_question_index + 1
    current_text = QUESTIONS[current_question_index].get('question', '')
    candidates = []
    for pack_path in question_pack_paths():
        try:
            with open(pack_path, 'r', encoding='utf-8') as file:
                pack_questions = json.load(file)
        except Exception:
            continue
        for question in pack_questions:
            if question.get('level') == level and question.get('question') != current_text:
                candidates.append(question)
    if not candidates:
        return False
    chosen = random.choice(candidates)
    return update_current_question_from_host(
        chosen['question'],
        chosen['options'],
        chosen['answer'],
    )

def get_interactive_poll_questions(count=3):
    current_text = ""
    if current_question_index is not None and 0 <= current_question_index < len(QUESTIONS):
        current_text = QUESTIONS[current_question_index].get('question', '')

    pack_paths = question_pack_paths()
    inactive_packs = []
    for pack_path in pack_paths:
        if active_question_pack_path is None:
            inactive_packs.append(pack_path)
            continue
        try:
            if pack_path.resolve() != active_question_pack_path.resolve():
                inactive_packs.append(pack_path)
        except OSError:
            inactive_packs.append(pack_path)

    candidates = []
    for pack_path in inactive_packs or pack_paths:
        try:
            with open(pack_path, 'r', encoding='utf-8') as file:
                pack_questions = json.load(file)
        except Exception:
            continue

        for question in pack_questions:
            text = str(question.get('question', '')).strip()
            options = question.get('options', {})
            if not text or text == current_text or not isinstance(options, dict):
                continue
            if not all(str(options.get(key, '')).strip() for key in ['A', 'B', 'C', 'D']):
                continue
            candidates.append({
                'level': question.get('level', 0),
                'question': text,
                'options': {key: str(options.get(key, '')).strip() for key in ['A', 'B', 'C', 'D']},
            })

    random.shuffle(candidates)
    return candidates[:count]

def set_waiting_for_ready(level):
    global waiting_for_ready_level
    with host_control_lock:
        waiting_for_ready_level = level if needs_ready_confirmation(level) else 0
    if not needs_ready_confirmation(level):
        host_ready_event.set()

def clear_waiting_for_ready():
    global waiting_for_ready_level
    with host_control_lock:
        waiting_for_ready_level = 0
    host_ready_event.clear()

def set_pending_answer(answer, level):
    global pending_answer, pending_answer_level
    with host_control_lock:
        pending_answer = answer
        pending_answer_level = level

def clear_pending_answer():
    global pending_answer, pending_answer_level
    with host_control_lock:
        pending_answer = None
        pending_answer_level = 0
    host_answer_confirm_event.clear()

def needs_ready_confirmation(level):
    return level >= READY_REQUIRED_FROM_LEVEL

def final_prize_on_wrong(level, current_prize):
    if level >= 11:
        return LOSS_GUARANTEE_FROM_LEVEL_11
    if level >= 6:
        return LOSS_GUARANTEE_FROM_LEVEL_6
    return "0"

def load_random_question_pack():
    global QUESTIONS, active_question_pack_path
    try:
        question_files = question_pack_paths()
        if not question_files:
            update_host_gui({'type': 'log', 'message': "LỖI: Không tìm thấy gói câu hỏi nào."})
            return False

        chosen_pack = random.choice(question_files)
        with open(chosen_pack, 'r', encoding='utf-8') as f:
            QUESTIONS = json.load(f)
        active_question_pack_path = chosen_pack
        update_host_gui({'type': 'log', 'message': f"Đã tải ngẫu nhiên gói câu hỏi: '{chosen_pack.name}'."})
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

def receive_initial_packet(conn):
    previous_timeout = conn.gettimeout()
    conn.settimeout(5)
    try:
        raw_data = conn.recv(BUFFER_SIZE)
        if not raw_data:
            raise ConnectionError("Client không gửi gói định danh.")
    finally:
        conn.settimeout(previous_timeout)

    message = raw_data.decode('utf-8').strip()
    if '\n' in message:
        message = message.split('\n', 1)[0]
    return json.loads(message)

def receive_json_message(conn, buffer, timeout=None):
    previous_timeout = conn.gettimeout()
    if timeout is not None:
        conn.settimeout(timeout)

    try:
        while True:
            if '\n' in buffer:
                message, buffer = buffer.split('\n', 1)
                return json.loads(message), buffer

            if buffer:
                try:
                    return json.loads(buffer), ""
                except json.JSONDecodeError:
                    pass

            try:
                raw_data = conn.recv(BUFFER_SIZE)
            except socket.timeout:
                if timeout is not None:
                    return None, buffer
                raise

            if not raw_data:
                raise ConnectionError("Client ngắt kết nối.")
            buffer += raw_data.decode('utf-8')
    finally:
        if timeout is not None:
            conn.settimeout(previous_timeout)

def handle_client(conn, addr, player_info):
    global player_conn, current_game_state_packet, current_question_index
    player_name, player_id = "N/A", "N/A"
    game_finished_normally = False

    try:
        player_name = player_info.get('name', 'Ẩn danh')
        player_id = player_info.get('id', 'N/A')
        update_host_gui({'type': 'connect', 'name': player_name, 'id': player_id, 'addr': addr})
        current_stats.update({
            'questions_seen': 0,
            'correct_answers': 0,
            'wrong_answers': 0,
            'lifelines_used': 0,
            'fastest_ping': None,
        })

        game_state = {'level': 0, 'lifelines': {'5050': True, 'audience': True, 'call': True, 'wise_man': True}, 'prize': "0", 'milestone_prize': "0"}
        client_buffer = ""

        while game_state['level'] < len(QUESTIONS):
            while is_game_paused:
                time.sleep(0.5)

            current_level = game_state['level']
            current_question_index = current_level
            q_data = QUESTIONS[current_level]
            current_q_options = q_data['options'].copy()
            update_host_gui({'type': 'game_state', 'level': current_level + 1, 'prize': game_state['prize']})

            broadcast({'type': 'ask_ready', 'level': current_level + 1})
            set_waiting_for_ready(current_level + 1)
            update_host_gui({'type': 'ready_waiting', 'level': current_level + 1})
            while True:
                if not needs_ready_confirmation(current_level + 1):
                    break
                while is_game_paused:
                    time.sleep(0.5)

                if host_ready_event.is_set():
                    update_host_gui({'type': 'log', 'message': f"Host đã xác nhận bắt đầu câu {current_level + 1}."})
                    break

                ready_response, client_buffer = receive_json_message(conn, client_buffer, timeout=0.25)
                if ready_response is None:
                    continue
                if not ready_response.get('ready'):
                    raise ConnectionError("Client không sẵn sàng")
                break
            clear_waiting_for_ready()
            update_host_gui({'type': 'ready_cleared'})

            needs_question_broadcast = True
            locked_answer = None
            locked_answer_timestamp = time.time()
            clear_pending_answer()
            while True:
                if needs_question_broadcast:
                    current_game_state_packet = {
                        'type': 'question', 'question': q_data['question'], 'options': current_q_options,
                        'level': current_level + 1, 'prize': PRIZE_LEVELS[current_level], 'lifelines': game_state['lifelines']
                    }
                    broadcast(current_game_state_packet)
                    update_host_gui({'type': 'question_live', 'level': current_level + 1})
                    current_stats['questions_seen'] = max(current_stats['questions_seen'], current_level + 1)
                    needs_question_broadcast = False

                if locked_answer and current_level + 1 >= 6 and host_answer_confirm_event.is_set():
                    response = {
                        'action': 'answer',
                        'value': locked_answer,
                        'timestamp': locked_answer_timestamp,
                        'confirmed_by_host': True,
                    }
                    update_host_gui({'type': 'log', 'message': f"Host công bố đáp án {locked_answer} cho câu {current_level + 1}."})
                    break

                response, client_buffer = receive_json_message(conn, client_buffer, timeout=0.25)
                if response is None:
                    continue

                action = response.get('action')
                if action == 'answer':
                    if current_level + 1 >= 6 and not response.get('confirmed_by_host'):
                        locked_answer = response.get('value')
                        locked_answer_timestamp = response.get('timestamp', time.time())
                        set_pending_answer(locked_answer, current_level + 1)
                        update_host_gui({
                            'type': 'answer_locked',
                            'player_answer': locked_answer,
                            'level': current_level + 1,
                            'requires_host_confirm': True,
                        })
                        broadcast({
                            'type': 'answer_locked',
                            'player_answer': locked_answer,
                            'level': current_level + 1,
                            'requires_host_confirm': True,
                        })
                        continue
                    break
                elif action == 'answer_locked':
                    locked_answer = response.get('value')
                    locked_answer_timestamp = response.get('timestamp', time.time())
                    requires_host_confirm = current_level + 1 >= 6
                    if requires_host_confirm:
                        set_pending_answer(locked_answer, current_level + 1)
                    update_host_gui({
                        'type': 'answer_locked',
                        'player_answer': locked_answer,
                        'level': current_level + 1,
                        'requires_host_confirm': requires_host_confirm,
                    })
                    broadcast({
                        'type': 'answer_locked',
                        'player_answer': locked_answer,
                        'level': current_level + 1,
                        'requires_host_confirm': requires_host_confirm,
                    })
                elif action == 'lifeline':
                    lifeline_type = response.get('value')
                    update_host_gui({'type': 'log', 'message': f"Người chơi dùng trợ giúp: {lifeline_type.upper()}"})
                    current_stats['lifelines_used'] += 1

                    if lifeline_type == '5050' and game_state['lifelines']['5050']:
                        game_state['lifelines']['5050'] = False
                        current_q_options = handle_lifeline_5050(q_data)
                        needs_question_broadcast = True
                    elif lifeline_type == 'audience' and game_state['lifelines']['audience']:
                        game_state['lifelines']['audience'] = False
                        update_host_gui({'type': 'audience_request'})
                    elif lifeline_type == 'call' and game_state['lifelines']['call']:
                        game_state['lifelines']['call'] = False
                        update_host_gui({
                            'type': 'call_request',
                            'question': q_data['question'],
                            'answer': q_data['answer'],
                        })
                    elif lifeline_type == 'wise_man' and game_state['lifelines']['wise_man'] and game_state['level'] >= 5:
                        game_state['lifelines']['wise_man'] = False
                        wrong_answers = [key for key in q_data['options'] if key != q_data['answer']]
                        suggested_answer = q_data['answer'] if random.random() < 0.5 else random.choice(wrong_answers)
                        advice = f"Tổ tư vấn nghiêng về đáp án {suggested_answer}"
                        broadcast({'type': 'lifeline_result', 'lifeline': 'wise_man', 'message': advice})
                        update_host_gui({'type': 'log', 'message': f"Tổ tư vấn đã gợi ý đáp án {suggested_answer}."})

            player_answer = response.get('value')
            clear_pending_answer()
            if player_answer and player_answer != locked_answer:
                broadcast({
                    'type': 'answer_locked',
                    'player_answer': player_answer,
                    'level': current_level + 1,
                    'requires_host_confirm': False,
                })
            correct_answer = q_data['answer']
            is_correct = player_answer and player_answer.upper() == correct_answer
            ping = (time.time() - response.get('timestamp', time.time())) * 1000
            if current_stats['fastest_ping'] is None or ping < current_stats['fastest_ping']:
                current_stats['fastest_ping'] = ping

            update_host_gui({'type': 'answer', 'player_answer': player_answer, 'correct_answer': correct_answer, 'is_correct': is_correct})
            broadcast({'type': 'result', 'correct': is_correct, 'correct_answer': correct_answer, 'player_answer': player_answer, 'ping': ping})

            if is_correct:
                current_stats['correct_answers'] += 1
                game_state['prize'] = PRIZE_LEVELS[current_level]
                if current_level + 1 in [5, 10, 15]:
                    game_state['milestone_prize'] = game_state['prize']
                game_state['level'] += 1
                if game_state['level'] == len(QUESTIONS):
                    time.sleep(4)
                    game_finished_normally = True
                    broadcast({'type': 'win', 'prize': PRIZE_LEVELS[-1], 'player_name': player_name})
                    update_host_gui({'type': 'log', 'message': f"{player_name} ĐÃ TRỞ THÀNH TRIỆU PHÚ!"})
                    break
                time.sleep(4)
            else:
                current_stats['wrong_answers'] += 1
                time.sleep(4)
                final_prize = final_prize_on_wrong(current_level + 1, game_state['prize'])
                game_finished_normally = True
                broadcast({'type': 'game_over', 'prize': final_prize, 'player_name': player_name, 'level': current_level + 1})
                update_host_gui({'type': 'log', 'message': f"{player_name} đã thua cuộc."})
                break
    except (ConnectionError, ConnectionResetError, BrokenPipeError, json.JSONDecodeError, AttributeError) as e:
        update_host_gui({'type': 'log', 'message': f"Người chơi '{player_name}' đã ngắt kết nối: {e}"})
    finally:
        clear_waiting_for_ready()
        clear_pending_answer()
        if not game_finished_normally:
            broadcast({'type': 'game_ended_waiting'})
        update_host_gui({'type': 'disconnect'})
        if conn:
            conn.close()
        with connections_lock:
            player_conn = None
            current_game_state_packet = None
            current_question_index = None

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
            try:
                initial_packet = receive_initial_packet(conn)
            except (ConnectionError, json.JSONDecodeError, UnicodeDecodeError, socket.timeout) as e:
                update_host_gui({'type': 'log', 'message': f"Từ chối kết nối không hợp lệ từ {addr}: {e}"})
                conn.close()
                continue

            with connections_lock:
                if initial_packet.get('type') == 'viewer':
                    viewer_sockets.append(conn)
                    update_host_gui({'type': 'log', 'message': f"Khán giả mới đã kết nối từ {addr}"})
                    if current_game_state_packet:
                        send_to_one(conn, current_game_state_packet)
                    if current_viewer_scene_packet:
                        send_to_one(conn, current_viewer_scene_packet)
                elif not player_conn:
                    player_conn = conn
                    client_thread = threading.Thread(target=handle_client, args=(conn, addr, initial_packet), daemon=True)
                    client_thread.start()
                else:
                    send_to_one(conn, {'type': 'server_busy', 'message': 'Đã có thí sinh đang chơi.'})
                    conn.close()
    except OSError as e:
        update_host_gui({'type': 'log', 'message': f"LỖI SERVER: {e}."})
    finally:
        update_host_gui({'type': 'log', 'message': "Server đã đóng."})
        server_socket.close()
