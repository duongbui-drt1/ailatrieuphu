from PIL import Image, ImageDraw, ImageOps, ImageTk

from resources import image_path


LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

BUTTON_FILES = {
    "normal": ("button_normal.png", "normal.png"),
    "selected": ("button_selected.png", "selected.png"),
    "correct": ("button_correct.png", "correct.png"),
    "wrong": ("button_wrong.png", "wrong.png"),
}

FALLBACK_BUTTON_COLORS = {
    "normal": ("#243c9f", "#7fa7ff"),
    "selected": ("#d58d00", "#ffdf73"),
    "correct": ("#14733d", "#67e69c"),
    "wrong": ("#8f1d2b", "#ff7d8c"),
}


def load_button_images(size=(450, 60)):
    return {
        state: ImageTk.PhotoImage(_load_button_image(state, size))
        for state in BUTTON_FILES
    }


def load_background_source():
    path = image_path("background.png", "background.jpg")
    if not path.exists():
        return None
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
    path = image_path(*BUTTON_FILES[state])
    if path.exists():
        source = Image.open(path).convert("RGBA").resize(size, LANCZOS)
        return _polish_button(source, state, size)
    return _fallback_button(size, *FALLBACK_BUTTON_COLORS[state])


def _fallback_button(size, fill, outline):
    return _draw_capsule_button(size, fill, outline)


def _polish_button(source, state, size):
    fill, outline = FALLBACK_BUTTON_COLORS[state]
    base = _draw_capsule_button(size, fill, outline)
    source = _rounded_image(source, size, radius=size[1] // 2)
    base.alpha_composite(source)
    return _draw_capsule_button(size, fill, outline, base=base)


def _draw_capsule_button(size, fill, outline, base=None):
    width, height = size
    image = base or Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = height // 2
    fill_color = fill if base is None else None

    draw.rounded_rectangle(
        (2, 2, width - 3, height - 3),
        radius=radius,
        fill=fill_color,
        outline=outline,
        width=3,
    )
    draw.rounded_rectangle(
        (8, 8, width - 9, height // 2),
        radius=radius // 2,
        outline=(255, 255, 255, 70),
        width=1,
    )
    draw.rounded_rectangle(
        (10, height // 2, width - 11, height - 10),
        radius=radius // 2,
        outline=(0, 0, 0, 70),
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
