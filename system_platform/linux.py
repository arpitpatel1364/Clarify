"""
Clarify — Linux Selection Monitor
Watches PRIMARY selection (X11 highlight buffer) + clipboard.
Emits signal when new meaningful text is selected.
"""
from __future__ import annotations
import time
import threading
import subprocess
import shutil
from typing import Callable, Optional

from config.settings import settings

# Lazy cache of command existence to prevent constant subprocess spawning when not installed
_HAS_XCLIP = shutil.which("xclip") is not None
_HAS_XSEL = shutil.which("xsel") is not None
_HAS_XDOTOOL = shutil.which("xdotool") is not None


def _get_primary_selection() -> str:
    """Read X11 PRIMARY selection (text highlighted by mouse) incrementally to prevent OOM."""
    max_len = settings.trigger.max_selection_length
    
    if _HAS_XCLIP:
        try:
            # Run without communicate() to avoid loading massive outputs into RAM in a single block
            proc = subprocess.Popen(
                ["xclip", "-selection", "primary", "-o"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            chunks = []
            bytes_read = 0
            while bytes_read < max_len + 100:
                chunk = proc.stdout.read(1024)
                if not chunk:
                    break
                chunks.append(chunk)
                bytes_read += len(chunk)
            proc.terminate()
            proc.wait(timeout=0.1)
            return "".join(chunks).strip()
        except Exception:
            pass

    if _HAS_XSEL:
        try:
            proc = subprocess.Popen(
                ["xsel", "--primary", "--output"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            chunks = []
            bytes_read = 0
            while bytes_read < max_len + 100:
                chunk = proc.stdout.read(1024)
                if not chunk:
                    break
                chunks.append(chunk)
                bytes_read += len(chunk)
            proc.terminate()
            proc.wait(timeout=0.1)
            return "".join(chunks).strip()
        except Exception:
            pass

    return ""


def _get_clipboard() -> str:
    if _HAS_XCLIP:
        try:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=0.5
            )
            return result.stdout.strip()
        except Exception:
            pass

    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception:
        return ""


def get_active_window_name() -> str:
    if not _HAS_XDOTOOL:
        return ""
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=0.5
        )
        return result.stdout.strip()
    except Exception:
        return ""


class SelectionMonitor:
    """
    Polls X11 PRIMARY selection at ~10Hz.
    Calls `on_selection(text)` when a new valid selection is detected.
    Thread-safe, daemon thread.
    """

    def __init__(self, on_selection: Callable[[str, str], None]):
        self.on_selection = on_selection
        self._running = False
        self._paused = False
        self._last_text = ""
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="SelectionMonitor")
        self._thread.start()

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    @property
    def is_running(self) -> bool:
        return self._running and not self._paused

    def _loop(self):
        stable_count = 0
        candidate = ""

        while self._running:
            time.sleep(0.1)  # 10Hz base poll

            if self._paused or not settings.trigger.auto_on_select:
                stable_count = 0
                candidate = ""
                continue

            text = _get_primary_selection()
            min_len = settings.trigger.min_selection_length
            max_len = settings.trigger.max_selection_length

            if not text or len(text) < min_len or len(text) > max_len:
                stable_count = 0
                candidate = ""
                # Clear last text so that clearing highlight resets memory,
                # letting user re-select and explain the same text later.
                with self._lock:
                    self._last_text = ""
                continue

            if text == self._last_text:
                stable_count = 0
                candidate = ""
                continue

            # Debounce: text must be stable for N cycles
            poll_interval = settings.trigger.trigger_delay_ms / 1000.0
            if text == candidate:
                stable_count += 1
            else:
                candidate = text
                stable_count = 1

            # Use round() instead of int() to prevent float division truncation errors
            needed_cycles = max(1, round(poll_interval / 0.1))
            if stable_count >= needed_cycles:
                with self._lock:
                    self._last_text = text
                stable_count = 0
                candidate = ""
                source_app = get_active_window_name()
                try:
                    self.on_selection(text, source_app)
                except Exception as e:
                    print(f"[SelectionMonitor] callback error: {e}")
