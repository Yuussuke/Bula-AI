import pytest
import jwt

from app.modules.auth.security import PasswordHasher 
from app.modules.auth.service import TokenService
from app.core.config import SecuritySettings
from datetime import timedelta

hasher = PasswordHasher()

class TestPasswordHasher:
    """Tests for the pwdlib-based password hashing with Argon2id."""

    def test_hashing_returns_argon2id(self):
        """Test that hashing produces an Argon2id hash string."""
        password = "test_password_123"
        hashed = hasher.get_password_hash(password)

        assert hashed.startswith("$argon2id$")

    def test_verify_correct_password(self):
        """Test that correct password verifies successfully."""
        password = "my_secure_password"
        hashed = hasher.get_password_hash(password)

        assert hasher.verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test that incorrect password is rejected."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = hasher.get_password_hash(password)

        assert hasher.verify_password(wrong_password, hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password = "same_password"
        hash1 = hasher.get_password_hash(password)
        hash2 = hasher.get_password_hash(password)

        assert hash1 != hash2
        assert hasher.verify_password(password, hash1) is True
        assert hasher.verify_password(password, hash2) is True


class TestJWTToken:
    """Tests for JWT Token generation and validation."""

    def test_jwt_token_round_trip(self):
        """Test that a token can be created and then decoded to retrieve the original subject."""
        token_service = TokenService(
            secret_key="chave_super_secreta_de_teste_123456",
            algorithm="HS256",
            access_token_expire_minutes=30
        )
        
        user_id = "42"
        token = token_service.create_access_token(data={"sub": str(user_id)})
        
        assert isinstance(token, str)
        assert len(token) > 20 
        
        decoded_subject = token_service.decode_subject(token)
        assert decoded_subject == user_id
    
    def test_jwt_token_invalid_signature_raises_error(self):

        service_a = TokenService(secret_key="supersecretkey_for_testing_A_1234567890", algorithm="HS256", access_token_expire_minutes=30)
        service_b = TokenService(secret_key="supersecretkey_for_testing_B_1234567890", algorithm="HS256", access_token_expire_minutes=30)
        
        token = service_a.create_access_token(data={"sub": "42"})
        
        with pytest.raises(jwt.InvalidSignatureError):
            service_b.decode_subject(token)

    def test_jwt_token_expired_raises_error(self):
        token_service = TokenService(
            secret_key="supersecretkey_for_testing_1234567890", 
            algorithm="HS256", 
            access_token_expire_minutes=30
        )
        
        token = token_service.create_access_token(
            data={"sub": "42"},
            expires_delta=timedelta(seconds=-1)
        )
        
        with pytest.raises(jwt.ExpiredSignatureError):
            token_service.decode_subject(token)