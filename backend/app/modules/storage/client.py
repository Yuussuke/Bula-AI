import hashlib
import uuid
from abc import ABC, abstractmethod

from fastapi import UploadFile

from app.modules.storage.models import StoredObject
from app.modules.storage.repository import (
    StoredObjectNotFoundError,
    StoredObjectRepository,
)
from app.modules.storage.schemas import StoredObjectRef


class ObjectStoreClient(ABC):
    @abstractmethod
    async def put_bytes(self, data: bytes, filename: str) -> str:
        """Store bytes and return the persisted object address."""

    @abstractmethod
    async def put_file(self, file: UploadFile) -> str:
        """Store an uploaded file and return the persisted object address."""

    @abstractmethod
    async def get_bytes(self, address: str) -> bytes:
        """Return object bytes for an existing address."""

    @abstractmethod
    async def get_metadata(
        self,
        address: str,
    ) -> StoredObjectRef:
        """Return object metadata for an existing address."""

    @abstractmethod
    async def exists(self, address: str) -> bool:
        """Return whether an object exists at the given address."""

    @abstractmethod
    async def delete(self, address: str) -> None:
        """Delete an existing object by address."""


class PgObjectStoreClient(ObjectStoreClient):
    def __init__(self, repository: StoredObjectRepository) -> None:
        self.repository = repository

    async def put_bytes(self, data: bytes, filename: str) -> str:
        object_address = self._build_object_address()
        sha256_checksum = self._calculate_sha256_checksum(data)

        await self.repository.create_stored_object(
            object_address=object_address,
            original_filename=filename,
            content_type=None,
            content_size_bytes=len(data),
            sha256_checksum=sha256_checksum,
            data=data,
        )

        return object_address

    async def put_file(self, file: UploadFile) -> str:
        content = await file.read()
        filename = file.filename or ""
        return await self.put_bytes(data=content, filename=filename)

    async def get_bytes(self, address: str) -> bytes:
        stored_object = await self.repository.get_by_object_address_with_data(address)
        if stored_object is None:
            raise StoredObjectNotFoundError(address)

        return stored_object.data

    async def get_metadata(
        self,
        address: str,
    ) -> StoredObjectRef:
        stored_object = await self.repository.get_by_object_address(address)
        if stored_object is None:
            raise StoredObjectNotFoundError(address)

        return self._build_metadata(stored_object)

    async def exists(self, address: str) -> bool:
        return await self.repository.object_exists(address)

    async def delete(self, address: str) -> None:
        await self.repository.delete_by_address(address)

    def _build_object_address(self) -> str:
        return f"stored_objects/{uuid.uuid4()}"

    def _calculate_sha256_checksum(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _build_metadata(self, stored_object: StoredObject) -> StoredObjectRef:
        return StoredObjectRef(
            object_address=stored_object.object_address,
            original_filename=stored_object.original_filename,
            content_type=stored_object.content_type,
            content_size_bytes=stored_object.content_size_bytes,
            sha256_checksum=stored_object.sha256_checksum,
            created_at=stored_object.created_at,
            updated_at=stored_object.updated_at,
        )
