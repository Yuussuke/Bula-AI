from fastapi import HTTPException, UploadFile, status

from app.modules.bulas.models import Bula
from app.modules.bulas.repository import BulaRepository
from app.modules.storage.client import ObjectStoreClient


PDF_CONTENT_TYPE = "application/pdf"
PDF_MAGIC_BYTES = b"%PDF-"


class BulaService:
    def __init__(
        self,
        bula_repo: BulaRepository,
        object_store: ObjectStoreClient,
        max_upload_size_bytes: int,
    ) -> None:
        self.repo = bula_repo
        self.object_store = object_store
        self.max_upload_size_bytes = max_upload_size_bytes

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

        file_size_bytes = self._get_file_size_bytes(file)
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

        await file.seek(0)
        magic_bytes = await file.read(len(PDF_MAGIC_BYTES))
        await file.seek(0)

        is_pdf_magic_valid = magic_bytes == PDF_MAGIC_BYTES
        if not is_pdf_magic_valid:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Apenas arquivos PDF validos sao aceitos.",
            )

    def _get_file_size_bytes(self, file: UploadFile) -> int:
        file.file.seek(0, 2)
        file_size_bytes = file.file.tell()
        file.file.seek(0)
        return file_size_bytes

    async def _delete_uploaded_file_after_failure(self, file_address: str) -> None:
        try:
            await self.object_store.delete(file_address)
        except Exception:
            return
