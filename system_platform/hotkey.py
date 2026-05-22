"""
Clarify — Global Hotkey Manager (Linux)
Uses keyboard lib for global hotkey registration.
"""
from __future__ import annotations
import threading
from typing import Callable, Optional

from config.settings import settings


class HotkeyManager:
    def __init__(self, on_hotkey: Callable[[], None]):
        self.on_hotkey = on_hotkey
        self._registered = False
        self._hotkey_id = None

    def start(self):
        if not settings.trigger.hotkey_enabled:
            return
        self._register()

    def _register(self):
        try:
            import keyboard
            combo = settings.trigger.hotkey_combo
            keyboard.add_hotkey(combo, self._fired, suppress=False)
            self._registered = True
            print(f"[HotkeyManager] Registered hotkey: {combo}")
        except Exception as e:
            print(f"[HotkeyManager] Could not register hotkey: {e}")

    def _fired(self):
        try:
            self.on_hotkey()
        except Exception as e:
            print(f"[HotkeyManager] callback error: {e}")

    def update(self):
        """Re-register after settings change."""
        try:
            import keyboard
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self._registered = False
        if settings.trigger.hotkey_enabled:
            self._register()

    def stop(self):
        try:
            import keyboard
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
