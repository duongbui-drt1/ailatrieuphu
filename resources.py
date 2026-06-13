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
    from question_packs import active_question_pack_paths

    return active_question_pack_paths()
