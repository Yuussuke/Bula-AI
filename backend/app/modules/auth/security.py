# JWT utilities and password hashing logic.
# Using pwdlib with Argon2id per OWASP Password Storage Cheat Sheet recommendations
# https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
from pwdlib import PasswordHash


class PasswordHasher:
    """
    Secure password hasher using pwdlib with Argon2id.

    PasswordHash.recommended() automatically configures Argon2id with
    OWASP-recommended parameters (memory, iterations, parallelism).

    Argon2id is the winner of the Password Hashing Competition (PHC) and
    provides resistance against both GPU cracking attacks and side-channel attacks.
    """

    def __init__(self) -> None:
        # Use the recommended configuration which defaults to Argon2id
        self._hasher = PasswordHash.recommended()

    def get_password_hash(self, password: str) -> str:
        """
        Hashes a plain text password for secure database storage.

        Uses Argon2id with automatically generated random salt.
        The resulting hash string contains all parameters needed for verification.

        Args:
            password: Plain text password to hash

        Returns:
            Argon2id hash string (includes algorithm, salt, and parameters)
        """
        return self._hasher.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verifies if a plain text password matches the hashed password from the database.

        Automatically detects the hash algorithm (supports migration from other schemes).

        Args:
            plain_password: Plain text password to verify
            hashed_password: Stored hash from database

        Returns:
            True if password matches, False otherwise
        """
        return self._hasher.verify(plain_password, hashed_password)
