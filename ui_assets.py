import math
import tkinter as tk

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk

from resources import image_path


LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

BUTTON_FILES = {
    "normal": ("button_normal.png", "normal.png"),
    "selected": ("button_selected.png", "selected.png"),
    "correct": ("button_correct.png", "correct.png"),
    "wrong": ("button_wrong.png", "wrong.png"),
    "dim": ("button_normal.png", "normal.png"),
}

LOZENGE_EDGE = "#050E21"
LOZENGE_CENTER = "#0F254E"
NEON_BLUE = "#00D2FF"
NEON_BLUE_DEEP = "#0072FF"
IMPORTANT_ORANGE = "#FF9900"
CORRECT_GREEN = "#00CC44"

BUTTON_STYLES = {
    "normal": {"edge": LOZENGE_EDGE, "center": LOZENGE_CENTER, "outline": NEON_BLUE, "glow": NEON_BLUE_DEEP},
    "milestone": {"edge": LOZENGE_EDGE, "center": LOZENGE_CENTER, "outline": IMPORTANT_ORANGE, "glow": IMPORTANT_ORANGE},
    "selected": {"edge": "#140A00", "center": IMPORTANT_ORANGE, "outline": IMPORTANT_ORANGE, "glow": IMPORTANT_ORANGE},
    "correct": {"edge": "#001B0A", "center": CORRECT_GREEN, "outline": CORRECT_GREEN, "glow": CORRECT_GREEN},
    "wrong": {"edge": "#24050D", "center": "#A61E36", "outline": "#FF4161", "glow": "#FF4161"},
    "dim": {"edge": "#030711", "center": "#263047", "outline": "#4B5C7F", "glow": "#4B5C7F"},
}

LIFELINE_ASSET_FILES = {
    "5050": ("lifeline_5050.png", "lifeline_50_50.png"),
    "call": ("lifeline_call.png", "lifeline_phone.png"),
    "audience": ("lifeline_audience.png",),
    "wise_man": ("lifeline_wise_man.png", "lifeline_expert.png"),
}

TIMER_ASSET_FILES = ("timer_countdown.png", "timer_30s.png", "timer.png")


def load_button_images(size=(450, 60), background=None):
    return {
        state: ImageTk.PhotoImage(_load_button_image(state, size, background=background))
        for state in BUTTON_FILES
    }


def load_lozenge_photo(size=(450, 60), state="normal", radius=None, background=None):
    return ImageTk.PhotoImage(_draw_lozenge(size, state, radius=radius, base=_background_base(background, size)))


def load_lifeline_icon(kind, size=(96, 58), used=False):
    return ImageTk.PhotoImage(_load_lifeline_image(kind, size, used=used))


def load_timer_photo(size=(220, 220), seconds=30):
    return ImageTk.PhotoImage(_draw_timer_badge(size, seconds=seconds))


def load_background_source():
    candidates = [image_path(name) for name in ("background.png", "background.jpg", "background.jpeg")]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    path = max(existing, key=lambda candidate: candidate.stat().st_mtime)
    return Image.open(path).convert("RGB")


def render_background_image(source, size, fallback_start="#1a237e", fallback_end="#0d1b2a"):
    width, height = size
    if width <= 0 or height <= 0:
        width, height = 1, 1

    if source is not None:
        image = ImageOps.fit(source, (width, height), method=LANCZOS)
    else:
        image = _gradient_image(width, height, fallback_start, fallback_end)

    return image


def render_background(source, size, fallback_start="#1a237e", fallback_end="#0d1b2a"):
    return ImageTk.PhotoImage(render_background_image(source, size, fallback_start, fallback_end))


def load_logo_photo(size=(110, 110)):
    path = image_path("logo.png")
    if not path.exists():
        return None
    image = Image.open(path).convert("RGBA").resize(size, LANCZOS)
    return ImageTk.PhotoImage(image)


