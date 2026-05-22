"""
Clarify — Glassmorphism Tooltip Popup
Appears near cursor with streaming AI explanation.
Smooth fade/slide animations, frosted glass aesthetic.
"""
from __future__ import annotations
import textwrap
from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSizePolicy,
    QApplication
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QPoint, QRect, QSize, QThread, pyqtSlot
)
from PyQt6.QtGui import (
    QPainter, QColor, QPainterPath, QFont, QFontDatabase,
    QPixmap, QLinearGradient, QBrush, QPen, QCursor
)

# ── Design Token Constants ────────────────────────────────────────────────────
# Cosmic Ink × Spectral Violet × Aqua Cyan palette
_BG_OVERLAY   = "rgba(10, 14, 39, 0.94)"
_BORDER_MID   = "rgba(245, 247, 250, 0.08)"
_BORDER_ACCENT= "rgba(108, 92, 231, 0.35)"
_ACCENT_400   = "#00D4FF"
_ACCENT_GLOW  = "rgba(0, 212, 255, 0.20)"
_ACCENT_500   = "#33DDFF"
_ACCENT_600   = "#00B5D9"
_AQUA_400     = "#00D084"
_AQUA_MUTED   = "rgba(0, 208, 132, 0.18)"
_TEXT_PRIMARY = "#F5F7FA"
_TEXT_BODY    = "#A0A8C0"
_TEXT_MUTED   = "#5B6380"
_TEXT_ACCENT  = "#00D4FF"

GLASS_STYLE = """
QWidget#popup_root {
    background: transparent;
}

QFrame#glass_frame {
    background: rgba(10, 14, 39, 0.94);
    border-radius: 16px;
    border: 1px solid rgba(108, 92, 231, 0.3);
}

QLabel#title_label {
    color: #00D4FF;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 0px;
    background: transparent;
}

QLabel#selected_preview {
    color: #A0A8C0;
    font-size: 11px;
    font-style: italic;
    padding: 8px 12px;
    background: rgba(245, 247, 250, 0.05);
    border-radius: 8px;
    border-left: 2px solid #6C5CE7;
}

QLabel#explanation_text {
    color: #F5F7FA;
    font-size: 14px;
    line-height: 1.6;
    padding: 4px 2px;
    background: transparent;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QScrollBar:vertical {
    background: rgba(245, 247, 250, 0.04);
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: rgba(108, 92, 231, 0.5);
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(108, 92, 231, 0.8);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QPushButton#action_btn {
    background: rgba(245, 247, 250, 0.05);
    color: #A0A8C0;
    border: 1px solid rgba(245, 247, 250, 0.08);
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 16px;
}
QPushButton#action_btn:hover {
    background: rgba(108, 92, 231, 0.15);
    border: 1px solid rgba(108, 92, 231, 0.4);
    color: #F5F7FA;
}
QPushButton#action_btn:pressed {
    background: rgba(108, 92, 231, 0.4);
    border: 1px solid #6C5CE7;
    color: white;
}
QPushButton#action_btn:focus {
    border: 1px solid #00D4FF;
    outline: none;
}

QPushButton#close_btn {
    background: transparent;
    color: #5B6380;
    border: none;
    font-size: 14px;
    font-weight: 600;
    padding: 0px;
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
    border-radius: 12px;
}
QPushButton#close_btn:hover {
    background: rgba(255, 71, 87, 0.15);
    color: #FF4757;
}
QPushButton#close_btn:pressed {
    background: rgba(255, 71, 87, 0.3);
    color: white;
}
QPushButton#close_btn:focus {
    border: 1px solid rgba(255, 71, 87, 0.5);
    outline: none;
}

QPushButton#provider_badge {
    background: rgba(0, 208, 132, 0.1);
    color: #00D084;
    border: 1px solid rgba(0, 208, 132, 0.3);
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    letter-spacing: 0.8px;
}
QPushButton#provider_badge:hover {
    background: rgba(0, 208, 132, 0.2);
    border: 1px solid rgba(0, 208, 132, 0.5);
}

QLabel#status_label {
    color: #00D4FF;
    font-size: 12px;
    background: transparent;
}
"""

