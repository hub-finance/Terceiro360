"""Trilhas de auditoria, logs de acesso e evidências (§5, §33)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.tempo import agora
from app.core.types import GUID, JSONType


class LogAcesso(UUIDMixin, Base):
    __tablename__ = "logs"

    usuario_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"), index=True)
    acao: Mapped[str] = mapped_column(String(80))
    recurso: Mapped[str | None] = mapped_column(String(200))
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("entidades.id"))
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    resultado: Mapped[str] = mapped_column(String(20), default="OK")
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora, index=True)


class RegistroAuditoria(UUIDMixin, Base):
    """Quem alterou, quando, o quê e por quê (§20)."""

    __tablename__ = "auditoria"

    entidade_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    tabela: Mapped[str] = mapped_column(String(80), index=True)
    registro_id: Mapped[str] = mapped_column(String(60), index=True)
    operacao: Mapped[str] = mapped_column(String(20))  # INSERT|UPDATE|DELETE
    antes: Mapped[dict | None] = mapped_column(JSONType())
    depois: Mapped[dict | None] = mapped_column(JSONType())
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    motivo: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=agora, index=True)
