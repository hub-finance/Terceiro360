"""TERCEIRO360 JURÍDICO — estatuto, órgãos, quadro diretivo, associados,
assembleias e o motor de eventos (§7 a §12, §24, §27, §41, §42)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
    UniqueConstraint, event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.enums import (
    Convocacao,
    OrigemDado,
    Semaforo,
    SituacaoAssociado,
    SituacaoMembro,
    StatusEvento,
    StatusParecer,
    TipoAssembleia,
    TipoEvento,
    TipoOrgao,
)
from app.core.cifra import indice
from app.core.types import DadoCifrado, EnumType, GUID, JSONType


# ---------------------------------------------------------------- Pessoas


class Pessoa(UUIDMixin, TimestampMixin, Base):
    """Pessoa natural. Dados pessoais sujeitos à LGPD (§33)."""

    __tablename__ = "pessoas"
    # A unicidade migra para o índice: com o CPF cifrado, duas gravações do
    # mesmo número produzem textos diferentes e a restrição não pegaria nada.
    __table_args__ = (
        UniqueConstraint("cliente_id", "cpf_indice", name="uq_pessoas_cliente_cpf"),
    )

    cliente_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("clientes.id"), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    # Cifrados em repouso. O texto cifrado muda a cada gravação, então quem
    # procura por CPF procura pelo índice cego abaixo, nunca por esta coluna.
    cpf: Mapped[str | None] = mapped_column(DadoCifrado(200))
    cpf_indice: Mapped[str | None] = mapped_column(String(64), index=True)
    rg: Mapped[str | None] = mapped_column(DadoCifrado(200))
    orgao_expedidor: Mapped[str | None] = mapped_column(String(20))
    nacionalidade: Mapped[str | None] = mapped_column(String(60))
    estado_civil: Mapped[str | None] = mapped_column(String(40))
    profissao: Mapped[str | None] = mapped_column(String(100))
    data_nascimento: Mapped[dt.date | None] = mapped_column(Date)

    logradouro: Mapped[str | None] = mapped_column(String(200))
    numero: Mapped[str | None] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(100))
    bairro: Mapped[str | None] = mapped_column(String(100))
    municipio: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    cep: Mapped[str | None] = mapped_column(String(9))
    email: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(30))

    # LGPD: base legal do tratamento e consentimento quando aplicável.
    base_legal_tratamento: Mapped[str | None] = mapped_column(String(60))
    consentimento_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def qualificacao(self) -> str:
        """Qualificação civil usada nos documentos (§15)."""
        partes = [p for p in (self.nacionalidade, self.estado_civil, self.profissao) if p]
        doc = []
        if self.rg:
            doc.append(f"portador do RG nº {self.rg}" + (f"/{self.orgao_expedidor}" if self.orgao_expedidor else ""))
        if self.cpf:
            doc.append(f"inscrito no CPF sob o nº {self.cpf}")
        return ", ".join(partes + doc)


# ---------------------------------------------------------------- Estatuto


@event.listens_for(Pessoa, "before_insert")
@event.listens_for(Pessoa, "before_update")
def _manter_indice_do_cpf(_mapper, _conexao, pessoa: "Pessoa") -> None:
    """Mantém o índice cego em dia sozinho.

    Deixar isso a cargo de quem grava significaria que uma rotina nova, um
    script de importação ou um seed esqueceriam — e o esquecimento não dá erro:
    só faz a busca por CPF não achar e a restrição de duplicata não pegar.
    """
    pessoa.cpf_indice = indice(pessoa.cpf)


class Estatuto(UUIDMixin, TimestampMixin, Base):
    """§7 — o estatuto vira dado parametrizável, não apenas um PDF."""

    __tablename__ = "estatutos"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    versao_vigente_id: Mapped[uuid.UUID | None] = mapped_column(GUID())

    versoes: Mapped[list["EstatutoVersao"]] = relationship(
        back_populates="estatuto", cascade="all, delete-orphan", foreign_keys="EstatutoVersao.estatuto_id"
    )


class EstatutoVersao(UUIDMixin, TimestampMixin, Base):
    """§20 — nunca substituir silenciosamente: cada redação é uma versão."""

    __tablename__ = "estatuto_versoes"
    __table_args__ = (UniqueConstraint("estatuto_id", "numero_versao", name="uq_estatuto_versao"),)

    estatuto_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("estatutos.id"), index=True)
    numero_versao: Mapped[int] = mapped_column(Integer, default=1)
    data_estatuto: Mapped[dt.date | None] = mapped_column(Date)
    data_registro: Mapped[dt.date | None] = mapped_column(Date)
    numero_registro: Mapped[str | None] = mapped_column(String(50))
    livro: Mapped[str | None] = mapped_column(String(30))
    folha: Mapped[str | None] = mapped_column(String(30))
    rcpj_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("rcpj.id"))
    municipio: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    texto: Mapped[str | None] = mapped_column(Text)
    documento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documentos.id"))
    vigente: Mapped[bool] = mapped_column(Boolean, default=False)
    evento_origem_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("eventos.id"))
    motivo_alteracao: Mapped[str | None] = mapped_column(String(400))

    estatuto: Mapped[Estatuto] = relationship(back_populates="versoes", foreign_keys=[estatuto_id])
    parametros: Mapped[list["EstatutoParametro"]] = relationship(
        back_populates="versao", cascade="all, delete-orphan"
    )


class EstatutoParametro(UUIDMixin, TimestampMixin, Base):
    """Cada regra estatutária extraída vira um parâmetro auditável.

    Nada é presumido: um parâmetro só é usado nas validações depois de
    `confirmado` por um usuário responsável (§46, §49).
    """

    __tablename__ = "estatuto_parametros"
    __table_args__ = (UniqueConstraint("versao_id", "chave", name="uq_parametro_versao_chave"),)

    versao_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("estatuto_versoes.id"), index=True)
    chave: Mapped[str] = mapped_column(String(80), index=True)
    valor: Mapped[str | None] = mapped_column(String(400))
    tipo_valor: Mapped[str] = mapped_column(String(20), default="texto")  # texto|inteiro|decimal|booleano|fracao|data
    unidade: Mapped[str | None] = mapped_column(String(30))  # dias|meses|anos|percentual|fracao
    dispositivo: Mapped[str | None] = mapped_column(String(120))  # ex.: "art. 21, §2º"
    trecho: Mapped[str | None] = mapped_column(Text)
    origem: Mapped[OrigemDado] = mapped_column(EnumType(OrigemDado), default=OrigemDado.ESTATUTO)
    confianca: Mapped[float | None] = mapped_column(Numeric(4, 3))  # preenchida pela IA (§37)
    confirmado: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    confirmado_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    observacao: Mapped[str | None] = mapped_column(String(400))

    versao: Mapped[EstatutoVersao] = relationship(back_populates="parametros")


# ---------------------------------------------------------------- Órgãos e cargos


class Orgao(UUIDMixin, TimestampMixin, Base):
    """§7/§18 — órgãos da entidade, hierarquizados."""

    __tablename__ = "orgaos"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    nome: Mapped[str] = mapped_column(String(150))
    codigo: Mapped[str | None] = mapped_column(String(50))
    tipo: Mapped[TipoOrgao] = mapped_column(EnumType(TipoOrgao), default=TipoOrgao.EXECUTIVO)
    orgao_pai_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("orgaos.id"))
    competencias: Mapped[list] = mapped_column(JSONType(), default=list)
    dispositivo_estatutario: Mapped[str | None] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    cargos: Mapped[list["Cargo"]] = relationship(back_populates="orgao", cascade="all, delete-orphan")
    filhos: Mapped[list["Orgao"]] = relationship()


class Cargo(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cargos"

    orgao_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("orgaos.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    codigo: Mapped[str | None] = mapped_column(String(50))
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=True)
    vagas: Mapped[int] = mapped_column(Integer, default=1)
    poderes_representacao: Mapped[str | None] = mapped_column(Text)
    forma_assinatura: Mapped[str | None] = mapped_column(String(200))
    dispositivo_estatutario: Mapped[str | None] = mapped_column(String(120))

    orgao: Mapped[Orgao] = relationship(back_populates="cargos")


# ---------------------------------------------------------------- Mandatos


class Mandato(UUIDMixin, TimestampMixin, Base):
    """§41 — a diretoria anterior nunca é apagada; vira histórico de gestão."""

    __tablename__ = "mandatos"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    orgao_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("orgaos.id"))
    designacao: Mapped[str] = mapped_column(String(60))  # "GESTÃO 2024–2026"
    data_inicio: Mapped[dt.date] = mapped_column(Date)
    data_fim: Mapped[dt.date] = mapped_column(Date)
    evento_origem_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("eventos.id"))
    encerrado: Mapped[bool] = mapped_column(Boolean, default=False)

    membros: Mapped[list["MandatoMembro"]] = relationship(
        back_populates="mandato", cascade="all, delete-orphan"
    )
    orgao: Mapped[Orgao] = relationship()

    def vigente_em(self, data: dt.date) -> bool:
        return not self.encerrado and self.data_inicio <= data <= self.data_fim


class MandatoMembro(UUIDMixin, TimestampMixin, Base):
    """§8 — PESSOA → CARGO → MANDATO → ATA → REGISTRO."""

    __tablename__ = "mandato_membros"

    mandato_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("mandatos.id"), index=True)
    pessoa_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("pessoas.id"), index=True)
    cargo_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("cargos.id"))
    data_inicio: Mapped[dt.date] = mapped_column(Date)
    data_fim: Mapped[dt.date | None] = mapped_column(Date)
    situacao: Mapped[SituacaoMembro] = mapped_column(EnumType(SituacaoMembro), default=SituacaoMembro.ATIVO)
    documento_eleicao_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documentos.id"))
    documento_posse_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documentos.id"))
    protocolo_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("protocolos.id"))
    observacoes: Mapped[str | None] = mapped_column(String(400))

    mandato: Mapped[Mandato] = relationship(back_populates="membros")
    pessoa: Mapped[Pessoa] = relationship()
    cargo: Mapped[Cargo] = relationship()


# ---------------------------------------------------------------- Associados


class Associado(UUIDMixin, TimestampMixin, Base):
    """§9 — quem pode votar, quem está impedido, quem conta para o quórum."""

    __tablename__ = "associados"
    __table_args__ = (UniqueConstraint("entidade_id", "pessoa_id", name="uq_associado_entidade_pessoa"),)

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    pessoa_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("pessoas.id"), index=True)
    categoria: Mapped[str | None] = mapped_column(String(60))  # fundador|efetivo|contribuinte|honorário|membro
    data_admissao: Mapped[dt.date | None] = mapped_column(Date)
    situacao: Mapped[SituacaoAssociado] = mapped_column(EnumType(SituacaoAssociado), default=SituacaoAssociado.ATIVO)
    direito_voto: Mapped[bool] = mapped_column(Boolean, default=True)
    elegivel: Mapped[bool] = mapped_column(Boolean, default=True)
    data_suspensao: Mapped[dt.date | None] = mapped_column(Date)
    data_desligamento: Mapped[dt.date | None] = mapped_column(Date)
    observacoes: Mapped[str | None] = mapped_column(String(400))

    pessoa: Mapped[Pessoa] = relationship()

    def apto_a_votar_em(self, data: dt.date) -> bool:
        if not self.direito_voto or self.situacao is not SituacaoAssociado.ATIVO:
            return False
        if self.data_admissao and self.data_admissao > data:
            return False
        if self.data_desligamento and self.data_desligamento <= data:
            return False
        if self.data_suspensao and self.data_suspensao <= data:
            return False
        return True


# ---------------------------------------------------------------- Eventos


class Evento(UUIDMixin, TimestampMixin, Base):
    """§10 — motor de eventos. Cada ato jurídico/administrativo é um evento
    com fluxo próprio (§3)."""

    __tablename__ = "eventos"

    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    tipo: Mapped[TipoEvento] = mapped_column(EnumType(TipoEvento), index=True)
    titulo: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[StatusEvento] = mapped_column(EnumType(StatusEvento), default=StatusEvento.RASCUNHO, index=True)
    data_referencia: Mapped[dt.date | None] = mapped_column(Date)
    # Respostas do questionário inteligente (§11).
    dados: Mapped[dict] = mapped_column(JSONType(), default=dict)
    # Último resultado do motor de validação (§12/§13).
    semaforo: Mapped[Semaforo | None] = mapped_column(EnumType(Semaforo))
    validado_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    resultado_validacao: Mapped[dict] = mapped_column(JSONType(), default=dict)
    criado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    observacoes: Mapped[str | None] = mapped_column(Text)

    assembleia: Mapped["Assembleia | None"] = relationship(back_populates="evento", uselist=False)


class Assembleia(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assembleias"

    evento_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("eventos.id"), index=True)
    entidade_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("entidades.id"), index=True)
    tipo: Mapped[TipoAssembleia] = mapped_column(EnumType(TipoAssembleia), default=TipoAssembleia.EXTRAORDINARIA)
    data_hora: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    local: Mapped[str | None] = mapped_column(String(300))
    convocacao: Mapped[Convocacao] = mapped_column(EnumType(Convocacao), default=Convocacao.PRIMEIRA)
    hora_segunda_convocacao: Mapped[str | None] = mapped_column(String(10))
    total_aptos: Mapped[int | None] = mapped_column(Integer)
    total_presentes: Mapped[int | None] = mapped_column(Integer)
    presidida_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("pessoas.id"))
    secretariada_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("pessoas.id"))
    ordem_do_dia: Mapped[list] = mapped_column(JSONType(), default=list)

    evento: Mapped[Evento] = relationship(back_populates="assembleia")
    convocacoes: Mapped[list["ConvocacaoAto"]] = relationship(
        back_populates="assembleia", cascade="all, delete-orphan"
    )
    deliberacoes: Mapped[list["Deliberacao"]] = relationship(
        back_populates="assembleia", cascade="all, delete-orphan"
    )
    presencas: Mapped[list["Presenca"]] = relationship(
        back_populates="assembleia", cascade="all, delete-orphan"
    )


class ConvocacaoAto(UUIDMixin, TimestampMixin, Base):
    """Edital/aviso/comunicação que convocou a assembleia (§14)."""

    __tablename__ = "convocacoes"

    assembleia_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("assembleias.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(40), default="EDITAL")
    data_publicacao: Mapped[dt.date] = mapped_column(Date)
    meio: Mapped[str | None] = mapped_column(String(120))  # mural|jornal|e-mail|site|aplicativo
    convocado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("pessoas.id"))
    orgao_convocante_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("orgaos.id"))
    documento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documentos.id"))

    assembleia: Mapped[Assembleia] = relationship(back_populates="convocacoes")


class Presenca(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "listas_presenca"

    assembleia_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("assembleias.id"), index=True)
    pessoa_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("pessoas.id"))
    apto_a_votar: Mapped[bool] = mapped_column(Boolean, default=True)
    representado_por_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("pessoas.id"))
    procuracao_documento_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("documentos.id"))

    assembleia: Mapped[Assembleia] = relationship(back_populates="presencas")
    pessoa: Mapped[Pessoa] = relationship(foreign_keys=[pessoa_id])


class Deliberacao(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "deliberacoes"

    assembleia_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("assembleias.id"), index=True)
    ordem: Mapped[int] = mapped_column(Integer, default=1)
    materia: Mapped[str] = mapped_column(String(400))
    chave_quorum: Mapped[str | None] = mapped_column(String(80))  # liga à regra estatutária aplicável
    votos_favor: Mapped[int | None] = mapped_column(Integer)
    votos_contra: Mapped[int | None] = mapped_column(Integer)
    abstencoes: Mapped[int | None] = mapped_column(Integer)
    aprovada: Mapped[bool | None] = mapped_column(Boolean)
    texto_deliberacao: Mapped[str | None] = mapped_column(Text)

    assembleia: Mapped[Assembleia] = relationship(back_populates="deliberacoes")


# ---------------------------------------------------------------- Parecer jurídico


class ParecerJuridico(UUIDMixin, TimestampMixin, Base):
    """§27 — módulo de advocacia; §47 — responsabilidade profissional."""

    __tablename__ = "pareceres_juridicos"

    evento_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("eventos.id"), index=True)
    responsavel_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("usuarios.id"))
    registro_oab: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[StatusParecer] = mapped_column(EnumType(StatusParecer), default=StatusParecer.EM_ANALISE)
    texto: Mapped[str | None] = mapped_column(Text)
    ressalvas: Mapped[str | None] = mapped_column(Text)
    data_parecer: Mapped[dt.date | None] = mapped_column(Date)
    assinatura_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("assinaturas.id"))
