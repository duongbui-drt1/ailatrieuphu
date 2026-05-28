import socket
import json
import threading
import tkinter as tk
from tkinter import messagebox
import random
import string
import time
try:
    from ui_assets import load_background_source, load_button_images, load_logo_photo, render_background
except ImportError:
    messagebox.showerror("Thiếu thư viện", "Vui lòng cài đặt: pip install Pillow")
    exit()
from audio_backend import AudioManager

# --- CẤU HÌNH ---
PORT = 65432
BUFFER_SIZE = 4096
PRIZE_LEVELS = [
    "150.000.000", "85.000.000", "60.000.000", "40.000.000", "30.000.000", "22.000.000",
    "14.000.000", "10.000.000", "6.000.000", "3.000.000", "2.000.000", "1.000.000",
    "600.000", "400.000", "200.000"
]

# Màu sắc - làm đậm màu đáp án
GRADIENT_START = "#081d4f"
GRADIENT_END = "#030712"
WIDGET_BG = "#07143a"
PANEL_BG = "#091b4d"
PANEL_BORDER = "#d7b75a"
TEXT_MUTED = "#aebbe8"
MILESTONE_COLOR = "#f39c12"  # Đậm hơn
CURRENT_COLOR = "#f1c40f"    # Đậm hơn
DEFAULT_PRIZE_COLOR = "#3498db"  # Đậm hơn
PASSED_PRIZE_COLOR = "#7f8c8d"

