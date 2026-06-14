import socket
import json
import random
import time
import threading
import traceback

from app_info import APP_AUTHOR, APP_COPYRIGHT, APP_VERSION
import question_packs

# --- CẤU HÌNH SERVER ---
HOST = '0.0.0.0'
PORT = 65432
BUFFER_SIZE = 4096
SERVER_POLL_INTERVAL = 0.08

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
LOSS_PRIZE_FROM_LEVEL_10 = "5.000.000"

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
active_question_pack_id = None
active_question_pack_reserved = False
current_poll_session = None
current_stats = {
    'questions_seen': 0,
    'correct_answers': 0,
    'wrong_answers': 0,
    'lifelines_used': 0,
    'fastest_ping': None,
}
host_ready_event = threading.Event()
host_answer_confirm_event = threading.Event()
host_give_up_event = threading.Event()
host_regret_reveal_event = threading.Event()
host_finish_give_up_event = threading.Event()
host_control_lock = threading.Lock()
waiting_for_ready_level = 0
pending_answer = None
pending_answer_level = 0
pending_answer_is_regret = False

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
    f"{APP_AUTHOR} | Version {APP_VERSION}",
    "",
    APP_COPYRIGHT,
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

def send_to_player(data):
    with connections_lock:
        conn = player_conn
    if not conn:
        return False
    send_to_one(conn, data)
    return True

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
        can_confirm = pending_answer is not None and pending_answer_level >= 6 and not pending_answer_is_regret
    if can_confirm:
        host_answer_confirm_event.set()
    return can_confirm

def cancel_locked_answer_from_host():
    with host_control_lock:
        can_cancel = pending_answer is not None and (pending_answer_is_regret or pending_answer_level >= READY_REQUIRED_FROM_LEVEL)
        level = pending_answer_level
        is_regret = pending_answer_is_regret
    if can_cancel:
        if is_regret:
            host_regret_reveal_event.set()
            update_host_gui({'type': 'log', 'message': f"Host yêu cầu công bố đáp án tiếc nuối ở câu {level}."})
            return True
        clear_pending_answer()
        broadcast({'type': 'answer_unlocked', 'level': level})
        update_host_gui({'type': 'log', 'message': f"Host đã hủy đáp án đã chốt ở câu {level}."})
    return can_cancel

def give_up_from_host():
    can_give_up = player_conn is not None and current_question_index is not None
    if can_give_up:
        host_give_up_event.set()
    return can_give_up

def finish_give_up_from_host():
    can_finish = player_conn is not None and current_question_index is not None
    if can_finish:
        host_finish_give_up_event.set()
    return can_finish

