"""
Clarify — Settings & Configuration
Pydantic-based settings with SQLite persistence
"""
import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, PrivateAttr
from appdirs import user_data_dir, user_config_dir

APP_NAME = "Clarify"
APP_AUTHOR = "Clarify"

DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
CONFIG_DIR = Path(user_config_dir(APP_NAME, APP_AUTHOR))
DB_PATH = DATA_DIR / "clarify.db"
KEY_FILE = DATA_DIR / ".keyfile"

DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class TriggerSettings(BaseModel):
    auto_on_select: bool = True
    hotkey_enabled: bool = True
    hotkey_combo: str = "ctrl+shift+e"
    trigger_delay_ms: int = 700
    min_selection_length: int = 3
    max_selection_length: int = 5000


class PopupSettings(BaseModel):
    show_tooltip: bool = True
    tooltip_width: int = 440
    tooltip_max_height: int = 340
    tooltip_opacity: float = 0.95
    auto_close_seconds: int = 0


class AISettings(BaseModel):
    active_provider: str = "ollama"
    temperature: float = 0.3
    max_tokens: int = 1024
    stream_response: bool = True
    explain_style: str = "simple"


class AppSettings(BaseModel):
    trigger: TriggerSettings = TriggerSettings()
    popup: PopupSettings = PopupSettings()
    ai: AISettings = AISettings()
    theme: str = "dark"
    autostart: bool = False
    save_history: bool = True
    encrypt_keys: bool = True

    _config_file: str = PrivateAttr(default_factory=lambda: str(CONFIG_DIR / "settings.json"))

    model_config = {"arbitrary_types_allowed": True}

    def save(self):
        data = self.model_dump()
        with open(self._config_file, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "AppSettings":
        cfg_file = CONFIG_DIR / "settings.json"
        if cfg_file.exists():
            try:
                with open(cfg_file) as f:
                    data = json.load(f)
                return cls(**data)
            except Exception:
                pass
        return cls()


# Global settings instance
settings = AppSettings.load()
