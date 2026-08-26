#!/usr/bin/env python3
"""
ANVISA Bulario PDF Downloader
=============================
Downloads bula PDFs from https://consultas.anvisa.gov.br

This is part of the BulaIntelegence platform for RAG-based
pharmaceutical document analysis.

Usage:
    uv run python -m scripts.download_bulas
    uv run python -m scripts.download_bulas --limit 5
    uv run python -m scripts.download_bulas --proxy http://127.0.0.1:8080

Requirements:
    uv sync --dev
    uv run playwright install chromium
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import logging
import re
from pathlib import Path
from typing import cast
from urllib.parse import quote

from playwright.async_api import Page, async_playwright
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.modules.bulas.schemas import SystemBulaManifest, SystemBulaManifestEntry

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

MANIFEST_FILENAME = "manifest.json"
MINIMUM_EXISTING_PDF_SIZE_BYTES = 1024
PDF_MAGIC_BYTES = b"%PDF"


class AnvisaBulaRecord(BaseModel):
    razao_social: str = Field(alias="razaoSocial")
    patient_bula_id: str | None = Field(default=None, alias="idBulaPacienteProtegido")
    professional_bula_id: str | None = Field(
        default=None,
        alias="idBulaProfissionalProtegido",
    )
    updated_at: str | None = Field(default=None, alias="dataAtualizacao")
    published_at: str | None = Field(default=None, alias="data")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class AnvisaSearchResponse(BaseModel):
    content: list[AnvisaBulaRecord] = Field(default_factory=list)
    total_pages: int = Field(default=1, alias="totalPages", ge=1)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


@dataclass(frozen=True)
class DownloadArguments:
    output_directory: Path
    manifest_path: Path
    proxy: str | None
    is_headless: bool
    limit: int | None
    is_debug_enabled: bool


@dataclass(frozen=True)
class DownloadResult:
    manifest_entry: SystemBulaManifestEntry
    file_path: Path


# Download targets
# Each key is the drug name as it appears in ANVISA search (nomeProduto).
# Values are manufacturer candidates in priority order. The downloader tries
# each one and stops after the first valid PDF, so every drug gets at most one
# bula from the most influential available manufacturer.
TARGETS: dict[str, list[str]] = {
    "Amoxicilina": [
        "EMS",
        "Eurofarma",
        "Cimed",
        "Sandoz",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
        "Multilab",
    ],
    "Anlodipino": [
        "EMS",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Sandoz",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
        "Vitamedic",
    ],
    "Atenolol": [
        "EMS",
        "Eurofarma",
        "Cimed",
        "Medley",
    ],
    "Atorvastatina": [
        "EMS",
        "Eurofarma",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Sandoz",
        "Germed",
        "Legrand",
        "Geolab",
        "Multilab",
    ],
    "Captopril": [
        "EMS",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Germed",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
        "Vitamedic",
    ],
    "Diazepam": [
        "EMS",
        "Legrand",
        "Pharlab",
    ],
    "Diclofenaco": [
        "EMS",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Germed",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
        "Pharlab",
    ],
    "Dipirona sódica": [
        "EMS",
        "Sanofi Medley",
        "Sanofi",
        "Medley",
        "Germed",
        "Geolab",
        "Unither",
    ],
    "Enalapril": [
        "EMS",
        "Cimed",
        "Germed",
        "Legrand",
        "Geolab",
        "Multilab",
        "Vitamedic",
    ],
    "Fluoxetina": [
        "EMS",
        "Eurofarma",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Sandoz",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
        "Vitamedic",
        "Pharlab",
    ],
    "Glibenclamida": [
        "EMS",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
    ],
    "Gliclazida": [
        "EMS",
        "Cimed",
        "Germed",
        "Legrand",
        "Pharlab",
    ],
    "Hidroclorotiazida": [
        "EMS",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
    ],
    "Ibuprofeno": [
        "Eurofarma",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
        "Vitamedic",
        "Pharlab",
    ],
    "Loratadina": [
        "EMS",
        "Cimed",
        "Germed",
        "Prati-Donaduzzi",
        "Vitamedic",
    ],
    "Losartana": [
        "EMS",
        "Eurofarma",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Sandoz",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
        "Vitamedic",
        "Pharlab",
        "Zydus Nikkho",
    ],
    "Metformina": [
        "EMS",
        "Cimed",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
        "Vitamedic",
    ],
    "Metronidazol": [
        "Cimed",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
    ],
    "Nimesulida": [
        "EMS",
        "Eurofarma",
        "Cimed",
        "Prati-Donaduzzi",
    ],
    "Omeprazol": [
        "EMS",
        "Eurofarma",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Germed",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
        "Pharlab",
    ],
    "Paracetamol": [
        "EMS",
        "Eurofarma",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
    ],
    "Prednisona": [
        "EMS",
        "Sanofi Medley",
        "Medley",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
        "Multilab",
        "Vitamedic",
    ],
    "Propranolol": [
        "EMS",
    ],
    "Ranitidina": [
        "Eurofarma",
        "Geolab",
    ],
    "Salbutamol": [
        "Prati-Donaduzzi",
        "Geolab",
    ],
    "Sertralina": [
        "EMS",
        "Eurofarma",
        "Cimed",
        "Sanofi Medley",
        "Medley",
        "Germed",
        "Legrand",
        "Prati-Donaduzzi",
        "Geolab",
        "Multilab",
    ],
    "Simeticona": [
        "EMS",
        "Germed",
    ],
    "Sinvastatina": [
        "EMS",
        "Cimed",
        "Sandoz",
        "Germed",
        "Legrand",
        "Geolab",
        "Multilab",
        "Pharlab",
    ],
    "Sulfametoxazol + Trimetoprima": [
        "EMS",
        "Prati-Donaduzzi",
        "Vitamedic",
    ],
}

# Alternate drug names to try if primary search fails
# Key: primary drug name (must match TARGETS key)
# Value: list of alternate search terms to try
DRUG_ALIASES: dict[str, list[str]] = {
    "Anlodipino": ["Besilato de Anlodipino"],
    "Atorvastatina": ["Atorvastatina Cálcica"],
    "Enalapril": ["Enalapril Maleato", "Maleato de Enalapril"],
    "Losartana": ["Losartana Potássica"],
    "Dipirona sódica": ["Dipirona", "Dipirona Monoidratada"],
    "Fluoxetina": ["Cloridrato de Fluoxetina"],
    "Hidroclorotiazida": ["Hidroclorotiazida 25mg", "HCT"],
    "Metformina": ["Cloridrato de Metformina"],
    "Ranitidina": ["Cloridrato de Ranitidina"],
    "Salbutamol": ["Sulfato de Salbutamol"],
    "Sertralina": ["Cloridrato de Sertralina"],
    "Sulfametoxazol + Trimetoprima": [
        "Sulfametoxazol Trimetoprima",
        "Sulfametoxazol",
        "Trimetoprima",
    ],
}

# ANVISA API
BASE = "https://consultas.anvisa.gov.br"


def search_url(drug: str, page_num: int = 1, count: int = 100) -> str:
    """
    ANVISA bulario search endpoint.
    filter[nomeProduto] searches by product/active-ingredient name.
    """
    return (
        f"{BASE}/api/consulta/bulario"
        f"?count={count}"
        f"&filter%5BnomeProduto%5D={quote(drug)}"
        f"&page={page_num}"
    )


def pdf_url(bula_id: str) -> str:
    """
    PDF download endpoint.
    The Authorization= query param with empty value is the documented pattern
    for public (guest) access; the Authorization: Guest header is also sent.
    """
    return f"{BASE}/api/consulta/medicamentos/arquivo/bula/parecer/{bula_id}/?Authorization="


# Manufacturer matching
# Short name to substrings that appear in ANVISA razaoSocial (upper-cased).
# Order matters: more-specific entries should come before generic ones when
# a company could otherwise be caught by a shorter alias (e.g. Sanofi vs
# Sanofi Medley).
_ALIASES: dict[str, list[str]] = {
    "EMS": ["EMS S/A"],
    "Germed": ["GERMED FARMACEUTICA"],
    "Torrent": ["TORRENT"],
    "Organon": ["ORGANON", "ORGANON PHARMA"],
    "Pharlab": ["PHARLAB"],
    "Multilab": ["MULTILAB", "MULTI LAB"],
    "Sandoz": ["SANDOZ DO BRASIL"],
    "Vitamedic": ["VITAMEDIC"],
    # Sanofi Medley (former Medley, acquired by Sanofi ~2009)
    "Sanofi Medley": ["SANOFI MEDLEY FARMACEUTICA", "SANOFI-MEDLEY"],
    "Nova Química": [
        "NOVA QUIMICA",
        "NOVA QUÍMICA",
        "NOVAQUIMICA",
        "LABORATORIO NOVA QUIMICA",
    ],
    "Legrand": ["LEGRAND PHARMA"],
    "Zydus Nikkho": ["ZYDUS NIKKHO FARMACEUTICA"],
    "Prati-Donaduzzi": ["PRATI DONADUZZI", "PRATI-DONADUZZI"],
    "Unither": ["UNITHER"],
    "Neo Química": [
        "NEO QUIMICA",
        "NEO QUÍMICA",
        "NEOQUIMICA",
        "NEOQUÍMICA",
        "LABORATORIO NEO QUIMICA",
    ],
    # Plain Sanofi (Sanofi-Aventis) must NOT match "SANOFI MEDLEY".
    "Sanofi": [
        "SANOFI AVENTIS",
        "SANOFI-AVENTIS",
        "SANOFI LTDA",
        "SANOFI S/A",
        "SANOFI BRASIL",
    ],
    "Cimed": ["CIMED INDUSTRIA"],
    "Medley": ["MEDLEY"],  # Note: Most Medley products are now under Sanofi Medley
    "Eurofarma": ["EUROFARMA LABORATORIOS"],
    "Geolab": ["GEOLAB INDUSTRIA"],
}

# Fallback: if the specific aliases above don't match we try the raw name
_FALLBACK_ALIASES: dict[str, list[str]] = {
    "Sanofi": ["SANOFI"],  # catches anything with SANOFI in it if nothing else matched
    "Neo Química": ["NEO"],  # broader match for Neo Química
    "Cimed": ["CIMED"],
    "Medley": ["MEDLEY"],
    "Prati-Donaduzzi": ["PRATI"],
}


def matches_manufacturer(razao_social: str, target: str) -> bool:
    rs = razao_social.upper()
    for fragment in _ALIASES.get(target, [target.upper()]):
        if fragment in rs:
            return True
    return False


def matches_manufacturer_loose(razao_social: str, target: str) -> bool:
    """Fallback with broader matching (used only when strict matching returns nothing)."""
    rs = razao_social.upper()
    for fragment in _FALLBACK_ALIASES.get(target, [target.upper()]):
        if fragment in rs:
            return True
    return False


# Browser helpers

_FETCH_HEADERS = """{
    "Authorization": "Guest",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}"""


async def browser_json(page: Page, url: str) -> object | None:
    result = cast(
        object,
        await page.evaluate(
            f"""async (url) => {{
                try {{
                    const response = await fetch(url, {{
                        headers: {_FETCH_HEADERS},
                        credentials: "include",
                    }});
                    if (!response.ok) return {{ _http_error: response.status }};
                    return await response.json();
                }} catch (error) {{
                    return {{ _js_error: String(error) }};
                }}
            }}""",
            url,
        ),
    )

    if isinstance(result, dict):
        if "_http_error" in result:
            log.warning("ANVISA returned HTTP %s.", result["_http_error"])
            return None
        if "_js_error" in result:
            log.warning("Browser request failed: %s", result["_js_error"])
            return None

    return result


async def browser_pdf(page: Page, url: str) -> bytes | None:
    encoded_pdf = await page.evaluate(
        """async (url) => {
            try {
                const response = await fetch(url, {
                    headers: {
                        "Authorization": "Guest",
                        "Accept": "application/pdf, application/octet-stream, */*"
                    },
                    credentials: "include"
                });
                if (!response.ok) return null;
                const buffer = await response.arrayBuffer();
                const view = new Uint8Array(buffer);
                let binary = "";
                for (let index = 0; index < view.byteLength; index++) {
                    binary += String.fromCharCode(view[index]);
                }
                return btoa(binary);
            } catch (error) {
                return null;
            }
        }""",
        url,
    )
    if not isinstance(encoded_pdf, str) or not encoded_pdf:
        return None

    pdf_bytes = base64.b64decode(encoded_pdf)
    if not pdf_bytes.startswith(PDF_MAGIC_BYTES):
        return None
    return pdf_bytes


class AnvisaBulaDownloader:
    def __init__(
        self,
        *,
        page: Page,
        output_directory: Path,
        manifest_path: Path,
    ) -> None:
        self.page = page
        self.output_directory = output_directory
        self.manifest_path = manifest_path
        self.manifest_entries = self._load_existing_manifest_entries()

    async def download_targets(
        self,
        targets: Sequence[tuple[str, list[str]]],
    ) -> dict[str, DownloadResult | None]:
        results: dict[str, DownloadResult | None] = {}
        for drug_name, manufacturers in targets:
            result = await self.download_drug(
                drug_name=drug_name,
                manufacturers=manufacturers,
            )
            results[drug_name] = result
            if result is None:
                continue

            source_url = str(result.manifest_entry.source_url)
            self.manifest_entries[source_url] = result.manifest_entry
            self._write_manifest()

        return results

    async def download_drug(
        self,
        *,
        drug_name: str,
        manufacturers: list[str],
    ) -> DownloadResult | None:
        log.info("Searching ANVISA for %s.", drug_name)
        records = await self.fetch_all_results(drug_name=drug_name)
        if not records:
            return None

        for manufacturer_name in manufacturers:
            matching_records = self._find_manufacturer_records(
                records=records,
                manufacturer_name=manufacturer_name,
            )
            if not matching_records:
                log.warning(
                    "Manufacturer %s was not found for %s.",
                    manufacturer_name,
                    drug_name,
                )
                continue

            newest_record = max(
                matching_records,
                key=lambda record: record.updated_at or record.published_at or "",
            )
            download_candidates = (
                ("patient", newest_record.patient_bula_id),
                ("professional", newest_record.professional_bula_id),
            )
            for audience, protected_bula_id in download_candidates:
                if protected_bula_id is None:
                    continue

                source_url = pdf_url(protected_bula_id)
                filename = self._build_filename(
                    drug_name=drug_name,
                    manufacturer_name=manufacturer_name,
                )
                file_path = self.output_directory / filename
                existing_result = self._build_existing_file_result(
                    file_path=file_path,
                    drug_name=drug_name,
                    manufacturer=newest_record.razao_social,
                    source_url=source_url,
                )
                if existing_result is not None:
                    log.info("Using existing PDF %s.", filename)
                    return existing_result

                log.info(
                    "Downloading %s leaflet for %s from %s.",
                    audience,
                    drug_name,
                    newest_record.razao_social,
                )
                pdf_bytes = await browser_pdf(self.page, source_url)
                if pdf_bytes is None:
                    continue

                file_path.write_bytes(pdf_bytes)
                return self._build_download_result(
                    file_path=file_path,
                    pdf_bytes=pdf_bytes,
                    drug_name=drug_name,
                    manufacturer=newest_record.razao_social,
                    source_url=source_url,
                )

        log.error("No downloadable ANVISA leaflet was found for %s.", drug_name)
        return None

    async def fetch_all_results(self, *, drug_name: str) -> list[AnvisaBulaRecord]:
        queries = self._build_search_queries(drug_name=drug_name)

        for query in queries:
            records: list[AnvisaBulaRecord] = []
            page_number = 1
            while True:
                response_payload = await browser_json(
                    self.page,
                    search_url(query, page_num=page_number, count=100),
                )
                if response_payload is None:
                    break

                try:
                    response = AnvisaSearchResponse.model_validate(response_payload)
                except ValidationError:
                    log.warning(
                        "ANVISA returned an invalid search response for %s.",
                        query,
                    )
                    break

                records.extend(response.content)
                log.info(
                    "ANVISA query %s page %s/%s returned %s records.",
                    query,
                    page_number,
                    response.total_pages,
                    len(response.content),
                )
                if page_number >= response.total_pages:
                    break

                page_number += 1
                await asyncio.sleep(0.5)

            if records:
                return records

        log.warning("ANVISA returned no records for %s.", drug_name)
        return []

    def _build_search_queries(self, *, drug_name: str) -> list[str]:
        queries = [drug_name]
        first_word = drug_name.split()[0]
        if first_word.casefold() != drug_name.casefold():
            queries.append(first_word)
        queries.extend(DRUG_ALIASES.get(drug_name, []))
        return list(dict.fromkeys(queries))

    def _find_manufacturer_records(
        self,
        *,
        records: list[AnvisaBulaRecord],
        manufacturer_name: str,
    ) -> list[AnvisaBulaRecord]:
        strict_matches = [
            record
            for record in records
            if matches_manufacturer(record.razao_social, manufacturer_name)
        ]
        if strict_matches:
            return strict_matches

        return [
            record
            for record in records
            if matches_manufacturer_loose(record.razao_social, manufacturer_name)
        ]

    def _build_filename(self, *, drug_name: str, manufacturer_name: str) -> str:
        safe_drug_name = re.sub(r"[^\w-]", "_", drug_name)
        safe_manufacturer_name = re.sub(r"[^\w-]", "_", manufacturer_name)
        return f"{safe_drug_name}__{safe_manufacturer_name}.pdf"

    def _build_existing_file_result(
        self,
        *,
        file_path: Path,
        drug_name: str,
        manufacturer: str,
        source_url: str,
    ) -> DownloadResult | None:
        if not file_path.is_file():
            return None
        if file_path.stat().st_size <= MINIMUM_EXISTING_PDF_SIZE_BYTES:
            return None

        pdf_bytes = file_path.read_bytes()
        if not pdf_bytes.startswith(PDF_MAGIC_BYTES):
            return None

        return self._build_download_result(
            file_path=file_path,
            pdf_bytes=pdf_bytes,
            drug_name=drug_name,
            manufacturer=manufacturer,
            source_url=source_url,
        )

    def _build_download_result(
        self,
        *,
        file_path: Path,
        pdf_bytes: bytes,
        drug_name: str,
        manufacturer: str,
        source_url: str,
    ) -> DownloadResult:
        checksum = hashlib.sha256(pdf_bytes).hexdigest()
        manifest_entry = SystemBulaManifestEntry(
            drug_name=drug_name,
            manufacturer=manufacturer,
            source_url=source_url,
            filename=file_path.name,
            sha256_checksum=checksum,
            content_size_bytes=len(pdf_bytes),
        )
        return DownloadResult(
            manifest_entry=manifest_entry,
            file_path=file_path,
        )

    def _load_existing_manifest_entries(
        self,
    ) -> dict[str, SystemBulaManifestEntry]:
        if not self.manifest_path.is_file():
            return {}

        manifest = SystemBulaManifest.model_validate_json(
            self.manifest_path.read_text(encoding="utf-8")
        )
        return {str(document.source_url): document for document in manifest.documents}

    def _write_manifest(self) -> None:
        documents = sorted(
            self.manifest_entries.values(),
            key=lambda document: (
                document.drug_name.casefold(),
                document.manufacturer or "",
            ),
        )
        manifest = SystemBulaManifest(documents=documents)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            f"{manifest.model_dump_json(indent=2)}\n",
            encoding="utf-8",
            newline="\n",
        )


def positive_integer(value: str) -> int:
    parsed_value = int(value)
    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")
    return parsed_value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download public leaflet PDFs from ANVISA.",
    )
    parser.add_argument(
        "--proxy",
        help="Optional HTTP or SOCKS5 proxy URL.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="tmp/anvisa-bulas",
        help="Directory for PDFs and the generated manifest.",
    )
    parser.add_argument(
        "--manifest",
        help="Manifest path. Defaults to <output>/manifest.json.",
    )
    parser.add_argument(
        "--limit",
        type=positive_integer,
        help="Download only the first N configured medicines.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without a visible browser window.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose downloader logs.",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> DownloadArguments:
    parser = build_parser()
    parsed_arguments = parser.parse_args(argv)
    output_directory = Path(parsed_arguments.output)
    manifest_path = (
        Path(parsed_arguments.manifest)
        if parsed_arguments.manifest
        else output_directory / MANIFEST_FILENAME
    )
    return DownloadArguments(
        output_directory=output_directory,
        manifest_path=manifest_path,
        proxy=parsed_arguments.proxy,
        is_headless=parsed_arguments.headless,
        limit=parsed_arguments.limit,
        is_debug_enabled=parsed_arguments.debug,
    )


async def run_download(arguments: DownloadArguments) -> int:
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    selected_targets = list(TARGETS.items())
    if arguments.limit is not None:
        selected_targets = selected_targets[: arguments.limit]

    async with async_playwright() as playwright:
        launch_arguments: dict[str, object] = {
            "headless": arguments.is_headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        }
        browser = await playwright.chromium.launch(**launch_arguments)
        context_arguments: dict[str, object] = {
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "locale": "pt-BR",
            "viewport": {"width": 1280, "height": 900},
            "extra_http_headers": {"Accept-Language": "pt-BR,pt;q=0.9"},
        }
        if arguments.proxy is not None:
            context_arguments["proxy"] = {"server": arguments.proxy}

        context = await browser.new_context(**context_arguments)
        try:
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await context.new_page()
            log.info("Opening ANVISA to establish a browser session.")
            await page.goto(
                f"{BASE}/#/bulario",
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            await asyncio.sleep(4)

            page_content = await page.content()
            page_title = await page.title()
            is_blocked = (
                "Service Unavailable" in page_content
                or "Access Denied" in page_content
                or not page_title
            )
            if is_blocked:
                raise RuntimeError(
                    "ANVISA blocked the browser session. Try headed mode or a "
                    "Brazilian proxy."
                )

            downloader = AnvisaBulaDownloader(
                page=page,
                output_directory=arguments.output_directory,
                manifest_path=arguments.manifest_path,
            )
            results = await downloader.download_targets(selected_targets)
        finally:
            await browser.close()

    print_download_summary(
        results=results,
        output_directory=arguments.output_directory,
        manifest_path=arguments.manifest_path,
    )
    return 0 if all(result is not None for result in results.values()) else 1


def print_download_summary(
    *,
    results: dict[str, DownloadResult | None],
    output_directory: Path,
    manifest_path: Path,
) -> None:
    successful_downloads = sum(result is not None for result in results.values())
    print(f"Downloaded or reused: {successful_downloads}/{len(results)}")
    print(f"PDF directory: {output_directory.resolve()}")
    print(f"Manifest: {manifest_path.resolve()}")

    for drug_name, result in results.items():
        if result is None:
            print(f"[failed] {drug_name}")
            continue
        print(f"[ready] {drug_name}: {result.file_path.name}")


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    if arguments.is_debug_enabled:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        return asyncio.run(run_download(arguments))
    except (OSError, RuntimeError, ValidationError) as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
