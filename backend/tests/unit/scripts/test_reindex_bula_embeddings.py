from uuid import UUID

import pytest

from app.scripts.reindex_bula_embeddings import parse_arguments


BULA_ID = "11111111-1111-1111-1111-111111111111"


def test_parse_reindex_arguments_supports_dry_run() -> None:
    arguments = parse_arguments(["--bula-id", BULA_ID, "--dry-run"])

    assert arguments.bula_id == UUID(BULA_ID)
    assert arguments.is_dry_run is True


def test_parse_reindex_arguments_rejects_invalid_bula_id() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(["--bula-id", "not-a-uuid"])
