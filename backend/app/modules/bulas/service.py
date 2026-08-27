import hashlib
from collections.abc import Sequence
from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.modules.auth.models import UserRole
from app.modules.auth.repository import UserRepository
from app.modules.bulas.models import Bula, BulaCorpus
from app.modules.bulas.helpers import InvalidPdfError, validate_pdf_bytes
from app.modules.bulas.queue import BulaIngestionQueue
from app.modules.bulas.repository import BulaRepository
from app.modules.bulas.schemas import (
    SystemBulaSeedCandidate,
    SystemBulaSeedFailure,
    SystemBulaSeedSummary,
)
from app.modules.storage.client import ObjectStoreClient


PDF_CONTENT_TYPE = "application/pdf"
PDF_MAGIC_BYTES = b"%PDF-"
UPLOAD_VALIDATION_CHUNK_SIZE_BYTES = 1024 * 1024


class SystemBulaSeedConfigurationError(Exception):
    """Raised when the system corpus seed command is configured incorrectly."""


class BulaService:
    def __init__(
        self,
        bula_repo: BulaRepository,
        object_store: ObjectStoreClient,
        ingestion_queue: BulaIngestionQueue,
        max_upload_size_bytes: int,
    ) -> None:
        self.repo = bula_repo
        self.object_store = object_store
        self.ingestion_queue = ingestion_queue
        self.max_upload_size_bytes = max_upload_size_bytes

    async def upload_and_enqueue_bula(
        self,
        *,
        user_id: int,
        drug_name: str | None,
        manufacturer: str | None,
        file: UploadFile | None,
    ) -> Bula:
        bula = await self.upload_bula(
            user_id=user_id,
            drug_name=drug_name,
            manufacturer=manufacturer,
            file=file,
        )

        try:
            await self.ingestion_queue.enqueue_bula_ingestion(
                bula_id=bula.id,
            )
        except Exception:
            await self._cleanup_persisted_bula_after_enqueue_failure(bula)
            raise

        return bula

    async def upload_bula(
        self,
        *,
        user_id: int,
        drug_name: str | None,
        manufacturer: str | None,
        file: UploadFile | None,
    ) -> Bula:
        clean_drug_name = self._validate_drug_name(drug_name)

        if file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo PDF e obrigatorio.",
            )

        await self._validate_pdf_upload(file)

        file_address: str | None = None
        try:
            await file.seek(0)
            file_address = await self.object_store.put_file(file)
            bula = await self.repo.create_bula(
                user_id=user_id,
                drug_name=clean_drug_name,
                manufacturer=manufacturer,
                file_address=file_address,
            )
        except Exception:
            if file_address is not None:
                await self._delete_uploaded_file_after_failure(file_address)
            raise

        return bula

    async def list_bulas_for_user(self, *, user_id: int) -> list[Bula]:
        return await self.repo.list_by_user(user_id=user_id)

    async def get_bula_status_for_user(
        self,
        *,
        bula_id: UUID,
        user_id: int,
    ) -> Bula:
        bula = await self.repo.get_by_id_for_user(bula_id=bula_id, user_id=user_id)
        if bula is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bula nao encontrada.",
            )

        return bula

    def _validate_drug_name(self, drug_name: str | None) -> str:
        if drug_name is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome do medicamento e obrigatorio.",
            )

        clean_drug_name = drug_name.strip()
        has_drug_name = len(clean_drug_name) > 0
        if not has_drug_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome do medicamento e obrigatorio.",
            )

        return clean_drug_name

    async def _validate_pdf_upload(self, file: UploadFile) -> None:
        is_pdf_content_type = file.content_type == PDF_CONTENT_TYPE
        if not is_pdf_content_type:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Apenas arquivos PDF sao aceitos.",
            )

        magic_bytes, file_size_bytes = await self._read_magic_bytes_and_file_size(file)

        is_file_empty = file_size_bytes == 0
        if is_file_empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo PDF nao pode estar vazio.",
            )

        is_file_too_large = file_size_bytes > self.max_upload_size_bytes
        if is_file_too_large:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="O arquivo excede o tamanho maximo permitido.",
            )

        is_pdf_magic_valid = magic_bytes == PDF_MAGIC_BYTES
        if not is_pdf_magic_valid:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Apenas arquivos PDF validos sao aceitos.",
            )

    async def _read_magic_bytes_and_file_size(
        self,
        file: UploadFile,
    ) -> tuple[bytes, int]:
        await file.seek(0)

        magic_bytes = b""
        file_size_bytes = 0

        while True:
            chunk = await file.read(UPLOAD_VALIDATION_CHUNK_SIZE_BYTES)
            has_chunk = len(chunk) > 0
            if not has_chunk:
                break

            has_complete_magic_bytes = len(magic_bytes) >= len(PDF_MAGIC_BYTES)
            if not has_complete_magic_bytes:
                magic_bytes += chunk
                magic_bytes = magic_bytes[: len(PDF_MAGIC_BYTES)]

            file_size_bytes += len(chunk)
            is_file_too_large = file_size_bytes > self.max_upload_size_bytes
            if is_file_too_large:
                break

        await file.seek(0)
        return magic_bytes, file_size_bytes

    async def _delete_uploaded_file_after_failure(self, file_address: str) -> None:
        try:
            await self.object_store.delete(file_address)
        except Exception:
            return

    async def _cleanup_persisted_bula_after_enqueue_failure(self, bula: Bula) -> None:
        try:
            await self.repo.delete_bula(bula)
        except Exception:
            pass

        if bula.file_address is None:
            return

        await self._delete_uploaded_file_after_failure(bula.file_address)


