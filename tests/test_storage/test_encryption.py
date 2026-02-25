"""Tests for encryption module."""

import pytest

from nyaynet.common.exceptions import EncryptionError
from nyaynet.storage.encryption import EncryptionManager


def test_encrypt_decrypt_roundtrip():
    key = EncryptionManager.generate_key()
    manager = EncryptionManager(key)

    plaintext = "Sensitive user data for evidence"
    ciphertext = manager.encrypt(plaintext)
    assert ciphertext != plaintext

    decrypted = manager.decrypt(ciphertext)
    assert decrypted == plaintext


def test_generate_key():
    key1 = EncryptionManager.generate_key()
    key2 = EncryptionManager.generate_key()
    assert key1 != key2
    assert len(key1) > 0


def test_invalid_key():
    with pytest.raises(EncryptionError):
        EncryptionManager("not-a-valid-key")


def test_empty_key():
    with pytest.raises(EncryptionError):
        EncryptionManager("")


def test_decrypt_with_wrong_key():
    key1 = EncryptionManager.generate_key()
    key2 = EncryptionManager.generate_key()

    manager1 = EncryptionManager(key1)
    manager2 = EncryptionManager(key2)

    ciphertext = manager1.encrypt("secret")
    with pytest.raises(EncryptionError):
        manager2.decrypt(ciphertext)
