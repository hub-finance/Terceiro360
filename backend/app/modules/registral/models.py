"""Motor de RCPJ, protocolos e checklists registrais (§22, §23)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.enums import StatusProtocolo
from app.core.types import GUID, JSONType


class RCPJ(UUIDMixin, TimestampMixin, Base):
    """§22 — ESTADO → MUNICÍPIO → RCPJ. Regras alimentadas manualmente e
    versionadas; o sistema nunca presume exigência de cartório (§46)."""

    __tablename__ = "rcpj"

    uf: Mapped[str] = mapped_column(String(2), index=True)
    municipio: Mapped[str] = mapped_column(String(120), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    endereco: Mapped[str | None] = mapped_column(String(300))
    site: Mapped[str | None] = mapped_column(String(255))
    contato: Mapped[str | None] = mapped_column(String(200))
    forma_protocolo: Mapped[str | None] = mapped_column(String(120))  # presencial|eletrônico|híbrido
    formatos_aceitos: Mapped[list] = mapped_column(JSONType(), default=list)
    exige_reconhecimento_firma: Mapped[bool | None] = mapped_column(Boolean)
    exige_visto_advogado: Mapped[bool | None] = mapped_column(Boolean)
    observacoes: Mapped[str | None] = mapped_column(Text)
    fonte_informacao: Mapped[str | None] = mapped_column(String(300))
    atualizado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    data_ultima_verificacao: Mapped[dt.date | None] = mapped_column(Date)
    # Periodicidade esperada de reconferência das regras cartorárias.
    validade_regras_dias: Mapped[int] = mapped_column(Integer, default=180)

    regras: Mapped[list["RegraRCPJ"]] = relationship(back_populates="rcpj", cascade="all, delete-orphan")

    def regras_desatualizadas_em(self, hoje: dt.date) -> bool:
        if not self.data_ultima_verificacao:
            return True
        return (hoje - self.data_ultima_verificacao).days > self.validade_regras_dias


class RegraRCPJ(UUIDMixin, TimestampMixin, Base):
    """Exigências do cartório por tipo de ato."""

    __tablename__ = "regras_rcpj"

    rcpj_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("rcpj.id"), index=True)
    tipo_evento: Mapped[str] = mapped_column(String(40), index=True)
    # [{codigo, descricao, obrigatorio, vias, observacao}]
    documentos_exigidos: Mapped[list] = mapped_column(JSONType(), default=list)
    vias: Mapped[int | None] = mapped_column(Integer)
    exige_reconhecimento_firma: Mapped[bool | None] = mapped_column(Boolean)
    exige_visto_advogado: Mapped[bool | None] = mapped_column(Boolean)
    custas_estimadas: Mapped[float | None] = mapped_column(Numeric(12, 2))
    prazo_estimado_dias: Mapped[int | None] = mapped_column(Integer)
    observacoes: Mapped[str | None] = mapped_column(Text)
    vigente_desde: Mapped[dt.date | None] = mapped_column(Date)
    fonte_informacao: Mapped[str | None] = mapped_column(String(300))
    data_ultima_verificacao: Mapped[dt.date | None] = mapped_column(Date)

    rcpj: Mapped[RCPJ] = relationship(back_populates="regras")


class Protocolo(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "protocolos"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    evento_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("eventos.id"), index=True)
    rcpj_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("rcpj.id"))
    numero: Mapped[str | None] = mapped_column(String(60))
    data_protocolo: Mapped[dt.date | None] = mapped_column(Date)
    status: Mapped[StatusProtocolo] = mapped_column(String(20), default=StatusProtocolo.PREPARACAO)
    # [{descricao, prazo, cumprida, data}]
    exigencias: Mapped[list] = mapped_column(JSONType(), default=list)
    data_registro: Mapped[dt.date | None] = mapped_column(Date)
    numero_registro: Mapped[str | None] = mapped_column(String(60))
    livro: Mapped[str | None] = mapped_column(String(30))
    folha: Mapped[str | None] = mapped_column(String(30))
    custas: Mapped[float | None] = mapped_column(Numeric(12, 2))
    observacoes: Mapped[str | None] = mapped_column(Text)


class Checklist(UUIDMixin, TimestampMixin, Base):
    """§23 — checklist montado dinamicamente por ato."""

    __tablename__ = "checklists"

    evento_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("eventos.id"), index=True)
    rcpj_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("rcpj.id"))
    gerado_em: Mapped[dt.datetime | None] = mapped_column()

    itens: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="checklist", cascade="all, delete-orphan", order_by="ChecklistItem.ordem"
    )


class ChecklistItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "checklist_itens"

    checklist_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("checklists.id"), index=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    codigo: Mapped[str] = mapped_column(String(80))
    descricao: Mapped[str] = mapped_column(String(300))
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=True)
    origem: Mapped[str] = mapped_column(String(20), default="SISTEMA")  # LEI|ESTATUTO|RCPJ|SISTEMA
    fundamento: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="PENDENTE")  # PENDENTE|OK|NAO_APLICAVEL
    documento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documentos.id"))

    checklist: Mapped[Checklist] = relationship(back_populates="itens")
