"""MÓDULO 01 — Usuários, perfis e permissões (§5) + multiempresa/multiusuário (§31, §32)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.enums import Plano
from app.core.types import EnumType, GUID, JSONType


class Cliente(UUIDMixin, TimestampMixin, Base):
    """Tenant. Um escritório jurídico/contábil, consultoria ou a própria entidade."""

    __tablename__ = "clientes"

    nome: Mapped[str] = mapped_column(String(200))
    documento: Mapped[str | None] = mapped_column(String(20))
    plano: Mapped[Plano] = mapped_column(EnumType(Plano), default=Plano.BASICO)
    limite_entidades: Mapped[int] = mapped_column(default=1)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="cliente")
    entidades: Mapped[list] = relationship("Entidade", back_populates="cliente")


class Perfil(UUIDMixin, TimestampMixin, Base):
    """Perfil de acesso. `cliente_id` nulo = perfil padrão do sistema."""

    __tablename__ = "perfis"
    __table_args__ = (UniqueConstraint("cliente_id", "codigo", name="uq_perfis_cliente_codigo"),)

    cliente_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("clientes.id"))
    codigo: Mapped[str] = mapped_column(String(50))
    nome: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[str | None] = mapped_column(String(400))
    # Lista de permissões no formato "modulo:recurso:acao" (ex.: "juridico:evento:gerar")
    permissoes: Mapped[list] = mapped_column(JSONType(), default=list)
    exige_habilitacao_profissional: Mapped[bool] = mapped_column(Boolean, default=False)


class Usuario(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "usuarios"

    cliente_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("clientes.id"), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Habilitação profissional — usada pelo módulo de advocacia (§27) e pela
    # camada de responsabilidade profissional (§47).
    registro_profissional: Mapped[str | None] = mapped_column(String(50))  # OAB, CRC
    uf_registro: Mapped[str | None] = mapped_column(String(2))
    ultimo_acesso: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    # Segundo fator (TOTP). O segredo só vira "habilitado" depois que a pessoa
    # prova que conseguiu ler um código do aplicativo — habilitar antes disso
    # tranca o usuário para fora da própria conta.
    mfa_habilitado: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_segredo: Mapped[str | None] = mapped_column(String(64))
    mfa_confirmado_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # Guardados como hash, como senha: quem lê o banco não recupera os códigos.
    mfa_codigos_recuperacao: Mapped[list] = mapped_column(JSONType(), default=list)
    senha_alterada_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    cliente: Mapped[Cliente] = relationship(back_populates="usuarios")
    vinculos: Mapped[list["UsuarioPerfil"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class UsuarioPerfil(UUIDMixin, TimestampMixin, Base):
    """Vínculo usuário↔perfil, opcionalmente restrito a uma entidade (§5)."""

    __tablename__ = "usuario_perfis"
    __table_args__ = (
        UniqueConstraint("usuario_id", "perfil_id", "entidade_id", name="uq_usuario_perfil_entidade"),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("usuarios.id"), index=True)
    perfil_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("perfis.id"))
    # Nulo = vale para todas as entidades do cliente.
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("entidades.id"))
    data_inicio: Mapped[dt.date | None] = mapped_column(Date)
    data_fim: Mapped[dt.date | None] = mapped_column(Date)

    usuario: Mapped[Usuario] = relationship(back_populates="vinculos")
    perfil: Mapped[Perfil] = relationship()