class SystemBulaSeedService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        bula_repository: BulaRepository,
        object_store: ObjectStoreClient,
        ingestion_queue: BulaIngestionQueue,
        max_upload_size_bytes: int,
    ) -> None:
        self.user_repository = user_repository
        self.bula_repository = bula_repository
        self.object_store = object_store
        self.ingestion_queue = ingestion_queue
        self.max_upload_size_bytes = max_upload_size_bytes

    async def seed_documents(
        self,
        *,
        admin_email: str,
        candidates: Sequence[SystemBulaSeedCandidate],
        is_dry_run: bool,
    ) -> SystemBulaSeedSummary:
        admin_user_id = await self._get_active_admin_user_id(admin_email)
        summary = SystemBulaSeedSummary()

        for candidate in candidates:
            try:
                await self._seed_document(
                    admin_user_id=admin_user_id,
                    candidate=candidate,
                    is_dry_run=is_dry_run,
                    summary=summary,
                )
            except Exception as exc:
                summary.failed += 1
                summary.failures.append(
                    SystemBulaSeedFailure(
                        filename=candidate.manifest_entry.filename,
                        reason=self._build_safe_failure_reason(exc),
                    )
                )

        return summary

    async def _get_active_admin_user_id(self, admin_email: str) -> int:
        clean_admin_email = admin_email.strip().lower()
        admin_user = await self.user_repository.get_user_by_email(clean_admin_email)
        if admin_user is None:
            raise SystemBulaSeedConfigurationError(
                "The configured administrator does not exist."
            )

        if admin_user.role != UserRole.ADMIN:
            raise SystemBulaSeedConfigurationError(
                "The configured user does not have the admin role."
            )

        if not admin_user.is_active:
            raise SystemBulaSeedConfigurationError(
                "The configured administrator is inactive."
            )

        return int(admin_user.id)

    async def _seed_document(
        self,
        *,
        admin_user_id: int,
        candidate: SystemBulaSeedCandidate,
        is_dry_run: bool,
        summary: SystemBulaSeedSummary,
    ) -> None:
        self._validate_candidate(candidate)

        manifest_entry = candidate.manifest_entry
        stored_object = await self.object_store.find_by_sha256_checksum(
            manifest_entry.sha256_checksum
        )
        if stored_object is not None:
            existing_bula = await self.bula_repository.get_by_file_address_and_corpus(
                file_address=stored_object.object_address,
                corpus=BulaCorpus.SYSTEM,
            )
            if existing_bula is not None:
                summary.skipped += 1
                return

        summary.planned += 1
        if is_dry_run:
            return

        object_address = (
            stored_object.object_address
            if stored_object is not None
            else await self.object_store.put_bytes(
                data=candidate.content,
                filename=manifest_entry.filename,
            )
        )
        was_object_created = stored_object is None

        try:
            bula = await self.bula_repository.create_bula(
                user_id=admin_user_id,
                drug_name=manifest_entry.product_name,
                manufacturer=manifest_entry.manufacturer,
                file_address=object_address,
                file_url=str(manifest_entry.canonical_source_url),
                corpus=BulaCorpus.SYSTEM,
            )
        except Exception:
            if was_object_created:
                await self._delete_created_object_after_failure(object_address)
            raise

        try:
            await self.ingestion_queue.enqueue_bula_ingestion(bula_id=bula.id)
        except Exception:
            await self._cleanup_bula_after_enqueue_failure(
                bula=bula,
                was_object_created=was_object_created,
            )
            raise

        summary.inserted += 1
        summary.queued += 1

    def _validate_candidate(self, candidate: SystemBulaSeedCandidate) -> None:
        manifest_entry = candidate.manifest_entry
        content = candidate.content

        try:
            validate_pdf_bytes(
                content,
                max_size_bytes=self.max_upload_size_bytes,
            )
        except InvalidPdfError as exc:
            raise ValueError(str(exc)) from exc

        if len(content) != manifest_entry.content_size_bytes:
            raise ValueError("The PDF size does not match the manifest.")

        actual_checksum = hashlib.sha256(content).hexdigest()
        if actual_checksum != manifest_entry.sha256_checksum:
            raise ValueError("The PDF checksum does not match the manifest.")

    async def _cleanup_bula_after_enqueue_failure(
        self,
        *,
        bula: Bula,
        was_object_created: bool,
    ) -> None:
        try:
            await self.bula_repository.delete_bula(bula)
        except Exception:
            return

        if was_object_created and bula.file_address is not None:
            await self._delete_created_object_after_failure(bula.file_address)

    async def _delete_created_object_after_failure(self, object_address: str) -> None:
        try:
            await self.object_store.delete(object_address)
        except Exception:
            return

    def _build_safe_failure_reason(self, error: Exception) -> str:
        if isinstance(error, ValueError):
            return str(error)

        return "The document could not be persisted or queued."
