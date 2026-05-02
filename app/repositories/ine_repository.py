"""Repository for documentos_ine_mexico table."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.documento_ine import DocumentoINEMexico


class INERepository:
    def create(
        self,
        db: Session,
        *,
        usuario_id: int,
        nombre: str | None = None,
        apellido_paterno: str | None = None,
        apellido_materno: str | None = None,
        nombre_completo: str | None = None,
        nacionalidad: str | None = None,
        fecha_nacimiento: date | None = None,
        curp: str | None = None,
        domicilio: str | None = None,
        ocr_texto_original: str | None = None,
        ocr_confianza: float | None = None,
        imagen_frontal_url: str | None = None,
        fecha_captura: datetime | None = None,
        creado_por: str | None = None,
    ) -> DocumentoINEMexico:
        record = DocumentoINEMexico(
            usuario_id=usuario_id,
            nombre=nombre,
            apellido_paterno=apellido_paterno,
            apellido_materno=apellido_materno,
            nombre_completo=nombre_completo,
            nacionalidad=nacionalidad,
            fecha_nacimiento=fecha_nacimiento,
            curp=curp,
            domicilio=domicilio,
            ocr_texto_original=ocr_texto_original,
            ocr_confianza=ocr_confianza,
            imagen_frontal_url=imagen_frontal_url,
            fecha_captura=fecha_captura,
            creado_por=creado_por,
        )
        db.add(record)
        db.flush()
        db.refresh(record)
        return record

    def get_by_id(self, db: Session, record_id: int) -> DocumentoINEMexico | None:
        stmt = select(DocumentoINEMexico).where(DocumentoINEMexico.id == record_id)
        return db.execute(stmt).scalars().first()

    def get_by_user_id(self, db: Session, usuario_id: int) -> list[DocumentoINEMexico]:
        stmt = (
            select(DocumentoINEMexico)
            .where(DocumentoINEMexico.usuario_id == usuario_id)
            .order_by(DocumentoINEMexico.created_at.desc())
        )
        return list(db.execute(stmt).scalars().all())

    def get_latest_by_user_id(self, db: Session, usuario_id: int) -> DocumentoINEMexico | None:
        stmt = (
            select(DocumentoINEMexico)
            .where(DocumentoINEMexico.usuario_id == usuario_id)
            .order_by(DocumentoINEMexico.created_at.desc())
        )
        return db.execute(stmt).scalars().first()
