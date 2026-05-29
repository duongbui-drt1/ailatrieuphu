from PIL import Image, ImageDraw, ImageOps, ImageTk

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


def load_button_images(size=(450, 60)):
    return {
        state: ImageTk.PhotoImage(_load_button_image(state, size))
        for state in BUTTON_FILES
    }


def load_lozenge_photo(size=(450, 60), state="normal", radius=None):
    return ImageTk.PhotoImage(_draw_lozenge(size, state, radius=radius))


def load_background_source():
    candidates = [image_path(name) for name in ("background.png", "background.jpg", "background.jpeg")]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    path = max(existing, key=lambda candidate: candidate.stat().st_mtime)
    return Image.open(path).convert("RGB")


def render_background(source, size, fallback_start="#1a237e", fallback_end="#0d1b2a"):
    width, height = size
    if width <= 0 or height <= 0:
        width, height = 1, 1

    if source is not None:
        image = ImageOps.fit(source, (width, height), method=LANCZOS)
    else:
        image = _gradient_image(width, height, fallback_start, fallback_end)

    return ImageTk.PhotoImage(image)


def load_logo_photo(size=(110, 110)):
    path = image_path("logo.png")
    if not path.exists():
        return None
    image = Image.open(path).convert("RGBA").resize(size, LANCZOS)
    return ImageTk.PhotoImage(image)


def _load_button_image(state, size):
    return _draw_lozenge(size, state, radius=size[1] // 2)


def _fallback_button(size, fill, outline):
    return _draw_lozenge(size, "normal", radius=size[1] // 2)


def _polish_button(source, state, size):
    base = _draw_lozenge(size, state, radius=size[1] // 2)
    source = _rounded_image(source, size, radius=size[1] // 2)
    base.alpha_composite(source)
    return _draw_lozenge(size, state, radius=size[1] // 2, base=base)


def _draw_capsule_button(size, fill, outline, base=None):
    return _draw_lozenge(size, "normal", radius=size[1] // 2, base=base)


def _draw_lozenge(size, state="normal", radius=None, base=None):
    width, height = size
    image = base or Image.new("RGBA", size, (0, 0, 0, 0))
    style = BUTTON_STYLES.get(state, BUTTON_STYLES["normal"])
    radius = radius if radius is not None else min(12, max(4, height // 4))
    compact = height < 42

    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_inset = 2 if compact else 3
    mask_draw.rounded_rectangle(
        (mask_inset, mask_inset, width - 1 - mask_inset, height - 1 - mask_inset),
        radius=radius,
        fill=255,
    )
    gradient = _horizontal_center_gradient(width, height, style["edge"], style["center"])
    image.paste(gradient, (0, 0), mask)

    draw = ImageDraw.Draw(image)
    glow_rgb = _hex_to_rgb(style["glow"])
    outline_rgb = _hex_to_rgb(style["outline"])
    glow_layers = [(0, 68)] if compact else [(0, 55), (2, 80)]
    for inset, alpha in glow_layers:
        draw.rounded_rectangle(
            (inset, inset, width - 1 - inset, height - 1 - inset),
            radius=max(radius - inset, 2),
            outline=(*glow_rgb, alpha),
            width=1 if compact else 2,
        )
    draw.rounded_rectangle(
        (2, 2, width - 3, height - 3),
        radius=radius,
        outline=outline_rgb,
        width=2 if compact else 3,
    )
    if not compact:
        draw.rounded_rectangle(
            (8, 8, width - 9, height // 2),
            radius=radius // 2,
            outline=(255, 255, 255, 48),
            width=1,
        )
        draw.rounded_rectangle(
            (10, height // 2, width - 11, height - 10),
            radius=radius // 2,
            outline=(0, 0, 0, 90),
            width=1,
        )
    return image


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
