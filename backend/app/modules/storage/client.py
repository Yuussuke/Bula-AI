import hashlib
import uuid
from abc import ABC, abstractmethod

from app.modules.storage.models import StoredObject
from app.modules.storage.repository import StoredObjectRepository
from app.modules.storage.schemas import StoredObjectMetadata


class ObjectStoreClient(ABC):
    @abstractmethod
    async def put_bytes(
        self,
        *,
        content: bytes,
        original_filename: str | None = None,
        content_type: str | None = None,
    ) -> StoredObjectMetadata:
        """Store bytes and return metadata for the persisted object."""

    @abstractmethod
    async def get_bytes(self, object_address: str) -> bytes | None:
        """Return object bytes, or None when the address does not exist."""

    @abstractmethod
    async def get_metadata(
        self,
        object_address: str,
    ) -> StoredObjectMetadata | None:
        """Return object metadata, or None when the address does not exist."""

    @abstractmethod
    async def exists(self, object_address: str) -> bool:
        """Return whether an object exists at the given address."""


class PgObjectStoreClient(ObjectStoreClient):
    def __init__(self, repository: StoredObjectRepository) -> None:
        self.repository = repository

    async def put_bytes(
        self,
        *,
        content: bytes,
        original_filename: str | None = None,
        content_type: str | None = None,
    ) -> StoredObjectMetadata:
        object_address = self._build_object_address()
        sha256_checksum = self._calculate_sha256_checksum(content)

        stored_object = await self.repository.create_stored_object(
            object_address=object_address,
            original_filename=original_filename,
            content_type=content_type,
            content_size_bytes=len(content),
            sha256_checksum=sha256_checksum,
            content=content,
        )

        return self._build_metadata(stored_object)

    async def get_bytes(self, object_address: str) -> bytes | None:
        stored_object = await self.repository.get_by_object_address(object_address)
        if stored_object is None:
            return None

        return stored_object.content

    async def get_metadata(
        self,
        object_address: str,
    ) -> StoredObjectMetadata | None:
        stored_object = await self.repository.get_by_object_address(object_address)
        if stored_object is None:
            return None

        return self._build_metadata(stored_object)

    async def exists(self, object_address: str) -> bool:
        return await self.repository.object_exists(object_address)

    def _build_object_address(self) -> str:
        return f"stored_objects/{uuid.uuid4()}"

    def _calculate_sha256_checksum(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _build_metadata(self, stored_object: StoredObject) -> StoredObjectMetadata:
        return StoredObjectMetadata(
            object_address=stored_object.object_address,
            original_filename=stored_object.original_filename,
            content_type=stored_object.content_type,
            content_size_bytes=stored_object.content_size_bytes,
            sha256_checksum=stored_object.sha256_checksum,
            created_at=stored_object.created_at,
            updated_at=stored_object.updated_at,
        )
