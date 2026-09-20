from unittest.mock import AsyncMock

import pytest

from scripts import backfill_chunk_meta as script
from app.modules.rag.backfill_service import ChunkBackfillResult, ChunkBackfillError


def test_arguments_reject_bad_uuid_and_unbounded_page_size() -> None:
    for arguments in (
        ["--bula-id", "invalid"],
        ["--batch-size", "0"],
        ["--batch-size", "1001"],
    ):
        with pytest.raises(SystemExit):
            script.parse_arguments(arguments)


@pytest.mark.anyio
async def test_cli_dry_run_reports_validated_counts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = AsyncMock(return_value=ChunkBackfillResult(2, 20, True))
    monkeypatch.setattr(script, "run_backfill", runner)
    assert await script.async_main(["--dry-run"]) == 0
    assert runner.call_args.args[0].is_dry_run is True
    output = capsys.readouterr().out
    assert "dry-run" in output
    assert "20" in output


@pytest.mark.anyio
async def test_cli_failure_does_not_expose_exception_payload(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        script,
        "run_backfill",
        AsyncMock(side_effect=ChunkBackfillError("secret source text")),
    )
    assert await script.async_main([]) == 1
    output = capsys.readouterr().out
    assert "Backfill failed" in output
    assert "secret source text" not in output
