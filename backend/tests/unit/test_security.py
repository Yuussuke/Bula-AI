import pytest
from app.modules.auth.security import PasswordHasher, PASSWORD_HASHER


class TestPasswordHasher:
    """Tests for the pwdlib-based password hashing with Argon2id."""

    def test_password_hasher_singleton(self):
        """Test that PASSWORD_HASHER is a properly configured PasswordHasher instance."""
        assert isinstance(PASSWORD_HASHER, PasswordHasher)

    def test_hashing_returns_argon2id(self):
        """Test that hashing produces an Argon2id hash string."""
        password = "test_password_123"
        hashed = PASSWORD_HASHER.get_password_hash(password)

        # Check format: $argon2id$v=19$m=...,t=...,p=...$salt$hash
        assert hashed.startswith("$argon2id$v=19$")
        assert "m=" in hashed and "t=" in hashed and "p=" in hashed

    def test_verify_correct_password(self):
        """Test that correct password verifies successfully."""
        password = "my_secure_password"
        hashed = PASSWORD_HASHER.get_password_hash(password)

        assert PASSWORD_HASHER.verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test that incorrect password is rejected."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = PASSWORD_HASHER.get_password_hash(password)

        assert PASSWORD_HASHER.verify_password(wrong_password, hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes (due to random salts)."""
        password = "same_password"
        hash1 = PASSWORD_HASHER.get_password_hash(password)
        hash2 = PASSWORD_HASHER.get_password_hash(password)

        # Same password should produce different hashes due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert PASSWORD_HASHER.verify_password(password, hash1) is True
        assert PASSWORD_HASHER.verify_password(password, hash2) is True

    def test_hash_contains_parameters(self):
        """Test that hash contains Argon2id parameters."""
        password = "test"
        hashed = PASSWORD_HASHER.get_password_hash(password)

        # OWASP recommended parameters should be present
        # m=65536 (64MB), t=3, p=4
        assert "m=65536" in hashed
        assert "t=3" in hashed
        assert "p=4" in hashed
