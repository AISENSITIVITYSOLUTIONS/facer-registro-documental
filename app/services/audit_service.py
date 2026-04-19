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
