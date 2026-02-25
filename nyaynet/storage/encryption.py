"""Fernet at-rest encryption for sensitive data."""

from cryptography.fernet import Fernet, InvalidToken

from nyaynet.common.exceptions import EncryptionError


class EncryptionManager:
    """Handles encryption and decryption of sensitive data using Fernet."""

    def __init__(self, key: str):
        if not key:
            raise EncryptionError("Encryption key is required")
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise EncryptionError(f"Invalid encryption key: {e}") from e

    def encrypt(self, data: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext."""
        try:
            return self._fernet.encrypt(data.encode("utf-8")).decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}") from e

    def decrypt(self, token: str) -> str:
        """Decrypt a Fernet token back to plaintext."""
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken as e:
            raise EncryptionError("Decryption failed: invalid token or key") from e
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}") from e

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key."""
        return Fernet.generate_key().decode("utf-8")
