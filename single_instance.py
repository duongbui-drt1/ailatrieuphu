from __future__ import annotations

import socket
import tkinter as tk
from tkinter import messagebox


_LOCKS: dict[str, socket.socket] = {}


def ensure_single_instance(role: str, port: int, title: str) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.listen(1)
    except OSError:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(title, f"{title} đang chạy rồi. Không mở thêm tab/app thứ hai.")
            root.destroy()
        except Exception:
            pass
        return False

    _LOCKS[role] = sock
    return True
