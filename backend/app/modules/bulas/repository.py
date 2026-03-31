from sqlalchemy.orm import Session
from app.modules.bulas.models import Document


def create_document(db: Session, name: str):
    document = Document(name=name)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document