THINKING_DOTS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class GlassPopup(QWidget):
    """Frosted glass tooltip popup for AI explanations."""

    open_chat_requested = pyqtSignal(str, str, str)  # selected_text, explanation, explanation_id
    bookmark_requested = pyqtSignal(str)              # explanation_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._explanation_id: Optional[str] = None
        self._selected_text = ""
        self._full_explanation = ""
        self._is_streaming = False
        self._dot_index = 0

        self._setup_window()
        self._setup_ui()
        self._setup_animations()
        self._setup_timers()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setObjectName("popup_root")
        self.setMinimumWidth(400)
        self.setMaximumWidth(480)
        self.setStyleSheet(GLASS_STYLE)

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(0)

        # Main glass frame
        self.glass = QFrame()
        self.glass.setObjectName("glass_frame")
        root_layout.addWidget(self.glass)

        layout = QVBoxLayout(self.glass)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # ── Header row ──────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(8)

        self.title_lbl = QLabel("CLARIFY")
        self.title_lbl.setObjectName("title_label")

        self.provider_btn = QPushButton("claude")
        self.provider_btn.setObjectName("provider_badge")
        self.provider_btn.setFlat(True)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("status_label")

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("close_btn")
        self.close_btn.clicked.connect(self.hide_animated)

        header.addWidget(self.title_lbl)
        header.addWidget(self.provider_btn)
        header.addStretch()
        header.addWidget(self.status_lbl)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        # ── Divider ──────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background: rgba(255,255,255,20); max-height:1px; border:none;")
        layout.addWidget(divider)

        # ── Selected text preview ────────────────────────────────────────
        self.preview_lbl = QLabel()
        self.preview_lbl.setObjectName("selected_preview")
        self.preview_lbl.setWordWrap(True)
        self.preview_lbl.setMaximumHeight(50)
        layout.addWidget(self.preview_lbl)

        # ── Explanation text (scrollable) ─────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(80)
        self.scroll.setMaximumHeight(240)

        self.explain_lbl = QLabel()
        self.explain_lbl.setObjectName("explanation_text")
        self.explain_lbl.setWordWrap(True)
        self.explain_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.explain_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.explain_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.scroll.setWidget(self.explain_lbl)
        layout.addWidget(self.scroll)

        # ── Action buttons ────────────────────────────────────────────────
        actions = QHBoxLayout()
        actions.setSpacing(6)

        self.chat_btn = QPushButton("Continue")
        self.chat_btn.setObjectName("action_btn")
        self.chat_btn.clicked.connect(self._on_chat)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("action_btn")
        self.copy_btn.clicked.connect(self._on_copy)

        self.bookmark_btn = QPushButton("Save")
        self.bookmark_btn.setObjectName("action_btn")
        self.bookmark_btn.clicked.connect(self._on_bookmark)

        actions.addWidget(self.chat_btn)
        actions.addWidget(self.copy_btn)
        actions.addWidget(self.bookmark_btn)
        layout.addLayout(actions)

        # drag support
        self._drag_pos = None

    def _setup_animations(self):
        # Opacity fade animation
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Y-slide animation (geometry): slides up 10px on enter
        self._slide_anim = QPropertyAnimation(self, b"geometry")
        self._slide_anim.setDuration(220)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_timers(self):
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._update_dot)
        self._dot_timer.setInterval(80)

        self._scroll_timer = QTimer(self)
        self._scroll_timer.timeout.connect(self._scroll_to_bottom)
        self._scroll_timer.setInterval(50)

    # ── Public API ──────────────────────────────────────────────────────────

    def show_explanation(self, selected_text: str, position: QPoint, provider: str):
        """Start showing the popup for a new selection."""
        self._selected_text = selected_text
        self._full_explanation = ""
        self._is_streaming = True
        self._explanation_id = None

        # Preview truncated selected text
        preview = textwrap.shorten(selected_text, width=80, placeholder="…")
        self.preview_lbl.setText(f'"{preview}"')

        self.explain_lbl.setText("")
        self.provider_btn.setText(provider.upper())
        self.status_lbl.setText("")

        self._position_near_cursor(position)
        self._show_animated()

        self._dot_timer.start()
        self._scroll_timer.start()
        self.status_lbl.setText(THINKING_DOTS[0])

    @pyqtSlot(str)
    def append_token(self, token: str):
        """Called on each streaming token."""
        self._full_explanation += token
        html = self._markdown_to_html(self._full_explanation)
        self.explain_lbl.setText(html)
        self.explain_lbl.adjustSize()

    @pyqtSlot(str, str)
    def finish_explanation(self, explanation_id: str, provider: str):
        """Called when streaming is done."""
        self._is_streaming = False
        self._explanation_id = explanation_id
        self._dot_timer.stop()
        self._scroll_timer.stop()
        self.status_lbl.setText("✓")
        QTimer.singleShot(1500, lambda: self.status_lbl.setText(""))

    @pyqtSlot(str)
    def show_error(self, error_msg: str):
        self._is_streaming = False
        self._dot_timer.stop()
        self._scroll_timer.stop()
        self.explain_lbl.setText(
            f'<span style="color: rgba(255,100,100,200);">⚠ {error_msg}</span>'
        )
        self.status_lbl.setText("")

    # ── Private helpers ──────────────────────────────────────────────────────

    def _markdown_to_html(self, text: str) -> str:
        """Basic markdown → HTML for display, escaping raw HTML to prevent injection and layout breakage."""
        import html
        import re
        # Escape any raw HTML/XML tags in selection or response (e.g. <int>)
        text = html.escape(text)
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        # Inline code
        text = re.sub(r'`(.+?)`', r'<code style="background:rgba(255,255,255,15);padding:1px 4px;border-radius:3px;font-family:monospace;">\1</code>', text)
        # Bullet points
        text = re.sub(r'^[-•] (.+)$', r'&nbsp;&nbsp;• \1', text, flags=re.MULTILINE)
        # Newlines
        text = text.replace('\n', '<br>')
        return f'<span style="color:#F5F7FA;font-size:14px;">{text}</span>'

    def _position_near_cursor(self, cursor_pos: QPoint):
        # Support multi-display context by obtaining the screen where the cursor resides
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
        screen_geo = screen.geometry()

        self.adjustSize()
        w = self.width() or 440
        h = self.height() or 300

        x = cursor_pos.x() + 20
        y = cursor_pos.y() + 20

        if x + w > screen_geo.right() - 20:
            x = cursor_pos.x() - w - 10
        if y + h > screen_geo.bottom() - 40:
            y = cursor_pos.y() - h - 10

        x = max(screen_geo.left() + 20, min(x, screen_geo.right() - w - 20))
        y = max(screen_geo.top() + 20, min(y, screen_geo.bottom() - h - 40))
        self.move(x, y)

    def _show_animated(self):
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        # Opacity
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

        # Slide: start 10px lower, glide to natural position
        self._slide_anim.stop()
        geo = self.geometry()
        start_geo = geo.translated(0, 10)
        self._slide_anim.setStartValue(start_geo)
        self._slide_anim.setEndValue(geo)
        self._slide_anim.start()

    def hide_animated(self):
        # Disconnect first to prevent accumulation if called multiple times
        try:
            self._anim.finished.disconnect(self._after_hide)
        except Exception:
            pass
        self._anim.stop()
        self._anim.setStartValue(self.windowOpacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._after_hide)
        self._anim.start()

    def _after_hide(self):
        self.hide()
        try:
            self._anim.finished.disconnect(self._after_hide)
        except Exception:
            pass

    def _update_dot(self):
        if self._is_streaming:
            self._dot_index = (self._dot_index + 1) % len(THINKING_DOTS)
            self.status_lbl.setText(THINKING_DOTS[self._dot_index])

    def _scroll_to_bottom(self):
        sb = self.scroll.verticalScrollBar()
        # Only auto-scroll if user is close to the bottom (within a 30px threshold)
        if sb.maximum() - sb.value() < 30:
            sb.setValue(sb.maximum())

    def _on_chat(self):
        self.open_chat_requested.emit(
            self._selected_text,
            self._full_explanation,
            self._explanation_id or "",
        )
        self.hide_animated()

    def _on_copy(self):
        try:
            import pyperclip
            pyperclip.copy(self._full_explanation)
        except Exception:
            QApplication.clipboard().setText(self._full_explanation)
        self.copy_btn.setText("✓ Copied")
        QTimer.singleShot(1800, lambda: self.copy_btn.setText("Copy"))

    def _on_bookmark(self):
        if self._explanation_id:
            self.bookmark_requested.emit(self._explanation_id)
            self.bookmark_btn.setText("✓ Saved")
            QTimer.singleShot(1800, lambda: self.bookmark_btn.setText("Save"))

    # ── Drag to move ────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def paintEvent(self, event):
        """Draw multi-layer premium glow border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 16, 16)

        # Layer 1 — wide diffuse ambient halo
        painter.setPen(QPen(QColor(108, 92, 231, 20), 14))
        painter.drawPath(path)

        # Layer 2 — medium glow ring
        painter.setPen(QPen(QColor(0, 212, 255, 40), 6))
        painter.drawPath(path)

        # Layer 3 — crisp accent border
        painter.setPen(QPen(QColor(108, 92, 231, 80), 1))
        painter.drawPath(path)

        # Layer 4 — top-edge "light leak" highlight
        top_path = QPainterPath()
        top_path.addRoundedRect(rect.x() + 20, rect.y(), rect.width() - 40, 1, 0, 0)
        painter.setPen(Qt.PenStyle.NoPen)
        grad = QLinearGradient(rect.x() + 20, rect.y(), rect.x() + rect.width() - 20, rect.y())
        grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        grad.setColorAt(0.4, QColor(255, 255, 255, 55))
        grad.setColorAt(0.6, QColor(255, 255, 255, 55))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(top_path, QBrush(grad))

        painter.end()
