from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "images"
AUDIO_DIR = BASE_DIR / "audio"


def image_path(*names):
    for name in names:
        path = IMAGE_DIR / name
        if path.exists():
            return path
    return IMAGE_DIR / names[0] if names else IMAGE_DIR


def audio_path(*names):
    for name in names:
        path = AUDIO_DIR / name
        if path.exists():
            return path
    return None


def question_pack_paths():
    packs = sorted(BASE_DIR.glob("questions_*.json"))
    fallback = BASE_DIR / "questions.json"
    if not packs and fallback.exists():
        packs.append(fallback)
    return packs
