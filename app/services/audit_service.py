from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import DocumentAuditLog, IdentityDocument


class AuditService:
    def log_document_action(
        self,
        *,
        db: Session,
        document: IdentityDocument,
        action: str,
        details: dict | None = None,
    ) -> DocumentAuditLog:
        audit_log = DocumentAuditLog(
            document_id=document.id,
            action=action,
            details=details,
        )
        db.add(audit_log)
        db.flush()
        return audit_log

    def count_retries(self, db: Session, document_id: int) -> int:
        from sqlalchemy import func, select
        stmt = select(func.count(DocumentAuditLog.id)).where(
            DocumentAuditLog.document_id == document_id,
            DocumentAuditLog.action == "document_retry",
        )
        return int(db.execute(stmt).scalar_one())
