"""Source-backed conversion regression without ingestion or provider calls."""

from __future__ import annotations

import hashlib
import socket
from unittest.mock import patch

import pymupdf
import pytest

from app.modules.rag.parsers.pdf_parser import BulaParser, PARSER_VERSION


@pytest.mark.anyio
async def test_native_parser_keeps_later_presentation_after_legal_block() -> None:
    with pymupdf.open() as document:
        for text in (
            "COMPOSICAO\nSolucao oral: 1 mg/mL.\n"
            "3. QUANDO NAO DEVO USAR ESTE MEDICAMENTO?\n"
            "Nao utilize em caso de alergia.\n"
            "DIZERES LEGAIS\nRegistro MS 1.1111.1111",
            "SPRAY\nCOMPOSICAO\nSolucao spray: 2 mg/mL.\n"
            "3. QUANDO NAO DEVO USAR ESTE MEDICAMENTO?\n"
            "O spray e contraindicado para menores de 2 anos de idade.\n"
            "DIZERES LEGAIS\nRegistro MS 1.2222.2222",
        ):
            page = document.new_page()
            body, legal_text = text.split("DIZERES LEGAIS\n", maxsplit=1)
            page.insert_text((72, 72), body, fontsize=11)
            page.insert_text((72, 230), "DIZERES LEGAIS", fontsize=14, fontname="hebo")
            page.insert_text((72, 255), legal_text, fontsize=11)
        source = document.tobytes()
    source_hash = hashlib.sha256(source).hexdigest()

    with patch.object(
        socket.socket, "connect", side_effect=AssertionError("Network prohibited")
    ):
        result = await BulaParser().parse(source, "multiple-presentations.pdf")

    assert result.success, result.error
    assert result.parser_version == PARSER_VERSION
    assert "Solucao oral: 1 mg/mL." in result.markdown
    assert "Solucao spray: 2 mg/mL." in result.markdown
    assert (
        "O spray e contraindicado para menores de 2 anos de idade." in result.markdown
    )
    assert "Registro MS 1.1111.1111" in result.markdown
    assert "Registro MS 1.2222.2222" not in result.markdown
    assert hashlib.sha256(source).hexdigest() == source_hash
