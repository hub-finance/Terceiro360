"""TERCEIRO360 GOVERNANÇA — score de conformidade e linha do tempo (§30, §42)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.types import GUID, JSONType


class ConfiguracaoScore(UUIDMixin, TimestampMixin, Base):
    """§30 — os pesos do score são configuráveis por cliente."""

    __tablename__ = "configuracoes_score"

    cliente_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("clientes.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120), default="Padrão TERCEIRO360")
    # {"estatuto_atualizado": 12, "diretoria_regular": 15, ...}
    pesos: Mapped[dict] = mapped_column(JSONType(), default=dict)
    ativa: Mapped[bool] = mapped_column(Integer, default=1)


class ScoreSnapshot(UUIDMixin, TimestampMixin, Base):
    """Fotografia do score numa data — permite acompanhar evolução."""

    __tablename__ = "score_snapshots"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    data_referencia: Mapped[dt.date] = mapped_column(Date, index=True)
    pontuacao: Mapped[float] = mapped_column(Numeric(5, 2))
    classificacao: Mapped[str] = mapped_column(String(20))
    criterios: Mapped[list] = mapped_column(JSONType(), default=list)
    configuracao_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("configuracoes_score.id"))


class EventoLinhaTempo(UUIDMixin, TimestampMixin, Base):
    """§42 — linha do tempo jurídica da entidade."""

    __tablename__ = "linha_tempo"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    data: Mapped[dt.date] = mapped_column(Date, index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)
    evento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("eventos.id"))
    protocolo_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("protocolos.id"))
    documentos: Mapped[list] = mapped_column(JSONType(), default=list)
