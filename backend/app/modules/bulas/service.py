import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import UserRepository
from app.modules.bulas.models import (
    Bula,
    BulaCorpus,
    BulaStatus,
    SystemBulaPublication,
    SystemBulaPublicationState,
)
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


class SystemBulaPublicationError(Exception):
    """Raised when a system bula publication transition is not allowed."""


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

    async def list_published_system_bulas(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[Bula]:
        return await self.repo.list_published_system_bulas(
            limit=limit,
            offset=offset,
        )

    async def get_published_system_bula(self, *, bula_id: UUID) -> Bula:
        bula = await self.repo.get_published_system_bula(bula_id=bula_id)
        if bula is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bula de sistema nao encontrada.",
            )
        return bula

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
        existing_publication = (
            await self.bula_repository.get_latest_system_publication_by_source_identity(
                source_record_id=manifest_entry.source_record_id,
                audience=manifest_entry.audience,
            )
        )
        if existing_publication is not None and self._publication_matches_manifest(
            publication=existing_publication,
            candidate=candidate,
        ):
            if existing_publication.bula.status == BulaStatus.READY:
                summary.skipped += 1
                return

            summary.planned += 1
            if not is_dry_run:
                await self.ingestion_queue.enqueue_bula_ingestion(
                    bula_id=existing_publication.bula_id
                )
                summary.queued += 1
            return

        stored_object = await self.object_store.find_by_sha256_checksum(
            manifest_entry.sha256_checksum
        )
        existing_bula: Bula | None = None
        if stored_object is not None:
            existing_bula = await self.bula_repository.get_by_file_address_and_corpus(
                file_address=stored_object.object_address,
                corpus=BulaCorpus.SYSTEM,
            )

        summary.planned += 1
        if is_dry_run:
            return

        if existing_bula is not None and existing_publication is None:
            await self.bula_repository.create_system_publication(
                bula=existing_bula,
                manifest_entry=manifest_entry,
            )
            summary.inserted += 1
            if existing_bula.status != BulaStatus.READY:
                await self.ingestion_queue.enqueue_bula_ingestion(
                    bula_id=existing_bula.id
                )
                summary.queued += 1
            return

        if existing_publication is not None:
            await self.bula_repository.update_system_publication_state(
                publication=existing_publication,
                state=SystemBulaPublicationState.WITHDRAWN,
                withdrawal_reason="ANVISA source metadata or checksum changed.",
            )

        object_address = (
            stored_object.object_address
            if stored_object is not None
            else await self.object_store.put_bytes(
                data=candidate.content,
                filename=manifest_entry.filename,
            )
        )
        was_object_created = stored_object is None

        bula: Bula | None = None
        try:
            bula = await self.bula_repository.create_bula(
                user_id=admin_user_id,
                drug_name=manifest_entry.product_name,
                manufacturer=manifest_entry.manufacturer,
                file_address=object_address,
                file_url=str(manifest_entry.canonical_source_url),
                corpus=BulaCorpus.SYSTEM,
            )
            await self.bula_repository.create_system_publication(
                bula=bula,
                manifest_entry=manifest_entry,
                supersedes_bula_id=(
                    existing_publication.bula_id
                    if existing_publication is not None
                    else None
                ),
            )
        except Exception:
            was_bula_deleted = True
            if bula is not None:
                was_bula_deleted = await self._delete_bula_after_publication_failure(
                    bula
                )
            if was_object_created and was_bula_deleted:
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

    def _publication_matches_manifest(
        self,
        *,
        publication: SystemBulaPublication,
        candidate: SystemBulaSeedCandidate,
    ) -> bool:
        manifest_entry = candidate.manifest_entry
        return (
            publication.target_id == manifest_entry.target_id
            and publication.active_ingredient == manifest_entry.active_ingredient
            and publication.product_name == manifest_entry.product_name
            and publication.strength == manifest_entry.strength
            and publication.pharmaceutical_form == manifest_entry.pharmaceutical_form
            and publication.presentation == manifest_entry.presentation
            and publication.manufacturer == manifest_entry.manufacturer
            and publication.company_tax_id == manifest_entry.company_tax_id
            and publication.anvisa_product_id == manifest_entry.anvisa_product_id
            and publication.registration_number == manifest_entry.registration_number
            and publication.process_number == manifest_entry.process_number
            and publication.expedition_number == manifest_entry.expedition_number
            and publication.transaction_number == manifest_entry.transaction_number
            and publication.source_record_id == manifest_entry.source_record_id
            and publication.audience == manifest_entry.audience
            and publication.canonical_source_url
            == str(manifest_entry.canonical_source_url)
            and publication.source_published_at == manifest_entry.source_published_at
            and publication.source_updated_at == manifest_entry.source_updated_at
            and publication.sha256_checksum == manifest_entry.sha256_checksum
            and publication.content_size_bytes == manifest_entry.content_size_bytes
        )

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

    async def _delete_bula_after_publication_failure(self, bula: Bula) -> bool:
        try:
            await self.bula_repository.delete_bula(bula)
        except Exception:
            return False
        return True

    async def _delete_created_object_after_failure(self, object_address: str) -> None:
        try:
            await self.object_store.delete(object_address)
        except Exception:
            return

    def _build_safe_failure_reason(self, error: Exception) -> str:
        if isinstance(error, ValueError):
            return str(error)

        return "The document could not be persisted or queued."


