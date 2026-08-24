"""Contexto de validação — a fotografia do caso concreto (§12).

Estruturas simples, sem ORM: os checks são funções puras sobre este contexto,
o que os torna testáveis isoladamente e reaproveitáveis fora da API.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.core.enums import TipoEntidade
from app.engines.conformidade.resolucao import ResolvedorParametros


@dataclass
class EntidadeInfo:
    id: str
    razao_social: str
    tipo_entidade: TipoEntidade = TipoEntidade.ASSOCIACAO
    cnpj: str | None = None
    municipio: str | None = None
    uf: str | None = None
    data_constituicao: dt.date | None = None


@dataclass
class EstatutoInfo:
    versao: int
    vigente: bool = True
    data_estatuto: dt.date | None = None
    data_registro: dt.date | None = None
    numero_registro: str | None = None
    livro: str | None = None
    folha: str | None = None
    total_parametros: int = 0
    parametros_confirmados: int = 0


@dataclass
class MembroInfo:
    pessoa_id: str
    nome: str
    cargo: str
    cargo_codigo: str | None = None
    situacao: str = "ATIVO"


@dataclass
class MandatoInfo:
    id: str
    orgao: str
    designacao: str
    data_inicio: dt.date
    data_fim: dt.date
    encerrado: bool = False
    membros: list[MembroInfo] = field(default_factory=list)

    def vigente_em(self, data: dt.date) -> bool:
        return not self.encerrado and self.data_inicio <= data <= self.data_fim

    def ocupante(self, cargo_codigo: str) -> MembroInfo | None:
        return next(
            (m for m in self.membros if (m.cargo_codigo or "").upper() == cargo_codigo.upper()), None
        )


@dataclass
class RegraRCPJInfo:
    tipo_evento: str
    documentos_exigidos: list[dict] = field(default_factory=list)
    exige_reconhecimento_firma: bool | None = None
    exige_visto_advogado: bool | None = None
    vias: int | None = None
    fonte_informacao: str | None = None
    data_ultima_verificacao: dt.date | None = None


@dataclass
class RCPJInfo:
    id: str
    nome: str
    uf: str
    municipio: str
    exige_reconhecimento_firma: bool | None = None
    exige_visto_advogado: bool | None = None
    data_ultima_verificacao: dt.date | None = None
    regras_desatualizadas: bool = False
    regra_evento: RegraRCPJInfo | None = None


@dataclass
class ImpactoNormativoInfo:
    """Alerta vindo do motor de atualização normativa (§38)."""

    alvo_tipo: str
    alvo_ref: str
    severidade: str
    descricao: str
    norma: str | None = None


@dataclass
class ContextoValidacao:
    entidade: EntidadeInfo
    tipo_evento: str
    resolvedor: ResolvedorParametros
    data_ato: dt.date | None = None
    hoje: dt.date = field(default_factory=dt.date.today)
    dados: dict = field(default_factory=dict)
    estatuto: EstatutoInfo | None = None
    mandatos: list[MandatoInfo] = field(default_factory=list)
    total_associados: int = 0
    associados_aptos: int = 0
    rcpj: RCPJInfo | None = None
    documentos_anexados: set[str] = field(default_factory=set)
    impactos_normativos: list[ImpactoNormativoInfo] = field(default_factory=list)

    # --------------------------------------------------------------- helpers

    @property
    def data_efetiva(self) -> dt.date:
        return self.data_ato or self.hoje

    def mandato_vigente(self, orgao: str = "DIRETORIA") -> MandatoInfo | None:
        candidatos = [
            m for m in self.mandatos
            if m.orgao.upper() == orgao.upper() and m.vigente_em(self.data_efetiva)
        ]
        return max(candidatos, key=lambda m: m.data_inicio) if candidatos else None

    def mandato_mais_recente(self, orgao: str = "DIRETORIA") -> MandatoInfo | None:
        candidatos = [m for m in self.mandatos if m.orgao.upper() == orgao.upper()]
        return max(candidatos, key=lambda m: m.data_fim) if candidatos else None

    def param(self, chave: str):
        return self.resolvedor.resolver(chave)

    def dado(self, chave: str, padrao=None):
        return self.dados.get(chave, padrao)
