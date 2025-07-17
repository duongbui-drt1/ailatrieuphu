import socket
import json
import threading
import tkinter as tk
from tkinter import messagebox
import random
import string
import time
import os
try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError: 
    messagebox.showerror("Thiếu thư viện", "Vui lòng cài đặt: pip install Pillow")
    exit()
try:
    import pygame
except ImportError: 
    messagebox.showerror("Thiếu thư viện", "Vui lòng cài đặt: pip install pygame")
    exit()

# --- CẤU HÌNH ---
PORT = 65432
BUFFER_SIZE = 4096
PRIZE_LEVELS = [
    "150.000.000", "85.000.000", "60.000.000", "40.000.000", "30.000.000", "22.000.000",
    "14.000.000", "10.000.000", "6.000.000", "3.000.000", "2.000.000", "1.000.000",
    "600.000", "400.000", "200.000"
]

# Màu sắc - làm đậm màu đáp án
GRADIENT_START = "#1a237e"
GRADIENT_END = "#0d1b2a"
WIDGET_BG = "#1a237e"
MILESTONE_COLOR = "#f39c12"  # Đậm hơn
CURRENT_COLOR = "#f1c40f"    # Đậm hơn
DEFAULT_PRIZE_COLOR = "#3498db"  # Đậm hơn
PASSED_PRIZE_COLOR = "#7f8c8d"

