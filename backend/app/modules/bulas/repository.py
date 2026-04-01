from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.bulas.models import Document

async def create_document(db: AsyncSession, name: str) -> Document:
    document = Document(name=name)
    db.add(document)
    await db.flush()
    await db.refresh(document)
    return document