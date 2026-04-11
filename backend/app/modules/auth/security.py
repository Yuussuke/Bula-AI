# JWT utilities and password hashing logic.
from passlib.context import CryptContext

class PasswordHasher:
    # Use a stable scheme that avoids bcrypt backend incompatibilities in container builds.
    def __init__(self) -> None:
        self.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    def get_password_hash(self, password: str) -> str:
        """
        Hashes a plain text password for secure database storage.
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifies if a plain text password matches the hashed password from the database.
        """
        return self.pwd_context.verify(plain_password, hashed_password)


PASSWORD_HASHER = PasswordHasher()