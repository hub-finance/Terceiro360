"""TERCEIRO360 IA — camada auxiliar de análise documental (§37).

A IA propõe; o responsável confirma. Toda extração nasce como sugestão
com grau de confiança e trecho de origem, e só vira parâmetro válido depois
de confirmada por um usuário (§46, §49).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.types import GUID, JSONType


class AnaliseIA(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analises_ia"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    documento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documentos.id"))
    estatuto_versao_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("estatuto_versoes.id"))
    tipo: Mapped[str] = mapped_column(String(50))  # EXTRACAO_ESTATUTO|COMPARACAO|RESUMO|CHECKLIST
    modelo: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="CONCLUIDA")
    resumo: Mapped[str | None] = mapped_column(Text)
    solicitado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    concluida_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    sugestoes: Mapped[list["SugestaoIA"]] = relationship(
        back_populates="analise", cascade="all, delete-orphan"
    )


class SugestaoIA(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sugestoes_ia"

    analise_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("analises_ia.id"), index=True)
    chave: Mapped[str] = mapped_column(String(80), index=True)
    valor_sugerido: Mapped[str | None] = mapped_column(String(400))
    dispositivo: Mapped[str | None] = mapped_column(String(120))
    trecho: Mapped[str | None] = mapped_column(Text)
    confianca: Mapped[float | None] = mapped_column(Numeric(4, 3))
    # Quando a IA não tem segurança: VALIDACAO_NECESSARIA + o que confirmar (§37).
    status: Mapped[str] = mapped_column(String(30), default="SUGERIDA")
    pergunta_validacao: Mapped[str | None] = mapped_column(String(400))
    aceita_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    aceita_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    metadados: Mapped[dict] = mapped_column(JSONType(), default=dict)

    analise: Mapped[AnaliseIA] = relationship(back_populates="sugestoes")