def apply_window_icon(window, size=(64, 64)):
    try:
        icon = load_logo_photo(size)
        if not icon:
            return
        window.iconphoto(True, icon)
        window._app_icon_image = icon
    except Exception:
        pass


class ColorButton(tk.Label):
    def __init__(
        self,
        parent,
        command=None,
        bg="#10265f",
        fg="#ffffff",
        activebackground=None,
        activeforeground=None,
        disabledbackground=None,
        disabledforeground="#8a94ad",
        state=tk.NORMAL,
        cursor="hand2",
        **kwargs,
    ):
        hover_enabled = kwargs.pop("hover_enabled", True)
        self._command = command
        self._normal_bg = bg
        self._normal_fg = fg
        self._active_bg = activebackground or bg
        self._active_fg = activeforeground or fg
        self._disabled_bg = disabledbackground or _blend_hex(bg, "#020817", 0.55)
        self._disabled_fg = disabledforeground
        self._enabled = str(state) != str(tk.DISABLED)
        self._cursor = cursor
        self._pressed = False
        self._hover_enabled = bool(hover_enabled)
        kwargs.pop("state", None)
        kwargs.setdefault("bg", bg)
        kwargs.setdefault("fg", fg)
        kwargs.setdefault("anchor", tk.CENTER)
        kwargs.setdefault("takefocus", 1)
        kwargs.setdefault("highlightthickness", 1)
        kwargs.setdefault("highlightbackground", _blend_hex(bg, "#ffffff", 0.18))
        kwargs.setdefault("highlightcolor", activebackground or bg)
        super().__init__(parent, **kwargs)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self.bind("<Return>", self._keyboard_click)
        self.bind("<space>", self._keyboard_click)
        self._apply_visual()

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, str):
            return super().configure(cnf)
        if cnf:
            kwargs.update(cnf)

        command = kwargs.pop("command", None)
        if command is not None:
            self._command = command

        state = kwargs.pop("state", None)
        if "bg" in kwargs:
            self._normal_bg = kwargs["bg"]
        if "fg" in kwargs:
            self._normal_fg = kwargs["fg"]
        if "activebackground" in kwargs:
            self._active_bg = kwargs.pop("activebackground")
        if "activeforeground" in kwargs:
            self._active_fg = kwargs.pop("activeforeground")
        if "disabledbackground" in kwargs:
            self._disabled_bg = kwargs.pop("disabledbackground")
        if "disabledforeground" in kwargs:
            self._disabled_fg = kwargs.pop("disabledforeground")
        if "hover_enabled" in kwargs:
            self._hover_enabled = bool(kwargs.pop("hover_enabled"))
            if not self._hover_enabled:
                self._pressed = False

        super().configure(**kwargs)
        if state is not None:
            self.set_enabled(state)
        else:
            self._apply_visual()

    config = configure

    def cget(self, key):
        if key == "state":
            return tk.NORMAL if self._enabled else tk.DISABLED
        return super().cget(key)

    def set_enabled(self, state):
        self._enabled = str(state) != str(tk.DISABLED)
        if not self._enabled:
            self._pressed = False
        self._apply_visual()

    def _apply_visual(self, active=False, focused=False):
        active = active and self._hover_enabled
        if not self._enabled:
            bg = self._disabled_bg
            fg = self._disabled_fg
            relief = tk.FLAT
            cursor = "arrow"
        else:
            bg = self._active_bg if active else self._normal_bg
            fg = self._active_fg if active else self._normal_fg
            relief = tk.SUNKEN if self._pressed and self._hover_enabled else tk.FLAT
            cursor = self._cursor if self._hover_enabled else "arrow"
        highlight = self._active_bg if (active or focused) and self._enabled else _blend_hex(bg, "#ffffff", 0.18)
        super().configure(bg=bg, fg=fg, cursor=cursor, relief=relief, highlightbackground=highlight)

    def _enter(self, _event=None):
        if not self._hover_enabled:
            return
        self._apply_visual(active=True)

    def _leave(self, _event=None):
        self._pressed = False
        self._apply_visual(active=False)

    def _press(self, _event=None):
        if not self._hover_enabled:
            return
        if self._enabled:
            self.focus_set()
            self._pressed = True
            self._apply_visual(active=True)

    def _release(self, event=None):
        if not self._enabled:
            return
        was_pressed = self._pressed
        self._pressed = False
        self._apply_visual(active=False)
        if not self._hover_enabled:
            return
        if not was_pressed or not self._command:
            return
        if event is not None:
            widget = event.widget.winfo_containing(event.x_root, event.y_root)
            if widget is not self:
                return
        self._command()

    def _focus_in(self, _event=None):
        if not self._hover_enabled:
            return
        self._apply_visual(focused=True)

    def _focus_out(self, _event=None):
        self._pressed = False
        self._apply_visual()

    def _keyboard_click(self, _event=None):
        if self._enabled and self._command:
            self._command()


