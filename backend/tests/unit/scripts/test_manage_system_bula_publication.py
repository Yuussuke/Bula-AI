from uuid import UUID

import pytest

from app.scripts.manage_system_bula_publication import parse_arguments


BULA_ID = "11111111-1111-1111-1111-111111111111"


def test_parse_vet_arguments_records_actor_and_notes() -> None:
    arguments = parse_arguments(
        [
            "vet",
            "--bula-id",
            BULA_ID,
            "--actor-email",
            "reviewer@example.com",
            "--notes",
            "Checked against ANVISA.",
        ]
    )

    assert arguments.action == "vet"
    assert arguments.bula_id == UUID(BULA_ID)
    assert arguments.actor_email == "reviewer@example.com"
    assert arguments.notes == "Checked against ANVISA."


def test_publish_does_not_accept_review_notes() -> None:
    with pytest.raises(SystemExit):
        parse_arguments(
            [
                "publish",
                "--bula-id",
                BULA_ID,
                "--actor-email",
                "admin@example.com",
                "--notes",
                "unexpected",
            ]
        )
