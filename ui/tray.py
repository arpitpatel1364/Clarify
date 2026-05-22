"""
Clarify — System Tray Icon
Manages tray icon, right-click menu, status indicators.
"""
from __future__ import annotations
import sys
import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont, QPainterPath, QBrush
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize


def _make_tray_icon(active: bool = True, color: str = "#00D4FF") -> QIcon:
    """Generate tray icon programmatically."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer circle
    bg = QColor(color if active else "#5B6380")
    bg.setAlpha(220)
    painter.setBrush(QBrush(bg))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # Letter T
    painter.setPen(QColor(255, 255, 255, 240))
    font = QFont("sans-serif", 26, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "T")
    painter.end()
    return QIcon(pm)


class TrayManager(QObject):
    open_chat_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    pause_toggled = pyqtSignal(bool)  # True = paused

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = False
        self._tray = QSystemTrayIcon()
        self._setup_tray()

    def _setup_tray(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "assets", "logo.png")
        if os.path.exists(icon_path):
            self._icon_active = QIcon(icon_path)
        else:
            self._icon_active = _make_tray_icon(True)
            
        self._icon_paused = _make_tray_icon(False)
        self._tray.setIcon(self._icon_active)
        self._tray.setToolTip("Clarify — AI Explainer (Active)")

        self._menu = QMenu()
        self._menu.setStyleSheet("""
            QMenu {
                background: rgba(10, 14, 39, 250);
                border: 1px solid rgba(108, 92, 231, 80);
                border-radius: 10px;
                padding: 6px 0px;
                color: rgba(245, 247, 250, 220);
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 20px 8px 16px;
                border-radius: 6px;
                margin: 1px 6px;
            }
            QMenu::item:selected {
                background: rgba(108, 92, 231, 80);
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(245, 247, 250, 15);
                margin: 4px 12px;
            }
        """)

        self._header_action = self._menu.addAction("✦ Clarify")
        self._header_action.setEnabled(False)
        self._menu.addSeparator()

        self._pause_action = self._menu.addAction("⏸  Pause")
        self._pause_action.triggered.connect(self._toggle_pause)

        self._chat_action = self._menu.addAction("💬  Open Chat Panel")
        self._chat_action.triggered.connect(self.open_chat_requested.emit)

        self._settings_action = self._menu.addAction("⚙  Settings")
        self._settings_action.triggered.connect(self.open_settings_requested.emit)

        self._menu.addSeparator()

        self._quit_action = self._menu.addAction("✕  Quit Clarify")
        self._quit_action.triggered.connect(self.quit_requested.emit)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_chat_requested.emit()

    def _toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self._tray.setIcon(self._icon_paused)
            self._tray.setToolTip("Clarify — Paused")
            self._pause_action.setText("▶  Resume")
        else:
            self._tray.setIcon(self._icon_active)
            self._tray.setToolTip("Clarify — AI Explainer (Active)")
            self._pause_action.setText("⏸  Pause")
        self.pause_toggled.emit(self._paused)

    def notify(self, title: str, message: str):
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.NoIcon, 3000)

    def set_processing(self, processing: bool):
        """Pulse the icon slightly to show processing."""
        pass  # Could animate in future

    @property
    def is_paused(self) -> bool:
        return self._paused