class SystemBulaPublicationService:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        bula_repository: BulaRepository,
        object_store: ObjectStoreClient,
    ) -> None:
        self.user_repository = user_repository
        self.bula_repository = bula_repository
        self.object_store = object_store

    async def vet_document(
        self,
        *,
        bula_id: UUID,
        actor_email: str,
        review_notes: str | None,
    ) -> SystemBulaPublication:
        actor = await self._get_actor(
            actor_email=actor_email,
            allowed_roles={UserRole.ADMIN, UserRole.REVIEWER},
        )
        bula, publication = await self._get_system_bula_and_publication(bula_id)
        if publication.state not in {
            SystemBulaPublicationState.STAGED,
            SystemBulaPublicationState.WITHDRAWN,
        }:
            raise SystemBulaPublicationError(
                "Only staged or withdrawn system bulas can be vetted."
            )

        await self._validate_publishable_integrity(
            bula=bula,
            publication=publication,
        )
        return await self.bula_repository.update_system_publication_state(
            publication=publication,
            state=SystemBulaPublicationState.VETTED,
            reviewed_by_user_id=int(actor.id),
            reviewed_by_name=str(actor.full_name),
            reviewed_at=datetime.now(UTC),
            review_notes=self._clean_optional_text(review_notes),
        )

    async def publish_document(
        self,
        *,
        bula_id: UUID,
        actor_email: str,
    ) -> SystemBulaPublication:
        actor = await self._get_actor(
            actor_email=actor_email,
            allowed_roles={UserRole.ADMIN},
        )
        bula, publication = await self._get_system_bula_and_publication(bula_id)
        if publication.state != SystemBulaPublicationState.VETTED:
            raise SystemBulaPublicationError(
                "Only vetted system bulas can be published."
            )

        await self._validate_publishable_integrity(
            bula=bula,
            publication=publication,
        )
        return await self.bula_repository.update_system_publication_state(
            publication=publication,
            state=SystemBulaPublicationState.PUBLISHED,
            published_by_user_id=int(actor.id),
            published_by_name=str(actor.full_name),
            published_at=datetime.now(UTC),
        )

    async def withdraw_document(
        self,
        *,
        bula_id: UUID,
        actor_email: str,
        reason: str,
    ) -> SystemBulaPublication:
        await self._get_actor(
            actor_email=actor_email,
            allowed_roles={UserRole.ADMIN},
        )
        _, publication = await self._get_system_bula_and_publication(bula_id)
        if publication.state != SystemBulaPublicationState.PUBLISHED:
            raise SystemBulaPublicationError(
                "Only published system bulas can be withdrawn."
            )
        return await self.bula_repository.update_system_publication_state(
            publication=publication,
            state=SystemBulaPublicationState.WITHDRAWN,
            withdrawal_reason=self._require_text(reason, field_name="reason"),
        )

    async def reject_document(
        self,
        *,
        bula_id: UUID,
        actor_email: str,
        reason: str,
    ) -> SystemBulaPublication:
        await self._get_actor(
            actor_email=actor_email,
            allowed_roles={UserRole.ADMIN, UserRole.REVIEWER},
        )
        _, publication = await self._get_system_bula_and_publication(bula_id)
        if publication.state not in {
            SystemBulaPublicationState.STAGED,
            SystemBulaPublicationState.VETTED,
        }:
            raise SystemBulaPublicationError(
                "Only staged or vetted system bulas can be rejected."
            )
        return await self.bula_repository.update_system_publication_state(
            publication=publication,
            state=SystemBulaPublicationState.REJECTED,
            withdrawal_reason=self._require_text(reason, field_name="reason"),
        )

    async def _get_actor(
        self,
        *,
        actor_email: str,
        allowed_roles: set[UserRole],
    ) -> User:
        clean_email = actor_email.strip().lower()
        actor = await self.user_repository.get_user_by_email(clean_email)
        if actor is None or not actor.is_active or actor.role not in allowed_roles:
            raise SystemBulaPublicationError(
                "The actor is not authorized for this publication action."
            )
        return actor

    async def _get_system_bula_and_publication(
        self,
        bula_id: UUID,
    ) -> tuple[Bula, SystemBulaPublication]:
        bula = await self.bula_repository.get_by_id(bula_id=bula_id)
        if bula is None or bula.corpus != BulaCorpus.SYSTEM:
            raise SystemBulaPublicationError("System bula not found.")

        publication = bula.system_publication
        if publication is None:
            raise SystemBulaPublicationError(
                "System bula does not have provenance metadata."
            )
        return bula, publication

    async def _validate_publishable_integrity(
        self,
        *,
        bula: Bula,
        publication: SystemBulaPublication,
    ) -> None:
        if bula.status != BulaStatus.READY:
            raise SystemBulaPublicationError(
                "Only successfully ingested system bulas can be vetted or published."
            )
        if bula.file_address is None:
            raise SystemBulaPublicationError("System bula does not have a PDF object.")

        stored_object = await self.object_store.get_metadata(bula.file_address)
        has_matching_integrity = (
            stored_object.sha256_checksum == publication.sha256_checksum
            and stored_object.content_size_bytes == publication.content_size_bytes
        )
        if not has_matching_integrity:
            raise SystemBulaPublicationError(
                "Stored PDF integrity does not match the vetted provenance."
            )

    def _require_text(self, value: str, *, field_name: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise SystemBulaPublicationError(f"{field_name} is required.")
        return clean_value

    def _clean_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        clean_value = value.strip()
        return clean_value or None
