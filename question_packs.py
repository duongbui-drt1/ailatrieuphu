from __future__ import annotations

import json
import os
import random
import re
import shutil
import tempfile
import time
from pathlib import Path

from resources import BASE_DIR


MAX_ACTIVE_USES = 2
PACK_PREFIX = "questions_"


def app_data_dir() -> Path:
    override = os.environ.get("AILTP_APP_DATA_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path

    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        path = root / "AiLaTrieuPhu"
    elif sys_platform() == "darwin":
        path = Path.home() / "Library" / "Application Support" / "AiLaTrieuPhu"
    else:
        path = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "ailatrieuphu"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        path = Path(tempfile.gettempdir()) / "AiLaTrieuPhu"
        path.mkdir(parents=True, exist_ok=True)
    return path


def sys_platform() -> str:
    import sys

    return sys.platform


def imported_pack_dir() -> Path:
    path = app_data_dir() / "question_packs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_path() -> Path:
    return app_data_dir() / "question_packs_state.json"


def bundled_pack_paths() -> list[Path]:
    packs = sorted(BASE_DIR.glob("questions_*.json"))
    fallback = BASE_DIR / "questions.json"
    if not packs and fallback.exists():
        packs.append(fallback)
    return packs


def imported_pack_paths() -> list[Path]:
    return sorted(imported_pack_dir().glob("*.json"))


def pack_id_for_path(path: Path, source: str) -> str:
    return f"{source}:{path.name}"


def default_pack_name(path: Path, source: str) -> str:
    stem = path.stem
    match = re.search(r"pack[_-]?(\d+)", stem, flags=re.IGNORECASE)
    if source == "bundled":
        if match:
            return f"Pack chính thức {int(match.group(1)):02d}"
        return "Pack câu hỏi mặc định"

    clean_name = re.sub(r"^questions[_-]?", "", stem, flags=re.IGNORECASE)
    clean_name = re.sub(r"[_-]\d{8}_\d{6}$", "", clean_name)
    clean_name = clean_name.replace("_", " ").replace("-", " ").strip()
    clean_name = re.sub(r"\s+", " ", clean_name) or "nhập ngoài"
    return f"Pack nhập ngoài - {clean_name.title()}"


def load_state() -> dict:
    path = state_path()
    if not path.exists():
        return {"packs": {}}
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict) and isinstance(data.get("packs"), dict):
            return data
    except Exception:
        pass
    return {"packs": {}}


def save_state(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)


