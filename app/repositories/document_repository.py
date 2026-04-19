from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import DocumentAuditLog, IdentityDocument


class DocumentRepository:
    def create(self, db: Session, **kwargs: Any) -> IdentityDocument:
        document = IdentityDocument(**kwargs)
        db.add(document)
        db.flush()
        db.refresh(document)
        return document

    def get_by_id(self, db: Session, document_id: int) -> IdentityDocument | None:
        stmt = select(IdentityDocument).where(IdentityDocument.id == document_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_latest_by_user_id(self, db: Session, user_id: int) -> IdentityDocument | None:
        stmt = (
            select(IdentityDocument)
            .where(IdentityDocument.user_id == user_id)
            .order_by(desc(IdentityDocument.created_at), desc(IdentityDocument.id))
        )
        return db.execute(stmt).scalars().first()

    def count_audit_events(self, db: Session, document_id: int, action: str) -> int:
        stmt = select(func.count(DocumentAuditLog.id)).where(
            DocumentAuditLog.document_id == document_id,
            DocumentAuditLog.action == action,
        )
        return int(db.execute(stmt).scalar_one())

    def update(self, db: Session, document: IdentityDocument, **kwargs: Any) -> IdentityDocument:
        for key, value in kwargs.items():
            setattr(document, key, value)
        db.add(document)
        db.flush()
        db.refresh(document)
        return document
