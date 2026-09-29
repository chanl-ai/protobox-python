"""Tests for secret encryption."""

import base64
import os
from unittest.mock import patch

import pytest

from protobox.admin.secrets.encryption import SecretEncryption


class TestSecretEncryption:
    """Test cases for secret encryption/decryption."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_master_key = "test_master_key_for_encryption_testing_123"
        self.encryption = SecretEncryption(self.test_master_key)
        self.test_secret = "my_super_secret_api_key_12345"

    def test_encrypt_secret(self):
        """Test secret encryption."""
        encrypted_data = self.encryption.encrypt(self.test_secret)

        # Check all required fields are present
        required_fields = ["encrypted_value", "salt", "iv", "tag", "algorithm"]
        for field in required_fields:
            assert field in encrypted_data
            assert encrypted_data[field] is not None
            assert len(encrypted_data[field]) > 0

        # Check algorithm is correct
        assert encrypted_data["algorithm"] == "AES-256-GCM"

        # Check values are properly base64 encoded
        for field in ["encrypted_value", "salt", "iv", "tag"]:
            # Should not raise exception
            base64.b64decode(encrypted_data[field])

    def test_decrypt_secret(self):
        """Test secret decryption."""
        # First encrypt
        encrypted_data = self.encryption.encrypt(self.test_secret)

        # Then decrypt
        decrypted_value = self.encryption.decrypt(encrypted_data)

        # Should match original
        assert decrypted_value == self.test_secret

    def test_encrypt_decrypt_roundtrip(self):
        """Test full encrypt-decrypt roundtrip with various values."""
        test_values = [
            "simple_secret",
            "secret with spaces and symbols !@#$%",
            "very_long_secret_" + "x" * 1000,
            "unicode_secret_ñ_éテスト",
            "",  # This should raise an error
        ]

        for value in test_values[:-1]:  # Skip empty string
            encrypted = self.encryption.encrypt(value)
            decrypted = self.encryption.decrypt(encrypted)
            assert decrypted == value

        # Test empty string raises error
        with pytest.raises(ValueError, match="Cannot encrypt empty value"):
            self.encryption.encrypt("")

    def test_encryption_key_derivation(self):
        """Test encryption key derivation produces different results with different salts."""
        # Encrypt same value twice - should produce different results due to different salts
        encrypted1 = self.encryption.encrypt(self.test_secret)
        encrypted2 = self.encryption.encrypt(self.test_secret)

        # Encrypted values should be different (different salts/IVs)
        assert encrypted1["encrypted_value"] != encrypted2["encrypted_value"]
        assert encrypted1["salt"] != encrypted2["salt"]
        assert encrypted1["iv"] != encrypted2["iv"]

        # But both should decrypt to same value
        assert self.encryption.decrypt(encrypted1) == self.test_secret
        assert self.encryption.decrypt(encrypted2) == self.test_secret

    def test_fixed_salt_encryption(self):
        """Test encryption with fixed salt produces consistent results."""
        fixed_salt = os.urandom(16)

        encrypted1 = self.encryption.encrypt(self.test_secret, salt=fixed_salt)
        encrypted2 = self.encryption.encrypt(self.test_secret, salt=fixed_salt)

        # With same salt, salt should be same but IV should be different
        assert encrypted1["salt"] == encrypted2["salt"]
        assert encrypted1["iv"] != encrypted2["iv"]  # IV should still be random

        # Both should decrypt correctly
        assert self.encryption.decrypt(encrypted1) == self.test_secret
        assert self.encryption.decrypt(encrypted2) == self.test_secret

    def test_decrypt_invalid_data(self):
        """Test decryption with invalid data."""
        # Missing fields
        with pytest.raises(ValueError, match="Missing required fields"):
            self.encryption.decrypt({"encrypted_value": "test"})

        # Invalid base64
        with pytest.raises(Exception, match="Decryption failed"):
            self.encryption.decrypt(
                {
                    "encrypted_value": "invalid_base64!",
                    "salt": "valid_base64",
                    "iv": "valid_base64",
                    "tag": "valid_base64",
                }
            )

    def test_master_key_validation(self):
        """Test master key validation."""
        # Empty master key should raise error
        with pytest.raises(ValueError, match="Master key cannot be empty"):
            SecretEncryption("")

        with pytest.raises(ValueError, match="Master key cannot be empty"):
            SecretEncryption("   ")

        # Short master key should log warning but work
        with patch("protobox.admin.secrets.encryption.logger") as mock_logger:
            SecretEncryption("short")
            mock_logger.warning.assert_called_with(
                "Master key is shorter than recommended (32+ characters)"
            )

    def test_rotation_encryption(self):
        """Test encryption rotation (re-encrypt with new salt)."""
        # Original encryption
        original_encrypted = self.encryption.encrypt(self.test_secret)

        # Rotate encryption
        rotated_encrypted = self.encryption.rotate_encryption(original_encrypted)

        # Should have different encrypted components
        assert rotated_encrypted["encrypted_value"] != original_encrypted["encrypted_value"]
        assert rotated_encrypted["salt"] != original_encrypted["salt"]
        assert rotated_encrypted["iv"] != original_encrypted["iv"]

        # But should decrypt to same value
        assert self.encryption.decrypt(rotated_encrypted) == self.test_secret
        assert self.encryption.decrypt(original_encrypted) == self.test_secret

    def test_generate_master_key(self):
        """Test master key generation."""
        generated_key = SecretEncryption.generate_master_key()

        # Should be a valid base64 string
        decoded = base64.b64decode(generated_key)

        # Should be 32 bytes (256 bits)
        assert len(decoded) == 32

        # Should be different each time
        key2 = SecretEncryption.generate_master_key()
        assert generated_key != key2

        # Should work as a master key
        encryption = SecretEncryption(generated_key)
        test_value = "test_secret"
        encrypted = encryption.encrypt(test_value)
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == test_value

    def test_different_master_keys_incompatible(self):
        """Test that different master keys cannot decrypt each other's data."""
        encryption1 = SecretEncryption("master_key_1")
        encryption2 = SecretEncryption("master_key_2")

        encrypted_data = encryption1.encrypt(self.test_secret)

        # encryption2 should not be able to decrypt data from encryption1
        with pytest.raises(Exception, match="Decryption failed"):
            encryption2.decrypt(encrypted_data)