def normalize_questions(raw_data) -> list[dict]:
    questions = raw_data.get("questions") if isinstance(raw_data, dict) else raw_data
    if not isinstance(questions, list):
        raise ValueError("Pack must be a JSON list or an object with a questions list.")

    normalized = []
    for index, item in enumerate(questions, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Question {index} must be an object.")
        options = item.get("options")
        answer = str(item.get("answer", "")).strip().upper()
        if not isinstance(options, dict) or answer not in {"A", "B", "C", "D"}:
            raise ValueError(f"Question {index} must include options A-D and answer A/B/C/D.")
        missing = [key for key in ("A", "B", "C", "D") if not str(options.get(key, "")).strip()]
        if missing:
            raise ValueError(f"Question {index} is missing option(s): {', '.join(missing)}.")
        normalized.append(
            {
                "level": int(item.get("level") or index),
                "question": str(item.get("question", "")).strip(),
                "options": {key: str(options.get(key, "")).strip() for key in ("A", "B", "C", "D")},
                "answer": answer,
            }
        )
        if not normalized[-1]["question"]:
            raise ValueError(f"Question {index} is missing question text.")
    if not normalized:
        raise ValueError("Pack has no questions.")
    return normalized


def read_question_pack(path: Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as file:
        return normalize_questions(json.load(file))


def ensure_record(state: dict, path: Path, source: str) -> dict:
    pack_id = pack_id_for_path(path, source)
    default_name = default_pack_name(path, source)
    record = state["packs"].setdefault(
        pack_id,
        {
            "id": pack_id,
            "name": default_name,
            "path": str(path),
            "source": source,
            "status": "active",
            "use_count": 0,
            "created_at": time.time(),
            "last_used_at": None,
        },
    )
    record.update({"id": pack_id, "path": str(path), "source": source})
    existing_name = str(record.get("name") or "")
    if source == "bundled" or existing_name in {"", path.stem}:
        record["name"] = default_name
    record.setdefault("status", "active")
    record.setdefault("use_count", 0)
    record.setdefault("created_at", time.time())
    record.setdefault("last_used_at", None)
    return record


def question_pack_records(include_deleted: bool = False) -> list[dict]:
    state = load_state()
    for path in bundled_pack_paths():
        ensure_record(state, path, "bundled")
    for path in imported_pack_paths():
        ensure_record(state, path, "imported")
    save_state(state)

    records = []
    for record in state["packs"].values():
        path = Path(record.get("path", ""))
        exists = path.exists()
        if record.get("source") == "imported" and not exists and record.get("status") != "deleted":
            record["status"] = "deleted"
        if record.get("status") == "deleted" and not include_deleted:
            continue
        records.append({**record, "exists": exists})
    records.sort(key=lambda item: (item.get("status") != "active", item.get("use_count", 0), item.get("name", "")))
    save_state(state)
    return records


def active_pack_records() -> list[dict]:
    return [
        record
        for record in question_pack_records()
        if record.get("status") == "active" and record.get("exists")
    ]


def active_question_pack_paths() -> list[Path]:
    return [Path(record["path"]) for record in active_pack_records()]


def choose_next_pack(previous_id: str | None = None) -> dict | None:
    records = active_pack_records()
    if not records:
        return None
    candidates = [record for record in records if record["id"] != previous_id] or records
    lowest_use = min(int(record.get("use_count", 0)) for record in candidates)
    least_used = [record for record in candidates if int(record.get("use_count", 0)) == lowest_use]
    return random.choice(least_used)


def mark_pack_used(pack_id: str) -> dict | None:
    state = load_state()
    record = state["packs"].get(pack_id)
    if not record:
        return None
    record["use_count"] = int(record.get("use_count", 0)) + 1
    record["last_used_at"] = time.time()
    if record["use_count"] > MAX_ACTIVE_USES:
        record["status"] = "archived"
        record["archived_reason"] = "usage_limit"
        if record.get("source") == "imported":
            path = Path(record.get("path", ""))
            if path.exists():
                path.unlink()
            record["status"] = "deleted"
            record["deleted_at"] = time.time()
    save_state(state)
    return record


def import_question_pack(source_path: str | Path) -> dict:
    source = Path(source_path)
    questions = read_question_pack(source)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in source.stem).strip("_") or "pack"
    destination = imported_pack_dir() / f"{PACK_PREFIX}{safe_stem}_{timestamp}.json"
    shutil.copy2(source, destination)

    state = load_state()
    record = ensure_record(state, destination, "imported")
    record.update(
        {
            "name": default_pack_name(destination, "imported"),
            "status": "active",
            "use_count": 0,
            "question_count": len(questions),
            "imported_at": time.time(),
        }
    )
    save_state(state)
    return record


def archive_pack(pack_id: str) -> bool:
    state = load_state()
    record = state["packs"].get(pack_id)
    if not record:
        return False
    record["status"] = "archived"
    record["archived_at"] = time.time()
    record["archived_reason"] = "host"
    save_state(state)
    return True


def delete_pack(pack_id: str) -> bool:
    state = load_state()
    record = state["packs"].get(pack_id)
    if not record:
        return False
    path = Path(record.get("path", ""))
    if record.get("source") == "imported" and path.exists():
        path.unlink()
    record["status"] = "deleted"
    record["deleted_at"] = time.time()
    save_state(state)
    return True


def restore_pack(pack_id: str) -> bool:
    state = load_state()
    record = state["packs"].get(pack_id)
    if not record or not Path(record.get("path", "")).exists():
        return False
    record["status"] = "active"
    record.pop("archived_reason", None)
    save_state(state)
    return True
