#!/usr/bin/env python3
"""
Docker smoke test for Argon2id password hashing.
This script runs inside the Docker container to verify that:
1. pwdlib is installed correctly
2. Argon2id hashing works
3. Verification works
4. The C bindings for argon2-cffi are working
"""

import sys
import time

# Add /app to Python path for imports
sys.path.insert(0, "/app")


def test_import():
    """Test that pwdlib and argon2 are importable."""
    print("🔧 Testing imports...")
    try:
        from pwdlib import PasswordHash  # noqa: F401
        import argon2  # noqa: F401

        print("   ✅ pwdlib imported successfully")
        print("   ✅ argon2-cffi imported successfully")
        return True
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False


def test_hashing():
    """Test Argon2id hashing and verification."""
    print("\n🔐 Testing Argon2id hashing...")
    from pwdlib import PasswordHash

    hasher = PasswordHash.recommended()
    password = "my_secure_password_123"

    # Test hashing
    start = time.time()
    hashed = hasher.hash(password)
    hash_time = time.time() - start

    print(f"   Hash time: {hash_time:.3f}s")
    print(f"   Hash prefix: {hashed[:50]}...")

    # Verify algorithm
    parts = hashed.split("$")
    if len(parts) >= 2 and parts[1] == "argon2id":
        print("   ✅ Algorithm is Argon2id")
    else:
        print(
            f"   ❌ Unexpected algorithm: {parts[1] if len(parts) >= 2 else 'unknown'}"
        )
        return False

    # Test verification
    start = time.time()
    is_valid = hasher.verify(password, hashed)
    verify_time = time.time() - start

    print(f"   Verify time: {verify_time:.3f}s")

    if is_valid:
        print("   ✅ Password verification successful")
    else:
        print("   ❌ Password verification failed")
        return False

    # Test rejection of wrong password
    is_invalid = hasher.verify("wrong_password", hashed)
    if not is_invalid:
        print("   ✅ Wrong password correctly rejected")
    else:
        print("   ❌ Wrong password was accepted!")
        return False

    return True


def test_security_module():
    """Test the application's security module."""
    print("\n🔒 Testing application security module...")
    try:
        from app.modules.auth.security import PASSWORD_HASHER, PasswordHasher

        # Test singleton
        assert isinstance(PASSWORD_HASHER, PasswordHasher)
        print("   ✅ PASSWORD_HASHER singleton is correctly typed")

        # Test hash and verify
        password = "docker_test_pass"
        hashed = PASSWORD_HASHER.get_password_hash(password)

        assert PASSWORD_HASHER.verify_password(password, hashed)
        print("   ✅ PASSWORD_HASHER.verify_password works")

        assert not PASSWORD_HASHER.verify_password("wrong", hashed)
        print("   ✅ PASSWORD_HASHER rejects wrong passwords")

        return True
    except Exception as e:
        print(f"   ❌ Security module test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("🔥 Docker Smoke Test: Argon2id Password Hashing")
    print("=" * 60)

    tests = [
        test_import,
        test_hashing,
        test_security_module,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n   ❌ Test crashed: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 60)
    if all(results):
        print("✅ All smoke tests passed!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some smoke tests failed!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
