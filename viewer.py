import socket
import json
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
import os
try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError:
    messagebox.showerror("Thiếu thư viện", "Vui lòng cài đặt: pip install Pillow")
    exit()

# --- CẤU HÌNH ---
PORT = 65432
BUFFER_SIZE = 4096
PRIZE_LEVELS = [
    "150.000.000", "85.000.000", "60.000.000", "40.000.000", "30.000.000", "22.000.000",
    "14.000.000", "10.000.000", "6.000.000", "3.000.000", "2.000.000", "1.000.000",
    "600.000", "400.000", "200.000"
]

# Màu sắc (giống hệt client)
GRADIENT_START = "#1a237e"
GRADIENT_END = "#0d1b2a"
WIDGET_BG = "#1a237e"
MILESTONE_COLOR = "#f39c12"
CURRENT_COLOR = "#f1c40f"
DEFAULT_PRIZE_COLOR = "#3498db"
PASSED_PRIZE_COLOR = "#7f8c8d"

class ViewerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chế độ Khán giả - Ai Là Triệu Phú")
        self.geometry("1280x720")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.viewer_socket = None
        self.current_level = 0
        
        self.load_assets()
        self.create_widgets()
        
        self.after(100, self.prompt_for_ip)

    def load_assets(self):
        """Tải các tài nguyên hình ảnh cần thiết cho giao diện."""
        try:
            self.btn_images = {
                'normal': ImageTk.PhotoImage(Image.open("images/button_normal.png").resize((450, 60))),
                'selected': ImageTk.PhotoImage(Image.open("images/button_selected.png").resize((450, 60))),
                'correct': ImageTk.PhotoImage(Image.open("images/button_correct.png").resize((450, 60))),
                'wrong': ImageTk.PhotoImage(Image.open("images/button_wrong.png").resize((450, 60)))
            }
        except Exception as e:
            messagebox.showerror("Lỗi Tải Ảnh", f"Không thể tải ảnh: {e}")
            self.destroy()

    def create_widgets(self):
        """Tạo tất cả các thành phần giao diện người dùng."""
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.draw_gradient)

        self.status_bar = tk.Label(self, text="...", bd=1, relief=tk.SUNKEN, anchor=tk.W, fg="white", bg="#0d1b2a")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Bảng giải thưởng bên phải
        prize_frame = tk.Frame(self.canvas, bg=WIDGET_BG)
        prize_frame.place(relx=0.75, rely=0, relwidth=0.25, relheight=1)
        self.prize_labels = []
        for i, prize in enumerate(PRIZE_LEVELS):
            label = tk.Label(prize_frame, text=f"{15 - i:2d} ♦ {prize}", font=("Arial", 14, "bold"), bg=WIDGET_BG, fg="white", anchor='w')
            label.pack(fill='x', padx=20, pady=3)
            self.prize_labels.append(label)

        # Khung chính
        main_frame = tk.Frame(self.canvas, bg=WIDGET_BG)
        main_frame.place(relx=0, rely=0, relwidth=0.75, relheight=1)

        # Khu vực game
        self.game_area = tk.Frame(main_frame, bg=WIDGET_BG)
        self.lbl_question = tk.Label(self.game_area, text="...", font=("Arial", 20, "bold"), fg="white", bg=WIDGET_BG, wraplength=800)
        self.lbl_question.place(relx=0.5, rely=0.3, anchor=tk.CENTER, width=900, height=120)

        # Các nút đáp án
        self.option_buttons = {}
        self.option_positions = {}
        positions = [(0.25, 0.55), (0.75, 0.55), (0.25, 0.75), (0.75, 0.75)]
        for i, option in enumerate(["A", "B", "C", "D"]):
            relx, rely = positions[i]
            btn = tk.Button(self.game_area, image=self.btn_images['normal'], font=("Arial", 14, "bold"), fg="white", bd=0, highlightthickness=0, compound=tk.CENTER, state="disabled")
            btn.configure(bg=WIDGET_BG)
            btn.place(relx=relx, rely=rely, anchor=tk.CENTER)
            self.option_buttons[option] = btn
            self.option_positions[option] = {'relx': relx, 'rely': rely}

        # Lớp phủ cho các thông báo
        self.overlay_frame = tk.Frame(main_frame, bg=WIDGET_BG)
        self.overlay_label = tk.Label(self.overlay_frame, font=("Arial", 24, "bold"), fg="white", bg=WIDGET_BG)
        self.overlay_label.pack(pady=20)
        
        self.show_overlay("Đang chờ kết nối tới server...")

    def draw_gradient(self, event):
        """Vẽ nền gradient cho canvas."""
        self.canvas.delete("gradient")
        width, height = event.width, event.height
        if width <= 0 or height <= 0: return

        image = Image.new("RGB", (width, height), GRADIENT_END)
        draw = ImageDraw.Draw(image)
        start_rgb = tuple(int(GRADIENT_START.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        end_rgb = tuple(int(GRADIENT_END.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        for i in range(height):
            r, g, b = [int(start_rgb[j] + (end_rgb[j] - start_rgb[j]) * (i / height)) for j in range(3)]
            draw.line([(0, i), (width, i)], fill=(r, g, b))
            
        self.gradient_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.gradient_image, anchor="nw", tags="gradient")
        self.canvas.tag_lower("gradient")

    def show_overlay(self, message):
        """Hiển thị một lớp phủ với thông báo."""
        self.game_area.place_forget()
        self.overlay_label.config(text=message)
        self.overlay_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def hide_overlay(self):
        """Ẩn lớp phủ và hiển thị khu vực game."""
        self.overlay_frame.place_forget()
        self.game_area.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=1, relheight=0.8)

    def prompt_for_ip(self):
        """Hỏi IP server và bắt đầu kết nối."""
        server_ip = simpledialog.askstring("Kết nối Server", "Nhập địa chỉ IP của server:", parent=self)
        if not server_ip:
            self.destroy()
            return
        
        self.status_bar.config(text=f"Đang kết nối tới {server_ip}...")
        threading.Thread(target=self._connect_in_thread, args=(server_ip,), daemon=True).start()

    def _connect_in_thread(self, server_ip):
        """Thực hiện kết nối trong một luồng riêng biệt."""
        try:
            self.viewer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.viewer_socket.connect((server_ip, PORT))
            
            # Gửi thông tin định danh là viewer
            viewer_info = {'type': 'viewer'}
            self.viewer_socket.sendall((json.dumps(viewer_info) + '\n').encode('utf-8'))
            
            self.after(0, lambda: self.title(f"Chế độ Khán giả - Đã kết nối tới {server_ip}"))
            self.after(0, lambda: self.status_bar.config(text=f"Đã kết nối. Đang chờ game bắt đầu..."))
            self.after(0, lambda: self.show_overlay("Đang chờ người chơi bắt đầu..."))
            self.after(0, self.update_prize_display, 0)

            threading.Thread(target=self.listen_for_messages, daemon=True).start()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Lỗi Kết Nối", f"Không thể kết nối: {e}"))
            self.after(0, self.destroy)
    
    def listen_for_messages(self):
        """Lắng nghe tin nhắn từ server."""
        buffer = ""
        while self.viewer_socket:
            try:
                raw_data = self.viewer_socket.recv(BUFFER_SIZE)
                if not raw_data:
                    break
                
                buffer += raw_data.decode('utf-8')
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    self.after(0, self.process_message, json.loads(message))
            except (json.JSONDecodeError, ConnectionError, OSError):
                break
        self.after(0, self.handle_disconnection)

    def process_message(self, data):
        """Xử lý tin nhắn nhận được từ server."""
        msg_type = data.get('type')
        
        if msg_type == 'ask_ready':
            self.show_overlay(f"Đang chờ người chơi sẵn sàng cho câu {data['level']}...")
            self.update_prize_display(data['level'])
        elif msg_type == 'question':
            self.hide_overlay()
            self.update_question_display(data)
        elif msg_type == 'lifeline_result':
            self.handle_lifeline_result(data)
        elif msg_type == 'result':
            self.show_answer_result(data)
        elif msg_type == 'game_paused':
            if data.get('paused', False):
                self.show_overlay("GAME TẠM DỪNG BỞI HOST")
            else:
                self.hide_overlay()
        elif msg_type in ['win', 'game_over', 'game_ended_waiting']:
            self.reset_ui_for_new_game()

    def update_question_display(self, data):
        """Cập nhật giao diện với câu hỏi và các lựa chọn mới."""
        self.current_level = data['level']
        self.lbl_question.config(text=f"Câu {self.current_level}: {data['question']}")
        
        for option, btn in self.option_buttons.items():
            pos = self.option_positions[option]
            btn.place(relx=pos['relx'], rely=pos['rely'], anchor=tk.CENTER)
            btn.config(text=f"{option}: {data['options'][option]}", image=self.btn_images['normal'])
            
        self.update_prize_display(self.current_level)

    def update_prize_display(self, current_level):
        """Cập nhật màu sắc của bảng giải thưởng."""
        for i, label in enumerate(self.prize_labels):
            prize_level = 15 - i
            is_milestone = prize_level in [5, 10, 15]
            
            if prize_level < current_level:
                label.config(bg=WIDGET_BG, fg=PASSED_PRIZE_COLOR)
            elif prize_level == current_level:
                label.config(bg=CURRENT_COLOR, fg="black")
            else:
                color = MILESTONE_COLOR if is_milestone else DEFAULT_PRIZE_COLOR
                label.config(bg=WIDGET_BG, fg=color)

    def handle_lifeline_result(self, data):
        """Xử lý kết quả từ sự trợ giúp (chỉ hiển thị 50:50)."""
        if data['lifeline'] == '5050' and 'options' in data:
            for option, btn in self.option_buttons.items():
                if not data['options'].get(option):
                    btn.place_forget()

    def show_answer_result(self, data):
        """Hiển thị kết quả trả lời của người chơi."""
        player_answer = data.get('player_answer')
        correct_answer = data.get('correct_answer')
        
        # Đánh dấu câu trả lời của người chơi
        if player_answer and player_answer in self.option_buttons:
            self.option_buttons[player_answer].config(image=self.btn_images['selected'])
        
        # Sau một khoảng trễ, hiển thị đáp án đúng/sai
        def final_result():
            for key, btn in self.option_buttons.items():
                if btn.winfo_ismapped(): # Chỉ cập nhật các nút còn hiển thị
                    if key == correct_answer:
                        btn.config(image=self.btn_images['correct'])
                    else:
                        btn.config(image=self.btn_images['wrong'])
        self.after(1500, final_result)

    def reset_ui_for_new_game(self):
        """Reset giao diện để chờ lượt chơi mới."""
        self.show_overlay("Lượt chơi đã kết thúc. Chờ người chơi mới...")
        self.current_level = 0
        self.update_prize_display(0)
        
        # Đảm bảo tất cả các nút đáp án được hiển thị lại
        for option, btn in self.option_buttons.items():
            pos = self.option_positions[option]
            btn.place(relx=pos['relx'], rely=pos['rely'], anchor=tk.CENTER)
            btn.config(text=f"{option}:", image=self.btn_images['normal'])

    def handle_disconnection(self):
        """Xử lý khi mất kết nối tới server."""
        if self.viewer_socket:
            self.viewer_socket = None
            messagebox.showinfo("Mất kết nối", "Mất kết nối tới server.")
            self.destroy()

    def on_closing(self):
        """Dọn dẹp tài nguyên khi đóng cửa sổ."""
        if self.viewer_socket:
            try:
                self.viewer_socket.close()
            except:
                pass
            self.viewer_socket = None
        self.destroy()

if __name__ == "__main__":
    app = ViewerGUI()
    app.mainloop()