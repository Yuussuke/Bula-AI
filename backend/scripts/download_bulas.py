#!/usr/bin/env python3
"""Download explicitly pinned ANVISA leaflet targets with auditable provenance."""

from __future__ import annotations

import argparse
import asyncio
import base64
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Literal, cast
from urllib.parse import quote

from playwright.async_api import Page, async_playwright
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.modules.bulas.helpers import InvalidPdfError, validate_pdf_bytes
from app.modules.bulas.schemas import (
    SystemBulaManifest,
    SystemBulaManifestEntry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BASE = "https://consultas.anvisa.gov.br"
DEFAULT_OUTPUT_DIRECTORY = Path("tmp/anvisa-bulas-v2")
DEFAULT_TARGETS_PATH = Path("scripts/anvisa_targets.json")
MANIFEST_FILENAME = "manifest.json"
DOWNLOADER_VERSION = "2.0"
MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024


class AnvisaSelectionError(ValueError):
    """Raised when an exact ANVISA target cannot be resolved safely."""


class AnvisaBulaRecord(BaseModel):
    product_id: int = Field(alias="idProduto")
    registration_number: str = Field(alias="numeroRegistro")
    product_name: str = Field(alias="nomeProduto")
    expedition_number: str = Field(alias="expediente")
    manufacturer: str = Field(alias="razaoSocial")
    company_tax_id: str = Field(alias="cnpj")
    transaction_number: str = Field(alias="numeroTransacao")
    published_at: datetime = Field(alias="data")
    process_number: str = Field(alias="numProcesso")
    patient_bula_id: str | None = Field(
        default=None,
        alias="idBulaPacienteProtegido",
    )
    professional_bula_id: str | None = Field(
        default=None,
        alias="idBulaProfissionalProtegido",
    )
    updated_at: datetime | None = Field(default=None, alias="dataAtualizacao")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    def protected_document_id(
        self, audience: Literal["patient", "professional"]
    ) -> str:
        protected_id = (
            self.patient_bula_id if audience == "patient" else self.professional_bula_id
        )
        if protected_id is None:
            raise AnvisaSelectionError(
                f"ANVISA record {self.product_id} has no {audience} leaflet."
            )
        return protected_id

    def source_record_id(self, audience: Literal["patient", "professional"]) -> str:
        return decode_source_record_id(self.protected_document_id(audience))


class AnvisaSearchResponse(BaseModel):
    content: list[AnvisaBulaRecord] = Field(default_factory=list)
    total_pages: int = Field(default=1, alias="totalPages", ge=1)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class AnvisaBulaTarget(BaseModel):
    target_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    search_query: str = Field(min_length=1)
    active_ingredient: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    strength: str = Field(min_length=1)
    pharmaceutical_form: str = Field(min_length=1)
    presentation: str = Field(min_length=1)
    audience: Literal["patient", "professional"]
    manufacturer: str = Field(min_length=1)
    company_tax_id: str = Field(min_length=1)
    anvisa_product_id: int = Field(gt=0)
    registration_number: str = Field(min_length=1)
    process_number: str = Field(min_length=1)
    expedition_number: str = Field(min_length=1)
    transaction_number: str = Field(min_length=1)
    source_record_id: str = Field(pattern=r"^[0-9]+$")
    expected_pdf_terms: list[str] = Field(min_length=1)

    model_config = ConfigDict(str_strip_whitespace=True)


class AnvisaTargetConfiguration(BaseModel):
    schema_version: Literal[1] = 1
    targets: list[AnvisaBulaTarget] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_targets(self) -> "AnvisaTargetConfiguration":
        target_ids = [target.target_id for target in self.targets]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("Target configuration contains duplicate target IDs.")

        source_identities = [
            (target.source_record_id, target.audience) for target in self.targets
        ]
        if len(source_identities) != len(set(source_identities)):
            raise ValueError(
                "Target configuration contains duplicate source identities."
            )
        return self


@dataclass(frozen=True)
class DownloadArguments:
    output_directory: Path
    manifest_path: Path
    targets_path: Path
    discovery_query: str | None
    proxy: str | None
    is_headless: bool
    limit: int | None
    is_debug_enabled: bool


@dataclass(frozen=True)
class DownloadResult:
    manifest_entry: SystemBulaManifestEntry
    file_path: Path
    was_reused: bool


def search_url(drug: str, page_num: int = 1, count: int = 100) -> str:
    return (
        f"{BASE}/api/consulta/bulario"
        f"?count={count}"
        f"&filter%5BnomeProduto%5D={quote(drug)}"
        f"&page={page_num}"
    )


def pdf_url(protected_bula_id: str) -> str:
    return (
        f"{BASE}/api/consulta/medicamentos/arquivo/bula/parecer/"
        f"{protected_bula_id}/?Authorization="
    )


def decode_source_record_id(protected_bula_id: str) -> str:
    token_parts = protected_bula_id.split(".")
    if len(token_parts) != 3:
        raise AnvisaSelectionError("ANVISA returned an invalid protected document ID.")

    encoded_payload = token_parts[1]
    encoded_payload += "=" * (-len(encoded_payload) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise AnvisaSelectionError(
            "ANVISA returned an unreadable protected document ID."
        ) from exc

    source_record_id = payload.get("jti")
    if not isinstance(source_record_id, str) or not source_record_id.isdigit():
        raise AnvisaSelectionError(
            "ANVISA protected document ID does not contain a stable record ID."
        )
    return source_record_id


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
    result = cast(
        object,
        await page.evaluate(
            """async (url) => {
            try {
                const response = await fetch(url, {
                    headers: {
                        "Authorization": "Guest",
                        "Accept": "application/pdf, application/octet-stream, */*"
                    },
                    credentials: "include"
                });
                if (!response.ok) {
                    return {error: "http", status: response.status};
                }
                const buffer = await response.arrayBuffer();
                const view = new Uint8Array(buffer);
                let binary = "";
                for (let index = 0; index < view.byteLength; index++) {
                    binary += String.fromCharCode(view[index]);
                }
                return {data: btoa(binary)};
            } catch (error) {
                return {error: "javascript", detail: String(error)};
            }
        }""",
            url,
        ),
    )
    if not isinstance(result, dict):
        log.warning("ANVISA returned an invalid PDF response.")
        return None
    if result.get("error") == "http":
        log.warning("ANVISA PDF download returned HTTP %s.", result.get("status"))
        return None
    if result.get("error") == "javascript":
        log.warning("Browser PDF request failed: %s", result.get("detail"))
        return None

    encoded_pdf = result.get("data")
    if not isinstance(encoded_pdf, str) or not encoded_pdf:
        log.warning("ANVISA PDF response did not contain document bytes.")
        return None
    return base64.b64decode(encoded_pdf)


class AnvisaBulaDownloader:
    def __init__(
        self,
        *,
        page: Page,
        output_directory: Path,
        manifest_path: Path,
        max_pdf_size_bytes: int,
        should_load_manifest: bool = True,
    ) -> None:
        self.page = page
        self.output_directory = output_directory
        self.manifest_path = manifest_path
        self.max_pdf_size_bytes = max_pdf_size_bytes
        self.manifest_entries = (
            self._load_existing_manifest_entries() if should_load_manifest else {}
        )

    async def download_targets(
        self,
        targets: Sequence[AnvisaBulaTarget],
    ) -> dict[str, DownloadResult | None]:
        results: dict[str, DownloadResult | None] = {}
        for target in targets:
            try:
                result = await self.download_target(target)
            except (AnvisaSelectionError, InvalidPdfError) as exc:
                log.error("Target %s rejected: %s", target.target_id, exc)
                result = None
            results[target.target_id] = result
            if result is None:
                continue

            self._replace_manifest_entry(result.manifest_entry)
            self._write_manifest()
        return results

    async def download_target(
        self,
        target: AnvisaBulaTarget,
    ) -> DownloadResult | None:
        log.info("Searching ANVISA for exact target %s.", target.target_id)
        records = await self.fetch_all_results(search_query=target.search_query)
        record = self._resolve_exact_record(target=target, records=records)
        protected_document_id = record.protected_document_id(target.audience)
        source_record_id = record.source_record_id(target.audience)
        filename = self._build_filename(target=target)
        file_path = self.output_directory / filename

        existing_result = self._build_existing_file_result(
            target=target,
            record=record,
            file_path=file_path,
        )
        if existing_result is not None:
            log.info("Using provenance-verified PDF %s.", filename)
            return existing_result

        log.info(
            "Downloading %s leaflet for %s (source record %s).",
            target.audience,
            target.product_name,
            source_record_id,
        )
        pdf_bytes = await browser_pdf(
            self.page,
            pdf_url(protected_document_id),
        )
        if pdf_bytes is None:
            return None

        self._write_validated_pdf_atomically(
            file_path=file_path,
            pdf_bytes=pdf_bytes,
            expected_pdf_terms=target.expected_pdf_terms,
        )
        return DownloadResult(
            manifest_entry=self._build_manifest_entry(
                target=target,
                record=record,
                filename=filename,
                pdf_bytes=pdf_bytes,
            ),
            file_path=file_path,
            was_reused=False,
        )

    async def fetch_all_results(
        self,
        *,
        search_query: str,
    ) -> list[AnvisaBulaRecord]:
        records: list[AnvisaBulaRecord] = []
        page_number = 1
        while True:
            response_payload = await browser_json(
                self.page,
                search_url(search_query, page_num=page_number, count=100),
            )
            if response_payload is None:
                raise AnvisaSelectionError(f"ANVISA search failed for {search_query}.")
            try:
                response = AnvisaSearchResponse.model_validate(response_payload)
            except ValidationError as exc:
                raise AnvisaSelectionError(
                    f"ANVISA returned an invalid response for {search_query}."
                ) from exc

            records.extend(response.content)
            log.info(
                "ANVISA query %s page %s/%s returned %s records.",
                search_query,
                page_number,
                response.total_pages,
                len(response.content),
            )
            if page_number >= response.total_pages:
                return records
            page_number += 1
            await asyncio.sleep(0.5)

    def _resolve_exact_record(
        self,
        *,
        target: AnvisaBulaTarget,
        records: Sequence[AnvisaBulaRecord],
    ) -> AnvisaBulaRecord:
        matches: list[AnvisaBulaRecord] = []
        for record in records:
            try:
                source_record_id = record.source_record_id(target.audience)
            except AnvisaSelectionError:
                continue

            is_exact_match = all(
                (
                    record.product_id == target.anvisa_product_id,
                    record.product_name.casefold() == target.product_name.casefold(),
                    record.manufacturer.casefold() == target.manufacturer.casefold(),
                    record.company_tax_id == target.company_tax_id,
                    record.registration_number == target.registration_number,
                    record.process_number == target.process_number,
                    record.expedition_number == target.expedition_number,
                    record.transaction_number == target.transaction_number,
                    source_record_id == target.source_record_id,
                )
            )
            if is_exact_match:
                matches.append(record)

        if len(matches) != 1:
            raise AnvisaSelectionError(
                f"Target {target.target_id} resolved to {len(matches)} records; "
                "exactly one is required."
            )
        return matches[0]

    def _build_existing_file_result(
        self,
        *,
        target: AnvisaBulaTarget,
        record: AnvisaBulaRecord,
        file_path: Path,
    ) -> DownloadResult | None:
        existing_entry = self.manifest_entries.get(target.target_id)
        if existing_entry is None or not file_path.is_file():
            return None
        if not self._entry_matches_source(
            entry=existing_entry,
            target=target,
            record=record,
        ):
            log.warning(
                "Source identity changed for %s; forcing a fresh download.",
                target.target_id,
            )
            return None

        pdf_bytes = file_path.read_bytes()
        try:
            validate_pdf_bytes(
                pdf_bytes,
                max_size_bytes=self.max_pdf_size_bytes,
                expected_text_terms=target.expected_pdf_terms,
            )
        except InvalidPdfError:
            log.warning("Existing PDF %s is incomplete or corrupt.", file_path.name)
            return None

        checksum = hashlib.sha256(pdf_bytes).hexdigest()
        if (
            len(pdf_bytes) != existing_entry.content_size_bytes
            or checksum != existing_entry.sha256_checksum
        ):
            log.warning("Existing PDF %s does not match its manifest.", file_path.name)
            return None

        return DownloadResult(
            manifest_entry=existing_entry,
            file_path=file_path,
            was_reused=True,
        )

    def _entry_matches_source(
        self,
        *,
        entry: SystemBulaManifestEntry,
        target: AnvisaBulaTarget,
        record: AnvisaBulaRecord,
    ) -> bool:
        return all(
            (
                entry.target_id == target.target_id,
                entry.active_ingredient == target.active_ingredient,
                entry.product_name.casefold() == target.product_name.casefold(),
                entry.strength == target.strength,
                entry.pharmaceutical_form == target.pharmaceutical_form,
                entry.presentation == target.presentation,
                entry.audience == target.audience,
                entry.manufacturer.casefold() == target.manufacturer.casefold(),
                entry.company_tax_id == target.company_tax_id,
                entry.anvisa_product_id == record.product_id,
                entry.registration_number == record.registration_number,
                entry.process_number == record.process_number,
                entry.expedition_number == record.expedition_number,
                entry.transaction_number == record.transaction_number,
                entry.source_record_id == record.source_record_id(target.audience),
                entry.search_query == target.search_query,
                entry.downloader_version == DOWNLOADER_VERSION,
            )
        )

    def _write_validated_pdf_atomically(
        self,
        *,
        file_path: Path,
        pdf_bytes: bytes,
        expected_pdf_terms: Sequence[str],
    ) -> None:
        partial_path = file_path.with_suffix(f"{file_path.suffix}.part")
        try:
            partial_path.write_bytes(pdf_bytes)
            persisted_bytes = partial_path.read_bytes()
            validate_pdf_bytes(
                persisted_bytes,
                max_size_bytes=self.max_pdf_size_bytes,
                expected_text_terms=expected_pdf_terms,
            )
            partial_path.replace(file_path)
        finally:
            if partial_path.exists():
                partial_path.unlink()

    def _build_manifest_entry(
        self,
        *,
        target: AnvisaBulaTarget,
        record: AnvisaBulaRecord,
        filename: str,
        pdf_bytes: bytes,
    ) -> SystemBulaManifestEntry:
        return SystemBulaManifestEntry(
            target_id=target.target_id,
            active_ingredient=target.active_ingredient,
            product_name=target.product_name,
            strength=target.strength,
            pharmaceutical_form=target.pharmaceutical_form,
            presentation=target.presentation,
            audience=target.audience,
            manufacturer=record.manufacturer,
            company_tax_id=record.company_tax_id,
            anvisa_product_id=record.product_id,
            registration_number=record.registration_number,
            process_number=record.process_number,
            expedition_number=record.expedition_number,
            transaction_number=record.transaction_number,
            source_record_id=record.source_record_id(target.audience),
            canonical_source_url=search_url(target.search_query),
            source_published_at=record.published_at,
            source_updated_at=record.updated_at,
            search_query=target.search_query,
            downloader_version=DOWNLOADER_VERSION,
            downloaded_at=datetime.now(UTC),
            filename=filename,
            sha256_checksum=hashlib.sha256(pdf_bytes).hexdigest(),
            content_size_bytes=len(pdf_bytes),
        )

    def _build_filename(self, *, target: AnvisaBulaTarget) -> str:
        safe_target_id = re.sub(r"[^a-z0-9_-]", "_", target.target_id.casefold())
        return f"{safe_target_id}__{target.source_record_id}__{target.audience}.pdf"

    def _load_existing_manifest_entries(
        self,
    ) -> dict[str, SystemBulaManifestEntry]:
        if not self.manifest_path.is_file():
            return {}
        manifest = SystemBulaManifest.model_validate_json(
            self.manifest_path.read_text(encoding="utf-8")
        )
        return {document.target_id: document for document in manifest.documents}

    def _replace_manifest_entry(self, entry: SystemBulaManifestEntry) -> None:
        for target_id, existing_entry in self.manifest_entries.items():
            if (
                target_id != entry.target_id
                and existing_entry.filename.casefold() == entry.filename.casefold()
            ):
                raise AnvisaSelectionError(
                    f"Filename {entry.filename} is already assigned to {target_id}."
                )
        self.manifest_entries[entry.target_id] = entry

    def _write_manifest(self) -> None:
        documents = sorted(
            self.manifest_entries.values(),
            key=lambda document: document.target_id,
        )
        manifest = SystemBulaManifest(documents=documents)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = self.manifest_path.with_suffix(
            f"{self.manifest_path.suffix}.part"
        )
        try:
            partial_path.write_text(
                f"{manifest.model_dump_json(indent=2)}\n",
                encoding="utf-8",
                newline="\n",
            )
            partial_path.replace(self.manifest_path)
        finally:
            if partial_path.exists():
                partial_path.unlink()


def positive_integer(value: str) -> int:
    parsed_value = int(value)
    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")
    return parsed_value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download exact, pinned public leaflet targets from ANVISA.",
    )
    parser.add_argument("--proxy", help="Optional HTTP or SOCKS5 proxy URL.")
    parser.add_argument(
        "--output",
        "-o",
        default=str(DEFAULT_OUTPUT_DIRECTORY),
        help="Directory for PDFs and the generated manifest.",
    )
    parser.add_argument(
        "--manifest",
        help="Manifest path. Defaults to <output>/manifest.json.",
    )
    parser.add_argument(
        "--targets",
        default=str(DEFAULT_TARGETS_PATH),
        help="JSON file containing exact ANVISA target identities.",
    )
    parser.add_argument(
        "--discover",
        dest="discovery_query",
        help="List auditable ANVISA candidate metadata without downloading.",
    )
    parser.add_argument(
        "--limit",
        type=positive_integer,
        help="Download only the first N configured targets.",
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
    parsed_arguments = build_parser().parse_args(argv)
    output_directory = Path(parsed_arguments.output)
    manifest_path = (
        Path(parsed_arguments.manifest)
        if parsed_arguments.manifest
        else output_directory / MANIFEST_FILENAME
    )
    return DownloadArguments(
        output_directory=output_directory,
        manifest_path=manifest_path,
        targets_path=Path(parsed_arguments.targets),
        discovery_query=parsed_arguments.discovery_query,
        proxy=parsed_arguments.proxy,
        is_headless=parsed_arguments.headless,
        limit=parsed_arguments.limit,
        is_debug_enabled=parsed_arguments.debug,
    )


def load_targets(arguments: DownloadArguments) -> list[AnvisaBulaTarget]:
    configuration = AnvisaTargetConfiguration.model_validate_json(
        arguments.targets_path.read_text(encoding="utf-8")
    )
    targets = configuration.targets
    if arguments.limit is not None:
        targets = targets[: arguments.limit]
    return targets


async def run_download(arguments: DownloadArguments) -> int:
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
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

            downloader = AnvisaBulaDownloader(
                page=page,
                output_directory=arguments.output_directory,
                manifest_path=arguments.manifest_path,
                max_pdf_size_bytes=MAX_PDF_SIZE_BYTES,
                should_load_manifest=arguments.discovery_query is None,
            )
            if arguments.discovery_query is not None:
                records = await downloader.fetch_all_results(
                    search_query=arguments.discovery_query
                )
                print_discovery(records)
                return 0

            targets = load_targets(arguments)
            results = await downloader.download_targets(targets)
        finally:
            await browser.close()

    print_download_summary(
        results=results,
        output_directory=arguments.output_directory,
        manifest_path=arguments.manifest_path,
    )
    return 0 if all(result is not None for result in results.values()) else 1


def print_discovery(records: Sequence[AnvisaBulaRecord]) -> None:
    candidates: list[dict[str, object]] = []
    for record in records:
        candidate = record.model_dump(
            mode="json",
            exclude={"patient_bula_id", "professional_bula_id"},
        )
        candidate["patient_source_record_id"] = (
            record.source_record_id("patient") if record.patient_bula_id else None
        )
        candidate["professional_source_record_id"] = (
            record.source_record_id("professional")
            if record.professional_bula_id
            else None
        )
        candidates.append(candidate)
    print(json.dumps(candidates, ensure_ascii=False, indent=2))


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
    for target_id, result in results.items():
        if result is None:
            print(f"[failed] {target_id}")
            continue
        action = "reused" if result.was_reused else "downloaded"
        print(f"[{action}] {target_id}: {result.file_path.name}")


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    if arguments.is_debug_enabled:
        logging.getLogger().setLevel(logging.DEBUG)
    try:
        return asyncio.run(run_download(arguments))
    except (OSError, RuntimeError, ValidationError, AnvisaSelectionError) as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
