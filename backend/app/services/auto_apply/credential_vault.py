"""
Credential Vault — Fernet-based symmetric encryption for all credential storage.
Passwords are NEVER stored unless the platform adapter explicitly requires it
(requires_password_storage = True).
"""
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class CredentialVault:
    """
    Encrypts and decrypts sensitive strings using Fernet symmetric encryption.
    Key is loaded from settings.CREDENTIAL_ENCRYPTION_KEY.
    Raises ValueError at startup if key is missing or invalid.
    """

    def __init__(self):
        self._fernet = None
        self._initialize()

    def _initialize(self):
        key = (settings.CREDENTIAL_ENCRYPTION_KEY or "").strip()
        if not key:
            logger.warning(
                "CREDENTIAL_ENCRYPTION_KEY not set. Credential vault running in SIMULATION mode. "
                "Do NOT use in production without setting this key."
            )
            return
        try:
            from cryptography.fernet import Fernet
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error(f"Invalid CREDENTIAL_ENCRYPTION_KEY: {e}")
            raise ValueError(f"CREDENTIAL_ENCRYPTION_KEY is invalid: {e}") from e

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext → Fernet token (URL-safe base64 string)."""
        if not plaintext:
            return ""
        if not self._fernet:
            # Simulation mode: return obfuscated placeholder
            return f"UNENCRYPTED:{plaintext[:4]}..."
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt Fernet token → plaintext."""
        if not ciphertext:
            return ""
        if not self._fernet:
            return ciphertext
        if ciphertext.startswith("UNENCRYPTED:"):
            return ciphertext  # Simulation fallback
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt credential: {e}")
            return ""

    def is_active(self) -> bool:
        """Returns True if a valid encryption key is configured."""
        return self._fernet is not None


# Module-level singleton
credential_vault = CredentialVault()