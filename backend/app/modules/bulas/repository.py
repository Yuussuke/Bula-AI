from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.bulas.models import Document

class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str) -> Document:
        document = Document(name=name)
        self.db.add(document)
        
        try:
            await self.db.commit()
            
            await self.db.refresh(document)
            
            return document
            
        except Exception as e:
            await self.db.rollback()
            raise e