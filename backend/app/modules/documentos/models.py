"""TERCEIRO360 DOCUMENTOS — templates, geração, versionamento e assinatura
(§14, §15, §16, §19, §20, §28)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.enums import (
    CategoriaDocumento,
    StatusAssinatura,
    StatusDocumento,
    TipoAssinatura,
    TipoDocumento,
)
from app.core.types import GUID, JSONType


class Template(UUIDMixin, TimestampMixin, Base):
    """§15/§16 — modelo com variáveis e regras condicionais.

    `cliente_id` nulo = template padrão do TERCEIRO360.
    """

    __tablename__ = "templates"
    __table_args__ = (UniqueConstraint("cliente_id", "codigo", "versao", name="uq_template_codigo_versao"),)

    cliente_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("clientes.id"))
    codigo: Mapped[str] = mapped_column(String(80), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    tipo_documento: Mapped[TipoDocumento] = mapped_column(String(40))
    # Restrições de aplicabilidade: tipos de entidade e tipos de evento.
    tipos_entidade: Mapped[list] = mapped_column(JSONType(), default=list)
    tipos_evento: Mapped[list] = mapped_column(JSONType(), default=list)
    uf: Mapped[str | None] = mapped_column(String(2))
    corpo: Mapped[str] = mapped_column(Text)
    variaveis: Mapped[list] = mapped_column(JSONType(), default=list)
    versao: Mapped[int] = mapped_column(Integer, default=1)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Dispositivos normativos que sustentam o modelo (§38). Alimenta o cálculo
    # de impacto do motor de atualização normativa.
    fundamentos: Mapped[list] = mapped_column(JSONType(), default=list)


class Documento(UUIDMixin, TimestampMixin, Base):
    """§19 — repositório documental por entidade."""

    __tablename__ = "documentos"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    evento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("eventos.id"), index=True)
    tipo: Mapped[TipoDocumento] = mapped_column(String(40))
    categoria: Mapped[CategoriaDocumento] = mapped_column(String(30), default=CategoriaDocumento.OUTRO)
    titulo: Mapped[str] = mapped_column(String(300))
    data_documento: Mapped[dt.date | None] = mapped_column(Date)
    status: Mapped[StatusDocumento] = mapped_column(String(20), default=StatusDocumento.RASCUNHO, index=True)
    versao_atual: Mapped[int] = mapped_column(Integer, default=0)
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    protocolo_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("protocolos.id"))
    observacoes: Mapped[str | None] = mapped_column(Text)
    # Campos preenchidos automaticamente quando o documento é gerado por template.
    template_codigo: Mapped[str | None] = mapped_column(String(80))
    origem: Mapped[str] = mapped_column(String(20), default="GERADO")  # GERADO|UPLOAD|IMPORTADO

    versoes: Mapped[list["DocumentoVersao"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan", order_by="DocumentoVersao.numero"
    )
    assinaturas: Mapped[list["Assinatura"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan"
    )


class DocumentoVersao(UUIDMixin, TimestampMixin, Base):
    """§20 — controle de versão: nunca substituir silenciosamente."""

    __tablename__ = "documento_versoes"
    __table_args__ = (UniqueConstraint("documento_id", "numero", name="uq_documento_versao_numero"),)

    documento_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("documentos.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer, default=1)
    conteudo: Mapped[str | None] = mapped_column(Text)
    arquivo_path: Mapped[str | None] = mapped_column(String(500))
    formato: Mapped[str] = mapped_column(String(10), default="html")  # html|docx|pdf
    hash_conteudo: Mapped[str | None] = mapped_column(String(64))
    template_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("templates.id"))
    # Fotografia dos dados usados na geração — garante reprodutibilidade.
    dados_snapshot: Mapped[dict] = mapped_column(JSONType(), default=dict)
    # Variáveis que ficaram sem valor: viram "DADO NÃO INFORMADO" no texto (§46).
    lacunas: Mapped[list] = mapped_column(JSONType(), default=list)
    # Versões das normas citadas no momento da geração (§38).
    fundamentos: Mapped[list] = mapped_column(JSONType(), default=list)
    gerado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    motivo: Mapped[str | None] = mapped_column(String(400))

    documento: Mapped[Documento] = relationship(back_populates="versoes")


class Assinatura(UUIDMixin, TimestampMixin, Base):
    """§28 — arquitetura preparada para assinatura eletrônica/ICP-Brasil."""

    __tablename__ = "assinaturas"

    documento_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("documentos.id"), index=True)
    documento_versao_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documento_versoes.id"))
    pessoa_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("pessoas.id"))
    nome_signatario: Mapped[str] = mapped_column(String(200))
    papel: Mapped[str | None] = mapped_column(String(120))  # presidente|secretário|advogado|testemunha
    tipo: Mapped[TipoAssinatura] = mapped_column(String(20), default=TipoAssinatura.FISICA)
    status: Mapped[StatusAssinatura] = mapped_column(String(20), default=StatusAssinatura.PENDENTE)
    exige_reconhecimento_firma: Mapped[bool] = mapped_column(Boolean, default=False)
    data_assinatura: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    provedor: Mapped[str | None] = mapped_column(String(60))
    # Evidências do provedor externo. Nunca preenchido pelo sistema por conta própria (§46).
    evidencia: Mapped[dict] = mapped_column(JSONType(), default=dict)

    documento: Mapped[Documento] = relationship(back_populates="assinaturas")


class Certidao(UUIDMixin, TimestampMixin, Base):
    """Certidões e documentos com validade — alimentam o motor de prazos (§21)."""

    __tablename__ = "certidoes"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(120))
    orgao_emissor: Mapped[str | None] = mapped_column(String(150))
    numero: Mapped[str | None] = mapped_column(String(80))
    data_emissao: Mapped[dt.date | None] = mapped_column(Date)
    data_validade: Mapped[dt.date | None] = mapped_column(Date, index=True)
    documento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documentos.id"))
    observacoes: Mapped[str | None] = mapped_column(String(400))
