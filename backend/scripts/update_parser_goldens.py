from __future__ import annotations

import asyncio
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


FIXTURE_NAMES = (
    "dipirona_sanofi_medley_solucao_oral",
    "amoxicilina_cimed_suspensao_oral",
    "nesina_met_cosmed_comprimido_revestido",
)


async def main() -> None:
    from app.modules.rag.parsers.pdf_parser import BulaParser

    fixture_root = Path("tests/fixtures/rag")
    parser = BulaParser()

    for fixture_name in FIXTURE_NAMES:
        pdf_path = fixture_root / "bulas" / f"{fixture_name}.pdf"
        reference_path = fixture_root / "references" / f"{fixture_name}.md"
        parse_result = await parser.parse(
            pdf_bytes=pdf_path.read_bytes(),
            filename=pdf_path.name,
        )

        if not parse_result.success:
            raise RuntimeError(
                f"Parser failed for {pdf_path.name}: {parse_result.error}"
            )

        reference_path.write_text(parse_result.markdown + "\n", encoding="utf-8")
        print(
            f"Updated {reference_path} "
            f"({len(parse_result.markdown)} chars, "
            f"{len(parse_result.sections)} sections)"
        )


if __name__ == "__main__":
    asyncio.run(main())
