import socket
import json
import threading
import tkinter as tk
from tkinter import messagebox
import random
import string
import time
try:
    from ui_assets import ColorButton, apply_window_icon, load_background_source, load_button_images, load_logo_photo, load_lozenge_photo, render_background
except ImportError:
    messagebox.showerror("Thiếu thư viện", "Vui lòng cài đặt: pip install Pillow")
    exit()
from audio_backend import AudioManager
from app_info import APP_AUTHOR, APP_VERSION

# --- CẤU HÌNH ---
PORT = 65432
BUFFER_SIZE = 4096
PRIZE_LEVELS = [
    "500.000.000", "250.000.000", "120.000.000", "60.000.000", "30.000.000",
    "22.000.000", "14.000.000", "10.000.000", "8.000.000", "6.000.000",
    "5.000.000", "4.000.000", "3.000.000", "2.000.000", "1.000.000"
]

# Màu sắc - làm đậm màu đáp án
GRADIENT_START = "#081d4f"
GRADIENT_END = "#030712"
WIDGET_BG = "#07143a"
PANEL_BG = "#0F254E"
PANEL_BORDER = "#00D2FF"
TEXT_MUTED = "#aebbe8"
MILESTONE_COLOR = "#ffffff"
CURRENT_COLOR = "#FF9900"
DEFAULT_PRIZE_COLOR = "#FF9900"
PASSED_PRIZE_COLOR = "#7f8c8d"

