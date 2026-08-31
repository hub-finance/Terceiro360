"""Módulo de prazos, pendências e notificações (§21, §43)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.enums import Prioridade, StatusPendencia, StatusPrazo, TipoPrazo
from app.core.types import EnumType, GUID, JSONType

# §21 — janelas de alerta padrão. Parametrizáveis por cliente.
JANELAS_ALERTA_PADRAO = [90, 60, 30, 15, 7, 3, 1]


class Prazo(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "prazos"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    tipo: Mapped[TipoPrazo] = mapped_column(EnumType(TipoPrazo), index=True)
    descricao: Mapped[str] = mapped_column(String(300))
    data_base: Mapped[dt.date | None] = mapped_column(Date)
    data_limite: Mapped[dt.date] = mapped_column(Date, index=True)
    # §21 — prazos nunca presumidos: sempre com origem e fundamento declarados.
    origem: Mapped[str] = mapped_column(String(20), default="MANUAL")  # LEI|ESTATUTO|RCPJ|MANUAL
    fundamento: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[StatusPrazo] = mapped_column(EnumType(StatusPrazo), default=StatusPrazo.ABERTO, index=True)
    janelas_alerta: Mapped[list] = mapped_column(JSONType(), default=lambda: list(JANELAS_ALERTA_PADRAO))
    alertas_disparados: Mapped[list] = mapped_column(JSONType(), default=list)
    evento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("eventos.id"))
    mandato_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("mandatos.id"))
    protocolo_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("protocolos.id"))
    certidao_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("certidoes.id"))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    chave_idempotencia: Mapped[str | None] = mapped_column(String(120), index=True)

    def dias_restantes(self, hoje: dt.date) -> int:
        return (self.data_limite - hoje).days


class Pendencia(UUIDMixin, TimestampMixin, Base):
    """§43 — central de pendências.

    `entidade_id` nulo = pendência do sistema (ex.: triagem de uma mudança
    normativa que afeta toda a base, não uma entidade específica).
    """

    __tablename__ = "pendencias"

    entidade_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("entidades.id"), index=True, nullable=True
    )
    evento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("eventos.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(50))
    codigo: Mapped[str | None] = mapped_column(String(80), index=True)
    descricao: Mapped[str] = mapped_column(String(400))
    detalhamento: Mapped[str | None] = mapped_column(Text)
    prioridade: Mapped[Prioridade] = mapped_column(EnumType(Prioridade), default=Prioridade.MEDIA, index=True)
    status: Mapped[StatusPendencia] = mapped_column(EnumType(StatusPendencia), default=StatusPendencia.ABERTA, index=True)
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    prazo_limite: Mapped[dt.date | None] = mapped_column(Date)
    resolvida_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    origem: Mapped[str] = mapped_column(String(30), default="VALIDACAO")


class Notificacao(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notificacoes"

    usuario_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("usuarios.id"), index=True)
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("entidades.id"))
    prazo_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("prazos.id"))
    pendencia_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("pendencias.id"))
    canal: Mapped[str] = mapped_column(String(20), default="SISTEMA")  # SISTEMA|EMAIL|WHATSAPP
    titulo: Mapped[str] = mapped_column(String(200))
    mensagem: Mapped[str | None] = mapped_column(Text)
    lida: Mapped[bool] = mapped_column(Boolean, default=False)
    enviada_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
