import socket
import json
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
try:
    from ui_assets import load_background_source, load_button_images, load_logo_photo, load_lozenge_photo, render_background
except ImportError:
    messagebox.showerror("Thiếu thư viện", "Vui lòng cài đặt: pip install Pillow")
    exit()
from audio_backend import AudioManager

# --- CẤU HÌNH ---
PORT = 65432
BUFFER_SIZE = 4096
PRIZE_LEVELS = [
    "500.000.000", "250.000.000", "120.000.000", "60.000.000", "30.000.000",
    "22.000.000", "14.000.000", "10.000.000", "8.000.000", "6.000.000",
    "5.000.000", "4.000.000", "3.000.000", "2.000.000", "1.000.000"
]

# Màu sắc (giống hệt client)
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
ANSWER_STYLES = {
    "normal": {"bg": "#0F254E", "fg": "#ffffff", "border": "#00D2FF", "image": "normal"},
    "selected": {"bg": "#FF9900", "fg": "#050E21", "border": "#FF9900", "image": "selected"},
    "correct": {"bg": "#00CC44", "fg": "#031507", "border": "#00CC44", "image": "correct"},
    "wrong": {"bg": "#8b1f36", "fg": "#ffffff", "border": "#ff9caf"},
    "dim": {"bg": "#24304c", "fg": "#93a4cf", "border": "#3d4b70", "image": "dim"},
}

class ViewerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chế độ Khán giả - Ai Là Triệu Phú")
        self.geometry("1280x720")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.viewer_socket = None
        self.current_level = 0
        self.scene_countdown_job = None
        self.scene_remaining_seconds = 0
        self.final_scene_active = False
        self.current_lifelines_state = {'5050': True, 'audience': True, 'call': True, 'wise_man': True}
        self.credit_animation_job = None
        self.audio_manager = AudioManager()
        self.current_scene_sound = None
        self.current_scene_sound_loop = False

        self.load_assets()
        self.create_widgets()

        self.after(100, self.prompt_for_ip)

    def load_assets(self):
        """Tải các tài nguyên hình ảnh cần thiết cho giao diện."""
        try:
            self.background_source = load_background_source()
            self.btn_images = load_button_images((450, 60))
            self.answer_images = load_button_images((430, 82))
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
            self.destroy()

    def create_widgets(self):
        """Tạo tất cả các thành phần giao diện người dùng."""
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

        header_frame = tk.Frame(self.main_frame, bg="#061128")
        header_frame.place(relx=0.04, rely=0.035, width=650, height=88)

        if self.logo_image:
            tk.Label(header_frame, image=self.logo_image, bg="#061128").pack(side=tk.LEFT, padx=(0, 14))

        title_frame = tk.Frame(header_frame, bg="#061128")
        title_frame.pack(side=tk.LEFT, fill="y")
        tk.Label(
            title_frame,
            text="KHÁN GIẢ TRỰC TIẾP",
            font=("Segoe UI", 25, "bold"),
            fg="white",
            bg="#061128",
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_frame,
            text="Sân khấu Ai Là Triệu Phú",
            font=("Segoe UI", 12),
            fg=TEXT_MUTED,
            bg="#061128",
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        self.game_area = tk.Frame(self.main_frame, bg=WIDGET_BG)
        self.game_background_label = tk.Label(self.game_area, bd=0)
        self.game_background_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.lbl_question = tk.Label(
            self.game_area,
            text="...",
            image=self.question_panel_image,
            compound=tk.CENTER,
            font=("Arial", 20, "bold"),
            fg="white",
            bg=WIDGET_BG,
            wraplength=820,
            justify=tk.CENTER,
            highlightthickness=0,
            padx=24,
            pady=18,
        )
        self.lbl_question.place(relx=0.5, rely=0.26, anchor=tk.CENTER, width=880, height=135)

        self.option_buttons = {}
        self.option_positions = {}
        positions = [(0.25, 0.58), (0.75, 0.58), (0.25, 0.79), (0.75, 0.79)]
        for i, option in enumerate(["A", "B", "C", "D"]):
            relx, rely = positions[i]
            btn = tk.Label(
                self.game_area,
                text=f"{option}:",
                font=("Segoe UI", 17, "bold"),
                fg="white",
                image=self.answer_images["normal"],
                compound=tk.CENTER,
                bg=WIDGET_BG,
                bd=0,
                highlightthickness=0,
                anchor=tk.CENTER,
                justify=tk.CENTER,
                wraplength=360,
                padx=18,
                pady=10,
            )
            btn.place(relx=relx, rely=rely, anchor=tk.CENTER, width=430, height=82)
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
        self.overlay_label = tk.Label(
            self.overlay_frame,
            font=("Arial", 24, "bold"),
            fg="white",
            bg=PANEL_BG,
            wraplength=680,
            justify=tk.CENTER,
        )
        self.overlay_label.pack(pady=20)

        self.scene_frame = tk.Frame(self.canvas, bg="#020817")
        self.scene_title = tk.Label(
            self.scene_frame,
            text="",
            bg="#020817",
            fg=PANEL_BORDER,
            font=("Segoe UI", 34, "bold"),
            wraplength=980,
            justify=tk.CENTER,
        )
        self.scene_title.pack(expand=True, fill="both", pady=(90, 0))
        self.scene_message = tk.Label(
            self.scene_frame,
            text="",
            bg="#020817",
            fg="white",
            font=("Segoe UI", 22),
            wraplength=980,
            justify=tk.CENTER,
        )
        self.scene_message.pack(fill="x", padx=80)
        self.prize_scene_frame = tk.Frame(self.scene_frame, bg="#020817")
        self.poll_scene_frame = tk.Frame(self.scene_frame, bg="#020817")
        self.scene_countdown = tk.Label(
            self.scene_frame,
            text="",
            bg="#020817",
            fg=PANEL_BORDER,
            font=("Segoe UI", 42, "bold"),
        )
        self.scene_countdown.pack(pady=(28, 80))

        self.show_overlay("Đang chờ kết nối tới server...")

    def draw_gradient(self, event):
        """Vẽ nền gradient cho canvas."""
        self.canvas.delete("gradient")
        width, height = event.width, event.height
        if width <= 0 or height <= 0: return

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

    def show_overlay(self, message):
        """Hiển thị một lớp phủ với thông báo."""
        self.hide_scene()
        self.game_area.place_forget()
        self.overlay_label.config(text=message)
        self.overlay_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def hide_overlay(self):
        """Ẩn lớp phủ và hiển thị khu vực game."""
        self.hide_scene()
        self.overlay_frame.place_forget()
        self.game_area.place(relx=0.5, rely=0.58, anchor=tk.CENTER, relwidth=1, relheight=0.74)

    def place_answer_button(self, option):
        pos = self.option_positions[option]
        self.option_buttons[option].place(
            relx=pos['relx'],
            rely=pos['rely'],
            anchor=tk.CENTER,
            width=430,
            height=82,
        )

    def option_font_for_text(self, text):
        length = len(text)
        if length >= 92:
            size = 11
        elif length >= 70:
            size = 12
        elif length >= 50:
            size = 13
        else:
            size = 17
        return ("Segoe UI", size, "bold")

    def set_option_label_text(self, option, option_text):
        display_text = f"{option}: {option_text}"
        self.option_buttons[option].config(
            text=display_text,
            font=self.option_font_for_text(display_text),
            wraplength=360,
            justify=tk.CENTER,
            anchor=tk.CENTER,
        )

    def style_answer_button(self, option, state):
        style = ANSWER_STYLES[state]
        self.option_buttons[option].config(
            image=self.answer_images.get(style.get("image", state), self.answer_images["normal"]),
            bg=WIDGET_BG,
            fg=style["fg"],
            highlightbackground=style["border"],
        )

    def hide_scene(self):
        if self.scene_countdown_job:
            self.after_cancel(self.scene_countdown_job)
            self.scene_countdown_job = None
        self.stop_credit_animation()
        self.hide_prize_scene_board()
        self.hide_poll_scene_board()
        self.scene_frame.place_forget()

    def stop_credit_animation(self):
        if self.credit_animation_job:
            try:
                self.after_cancel(self.credit_animation_job)
            except tk.TclError:
                pass
            self.credit_animation_job = None

    def play_scene_audio(self, sound_name, loop=False):
        self.current_scene_sound = sound_name
        self.current_scene_sound_loop = loop
        self.audio_manager.stop_all()
        if sound_name and self.audio_manager.has_sound(sound_name):
            self.audio_manager.play(sound_name, loop=loop)

    def stop_scene_audio(self):
        self.current_scene_sound = None
        self.current_scene_sound_loop = False
        self.audio_manager.stop_all()

    def resume_scene_audio(self):
        if self.final_scene_active:
            return
        if self.current_scene_sound and self.audio_manager.has_sound(self.current_scene_sound):
            self.audio_manager.play(self.current_scene_sound, loop=self.current_scene_sound_loop)

    def play_final_audio(self, is_win, with_buzzer=False):
        self.audio_manager.stop_all()
        if with_buzzer and self.audio_manager.has_sound('end_buzzer'):
            self.audio_manager.play('end_buzzer')
            self.after(1200, lambda: self.play_program_end_audio(is_win))
        else:
            self.play_program_end_audio(is_win)

    def play_program_end_audio(self, is_win=True):
        if is_win and self.audio_manager.has_sound('complete'):
            self.audio_manager.play('complete')
        elif is_win and self.audio_manager.has_sound('program_end'):
            self.audio_manager.play('program_end')
        elif is_win:
            self.audio_manager.play('win')
        else:
            self.audio_manager.play('end_game')

    def credit_lines_from_payload(self, payload):
        lines = payload.get('lines') or [
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
        return [line for line in lines if line]

    def start_credit_animation(self, lines):
        self.stop_credit_animation()
        if not lines:
            return

        colors = [PANEL_BORDER, "#ffffff", "#8ff0c5"]

        def animate(step=0):
            line = lines[step % len(lines)]
            self.scene_title.config(fg=colors[step % len(colors)])
            self.scene_message.config(text=f"◆\n{line}")
            self.credit_animation_job = self.after(1350, lambda: animate(step + 1))

        animate()

    def hide_prize_scene_board(self):
        for child in self.prize_scene_frame.winfo_children():
            child.destroy()
        self.prize_scene_frame.pack_forget()
        if not self.scene_message.winfo_manager():
            self.scene_message.pack(before=self.scene_countdown, fill="x", padx=80)

    def hide_poll_scene_board(self):
        for child in self.poll_scene_frame.winfo_children():
            child.destroy()
        self.poll_scene_frame.pack_forget()
        if not self.scene_message.winfo_manager():
            self.scene_message.pack(before=self.scene_countdown, fill="x", padx=80)

    def show_prize_scene_board(self):
        if self.scene_message.winfo_manager():
            self.scene_message.pack_forget()
        for child in self.prize_scene_frame.winfo_children():
            child.destroy()
        self.scene_prize_row_images = []

        window_height = max(self.winfo_height(), 720)
        compact = window_height < 860
        lifeline_font = ("Segoe UI", 10 if compact else 12, "bold")
        prize_font = ("Consolas", 14 if compact else 17, "bold")
        row_pady = 0 if compact else 1

        lifeline_row = tk.Frame(self.prize_scene_frame, bg="#020817")
        lifeline_row.pack(fill="x", pady=(0, 7 if compact else 12))
        for key, label in [
            ("5050", "50:50"),
            ("audience", "KHÁN GIẢ"),
            ("call", "GỌI ĐIỆN"),
            ("wise_man", "TƯ VẤN"),
        ]:
            available = self.current_lifelines_state.get(key, True)
            locked = key == "wise_man" and self.current_level < 6 and available
            status = "KHÓA" if locked else ("OK" if available else "X")
            bg = "#26304a" if locked else ("#12346f" if available else "#64192b")
            fg = TEXT_MUTED if locked else ("#8ff0c5" if available else "#ff9caf")
            tk.Label(
                lifeline_row,
                text=f"{label}  {status}",
                bg=bg,
                fg=fg,
                font=lifeline_font,
                padx=10 if compact else 14,
                pady=5 if compact else 7,
            ).pack(side=tk.LEFT, padx=5)

        board = tk.Frame(self.prize_scene_frame, bg="#020817")
        board.pack(fill="both", expand=True)
        horizontal_pad = 110 if compact else 180
        row_width = max(760, self.winfo_width() - (horizontal_pad * 2) - 30)
        row_height = 29 if compact else 34
        for index, prize in enumerate(PRIZE_LEVELS):
            level = 15 - index
            is_current = level == self.current_level
            is_passed = level < self.current_level
            is_milestone = level in [5, 10, 15]
            image_state = "selected" if is_current else ("dim" if is_passed else ("milestone" if is_milestone else "normal"))
            row_image = load_lozenge_photo((row_width, row_height), image_state, radius=7)
            self.scene_prize_row_images.append(row_image)
            fg = "#06122f" if is_current else (PASSED_PRIZE_COLOR if is_passed else (MILESTONE_COLOR if is_milestone else DEFAULT_PRIZE_COLOR))
            row_text = f"{'▶' if is_current else ' '}   {level:02d}   ◆   {prize} VNĐ"
            tk.Label(
                board,
                text=row_text,
                image=row_image,
                compound=tk.CENTER,
                bg="#020817",
                fg=fg,
                font=prize_font,
                bd=0,
                highlightthickness=0,
            ).pack(fill="x", pady=row_pady)

        self.prize_scene_frame.pack(before=self.scene_countdown, fill="both", expand=True, padx=horizontal_pad, pady=(0, 8 if compact else 14))

    def show_poll_scene_board(self, payload):
        if self.scene_message.winfo_manager():
            self.scene_message.pack_forget()
        for child in self.poll_scene_frame.winfo_children():
            child.destroy()

        questions = payload.get('questions', [])
        current_index = int(payload.get('current_index', 0) or 0)
        announced = set(payload.get('announced', []))
        answers = payload.get('answers', {})
        locked = set(payload.get('locked', []))
        if not questions:
            self.scene_message.config(text="Chưa tìm thấy câu hỏi tương tác trong pack dự phòng.")
            self.scene_message.pack(before=self.scene_countdown, fill="x", padx=80)
            return

        current_index = min(max(current_index, 0), len(questions) - 1)
        progress = tk.Frame(self.poll_scene_frame, bg="#020817")
        progress.pack(fill="x", pady=(0, 18))
        done_font = ("Segoe UI", 13, "bold overstrike")
        active_font = ("Segoe UI", 13, "bold")
        for index, question in enumerate(questions):
            answer = answers.get(str(index))
            was_announced = index in announced
            is_current = index == current_index
            is_locked = index in locked
            bg = "#00CC44" if is_locked else (CURRENT_COLOR if is_current else ("#001B0A" if answer else ("#263a66" if was_announced else PANEL_BG)))
            fg = "#031507" if is_locked else ("#06122f" if is_current else ("#8ff0c5" if answer else TEXT_MUTED))
            text = f"Câu {index + 1}"
            if answer:
                text += f"  {answer}"
            if is_locked:
                text += "  CHỐT"
            tk.Label(
                progress,
                text=text,
                bg=bg,
                fg=fg,
                font=done_font if (is_locked or was_announced) else active_font,
                padx=18,
                pady=8,
            ).pack(side=tk.LEFT, padx=6)

        current_question = questions[current_index]
        selected_answer = answers.get(str(current_index))
        is_current_locked = current_index in locked
        question_font = ("Segoe UI", 24, "bold overstrike") if selected_answer else ("Segoe UI", 24, "bold")
        tk.Label(
            self.poll_scene_frame,
            text=f"Câu {current_index + 1}: {current_question.get('question', '')}",
            bg=PANEL_BG,
            fg="#ffffff",
            font=question_font,
            wraplength=1120,
            justify=tk.CENTER,
            highlightthickness=2,
            highlightbackground=PANEL_BORDER,
            padx=28,
            pady=20,
        ).pack(fill="x", pady=(0, 22))

        options_frame = tk.Frame(self.poll_scene_frame, bg="#020817")
        options_frame.pack(fill="x")
        options_frame.grid_columnconfigure(0, weight=1)
        options_frame.grid_columnconfigure(1, weight=1)
        options = current_question.get('options', {})
        for position, key in enumerate(["A", "B", "C", "D"]):
            row, column = divmod(position, 2)
            is_selected = selected_answer == key
            is_dimmed = selected_answer and not is_selected
            bg = ("#00CC44" if is_current_locked else CURRENT_COLOR) if is_selected else ("#24304c" if is_dimmed else PANEL_BG)
            fg = "#06122f" if is_selected else ("#93a4cf" if is_dimmed else "#ffffff")
            border = ("#00CC44" if is_current_locked else CURRENT_COLOR) if is_selected else PANEL_BORDER
            tk.Label(
                options_frame,
                text=f"{key}. {options.get(key, '')}",
                bg=bg,
                fg=fg,
                font=("Segoe UI", 18, "bold"),
                wraplength=520,
                justify=tk.LEFT,
                anchor="w",
                highlightthickness=2,
                highlightbackground=border,
                padx=20,
                pady=14,
            ).grid(row=row, column=column, sticky="ew", padx=8, pady=8)

        if selected_answer:
            final_text = (
                f"ĐÁP ÁN POLL ĐÃ CHỐT: {selected_answer} - CHỌN BACK-UP PLAYER"
                if is_current_locked else
                f"Khán giả đang chọn đáp án {selected_answer}"
            )
            tk.Label(
                self.poll_scene_frame,
                text=final_text,
                bg="#020817",
                fg="#00CC44" if is_current_locked else CURRENT_COLOR,
                font=("Segoe UI", 24, "bold"),
            ).pack(fill="x", pady=(20, 0))

        self.poll_scene_frame.pack(before=self.scene_countdown, fill="both", expand=True, padx=130, pady=(0, 24))

    def poll_scene_text(self, intro, questions):
        lines = [intro] if intro else []
        if not questions:
            lines.append("Chưa tìm thấy câu hỏi tương tác trong pack dự phòng.")
            return "\n".join(lines)

        for index, question in enumerate(questions, 1):
            options = question.get('options', {})
            lines.append(f"{index}. {question.get('question', '')}")
            lines.append(f"   A. {options.get('A', '')}    B. {options.get('B', '')}")
            lines.append(f"   C. {options.get('C', '')}    D. {options.get('D', '')}")
        return "\n".join(lines)

    def show_viewer_scene(self, data):
        scene = data.get('scene', 'standby')
        title = data.get('title', '')
        message = data.get('message', '')
        payload = data.get('payload', {})
        stats = data.get('stats', {})
        self.stop_credit_animation()
        self.hide_prize_scene_board()
        self.hide_poll_scene_board()
        self.scene_title.config(font=("Segoe UI", 34, "bold"))
        self.scene_message.config(font=("Segoe UI", 22), justify=tk.CENTER)
        if scene == 'prize':
            self.scene_title.config(font=("Segoe UI", 30, "bold"))
            self.scene_title.pack_configure(expand=False, fill="x", pady=(24, 8))
            self.scene_message.pack_configure(fill="both", expand=True, padx=100)
            self.scene_countdown.pack_configure(pady=(4, 18))
        elif scene in ['credits', 'poll']:
            self.scene_title.pack_configure(expand=False, fill="x", pady=(42, 12))
            self.scene_message.pack_configure(fill="both", expand=True, padx=130)
            self.scene_countdown.pack_configure(pady=(8, 30))
        else:
            self.scene_title.pack_configure(expand=True, fill="both", pady=(90, 0))
            self.scene_message.pack_configure(fill="x", expand=False, padx=80)
            self.scene_countdown.pack_configure(pady=(28, 80))

        if scene == 'game':
            self.play_scene_audio(data.get('sound'), data.get('sound_loop', False))
            self.hide_overlay()
            return
        if scene == 'blank':
            title = title or "AI LÀ TRIỆU PHÚ"
            message = ""
            self.scene_title.config(font=("Segoe UI", 52, "bold"))
            self.scene_frame.config(bg="#020817")
            self.scene_title.config(bg="#020817", fg=PANEL_BORDER)
            self.scene_message.config(bg="#020817", fg="#020817")
            self.scene_countdown.config(bg="#020817", fg="#020817")
        else:
            self.scene_frame.config(bg="#020817")
            self.scene_title.config(bg="#020817", fg=PANEL_BORDER)
            self.scene_message.config(bg="#020817", fg="white")
            self.scene_countdown.config(bg="#020817", fg=PANEL_BORDER)

        if scene == 'prize':
            message = ""
        elif scene == 'stats':
            fastest = stats.get('fastest_ping')
            fastest_text = f"{fastest:.0f}ms" if fastest is not None else "N/A"
            message = (
                f"Câu đã lên sóng: {stats.get('questions_seen', 0)}\n"
                f"Trả lời đúng: {stats.get('correct_answers', 0)} | Sai: {stats.get('wrong_answers', 0)}\n"
                f"Trợ giúp đã dùng: {stats.get('lifelines_used', 0)}\n"
                f"Thời gian phản hồi nhanh nhất: {fastest_text}"
            )
        elif scene == 'credits':
            message = "\n".join(self.credit_lines_from_payload(payload))
            self.scene_title.config(font=("Segoe UI", 42, "bold"))
            self.scene_message.config(font=("Segoe UI", 24, "bold"), justify=tk.CENTER)
        elif scene == 'poll':
            message = ""
        elif scene == 'mini_quiz':
            message = message + "\n\nHãy giữ câu trả lời của bạn cho phần quay lại."

        self.game_area.place_forget()
        self.overlay_frame.place_forget()
        self.scene_title.config(text=title)
        self.scene_message.config(text=message)
        if scene == 'prize':
            self.show_prize_scene_board()
        elif scene == 'poll':
            self.show_poll_scene_board(payload)
        self.scene_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.scene_frame.tkraise()
        self.start_scene_countdown(data.get('countdown_seconds', 0))
        if not (scene == 'poll' and not data.get('sound')):
            self.play_scene_audio(data.get('sound'), data.get('sound_loop', False))
        if scene == 'credits':
            self.start_credit_animation(self.credit_lines_from_payload(payload))

    def prize_scene_text(self):
        lines = ["TRỢ GIÚP"]
        lines.extend(self.lifeline_scene_lines())
        lines.append("")
        lines.append("CÂY TIỀN THƯỞNG")
        for index, prize in enumerate(PRIZE_LEVELS):
            level = 15 - index
            marker = "▶" if level == self.current_level else " "
            milestone = "◆" if level in [5, 10, 15] else "◇"
            lines.append(f"{marker} {level:02d} {milestone} {prize:>11} VNĐ")
        return "\n".join(lines)

    def lifeline_scene_lines(self):
        labels = [
            ("5050", "50:50"),
            ("audience", "Khán giả"),
            ("call", "Gọi điện"),
            ("wise_man", "Tư vấn"),
        ]
        parts = []
        for key, label in labels:
            available = self.current_lifelines_state.get(key, True)
            if key == "wise_man" and self.current_level < 6 and available:
                status = "KHÓA"
            else:
                status = "OK" if available else "X"
            parts.append(f"{label}: {status}")
        return ["  " + "   ".join(parts)]

    def start_scene_countdown(self, seconds):
        if self.scene_countdown_job:
            self.after_cancel(self.scene_countdown_job)
            self.scene_countdown_job = None
        self.scene_remaining_seconds = int(seconds or 0)
        self.update_scene_countdown()

    def update_scene_countdown(self):
        if self.scene_remaining_seconds <= 0:
            self.scene_countdown.config(text="")
            return
        minutes, seconds = divmod(self.scene_remaining_seconds, 60)
        self.scene_countdown.config(text=f"{minutes:02d}:{seconds:02d}")
        self.scene_remaining_seconds -= 1
        self.scene_countdown_job = self.after(1000, self.update_scene_countdown)

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
        elif msg_type == 'answer_locked':
            self.show_locked_answer(data)
        elif msg_type == 'answer_unlocked':
            self.unlock_answer_display(data)
        elif msg_type == 'result':
            self.show_answer_result(data)
        elif msg_type == 'give_up_regret':
            self.show_give_up_regret(data)
        elif msg_type == 'viewer_scene':
            self.show_viewer_scene(data)
        elif msg_type == 'viewer_reset':
            self.reset_ui_for_new_game()
        elif msg_type == 'game_paused':
            if data.get('paused', False):
                self.show_overlay("GAME TẠM DỪNG BỞI HOST")
            else:
                self.hide_overlay()
        elif msg_type == 'set_mute':
            muted = data.get('value', False)
            self.audio_manager.set_mute(muted)
            if not muted:
                self.resume_scene_audio()
        elif msg_type == 'play_effect':
            self.audio_manager.play(data.get('name', 'end_buzzer'))
        elif msg_type == 'win':
            self.show_final_scene(data, True)
        elif msg_type == 'game_over':
            self.show_final_scene(data, False)
        elif msg_type == 'game_ended_waiting':
            if not self.final_scene_active:
                self.reset_ui_for_new_game()

    def update_question_display(self, data):
        """Cập nhật giao diện với câu hỏi và các lựa chọn mới."""
        self.stop_scene_audio()
        self.final_scene_active = False
        self.current_level = data['level']
        self.current_lifelines_state = data.get('lifelines', self.current_lifelines_state)
        self.lbl_question.config(text=f"CÂU {self.current_level} - {data['prize']} VNĐ\n{data['question']}")

        for option, btn in self.option_buttons.items():
            option_text = data['options'].get(option, '')
            if option_text:
                self.place_answer_button(option)
                self.set_option_label_text(option, option_text)
                self.style_answer_button(option, "normal")
            else:
                btn.place_forget()

        self.update_prize_display(self.current_level)
        self.status_bar.config(text=f"Đang chờ thí sinh trả lời câu {self.current_level}...")

    def update_prize_display(self, current_level):
        """Cập nhật màu sắc của bảng giải thưởng."""
        for i, label in enumerate(self.prize_labels):
            prize_level = 15 - i
            is_milestone = prize_level in [5, 10, 15]

            if prize_level < current_level:
                label.config(image=self.prize_row_images["dim"], bg="#050b23", fg=PASSED_PRIZE_COLOR)
            elif prize_level == current_level:
                label.config(image=self.prize_row_images["selected"], bg="#050b23", fg="#050E21")
            else:
                color = MILESTONE_COLOR if is_milestone else DEFAULT_PRIZE_COLOR
                image_key = "milestone" if is_milestone else "normal"
                label.config(image=self.prize_row_images[image_key], bg="#050b23", fg=color)

    def handle_lifeline_result(self, data):
        """Xử lý kết quả từ sự trợ giúp (chỉ hiển thị 50:50)."""
        lifeline = data.get('lifeline')
        if lifeline in self.current_lifelines_state:
            self.current_lifelines_state[lifeline] = False
        if lifeline == '5050' and 'options' in data:
            for option, btn in self.option_buttons.items():
                if not data['options'].get(option):
                    btn.place_forget()

    def show_locked_answer(self, data):
        """Hiển thị ngay đáp án thí sinh vừa chốt, trước khi công bố đúng/sai."""
        player_answer = data.get('player_answer')
        if not player_answer or player_answer not in self.option_buttons:
            return

        for key, btn in self.option_buttons.items():
            if btn.winfo_ismapped():
                self.style_answer_button(key, "selected" if key == player_answer else "normal")

        if data.get('requires_host_confirm'):
            self.status_bar.config(text=f"Thí sinh đã chọn {player_answer}. Chờ MC công bố đáp án...")
        else:
            self.status_bar.config(text=f"Thí sinh đã chọn {player_answer}.")

    def unlock_answer_display(self, data):
        if data.get('level') != self.current_level:
            return
        for key, btn in self.option_buttons.items():
            if btn.winfo_ismapped():
                self.style_answer_button(key, "normal")
        self.status_bar.config(text="Host đã hủy chốt đáp án. Chờ thí sinh chọn lại.")

    def show_give_up_regret(self, data):
        self.current_lifelines_state = {key: False for key in self.current_lifelines_state}
        self.status_bar.config(
            text=f"Thí sinh đã give up câu {data.get('level')}. Đang chờ đáp án tiếc nuối..."
        )

    def show_answer_result(self, data):
        """Hiển thị kết quả trả lời của người chơi."""
        player_answer = data.get('player_answer')
        correct_answer = data.get('correct_answer')

        # Đánh dấu câu trả lời của người chơi
        if player_answer and player_answer in self.option_buttons:
            self.style_answer_button(player_answer, "selected")

        for key, btn in self.option_buttons.items():
            if btn.winfo_ismapped():
                if key == correct_answer:
                    self.style_answer_button(key, "correct")
                else:
                    self.style_answer_button(key, "wrong" if key == player_answer else "dim")

        status = "đúng" if data.get('correct') else "sai"
        prefix = "Đáp án tiếc nuối" if data.get('give_up_regret') else "Công bố: thí sinh trả lời"
        self.status_bar.config(text=f"{prefix} {status}. Đáp án đúng: {correct_answer}.")

    def show_final_scene(self, data, is_win):
        self.final_scene_active = True
        self.play_final_audio(is_win)
        player_name = data.get('player_name', 'Thí sinh')
        prize = data.get('prize', '0')
        if is_win:
            title = "CHÚC MỪNG TRIỆU PHÚ"
        elif data.get('reason') == 'give_up':
            title = "THÍ SINH DỪNG CUỘC CHƠI"
        else:
            title = "PHẦN THI KẾT THÚC"
        self.show_overlay(f"{title}\n\n{player_name}\nSố tiền nhận được: {prize} VNĐ")
        self.status_bar.config(text=f"Kết thúc lượt chơi. Số tiền nhận được: {prize} VNĐ")

    def reset_ui_for_new_game(self):
        """Reset giao diện để chờ lượt chơi mới."""
        self.final_scene_active = False
        self.stop_scene_audio()
        self.show_overlay("Lượt chơi đã kết thúc. Chờ người chơi mới...")
        self.current_level = 0
        self.current_lifelines_state = {'5050': True, 'audience': True, 'call': True, 'wise_man': True}
        self.update_prize_display(0)

        # Đảm bảo tất cả các nút đáp án được hiển thị lại
        for option, btn in self.option_buttons.items():
            self.place_answer_button(option)
            btn.config(text=f"{option}:")
            self.style_answer_button(option, "normal")

    def handle_disconnection(self):
        """Xử lý khi mất kết nối tới server."""
        if self.viewer_socket:
            self.viewer_socket = None
            if self.final_scene_active:
                return
            messagebox.showinfo("Mất kết nối", "Mất kết nối tới server.")
            self.destroy()

    def on_closing(self):
        """Dọn dẹp tài nguyên khi đóng cửa sổ."""
        self.stop_scene_audio()
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
