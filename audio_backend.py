import itertools
import os
from pathlib import Path

from resources import audio_path


try:
    import pygame
except ImportError:
    pygame = None


class AudioManager:
    SOUND_FILES = {
        "welcome": "welcome.mp3",
        "wait_1_5": "wait_1_5.mp3",
        "wait_6_10": "wait_6_10.mp3",
        "wait_11_15": "wait_11_15.mp3",
        "ready": "ready.mp3",
        "lifeline": "lifeline.mp3",
        "lifeline_5050": ("lifeline_5050.mp3", "lifeline_5050.wav"),
        "audience_countdown": ("audience_countdown.mp3", "audience_countdown.wav"),
        "lifeline_wise_man": ("lifeline_wise_man.mp3", "lifeline_wise_man.wav"),
        "win": "win.mp3",
        "complete": ("complete.mp3", "complete.wav"),
        "selected": "selected.wav",
        "correct": "correct.wav",
        "wrong": "wrong.wav",
        "end_game": "end_game.wav",
        "ringtone": "ringtone.wav",
    }

    def __init__(self):
        self.sounds = {}
        self.is_muted = False
        self.current_bg_music = None
        self._pygame_ready = False
        self._winmm = None
        self._winsound = None
        self._alias_counter = itertools.count(1)
        self._mci_background_alias = None
        self._mci_effect_aliases = []

        self._init_pygame()
        if not self._pygame_ready:
            self._init_windows_audio()
        self.load_sounds()

    def load_sounds(self):
        for key, filenames in self.SOUND_FILES.items():
            if isinstance(filenames, (tuple, list)):
                path = audio_path(*filenames)
                filename = filenames[0]
            else:
                path = audio_path(filenames)
                filename = filenames
            if not path:
                continue

            if self._pygame_ready and path.suffix.lower() == ".wav":
                try:
                    self.sounds[key] = pygame.mixer.Sound(str(path))
                    continue
                except pygame.error as exc:
                    print(f"Lỗi tải âm thanh '{filename}': {exc}")

            self.sounds[key] = path

    def play(self, name, loop=False):
        if self.is_muted or name not in self.sounds:
            return

        sound = self.sounds[name]
        try:
            if self._pygame_ready:
                self._play_with_pygame(name, sound, loop)
            elif self._winmm:
                self._play_with_windows_audio(name, sound, loop)
        except Exception as exc:
            print(f"Lỗi phát âm thanh '{name}': {exc}")

    def stop_all(self):
        self.current_bg_music = None
        if self._pygame_ready:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
            return

        if self._winsound:
            self._winsound.PlaySound(None, getattr(self._winsound, "SND_PURGE", 0))

        self._mci_close_alias(self._mci_background_alias)
        self._mci_background_alias = None
        for alias in self._mci_effect_aliases:
            self._mci_close_alias(alias)
        self._mci_effect_aliases.clear()

    def set_mute(self, status):
        self.is_muted = status
        if self.is_muted:
            self.stop_all()

    def has_sound(self, name):
        return name in self.sounds

    def _init_pygame(self):
        if pygame is None:
            return
        try:
            pygame.mixer.init()
            self._pygame_ready = True
        except pygame.error as exc:
            print(f"Không thể khởi tạo pygame.mixer: {exc}")

    def _init_windows_audio(self):
        if os.name != "nt":
            return
        try:
            import ctypes
            import winsound

            self._winmm = ctypes.windll.winmm
            self._winsound = winsound
        except Exception as exc:
            print(f"Không thể khởi tạo audio Windows: {exc}")

    def _play_with_pygame(self, name, sound, loop):
        if isinstance(sound, (str, Path)):
            if self.current_bg_music == name and pygame.mixer.music.get_busy():
                return
            pygame.mixer.music.stop()
            pygame.mixer.music.load(str(sound))
            pygame.mixer.music.play(-1 if loop else 0)
            self.current_bg_music = name
        else:
            sound.play(-1 if loop else 0)

    def _play_with_windows_audio(self, name, sound, loop):
        path = Path(sound)
        if path.suffix.lower() == ".wav" and not loop and self._winsound:
            flags = self._winsound.SND_FILENAME | self._winsound.SND_ASYNC
            self._winsound.PlaySound(str(path), flags)
            return

        if loop:
            if self.current_bg_music == name and self._mci_background_alias:
                return
            self._mci_close_alias(self._mci_background_alias)
            self._mci_background_alias = self._mci_play_file(path, repeat=True)
            self.current_bg_music = name
            return

        alias = self._mci_play_file(path, repeat=False)
        self._mci_effect_aliases.append(alias)
        self._trim_mci_effects()

    def _mci_play_file(self, path, repeat=False):
        alias = f"ailtp_{next(self._alias_counter)}"
        self._mci_send(f'open "{path}" alias {alias}')
        repeat_arg = " repeat" if repeat else ""
        self._mci_send(f"play {alias}{repeat_arg}")
        return alias

    def _mci_close_alias(self, alias):
        if not alias or not self._winmm:
            return
        self._mci_send(f"stop {alias}", raise_on_error=False)
        self._mci_send(f"close {alias}", raise_on_error=False)

    def _trim_mci_effects(self):
        while len(self._mci_effect_aliases) > 6:
            alias = self._mci_effect_aliases.pop(0)
            self._mci_close_alias(alias)

    def _mci_send(self, command, raise_on_error=True):
        if not self._winmm:
            return ""

        import ctypes

        result_buffer = ctypes.create_unicode_buffer(255)
        error_code = self._winmm.mciSendStringW(command, result_buffer, 255, None)
        if error_code and raise_on_error:
            error_buffer = ctypes.create_unicode_buffer(255)
            self._winmm.mciGetErrorStringW(error_code, error_buffer, 255)
            raise RuntimeError(error_buffer.value or f"MCI error {error_code}")
        return result_buffer.value
