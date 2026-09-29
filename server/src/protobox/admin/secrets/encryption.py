"""AES-256 encryption for secrets management."""

import base64
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger

from ..config import settings


class SecretEncryption:
    """AES-256 encryption with secure key derivation for secrets."""

    def __init__(self):
        """Initialize encryption with master key.

        Args:
            master_key: Master key for encryption (should be from environment)
        """
        master_key = settings._secret_encryption_key
        if not master_key or len(master_key.strip()) == 0:
            raise ValueError("Master key cannot be empty")

        self.master_key = master_key.encode("utf-8")
        self._validate_master_key()

    def _validate_master_key(self) -> None:
        """Validate master key meets security requirements."""
        if len(self.master_key) < 32:
            raise ValueError("MCP_SECRET_KEY must be at least 32 characters")

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master key using PBKDF2.

        Args:
            salt: Random salt for key derivation

        Returns:
            32-byte derived key for AES-256
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            iterations=100000,  # High iteration count for security
            backend=default_backend(),
        )
        return kdf.derive(self.master_key)

    async def encrypt_secret(self, value: str) -> dict[str, str]:
        """Encrypt a secret value and return all encryption components.

        This is a wrapper method for compatibility with SecretService.

        Args:
            value: Plain text secret value to encrypt

        Returns:
            Dictionary containing encrypted_value, salt, iv, and tag

        Raises:
            ValueError: If value is empty
            Exception: If encryption fails
        """
        return self.encrypt(value)

    def encrypt(self, value: str, salt: bytes = None) -> dict[str, str]:
        """Encrypt a secret value using AES-256-GCM.

        Args:
            value: Plain text secret value to encrypt
            salt: Optional salt (generated if not provided)

        Returns:
            Dictionary containing encrypted data components

        Raises:
            ValueError: If value is empty
            Exception: If encryption fails
        """
        if not value or len(value.strip()) == 0:
            raise ValueError("Cannot encrypt empty value")

        try:
            # Generate salt if not provided
            if salt is None:
                salt = os.urandom(16)  # 128-bit salt

            # Derive key from master key and salt
            key = self._derive_key(salt)

            # Generate random IV for GCM mode
            iv = os.urandom(12)  # 96-bit IV for GCM

            # Create cipher and encrypt
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            # Encrypt the value
            ciphertext = encryptor.update(value.encode("utf-8")) + encryptor.finalize()

            # Return all components needed for decryption
            return {
                "encrypted_value": base64.b64encode(ciphertext).decode("utf-8"),
                "salt": base64.b64encode(salt).decode("utf-8"),
                "iv": base64.b64encode(iv).decode("utf-8"),
                "tag": base64.b64encode(encryptor.tag).decode("utf-8"),
                "algorithm": "AES-256-GCM",
            }

        except Exception as e:
            logger.error(f"Failed to encrypt secret: {e}")
            raise Exception(f"Encryption failed: {str(e)}")

    async def decrypt_secret(self, encrypted_data: dict[str, str]) -> str:
        """Decrypt a secret value given all encryption components.

        This is a wrapper method for compatibility with SecretService.

        Args:
            encrypted_data: Dictionary containing encrypted_value, salt, iv, and tag

        Returns:
            Decrypted plain text value

        Raises:
            Exception: If decryption fails
        """
        return self.decrypt(encrypted_data)

    def decrypt(self, encrypted_data: dict[str, str]) -> str:
        """Decrypt a secret value.

        Args:
            encrypted_data: Dictionary containing encrypted components

        Returns:
            Decrypted plain text value

        Raises:
            ValueError: If encrypted_data is invalid
            Exception: If decryption fails
        """
        required_fields = ["encrypted_value", "salt", "iv", "tag"]
        missing_fields = [field for field in required_fields if field not in encrypted_data]

        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        try:
            # Decode base64 components
            ciphertext = base64.b64decode(encrypted_data["encrypted_value"])
            salt = base64.b64decode(encrypted_data["salt"])
            iv = base64.b64decode(encrypted_data["iv"])
            tag = base64.b64decode(encrypted_data["tag"])

            # Derive key from master key and salt
            key = self._derive_key(salt)

            # Create cipher for decryption
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()

            # Decrypt and return plain text
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext.decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to decrypt secret: {e}")
            raise Exception(f"Decryption failed: {str(e)}")

    def rotate_encryption(self, encrypted_data: dict[str, str]) -> dict[str, str]:
        """Re-encrypt data with new salt (for key rotation).

        Args:
            encrypted_data: Existing encrypted data

        Returns:
            New encrypted data with different salt
        """
        try:
            # Decrypt with old data
            plaintext = self.decrypt(encrypted_data)

            # Re-encrypt with new salt
            return self.encrypt(plaintext)

        except Exception as e:
            logger.error(f"Failed to rotate encryption: {e}")
            raise Exception(f"Encryption rotation failed: {str(e)}")

    @staticmethod
    def generate_master_key() -> str:
        """Generate a secure master key for development/testing.

        Returns:
            Base64-encoded random master key

        Note:
            This should only be used for development. Production keys
            should be generated using a proper key management system.
        """
        return base64.b64encode(os.urandom(32)).decode("utf-8")
