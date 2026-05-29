import tkinter as tk
from tkinter import scrolledtext, font, simpledialog, messagebox
import threading
import time
import os
import random
import server as server_logic
try:
    from ui_assets import load_logo_photo
except ImportError:
    load_logo_photo = None

HOST_BG = "#07101f"
HOST_PANEL = "#0d1930"
HOST_PANEL_ALT = "#101f3b"
HOST_BORDER = "#26395f"
HOST_TEXT = "#f4f7fb"
HOST_MUTED = "#9eacc7"
HOST_ACCENT = "#d7b75a"
HOST_GREEN = "#16a06b"
HOST_RED = "#d9485f"

class HostGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Host Control - Ai Là Triệu Phú")
        self.geometry("980x720")
        self.minsize(900, 640)
        self.configure(bg=HOST_BG)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.label_font = font.Font(family="Segoe UI", size=11)
        self.value_font = font.Font(family="Segoe UI", size=11, weight="bold")
        self.log_font = font.Font(family="Consolas", size=10)
        self.current_level = 0
        self.is_client_muted = False
        self.logo_image = self.load_logo_image()
        self.poll_window = None

        self.create_widgets()
        self.bind_hotkeys()

        server_logic.set_game_update_callback(self.queue_gui_update)
        self.server_thread = threading.Thread(target=server_logic.start_server_logic, daemon=True)
        self.server_thread.start()

    def load_logo_image(self):
        if not load_logo_photo:
            return None
        try:
            return load_logo_photo((58, 58))
        except Exception:
            return None

    def create_widgets(self):
        main_frame = tk.Frame(self, bg=HOST_BG, padx=18, pady=16)
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)

        header = tk.Frame(main_frame, bg=HOST_BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        title_column = 1 if self.logo_image else 0
        header.grid_columnconfigure(title_column, weight=1)

        if self.logo_image:
            tk.Label(header, image=self.logo_image, bg=HOST_BG).grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))

        tk.Label(
            header,
            text="AI LÀ TRIỆU PHÚ - HOST CONTROL",
            font=("Segoe UI", 22, "bold"),
            bg=HOST_BG,
            fg=HOST_TEXT,
            anchor="w",
        ).grid(row=0, column=title_column, sticky="w")
        self.lbl_server_status = tk.Label(
            header,
            text="SERVER ĐANG KHỞI ĐỘNG",
            font=("Segoe UI", 10, "bold"),
            bg=HOST_ACCENT,
            fg="#121212",
            padx=14,
            pady=6,
        )
        self.lbl_server_status.grid(row=0, column=title_column + 1, sticky="e")
        tk.Label(
            header,
            text="Phòng điều khiển game show",
            font=("Segoe UI", 11),
            bg=HOST_BG,
            fg=HOST_MUTED,
            anchor="w",
        ).grid(row=1, column=title_column, sticky="w", pady=(4, 0))

        status_frame = tk.Frame(main_frame, bg=HOST_BG)
        status_frame.grid(row=1, column=0, sticky="ew")
        for col in range(4):
            status_frame.grid_columnconfigure(col, weight=1, uniform="status")

        self.lbl_name = self.create_metric_card(status_frame, "THÍ SINH", "Chờ kết nối...", 0)
        self.lbl_id = self.create_metric_card(status_frame, "MÃ KẾT NỐI", "N/A", 1)
        self.lbl_level = self.create_metric_card(status_frame, "CÂU HIỆN TẠI", "0", 2)
        self.lbl_prize = self.create_metric_card(status_frame, "TIỀN THƯỞNG", "0 VNĐ", 3, accent=HOST_GREEN)

        answer_panel = tk.Frame(main_frame, bg=HOST_PANEL, highlightthickness=1, highlightbackground=HOST_BORDER, padx=16, pady=12)
        answer_panel.grid(row=2, column=0, sticky="ew", pady=14)
        answer_panel.grid_columnconfigure(0, weight=1)
        tk.Label(answer_panel, text="LƯỢT TRẢ LỜI", bg=HOST_PANEL, fg=HOST_MUTED, font=("Segoe UI", 9, "bold"), anchor="w").grid(row=0, column=0, sticky="ew")
        self.lbl_last_answer = tk.Label(
            answer_panel,
            text="Chưa có đáp án được chốt",
            bg=HOST_PANEL,
            fg=HOST_TEXT,
            font=("Segoe UI", 15, "bold"),
            anchor="w",
        )
        self.lbl_last_answer.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        work_area = tk.Frame(main_frame, bg=HOST_BG)
        work_area.grid(row=3, column=0, sticky="nsew")
        work_area.grid_columnconfigure(0, weight=0)
        work_area.grid_columnconfigure(1, weight=1)
        work_area.grid_rowconfigure(0, weight=1)

        control_shell = tk.Frame(work_area, bg=HOST_PANEL, highlightthickness=1, highlightbackground=HOST_BORDER, width=292)
        control_shell.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        control_shell.grid_propagate(False)
        control_shell.grid_rowconfigure(0, weight=1)
        control_shell.grid_columnconfigure(0, weight=1)

        self.control_canvas = tk.Canvas(control_shell, bg=HOST_PANEL, highlightthickness=0, bd=0)
        control_scrollbar = tk.Scrollbar(control_shell, orient=tk.VERTICAL, command=self.control_canvas.yview)
        self.control_canvas.configure(yscrollcommand=control_scrollbar.set)
        self.control_canvas.grid(row=0, column=0, sticky="nsew")
        control_scrollbar.grid(row=0, column=1, sticky="ns")

        control_frame = tk.Frame(self.control_canvas, bg=HOST_PANEL, padx=14, pady=14)
        control_window = self.control_canvas.create_window((0, 0), window=control_frame, anchor="nw")
        control_frame.bind(
            "<Configure>",
            lambda event: self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all")),
        )
        self.control_canvas.bind(
            "<Configure>",
            lambda event: self.control_canvas.itemconfigure(control_window, width=event.width),
        )
        self.control_canvas.bind("<Enter>", self.enable_control_scroll)
        self.control_canvas.bind("<Leave>", self.disable_control_scroll)
        control_frame.bind("<Enter>", self.enable_control_scroll)
        control_frame.bind("<Leave>", self.disable_control_scroll)
        tk.Label(control_frame, text="ĐIỀU KHIỂN", bg=HOST_PANEL, fg=HOST_ACCENT, font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", pady=(0, 12))

        self.create_control_button(control_frame, "Tắt Nhạc Client", lambda: self.send_command_to_client('set_mute', True)).pack(fill="x", pady=5)
        self.create_control_button(control_frame, "Bật Nhạc Client", lambda: self.send_command_to_client('set_mute', False)).pack(fill="x", pady=5)
        self.pause_button = self.create_control_button(control_frame, "Tạm Dừng Game", self.toggle_pause, bg="#263a66")
        self.pause_button.pack(fill="x", pady=(16, 5))
        self.force_ready_button = self.create_control_button(control_frame, "Bắt đầu câu", self.force_start_question, bg="#735f17")
        self.force_ready_button.config(state=tk.DISABLED, disabledforeground="#7f8aa6")
        self.force_ready_button.pack(fill="x", pady=5)
        self.confirm_answer_button = self.create_control_button(control_frame, "Công bố đáp án", self.confirm_locked_answer, bg=HOST_GREEN)
        self.confirm_answer_button.config(state=tk.DISABLED, disabledforeground="#7f8aa6")
        self.confirm_answer_button.pack(fill="x", pady=(16, 5))
        self.cancel_answer_button = self.create_control_button(control_frame, "Hủy chốt đáp án", self.cancel_locked_answer, bg=HOST_RED)
        self.cancel_answer_button.pack(fill="x", pady=5)

        self.add_group_label(control_frame, "SCENE VIEWER")
        self.create_button_row(control_frame, [
            ("Game", self.show_game_scene),
            ("Bảng thưởng", self.show_prize_scene),
        ])
        self.create_button_row(control_frame, [
            ("Nghỉ 5 phút", self.show_break_scene),
            ("Technical", self.show_technical_scene),
        ])
        self.create_button_row(control_frame, [
            ("Blank", self.show_blank_scene),
            ("Reset viewer", self.reset_viewers),
        ])
        self.create_button_row(control_frame, [
            ("Stats", self.show_stats_scene),
            ("Credits", self.show_credits_scene),
        ])
        self.create_button_row(control_frame, [
            ("Mini quiz", self.show_mini_quiz_scene),
            ("Poll", self.show_poll_scene),
        ])
        self.create_control_button(control_frame, "Kết thúc chương trình", self.end_program, bg=HOST_RED).pack(fill="x", pady=(10, 5))

        self.add_group_label(control_frame, "KỸ THUẬT")
        self.create_button_row(control_frame, [
            ("Resend", self.resend_state),
            ("Đổi câu", self.swap_question),
        ])
        self.create_control_button(control_frame, "Sửa câu hiện tại", self.edit_current_question, bg="#33456f").pack(fill="x", pady=5)

        self.add_group_label(control_frame, "AUDIO")
        self.create_button_row(control_frame, [
            ("Nhạc căng", self.play_tension_music),
            ("Dừng nhạc", self.stop_client_music),
        ])
        self.create_button_row(control_frame, [
            ("Nhạc nghỉ", self.play_break_music),
            ("Dừng nghỉ", self.stop_break_music),
        ])
        self.create_control_button(control_frame, "Phát còi kết thúc", self.play_end_buzzer, bg="#5f2940").pack(fill="x", pady=5)

        self.add_group_label(control_frame, "GHI CHÚ MC")
        self.mc_notes = tk.Text(
            control_frame,
            height=4,
            width=24,
            bg="#07101f",
            fg=HOST_TEXT,
            insertbackground=HOST_TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Segoe UI", 10),
        )
        self.mc_notes.pack(fill="x", pady=(4, 0))

        log_frame = tk.Frame(work_area, bg=HOST_PANEL, highlightthickness=1, highlightbackground=HOST_BORDER, padx=12, pady=12)
        log_frame.grid(row=0, column=1, sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        tk.Label(log_frame, text="NHẬT KÝ SERVER", bg=HOST_PANEL, fg=HOST_ACCENT, font=("Segoe UI", 12, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            state='disabled',
            font=self.log_font,
            bg="#050b16",
            fg="#dce6ff",
            insertbackground=HOST_TEXT,
            relief=tk.FLAT,
            bd=0,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")

    def create_metric_card(self, parent, title, value, column, accent=HOST_TEXT):
        card = tk.Frame(parent, bg=HOST_PANEL, highlightthickness=1, highlightbackground=HOST_BORDER, padx=14, pady=12)
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0))
        tk.Label(card, text=title, bg=HOST_PANEL, fg=HOST_MUTED, font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
        value_label = tk.Label(card, text=value, bg=HOST_PANEL, fg=accent, font=("Segoe UI", 16, "bold"), anchor="w")
        value_label.pack(fill="x", pady=(6, 0))
        return value_label

    def create_control_button(self, parent, text, command, bg=HOST_PANEL_ALT):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=HOST_TEXT,
            activebackground="#1b315d",
            activeforeground=HOST_TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Segoe UI", 11, "bold"),
            padx=16,
            pady=10,
        )

    def add_group_label(self, parent, text):
        tk.Label(
            parent,
            text=text,
            bg=HOST_PANEL,
            fg=HOST_ACCENT,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 4))

    def create_button_row(self, parent, buttons):
        row = tk.Frame(parent, bg=HOST_PANEL)
        row.pack(fill="x", pady=3)
        for text, command in buttons:
            btn = self.create_control_button(row, text, command)
            btn.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 4))
        return row

    def enable_control_scroll(self, event=None):
        self.bind_all("<MouseWheel>", self.on_control_mousewheel)

    def disable_control_scroll(self, event=None):
        self.unbind_all("<MouseWheel>")

    def on_control_mousewheel(self, event):
        if hasattr(self, "control_canvas"):
            self.control_canvas.yview_scroll(int(-event.delta / 120), "units")

    def bind_hotkeys(self):
        self.bind_all("<space>", lambda event: self.run_hotkey(event, self.confirm_locked_answer))
        self.bind_all("<Return>", lambda event: self.run_hotkey(event, self.force_start_question))
        self.bind_all("<Key-p>", lambda event: self.run_hotkey(event, self.toggle_pause))
        self.bind_all("<Key-P>", lambda event: self.run_hotkey(event, self.toggle_pause))
        self.bind_all("<Key-m>", lambda event: self.run_hotkey(event, self.toggle_client_mute))
        self.bind_all("<Key-M>", lambda event: self.run_hotkey(event, self.toggle_client_mute))
        self.bind_all("<Key-r>", lambda event: self.run_hotkey(event, self.resend_state))
        self.bind_all("<Key-R>", lambda event: self.run_hotkey(event, self.resend_state))
        self.bind_all("<Key-b>", lambda event: self.run_hotkey(event, self.show_break_scene))
        self.bind_all("<Key-B>", lambda event: self.run_hotkey(event, self.show_break_scene))
        self.bind_all("<Escape>", lambda event: self.run_hotkey(event, self.show_blank_scene))

    def run_hotkey(self, event, action):
        if isinstance(event.widget, (tk.Entry, tk.Text)):
            return
        action()

    def send_command_to_client(self, cmd_type, value):
        if not server_logic.player_conn:
            self.log("Lỗi: Không có người chơi để gửi lệnh.")
            return
        server_logic.broadcast({'type': cmd_type, 'value': value})
        self.log(f"Đã gửi lệnh '{cmd_type}: {value}' đến tất cả.")

    def toggle_client_mute(self):
        self.is_client_muted = not self.is_client_muted
        self.send_command_to_client('set_mute', self.is_client_muted)

    def force_start_question(self):
        if server_logic.force_ready_from_host():
            self.force_ready_button.config(state=tk.DISABLED)
            self.log("Host đã xác nhận bắt đầu câu hỏi.")
        else:
            self.log("Không có câu hỏi nào đang chờ xác nhận sẵn sàng.")

    def confirm_locked_answer(self):
        if server_logic.confirm_locked_answer_from_host():
            self.confirm_answer_button.config(state=tk.DISABLED)
            self.log("Host đã công bố đáp án đang được chốt.")
        else:
            self.log("Chưa có đáp án câu 6+ nào đang chờ công bố.")

    def cancel_locked_answer(self):
        if server_logic.cancel_locked_answer_from_host():
            self.confirm_answer_button.config(text="Công bố đáp án", state=tk.DISABLED)
            self.lbl_last_answer.config(text="Đã hủy chốt, chờ thí sinh chọn lại", fg=HOST_ACCENT)
        else:
            self.log("Không có đáp án nào để hủy chốt.")

    def resend_state(self):
        if server_logic.resend_current_state_from_host():
            self.log("Đã phát lại trạng thái hiện tại cho client/viewer.")
        else:
            self.log("Chưa có trạng thái game để phát lại.")

    def show_game_scene(self):
        server_logic.show_game_scene_from_host()
        self.log("Viewer: quay lại màn game.")

    def show_prize_scene(self):
        server_logic.set_viewer_scene('prize', 'BẢNG TIỀN THƯỞNG', 'Các mốc giải thưởng của chương trình', sound='viewer_stats')
        self.log("Viewer: hiện bảng tiền thưởng.")

    def show_break_scene(self):
        server_logic.set_viewer_scene(
            'break',
            'GIẢI LAO',
            'Chương trình sẽ quay lại sau ít phút',
            countdown_seconds=300,
            sound='viewer_break',
            sound_loop=True,
        )
        self.log("Viewer: màn nghỉ 5 phút.")

    def show_technical_scene(self):
        server_logic.set_viewer_scene(
            'technical',
            'TECHNICAL STANDBY',
            'Chương trình tạm dừng trong ít phút',
            sound='viewer_technical',
            sound_loop=True,
        )
        self.log("Viewer: technical standby.")

    def show_blank_scene(self):
        server_logic.set_viewer_scene('blank', 'AI LÀ TRIỆU PHÚ', '', sound='viewer_blank')
        self.log("Viewer: blank screen.")

    def reset_viewers(self):
        server_logic.reset_viewers_from_host()
        self.log("Đã reset viewer về màn chờ.")

    def show_stats_scene(self):
        server_logic.set_viewer_scene(
            'stats',
            'THỐNG KÊ LƯỢT CHƠI',
            'Tổng hợp nhanh diễn biến hiện tại',
            sound='viewer_stats',
        )
        self.log("Viewer: hiện stats.")

    def show_credits_scene(self):
        server_logic.set_viewer_scene(
            'credits',
            'AI LÀ TRIỆU PHÚ',
            '',
            payload={'lines': server_logic.CREDIT_LINES},
            sound='viewer_credits',
            sound_loop=True,
        )
        self.log("Viewer: hiện credit/sponsor slide.")

    def end_program(self):
        server_logic.end_program_from_host()
        self.pause_button.config(text="Tiếp Tục Game", bg=HOST_GREEN, fg="white")
        self.log("Đã kết thúc chương trình: client chuyển tạm dừng, viewer chuyển credit.")

    def show_mini_quiz_scene(self):
        prompts = [
            "Theo bạn thí sinh sẽ dừng ở mốc nào?",
            "Câu hỏi tiếp theo sẽ thuộc lĩnh vực nào?",
            "Bạn sẽ dùng trợ giúp nào trong tình huống này?",
            "Nếu được đổi vai, bạn có tự tin ngồi ghế nóng không?",
        ]
        server_logic.set_viewer_scene(
            'mini_quiz',
            'MINI QUIZ KHÁN GIẢ',
            random.choice(prompts),
            sound='viewer_mini_quiz',
        )
        self.log("Viewer: hiện mini quiz.")

    def show_poll_scene(self):
        payload = server_logic.start_interactive_poll_from_host(3)
        question_count = len(payload.get('questions', []))
        self.open_poll_control()
        self.log(f"Viewer: hiện poll tương tác FFF ({question_count} câu).")

    def open_poll_control(self):
        if self.poll_window and self.poll_window.winfo_exists():
            self.poll_window.lift()
            self.poll_window.refresh()
            return
        self.poll_window = PollControlWindow(self)

    def play_tension_music(self):
        server_logic.play_client_music_from_host('wait_11_15')
        self.log("Đã phát nhạc căng thẳng cho client.")

    def stop_client_music(self):
        server_logic.stop_client_music_from_host()
        self.log("Đã dừng nhạc client.")

    def play_break_music(self):
        server_logic.play_client_music_from_host('viewer_break')
        self.log("Đã phát nhạc hiệu nghỉ/quảng cáo cho client.")

    def stop_break_music(self):
        server_logic.stop_client_music_from_host()
        self.log("Đã dừng nhạc hiệu nghỉ/quảng cáo.")

    def play_end_buzzer(self):
        server_logic.play_effect_from_host('end_buzzer')
        self.log("Đã phát còi kết thúc theo lệnh host.")

    def edit_current_question(self):
        snapshot = server_logic.get_current_question_snapshot()
        if not snapshot:
            self.log("Chưa có câu hỏi hiện tại để sửa.")
            return

        question = simpledialog.askstring("Sửa câu hỏi", "Nội dung câu hỏi:", initialvalue=snapshot['question'], parent=self)
        if question is None:
            return
        options = {}
        for key in ['A', 'B', 'C', 'D']:
            value = simpledialog.askstring(f"Sửa đáp án {key}", f"Phương án {key}:", initialvalue=snapshot['options'].get(key, ''), parent=self)
            if value is None:
                return
            options[key] = value
        answer = simpledialog.askstring("Đáp án đúng", "Nhập A/B/C/D:", initialvalue=snapshot['answer'], parent=self)
        if answer is None:
            return
        if server_logic.update_current_question_from_host(question, options, answer):
            self.log(f"Đã cập nhật câu {snapshot['level']} và phát lại cho màn hình.")
        else:
            messagebox.showerror("Không hợp lệ", "Đáp án đúng phải là A, B, C hoặc D.")

    def swap_question(self):
        if server_logic.swap_current_question_from_host():
            self.log("Đã đổi sang câu dự phòng cùng level.")
        else:
            self.log("Không tìm thấy câu dự phòng cùng level.")

    def toggle_pause(self):
        server_logic.is_game_paused = not server_logic.is_game_paused
        if server_logic.is_game_paused:
            self.pause_button.config(text="Tiếp Tục Game", bg=HOST_GREEN, fg="white")
            self.log("GAME ĐÃ TẠM DỪNG.")
            server_logic.broadcast({'type': 'game_paused', 'paused': True})
        else:
            self.pause_button.config(text="Tạm Dừng Game", bg="#263a66", fg=HOST_TEXT)
            self.log("GAME ĐÃ TIẾP TỤC.")
            server_logic.broadcast({'type': 'game_paused', 'paused': False})

    def queue_gui_update(self, data):
        self.after(0, self.process_gui_update, data)

    def process_gui_update(self, data):
        msg_type = data.get('type')
        if msg_type == 'log':
            self.log(data['message'])
            if "Server đang lắng nghe" in data['message']:
                self.lbl_server_status.config(text="SERVER ONLINE", bg=HOST_GREEN, fg="white")
            elif "LỖI" in data['message']:
                self.lbl_server_status.config(text="SERVER ERROR", bg=HOST_RED, fg="white")
        elif msg_type == 'connect':
            self.lbl_name.config(text=data['name'])
            self.lbl_id.config(text=data['id'])
            self.lbl_last_answer.config(text="Thí sinh đã kết nối, chờ câu hỏi", fg=HOST_ACCENT)
            self.log(f"Người chơi '{data['name']}' đã kết nối từ {data['addr']}")
        elif msg_type == 'disconnect':
            self.lbl_name.config(text="Chờ kết nối...")
            self.lbl_id.config(text="N/A")
            self.lbl_level.config(text="0")
            self.lbl_prize.config(text="0 VNĐ")
            self.lbl_last_answer.config(text="Chưa có đáp án được chốt", fg=HOST_TEXT)
            self.current_level = 0
            self.force_ready_button.config(state=tk.DISABLED)
            self.confirm_answer_button.config(state=tk.DISABLED)
        elif msg_type == 'game_state':
            self.current_level = data['level']
            self.lbl_level.config(text=str(data['level']))
            self.lbl_prize.config(text=f"{data['prize']} VNĐ")
            self.lbl_last_answer.config(text=f"Đang ở câu {data['level']}, chờ thí sinh chốt đáp án", fg=HOST_TEXT)
            self.confirm_answer_button.config(state=tk.DISABLED)
        elif msg_type == 'question_live':
            self.lbl_last_answer.config(text=f"Đang chờ thí sinh trả lời câu {data['level']}", fg=HOST_TEXT)
        elif msg_type == 'ready_waiting':
            self.force_ready_button.config(text=f"Bắt đầu câu {data['level']}", state=tk.NORMAL)
            self.lbl_last_answer.config(text=f"Đang chờ thí sinh sẵn sàng cho câu {data['level']}", fg=HOST_ACCENT)
        elif msg_type == 'ready_cleared':
            self.force_ready_button.config(text="Bắt đầu câu", state=tk.DISABLED)
        elif msg_type == 'answer_locked':
            if data.get('requires_host_confirm'):
                self.confirm_answer_button.config(text=f"Công bố đáp án {data['player_answer']}", state=tk.NORMAL)
                text = f"Đã chốt đáp án {data['player_answer']} - chờ MC công bố"
            else:
                self.confirm_answer_button.config(state=tk.DISABLED)
                text = f"Đã chốt đáp án {data['player_answer']} - tự động công bố"
            self.lbl_last_answer.config(text=text, fg=HOST_ACCENT)
            self.log(text)
        elif msg_type == 'answer':
            self.confirm_answer_button.config(text="Công bố đáp án", state=tk.DISABLED)
            status, color = ("ĐÚNG", HOST_GREEN) if data['is_correct'] else ("SAI", HOST_RED)
            text = f"'{data['player_answer']}' -> Đáp án đúng: '{data['correct_answer']}' ({status})"
            self.lbl_last_answer.config(text=text, fg=color)
            self.log(f"Người chơi trả lời câu {self.lbl_level.cget('text')}: {text}")
        elif msg_type == 'wise_man_request':
            self.handle_wise_man_request(data['question'], data['answer'])
        elif msg_type == 'audience_request':
            self.handle_audience_request()
        elif msg_type == 'call_request':
            self.handle_call_request(data['question'], data['answer'])

    def handle_audience_request(self):
        self.log("Chờ 2 giây cho nhạc hiệu hỏi khán giả, sau đó mở bộ đếm 30 giây...")
        self.after(2000, self.open_audience_dialog)

    def open_audience_dialog(self):
        self.log("Đang nhập ý kiến 3 khán giả trong 30 giây...")
        dialog = AudienceDialog(self)
        results = dialog.result
        if results and all(r.upper() in ['A', 'B', 'C', 'D'] for r in results if r):
            server_logic.broadcast({'type': 'lifeline_result', 'lifeline': 'audience', 'opinions': [r.upper() for r in results]})
            self.log(f"Đã gửi ý kiến khán giả: {results}")
        else:
            server_logic.broadcast({'type': 'lifeline_result', 'lifeline': 'audience', 'opinions': []})
            self.log("Đã hủy hoặc nhập sai ý kiến khán giả.")

    def handle_call_request(self, question, answer):
        self.log("Gọi điện: mở bộ đếm 30 giây để host nhập gợi ý.")
        self.open_call_dialog(question, answer)

    def open_call_dialog(self, question, answer):
        self.log("Đang nhập gợi ý gọi điện trong 30 giây...")
        dialog = CallDialog(self, question, answer)
        suggestion = (dialog.result or "").strip()
        message = f"Người được gọi gợi ý: {suggestion}" if suggestion else "Người được gọi không đưa ra được gợi ý."
        server_logic.broadcast({'type': 'lifeline_result', 'lifeline': 'call', 'message': message})
        self.log("Đã gửi gợi ý gọi điện cho thí sinh.")

    def handle_wise_man_request(self, question, answer):
        self.log("Đang chờ gợi ý từ Host cho Tổ Tư Vấn...")
        suggestion = simpledialog.askstring("Yêu cầu từ Tổ Tư Vấn", f"Người chơi cần trợ giúp!\n\nCâu hỏi: {question}\nĐáp án đúng: {answer}\n\nNhập gợi ý của bạn:", parent=self)
        msg_to_send = f"Tổ tư vấn gợi ý: {suggestion}" if suggestion else "Tổ tư vấn không đưa ra được gợi ý."
        server_logic.broadcast({'type': 'lifeline_result', 'lifeline': 'wise_man', 'message': msg_to_send})
        self.log(f"Đã gửi phản hồi Tổ Tư Vấn.")

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def on_closing(self):
        if messagebox.askokcancel("Thoát", "Bạn có chắc muốn đóng Bảng Điều Khiển không?"):
            self.destroy()
            os._exit(0)

class PollControlWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Điều Khiển Poll Khán Giả")
        self.geometry("560x460")
        self.configure(bg=HOST_BG)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.normal_font = font.Font(family="Segoe UI", size=10, weight="bold")
        self.done_font = font.Font(family="Segoe UI", size=10, weight="bold", overstrike=1)
        self.question_buttons = []
        self.option_buttons = []
        self.build_widgets()
        self.refresh()

    def build_widgets(self):
        container = tk.Frame(self, bg=HOST_BG, padx=16, pady=14)
        container.pack(fill="both", expand=True)
        tk.Label(
            container,
            text="POLL KHÁN GIẢ - FASTEST FINGER FIRST",
            bg=HOST_BG,
            fg=HOST_ACCENT,
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        self.current_label = tk.Label(
            container,
            text="",
            bg=HOST_PANEL,
            fg=HOST_TEXT,
            font=("Segoe UI", 11, "bold"),
            wraplength=500,
            justify=tk.LEFT,
            padx=12,
            pady=10,
            anchor="w",
        )
        self.current_label.pack(fill="x", pady=(0, 10))

        self.question_frame = tk.Frame(container, bg=HOST_BG)
        self.question_frame.pack(fill="both", expand=True)

        option_frame = tk.Frame(container, bg=HOST_BG)
        option_frame.pack(fill="x", pady=(12, 0))
        for answer in ["A", "B", "C", "D"]:
            button = tk.Button(
                option_frame,
                text=f"Khán giả chọn {answer}",
                command=lambda value=answer: self.choose_answer(value),
                bg=HOST_PANEL_ALT,
                fg=HOST_TEXT,
                activebackground="#1b315d",
                activeforeground=HOST_TEXT,
                relief=tk.FLAT,
                font=("Segoe UI", 10, "bold"),
                padx=10,
                pady=9,
            )
            button.pack(side=tk.LEFT, fill="x", expand=True, padx=4)
            self.option_buttons.append(button)

    def refresh(self):
        state = server_logic.get_interactive_poll_state()
        questions = state.get('questions', [])
        current_index = state.get('current_index', 0)
        announced = set(state.get('announced', []))
        answers = state.get('answers', {})

        for child in self.question_frame.winfo_children():
            child.destroy()
        self.question_buttons.clear()

        if not questions:
            self.current_label.config(text="Chưa có câu hỏi poll nào.")
            for button in self.option_buttons:
                button.config(state=tk.DISABLED)
            return

        current_question = questions[current_index].get('question', '')
        current_answer = answers.get(str(current_index))
        status = f" | Khán giả chọn {current_answer}" if current_answer else ""
        self.current_label.config(text=f"Đang lên sóng câu {current_index + 1}: {current_question}{status}")

        for index, question in enumerate(questions):
            answer = answers.get(str(index))
            was_announced = index in announced
            prefix = "✓" if answer else ("↗" if index == current_index else ("•" if was_announced else "○"))
            text = f"{prefix} Câu {index + 1}: {question.get('question', '')}"
            if answer:
                text += f"  [{answer}]"
            button = tk.Button(
                self.question_frame,
                text=text,
                command=lambda value=index: self.select_question(value),
                bg=self.question_bg(index, current_index, was_announced, answer),
                fg="#09111f" if index == current_index and not answer else HOST_TEXT,
                activebackground="#1b315d",
                activeforeground=HOST_TEXT,
                relief=tk.FLAT,
                font=self.done_font if was_announced else self.normal_font,
                anchor="w",
                justify=tk.LEFT,
                wraplength=500,
                padx=12,
                pady=9,
            )
            button.pack(fill="x", pady=4)
            self.question_buttons.append(button)

        for button in self.option_buttons:
            button.config(state=tk.NORMAL)

    def question_bg(self, index, current_index, was_announced, answer):
        if answer:
            return "#274f3e"
        if index == current_index:
            return HOST_ACCENT
        if was_announced:
            return "#263a66"
        return HOST_PANEL_ALT

    def select_question(self, index):
        if server_logic.select_interactive_poll_question_from_host(index):
            self.parent.log(f"Poll: công bố câu {index + 1}.")
        self.refresh()

    def choose_answer(self, answer):
        if server_logic.answer_interactive_poll_from_host(answer):
            self.parent.log(f"Poll: khán giả chọn đáp án {answer}.")
        self.refresh()

    def close(self):
        self.parent.poll_window = None
        self.destroy()

class AudienceDialog(simpledialog.Dialog):
    def body(self, master):
        self.title("Hỏi Ý Kiến Khán Giả")
        self.remaining_seconds = 30
        self.timer_job = None
        tk.Label(master, text="Nhập câu trả lời của 3 khán giả may mắn:").pack()
        self.timer_label = tk.Label(master, text="", fg="red", font=("Segoe UI", 10, "bold"))
        self.timer_label.pack(pady=(2, 8))
        self.entries = []
        for i in range(3):
            frame = tk.Frame(master)
            tk.Label(frame, text=f"Khán giả {i+1}:").pack(side="left")
            entry = tk.Entry(frame, width=5)
            entry.pack(side="left", padx=5)
            self.entries.append(entry)
            frame.pack(pady=2)
        self.update_countdown()
        return self.entries[0]

    def update_countdown(self):
        self.timer_label.config(text=f"Tự động chốt sau {self.remaining_seconds:02d} giây")
        if self.remaining_seconds <= 0:
            self.timer_job = None
            self.ok()
            return
        self.remaining_seconds -= 1
        self.timer_job = self.after(1000, self.update_countdown)

    def cancel(self, event=None):
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except tk.TclError:
                pass
            self.timer_job = None
        super().cancel(event)

    def apply(self):
        self.result = [e.get().strip() for e in self.entries]

class CallDialog(simpledialog.Dialog):
    def __init__(self, parent, question, answer):
        self.question = question
        self.answer = answer
        self.remaining_seconds = 30
        self.timer_job = None
        super().__init__(parent, "Gọi Điện Cho Người Thân")

    def body(self, master):
        tk.Label(master, text="Nhập gợi ý từ cuộc gọi 30 giây:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(master, text=f"Câu hỏi: {self.question}", wraplength=520, justify=tk.LEFT).pack(anchor="w", pady=(8, 2))
        tk.Label(master, text=f"Đáp án đúng nội bộ: {self.answer}", fg="#7a4b00").pack(anchor="w", pady=(0, 8))
        self.timer_label = tk.Label(master, text="", fg="red", font=("Segoe UI", 10, "bold"))
        self.timer_label.pack(anchor="w", pady=(0, 8))
        self.entry = tk.Entry(master, width=58)
        self.entry.pack(fill="x")
        self.update_countdown()
        return self.entry

    def update_countdown(self):
        self.timer_label.config(text=f"Tự động chốt sau {self.remaining_seconds:02d} giây")
        if self.remaining_seconds <= 0:
            self.timer_job = None
            self.ok()
            return
        self.remaining_seconds -= 1
        self.timer_job = self.after(1000, self.update_countdown)

    def cancel(self, event=None):
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except tk.TclError:
                pass
            self.timer_job = None
        super().cancel(event)

    def apply(self):
        self.result = self.entry.get().strip()

if __name__ == "__main__":
    app = HostGUI()
    app.mainloop()
