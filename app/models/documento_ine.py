"""Model for the documentos_ine_mexico table."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DocumentoINEMexico(Base):
    __tablename__ = "documentos_ine_mexico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    nombre: Mapped[str | None] = mapped_column(String(120), nullable=True)
    apellido_paterno: Mapped[str | None] = mapped_column(String(120), nullable=True)
    apellido_materno: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nombre_completo: Mapped[str | None] = mapped_column(String(250), nullable=True)
    nacionalidad: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    curp: Mapped[str | None] = mapped_column(String(18), nullable=True)
    domicilio: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_texto_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confianza: Mapped[float | None] = mapped_column(Float, nullable=True)
    imagen_frontal_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_captura: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    creado_por: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
