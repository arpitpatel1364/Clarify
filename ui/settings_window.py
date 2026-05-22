"""
Clarify — Settings Window
Tabs: Triggers | AI Providers | Appearance | Privacy
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QCheckBox, QComboBox, QSlider,
    QTabWidget, QScrollArea, QSizePolicy, QApplication,
    QSpacerItem, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath

from config.settings import settings, AppSettings
from db.database import get_db, get_or_create_provider, ProviderConfig
from core.crypto import encrypt, decrypt

SETTINGS_STYLE = """
QWidget#settings_root {
    background: #060814;
}
QTabWidget::pane {
    background: #060814;
    border: none;
    border-top: 1px solid rgba(108, 92, 231, 0.15);
}
QTabBar {
    background: #0A0E27;
}
QTabBar::tab {
    background: transparent;
    color: #5B6380;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 12px 24px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.8px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: transparent;
    color: #00D4FF;
    border-bottom: 2px solid #00D4FF;
}
QTabBar::tab:hover:!selected {
    color: #F5F7FA;
    border-bottom: 2px solid rgba(0, 212, 255, 0.4);
}
QLabel#settings_brand {
    color: #F5F7FA;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 3px;
    background: transparent;
}
QLabel#settings_brand_dot {
    color: #00D4FF;
    font-size: 18px;
    font-weight: 700;
    background: transparent;
}
QLabel#section_title {
    color: rgba(0, 212, 255, 0.6);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 10px 0px 4px 0px;
    background: transparent;
}
QLabel#setting_label {
    color: #F5F7FA;
    font-size: 13px;
    background: transparent;
}
QLabel#setting_desc {
    color: #A0A8C0;
    font-size: 11px;
    background: transparent;
    padding: 2px 0px;
}
QCheckBox {
    color: #F5F7FA;
    font-size: 13px;
    spacing: 12px;
    background: transparent;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 1px solid rgba(108, 92, 231, 0.5);
    background: #111636;
}
QCheckBox::indicator:checked {
    background: #6C5CE7;
    border: 1px solid #6C5CE7;
    image: none;
}
QCheckBox::indicator:hover {
    border: 1px solid #00D4FF;
    background: rgba(108, 92, 231, 0.15);
}
QCheckBox:focus {
    outline: none;
}
QCheckBox::indicator:focus {
    border: 2px solid #00D4FF;
}
QLineEdit#setting_input {
    background: #111636;
    color: #F5F7FA;
    border: 1px solid rgba(245, 247, 250, 0.08);
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
}
QLineEdit#setting_input:focus {
    border: 1px solid #00D4FF;
    background: #171D47;
}
QLineEdit#setting_input:disabled {
    background: rgba(245, 247, 250, 0.02);
    color: #5B6380;
    border: 1px solid rgba(245, 247, 250, 0.04);
}
QComboBox {
    background: #111636;
    color: #F5F7FA;
    border: 1px solid rgba(245, 247, 250, 0.08);
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    min-width: 160px;
}
QComboBox:focus { border: 1px solid #00D4FF; }
QComboBox:hover { border: 1px solid rgba(0, 212, 255, 0.4); }
QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}
QComboBox QAbstractItemView {
    background: #111636;
    color: #F5F7FA;
    border: 1px solid rgba(108, 92, 231, 0.3);
    selection-background-color: rgba(0, 212, 255, 0.25);
    outline: none;
    padding: 4px;
}
QSlider::groove:horizontal {
    background: rgba(245, 247, 250, 0.08);
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #00D4FF;
    width: 20px;
    height: 20px;
    margin: -7px 0;
    border-radius: 10px;
    border: 2px solid #060814;
}
QSlider::handle:horizontal:hover {
    background: #33DDFF;
}
QSlider::sub-page:horizontal {
    background: #6C5CE7;
    border-radius: 3px;
}
QPushButton#save_btn {
    background: #00D084;
    color: #060814;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 28px;
    letter-spacing: 0.3px;
}
QPushButton#save_btn:hover { background: #33E8A6; }
QPushButton#save_btn:pressed { background: #00B272; }
QPushButton#save_btn:focus {
    border: 2px solid #F5F7FA;
    outline: none;
}
QPushButton#cancel_btn {
    background: rgba(245, 247, 250, 0.05);
    color: #A0A8C0;
    border: 1px solid rgba(245, 247, 250, 0.08);
    border-radius: 10px;
    font-size: 13px;
    padding: 10px 20px;
}
QPushButton#cancel_btn:hover {
    background: rgba(245, 247, 250, 0.09);
    color: #F5F7FA;
    border: 1px solid rgba(245, 247, 250, 0.14);
}
QPushButton#cancel_btn:focus {
    border: 1px solid #00D4FF;
    outline: none;
}
QPushButton#danger_btn {
    background: rgba(255, 71, 87, 0.08);
    color: #FF4757;
    border: 1px solid rgba(255, 71, 87, 0.25);
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    padding: 9px 18px;
    letter-spacing: 0.2px;
}
QPushButton#danger_btn:hover {
    background: rgba(255, 71, 87, 0.18);
    border: 1px solid rgba(255, 71, 87, 0.50);
}
QPushButton#danger_btn:focus {
    border: 1px solid #FF4757;
    outline: none;
}
QPushButton#test_btn {
    background: rgba(0, 208, 132, 0.08);
    color: #00D084;
    border: 1px solid rgba(0, 208, 132, 0.25);
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    padding: 8px 16px;
}
QPushButton#test_btn:hover {
    background: rgba(0, 208, 132, 0.18);
    border: 1px solid rgba(0, 208, 132, 0.50);
}
QPushButton#test_btn:focus {
    border: 1px solid #00D084;
    outline: none;
}
QFrame#divider {
    background: rgba(245, 247, 250, 0.06);
    max-height: 1px;
}
QFrame#provider_card {
    background: #111636;
    border-radius: 12px;
    border: 1px solid rgba(245, 247, 250, 0.08);
    border-left: 3px solid #6C5CE7;
    padding: 6px;
}
QLabel#provider_name {
    color: #F5F7FA;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.3px;
    background: transparent;
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
"""

PROVIDERS = [
    ("claude",      "Claude (Anthropic)",   "claude-sonnet-4-20250514",  "https://api.anthropic.com"),
    ("openai",      "OpenAI",               "gpt-4o",                    "https://api.openai.com/v1"),
    ("gemini",      "Gemini (Google)",       "gemini-1.5-flash",          ""),
    ("groq",        "Groq",                 "llama3-70b-8192",            "https://api.groq.com/openai/v1"),
    ("ollama",      "Ollama (Local)",        "llama3.2:3b",               "http://localhost:11434"),
    ("openrouter",  "OpenRouter",            "openai/gpt-4o",             "https://openrouter.ai/api/v1"),
]

EXPLAIN_STYLES = ["simple", "detailed", "eli5", "technical", "summary"]
HOTKEY_OPTIONS = ["ctrl+shift+e", "ctrl+shift+x", "alt+e", "ctrl+alt+e", "ctrl+shift+space"]


class SettingsWindow(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settings_root")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint
        )
        self.setMinimumSize(660, 520)
        self.setStyleSheet(SETTINGS_STYLE)
        self._provider_widgets: dict = {}
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title_bar = QFrame()
        title_bar.setStyleSheet(
            "background: #0A0E27; border-bottom: 1px solid rgba(108,92,231,0.20);"
        )
        title_bar.setFixedHeight(56)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(22, 0, 16, 0)
        tb_layout.setSpacing(8)

        # Brand dot
        dot_lbl = QLabel("●")
        dot_lbl.setObjectName("settings_brand_dot")
        title_lbl = QLabel("SETTINGS")
        title_lbl.setObjectName("settings_brand")
        title_lbl.setStyleSheet(
            "font-size:14px; font-weight:700; letter-spacing:3px; color:#F5F7FA; background:transparent;"
        )
        close_btn = QPushButton("×")
        close_btn.setStyleSheet(
            "QPushButton { background:transparent; color:#A0A8C0; border:none; "
            "font-size:18px; font-weight:300; padding:2px 6px; border-radius:6px; }"
            "QPushButton:hover { background:rgba(255,71,87,0.22); color:#FF4757; }"
        )
        close_btn.clicked.connect(self.hide)
        tb_layout.addWidget(dot_lbl)
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()
        tb_layout.addWidget(close_btn)
        layout.addWidget(title_bar)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_triggers_tab(), "Triggers")
        self.tabs.addTab(self._build_providers_tab(), "AI Providers")
        self.tabs.addTab(self._build_appearance_tab(), "Appearance")
        self.tabs.addTab(self._build_privacy_tab(), "Privacy")

        # Bottom bar
        bottom = QFrame()
        bottom.setStyleSheet(
            "background: #0A0E27; border-top: 1px solid rgba(108,92,231,0.15);"
        )
        bottom.setFixedHeight(62)
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(20, 0, 20, 0)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(
            "color: #00D084; font-size:11px; background:transparent;"
        )
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("save_btn")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.hide)
        bl.addWidget(self.status_lbl)
        bl.addStretch()
        bl.addWidget(cancel_btn)
        bl.addWidget(save_btn)
        layout.addWidget(bottom)

        self._drag_pos = None

    def _scrollable(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setStyleSheet("background: transparent;")
        scroll.setWidget(widget)
        scroll.setStyleSheet("background: #060814;")
        return scroll

    def _section(self, title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setObjectName("section_title")
        return lbl

    def _divider(self) -> QFrame:
        f = QFrame()
        f.setObjectName("divider")
        return f

    # ── Triggers Tab ────────────────────────────────────────────────────────

    def _build_triggers_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(14)

        layout.addWidget(self._section("SELECTION TRIGGER"))

        self.auto_select_cb = QCheckBox("Auto-explain on text selection")
        self.auto_select_cb.setToolTip("Automatically explain text when you highlight it anywhere")
        layout.addWidget(self.auto_select_cb)

        delay_row = QHBoxLayout()
        delay_lbl = QLabel("Trigger delay (ms):")
        delay_lbl.setObjectName("setting_label")
        self.delay_slider = QSlider(Qt.Orientation.Horizontal)
        self.delay_slider.setRange(200, 2000)
        self.delay_slider.setSingleStep(100)
        self.delay_val_lbl = QLabel("700ms")
        self.delay_val_lbl.setObjectName("setting_label")
        self.delay_val_lbl.setFixedWidth(50)
        self.delay_slider.valueChanged.connect(
            lambda v: self.delay_val_lbl.setText(f"{v}ms"))
        delay_row.addWidget(delay_lbl)
        delay_row.addWidget(self.delay_slider)
        delay_row.addWidget(self.delay_val_lbl)
        layout.addLayout(delay_row)

        min_len_row = QHBoxLayout()
        min_len_lbl = QLabel("Minimum selection length:")
        min_len_lbl.setObjectName("setting_label")
        self.min_len_input = QLineEdit()
        self.min_len_input.setObjectName("setting_input")
        self.min_len_input.setFixedWidth(70)
        min_len_row.addWidget(min_len_lbl)
        min_len_row.addWidget(self.min_len_input)
        min_len_row.addStretch()
        layout.addLayout(min_len_row)

        layout.addWidget(self._divider())
        layout.addWidget(self._section("HOTKEY TRIGGER"))

        self.hotkey_cb = QCheckBox("Enable global hotkey")
        layout.addWidget(self.hotkey_cb)

        hotkey_row = QHBoxLayout()
        hotkey_lbl = QLabel("Hotkey combination:")
        hotkey_lbl.setObjectName("setting_label")
        self.hotkey_combo = QComboBox()
        self.hotkey_combo.addItems(HOTKEY_OPTIONS)
        self.hotkey_combo.setEditable(True)
        hotkey_row.addWidget(hotkey_lbl)
        hotkey_row.addWidget(self.hotkey_combo)
        hotkey_row.addStretch()
        layout.addLayout(hotkey_row)

        desc = QLabel("Note: Select text first, then press the hotkey to trigger an explanation.")
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addWidget(self._divider())
        layout.addWidget(self._section("POPUP BEHAVIOUR"))

        self.show_tooltip_cb = QCheckBox("Show floating tooltip near cursor")
        layout.addWidget(self.show_tooltip_cb)

        layout.addStretch()
        return self._scrollable(container)

    # ── Providers Tab ───────────────────────────────────────────────────────

    def _build_providers_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        active_row = QHBoxLayout()
        active_lbl = QLabel("Active provider:")
        active_lbl.setObjectName("setting_label")
        self.active_provider_combo = QComboBox()
        self.active_provider_combo.addItems([p[0] for p in PROVIDERS])
        active_row.addWidget(active_lbl)
        active_row.addWidget(self.active_provider_combo)
        active_row.addStretch()
        layout.addLayout(active_row)

        temp_row = QHBoxLayout()
        temp_lbl = QLabel("Temperature:")
        temp_lbl.setObjectName("setting_label")
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 10)
        self.temp_val_lbl = QLabel("0.4")
        self.temp_val_lbl.setObjectName("setting_label")
        self.temp_val_lbl.setFixedWidth(30)
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_val_lbl.setText(f"{v/10:.1f}"))
        temp_row.addWidget(temp_lbl)
        temp_row.addWidget(self.temp_slider)
        temp_row.addWidget(self.temp_val_lbl)
        layout.addLayout(temp_row)

        style_row = QHBoxLayout()
        style_lbl = QLabel("Explanation style:")
        style_lbl.setObjectName("setting_label")
        self.style_combo = QComboBox()
        self.style_combo.addItems(EXPLAIN_STYLES)
        style_row.addWidget(style_lbl)
        style_row.addWidget(self.style_combo)
        style_row.addStretch()
        layout.addLayout(style_row)

        layout.addWidget(self._divider())
        layout.addWidget(self._section("API KEYS & MODELS"))

        db = get_db()
        for pid, pname, default_model, default_url in PROVIDERS:
            cfg = get_or_create_provider(db, pid)
            card = self._build_provider_card(pid, pname, cfg, default_model, default_url)
            layout.addWidget(card)
        db.close()

        layout.addStretch()
        return self._scrollable(container)

    def _build_provider_card(self, pid, pname, cfg: ProviderConfig, default_model, default_url) -> QFrame:
        card = QFrame()
        card.setObjectName("provider_card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(8)

        name_lbl = QLabel(f"  {pname}")
        name_lbl.setObjectName("provider_name")
        cl.addWidget(name_lbl)

        key_row = QHBoxLayout()
        key_lbl = QLabel("API Key:")
        key_lbl.setObjectName("setting_label")
        key_lbl.setFixedWidth(70)
        key_input = QLineEdit()
        key_input.setObjectName("setting_input")
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_input.setPlaceholderText("sk-..." if pid != "ollama" else "Not required")
        key_input.setText(decrypt(cfg.api_key or ""))
        if pid == "ollama":
            key_input.setEnabled(False)
        key_row.addWidget(key_lbl)
        key_row.addWidget(key_input)

        test_btn = QPushButton("Test")
        test_btn.setObjectName("test_btn")
        test_btn.clicked.connect(lambda checked, p=pid, k=key_input: self._test_key(p, k.text()))
        key_row.addWidget(test_btn)
        cl.addLayout(key_row)

        model_row = QHBoxLayout()
        model_lbl = QLabel("Model:")
        model_lbl.setObjectName("setting_label")
        model_lbl.setFixedWidth(70)
        model_input = QLineEdit()
        model_input.setObjectName("setting_input")
        model_input.setPlaceholderText(default_model)
        model_input.setText(cfg.model or default_model)
        model_row.addWidget(model_lbl)
        model_row.addWidget(model_input)
        cl.addLayout(model_row)

        if pid in ("ollama", "openrouter"):
            url_row = QHBoxLayout()
            url_lbl = QLabel("Base URL:")
            url_lbl.setObjectName("setting_label")
            url_lbl.setFixedWidth(70)
            url_input = QLineEdit()
            url_input.setObjectName("setting_input")
            url_input.setPlaceholderText(default_url)
            url_input.setText(cfg.base_url or default_url)
            url_row.addWidget(url_lbl)
            url_row.addWidget(url_input)
            cl.addLayout(url_row)
            self._provider_widgets[pid] = (key_input, model_input, url_input)
        else:
            self._provider_widgets[pid] = (key_input, model_input, None)

        return card

    # ── Appearance Tab ──────────────────────────────────────────────────────

    def _build_appearance_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(14)

        layout.addWidget(self._section("POPUP"))

        opacity_row = QHBoxLayout()
        opacity_lbl = QLabel("Popup opacity:")
        opacity_lbl.setObjectName("setting_label")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_val_lbl = QLabel("95%")
        self.opacity_val_lbl.setObjectName("setting_label")
        self.opacity_val_lbl.setFixedWidth(35)
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_val_lbl.setText(f"{v}%"))
        opacity_row.addWidget(opacity_lbl)
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self.opacity_val_lbl)
        layout.addLayout(opacity_row)

        layout.addWidget(self._divider())
        layout.addWidget(self._section("SYSTEM"))

        self.autostart_cb = QCheckBox("Start Clarify on system login")
        layout.addWidget(self.autostart_cb)

        layout.addStretch()
        return self._scrollable(container)

    # ── Privacy Tab ─────────────────────────────────────────────────────────

    def _build_privacy_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(14)

        layout.addWidget(self._section("DATA"))

        self.save_history_cb = QCheckBox("Save explanation history locally")
        layout.addWidget(self.save_history_cb)

        self.encrypt_keys_cb = QCheckBox("Encrypt API keys at rest")
        layout.addWidget(self.encrypt_keys_cb)

        layout.addWidget(self._divider())
        layout.addWidget(self._section("DANGER ZONE"))

        clear_btn = QPushButton("Clear All History")
        clear_btn.setObjectName("danger_btn")
        clear_btn.clicked.connect(self._clear_history)
        layout.addWidget(clear_btn)

        layout.addStretch()
        return self._scrollable(container)

    # ── Load / Save ─────────────────────────────────────────────────────────

    def _load_values(self):
        s = settings
        self.auto_select_cb.setChecked(s.trigger.auto_on_select)
        self.hotkey_cb.setChecked(s.trigger.hotkey_enabled)
        idx = self.hotkey_combo.findText(s.trigger.hotkey_combo)
        if idx >= 0:
            self.hotkey_combo.setCurrentIndex(idx)
        else:
            self.hotkey_combo.setCurrentText(s.trigger.hotkey_combo)
        self.delay_slider.setValue(s.trigger.trigger_delay_ms)
        self.min_len_input.setText(str(s.trigger.min_selection_length))
        self.show_tooltip_cb.setChecked(s.popup.show_tooltip)
        self.opacity_slider.setValue(int(s.popup.tooltip_opacity * 100))
        idx = self.active_provider_combo.findText(s.ai.active_provider)
        if idx >= 0:
            self.active_provider_combo.setCurrentIndex(idx)
        self.temp_slider.setValue(int(s.ai.temperature * 10))
        idx = self.style_combo.findText(s.ai.explain_style)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)
        self.save_history_cb.setChecked(s.save_history)
        self.encrypt_keys_cb.setChecked(s.encrypt_keys)
        self.autostart_cb.setChecked(s.autostart)

    def _save(self):
        s = settings
        s.trigger.auto_on_select = self.auto_select_cb.isChecked()
        s.trigger.hotkey_enabled = self.hotkey_cb.isChecked()
        s.trigger.hotkey_combo = self.hotkey_combo.currentText()
        s.trigger.trigger_delay_ms = self.delay_slider.value()
        try:
            s.trigger.min_selection_length = int(self.min_len_input.text())
        except ValueError:
            pass
        s.popup.show_tooltip = self.show_tooltip_cb.isChecked()
        s.popup.tooltip_opacity = self.opacity_slider.value() / 100.0
        s.ai.active_provider = self.active_provider_combo.currentText()
        s.ai.temperature = self.temp_slider.value() / 10.0
        s.ai.explain_style = self.style_combo.currentText()
        s.save_history = self.save_history_cb.isChecked()
        s.encrypt_keys = self.encrypt_keys_cb.isChecked()
        s.autostart = self.autostart_cb.isChecked()
        s.save()

        # Save provider keys
        db = get_db()
        for pid, widgets in self._provider_widgets.items():
            key_input, model_input, url_input = widgets
            cfg = get_or_create_provider(db, pid)
            raw_key = key_input.text().strip()
            cfg.api_key = encrypt(raw_key) if raw_key else ""
            cfg.model = model_input.text().strip()
            if url_input:
                cfg.base_url = url_input.text().strip()
            db.commit()
        db.close()

        if s.autostart:
            self._setup_autostart()

        self.status_lbl.setText("✓ Settings saved!")
        QTimer.singleShot(2500, lambda: self.status_lbl.setText(""))
        self.settings_changed.emit()

    def _test_key(self, provider: str, key: str):
        if not key and provider != "ollama":
            self.status_lbl.setText(f"⚠ Enter a key for {provider} first")
            QTimer.singleShot(2000, lambda: self.status_lbl.setText(""))
            return
        self.status_lbl.setText(f"Testing {provider}…")
        # Quick non-blocking test
        import threading
        def _test():
            try:
                if provider == "claude":
                    import anthropic
                    c = anthropic.Anthropic(api_key=key)
                    c.messages.create(model="claude-3-haiku-20240307", max_tokens=5, messages=[{"role":"user","content":"hi"}])
                elif provider in ("openai", "groq", "openrouter"):
                    from openai import OpenAI
                    urls = {"groq":"https://api.groq.com/openai/v1","openrouter":"https://openrouter.ai/api/v1"}
                    kwargs = {"api_key": key}
                    if provider in urls:
                        kwargs["base_url"] = urls[provider]
                    c = OpenAI(**kwargs)
                    c.models.list()
                QTimer.singleShot(0, lambda: self.status_lbl.setText(f"✓ {provider} key works!"))
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.status_lbl.setText(f"✗ {err[:60]}"))
            QTimer.singleShot(3000, lambda: self.status_lbl.setText(""))
        threading.Thread(target=_test, daemon=True).start()

    def _clear_history(self):
        from db.database import SessionLocal, Explanation, Message
        db = get_db()
        db.query(Message).delete()
        db.query(Explanation).delete()
        db.commit()
        db.close()
        self.status_lbl.setText("✓ History cleared")
        QTimer.singleShot(2000, lambda: self.status_lbl.setText(""))

    def _setup_autostart(self):
        from pathlib import Path
        main_py = str(Path(__file__).resolve().parent.parent / "main.py")
        desktop_entry = f"""[Desktop Entry]
Type=Application
Name=Clarify
Exec=python3 {main_py}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        with open(os.path.join(autostart_dir, "clarify.desktop"), "w") as f:
            f.write(desktop_entry)

    # ── Drag ────────────────────────────────────────────────────────────────

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

        # Subtle top-edge gradient sheen (title bar highlight)
        from PyQt6.QtGui import QLinearGradient, QBrush
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(0, 212, 255, 0))
        grad.setColorAt(0.3, QColor(0, 212, 255, 14))
        grad.setColorAt(0.7, QColor(108, 92, 231, 15))
        grad.setColorAt(1.0, QColor(108, 92, 231, 0))
        painter.fillRect(0, 0, self.width(), 52, QBrush(grad))
