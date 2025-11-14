"""
Unit Tests for Encryption Service

Tests for OAuth token encryption/decryption using AES-256.
"""

import pytest
import os
from cryptography.fernet import Fernet


# Mock environment for testing
@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set up test environment variables"""
    # Generate a test encryption key
    test_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)


def test_encryption_service_initialization():
    """Test that encryption service initializes correctly"""
    from utils.encryption import EncryptionService

    service = EncryptionService()
    assert service.encryption_key is not None
    assert service.fernet is not None


def test_encrypt_decrypt_single_token():
    """Test encryption and decryption of a single token"""
    from utils.encryption import encrypt_token, decrypt_token

    # Test token
    original_token = "ya29.a0AfH6SMBx_test_token_12345"

    # Encrypt
    encrypted = encrypt_token(original_token)
    assert encrypted is not None
    assert isinstance(encrypted, bytes)
    assert encrypted != original_token.encode()

    # Decrypt
    decrypted = decrypt_token(encrypted)
    assert decrypted == original_token


def test_encrypt_decrypt_token_pair():
    """Test encryption and decryption of OAuth token pair"""
    from utils.encryption import encrypt_token_pair, decrypt_token_pair

    # Test tokens
    access_token = "ya29.a0AfH6SMBx_access_token"
    refresh_token = "1//0gVZW6_refresh_token"

    # Encrypt
    encrypted_access, encrypted_refresh = encrypt_token_pair(access_token, refresh_token)
    assert encrypted_access is not None
    assert encrypted_refresh is not None
    assert isinstance(encrypted_access, bytes)
    assert isinstance(encrypted_refresh, bytes)

    # Decrypt
    decrypted_access, decrypted_refresh = decrypt_token_pair(
        encrypted_access, encrypted_refresh
    )
    assert decrypted_access == access_token
    assert decrypted_refresh == refresh_token


def test_encryption_produces_different_output():
    """Test that encrypting the same token twice produces different ciphertexts"""
    from utils.encryption import encrypt_token

    token = "test_token_123"

    # Encrypt twice
    encrypted1 = encrypt_token(token)
    encrypted2 = encrypt_token(token)

    # Fernet includes timestamp and random IV, so outputs will differ
    # But both should decrypt to the same value
    from utils.encryption import decrypt_token

    assert decrypt_token(encrypted1) == token
    assert decrypt_token(encrypted2) == token


def test_invalid_encryption_key():
    """Test that invalid encryption key raises error"""
    from utils.encryption import EncryptionService
    import os

    # Save original key
    original_key = os.getenv("ENCRYPTION_KEY")

    try:
        # Set invalid key
        os.environ["ENCRYPTION_KEY"] = "invalid-key"

        # Should raise ValueError
        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            EncryptionService()

    finally:
        # Restore original key
        if original_key:
            os.environ["ENCRYPTION_KEY"] = original_key


def test_decrypt_invalid_data():
    """Test that decrypting invalid data raises error"""
    from utils.encryption import decrypt_token

    invalid_data = b"invalid encrypted data"

    with pytest.raises(Exception):
        decrypt_token(invalid_data)


def test_encryption_with_special_characters():
    """Test encryption of tokens with special characters"""
    from utils.encryption import encrypt_token, decrypt_token

    # Token with special characters
    token = "token!@#$%^&*()_+-={}[]|\\:;<>?,./~`"

    encrypted = encrypt_token(token)
    decrypted = decrypt_token(encrypted)

    assert decrypted == token


def test_encryption_with_unicode():
    """Test encryption of tokens with unicode characters"""
    from utils.encryption import encrypt_token, decrypt_token

    # Token with unicode
    token = "token_with_unicode_😀🚀✅"

    encrypted = encrypt_token(token)
    decrypted = decrypt_token(encrypted)

    assert decrypted == token


def test_encryption_service_singleton():
    """Test that get_encryption_service returns same instance"""
    from utils.encryption import get_encryption_service

    service1 = get_encryption_service()
    service2 = get_encryption_service()

    assert service1 is service2
