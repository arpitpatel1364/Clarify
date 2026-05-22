"""
Clarify — Main Application
Orchestrates: tray, selection monitor, hotkey, popup, chat panel, settings.
All UI callbacks happen on the Qt main thread via QTimer.singleShot(0, ...).
"""
from __future__ import annotations
import sys
import uuid
import os

# Must be set before any Qt import on some Linux setups
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont, QCursor, QIcon

from config.settings import settings
from db.database import get_db, SessionRecord, save_explanation
from core.ai_router import explain_text
from system_platform.linux import SelectionMonitor
from system_platform.hotkey import HotkeyManager
from ui.tray import TrayManager
from ui.tooltip_popup import GlassPopup
from ui.chat_panel import ChatPanel
from ui.settings_window import SettingsWindow
from PyQt6.QtCore import QObject, pyqtSignal

class ExplainBridge(QObject):
    on_token = pyqtSignal(str)
    on_done = pyqtSignal(str, int, str)
    on_error = pyqtSignal(str)
    trigger_explain = pyqtSignal(str, str)

class ClarifyApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Clarify")
        self.app.setDesktopFileName("clarify")
        self.app.setQuitOnLastWindowClosed(False)

        # Font — Inter for crisp Linux rendering (falls back to system sans-serif)
        font = QFont("Inter")
        font.setPointSize(11)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.app.setFont(font)
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")
        self.app.setWindowIcon(QIcon(icon_path))

        # DB session
        self._db = get_db()
        self._session_record = SessionRecord(
            id=str(uuid.uuid4()),
            os="linux",
            provider=settings.ai.active_provider,
        )
        self._db.add(self._session_record)
        self._db.commit()
        self._session_id = self._session_record.id

        # State
        self._last_selected = ""
        self._pending_text = ""
        self._pending_source = ""
        self._is_processing = False

        # UI components
        self.tray = TrayManager()
        self.popup = GlassPopup()
        self.chat_panel = ChatPanel()
        self.settings_win = SettingsWindow()

        # Platform
        self.monitor = SelectionMonitor(on_selection=self._on_selection_detected)
        self.hotkey_mgr = HotkeyManager(on_hotkey=self._on_hotkey)

        # Thread-safe signal bridge
        self._bridge = ExplainBridge()
        self._bridge.on_token.connect(self._on_token)
        self._bridge.on_done.connect(self._on_done)
        self._bridge.on_error.connect(self._on_error)
        self._bridge.trigger_explain.connect(self._trigger_explain)

        self._connect_signals()
        self._start_services()

        print("[Clarify] Started. Watching for text selections…")
        self.tray.notify("Clarify", "Running in background. Select any text to get an explanation.")

    def _connect_signals(self):
        # Tray
        self.tray.open_chat_requested.connect(self._open_chat)
        self.tray.open_settings_requested.connect(self._open_settings)
        self.tray.quit_requested.connect(self._quit)
        self.tray.pause_toggled.connect(self._on_pause_toggled)

        # Popup
        self.popup.open_chat_requested.connect(self._open_chat_from_popup)
        self.popup.bookmark_requested.connect(self._on_bookmark)

        # Settings
        self.settings_win.settings_changed.connect(self._on_settings_changed)

    def _start_services(self):
        self.monitor.start()
        self.hotkey_mgr.start()

    def run(self) -> int:
        return self.app.exec()

    # ── Selection / Hotkey ────────────────────────────────────────────────

    def _on_selection_detected(self, text: str, source_app: str):
        """Called from background thread — must dispatch to Qt thread."""
        if not settings.trigger.auto_on_select:
            return
        if self._is_processing or (hasattr(self, 'chat_panel') and self.chat_panel._is_streaming):
            return
        self._bridge.trigger_explain.emit(text, source_app)

    def _on_hotkey(self):
        """Called from background thread."""
        if not settings.trigger.hotkey_enabled:
            return
        if self._is_processing or (hasattr(self, 'chat_panel') and self.chat_panel._is_streaming):
            return
        # Read current primary selection
        from system_platform.linux import _get_primary_selection, get_active_window_name
        text = _get_primary_selection()
        source = get_active_window_name()
        if text and len(text) >= settings.trigger.min_selection_length:
            self._bridge.trigger_explain.emit(text, source)

    def _trigger_explain(self, text: str, source_app: str):
        """Main-thread: start explanation pipeline."""
        if self._is_processing:
            return
        if text == self._last_selected:
            return

        self._last_selected = text
        self._pending_text = text
        self._pending_source = source_app
        self._is_processing = True

        cursor_pos = QCursor.pos()
        provider = settings.ai.active_provider

        if settings.popup.show_tooltip:
            self.popup.show_explanation(text, cursor_pos, provider)

        self._current_exp_id = None
        self._streamed_full = ""

        explain_text(
            text=text,
            on_token=self._bridge.on_token.emit,
            on_done=lambda full, tokens: self._bridge.on_done.emit(full, tokens, source_app),
            on_error=self._bridge.on_error.emit,
        )

    def _on_token(self, token: str):
        self._streamed_full += token
        if settings.popup.show_tooltip and self.popup.isVisible():
            self.popup.append_token(token)

    def _on_done(self, full: str, tokens: int, source_app: str):
        self._is_processing = False   # ← always reset, even if save fails
        
        try:
            provider = settings.ai.active_provider
            with get_db() as db:
                from db.database import get_or_create_provider
                cfg = get_or_create_provider(db, provider)
                model = cfg.model or provider

                if settings.save_history and full:   # ← only save if full is non-empty
                    exp = save_explanation(
                        db=db,
                        session_id=self._session_id,
                        selected_text=self._pending_text,
                        explanation_text=full,
                        provider=provider,
                        model=model,
                        source_app=source_app,
                        tokens=tokens,
                    )
                    self._current_exp_id = exp.id
        except Exception as e:
            print(f"[Clarify] DB error in _on_done: {e}")

        if settings.popup.show_tooltip and self.popup.isVisible():
            self.popup.finish_explanation(self._current_exp_id or "", provider)

        # Refresh chat panel history if visible
        if self.chat_panel.isVisible():
            self.chat_panel.refresh_history()

    def _on_error(self, error: str):
        self._is_processing = False   # ← always reset on error too
        print(f"[Clarify] AI error: {error}")
        if settings.popup.show_tooltip and self.popup.isVisible():
            self.popup.show_error(error)

    # ── UI Actions ────────────────────────────────────────────────────────

    def _open_chat(self):
        if not self.chat_panel.isVisible():
            self.chat_panel.refresh_history()
            self.chat_panel.show()
        self.chat_panel.raise_()
        self.chat_panel.activateWindow()

    def _open_chat_from_popup(self, selected_text: str, explanation: str, explanation_id: str):
        self.chat_panel.open_with_explanation(selected_text, explanation, explanation_id)
        if not self.chat_panel.isVisible():
            self.chat_panel.show()
        self.chat_panel.raise_()
        self.chat_panel.activateWindow()

    def _open_settings(self):
        if not self.settings_win.isVisible():
            self.settings_win.show()
        self.settings_win.raise_()
        self.settings_win.activateWindow()

    def _on_bookmark(self, explanation_id: str):
        from db.database import toggle_bookmark
        with get_db() as db:
            toggle_bookmark(db, explanation_id)

    def _on_pause_toggled(self, paused: bool):
        if paused:
            self.monitor.pause()
        else:
            self.monitor.resume()
        self._last_selected = ""  # allow re-trigger after resume

    def _on_settings_changed(self):
        self.hotkey_mgr.update()
        self._last_selected = ""
        print("[Clarify] Settings reloaded.")

    def _quit(self):
        print("[Clarify] Quitting…")
        self.monitor.stop()
        self.hotkey_mgr.stop()
        self._db.close()
        self.app.quit()


def main():
    app = ClarifyApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
