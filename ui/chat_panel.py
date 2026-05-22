"""
Clarify — Full Chat Panel
Side panel with history sidebar + active conversation thread.
Glassmorphism dark theme, smooth scrolling.
"""
from __future__ import annotations
import textwrap
from datetime import datetime
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QTextEdit, QSplitter,
    QSizePolicy, QApplication, QListWidget, QListWidgetItem,
    QStackedWidget
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QSize, pyqtSlot
)
from PyQt6.QtGui import (
    QPainter, QColor, QPainterPath, QFont,
    QLinearGradient, QPen, QKeySequence, QShortcut
)

from db.database import get_db, get_history, save_message, toggle_bookmark, Explanation

PANEL_STYLE = """
QWidget#panel_root {
    background: #060814;
}

QFrame#sidebar {
    background: #0A0E27;
    border-right: 1px solid rgba(245, 247, 250, 0.08);
}

QFrame#chat_area {
    background: #060814;
}

QLabel#panel_title {
    color: #00D4FF;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 4px 0px;
    background: transparent;
}

QLineEdit#search_box {
    background: #111636;
    color: #F5F7FA;
    border: 1px solid rgba(245, 247, 250, 0.08);
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
}
QLineEdit#search_box:focus {
    border: 1px solid #00D4FF;
    background: #171D47;
    color: #F5F7FA;
}
QLineEdit#search_box::placeholder {
    color: #5B6380;
}

QListWidget#history_list {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget#history_list::item {
    background: transparent;
    padding: 0px;
    border: none;
    border-radius: 10px;
}
QListWidget#history_list::item:selected {
    background: transparent;
}
QListWidget#history_list:focus {
    outline: none;
}
QListWidget#history_list::item:focus {
    border: 1px solid rgba(0, 212, 255, 0.5);
    background: rgba(0, 212, 255, 0.05);
}

QFrame#history_item {
    background: rgba(245, 247, 250, 0.03);
    border-radius: 10px;
    border: 1px solid rgba(245, 247, 250, 0.05);
    padding: 8px;
}
QFrame#history_item:hover {
    background: rgba(108, 92, 231, 0.15);
    border: 1px solid rgba(108, 92, 231, 0.4);
}

QLabel#history_text {
    color: #F5F7FA;
    font-size: 12px;
    background: transparent;
}
QLabel#history_date {
    color: #A0A8C0;
    font-size: 10px;
    background: transparent;
}
QLabel#history_provider {
    color: #00D084;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background: transparent;
}

QFrame#message_bubble_user {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0F3B82, stop:1 #6C5CE7);
    border-radius: 14px;
    border-top-right-radius: 4px;
    border: 1px solid rgba(108, 92, 231, 0.5);
}
QFrame#message_bubble_assistant {
    background: #111636;
    border-radius: 14px;
    border-top-left-radius: 4px;
    border: 1px solid rgba(245, 247, 250, 0.08);
}

QLabel#msg_text {
    color: #F5F7FA;
    font-size: 14px;
    padding: 6px 10px;
    background: transparent;
}

QTextEdit#chat_input {
    background: #111636;
    color: #F5F7FA;
    border: 1px solid rgba(245, 247, 250, 0.08);
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 14px;
    selection-background-color: rgba(0, 212, 255, 0.3);
}
QTextEdit#chat_input:focus {
    border: 1px solid #00D4FF;
    background: #171D47;
}

QPushButton#send_btn {
    background: #00D4FF;
    color: #060814;
    border: none;
    border-radius: 12px;
    font-size: 18px;
    font-weight: 800;
    padding: 8px 14px;
    min-width: 44px;
    max-width: 44px;
}
QPushButton#send_btn:hover {
    background: #33DDFF;
}
QPushButton#send_btn:pressed {
    background: #00B5D9;
}
QPushButton#send_btn:disabled {
    background: rgba(245, 247, 250, 0.05);
    color: #5B6380;
}
QPushButton#send_btn:focus {
    border: 2px solid #F5F7FA;
    outline: none;
}

QPushButton#new_session_btn {
    background: rgba(108, 92, 231, 0.15);
    color: #00D4FF;
    border: 1px solid rgba(108, 92, 231, 0.4);
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 16px;
    letter-spacing: 0.5px;
}
QPushButton#new_session_btn:hover {
    background: rgba(108, 92, 231, 0.25);
    border: 1px solid #6C5CE7;
    color: #F5F7FA;
}
QPushButton#new_session_btn:pressed {
    background: rgba(108, 92, 231, 0.4);
}
QPushButton#new_session_btn:focus {
    border: 1px solid #00D4FF;
    outline: none;
}

QPushButton#icon_btn {
    background: rgba(245, 247, 250, 0.05);
    color: #A0A8C0;
    border: 1px solid rgba(245, 247, 250, 0.08);
    border-radius: 8px;
    font-size: 13px;
    padding: 6px 12px;
}
QPushButton#icon_btn:hover {
    background: rgba(108, 92, 231, 0.15);
    border: 1px solid rgba(108, 92, 231, 0.4);
    color: #F5F7FA;
}
QPushButton#icon_btn:pressed {
    background: rgba(108, 92, 231, 0.4);
    color: white;
}
QPushButton#icon_btn:focus {
    border: 1px solid #00D4FF;
    outline: none;
}
QPushButton#icon_btn:checked {
    background: rgba(108, 92, 231, 0.2);
    border: 1px solid #6C5CE7;
    color: #00D4FF;
}

QScrollBar:vertical {
    background: rgba(245, 247, 250, 0.03);
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
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QLabel#empty_state {
    color: #A0A8C0;
    font-size: 14px;
    background: transparent;
}

QLabel#context_preview {
    color: #00D4FF;
    font-size: 12px;
    font-style: italic;
    padding: 10px 14px;
    background: rgba(108, 92, 231, 0.1);
    border-radius: 10px;
    border-left: 3px solid #6C5CE7;
}
"""


