"""
Clarify — Key encryption using Fernet + machine-derived key
"""
import os
import base64
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet
from config.settings import KEY_FILE


def _get_or_create_key() -> bytes:
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    # Derive from machine-id + fallback
    machine_id = ""
    for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        if os.path.exists(path):
            machine_id = open(path).read().strip()
            break
    if not machine_id:
        machine_id = str(os.getuid()) + os.uname().nodename
    raw = hashlib.sha256(machine_id.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    return key


_fernet = Fernet(_get_or_create_key())


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ciphertext  # already plain or corrupted