class GameClientGUI(tk.Toplevel):
    def __init__(self, master, player_name, player_id, server_ip, audio_manager):
        super().__init__(master)
        self.title(f"Ai Là Triệu Phú - {player_name}")
        apply_window_icon(self)
        self.geometry("1280x720")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.withdraw()

        self.player_name = player_name
        self.player_id = player_id
        self.server_ip = server_ip
        self.client_socket = None
        self.audio_manager = audio_manager
        self.current_lifelines_state = {}
        self.current_level = 0
        self.game_has_ended = False
        self.final_animation_job = None
        self.pending_lifeline_type = None
        self.pending_lifeline_job = None
        self.lifeline_audio_job = None
        self.answer_buttons_locked = False
        self.last_background_music = None

        self.load_assets()
        self.create_widgets()
        self.connect_and_start()

    def load_assets(self):
        try:
            self.background_source = load_background_source()
            self.btn_images = load_button_images((470, 82))
            self.logo_image = load_logo_photo((72, 72))
            self.question_panel_image = load_lozenge_photo((880, 135), "normal", radius=18)
            self.prize_row_images = {
                "normal": load_lozenge_photo((300, 31), "normal", radius=7),
                "milestone": load_lozenge_photo((300, 31), "milestone", radius=7),
                "selected": load_lozenge_photo((300, 31), "selected", radius=7),
                "dim": load_lozenge_photo((300, 31), "dim", radius=7),
            }
        except Exception as e:
            messagebox.showerror("Lỗi Tải Ảnh", f"Không thể tải ảnh: {e}")
            self.on_closing()

    def create_widgets(self):
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.draw_gradient)

        self.status_bar = tk.Label(
            self,
            text="...",
            bd=0,
            anchor=tk.W,
            fg=TEXT_MUTED,
            bg="#020817",
            font=("Segoe UI", 10),
            padx=14,
            pady=5,
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.prize_frame = tk.Frame(self.canvas, bg="#050b23", highlightthickness=1, highlightbackground="#243b78")
        self.prize_frame.place(relx=0.75, rely=0, relwidth=0.25, relheight=1)
        self.prize_background_label = tk.Label(self.prize_frame, bd=0)
        self.prize_background_label.place(x=0, y=0, relwidth=1, relheight=1)

        tk.Label(
            self.prize_frame,
            text="MỐC THƯỞNG",
            font=("Segoe UI", 15, "bold"),
            fg=PANEL_BORDER,
            bg="#050b23",
            anchor="w",
        ).pack(fill='x', padx=20, pady=(18, 10))

        self.prize_labels = []
        for i, prize in enumerate(PRIZE_LEVELS):
            label = tk.Label(
                self.prize_frame,
                text=f"{15 - i:2d}  ♦  {prize}",
                image=self.prize_row_images["normal"],
                compound=tk.CENTER,
                font=("Segoe UI", 12, "bold"),
                bg="#050b23",
                fg="white",
                bd=0,
                highlightthickness=0,
            )
            label.pack(fill='x', padx=14, pady=2)
            self.prize_labels.append(label)

        self.main_frame = tk.Frame(self.canvas, bg=WIDGET_BG)
        self.main_frame.place(relx=0, rely=0, relwidth=0.75, relheight=1)
        self.main_background_label = tk.Label(self.main_frame, bd=0)
        self.main_background_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.header_frame = tk.Frame(self.main_frame, bg="#061128")
        self.header_frame.place(relx=0.04, rely=0.035, width=650, height=88)

        if self.logo_image:
            tk.Label(self.header_frame, image=self.logo_image, bg="#061128").pack(side=tk.LEFT, padx=(0, 14))

        title_frame = tk.Frame(self.header_frame, bg="#061128")
        title_frame.pack(side=tk.LEFT, fill="y")
        tk.Label(
            title_frame,
            text="AI LÀ TRIỆU PHÚ",
            font=("Segoe UI", 25, "bold"),
            fg="white",
            bg="#061128",
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_frame,
            text=f"Thí sinh: {self.player_name}",
            font=("Segoe UI", 12),
            fg=TEXT_MUTED,
            bg="#061128",
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        self.game_area = tk.Frame(self.main_frame, bg=WIDGET_BG)
        self.game_area.place(relx=0.5, rely=0.58, anchor=tk.CENTER, relwidth=1, relheight=0.74)
        self.game_background_label = tk.Label(self.game_area, bd=0)
        self.game_background_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.lbl_question = tk.Label(self.game_area, text="...", image=self.question_panel_image,
                                   compound=tk.CENTER, font=("Arial", 20, "bold"),
                                   fg="white", bg=WIDGET_BG, wraplength=820, justify=tk.CENTER,
                                   highlightthickness=0, padx=24, pady=18)
        self.lbl_question.place(relx=0.5, rely=0.2, anchor=tk.CENTER, width=880, height=135)

        self.lifeline_frame = tk.Frame(self.main_frame, bg=WIDGET_BG)
        self.lifeline_frame.place(relx=0.5, rely=0.205, anchor=tk.CENTER)

        self.lifeline_buttons = {}
        lifeline_texts = {"5050": "50:50", "audience": "Khán Giả", "call": "Gọi Điện", "wise_man": "Tư Vấn"}

        for key, text in lifeline_texts.items():
            btn = ColorButton(self.lifeline_frame, text=text, font=("Arial", 12, "bold"),
                          fg="white", bg="#10265f", activebackground="#173783",
                          activeforeground="white", disabledforeground="#61719d",
                          relief=tk.FLAT, bd=0, padx=16, pady=8, state="disabled",
                          command=lambda k=key: self.use_lifeline(k))
            btn.pack(side=tk.LEFT, padx=7, pady=8)
            self.lifeline_buttons[key] = btn

        self.option_buttons = {}
        self.option_positions = {}
        positions = [(0.25, 0.57), (0.75, 0.57), (0.25, 0.80), (0.75, 0.80)]

        for i, option in enumerate(["A", "B", "C", "D"]):
            relx, rely = positions[i]
            btn = ColorButton(self.game_area, image=self.btn_images['normal'],
                          font=("Segoe UI", 15, "bold"), fg="white", bd=0,
                          activebackground=WIDGET_BG, activeforeground="white",
                          highlightthickness=0, compound=tk.CENTER, state="disabled",
                          wraplength=410, justify=tk.CENTER, padx=12, pady=2,
                          bg=WIDGET_BG, disabledforeground="#d7dbea",
                          command=lambda o=option: self.send_answer(o))
            btn.place(relx=relx, rely=rely, anchor=tk.CENTER, width=470, height=82)
            self.option_buttons[option] = btn
            self.option_positions[option] = {'relx': relx, 'rely': rely}

        self.overlay_frame = tk.Frame(
            self.main_frame,
            bg=PANEL_BG,
            highlightthickness=2,
            highlightbackground=PANEL_BORDER,
            padx=36,
            pady=28,
        )
        self.overlay_label = tk.Label(self.overlay_frame, font=("Arial", 24, "bold"),
                                    fg="white", bg=PANEL_BG, wraplength=680, justify=tk.CENTER)
        self.overlay_label.pack(pady=20)

        self.ready_button = ColorButton(self.overlay_frame, text="Sẵn Sàng!",
                                    font=("Arial", 24, "bold"), command=self.send_ready,
                                    bg="#0f8f5f", activebackground="#12a873",
                                    fg="white", activeforeground="white",
                                    relief=tk.FLAT, padx=28, pady=10)
        self.return_button = ColorButton(
            self.overlay_frame,
            text="Kết thúc lượt chơi",
            font=("Segoe UI", 16, "bold"),
            command=self.on_closing,
            bg="#33456f",
            activebackground="#405785",
            fg="white",
            activeforeground="white",
            relief=tk.FLAT,
            padx=24,
            pady=10,
        )

    def draw_gradient(self, event):
        self.canvas.delete("gradient")
        width, height = event.width, event.height
        if width <= 0 or height <= 0:
            return

        self.gradient_image = render_background(
            self.background_source,
            (width, height),
            GRADIENT_START,
            GRADIENT_END,
        )
        self.canvas.create_image(0, 0, image=self.gradient_image, anchor="nw", tags="gradient")
        self.canvas.tag_lower("gradient")
        self.update_panel_backgrounds(width, height)

    def update_panel_backgrounds(self, width, height):
        if not hasattr(self, "main_background_label"):
            return

        main_width = max(1, int(width * 0.75))
        prize_width = max(1, width - main_width)
        game_height = max(1, int(height * 0.74))

        self.main_background_image = render_background(
            self.background_source,
            (main_width, height),
            GRADIENT_START,
            GRADIENT_END,
        )
        self.main_background_label.config(image=self.main_background_image)
        self.main_background_label.lower()

        self.game_background_image = render_background(
            self.background_source,
            (main_width, game_height),
            GRADIENT_START,
            GRADIENT_END,
        )
        self.game_background_label.config(image=self.game_background_image)
        self.game_background_label.lower()

        self.prize_background_image = render_background(
            self.background_source,
            (prize_width, height),
            GRADIENT_START,
            GRADIENT_END,
        )
        self.prize_background_label.config(image=self.prize_background_image)
        self.prize_background_label.lower()

    def show_overlay(self, message, show_ready_btn=False, show_return_btn=False):
        self.game_area.place_forget()
        self.lifeline_frame.place_forget()
        self.overlay_label.config(text=message)

        if show_ready_btn:
            self.ready_button.pack(pady=20)
            self.audio_manager.play('ready', loop=True)
        else:
            self.ready_button.pack_forget()

        if show_return_btn:
            self.return_button.pack(pady=(4, 0))
        else:
            self.return_button.pack_forget()

        self.overlay_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def hide_overlay(self):
        self.stop_final_animation()
        self.overlay_frame.place_forget()
        self.lifeline_frame.place(relx=0.5, rely=0.205, anchor=tk.CENTER)
        self.game_area.place(relx=0.5, rely=0.58, anchor=tk.CENTER, relwidth=1, relheight=0.74)
        self.main_background_label.lower()
        self.game_background_label.lower()
        self.lbl_question.tkraise()
        for button in self.option_buttons.values():
            button.tkraise()
        self.lifeline_frame.tkraise()

    def stop_final_animation(self):
        if self.final_animation_job:
            try:
                self.after_cancel(self.final_animation_job)
            except tk.TclError:
                pass
            self.final_animation_job = None
        self.overlay_frame.config(highlightbackground=PANEL_BORDER)
        self.overlay_label.config(fg="white")

    def start_final_animation(self, is_win):
        colors = ["#d7b75a", "#ffffff", "#16a06b"] if is_win else ["#d9485f", "#ffffff", "#d7b75a"]

        def animate(step=0):
            color = colors[step % len(colors)]
            self.overlay_frame.config(highlightbackground=color)
            self.overlay_label.config(fg=color if is_win else "white")
            self.final_animation_job = self.after(360, lambda: animate(step + 1))

        self.stop_final_animation()
        animate()

    def send_ready(self):
        self.send_data({'ready': True})
        self.hide_overlay()

    def option_font_for_text(self, text):
        length = len(text)
        if length >= 86:
            size = 10
        elif length >= 64:
            size = 11
        elif length >= 44:
            size = 12
        else:
            size = 15
        return ("Segoe UI", size, "bold")

    def set_option_button_text(self, option, option_text):
        display_text = f"{option}: {option_text}"
        self.option_buttons[option].config(
            text=display_text,
            font=self.option_font_for_text(display_text),
            wraplength=410,
            justify=tk.CENTER,
            anchor=tk.CENTER,
        )

    def update_question_display(self, data):
        self.game_has_ended = False
        self.answer_buttons_locked = False
        self.current_level = data['level']
        self.current_lifelines_state = data['lifelines']
        if self.pending_lifeline_type == '5050':
            self.finish_lifeline('5050', update_buttons=False)
        self.lbl_question.config(text=f"CÂU {self.current_level} - {data['prize']} VNĐ\n{data['question']}")

        for option, btn in self.option_buttons.items():
            pos = self.option_positions[option]
            option_text = data['options'].get(option, '')
            if option_text:
                btn.place(relx=pos['relx'], rely=pos['rely'], anchor=tk.CENTER, width=470, height=82)
                self.set_option_button_text(option, option_text)
                btn.config(state="normal", image=self.btn_images['normal'])
            else:
                btn.place_forget()

        self.update_lifeline_buttons()
        self.update_prize_display()
        self.play_music_by_level()
        self.status_bar.config(text=f"Đang chờ thí sinh trả lời câu {self.current_level}...")

    def update_lifeline_buttons(self):
        for key, btn in self.lifeline_buttons.items():
            is_available = self.current_lifelines_state.get(key, False)
            if key == 'wise_man' and self.current_level < 6:
                is_available = False
            if self.pending_lifeline_type:
                is_available = False
            btn.config(state="normal" if is_available else "disabled")

    def update_prize_display(self):
        for i, label in enumerate(self.prize_labels):
            prize_level = 15 - i
            is_milestone = prize_level in [5, 10, 15]

            if prize_level < self.current_level:
                label.config(image=self.prize_row_images["dim"], bg="#050b23", fg=PASSED_PRIZE_COLOR)
            elif prize_level == self.current_level:
                label.config(image=self.prize_row_images["selected"], bg="#050b23", fg="#050E21")
            else:
                color = MILESTONE_COLOR if is_milestone else DEFAULT_PRIZE_COLOR
                image_key = "milestone" if is_milestone else "normal"
                label.config(image=self.prize_row_images[image_key], bg="#050b23", fg=color)

    def play_music_by_level(self):
        if 1 <= self.current_level <= 5:
            self.play_background_music('wait_1_5')
        elif 6 <= self.current_level <= 10:
            self.play_background_music('wait_6_10')
        elif 11 <= self.current_level <= 15:
            self.play_background_music('wait_11_15')

    def play_background_music(self, name, loop=True):
        self.last_background_music = (name, loop)
        self.audio_manager.play(name, loop=loop)

    def resume_background_music(self):
        if self.game_has_ended:
            return
        if self.last_background_music:
            name, loop = self.last_background_music
            self.audio_manager.play(name, loop=loop)
        else:
            self.play_music_by_level()

    def set_visible_answer_buttons_state(self, state):
        self.answer_buttons_locked = state != "normal"
        for btn in self.option_buttons.values():
            if btn.winfo_ismapped():
                btn.config(state="normal")

    def handle_lifeline_result(self, data):
        lifeline_type = data.get('lifeline', 'unknown')
        if lifeline_type in self.current_lifelines_state:
            self.current_lifelines_state[lifeline_type] = False

        if lifeline_type == 'audience':
            opinions = data.get('opinions', [])
            message = "Ý kiến từ 3 khán giả may mắn:\n\n"
            if opinions:
                message += "\n".join([f"  - Khán giả {i+1} chọn: {ans}" for i, ans in enumerate(opinions)])
            else:
                message += "Không có dữ liệu hợp lệ từ khán giả."
            messagebox.showinfo("Trợ giúp", message)
        elif lifeline_type in ['call', 'wise_man']:
            messagebox.showinfo("Trợ giúp", data.get('message', 'Không có dữ liệu trợ giúp.'))
        elif data.get('message'):
            messagebox.showinfo("Trợ giúp", data['message'])

        self.finish_lifeline(lifeline_type)

    def send_answer(self, answer):
        if self.answer_buttons_locked:
            self.status_bar.config(text="Đang khóa đáp án trong lúc chạy hiệu ứng, vui lòng chờ...")
            return
        self.cancel_pending_lifeline(update_buttons=False)
        self.answer_buttons_locked = True
        self.audio_manager.play('selected')

        for btn in self.option_buttons.values():
            btn.config(state="normal")
        for btn in self.lifeline_buttons.values():
            btn.config(state="disabled")

        self.option_buttons[answer].config(image=self.btn_images['selected'])
        self.send_data({
            'action': 'answer_locked',
            'value': answer,
            'timestamp': time.time()
        })

        # Blinking effect
        self.blinking_animation(self.option_buttons[answer], 6, 250)
        if self.current_level >= 6:
            self.status_bar.config(text=f"Đã chốt đáp án {answer}. Chờ MC công bố kết quả...")
        else:
            self.after(900, lambda: self.send_data({
                'action': 'answer',
                'value': answer,
                'timestamp': time.time()
            }))

    def blinking_animation(self, button, times, delay):
        if times > 0 and self.client_socket:
            current_image = button.cget("image")
            new_image = (self.btn_images['normal'] if str(current_image) == str(self.btn_images['selected'])
                        else self.btn_images['selected'])
            button.config(image=new_image)
            self.after(delay, lambda: self.blinking_animation(button, times - 1, delay))
        elif self.client_socket:
            button.config(image=self.btn_images['selected'])

    def show_answer_result(self, data):
        is_correct = data['correct']
        correct_answer = data['correct_answer']

        self.audio_manager.stop_all()

        # Show correct/wrong answers
        for key, btn in self.option_buttons.items():
            if btn.winfo_ismapped():
                if key == correct_answer:
                    btn.config(image=self.btn_images['correct'])
                else:
                    btn.config(image=self.btn_images['wrong'])

        if data.get('give_up_regret'):
            if is_correct:
                self.audio_manager.play('correct')
                result_text = "đúng"
            else:
                self.audio_manager.play('wrong')
                result_text = "sai"
            self.status_bar.config(
                text=f"Đáp án tiếc nuối {result_text}. Đáp án đúng: {correct_answer}. Chờ host kết màn hình..."
            )
            return

        if is_correct:
            self.audio_manager.play('correct')
            if self.current_level < 5 or self.current_level >= len(PRIZE_LEVELS):
                self.status_bar.config(text="Chính xác. Đang chuyển sang trạng thái tiếp theo...")
                return
            self.after(3500, lambda: self.show_overlay(
                f"Sẵn sàng cho câu số {self.current_level + 1}?", True))
        else:
            self.audio_manager.play('wrong')
            self.status_bar.config(text="Sai đáp án. Đang tổng kết phần thi...")
            return

        # Update ping status
        ping = data.get('ping', 999)
        if ping < 80:
            status = "Rất Tốt"
        elif ping < 150:
            status = "Tốt"
        elif ping < 300:
            status = "Trung Bình"
        else:
            status = "Yếu"
        self.status_bar.config(text=f"Ping: {ping:.0f}ms ({status})")

    def unlock_answer_selection(self):
        self.answer_buttons_locked = False
        for option, btn in self.option_buttons.items():
            if btn.winfo_ismapped():
                btn.config(state="normal", image=self.btn_images['normal'])
        self.update_lifeline_buttons()
        self.status_bar.config(text="Host đã hủy chốt đáp án. Vui lòng chọn lại.")

    def connect_and_start(self):
        self.deiconify()
        self.status_bar.config(text=f"Đang kết nối tới {self.server_ip}...")
        threading.Thread(target=self._connect_in_thread, daemon=True).start()

    def _connect_in_thread(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, PORT))

            # Send player info
            player_info = {'name': self.player_name, 'id': self.player_id}
            self.client_socket.sendall((json.dumps(player_info) + '\n').encode('utf-8'))

            self.master.withdraw()
            self.status_bar.config(text=f"Đã kết nối tới {self.server_ip}")

            threading.Thread(target=self.listen_for_messages, daemon=True).start()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Lỗi Kết Nối", f"Không thể kết nối: {e}"))
            self.after(0, self.on_closing)

    def listen_for_messages(self):
        buffer = ""
        while self.client_socket:
            try:
                raw_data = self.client_socket.recv(BUFFER_SIZE)
                if not raw_data:
                    break

                buffer += raw_data.decode('utf-8')
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    self.after(0, self.process_message, json.loads(message))
            except Exception:
                break

        self.after(0, self.handle_disconnection)

    def process_message(self, data):
        msg_type = data.get('type')

        if msg_type == 'ask_ready':
            self.show_overlay(f"Sẵn sàng cho câu số {data['level']}?", show_ready_btn=True)
        elif msg_type == 'question':
            self.hide_overlay()
            self.update_question_display(data)
        elif msg_type == 'lifeline_result':
            self.handle_lifeline_result(data)
        elif msg_type == 'result':
            self.show_answer_result(data)
        elif msg_type == 'answer_unlocked':
            if data.get('level') == self.current_level:
                self.unlock_answer_selection()
        elif msg_type == 'give_up_regret':
            self.enter_give_up_regret_mode(data)
        elif msg_type == 'win':
            self.handle_win(data)
        elif msg_type == 'game_over':
            self.handle_game_over(data)
        elif msg_type == 'game_paused':
            if data['paused']:
                message = "CHƯƠNG TRÌNH ĐÃ KẾT THÚC\nClient đang ở chế độ tạm dừng." if data.get('reason') == 'program_end' else "GAME TẠM DỪNG BỞI HOST"
                self.show_overlay(message)
                self.last_background_music = None
                self.audio_manager.stop_all()
                if data.get('reason') == 'program_end':
                    self.play_program_end_audio()
            else:
                self.hide_overlay()
                self.play_music_by_level()
        elif msg_type == 'set_mute':
            muted = data.get('value', False)
            self.audio_manager.set_mute(muted)
            if not muted:
                self.resume_background_music()
        elif msg_type == 'set_beta':
            is_beta = data.get('value', False)
            title = f"Ai Là Triệu Phú (BETA) - {self.player_name}" if is_beta else f"Ai Là Triệu Phú - {self.player_name}"
            self.title(title)
        elif msg_type == 'play_music':
            self.play_background_music(data.get('name', 'wait_11_15'), loop=data.get('loop', True))
        elif msg_type == 'stop_music':
            self.last_background_music = None
            self.audio_manager.stop_all()
        elif msg_type == 'play_effect':
            self.audio_manager.play(data.get('name', 'end_buzzer'))
        elif msg_type == 'server_busy':
            messagebox.showerror("Server bận", data.get('message', 'Đã có thí sinh đang chơi.'))
            self.on_closing()

    def play_lifeline_audio(self, lifeline_type):
        sound_by_type = {
            '5050': 'lifeline_5050',
            'audience': 'audience_countdown',
            'call': 'lifeline_call',
            'wise_man': 'lifeline_wise_man',
        }
        sound_name = sound_by_type.get(lifeline_type, 'lifeline')
        self.audio_manager.stop_all()
        if self.audio_manager.has_sound('lifeline_click'):
            self.audio_manager.play('lifeline_click')
            self.lifeline_audio_job = self.after(650, lambda: self.play_lifeline_intro(sound_name))
        else:
            self.play_lifeline_intro(sound_name)

    def play_lifeline_intro(self, sound_name):
        self.lifeline_audio_job = None
        if self.audio_manager.has_sound(sound_name):
            self.audio_manager.play(sound_name, loop=False)
        else:
            self.audio_manager.play('lifeline', loop=True)

    def cancel_pending_lifeline(self, update_buttons=True):
        if self.pending_lifeline_job:
            try:
                self.after_cancel(self.pending_lifeline_job)
            except tk.TclError:
                pass
            self.pending_lifeline_job = None
        if self.lifeline_audio_job:
            try:
                self.after_cancel(self.lifeline_audio_job)
            except tk.TclError:
                pass
            self.lifeline_audio_job = None
        self.pending_lifeline_type = None
        if update_buttons:
            self.update_lifeline_buttons()

    def finish_lifeline(self, lifeline_type=None, update_buttons=True):
        self.pending_lifeline_job = None
        self.pending_lifeline_type = None
        self.play_music_by_level()
        self.set_visible_answer_buttons_state("normal")
        if update_buttons:
            self.update_lifeline_buttons()

    def send_lifeline_request(self, lifeline_type):
        self.pending_lifeline_job = None
        self.send_data({
            'action': 'lifeline',
            'value': lifeline_type,
            'timestamp': time.time()
        })

    def use_lifeline(self, lifeline_type):
        if self.pending_lifeline_type:
            self.status_bar.config(text="Đang chạy hiệu ứng trợ giúp, vui lòng chờ kết quả...")
            return
        if not self.current_lifelines_state.get(lifeline_type, False):
            return
        self.play_lifeline_audio(lifeline_type)
        self.pending_lifeline_type = lifeline_type
        self.current_lifelines_state[lifeline_type] = False
        self.set_visible_answer_buttons_state("disabled")
        self.update_lifeline_buttons()
        delay_ms = 2000 if lifeline_type == 'audience' else 5000
        delay_seconds = delay_ms // 1000
        self.status_bar.config(text=f"Đã chọn trợ giúp. Đang chạy hiệu ứng {delay_seconds} giây trước khi mở kết quả...")
        self.pending_lifeline_job = self.after(delay_ms, lambda: self.send_lifeline_request(lifeline_type))

    def enter_give_up_regret_mode(self, data):
        self.cancel_pending_lifeline(update_buttons=False)
        self.last_background_music = None
        self.audio_manager.stop_all()
        self.answer_buttons_locked = False
        for key in list(self.current_lifelines_state):
            self.current_lifelines_state[key] = False
        self.set_visible_answer_buttons_state("normal")
        self.update_lifeline_buttons()
        self.status_bar.config(
            text=f"Đã dừng cuộc chơi ở câu {data.get('level')}. Hãy chọn đáp án tiếc nuối..."
        )

    def send_data(self, data):
        try:
            if self.client_socket:
                message = json.dumps(data) + '\n'
                self.client_socket.sendall(message.encode('utf-8'))
        except socket.error:
            self.handle_disconnection()

    def show_final_overlay(self, title, player_name, prize, is_win):
        self.game_has_ended = True
        prize_text = f"{prize} VNĐ" if prize else "0 VNĐ"
        message = f"{title}\n\n{player_name}\nSố tiền nhận được: {prize_text}"
        self.show_overlay(message, show_return_btn=True)
        self.start_final_animation(is_win)

    def play_program_end_audio(self):
        if self.audio_manager.has_sound('program_end'):
            self.audio_manager.play('program_end')
        elif self.audio_manager.has_sound('end_game'):
            self.audio_manager.play('end_game')

    def play_final_audio(self, is_win, with_buzzer=False):
        self.audio_manager.stop_all()
        delay = 0
        if with_buzzer and self.audio_manager.has_sound('end_buzzer'):
            self.audio_manager.play('end_buzzer')
            delay = 1200

        def play_main_theme():
            if is_win and self.audio_manager.has_sound('complete'):
                self.audio_manager.play('complete')
            elif is_win and self.audio_manager.has_sound('program_end'):
                self.audio_manager.play('program_end')
            elif is_win:
                self.audio_manager.play('win')
            else:
                self.audio_manager.play('end_game')

        if delay:
            self.after(delay, play_main_theme)
        else:
            play_main_theme()

    def handle_win(self, data=None):
        data = data or {}
        self.play_final_audio(True)
        self.show_final_overlay(
            "CHÚC MỪNG TRIỆU PHÚ",
            data.get('player_name', self.player_name),
            data.get('prize', '500.000.000'),
            True,
        )

    def handle_game_over(self, data=None):
        data = data or {}
        self.play_final_audio(False)
        title = "THÍ SINH DỪNG CUỘC CHƠI" if data.get('reason') == 'give_up' else "PHẦN THI KẾT THÚC"
        self.show_final_overlay(
            title,
            data.get('player_name', self.player_name),
            data.get('prize', '0'),
            False,
        )

    def handle_disconnection(self):
        if self.client_socket:
            self.client_socket = None
            if self.game_has_ended:
                return
            messagebox.showerror("Mất kết nối", "Mất kết nối tới server.")
            self.on_closing()

    def on_closing(self):
        self.stop_final_animation()
        self.cancel_pending_lifeline(update_buttons=False)
        self.audio_manager.stop_all()
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        self.master.on_return()
        self.destroy()

class WelcomeScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ai Là Triệu Phú - Chào mừng")
        apply_window_icon(self)
        self.geometry("460x430")
        self.minsize(460, 430)
        self.configure(bg=WIDGET_BG)
        self.welcome_frame = tk.Frame(self, bg=WIDGET_BG)
        self.welcome_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=420)
        self.bind("<Configure>", self.layout_welcome)

        self.audio_manager = AudioManager()
        self.audio_manager.play('welcome', loop=True)

        try:
            logo_image = load_logo_photo((120, 120))
            if not logo_image:
                raise FileNotFoundError("images/logo.png")
            tk.Label(self.welcome_frame, image=logo_image, bg=WIDGET_BG).pack(pady=(0, 8))
            self.logo_image = logo_image
        except Exception:
            tk.Label(self.welcome_frame, text="AI LÀ TRIỆU PHÚ", font=("Segoe UI", 24, "bold"), bg=WIDGET_BG, fg="white").pack(pady=(0, 12))

        tk.Label(self.welcome_frame, text="AI LÀ TRIỆU PHÚ", font=("Segoe UI", 20, "bold"), bg=WIDGET_BG, fg="white").pack()
        tk.Label(self.welcome_frame, text="Kết nối thí sinh", font=("Segoe UI", 11), bg=WIDGET_BG, fg=TEXT_MUTED).pack(pady=(0, 18))

        form_frame = tk.Frame(self.welcome_frame, bg=WIDGET_BG)
        form_frame.pack(fill="x", padx=56)

        tk.Label(form_frame, text="Tên thí sinh", bg=WIDGET_BG, fg=TEXT_MUTED, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        self.name_entry = tk.Entry(form_frame, width=30, font=("Segoe UI", 12), bd=0, relief=tk.FLAT)
        self.name_entry.pack(fill="x", ipady=8, pady=(4, 12))

        tk.Label(form_frame, text="Địa chỉ IP Server", bg=WIDGET_BG, fg=TEXT_MUTED, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        self.ip_entry = tk.Entry(form_frame, width=30, font=("Segoe UI", 12), bd=0, relief=tk.FLAT)
        self.ip_entry.pack(fill="x", ipady=8, pady=(4, 16))

        ColorButton(
            self.welcome_frame,
            text="Bắt Đầu Chơi",
            font=("Segoe UI", 14, "bold"),
            command=self.start_game,
            bg=PANEL_BORDER,
            activebackground="#f0cf6a",
            fg="#081020",
            activeforeground="#081020",
            relief=tk.FLAT,
            padx=28,
            pady=9,
        ).pack(pady=2)

        tk.Label(self.welcome_frame, text=f"{APP_AUTHOR} | v{APP_VERSION} | 2020 - 2026", bg=WIDGET_BG, fg=TEXT_MUTED,
                font=("Segoe UI", 8, "italic")).pack(pady=(16, 0))

    def layout_welcome(self, event=None):
        if hasattr(self, "welcome_frame"):
            width = min(max(380, self.winfo_width() - 80), 460)
            self.welcome_frame.place_configure(width=width)

    def start_game(self):
        player_name = self.name_entry.get().strip()
        server_ip = self.ip_entry.get().strip()

        if not player_name or not server_ip:
            messagebox.showerror("Thiếu thông tin", "Vui lòng nhập tên và IP.")
            return

        self.audio_manager.stop_all()
        player_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        GameClientGUI(self, player_name, player_id, server_ip, self.audio_manager)

    def on_return(self):
        self.deiconify()
        self.audio_manager.play('welcome', loop=True)

if __name__ == "__main__":
    app = WelcomeScreen()
    app.mainloop()
