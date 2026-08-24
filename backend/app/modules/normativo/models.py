"""CENTRAL DE FONTES JURÍDICAS + MOTOR DE ATUALIZAÇÃO NORMATIVA (§4, §38, §46).

A base legal do sistema não é código-fonte: é dado versionado, datado e
curado por um responsável humano. Este módulo garante que:

1. toda conclusão jurídica cite a *versão* da norma vigente na data do ato;
2. mudanças na legislação sejam detectadas, triadas e publicadas com curadoria;
3. o sistema saiba exatamente o que foi impactado por cada mudança;
4. nenhuma norma entre em vigor no motor sem aprovação de um responsável.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.enums import (
    AlvoImpacto,
    Jurisdicao,
    OrigemDeteccao,
    SeveridadeImpacto,
    SituacaoAtualizacao,
    SituacaoVersaoNorma,
    TipoFonte,
)
from app.core.types import GUID, JSONType


class FonteJuridica(UUIDMixin, TimestampMixin, Base):
    """Uma norma: lei, decreto, norma contábil, provimento ou regra de RCPJ."""

    __tablename__ = "fontes_juridicas"
    __table_args__ = (UniqueConstraint("chave", name="uq_fonte_chave"),)

    chave: Mapped[str] = mapped_column(String(60), index=True)          # "CC_2002"
    identificacao: Mapped[str] = mapped_column(String(200))             # "Lei nº 10.406/2002"
    apelido: Mapped[str | None] = mapped_column(String(200))            # "Código Civil"
    tipo: Mapped[TipoFonte] = mapped_column(String(30), default=TipoFonte.LEI)
    jurisdicao: Mapped[Jurisdicao] = mapped_column(String(20), default=Jurisdicao.FEDERAL)
    uf: Mapped[str | None] = mapped_column(String(2))
    municipio: Mapped[str | None] = mapped_column(String(120))
    orgao_emissor: Mapped[str | None] = mapped_column(String(200))
    url_oficial: Mapped[str | None] = mapped_column(String(500))
    ementa: Mapped[str | None] = mapped_column(Text)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)

    versoes: Mapped[list["FonteVersao"]] = relationship(
        back_populates="fonte", cascade="all, delete-orphan", order_by="FonteVersao.numero_versao"
    )

    def versao_vigente_em(self, data: dt.date) -> "FonteVersao | None":
        """A redação que valia numa data — o ato de 2024 é julgado pela lei de 2024."""
        candidatas = [
            v
            for v in self.versoes
            if v.situacao in (SituacaoVersaoNorma.VIGENTE, SituacaoVersaoNorma.SUPERADA)
            and v.vigente_desde
            and v.vigente_desde <= data
            and (v.vigente_ate is None or v.vigente_ate >= data)
        ]
        return max(candidatas, key=lambda v: v.vigente_desde) if candidatas else None


class FonteVersao(UUIDMixin, TimestampMixin, Base):
    """Uma redação datada da norma. Só vale no motor quando VIGENTE e curada."""

    __tablename__ = "fonte_versoes"
    __table_args__ = (UniqueConstraint("fonte_id", "numero_versao", name="uq_fonte_versao_numero"),)

    fonte_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("fontes_juridicas.id"), index=True)
    numero_versao: Mapped[int] = mapped_column(Integer, default=1)
    situacao: Mapped[SituacaoVersaoNorma] = mapped_column(String(20), default=SituacaoVersaoNorma.RASCUNHO)
    vigente_desde: Mapped[dt.date | None] = mapped_column(Date, index=True)
    vigente_ate: Mapped[dt.date | None] = mapped_column(Date)
    publicado_em: Mapped[dt.date | None] = mapped_column(Date)
    resumo_alteracao: Mapped[str | None] = mapped_column(Text)
    texto_referencia: Mapped[str | None] = mapped_column(Text)
    url_captura: Mapped[str | None] = mapped_column(String(500))
    hash_conteudo: Mapped[str | None] = mapped_column(String(64))
    origem_captura: Mapped[OrigemDeteccao] = mapped_column(String(20), default=OrigemDeteccao.MANUAL)

    # Curadoria humana obrigatória — sem isto a versão não entra em vigor (§46).
    curado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    curado_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    registro_profissional_curador: Mapped[str | None] = mapped_column(String(30))

    fonte: Mapped[FonteJuridica] = relationship(back_populates="versoes")
    dispositivos: Mapped[list["Dispositivo"]] = relationship(
        back_populates="versao", cascade="all, delete-orphan"
    )

    @property
    def curada(self) -> bool:
        return self.curado_por_id is not None and self.curado_em is not None

    @property
    def citacao(self) -> str:
        return f"{self.fonte.identificacao} (redação vigente desde {self.vigente_desde:%d/%m/%Y})" if self.vigente_desde else self.fonte.identificacao


class Dispositivo(UUIDMixin, TimestampMixin, Base):
    """Artigo, parágrafo, inciso ou item citável de uma versão da norma (§38)."""

    __tablename__ = "dispositivos"
    __table_args__ = (UniqueConstraint("versao_id", "identificacao", name="uq_dispositivo_versao_id"),)

    versao_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("fonte_versoes.id"), index=True)
    identificacao: Mapped[str] = mapped_column(String(120), index=True)  # "art. 59, I"
    texto: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONType(), default=list)  # ["quorum", "destituicao"]
    revogado: Mapped[bool] = mapped_column(Boolean, default=False)

    versao: Mapped[FonteVersao] = relationship(back_populates="dispositivos")

    @property
    def referencia_completa(self) -> str:
        return f"{self.versao.fonte.identificacao}, {self.identificacao}"


class VinculoNormativo(UUIDMixin, TimestampMixin, Base):
    """Liga um artefato do sistema (regra de validação, template, checklist,
    regra de RCPJ) ao dispositivo que o fundamenta.

    É este vínculo que permite responder, quando uma lei muda: *o que exatamente
    parou de valer?*
    """

    __tablename__ = "vinculos_normativos"
    __table_args__ = (
        UniqueConstraint("alvo_tipo", "alvo_ref", "fonte_chave", "dispositivo", name="uq_vinculo_alvo_fonte"),
    )

    alvo_tipo: Mapped[AlvoImpacto] = mapped_column(String(30), index=True)
    alvo_ref: Mapped[str] = mapped_column(String(120), index=True)  # código da regra/template
    fonte_chave: Mapped[str] = mapped_column(String(60), index=True)
    dispositivo: Mapped[str | None] = mapped_column(String(120))
    observacao: Mapped[str | None] = mapped_column(String(400))


class MonitoramentoNormativo(UUIDMixin, TimestampMixin, Base):
    """O "dispositivo de atualização": uma vigília por fonte.

    Guarda o endereço oficial, a periodicidade de reconferência e a última
    impressão digital do conteúdo. Quando não existe fonte oficial consultável
    de forma automatizada — o caso da maioria dos RCPJ — o monitoramento vira
    tarefa de reconferência manual, com responsável e prazo (§35).
    """

    __tablename__ = "monitoramentos_normativos"

    fonte_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("fontes_juridicas.id"), index=True)
    rcpj_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("rcpj.id"), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(500))
    modo: Mapped[str] = mapped_column(String(20), default="MANUAL")  # HTTP|MANUAL
    seletor: Mapped[str | None] = mapped_column(String(200))
    periodicidade_dias: Mapped[int] = mapped_column(Integer, default=30)
    ultima_verificacao: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_hash: Mapped[str | None] = mapped_column(String(64))
    ultimo_erro: Mapped[str | None] = mapped_column(String(400))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    fonte: Mapped[FonteJuridica | None] = relationship()

    def vencido_em(self, agora: dt.datetime) -> bool:
        if not self.ativo:
            return False
        if self.ultima_verificacao is None:
            return True
        return (agora - self.ultima_verificacao).days >= self.periodicidade_dias


class AtualizacaoNormativa(UUIDMixin, TimestampMixin, Base):
    """Uma possível mudança na base legal, da detecção até a publicação.

    DETECTADA → EM_ANALISE → APROVADA → PUBLICADA (ou DESCARTADA).
    Só a publicação altera o que o motor de validação enxerga.
    """

    __tablename__ = "atualizacoes_normativas"

    fonte_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("fontes_juridicas.id"), index=True)
    rcpj_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("rcpj.id"))
    monitoramento_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("monitoramentos_normativos.id")
    )
    origem: Mapped[OrigemDeteccao] = mapped_column(String(25), default=OrigemDeteccao.MANUAL)
    situacao: Mapped[SituacaoAtualizacao] = mapped_column(
        String(20), default=SituacaoAtualizacao.DETECTADA, index=True
    )
    titulo: Mapped[str] = mapped_column(String(300))
    resumo: Mapped[str | None] = mapped_column(Text)
    # O que mudou, em texto — nunca inferido pelo sistema sem evidência.
    diff: Mapped[str | None] = mapped_column(Text)
    url_evidencia: Mapped[str | None] = mapped_column(String(500))
    hash_anterior: Mapped[str | None] = mapped_column(String(64))
    hash_novo: Mapped[str | None] = mapped_column(String(64))
    detectado_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    analisado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    parecer_curadoria: Mapped[str | None] = mapped_column(Text)
    publicado_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    fonte_versao_gerada_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("fonte_versoes.id"))

    impactos: Mapped[list["ImpactoNormativo"]] = relationship(
        back_populates="atualizacao", cascade="all, delete-orphan"
    )


class ImpactoNormativo(UUIDMixin, TimestampMixin, Base):
    """O que a mudança atinge: regras, templates, checklists, atos em curso."""

    __tablename__ = "impactos_normativos"

    atualizacao_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("atualizacoes_normativas.id"), index=True
    )
    alvo_tipo: Mapped[AlvoImpacto] = mapped_column(String(30))
    alvo_ref: Mapped[str] = mapped_column(String(120))
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("entidades.id"))
    severidade: Mapped[SeveridadeImpacto] = mapped_column(
        String(25), default=SeveridadeImpacto.REVISAO_RECOMENDADA
    )
    descricao: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="ABERTO")  # ABERTO|TRATADO|DISPENSADO
    tratado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    tratado_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    atualizacao: Mapped[AtualizacaoNormativa] = relationship(back_populates="impactos")
