"""Read-only regressions for portable publication verification."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from verify import PublicationVerifier, read_json, source_path


class PublicationVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[4]
        self.inventory = read_json(Path(__file__).parent / "publication.json")

    def test_effective_collection_and_audit_membership_are_preserved(self) -> None:
        counts = PublicationVerifier(self.root, self.inventory).verify()
        self.assertEqual(counts["records"], 1000)
        self.assertEqual(counts["positive"], 800)
        self.assertEqual(counts["negative"], 200)
        self.assertEqual(counts["pdfs"], 100)

    def test_changed_byte_identity_is_rejected(self) -> None:
        inventory = deepcopy(self.inventory)
        inventory["published_files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Changed published artifact"):
            PublicationVerifier(self.root, inventory).verify()

    def test_changed_effective_collection_is_rejected(self) -> None:
        inventory = deepcopy(self.inventory)
        inventory["effective_records_fingerprint_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Effective collection fingerprint"):
            PublicationVerifier(self.root, inventory).verify()

    def test_sources_cannot_escape_declared_root(self) -> None:
        with self.assertRaisesRegex(ValueError, "escapes the repository"):
            source_path(self.root, "../foreign-input.json")


if __name__ == "__main__":
    unittest.main()