class AudioManager:
    def __init__(self):
        try:
            pygame.mixer.init()
            self.sounds = {}
            self.is_muted = False
            self.current_bg_music = None
            self.load_sounds()
        except pygame.error as e:
            messagebox.showerror("Lỗi Pygame", f"Không thể khởi tạo: {e}")
            self.sounds = {}
    
    def load_sounds(self):
        audio_dir = 'audio'
        if not os.path.isdir(audio_dir):
            messagebox.showwarning("Lỗi Âm Thanh", f"Không tìm thấy thư mục '{audio_dir}'")
            return
        
        sound_files = {
            'welcome': 'welcome.mp3',
            'wait_1_5': 'wait_1_5.mp3',
            'wait_6_10': 'wait_6_10.mp3',
            'wait_11_15': 'wait_11_15.mp3',
            'ready': 'ready.mp3',
            'lifeline': 'lifeline.mp3',
            'win': 'win.mp3',
            'selected': 'selected.wav',
            'correct': 'correct.wav',
            'wrong': 'wrong.wav',
            'end_game': 'end_game.wav'
        }
        
        for key, filename in sound_files.items():
            path = os.path.join(audio_dir, filename)
            if os.path.exists(path):
                try:
                    if filename.endswith('.mp3'):
                        self.sounds[key] = path
                    else:
                        self.sounds[key] = pygame.mixer.Sound(path)
                except pygame.error as e:
                    print(f"Lỗi tải file '{filename}': {e}")
    
    def play(self, name, loop=False):
        if self.is_muted or name not in self.sounds:
            return
        
        try:
            sound_data = self.sounds[name]
            if isinstance(sound_data, str):  # MP3 file
                if self.current_bg_music == name and pygame.mixer.music.get_busy():
                    return
                pygame.mixer.music.stop()
                pygame.mixer.music.load(sound_data)
                pygame.mixer.music.play(-1 if loop else 0)
                self.current_bg_music = name
            else:  # WAV sound
                sound_data.play()
        except pygame.error as e:
            print(f"Lỗi phát âm thanh '{name}': {e}")
    
    def stop_all(self):
        self.current_bg_music = None
        pygame.mixer.music.stop()
        pygame.mixer.stop()
    
    def set_mute(self, status):
        self.is_muted = status
        if self.is_muted:
            self.stop_all()

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
        
        self.load_assets()
        self.create_widgets()
        self.connect_and_start()

    def load_assets(self):
        try:
            self.btn_images = {
                'normal': ImageTk.PhotoImage(Image.open("images/button_normal.png").resize((450, 60))),
                'selected': ImageTk.PhotoImage(Image.open("images/button_selected.png").resize((450, 60))),
                'correct': ImageTk.PhotoImage(Image.open("images/button_correct.png").resize((450, 60))),
                'wrong': ImageTk.PhotoImage(Image.open("images/button_wrong.png").resize((450, 60)))
            }
        except Exception as e:
            messagebox.showerror("Lỗi Tải Ảnh", f"Không thể tải ảnh: {e}")
            self.on_closing()

    def create_widgets(self):
        # Canvas với gradient nền
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.draw_gradient)

        # Thanh trạng thái
        self.status_bar = tk.Label(self, text="...", bd=1, relief=tk.SUNKEN, 
                                 anchor=tk.W, fg="white", bg="#0d1b2a")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bảng giải thưởng bên phải
        self.prize_frame = tk.Frame(self.canvas, bg=WIDGET_BG)
        self.prize_frame.place(relx=0.75, rely=0, relwidth=0.25, relheight=1)
        
        self.prize_labels = []
        for i, prize in enumerate(PRIZE_LEVELS):
            label = tk.Label(self.prize_frame, text=f"{15 - i:2d} ♦ {prize}", 
                           font=("Arial", 14, "bold"), bg=WIDGET_BG, fg="white", anchor='w')
            label.pack(fill='x', padx=20, pady=3)
            self.prize_labels.append(label)

        # Khung chính - BỎ LOGO
        self.main_frame = tk.Frame(self.canvas, bg=WIDGET_BG)
        self.main_frame.place(relx=0, rely=0, relwidth=0.75, relheight=1)

        # Khu vực game
        self.game_area = tk.Frame(self.main_frame, bg=WIDGET_BG)
        self.game_area.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=1, relheight=0.8)
        
        # Câu hỏi
        self.lbl_question = tk.Label(self.game_area, text="...", font=("Arial", 20, "bold"), 
                                   fg="white", bg=WIDGET_BG, wraplength=800)
        self.lbl_question.place(relx=0.5, rely=0.15, anchor=tk.CENTER, width=900, height=120)
        
        # Lifelines
        self.lifeline_frame = tk.Frame(self.main_frame, bg=WIDGET_BG)
        self.lifeline_frame.place(relx=0.5, rely=0.1, anchor=tk.CENTER)
        
        self.lifeline_buttons = {}
        lifeline_texts = {"5050": "50:50", "audience": "Khán Giả", "call": "Gọi Điện", "wise_man": "Tư Vấn"}
        
        for key, text in lifeline_texts.items():
            btn = tk.Button(self.lifeline_frame, text=text, font=("Arial", 12, "bold"), 
                          fg="white", bg="#192c8a", state="disabled", 
                          command=lambda k=key: self.use_lifeline(k))
            btn.pack(side=tk.LEFT, padx=10, pady=10)
            self.lifeline_buttons[key] = btn
            
        # Các nút đáp án
        self.option_buttons = {}
        self.option_positions = {}
        positions = [(0.25, 0.55), (0.75, 0.55), (0.25, 0.75), (0.75, 0.75)]
        
        for i, option in enumerate(["A", "B", "C", "D"]):
            relx, rely = positions[i]
            btn = tk.Button(self.game_area, image=self.btn_images['normal'], 
                          font=("Arial", 16, "bold"), fg="white", bd=0, 
                          highlightthickness=0, compound=tk.CENTER, state="disabled", 
                          command=lambda o=option: self.send_answer(o))
            btn.configure(bg=WIDGET_BG)
            btn.place(relx=relx, rely=rely, anchor=tk.CENTER)
            self.option_buttons[option] = btn
            self.option_positions[option] = {'relx': relx, 'rely': rely}
        
        # Overlay
        self.overlay_frame = tk.Frame(self.main_frame, bg=WIDGET_BG)
        self.overlay_label = tk.Label(self.overlay_frame, font=("Arial", 24, "bold"), 
                                    fg="white", bg=WIDGET_BG)
        self.overlay_label.pack(pady=20)
        
        self.ready_button = tk.Button(self.overlay_frame, text="Sẵn Sàng!", 
                                    font=("Arial", 24, "bold"), command=self.send_ready, 
                                    bg="green", fg="white")
        
    def draw_gradient(self, event):
        self.canvas.delete("gradient")
        width, height = event.width, event.height
        if width <= 0 or height <= 0:
            return
        
        image = Image.new("RGB", (width, height), GRADIENT_END)
        draw = ImageDraw.Draw(image)
        
        start_rgb = tuple(int(GRADIENT_START.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        end_rgb = tuple(int(GRADIENT_END.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        for i in range(height):
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * (i / height))
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * (i / height))
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * (i / height))
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        
        self.gradient_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.gradient_image, anchor="nw", tags="gradient")
        self.canvas.tag_lower("gradient")

    def show_overlay(self, message, show_ready_btn=False):
        self.game_area.place_forget()
        self.overlay_label.config(text=message)
        
        if show_ready_btn:
            self.ready_button.pack(pady=20)
            self.audio_manager.play('ready', loop=True)
        else:
            self.ready_button.pack_forget()
            
        self.overlay_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def hide_overlay(self):
        self.overlay_frame.place_forget()
        self.game_area.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=1, relheight=0.8)

    def send_ready(self):
        self.send_data({'ready': True})
        self.hide_overlay()

    def update_question_display(self, data):
        self.current_level = data['level']
        self.current_lifelines_state = data['lifelines']
        self.lbl_question.config(text=f"Câu {self.current_level}: {data['question']}")
        
        for option, btn in self.option_buttons.items():
            pos = self.option_positions[option]
            btn.place(relx=pos['relx'], rely=pos['rely'], anchor=tk.CENTER)
            btn.config(text=f"{option}: {data['options'][option]}", 
                      state="normal", image=self.btn_images['normal'])
        
        self.update_lifeline_buttons()
        self.update_prize_display()
        self.play_music_by_level()

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
        
        # Blinking effect
        self.blinking_animation(self.option_buttons[answer], 6, 250)
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
            self.after(3500, lambda: self.show_overlay(
                f"Sẵn sàng cho câu số {self.current_level + 1}?", True))
        else:
            self.audio_manager.play('wrong')
            self.after(3500, self.handle_game_over)
        
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
            self.client_socket.sendall(json.dumps(player_info).encode('utf-8'))
            
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
            self.update_question_display(data)
        elif msg_type == 'lifeline_result':
            self.handle_lifeline_result(data)
        elif msg_type == 'result':
            self.show_answer_result(data)
        elif msg_type == 'win':
            self.handle_win()
        elif msg_type == 'game_over':
            self.handle_game_over()
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

    def use_lifeline(self, lifeline_type):
        self.audio_manager.play('lifeline', loop=True)
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
            
    def handle_win(self):
        self.audio_manager.play('win')
        messagebox.showinfo("CHIẾN THẮNG!", f"CHÚC MỪNG {self.player_name}!")
        self.on_closing()
        
    def handle_game_over(self):
        messagebox.showerror("Thua cuộc", "Rất tiếc, bạn đã trả lời sai.")
        self.on_closing()
        
    def handle_disconnection(self):
        if self.client_socket:
            self.client_socket = None
            messagebox.showerror("Mất kết nối", "Mất kết nối tới server.")
            self.on_closing()
            
    def on_closing(self):
        self.audio_manager.play('end_game')
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
        self.geometry("400x300")
        
        self.audio_manager = AudioManager()
        self.audio_manager.play('welcome', loop=True)
        
        # Logo welcome screen
        try:
            logo_image = ImageTk.PhotoImage(Image.open("images/logo.png").resize((100, 100)))
            tk.Label(self, image=logo_image).pack(pady=5)
            self.logo_image = logo_image  # Keep reference
        except:
            tk.Label(self, text="AI LÀ TRIỆU PHÚ", font=("Arial", 24, "bold")).pack(pady=10)
        
        # Input fields
        tk.Label(self, text="Tên thí sinh:").pack()
        self.name_entry = tk.Entry(self, width=30)
        self.name_entry.pack()
        
        tk.Label(self, text="Địa chỉ IP Server:").pack(pady=(10, 0))
        self.ip_entry = tk.Entry(self, width=30)
        self.ip_entry.pack()
        
        tk.Button(self, text="Bắt Đầu Chơi", font=("Arial", 14, "bold"), 
                 command=self.start_game).pack(pady=10)
        
        tk.Label(self, text="Sản phẩm của Duli Production DLV", 
                font=("Arial", 8, "italic")).pack(side="bottom")
        
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