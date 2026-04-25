from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class StoredObjectRef:
    object_address: str
    original_filename: str | None
    content_type: str | None
    content_size_bytes: int
    sha256_checksum: str
    created_at: datetime
    updated_at: datetime
