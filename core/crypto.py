"""
Clarify — Key encryption using Fernet + random secure key
"""
import os
from pathlib import Path
from cryptography.fernet import Fernet
from config.settings import KEY_FILE


def _get_or_create_key() -> bytes:
    if KEY_FILE.exists():
        # Ensure permissions are secure even if created previously
        try:
            if (KEY_FILE.stat().st_mode & 0o777) != 0o600:
                KEY_FILE.chmod(0o600)
        except Exception:
            pass
        return KEY_FILE.read_bytes()
    
    # Generate a cryptographically secure random key
    key = Fernet.generate_key()
    
    # Create file with 0o600 permissions immediately to avoid race conditions
    fd = os.open(str(KEY_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
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
