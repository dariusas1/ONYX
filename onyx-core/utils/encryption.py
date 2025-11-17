"""
Encryption Utilities for OAuth Token Storage

This module provides AES-256 encryption/decryption for sensitive data like OAuth tokens.
Uses Fernet symmetric encryption from the cryptography library.
"""

import os
import base64
from typing import Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""

    def __init__(self):
        """Initialize encryption service with key from environment"""
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        if not self.encryption_key:
            logger.warning(
                "ENCRYPTION_KEY not set. Token encryption will fail. "
                "Generate one with: openssl rand -hex 32"
            )
            raise ValueError("ENCRYPTION_KEY environment variable not set")

        # Derive Fernet key from hex string
        self.fernet = self._initialize_fernet()

    def _initialize_fernet(self) -> Fernet:
        """Initialize Fernet cipher from encryption key"""
        try:
            # Convert hex string to bytes
            key_bytes = bytes.fromhex(self.encryption_key)

            # Derive a Fernet-compatible key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"onyx-encryption-salt",  # Static salt for key derivation
                iterations=100000,
            )
            derived_key = kdf.derive(key_bytes)

            # Encode as base64 for Fernet
            fernet_key = base64.urlsafe_b64encode(derived_key)

            return Fernet(fernet_key)

        except ValueError as e:
            logger.error(f"Invalid ENCRYPTION_KEY format: {e}")
            raise ValueError(
                "ENCRYPTION_KEY must be a 64-character hex string. "
                "Generate one with: openssl rand -hex 32"
            )

    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt a plaintext string

        Args:
            plaintext: The string to encrypt

        Returns:
            Encrypted bytes

        Raises:
            Exception: If encryption fails
        """
        try:
            encrypted = self.fernet.encrypt(plaintext.encode("utf-8"))
            logger.debug("Successfully encrypted data")
            return encrypted
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Decrypt encrypted bytes to plaintext string

        Args:
            encrypted_data: The encrypted bytes

        Returns:
            Decrypted plaintext string

        Raises:
            Exception: If decryption fails
        """
        try:
            decrypted = self.fernet.decrypt(encrypted_data)
            logger.debug("Successfully decrypted data")
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_token_pair(
        self, access_token: str, refresh_token: str
    ) -> Tuple[bytes, bytes]:
        """
        Encrypt an OAuth token pair (access + refresh)

        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token

        Returns:
            Tuple of (encrypted_access_token, encrypted_refresh_token)
        """
        encrypted_access = self.encrypt(access_token)
        encrypted_refresh = self.encrypt(refresh_token)
        logger.info("Encrypted OAuth token pair")
        return encrypted_access, encrypted_refresh

    def decrypt_token_pair(
        self, encrypted_access: bytes, encrypted_refresh: bytes
    ) -> Tuple[str, str]:
        """
        Decrypt an OAuth token pair

        Args:
            encrypted_access: Encrypted access token
            encrypted_refresh: Encrypted refresh token

        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = self.decrypt(encrypted_access)
        refresh_token = self.decrypt(encrypted_refresh)
        logger.info("Decrypted OAuth token pair (tokens redacted in logs)")
        return access_token, refresh_token


# Global encryption service instance
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """Get or create encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Convenience functions
def encrypt_token(token: str) -> bytes:
    """Encrypt a single token"""
    service = get_encryption_service()
    return service.encrypt(token)


def decrypt_token(encrypted_token: bytes) -> str:
    """Decrypt a single token"""
    service = get_encryption_service()
    return service.decrypt(encrypted_token)


def encrypt_token_pair(access_token: str, refresh_token: str) -> Tuple[bytes, bytes]:
    """Encrypt an OAuth token pair"""
    service = get_encryption_service()
    return service.encrypt_token_pair(access_token, refresh_token)


def decrypt_token_pair(
    encrypted_access: bytes, encrypted_refresh: bytes
) -> Tuple[str, str]:
    """Decrypt an OAuth token pair"""
    service = get_encryption_service()
    return service.decrypt_token_pair(encrypted_access, encrypted_refresh)
