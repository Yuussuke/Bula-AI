import asyncio
import hashlib
from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from fastapi import HTTPException, UploadFile
import structlog

from app.core.idempotency import IdempotencyConflictError, operation_fingerprint
from app.modules.auth.models import User, UserRole
from app.modules.bulas.curation_repository import (
    CurationConflictError,
    CurationRepository,
    CurationMutationResult,
    DuplicateSharedPdfError,
)
from app.modules.bulas.curation_schemas import (
    CurationDecision,
    CurationListQuery,
    SharedSourceInput,
    SharedBulaDetail,
    SharedBulaResponse,
    SharedBulaPage,
    CurationEventResponse,
    CurationMutationResponse,
    SharedMetadataSuggestion,
)
from app.modules.bulas.helpers import InvalidPdfError, validate_pdf_bytes
from app.modules.bulas.models import Bula
from app.modules.bulas.curation_queue_repository import IngestionQueueUnavailableError
from app.modules.storage.client import ObjectStoreClient
from app.modules.rag.parsers.pdf_parser import BulaParser

logger = structlog.get_logger(__name__)


class CurationService:
    def __init__(
        self,
        *,
        repository: CurationRepository,
        object_store: ObjectStoreClient,
        max_upload_size_bytes: int,
        metadata_parser: BulaParser,
    ) -> None:
        self.repository = repository
        self.object_store = object_store
        self.max_upload_size_bytes = max_upload_size_bytes
        self.metadata_parser = metadata_parser

    def require_reviewer(self, actor: User) -> None:
        if actor.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
            raise HTTPException(403, "Acesso restrito ao Curador e ao administrador.")

    async def submit(
        self,
        *,
        actor: User,
        file: UploadFile,
        source: SharedSourceInput,
        operation_id: UUID,
    ) -> CurationMutationResponse:
        if actor.role not in {UserRole.ADMIN, UserRole.CONTRIBUTOR}:
            raise HTTPException(
                403, "Somente Contribuidores e administradores podem submeter bulas."
            )
        if file.content_type != "application/pdf":
            raise HTTPException(400, "Envie um arquivo PDF.")
        content = await file.read(self.max_upload_size_bytes + 1)
        try:
            await asyncio.to_thread(
                validate_pdf_bytes, content, max_size_bytes=self.max_upload_size_bytes
            )
        except InvalidPdfError as error:
            raise HTTPException(400, str(error)) from error
        filename = PurePosixPath(
            PureWindowsPath(file.filename or "bula.pdf").name
        ).name[:255]
        checksum = hashlib.sha256(content).hexdigest()
        request_fingerprint = operation_fingerprint(
            "submit",
            {
                **source.model_dump(mode="json"),
                "sha256_checksum": checksum,
                "content_size_bytes": len(content),
                "filename": filename,
            },
        )
        actor_id = int(actor.id)
        try:
            replay = await self.repository.replay(
                actor_id=actor_id,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
        except IdempotencyConflictError as error:
            raise HTTPException(
                409, "Esta chave de operação já foi usada com outro conteúdo."
            ) from error
        if replay is not None:
            return await self._mutation_response(
                replay, operation_id=operation_id, actor_id=actor_id
            )
        if await self.repository.has_active_pdf(checksum):
            raise HTTPException(
                409, "Já existe uma submissão pendente ou aprovada deste PDF."
            )
        address = await self.object_store.put_bytes(content, filename)
        try:
            result = await self.repository.create(
                actor=actor,
                object_address=address,
                source_url=str(source.source_url),
                source_description=source.source_description,
                checksum=checksum,
                size=len(content),
                product_name=source.product_name,
                manufacturer=source.manufacturer,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
        except (DuplicateSharedPdfError, IdempotencyConflictError) as error:
            await self._discard_unreferenced_upload(address)
            raise HTTPException(
                409,
                "PDF já submetido ou chave de operação utilizada com outro conteúdo.",
            ) from error
        except BaseException:
            await self._discard_unreferenced_upload(address)
            raise
        if result.replayed and result.bula.file_address != address:
            await self._discard_unreferenced_upload(address)
        return await self._mutation_response(
            result, operation_id=operation_id, actor_id=actor_id
        )

    async def _discard_unreferenced_upload(self, address: str) -> None:
        # A lost commit acknowledgement must not delete an already linked PDF.
        try:
            if not await self.repository.is_object_referenced(address):
                await self.object_store.delete(address)
        except Exception:
            logger.exception("curation_unused_upload_cleanup_failed")

    async def _mutation_response(
        self, result: CurationMutationResult, *, operation_id: UUID, actor_id: int
    ) -> CurationMutationResponse:
        logger.info(
            "curation_operation_replayed"
            if result.replayed
            else "curation_operation_committed",
            operation_id=str(operation_id),
            actor_id=actor_id,
            bula_id=str(result.bula.id),
        )
        document = await self.describe(result.bula)
        return CurationMutationResponse(
            **document.model_dump(), operation_id=operation_id, replayed=result.replayed
        )

    async def list_page(
        self, *, actor: User, filters: CurationListQuery
    ) -> SharedBulaPage:
        if filters.view == "review":
            self.require_reviewer(actor)
        owner_id = int(actor.id) if filters.view == "mine" else None
        items, total = await self.repository.list_page(
            filters=filters, owner_id=owner_id
        )
        available = await self.repository.list_public(
            bula_ids=[item.id for item in items]
        )
        available_ids = {item.id for item in available}
        return SharedBulaPage(
            items=[
                SharedBulaResponse.from_bula(
                    item, is_available=item.id in available_ids
                )
                for item in items
            ],
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def describe(self, bula: Bula) -> SharedBulaResponse:
        available = await self.repository.list_public(bula_ids=[bula.id])
        return SharedBulaResponse.from_bula(bula, is_available=bool(available))

    async def get_visible(self, *, actor: User, bula_id: UUID) -> Bula:
        bula = await self.repository.get(bula_id)
        if bula is None:
            raise HTTPException(404, "Submissão não encontrada.")
        is_staff = actor.role in {UserRole.ADMIN, UserRole.REVIEWER}
        if bula.user_id == actor.id or is_staff:
            return bula
        public = await self.repository.list_public(bula_ids=[bula_id])
        if not public:
            raise HTTPException(404, "Submissão não encontrada.")
        return public[0]

    async def read_pdf(self, *, actor: User, bula_id: UUID) -> bytes:
        bula = await self.get_visible(actor=actor, bula_id=bula_id)
        return await self._verified_pdf(bula)

    async def suggest_metadata(
        self, *, actor: User, bula_id: UUID
    ) -> SharedMetadataSuggestion:
        self.require_reviewer(actor)
        bula = await self.get_visible(actor=actor, bula_id=bula_id)
        submission = bula.shared_submission
        if submission is None or submission.review_status != "pending":
            raise HTTPException(
                409, "As sugestões são destinadas a submissões aguardando curadoria."
            )
        version = submission.version
        checksum = submission.sha256_checksum
        content = await self._verified_pdf(bula)
        parsed = await self.metadata_parser.parse(
            pdf_bytes=content, filename="bula.pdf"
        )
        if not parsed.success:
            raise HTTPException(
                422,
                "Não foi possível extrair a identificação automaticamente. Confira o PDF e preencha os campos manualmente.",
            )
        current = await self.repository.get(bula_id)
        if (
            current is None
            or current.shared_submission is None
            or current.shared_submission.version != version
            or current.shared_submission.sha256_checksum != checksum
        ):
            raise HTTPException(
                409, "A submissão mudou durante a leitura. Atualize a conferência."
            )
        front_matter = parsed.metadata.get("front_matter")
        fields = front_matter if isinstance(front_matter, dict) else {}

        def text(value: object) -> str | None:
            return value.strip() if isinstance(value, str) and value.strip() else None

        product_name = text(parsed.metadata.get("drug_name"))
        if parsed.metadata.get("drug_name_source") == "filename_best_effort":
            product_name = None
        return SharedMetadataSuggestion(
            bula_id=bula_id,
            version=version,
            sha256_checksum=checksum,
            parser_version=parsed.parser_version,
            product_name=product_name,
            manufacturer=text(parsed.metadata.get("manufacturer")),
            presentation=text(fields.get("presentation")),
            strength=text(fields.get("strength")),
        )

    async def detail(self, *, actor: User, bula_id: UUID) -> SharedBulaDetail:
        bula = await self.get_visible(actor=actor, bula_id=bula_id)
        events = []
        if bula.user_id == actor.id or actor.role in {
            UserRole.ADMIN,
            UserRole.REVIEWER,
        }:
            events = await self.repository.events(bula_id)
        return SharedBulaDetail(
            document=await self.describe(bula),
            events=[CurationEventResponse.model_validate(event) for event in events],
            submitted_by_name=next(
                (event.actor_name for event in events if event.action == "submitted"),
                None,
            ),
        )

    async def _verified_pdf(self, bula: Bula) -> bytes:
        submission = bula.shared_submission
        if submission is None or bula.file_address is None:
            raise HTTPException(409, "Submissão sem PDF verificável.")
        content = await self.object_store.get_bytes(bula.file_address)
        if (
            len(content) != submission.content_size_bytes
            or hashlib.sha256(content).hexdigest() != submission.sha256_checksum
        ):
            raise HTTPException(
                409,
                "O PDF armazenado diverge da submissão. A decisão foi interrompida.",
            )
        return content

    async def decide(
        self,
        *,
        actor: User,
        bula_id: UUID,
        action: str,
        payload: CurationDecision,
        operation_id: UUID,
    ) -> CurationMutationResponse:
        self.require_reviewer(actor)
        actor_id = int(actor.id)
        request_fingerprint = operation_fingerprint(
            action, {"bula_id": str(bula_id), **payload.model_dump(mode="json")}
        )
        try:
            replay = await self.repository.replay(
                actor_id=actor_id,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
            )
        except IdempotencyConflictError as error:
            raise HTTPException(
                409, "Esta chave de operação já foi usada com outro conteúdo."
            ) from error
        if replay is not None:
            return await self._mutation_response(
                replay, operation_id=operation_id, actor_id=actor_id
            )
        bula = await self.get_visible(actor=actor, bula_id=bula_id)
        if action in {"approve", "reject"} and bula.user_id == actor.id:
            raise HTTPException(
                403, "O responsável pelo envio não pode revisar a própria submissão."
            )
        transitions = {
            "approve": ("pending", "approved", "approved"),
            "reject": ("pending", "rejected", "rejected"),
            "withdraw": ("approved", "withdrawn", "withdrawn"),
            "retry": ("approved", "approved", "ingestion_retry"),
        }
        if action not in transitions:
            raise HTTPException(400, "Ação desconhecida.")
        if action == "approve" and not payload.product_name:
            raise HTTPException(
                422, "Confirme o nome do medicamento identificado no PDF."
            )
        # A damaged or unavailable file must never prevent taking it out of use.
        if action in {"approve", "retry"}:
            await self._verified_pdf(bula)
        expected, target, event = transitions[action]
        try:
            result = await self.repository.transition(
                bula=bula,
                actor=actor,
                expected_version=payload.expected_version,
                expected_status=expected,
                target_status=target,
                action=event,
                reason=payload.reason,
                operation_id=operation_id,
                request_fingerprint=request_fingerprint,
                product_name=payload.product_name,
                manufacturer=payload.manufacturer,
                presentation=payload.presentation,
                strength=payload.strength,
                retry_ingestion=action == "retry",
            )
        except CurationConflictError as error:
            raise HTTPException(
                409, "A submissão mudou ou a ação não é permitida. Atualize a página."
            ) from error
        except IdempotencyConflictError as error:
            raise HTTPException(
                409, "Esta chave de operação já foi usada com outro conteúdo."
            ) from error
        except IngestionQueueUnavailableError as error:
            logger.exception(
                "curation_queue_transaction_failed",
                operation_id=str(operation_id),
                actor_id=actor_id,
                bula_id=str(bula_id),
            )
            raise HTTPException(
                503,
                "A ação não foi gravada porque a ingestão não pôde ser enfileirada. Tente novamente.",
            ) from error
        return await self._mutation_response(
            result, operation_id=operation_id, actor_id=actor_id
        )