class GameClientGUI(tk.Toplevel):
    def __init__(self, master, player_name, player_id, server_ip, audio_manager):
        super().__init__(master)
        self.title(f"Ai Là Triệu Phú - {player_name}")
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

        self.load_assets()
        self.create_widgets()
        self.connect_and_start()

    def load_assets(self):
        try:
            self.background_source = load_background_source()
            self.btn_images = load_button_images((450, 60))
            self.logo_image = load_logo_photo((72, 72))
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
            label = tk.Label(self.prize_frame, text=f"{15 - i:2d} ♦ {prize}",
                           font=("Segoe UI", 13, "bold"), bg="#050b23", fg="white", anchor='w')
            label.pack(fill='x', padx=20, pady=2)
            self.prize_labels.append(label)

        self.main_frame = tk.Frame(self.canvas, bg=WIDGET_BG)
        self.main_frame.place(relx=0, rely=0, relwidth=0.75, relheight=1)

        self.header_frame = tk.Frame(self.main_frame, bg=WIDGET_BG)
        self.header_frame.place(relx=0.04, rely=0.035, relwidth=0.92, height=88)

        if self.logo_image:
            tk.Label(self.header_frame, image=self.logo_image, bg=WIDGET_BG).pack(side=tk.LEFT, padx=(0, 14))

        title_frame = tk.Frame(self.header_frame, bg=WIDGET_BG)
        title_frame.pack(side=tk.LEFT, fill="both", expand=True)
        tk.Label(
            title_frame,
            text="AI LÀ TRIỆU PHÚ",
            font=("Segoe UI", 25, "bold"),
            fg="white",
            bg=WIDGET_BG,
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_frame,
            text=f"Thí sinh: {self.player_name}",
            font=("Segoe UI", 12),
            fg=TEXT_MUTED,
            bg=WIDGET_BG,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        self.game_area = tk.Frame(self.main_frame, bg=WIDGET_BG)
        self.game_area.place(relx=0.5, rely=0.58, anchor=tk.CENTER, relwidth=1, relheight=0.74)

        self.lbl_question = tk.Label(self.game_area, text="...", font=("Arial", 20, "bold"),
                                   fg="white", bg=PANEL_BG, wraplength=820, justify=tk.CENTER,
                                   highlightthickness=2, highlightbackground=PANEL_BORDER, padx=24, pady=18)
        self.lbl_question.place(relx=0.5, rely=0.2, anchor=tk.CENTER, width=880, height=135)

        self.lifeline_frame = tk.Frame(self.main_frame, bg=WIDGET_BG)
        self.lifeline_frame.place(relx=0.5, rely=0.205, anchor=tk.CENTER)

        self.lifeline_buttons = {}
        lifeline_texts = {"5050": "50:50", "audience": "Khán Giả", "call": "Gọi Điện", "wise_man": "Tư Vấn"}

        for key, text in lifeline_texts.items():
            btn = tk.Button(self.lifeline_frame, text=text, font=("Arial", 12, "bold"),
                          fg="white", bg="#10265f", activebackground="#173783",
                          activeforeground="white", disabledforeground="#61719d",
                          relief=tk.FLAT, bd=0, padx=16, pady=8, state="disabled",
                          command=lambda k=key: self.use_lifeline(k))
            btn.pack(side=tk.LEFT, padx=7, pady=8)
            self.lifeline_buttons[key] = btn

        self.option_buttons = {}
        self.option_positions = {}
        positions = [(0.25, 0.58), (0.75, 0.58), (0.25, 0.79), (0.75, 0.79)]

        for i, option in enumerate(["A", "B", "C", "D"]):
            relx, rely = positions[i]
            btn = tk.Button(self.game_area, image=self.btn_images['normal'],
                          font=("Segoe UI", 15, "bold"), fg="white", bd=0,
                          activebackground=WIDGET_BG, activeforeground="white",
                          highlightthickness=0, compound=tk.CENTER, state="disabled",
                          command=lambda o=option: self.send_answer(o))
            btn.configure(bg=WIDGET_BG)
            btn.place(relx=relx, rely=rely, anchor=tk.CENTER)
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

        self.ready_button = tk.Button(self.overlay_frame, text="Sẵn Sàng!",
                                    font=("Arial", 24, "bold"), command=self.send_ready,
                                    bg="#0f8f5f", activebackground="#12a873",
                                    fg="white", activeforeground="white",
                                    relief=tk.FLAT, padx=28, pady=10)
        self.return_button = tk.Button(
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

    def update_question_display(self, data):
        self.game_has_ended = False
        self.current_level = data['level']
        self.current_lifelines_state = data['lifelines']
        self.lbl_question.config(text=f"CÂU {self.current_level} - {data['prize']} VNĐ\n{data['question']}")

        for option, btn in self.option_buttons.items():
            pos = self.option_positions[option]
            btn.place(relx=pos['relx'], rely=pos['rely'], anchor=tk.CENTER)
            btn.config(text=f"{option}: {data['options'][option]}",
                      state="normal", image=self.btn_images['normal'])

        self.update_lifeline_buttons()
        self.update_prize_display()
        self.play_music_by_level()
        self.status_bar.config(text=f"Đang chờ thí sinh trả lời câu {self.current_level}...")

    def update_lifeline_buttons(self):
        for key, btn in self.lifeline_buttons.items():
            is_available = self.current_lifelines_state.get(key, False)
            if key == 'wise_man' and self.current_level < 5:
                is_available = False
            btn.config(state="normal" if is_available else "disabled")

    def update_prize_display(self):
        for i, label in enumerate(self.prize_labels):
            prize_level = 15 - i
            is_milestone = prize_level in [5, 10, 15]

            if prize_level < self.current_level:
                label.config(bg=WIDGET_BG, fg=PASSED_PRIZE_COLOR)
            elif prize_level == self.current_level:
                label.config(bg=CURRENT_COLOR, fg="black")
            else:
                color = MILESTONE_COLOR if is_milestone else DEFAULT_PRIZE_COLOR
                label.config(bg=WIDGET_BG, fg=color)

    def play_music_by_level(self):
        if 1 <= self.current_level <= 5:
            self.audio_manager.play('wait_1_5', loop=True)
        elif 6 <= self.current_level <= 10:
            self.audio_manager.play('wait_6_10', loop=True)
        elif 11 <= self.current_level <= 15:
            self.audio_manager.play('wait_11_15', loop=True)

    def handle_lifeline_result(self, data):
        self.play_music_by_level()
        lifeline_type = data['lifeline']

        if lifeline_type == 'audience':
            opinions = data['opinions']
            message = "Ý kiến từ 3 khán giả may mắn:\n\n"
            message += "\n".join([f"  - Khán giả {i+1} chọn: {ans}" for i, ans in enumerate(opinions)])
            messagebox.showinfo("Trợ giúp", message)
        elif lifeline_type in ['call', 'wise_man']:
            messagebox.showinfo("Trợ giúp", data['message'])

        self.update_lifeline_buttons()

    def send_answer(self, answer):
        self.audio_manager.play('selected')

        # Disable all buttons
        for btn in self.option_buttons.values():
            btn.config(state="disabled")
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
            self.after(1600, lambda: self.send_data({
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
        elif msg_type == 'win':
            self.handle_win(data)
        elif msg_type == 'game_over':
            self.handle_game_over(data)
        elif msg_type == 'game_paused':
            if data['paused']:
                self.show_overlay("GAME TẠM DỪNG BỞI HOST")
                self.audio_manager.stop_all()
            else:
                self.hide_overlay()
                self.play_music_by_level()
        elif msg_type == 'set_mute':
            self.audio_manager.set_mute(data.get('value', False))
        elif msg_type == 'set_beta':
            is_beta = data.get('value', False)
            title = f"Ai Là Triệu Phú (BETA) - {self.player_name}" if is_beta else f"Ai Là Triệu Phú - {self.player_name}"
            self.title(title)
        elif msg_type == 'play_music':
            self.audio_manager.play(data.get('name', 'wait_11_15'), loop=data.get('loop', True))
        elif msg_type == 'stop_music':
            self.audio_manager.stop_all()
        elif msg_type == 'server_busy':
            messagebox.showerror("Server bận", data.get('message', 'Đã có thí sinh đang chơi.'))
            self.on_closing()

    def play_lifeline_audio(self, lifeline_type):
        sound_by_type = {
            '5050': 'lifeline_5050',
            'audience': 'audience_countdown',
            'wise_man': 'lifeline_wise_man',
        }
        sound_name = sound_by_type.get(lifeline_type, 'lifeline')
        if self.audio_manager.has_sound(sound_name):
            self.audio_manager.play(sound_name, loop=False)
        else:
            self.audio_manager.play('lifeline', loop=True)

    def use_lifeline(self, lifeline_type):
        self.play_lifeline_audio(lifeline_type)
        self.lifeline_buttons[lifeline_type].config(state="disabled")
        self.send_data({
            'action': 'lifeline',
            'value': lifeline_type,
            'timestamp': time.time()
        })

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

    def handle_win(self, data=None):
        data = data or {}
        self.audio_manager.stop_all()
        if self.audio_manager.has_sound('complete'):
            self.audio_manager.play('complete')
        else:
            self.audio_manager.play('win')
        self.show_final_overlay(
            "CHÚC MỪNG ĐÃ HOÀN THÀNH PHẦN THI",
            data.get('player_name', self.player_name),
            data.get('prize', '150.000.000'),
            True,
        )

    def handle_game_over(self, data=None):
        data = data or {}
        self.audio_manager.stop_all()
        if self.audio_manager.has_sound('end_game'):
            self.audio_manager.play('end_game')
        else:
            self.audio_manager.play('wrong')
        self.show_final_overlay(
            "PHẦN THI KẾT THÚC",
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
        self.geometry("460x430")
        self.configure(bg=WIDGET_BG)

        self.audio_manager = AudioManager()
        self.audio_manager.play('welcome', loop=True)

        try:
            logo_image = load_logo_photo((120, 120))
            if not logo_image:
                raise FileNotFoundError("images/logo.png")
            tk.Label(self, image=logo_image, bg=WIDGET_BG).pack(pady=(22, 8))
            self.logo_image = logo_image
        except Exception:
            tk.Label(self, text="AI LÀ TRIỆU PHÚ", font=("Segoe UI", 24, "bold"), bg=WIDGET_BG, fg="white").pack(pady=(30, 12))

        tk.Label(self, text="AI LÀ TRIỆU PHÚ", font=("Segoe UI", 20, "bold"), bg=WIDGET_BG, fg="white").pack()
        tk.Label(self, text="Kết nối thí sinh", font=("Segoe UI", 11), bg=WIDGET_BG, fg=TEXT_MUTED).pack(pady=(0, 18))

        form_frame = tk.Frame(self, bg=WIDGET_BG)
        form_frame.pack(fill="x", padx=56)

        tk.Label(form_frame, text="Tên thí sinh", bg=WIDGET_BG, fg=TEXT_MUTED, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        self.name_entry = tk.Entry(form_frame, width=30, font=("Segoe UI", 12), bd=0, relief=tk.FLAT)
        self.name_entry.pack(fill="x", ipady=8, pady=(4, 12))

        tk.Label(form_frame, text="Địa chỉ IP Server", bg=WIDGET_BG, fg=TEXT_MUTED, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        self.ip_entry = tk.Entry(form_frame, width=30, font=("Segoe UI", 12), bd=0, relief=tk.FLAT)
        self.ip_entry.pack(fill="x", ipady=8, pady=(4, 16))

        tk.Button(
            self,
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

        tk.Label(self, text="Duli Production DLV", bg=WIDGET_BG, fg=TEXT_MUTED,
                font=("Segoe UI", 8, "italic")).pack(side="bottom", pady=12)

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
