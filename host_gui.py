import tkinter as tk
from tkinter import scrolledtext, font, simpledialog, messagebox
import threading
import time
import os
import server as server_logic

class HostGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bảng Điều Khiển Host - Ai Là Triệu Phú 5.1")
        self.geometry("800x650")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.label_font = font.Font(family="Segoe UI", size=11)
        self.value_font = font.Font(family="Segoe UI", size=11, weight="bold")
        self.log_font = font.Font(family="Consolas", size=10)
        
        self.create_widgets()

        server_logic.set_game_update_callback(self.queue_gui_update)
        self.server_thread = threading.Thread(target=server_logic.start_server_logic, daemon=True)
        self.server_thread.start()

    def create_widgets(self):
        main_frame = tk.Frame(self, padx=10, pady=5)
        main_frame.pack(fill="both", expand=True)
        
        status_frame = tk.LabelFrame(main_frame, text="Trạng Thái Trực Tiếp", padx=10, pady=10)
        status_frame.grid(row=0, column=0, sticky="ew", pady=5)
        main_frame.grid_columnconfigure(0, weight=1)

        tk.Label(status_frame, text="Thí sinh:", font=self.label_font).grid(row=0, column=0, sticky="w")
        self.lbl_name = tk.Label(status_frame, text="Chờ kết nối...", font=self.value_font, fg="#0078D7")
        self.lbl_name.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(status_frame, text="ID:", font=self.label_font).grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.lbl_id = tk.Label(status_frame, text="N/A", font=self.value_font)
        self.lbl_id.grid(row=0, column=3, sticky="w", padx=5)

        tk.Label(status_frame, text="Câu hỏi số:", font=self.label_font).grid(row=1, column=0, sticky="w")
        self.lbl_level = tk.Label(status_frame, text="0", font=self.value_font)
        self.lbl_level.grid(row=1, column=1, sticky="w", padx=5)
        
        tk.Label(status_frame, text="Tiền thưởng:", font=self.label_font).grid(row=1, column=2, sticky="w", padx=(20, 0))
        self.lbl_prize = tk.Label(status_frame, text="0 VNĐ", font=self.value_font, fg="green")
        self.lbl_prize.grid(row=1, column=3, sticky="w", padx=5)

        tk.Label(status_frame, text="Lượt trả lời cuối:", font=self.label_font).grid(row=2, column=0, sticky="w", columnspan=4)
        self.lbl_last_answer = tk.Label(status_frame, text="Chưa có", font=self.value_font)
        self.lbl_last_answer.grid(row=3, column=0, columnspan=4, sticky="w")
        
        control_frame = tk.LabelFrame(main_frame, text="Bảng Điều Khiển", padx=10, pady=10)
        control_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        tk.Button(control_frame, text="Tắt Nhạc Client", command=lambda: self.send_command_to_client('set_mute', True)).pack(side="left", padx=5, pady=5)
        tk.Button(control_frame, text="Bật Nhạc Client", command=lambda: self.send_command_to_client('set_mute', False)).pack(side="left", padx=5, pady=5)
        self.pause_button = tk.Button(control_frame, text="Tạm Dừng Game", command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=5, pady=5)

        log_frame = tk.LabelFrame(main_frame, text="Nhật Ký Server", padx=10, pady=10)
        log_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        main_frame.grid_rowconfigure(2, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', font=self.log_font)
        self.log_text.pack(fill="both", expand=True)

    def send_command_to_client(self, cmd_type, value):
        if not server_logic.player_conn:
            self.log("Lỗi: Không có người chơi để gửi lệnh.")
            return
        server_logic.broadcast({'type': cmd_type, 'value': value})
        self.log(f"Đã gửi lệnh '{cmd_type}: {value}' đến tất cả.")
    
    def toggle_pause(self):
        server_logic.is_game_paused = not server_logic.is_game_paused
        if server_logic.is_game_paused:
            self.pause_button.config(text="Tiếp Tục Game", bg="#28a745", fg="white")
            self.log("GAME ĐÃ TẠM DỪNG.")
            server_logic.broadcast({'type': 'game_paused', 'paused': True})
        else:
            self.pause_button.config(text="Tạm Dừng Game", bg="SystemButtonFace", fg="black")
            self.log("GAME ĐÃ TIẾP TỤC.")
            server_logic.broadcast({'type': 'game_paused', 'paused': False})

    def queue_gui_update(self, data):
        self.after(0, self.process_gui_update, data)
        
    def process_gui_update(self, data):
        msg_type = data.get('type')
        if msg_type == 'log':
            self.log(data['message'])
        elif msg_type == 'connect':
            self.lbl_name.config(text=data['name'])
            self.lbl_id.config(text=data['id'])
            self.log(f"Người chơi '{data['name']}' đã kết nối từ {data['addr']}")
        elif msg_type == 'disconnect':
            self.lbl_name.config(text="Chờ kết nối...")
            self.lbl_id.config(text="N/A")
            self.lbl_level.config(text="0")
            self.lbl_prize.config(text="0 VNĐ")
            self.lbl_last_answer.config(text="Chưa có", fg='black')
        elif msg_type == 'game_state':
            self.lbl_level.config(text=str(data['level']))
            self.lbl_prize.config(text=f"{data['prize']} VNĐ")
        elif msg_type == 'answer':
            status, color = ("ĐÚNG", "green") if data['is_correct'] else ("SAI", "red")
            text = f"'{data['player_answer']}' -> Đáp án đúng: '{data['correct_answer']}' ({status})"
            self.lbl_last_answer.config(text=text, fg=color)
            self.log(f"Người chơi trả lời câu {self.lbl_level.cget('text')}: {text}")
        elif msg_type == 'wise_man_request':
            self.handle_wise_man_request(data['question'], data['answer'])
        elif msg_type == 'audience_request':
            self.handle_audience_request()

    def handle_audience_request(self):
        self.log("Đang chờ nhập ý kiến 3 khán giả...")
        dialog = AudienceDialog(self)
        results = dialog.result
        if results and all(r.upper() in ['A', 'B', 'C', 'D'] for r in results if r):
            server_logic.broadcast({'type': 'lifeline_result', 'lifeline': 'audience', 'opinions': [r.upper() for r in results]})
            self.log(f"Đã gửi ý kiến khán giả: {results}")
        else:
            server_logic.broadcast({'type': 'lifeline_result', 'lifeline': 'audience', 'opinions': []})
            self.log("Đã hủy hoặc nhập sai ý kiến khán giả.")

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

class AudienceDialog(simpledialog.Dialog):
    def body(self, master):
        self.title("Hỏi Ý Kiến Khán Giả")
        tk.Label(master, text="Nhập câu trả lời của 3 khán giả may mắn:").pack()
        self.entries = []
        for i in range(3):
            frame = tk.Frame(master)
            tk.Label(frame, text=f"Khán giả {i+1}:").pack(side="left")
            entry = tk.Entry(frame, width=5)
            entry.pack(side="left", padx=5)
            self.entries.append(entry)
            frame.pack(pady=2)
        return self.entries[0]
    def apply(self):
        self.result = [e.get().strip() for e in self.entries]

if __name__ == "__main__":
    app = HostGUI()
    app.mainloop()