class HistoryItemWidget(QFrame):
    clicked = pyqtSignal(str)  # explanation_id

    def __init__(self, exp: Explanation, parent=None):
        super().__init__(parent)
        self.exp_id = exp.id
        self.setObjectName("history_item")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        preview = textwrap.shorten(exp.selected_text, width=55, placeholder="…")
        text_lbl = QLabel(preview)
        text_lbl.setObjectName("history_text")
        text_lbl.setWordWrap(True)

        meta = QHBoxLayout()
        meta.setSpacing(6)
        date_lbl = QLabel(exp.created_at.strftime("%b %d, %H:%M") if exp.created_at else "")
        date_lbl.setObjectName("history_date")
        prov_lbl = QLabel(exp.provider.upper())
        prov_lbl.setObjectName("history_provider")
        if exp.is_bookmarked:
            bm_lbl = QLabel("\u25c6")
            bm_lbl.setStyleSheet("color: #00D084; font-size:9px; background:transparent;")
            meta.addWidget(bm_lbl)
        meta.addWidget(date_lbl)
        meta.addStretch()
        meta.addWidget(prov_lbl)

        layout.addWidget(text_lbl)
        layout.addLayout(meta)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.exp_id)


class MessageBubble(QFrame):
    def __init__(self, role: str, content: str, parent=None):
        super().__init__(parent)
        self.setObjectName(f"message_bubble_{role}")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

        lbl = QLabel()
        lbl.setObjectName("msg_text")
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setText(self._format(content))
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(lbl)
        self.lbl = lbl
        self._raw = content  # track raw text for streaming appends

    def _format(self, text: str) -> str:
        import re
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'`(.+?)`',
            r'<code style="background:rgba(255,255,255,15);padding:1px 4px;border-radius:3px;font-family:monospace;font-size:12px;">\1</code>',
            text)
        text = text.replace('\n', '<br>')
        return text

    def append_text(self, token: str):
        self._raw += token
        self.lbl.setText(self._format(self._raw))