def _blend_hex(color, target, ratio):
    def parse(value):
        value = str(value).lstrip("#")
        if len(value) != 6:
            return (0, 0, 0)
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

    base_rgb = parse(color)
    target_rgb = parse(target)
    mixed = tuple(round(base_rgb[i] * (1 - ratio) + target_rgb[i] * ratio) for i in range(3))
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def _load_button_image(state, size, background=None):
    return _draw_lozenge(size, state, radius=size[1] // 2, base=_background_base(background, size))


def _fallback_button(size, fill, outline):
    return _draw_lozenge(size, "normal", radius=size[1] // 2)


def _polish_button(source, state, size):
    base = _draw_lozenge(size, state, radius=size[1] // 2)
    source = _rounded_image(source, size, radius=size[1] // 2)
    base.alpha_composite(source)
    return _draw_lozenge(size, state, radius=size[1] // 2, base=base)


def _draw_capsule_button(size, fill, outline, base=None):
    return _draw_lozenge(size, "normal", radius=size[1] // 2, base=base)


def _background_base(background, size):
    if background is None:
        return None
    if isinstance(background, str):
        return Image.new("RGBA", size, background)
    if isinstance(background, Image.Image):
        return background.convert("RGBA").resize(size, LANCZOS)
    return None


def _draw_lozenge(size, state="normal", radius=None, base=None):
    width, height = size
    if width <= 0 or height <= 0:
        return Image.new("RGBA", (max(width, 1), max(height, 1)), (0, 0, 0, 0))

    scale = 3
    scaled_size = (width * scale, height * scale)
    image = base.resize(scaled_size, LANCZOS) if base else Image.new("RGBA", scaled_size, (0, 0, 0, 0))
    style = BUTTON_STYLES.get(state, BUTTON_STYLES["normal"])
    compact = height < 42
    sw, sh = scaled_size
    inset = max(2, int(height * 0.05)) * scale
    nose = max(int(height * 0.48), 20) * scale
    if width < height * 3:
        nose = max(int(width * 0.08), 10) * scale

    mask = Image.new("L", scaled_size, 0)
    mask_draw = ImageDraw.Draw(mask)
    outer_points = _lozenge_points(sw, sh, inset, nose)
    mask_draw.polygon(outer_points, fill=255)

    gradient = _horizontal_center_gradient(sw, sh, style["edge"], style["center"])
    image.paste(gradient, (0, 0), mask)

    draw = ImageDraw.Draw(image)
    outline_rgb = _hex_to_rgb(style["outline"])

    outline_points = _lozenge_points(sw, sh, 3 * scale, nose)
    draw.line(outline_points + [outline_points[0]], fill=outline_rgb, width=2 * scale if compact else 3 * scale, joint="curve")

    inner_inset = 8 * scale if not compact else 5 * scale
    inner_points = _lozenge_points(sw, sh, inner_inset, max(nose - 4 * scale, 5 * scale))
    draw.line(inner_points + [inner_points[0]], fill=(255, 255, 255, 55), width=scale, joint="curve")

    shadow_points = _lozenge_points(sw, sh, max(inner_inset + 5 * scale, 1), max(nose - 7 * scale, 5 * scale))
    lower = [(x, y) for x, y in shadow_points if y >= sh // 2]
    if len(lower) >= 2:
        draw.line(lower, fill=(0, 0, 0, 92), width=scale)

    if not compact:
        left = nose + 8 * scale
        right = sw - nose - 8 * scale
        draw.line((left, 9 * scale, right, 9 * scale), fill=(255, 255, 255, 72), width=scale)
        draw.line((left, sh - 10 * scale, right, sh - 10 * scale), fill=(0, 0, 0, 120), width=scale)
        draw.line((left, sh // 2, right, sh // 2), fill=(255, 255, 255, 18), width=scale)

    return image.resize(size, LANCZOS)


def _lozenge_points(width, height, inset, nose):
    inset = max(0, min(inset, width // 4, height // 3))
    nose = max(inset + 2, min(nose, width // 2 - inset))
    mid_y = height // 2
    return [
        (nose, inset),
        (width - nose, inset),
        (width - inset - 1, mid_y),
        (width - nose, height - inset - 1),
        (nose, height - inset - 1),
        (inset, mid_y),
    ]


def _load_lifeline_image(kind, size=(96, 58), used=False):
    kind = str(kind)
    normal_names = LIFELINE_ASSET_FILES.get(kind, (f"lifeline_{kind}.png",))
    used_names = tuple(_used_lifeline_name(name) for name in normal_names)
    if used:
        used_path = image_path(*used_names)
        if used_path.exists():
            return _fit_transparent_image(used_path, size)

    normal_path = image_path(*normal_names)
    if normal_path.exists():
        image = _fit_transparent_image(normal_path, size)
        if used:
            return _draw_used_cross(image)
        return image

    return _draw_lifeline_icon(kind, size, used=used)


def _used_lifeline_name(name):
    stem, dot, suffix = name.partition(".")
    return f"{stem}_used.{suffix}" if dot else f"{name}_used"


def _fit_transparent_image(path, size):
    source = Image.open(path).convert("RGBA")
    fitted = ImageOps.contain(source, size, method=LANCZOS)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (size[0] - fitted.width) // 2
    y = (size[1] - fitted.height) // 2
    image.alpha_composite(fitted, (x, y))
    return image


def _draw_used_cross(image):
    result = image.copy()
    draw = ImageDraw.Draw(result)
    width, height = result.size
    line_width = max(4, min(width, height) // 10)
    margin = max(7, min(width, height) // 7)
    draw.line((margin, margin, width - margin, height - margin), fill=(130, 6, 18, 235), width=line_width)
    draw.line((width - margin, margin, margin, height - margin), fill=(130, 6, 18, 235), width=line_width)
    draw.line((margin, margin, width - margin, height - margin), fill=(220, 24, 32, 245), width=max(2, line_width // 2))
    draw.line((width - margin, margin, margin, height - margin), fill=(220, 24, 32, 245), width=max(2, line_width // 2))
    return result


def _draw_lifeline_icon(kind, size=(96, 58), used=False):
    width, height = size
    scale = 3
    sw, sh = width * scale, height * scale
    image = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    pad_x = int(width * 0.06) * scale
    pad_y = int(height * 0.08) * scale
    bounds = (pad_x, pad_y, sw - pad_x, sh - pad_y)
    draw.ellipse(bounds, fill=(10, 44, 142, 255), outline=(36, 52, 73, 255), width=5 * scale)
    draw.ellipse(_inset_box(bounds, 4 * scale), outline=(225, 229, 218, 230), width=2 * scale)
    draw.ellipse(_inset_box(bounds, 8 * scale), outline=(96, 181, 255, 90), width=scale)

    kind = str(kind)
    if kind == "5050":
        font = _load_font(int(height * 0.38) * scale, bold=True)
        _draw_centered_text(draw, "50:50", (sw // 2, sh // 2), font, (255, 255, 255, 255), shadow=True)
    elif kind == "call":
        _draw_call_icon(draw, sw, sh, scale)
    elif kind == "audience":
        _draw_audience_icon(draw, sw, sh, scale)
    else:
        _draw_wise_man_icon(draw, sw, sh, scale)

    if used:
        margin = 14 * scale
        draw.line((margin, margin, sw - margin, sh - margin), fill=(138, 8, 18, 235), width=7 * scale)
        draw.line((sw - margin, margin, margin, sh - margin), fill=(138, 8, 18, 235), width=7 * scale)
        draw.line((margin, margin, sw - margin, sh - margin), fill=(210, 28, 36, 235), width=3 * scale)
        draw.line((sw - margin, margin, margin, sh - margin), fill=(210, 28, 36, 235), width=3 * scale)

    return image.resize(size, LANCZOS)


def _draw_timer_badge(size=(220, 220), seconds=30):
    custom = _load_timer_image(size, seconds)
    if custom is not None:
        return custom

    width, height = size
    scale = 3
    sw, sh = width * scale, height * scale
    image = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    cx, cy = sw // 2, sh // 2
    radius = min(sw, sh) // 2 - 24 * scale
    center_box = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(center_box, fill=(12, 53, 158, 255), outline=(205, 213, 205, 240), width=4 * scale)

    dots = 30
    for index in range(dots):
        angle = -90 + (360 / dots) * index
        color = _timer_dot_color(index, dots)
        x = cx + int((radius + 26 * scale) * math.cos(math.radians(angle)))
        y = cy + int((radius + 26 * scale) * math.sin(math.radians(angle)))
        dot = 8 * scale
        draw.ellipse((x - dot, y - dot, x + dot, y + dot), fill=color, outline=(225, 225, 215, 220), width=2 * scale)

    font = _load_font(int(height * 0.36) * scale, bold=True)
    _draw_centered_text(draw, str(seconds), (cx, cy), font, (255, 255, 255, 255), shadow=True)
    return image.resize(size, LANCZOS)


def _load_timer_image(size, seconds):
    per_second_names = (
        f"timer_{seconds:02d}.png",
        f"timer_{seconds}.png",
        f"timer_countdown_{seconds:02d}.png",
        f"timer_countdown_{seconds}.png",
    )
    per_second_path = image_path(*per_second_names)
    if per_second_path.exists():
        return _fit_transparent_image(per_second_path, size)

    background_path = image_path(*TIMER_ASSET_FILES)
    if not background_path.exists():
        return None

    image = _fit_transparent_image(background_path, size)
    draw = ImageDraw.Draw(image)
    font = _load_font(int(size[1] * 0.34), bold=True)
    _draw_centered_text(draw, str(seconds), (size[0] // 2, size[1] // 2), font, (255, 255, 255, 255), shadow=True)
    return image


def _inset_box(box, inset):
    left, top, right, bottom = box
    return (left + inset, top + inset, right - inset, bottom - inset)


def _draw_centered_text(draw, text, center, font, fill, shadow=False):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = center[0] - (bbox[2] - bbox[0]) // 2
    y = center[1] - (bbox[3] - bbox[1]) // 2 - bbox[1] // 2
    if shadow:
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 95))
    draw.text((x, y), text, font=font, fill=fill)


def _draw_call_icon(draw, width, height, scale):
    points = [
        (0.28, 0.64), (0.36, 0.45), (0.45, 0.50), (0.56, 0.30),
        (0.66, 0.36), (0.55, 0.66), (0.45, 0.60), (0.36, 0.76),
    ]
    scaled = [(int(width * x), int(height * y)) for x, y in points]
    draw.line(scaled, fill=(255, 255, 255, 255), width=5 * scale, joint="curve")
    for offset in range(3):
        x = int(width * (0.18 + offset * 0.055))
        draw.arc((x, int(height * 0.42), x + 26 * scale, int(height * 0.78)), 130, 215, fill=(255, 255, 255, 220), width=2 * scale)


def _draw_audience_icon(draw, width, height, scale):
    draw.line((int(width * 0.21), int(height * 0.42), int(width * 0.43), int(height * 0.42)), fill=(255, 255, 255, 255), width=5 * scale)
    draw.line((int(width * 0.32), int(height * 0.25), int(width * 0.32), int(height * 0.60)), fill=(255, 255, 255, 255), width=5 * scale)
    draw.ellipse((int(width * 0.56), int(height * 0.22), int(width * 0.69), int(height * 0.43)), outline=(255, 255, 255, 255), width=4 * scale)
    draw.line((int(width * 0.62), int(height * 0.43), int(width * 0.62), int(height * 0.75)), fill=(255, 255, 255, 255), width=5 * scale)
    draw.line((int(width * 0.62), int(height * 0.54), int(width * 0.77), int(height * 0.76)), fill=(255, 255, 255, 255), width=4 * scale)


def _draw_wise_man_icon(draw, width, height, scale):
    cap = [
        (int(width * 0.27), int(height * 0.39)),
        (int(width * 0.50), int(height * 0.20)),
        (int(width * 0.76), int(height * 0.38)),
        (int(width * 0.50), int(height * 0.55)),
    ]
    draw.polygon(cap, outline=(255, 255, 255, 255), fill=None)
    draw.line(cap + [cap[0]], fill=(255, 255, 255, 255), width=4 * scale)
    draw.rectangle((int(width * 0.40), int(height * 0.50), int(width * 0.62), int(height * 0.70)), outline=(255, 255, 255, 255), width=4 * scale)
    draw.line((int(width * 0.70), int(height * 0.42), int(width * 0.70), int(height * 0.70)), fill=(255, 255, 255, 255), width=3 * scale)


def _timer_dot_color(index, total):
    ratio = index / max(total - 1, 1)
    if ratio < 0.34:
        start, end = (255, 40, 18), (255, 185, 28)
        local = ratio / 0.34
    elif ratio < 0.67:
        start, end = (255, 210, 22), (170, 255, 0)
        local = (ratio - 0.34) / 0.33
    else:
        start, end = (120, 255, 0), (0, 238, 36)
        local = (ratio - 0.67) / 0.33
    return tuple(int(start[i] + (end[i] - start[i]) * local) for i in range(3)) + (255,)


def _load_font(size, bold=False):
    candidates = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _rounded_image(source, size, radius):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=95)
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    result.paste(source, (0, 0), mask)
    return result


def _gradient_image(width, height, start, end):
    image = Image.new("RGB", (width, height), end)
    draw = ImageDraw.Draw(image)
    start_rgb = tuple(int(start.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    end_rgb = tuple(int(end.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

    for y in range(height):
        ratio = y / max(height, 1)
        color = tuple(
            int(start_rgb[index] + (end_rgb[index] - start_rgb[index]) * ratio)
            for index in range(3)
        )
        draw.line([(0, y), (width, y)], fill=color)

    return image


def _horizontal_center_gradient(width, height, edge, center):
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    edge_rgb = _hex_to_rgb(edge)
    center_rgb = _hex_to_rgb(center)

    for x in range(width):
        distance_from_center = abs((x / max(width - 1, 1)) - 0.5) * 2
        center_weight = 1 - distance_from_center
        color = tuple(
            int(edge_rgb[channel] + (center_rgb[channel] - edge_rgb[channel]) * center_weight)
            for channel in range(3)
        )
        draw.line([(x, 0), (x, height)], fill=(*color, 255))
    return image


def _hex_to_rgb(value):
    return tuple(int(value.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