def resend_current_state_from_host():
    resent = False
    if current_game_state_packet:
        broadcast(current_game_state_packet)
        resent = True
    with host_control_lock:
        answer = pending_answer
        level = pending_answer_level
        is_regret = pending_answer_is_regret
    if answer:
        broadcast({
            'type': 'answer_locked',
            'player_answer': answer,
            'level': level,
            'requires_host_confirm': level >= 6,
            'give_up_regret': is_regret,
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
    return send_to_player({'type': 'play_music', 'name': name, 'loop': True})

def stop_client_music_from_host():
    return send_to_player({'type': 'stop_music'})

def play_effect_from_host(name):
    broadcast({'type': 'play_effect', 'name': name})
    return True

def poll_payload_from_session():
    if not current_poll_session:
        return {'questions': [], 'current_index': 0, 'announced': [], 'answers': {}, 'results': {}}
    public_questions = []
    for question in current_poll_session.get('questions', []):
        public_questions.append({
            'level': question.get('level', 0),
            'question': question.get('question', ''),
            'options': question.get('options', {}).copy(),
            'pack_id': question.get('pack_id', ''),
        })
    return {
        'questions': public_questions,
        'current_index': current_poll_session.get('current_index', 0),
        'announced': sorted(current_poll_session.get('announced', set())),
        'answers': {str(index): answer for index, answer in current_poll_session.get('answers', {}).items()},
        'results': {str(index): result for index, result in current_poll_session.get('results', {}).items()},
        'locked': sorted(current_poll_session.get('locked', set())),
    }

def broadcast_interactive_poll(sound=None):
    payload = poll_payload_from_session()
    set_viewer_scene(
        'poll',
        'FASTEST FINGER FIRST',
        'Host đang lấy ý kiến khán giả',
        payload=payload,
        sound=sound,
        sound_loop=bool(sound),
    )
    return payload

def start_interactive_poll_from_host(count=3):
    global current_poll_session
    questions = get_interactive_poll_questions(count)
    current_poll_session = {
        'questions': questions,
        'current_index': 0,
        'announced': {0} if questions else set(),
        'answers': {},
        'results': {},
        'locked': set(),
    }
    return broadcast_interactive_poll(sound='viewer_poll')

def select_interactive_poll_question_from_host(index):
    if not current_poll_session:
        return False
    questions = current_poll_session.get('questions', [])
    if index < 0 or index >= len(questions):
        return False
    current_poll_session['current_index'] = index
    current_poll_session.setdefault('announced', set()).add(index)
    broadcast_interactive_poll()
    return True

def answer_interactive_poll_from_host(answer):
    if not current_poll_session:
        return False
    normalized_answer = str(answer).strip().upper()
    if normalized_answer not in ['A', 'B', 'C', 'D']:
        return False
    index = current_poll_session.get('current_index', 0)
    if index in current_poll_session.get('locked', set()):
        return False
    current_poll_session.setdefault('answers', {})[index] = normalized_answer
    current_poll_session.setdefault('announced', set()).add(index)
    broadcast_interactive_poll()
    return True

def lock_interactive_poll_answer_from_host(index=None):
    if not current_poll_session:
        return False
    questions = current_poll_session.get('questions', [])
    target_index = current_poll_session.get('current_index', 0) if index is None else index
    if target_index < 0 or target_index >= len(questions):
        return False
    if target_index not in current_poll_session.get('answers', {}):
        return False
    selected_answer = current_poll_session['answers'][target_index]
    correct_answer = str(questions[target_index].get('answer', '')).strip().upper()
    current_poll_session.setdefault('results', {})[target_index] = {
        'selected_answer': selected_answer,
        'correct_answer': correct_answer,
        'qualified': selected_answer == correct_answer,
    }
    current_poll_session.setdefault('locked', set()).add(target_index)
    current_poll_session.setdefault('announced', set()).add(target_index)
    broadcast_interactive_poll()
    return True

def get_interactive_poll_state():
    return poll_payload_from_session()

def get_question_pack_records(include_deleted=False):
    records = question_packs.question_pack_records(include_deleted=include_deleted)
    for record in records:
        record['active'] = record.get('id') == active_question_pack_id
    return records

def import_question_pack_from_host(path):
    record = question_packs.import_question_pack(path)
    update_host_gui({'type': 'pack_state_changed'})
    update_host_gui({'type': 'log', 'message': f"Da import pack cau hoi: {record.get('name')}."})
    return record

def archive_question_pack_from_host(pack_id):
    ok = question_packs.archive_pack(pack_id)
    if ok:
        update_host_gui({'type': 'pack_state_changed'})
        update_host_gui({'type': 'log', 'message': f"Da luu tru pack: {pack_id}."})
    return ok

def delete_question_pack_from_host(pack_id):
    ok = question_packs.delete_pack(pack_id)
    if ok:
        update_host_gui({'type': 'pack_state_changed'})
        update_host_gui({'type': 'log', 'message': f"Da xoa pack: {pack_id}."})
    return ok

def restore_question_pack_from_host(pack_id):
    ok = question_packs.restore_pack(pack_id)
    if ok:
        update_host_gui({'type': 'pack_state_changed'})
        update_host_gui({'type': 'log', 'message': f"Da kich hoat lai pack: {pack_id}."})
    return ok

def preview_question_pack_from_host(pack_id):
    for record in question_packs.question_pack_records(include_deleted=True):
        if record.get('id') != pack_id:
            continue
        questions = question_packs.read_question_pack(record['path']) if record.get('exists') else []
        return {**record, 'questions': questions}
    return None

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

def notify_host_question_panel(event_type='question_live', status=None, question_data=None, level=None, prize=None):
    if question_data:
        payload = {
            'type': event_type,
            'level': level or question_data.get('level', ''),
            'question': question_data.get('question', ''),
            'options': question_data.get('options', {}).copy(),
            'answer': question_data.get('answer', ''),
            'prize': prize or '',
        }
    else:
        snapshot = get_current_question_snapshot()
        if not snapshot:
            return
        payload = {'type': event_type, **snapshot}
    if status:
        payload['status'] = status
    update_host_gui(payload)

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
    notify_host_question_panel()
    update_host_gui({'type': 'log', 'message': f"Host đã cập nhật câu {current_question_index + 1}."})
    return True

def swap_current_question_from_host():
    if current_question_index is None:
        return False
    level = current_question_index + 1
    current_text = QUESTIONS[current_question_index].get('question', '')
    candidates = []
    for pack_path in question_packs.active_question_pack_paths():
        try:
            pack_questions = question_packs.read_question_pack(pack_path)
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

    pack_records = question_packs.active_pack_records()
    inactive_records = []
    for record in pack_records:
        if active_question_pack_id is None:
            inactive_records.append(record)
            continue
        if record.get('id') != active_question_pack_id:
            inactive_records.append(record)

    candidates = []
    for record in inactive_records or pack_records:
        try:
            pack_questions = question_packs.read_question_pack(record['path'])
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
                'answer': str(question.get('answer', '')).strip().upper(),
                'pack_id': record.get('id', ''),
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

def set_pending_answer(answer, level, is_regret=False):
    global pending_answer, pending_answer_level, pending_answer_is_regret
    with host_control_lock:
        pending_answer = answer
        pending_answer_level = level
        pending_answer_is_regret = is_regret

def clear_pending_answer():
    global pending_answer, pending_answer_level, pending_answer_is_regret
    with host_control_lock:
        pending_answer = None
        pending_answer_level = 0
        pending_answer_is_regret = False
    host_answer_confirm_event.clear()

def needs_ready_confirmation(level):
    return level >= READY_REQUIRED_FROM_LEVEL

def final_prize_on_wrong(level, current_prize):
    if level >= 10:
        return LOSS_PRIZE_FROM_LEVEL_10
    return current_prize or "0"

def final_prize_on_give_up(level):
    if 1 <= level <= len(PRIZE_LEVELS):
        return PRIZE_LEVELS[level - 1]
    return "0"

def broadcast_lifeline_error(lifeline_type, message):
    payload = {
        'type': 'lifeline_result',
        'lifeline': lifeline_type or 'unknown',
        'message': message,
        'opinions': [],
    }
    broadcast(payload)

def notify_pack_usage_update(updated_pack):
    if updated_pack and updated_pack.get('status') in ('archived', 'deleted'):
        update_host_gui({
            'type': 'log',
            'message': f"Pack '{updated_pack.get('name')}' da vuot {question_packs.MAX_ACTIVE_USES} luot hoi va chuyen sang {updated_pack.get('status')}.",
        })
    update_host_gui({
        'type': 'pack_state_changed',
        'active_pack_id': active_question_pack_id,
        'active_pack_name': updated_pack.get('name') if updated_pack else active_question_pack_id,
    })


def mark_active_question_pack_used():
    global active_question_pack_reserved
    if not active_question_pack_id:
        return None
    updated_pack = question_packs.mark_pack_used(active_question_pack_id)
    active_question_pack_reserved = False
    notify_pack_usage_update(updated_pack)
    if updated_pack:
        update_host_gui({
            'type': 'log',
            'message': f"Counter pack '{updated_pack.get('name', active_question_pack_id)}': {updated_pack.get('use_count', 0)}/{question_packs.MAX_ACTIVE_USES}.",
        })
    return updated_pack


def load_random_question_pack(avoid_current=False, mark_used=False, reserve_for_next_player=False):
    global QUESTIONS, active_question_pack_path, active_question_pack_id, active_question_pack_reserved
    try:
        previous_id = active_question_pack_id if avoid_current else None
        chosen_pack = question_packs.choose_next_pack(previous_id)
        if not chosen_pack:
            update_host_gui({'type': 'log', 'message': "LOI: Khong tim thay pack cau hoi active nao."})
            return False

        QUESTIONS = question_packs.read_question_pack(chosen_pack['path'])
        active_question_pack_path = chosen_pack['path']
        active_question_pack_id = chosen_pack['id']
        active_question_pack_reserved = reserve_for_next_player
        if mark_used:
            mark_active_question_pack_used()
        update_host_gui({
            'type': 'pack_state_changed',
            'active_pack_id': active_question_pack_id,
            'active_pack_name': chosen_pack.get('name', chosen_pack.get('id', '')),
        })
        update_host_gui({'type': 'log', 'message': f"Da tai pack cau hoi: '{chosen_pack.get('name', chosen_pack.get('id'))}'."})
        return True
    except Exception as e:
        update_host_gui({'type': 'log', 'message': f"LOI: Khong the tai pack cau hoi. Ly do: {e}"})
        return False


def load_question_pack_for_player():
    active_records = question_packs.active_pack_records()
    reserved_record = next((record for record in active_records if record.get('id') == active_question_pack_id), None)
    if active_question_pack_reserved and reserved_record and QUESTIONS:
        reserved_name = reserved_record.get('name', active_question_pack_id)
        update_host_gui({'type': 'log', 'message': f"Su dung pack da chuan bi san: '{reserved_name}'."})
        update_host_gui({
            'type': 'pack_state_changed',
            'active_pack_id': active_question_pack_id,
            'active_pack_name': reserved_name,
        })
        return True
    return load_random_question_pack(avoid_current=True, mark_used=False)


def prepare_next_question_pack_after_game():
    if load_random_question_pack(avoid_current=True, mark_used=False, reserve_for_next_player=True):
        update_host_gui({'type': 'log', 'message': "Da shuffle va chuan bi pack cau hoi cho nguoi choi tiep theo."})
        return True
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
        if not load_question_pack_for_player():
            raise ConnectionError("Khong co pack cau hoi active de bat dau luot choi.")
        current_stats.update({
            'questions_seen': 0,
            'correct_answers': 0,
            'wrong_answers': 0,
            'lifelines_used': 0,
            'fastest_ping': None,
        })
        host_give_up_event.clear()
        host_regret_reveal_event.clear()
        host_finish_give_up_event.clear()

        game_state = {'level': 0, 'lifelines': {'5050': True, 'audience': True, 'call': True, 'wise_man': True}, 'prize': "0", 'milestone_prize': "0"}
        client_buffer = ""
        give_up_mode = False
        give_up_result_revealed = False
        give_up_final_prize = "0"
        session_pack_counted = False

        def enter_give_up_regret_mode(level):
            nonlocal give_up_mode, give_up_result_revealed, give_up_final_prize
            give_up_mode = True
            give_up_result_revealed = False
            give_up_final_prize = final_prize_on_give_up(level)
            host_give_up_event.clear()
            host_regret_reveal_event.clear()
            host_finish_give_up_event.clear()
            clear_pending_answer()
            payload = {
                'type': 'give_up_regret',
                'level': level,
                'prize': give_up_final_prize,
                'player_name': player_name,
            }
            broadcast(payload)
            update_host_gui(payload)
            update_host_gui({'type': 'log', 'message': f"{player_name} give up ở câu {level}. Chờ chọn đáp án tiếc nuối."})

        def reveal_give_up_regret_answer(level):
            nonlocal give_up_result_revealed
            with host_control_lock:
                player_answer = pending_answer
            if not player_answer:
                host_regret_reveal_event.clear()
                update_host_gui({'type': 'log', 'message': "Chưa có đáp án tiếc nuối để công bố."})
                return
            host_regret_reveal_event.clear()
            correct_answer = q_data['answer']
            is_correct = player_answer.upper() == correct_answer
            clear_pending_answer()
            result_payload = {
                'type': 'result',
                'correct': is_correct,
                'correct_answer': correct_answer,
                'player_answer': player_answer,
                'ping': 0,
                'give_up_regret': True,
                'level': level,
            }
            update_host_gui({
                'type': 'answer',
                'player_answer': player_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'give_up_regret': True,
            })
            broadcast(result_payload)
            give_up_result_revealed = True
            update_host_gui({'type': 'give_up_revealed', 'level': level, 'prize': give_up_final_prize})

        def finish_give_up_after_regret(level):
            host_finish_give_up_event.clear()
            clear_pending_answer()
            broadcast({
                'type': 'game_over',
                'prize': give_up_final_prize,
                'player_name': player_name,
                'level': level,
                'reason': 'give_up',
            })
            update_host_gui({'type': 'log', 'message': f"Kết màn hình give up: {player_name} nhận {give_up_final_prize} VNĐ."})

        while game_state['level'] < len(QUESTIONS):
            while is_game_paused:
                time.sleep(0.5)

            current_level = game_state['level']
            current_question_index = current_level
            q_data = QUESTIONS[current_level]
            current_q_options = q_data['options'].copy()
            update_host_gui({'type': 'game_state', 'level': current_level + 1, 'prize': game_state['prize']})
            notify_host_question_panel(
                event_type='question_preview',
                question_data={**q_data, 'options': current_q_options},
                level=current_level + 1,
                prize=PRIZE_LEVELS[current_level],
                status=f"Chuẩn bị hỏi câu {current_level + 1} - {PRIZE_LEVELS[current_level]} VNĐ",
            )

            broadcast({'type': 'ask_ready', 'level': current_level + 1})
            set_waiting_for_ready(current_level + 1)
            update_host_gui({'type': 'ready_waiting', 'level': current_level + 1})
            host_give_up_requested = False
            while True:
                if host_give_up_event.is_set():
                    host_give_up_requested = True
                    break
                if not needs_ready_confirmation(current_level + 1):
                    break
                while is_game_paused:
                    time.sleep(0.5)

                if host_ready_event.is_set():
                    update_host_gui({'type': 'log', 'message': f"Host đã xác nhận bắt đầu câu {current_level + 1}."})
                    break

                ready_response, client_buffer = receive_json_message(conn, client_buffer, timeout=SERVER_POLL_INTERVAL)
                if ready_response is None:
                    continue
                if not ready_response.get('ready'):
                    raise ConnectionError("Client không sẵn sàng")
                break
            clear_waiting_for_ready()
            update_host_gui({'type': 'ready_cleared'})
            host_give_up_requested = False

            needs_question_broadcast = True
            locked_answer = None
            locked_answer_timestamp = time.time()
            clear_pending_answer()
            while True:
                if needs_question_broadcast:
                    current_game_state_packet = {
                        'type': 'question',
                        'question': q_data['question'],
                        'options': current_q_options,
                        'level': current_level + 1,
                        'prize': PRIZE_LEVELS[current_level],
                        'lifelines': game_state['lifelines'],
                    }
                    broadcast(current_game_state_packet)
                    notify_host_question_panel()
                    if not session_pack_counted:
                        mark_active_question_pack_used()
                        session_pack_counted = True
                    current_stats['questions_seen'] = max(current_stats['questions_seen'], current_level + 1)
                    needs_question_broadcast = False

                if host_give_up_event.is_set() and not give_up_mode:
                    enter_give_up_regret_mode(current_level + 1)
                    continue

                if give_up_mode:
                    if host_regret_reveal_event.is_set():
                        reveal_give_up_regret_answer(current_level + 1)
                        continue
                    if give_up_result_revealed and host_finish_give_up_event.is_set():
                        finish_give_up_after_regret(current_level + 1)
                        game_finished_normally = True
                        break

                if locked_answer and current_level + 1 >= 6 and host_answer_confirm_event.is_set():
                    response = {
                        'action': 'answer',
                        'value': locked_answer,
                        'timestamp': locked_answer_timestamp,
                        'confirmed_by_host': True,
                    }
                    update_host_gui({'type': 'log', 'message': f"Host công bố đáp án {locked_answer} cho câu {current_level + 1}."})
                    break

                response, client_buffer = receive_json_message(conn, client_buffer, timeout=SERVER_POLL_INTERVAL)
                if response is None:
                    continue

                action = response.get('action')
                if give_up_mode:
                    if give_up_result_revealed:
                        continue
                    if action in ('answer', 'answer_locked'):
                        regret_answer = response.get('value')
                        if not regret_answer:
                            continue
                        with host_control_lock:
                            same_pending_regret = pending_answer == regret_answer and pending_answer_is_regret
                        if same_pending_regret:
                            continue
                        set_pending_answer(regret_answer, current_level + 1, is_regret=True)
                        update_host_gui({
                            'type': 'answer_locked',
                            'player_answer': regret_answer,
                            'level': current_level + 1,
                            'requires_host_confirm': True,
                            'give_up_regret': True,
                        })
                        broadcast({
                            'type': 'answer_locked',
                            'player_answer': regret_answer,
                            'level': current_level + 1,
                            'requires_host_confirm': True,
                            'give_up_regret': True,
                        })
                    elif action == 'lifeline':
                        broadcast_lifeline_error(
                            response.get('value'),
                            "Thí sinh đã give up, phần trợ giúp đã khóa. Hãy chọn đáp án tiếc nuối.",
                        )
                    continue

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
                    try:
                        if lifeline_type not in game_state['lifelines']:
                            message = f"Trợ giúp không hợp lệ: {lifeline_type}"
                            update_host_gui({'type': 'log', 'message': message})
                            broadcast_lifeline_error(lifeline_type, message)
                            continue

                        if not game_state['lifelines'].get(lifeline_type, False):
                            message = f"Trợ giúp {lifeline_type.upper()} đã dùng hoặc không khả dụng."
                            update_host_gui({'type': 'log', 'message': message})
                            broadcast_lifeline_error(lifeline_type, message)
                            continue

                        if lifeline_type == 'wise_man' and game_state['level'] < 5:
                            message = "Tư vấn chỉ mở từ câu 6."
                            update_host_gui({'type': 'log', 'message': message})
                            broadcast_lifeline_error(lifeline_type, message)
                            continue

                        update_host_gui({'type': 'log', 'message': f"Người chơi dùng trợ giúp: {lifeline_type.upper()}"})
                        current_stats['lifelines_used'] += 1

                        if lifeline_type == '5050':
                            game_state['lifelines']['5050'] = False
                            current_q_options = handle_lifeline_5050(q_data)
                            needs_question_broadcast = True
                        elif lifeline_type == 'audience':
                            game_state['lifelines']['audience'] = False
                            update_host_gui({'type': 'audience_request'})
                        elif lifeline_type == 'call':
                            game_state['lifelines']['call'] = False
                            update_host_gui({
                                'type': 'call_request',
                                'question': q_data['question'],
                                'answer': q_data['answer'],
                            })
                        elif lifeline_type == 'wise_man':
                            game_state['lifelines']['wise_man'] = False
                            wrong_answers = [key for key in q_data['options'] if key != q_data['answer']]
                            suggested_answer = q_data['answer'] if random.random() < 0.5 else random.choice(wrong_answers)
                            advice = f"Tổ tư vấn nghiêng về đáp án {suggested_answer}"
                            broadcast({'type': 'lifeline_result', 'lifeline': 'wise_man', 'message': advice})
                            update_host_gui({'type': 'log', 'message': f"Tổ tư vấn đã gợi ý đáp án {suggested_answer}."})
                    except Exception as lifeline_error:
                        message = f"LỖI trợ giúp {lifeline_type}: {lifeline_error}"
                        update_host_gui({'type': 'log', 'message': message})
                        update_host_gui({'type': 'log', 'message': traceback.format_exc()})
                        broadcast_lifeline_error(
                            lifeline_type,
                            "Trợ giúp gặp lỗi kỹ thuật, host có thể xử lý thủ công. Kết nối vẫn được giữ.",
                        )
                        continue

            if game_finished_normally:
                break

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
    except Exception as e:
        update_host_gui({'type': 'log', 'message': f"LỖI SERVER trong luồng người chơi '{player_name}': {e}"})
        update_host_gui({'type': 'log', 'message': traceback.format_exc()})
    finally:
        clear_waiting_for_ready()
        clear_pending_answer()
        host_give_up_event.clear()
        host_regret_reveal_event.clear()
        host_finish_give_up_event.clear()
        if not game_finished_normally:
            broadcast({'type': 'game_ended_waiting'})
        else:
            prepare_next_question_pack_after_game()
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
