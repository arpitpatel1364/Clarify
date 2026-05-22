"""
Clarify — Global Hotkey Manager (Linux, X11)
Uses python-xlib to register hotkeys globally without requiring root permissions.
"""
from __future__ import annotations
import threading
from typing import Callable, Optional
from config.settings import settings


class HotkeyManager:
    def __init__(self, on_hotkey: Callable[[], None]):
        self.on_hotkey = on_hotkey
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if not settings.trigger.hotkey_enabled:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="X11HotkeyListener"
        )
        self._thread.start()

    def _loop(self):
        from Xlib import X, XK
        from Xlib.display import Display
        import Xlib.error

        try:
            disp = Display()
            root = disp.screen().root
            combo = settings.trigger.hotkey_combo.lower()
            parts = combo.split("+")
            mods = 0
            key = None

            for p in parts:
                if p == "ctrl":
                    mods |= X.ControlMask
                elif p == "shift":
                    mods |= X.ShiftMask
                elif p == "alt":
                    mods |= X.Mod1Mask
                elif p == "super" or p == "win":
                    mods |= X.Mod4Mask
                else:
                    key = p

            if not key:
                print(f"[HotkeyManager] Invalid hotkey configuration: {combo}")
                return

            keysym = XK.string_to_keysym(key)
            if keysym == 0:
                # Try uppercase
                keysym = XK.string_to_keysym(key.upper())
            if keysym == 0:
                print(f"[HotkeyManager] Unknown keysym for key: {key}")
                return

            keycode = disp.keysym_to_keycode(keysym)
            if keycode == 0:
                print(f"[HotkeyManager] Unknown keycode for keysym: {keysym}")
                return

            # Grab key with Lock/NumLock permutations to ensure reliability
            # modifiers: 0, NumLock (Mod2Mask), CapsLock (LockMask), and both
            for extra_mod in [0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask]:
                try:
                    root.grab_key(keycode, mods | extra_mod, True, X.GrabModeAsync, X.GrabModeAsync)
                except Xlib.error.BadAccess:
                    # Hotkey already grabbed by another app or desktop manager
                    pass

            print(f"[HotkeyManager] Registered non-root X11 hotkey: {combo}")

            while self._running:
                # wait for keypress events
                event = disp.next_event()
                if event.type == X.KeyPress and event.detail == keycode:
                    self._fired()
        except Exception as e:
            print(f"[HotkeyManager] X11 Grab failed: {e}")

    def _fired(self):
        try:
            self.on_hotkey()
        except Exception as e:
            print(f"[HotkeyManager] Callback error: {e}")

    def update(self):
        """Re-register after settings change."""
        self.stop()
        if settings.trigger.hotkey_enabled:
            self.start()

    def stop(self):
        self._running = False
        # We don't explicitly ungrab since the X connection closes automatically when the thread/app exits
        if self._thread and self._thread.is_alive():
            # A dummy X event can be sent to unblock next_event(), but thread daemon=True will exit on app close anyway.
            pass
