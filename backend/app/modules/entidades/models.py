"""MÓDULO 02 — Cadastro central da entidade (§6). O coração do sistema."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.enums import TipoEntidade
from app.core.types import EnumType, GUID, JSONType


class NaturezaJuridica(UUIDMixin, TimestampMixin, Base):
    """Tabela de naturezas jurídicas (código IBGE/RFB)."""

    __tablename__ = "naturezas_juridicas"

    codigo: Mapped[str] = mapped_column(String(10), unique=True)
    descricao: Mapped[str] = mapped_column(String(200))
    sem_fins_lucrativos: Mapped[bool] = mapped_column(Boolean, default=True)


class Entidade(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "entidades"
    __table_args__ = (UniqueConstraint("cliente_id", "cnpj", name="uq_entidades_cliente_cnpj"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("clientes.id"), index=True)
    codigo_interno: Mapped[str | None] = mapped_column(String(30))

    razao_social: Mapped[str] = mapped_column(String(300))
    nome_fantasia: Mapped[str | None] = mapped_column(String(300))
    cnpj: Mapped[str | None] = mapped_column(String(18), index=True)
    natureza_juridica_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("naturezas_juridicas.id"))
    tipo_entidade: Mapped[TipoEntidade] = mapped_column(EnumType(TipoEntidade), default=TipoEntidade.ASSOCIACAO)

    data_constituicao: Mapped[dt.date | None] = mapped_column(Date)
    data_inscricao_cnpj: Mapped[dt.date | None] = mapped_column(Date)
    cnae_principal: Mapped[str | None] = mapped_column(String(10))
    cnaes_secundarios: Mapped[list] = mapped_column(JSONType(), default=list)

    logradouro: Mapped[str | None] = mapped_column(String(200))
    numero: Mapped[str | None] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(100))
    bairro: Mapped[str | None] = mapped_column(String(100))
    municipio: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    cep: Mapped[str | None] = mapped_column(String(9))

    email: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(30))
    site: Mapped[str | None] = mapped_column(String(255))
    redes_sociais: Mapped[dict] = mapped_column(JSONType(), default=dict)

    situacao_cadastral: Mapped[str | None] = mapped_column(String(40))
    # RCPJ competente (§22). Define quais exigências registrais se aplicam.
    rcpj_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("rcpj.id"))
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="entidades")
    natureza_juridica: Mapped[NaturezaJuridica | None] = relationship()

    @property
    def eclesiastica(self) -> bool:
        return self.tipo_entidade in (TipoEntidade.IGREJA, TipoEntidade.ORGANIZACAO_RELIGIOSA)
