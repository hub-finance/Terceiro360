"""TERCEIRO360 IGREJAS — núcleo para igrejas e organizações religiosas (§17).

O sistema não presume estrutura eclesiástica: ela é declarada a partir do
ESTATUTO + REGIMENTO INTERNO + MODELO ORGANIZACIONAL DA DENOMINAÇÃO.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.enums import FuncaoEclesiastica, TipoUnidadeEclesiastica
from app.core.types import EnumType, GUID, JSONType


class UnidadeEclesiastica(UUIDMixin, TimestampMixin, Base):
    """Denominação, convenção, igreja, congregação, campo, filial, templo."""

    __tablename__ = "unidades_eclesiasticas"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    tipo: Mapped[TipoUnidadeEclesiastica] = mapped_column(EnumType(TipoUnidadeEclesiastica))
    nome: Mapped[str] = mapped_column(String(200))
    unidade_pai_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("unidades_eclesiasticas.id"))
    # Personalidade jurídica própria? Congregação normalmente não tem.
    possui_cnpj_proprio: Mapped[bool] = mapped_column(Boolean, default=False)
    cnpj: Mapped[str | None] = mapped_column(String(18))
    endereco: Mapped[str | None] = mapped_column(String(300))
    municipio: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    responsavel_pessoa_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("pessoas.id"))
    data_fundacao: Mapped[dt.date | None] = mapped_column(Date)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)

    filhas: Mapped[list["UnidadeEclesiastica"]] = relationship()


class ModeloGovernancaEclesiastica(UUIDMixin, TimestampMixin, Base):
    """Modelo organizacional declarado (episcopal, presbiteral, congregacional,
    convencional, misto). Determina quem convoca, quem elege e quem representa."""

    __tablename__ = "modelos_governanca_eclesiastica"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str | None] = mapped_column(Text)
    denominacao: Mapped[str | None] = mapped_column(String(200))
    convencao: Mapped[str | None] = mapped_column(String(200))
    # {"convoca_assembleia": "PASTOR_PRESIDENTE", "elege_diretoria": "ASSEMBLEIA"}
    regras: Mapped[dict] = mapped_column(JSONType(), default=dict)
    fonte: Mapped[str | None] = mapped_column(String(200))  # estatuto|regimento|convenção
    confirmado: Mapped[bool] = mapped_column(Boolean, default=False)


class Ministro(UUIDMixin, TimestampMixin, Base):
    """Pastor, ministro, presbítero, diácono. Função eclesiástica não se
    confunde com cargo estatutário — as duas coisas convivem."""

    __tablename__ = "ministros"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    pessoa_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("pessoas.id"), index=True)
    unidade_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("unidades_eclesiasticas.id"))
    funcao: Mapped[FuncaoEclesiastica] = mapped_column(EnumType(FuncaoEclesiastica))
    data_ordenacao: Mapped[dt.date | None] = mapped_column(Date)
    credencial: Mapped[str | None] = mapped_column(String(80))
    orgao_credenciador: Mapped[str | None] = mapped_column(String(200))
    situacao: Mapped[str] = mapped_column(String(20), default="ATIVO")
    observacoes: Mapped[str | None] = mapped_column(Text)