class ChatPanel(QWidget):
    """Main full-screen chat panel."""

    _token_signal = pyqtSignal(str)
    _done_signal = pyqtSignal(str, int)
    _error_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_exp_id: Optional[str] = None
        self._current_selected_text = ""
        self._current_explanation = ""
        self._chat_history: List[dict] = []
        self._streaming_bubble: Optional[MessageBubble] = None
        self._is_streaming = False

        self.setObjectName("panel_root")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(800, 550)
        self.setStyleSheet(PANEL_STYLE)

        self._token_signal.connect(self._stream_token)
        self._done_signal.connect(self._stream_done)
        self._error_signal.connect(self._stream_error)

        self._setup_ui()
        self._load_history()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ─────────────────────────────────────────────────────
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(268)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(24, 24, 24, 24)
        sidebar_layout.setSpacing(12)

        # Brand header
        brand_row = QHBoxLayout()
        brand_row.setSpacing(0)
        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        title_lbl = QLabel("CLARIFY")
        title_lbl.setObjectName("brand_label")
        sub_lbl = QLabel("AI READING ASSISTANT")
        sub_lbl.setObjectName("brand_sub")
        brand_col.addWidget(title_lbl)
        brand_col.addWidget(sub_lbl)
        close_btn = QPushButton("×")
        close_btn.setObjectName("icon_btn")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton{font-size:16px; font-weight:300;}"
            "QPushButton:hover{background:rgba(255,71,87,0.22);color:#FF4757;border-color:rgba(255,71,87,0.40);}"
        )
        close_btn.clicked.connect(self.hide)
        brand_row.addLayout(brand_col)
        brand_row.addStretch()
        brand_row.addWidget(close_btn)
        sidebar_layout.addLayout(brand_row)

        # Thin accent divider below brand
        brand_divider = QFrame()
        brand_divider.setFixedHeight(1)
        brand_divider.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 rgba(0,212,255,0.60), stop:1 rgba(0,212,255,0.00));"
        )
        sidebar_layout.addWidget(brand_divider)

        self.search_box = QLineEdit()
        self.search_box.setObjectName("search_box")
        self.search_box.setPlaceholderText("Search history...")
        self.search_box.textChanged.connect(self._filter_history)
        sidebar_layout.addWidget(self.search_box)

        # Filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        self.filter_all = QPushButton("All")
        self.filter_bm = QPushButton("Saved")
        for btn in [self.filter_all, self.filter_bm]:
            btn.setObjectName("icon_btn")
            btn.setCheckable(True)
            filter_row.addWidget(btn)
        self.filter_all.setChecked(True)
        self.filter_all.clicked.connect(lambda: self._set_filter("all"))
        self.filter_bm.clicked.connect(lambda: self._set_filter("bookmarked"))
        filter_row.addStretch()
        sidebar_layout.addLayout(filter_row)

        self.history_list = QListWidget()
        self.history_list.setObjectName("history_list")
        self.history_list.setSpacing(4)
        self.history_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        sidebar_layout.addWidget(self.history_list)

        new_btn = QPushButton("+ New Session")
        new_btn.setObjectName("new_session_btn")
        new_btn.setFixedHeight(38)
        new_btn.clicked.connect(self._on_new_session)
        sidebar_layout.addWidget(new_btn)

        # ── Chat Area ────────────────────────────────────────────────────
        self.chat_area = QFrame()
        self.chat_area.setObjectName("chat_area")
        chat_layout = QVBoxLayout(self.chat_area)
        chat_layout.setContentsMargins(24, 24, 24, 24)
        chat_layout.setSpacing(12)

        # Top bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        self.chat_title = QLabel("Select text anywhere to get started")
        self.chat_title.setObjectName("panel_title")
        self.chat_title.setStyleSheet(
            "font-size:12px; font-weight:500; color:#A0A8C0; letter-spacing:0px;"
        )

        self.bm_btn = QPushButton("Save")
        self.bm_btn.setObjectName("icon_btn")
        self.bm_btn.setFixedHeight(30)
        self.bm_btn.setMinimumWidth(52)
        self.bm_btn.clicked.connect(self._on_bookmark)
        self.bm_btn.setToolTip("Bookmark this explanation")

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("icon_btn")
        self.copy_btn.setFixedHeight(30)
        self.copy_btn.setMinimumWidth(52)
        self.copy_btn.clicked.connect(self._on_copy)

        top_bar.addWidget(self.chat_title)
        top_bar.addStretch()
        top_bar.addWidget(self.copy_btn)
        top_bar.addWidget(self.bm_btn)
        chat_layout.addLayout(top_bar)

        # Context preview
        self.context_preview = QLabel()
        self.context_preview.setObjectName("context_preview")
        self.context_preview.setWordWrap(True)
        self.context_preview.hide()
        chat_layout.addWidget(self.context_preview)

        # Messages scroll area
        self.msg_scroll = QScrollArea()
        self.msg_scroll.setWidgetResizable(True)
        self.msg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.msg_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.msg_scroll.setStyleSheet("background: transparent; border: none;")

        self.msg_container = QWidget()
        self.msg_container.setStyleSheet("background: transparent;")
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(0, 0, 8, 0)
        self.msg_layout.setSpacing(14)
        self.msg_layout.addStretch()

        self.msg_scroll.setWidget(self.msg_container)
        chat_layout.addWidget(self.msg_scroll)

        # Input area
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.chat_input = QTextEdit()
        self.chat_input.setObjectName("chat_input")
        self.chat_input.setPlaceholderText("Ask a follow-up question...")
        self.chat_input.setFixedHeight(52)
        self.chat_input.setAcceptRichText(False)

        self.send_btn = QPushButton("↑")
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setFixedSize(44, 44)
        self.send_btn.clicked.connect(self._on_send)

        input_row.addWidget(self.chat_input)
        input_row.addWidget(self.send_btn)
        chat_layout.addLayout(input_row)

        # Ctrl+Enter to send
        send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        send_shortcut.activated.connect(self._on_send)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.chat_area, 1)

        # Window drag
        self._drag_pos = None

    # ── Public API ──────────────────────────────────────────────────────────

    def _on_new_session(self):
        self._current_exp_id = None
        self._current_selected_text = ""
        self._current_explanation = ""
        self._chat_history = []
        self._clear_messages()
        self.context_preview.hide()
        self.chat_title.setText("Select text anywhere to get started")
        self.chat_input.clear()

    def open_with_explanation(self, selected_text: str, explanation: str, explanation_id: str):
        self._current_exp_id = explanation_id
        self._current_selected_text = selected_text
        self._current_explanation = explanation
        self._chat_history = []

        self._clear_messages()
        self.context_preview.setText(f'"{textwrap.shorten(selected_text, 100, placeholder="…")}"')
        self.context_preview.show()
        self.chat_title.setText(textwrap.shorten(selected_text, 40, placeholder="…"))

        # Show initial explanation as assistant message
        bubble = self._add_bubble("assistant", explanation)
        self._scroll_to_bottom()

        if not self.isVisible():
            self._center_on_screen()
            self.show()
        self.raise_()
        self.activateWindow()

    @pyqtSlot(str)
    def append_token_to_last(self, token: str):
        if self._streaming_bubble:
            self._streaming_bubble.append_text(token)
            self._scroll_to_bottom()

    @pyqtSlot()
    def finish_streaming(self):
        self._is_streaming = False
        self._streaming_bubble = None
        self.send_btn.setEnabled(True)
        self.chat_input.setEnabled(True)

    def refresh_history(self):
        self._load_history()

    # ── History ──────────────────────────────────────────────────────────────

    def _load_history(self, filter_mode="all", query=""):
        self.history_list.clear()
        db = get_db()
        exps = get_history(db, limit=200)
        db.close()

        for exp in exps:
            if filter_mode == "bookmarked" and not exp.is_bookmarked:
                continue
            if query and query.lower() not in exp.selected_text.lower():
                continue

            item = QListWidgetItem(self.history_list)
            widget = HistoryItemWidget(exp)
            widget.clicked.connect(self._load_explanation)
            item.setSizeHint(QSize(240, 72))
            self.history_list.addItem(item)
            self.history_list.setItemWidget(item, widget)

    def _filter_history(self, query: str):
        mode = "bookmarked" if self.filter_bm.isChecked() else "all"
        self._load_history(filter_mode=mode, query=query)

    def _set_filter(self, mode: str):
        self.filter_all.setChecked(mode == "all")
        self.filter_bm.setChecked(mode == "bookmarked")
        self._load_history(filter_mode=mode, query=self.search_box.text())

    def _load_explanation(self, exp_id: str):
        db = get_db()
        exp = db.query(Explanation).filter_by(id=exp_id).first()
        if not exp:
            db.close()
            return
        self._current_exp_id = exp_id
        self._current_selected_text = exp.selected_text
        self._current_explanation = exp.explanation
        self._chat_history = []
        self._clear_messages()
        self.context_preview.setText(f'"{textwrap.shorten(exp.selected_text, 100, placeholder="…")}"')
        self.context_preview.show()
        self.chat_title.setText(textwrap.shorten(exp.selected_text, 40, placeholder="…"))
        self._add_bubble("assistant", exp.explanation)
        for msg in exp.messages:
            self._chat_history.append({"role": msg.role, "content": msg.content})
            self._add_bubble(msg.role, msg.content)
        db.close()
        self._scroll_to_bottom()

    # ── Messaging ────────────────────────────────────────────────────────────

    def _on_send(self):
        text = self.chat_input.toPlainText().strip()
        if not text or self._is_streaming:
            return

        self.chat_input.clear()
        self._add_bubble("user", text)

        # Build context: original explanation context + all prior turns + current question
        context_messages = []

        # Inject original selected text + explanation as context
        if self._current_selected_text or self._current_explanation:
            context_messages.append({
                "role": "user",
                "content": (
                    f"Please explain this text:\n"
                    f'"""\n{self._current_selected_text}\n"""'
                )
            })
            context_messages.append({
                "role": "assistant",
                "content": self._current_explanation
            })

        # Add all prior chat turns
        context_messages.extend(self._chat_history)

        # Add the current user question
        context_messages.append({"role": "user", "content": text})

        # Now append to local history AFTER building context
        self._chat_history.append({"role": "user", "content": text})

        # Create empty streaming bubble
        bubble = self._add_bubble("assistant", "")
        bubble._raw = ""
        self._streaming_bubble = bubble
        self._is_streaming = True
        self.send_btn.setEnabled(False)
        self.chat_input.setEnabled(False)

        from core.ai_router import explain_text

        # Pass current user question as text, full context as extra_messages
        # mode="chat" tells explain_text NOT to wrap text in style prompt
        explain_text(
            text=text,
            on_token=lambda t: QTimer.singleShot(0, lambda tok=t: self._stream_token(tok)),
            on_done=lambda full, tokens: QTimer.singleShot(0, lambda f=full, tk=tokens: self._stream_done(f, tk)),
            on_error=lambda e: QTimer.singleShot(0, lambda err=e: self._stream_error(err)),
            extra_messages=context_messages[:-1],  # context WITHOUT the current question
            original_text=self._current_selected_text,
            mode="chat",
        )

        # Save user message to DB
        if self._current_exp_id:
            try:
                db = get_db()
                save_message(db, self._current_exp_id, "user", text)
                db.close()
            except Exception as e:
                print(f"[Clarify] DB save error: {e}")

    def _stream_token(self, token: str):
        if self._streaming_bubble:
            if not self._streaming_bubble._raw:
                # First token arrived, reset styling
                self._streaming_bubble.lbl.setStyleSheet("color: #F5F7FA; font-style: normal;")
            self._streaming_bubble.append_text(token)
            self._scroll_to_bottom()

    def _stream_done(self, full: str, tokens: int):
        self._is_streaming = False
        self._streaming_bubble = None
        self.send_btn.setEnabled(True)
        self.chat_input.setEnabled(True)
        self._chat_history.append({"role": "assistant", "content": full})
        if self._current_exp_id:
            db = get_db()
            save_message(db, self._current_exp_id, "assistant", full)
            db.close()

    def _stream_error(self, error: str):
        self._is_streaming = False
        if self._streaming_bubble:
            self._streaming_bubble.deleteLater()
            self._streaming_bubble = None
        self.send_btn.setEnabled(True)
        self.chat_input.setEnabled(True)
        self._add_bubble("assistant", f"⚠ Error: {error}")

    def _add_bubble(self, role: str, content: str) -> MessageBubble:
        bubble = MessageBubble(role, content)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            row.addStretch()
            row.addWidget(bubble, 0, Qt.AlignmentFlag.AlignRight)
            bubble.setMaximumWidth(380)
        else:
            row.addWidget(bubble, 0, Qt.AlignmentFlag.AlignLeft)
            bubble.setMaximumWidth(520)
            row.addStretch()
        # Insert before the stretch at the end
        count = self.msg_layout.count()
        self.msg_layout.insertLayout(count - 1, row)

        # Per-bubble fade-in animation
        anim = QPropertyAnimation(bubble, b"windowOpacity")
        anim.setDuration(180)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        # Keep reference alive; store on bubble so GC doesn't collect
        bubble._fade_anim = anim
        anim.start()

        QTimer.singleShot(50, self._scroll_to_bottom)
        return bubble

    def _clear_messages(self):
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    w = item.layout().takeAt(0).widget()
                    if w:
                        w.deleteLater()
            elif item.widget():
                item.widget().deleteLater()

    def _scroll_to_bottom(self):
        sb = self.msg_scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_bookmark(self):
        if self._current_exp_id:
            db = get_db()
            result = toggle_bookmark(db, self._current_exp_id)
            db.close()
            self.bm_btn.setText("✓ Saved" if result else "Save")
            QTimer.singleShot(1800, lambda: self.bm_btn.setText("Save"))
            self._load_history()

    def _on_copy(self):
        try:
            import pyperclip
            pyperclip.copy(self._current_explanation)
        except Exception:
            QApplication.clipboard().setText(self._current_explanation)
        self.copy_btn.setText("✓ Copied")
        QTimer.singleShot(1800, lambda: self.copy_btn.setText("Copy"))

    # ── Window ───────────────────────────────────────────────────────────────

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        w, h = 860, 580
        self.resize(w, h)
        self.move((screen.width() - w) // 2, (screen.height() - h) // 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(6, 8, 20, 255))
