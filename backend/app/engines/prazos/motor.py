"""MOTOR DE PRAZOS — calendário jurídico e alertas (§21).

Regra dura: prazo que depende do estatuto ou de regra local **nunca** é
presumido. Se o parâmetro não está confirmado, o motor não inventa a data —
gera uma pendência dizendo o que falta confirmar.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from app.core.enums import Prioridade, TipoPrazo
from app.engines.base import ParametroResolvido

JANELAS_PADRAO = (90, 60, 30, 15, 7, 3, 1)


@dataclass
class PrazoCalculado:
    chave: str                     # idempotência: recalcular não duplica
    tipo: TipoPrazo
    descricao: str
    data_limite: dt.date
    origem: str                    # LEI|ESTATUTO|RCPJ|MANUAL
    fundamento: str | None = None
    data_base: dt.date | None = None
    referencia_id: str | None = None
    janelas: tuple[int, ...] = JANELAS_PADRAO

    def dias_restantes(self, hoje: dt.date) -> int:
        return (self.data_limite - hoje).days

    def vencido(self, hoje: dt.date) -> bool:
        return self.data_limite < hoje

    def prioridade(self, hoje: dt.date) -> Prioridade:
        dias = self.dias_restantes(hoje)
        if dias < 0 or dias <= 3:
            return Prioridade.URGENTE
        if dias <= 15:
            return Prioridade.ALTA
        if dias <= 60:
            return Prioridade.MEDIA
        return Prioridade.BAIXA

    def janela_ativa(self, hoje: dt.date) -> int | None:
        """A menor janela de alerta já atingida."""
        dias = self.dias_restantes(hoje)
        if dias < 0:
            return 0
        atingidas = [j for j in self.janelas if dias <= j]
        return min(atingidas) if atingidas else None


@dataclass
class PendenciaCalculada:
    codigo: str
    descricao: str
    prioridade: Prioridade = Prioridade.MEDIA
    detalhamento: str | None = None


@dataclass
class AgendaEntidade:
    prazos: list[PrazoCalculado] = field(default_factory=list)
    pendencias: list[PendenciaCalculada] = field(default_factory=list)

    def alertas(self, hoje: dt.date) -> list[tuple[PrazoCalculado, int]]:
        resultado = []
        for p in self.prazos:
            janela = p.janela_ativa(hoje)
            if janela is not None:
                resultado.append((p, janela))
        return sorted(resultado, key=lambda t: t[0].data_limite)


@dataclass
class MandatoParaPrazo:
    id: str
    designacao: str
    orgao: str
    data_fim: dt.date
    encerrado: bool = False


@dataclass
class CertidaoParaPrazo:
    id: str
    tipo: str
    data_validade: dt.date | None


@dataclass
class ExigenciaParaPrazo:
    protocolo_id: str
    descricao: str
    prazo: dt.date | None
    cumprida: bool = False


def gerar_agenda(
    hoje: dt.date,
    mandatos: list[MandatoParaPrazo] | None = None,
    certidoes: list[CertidaoParaPrazo] | None = None,
    exigencias: list[ExigenciaParaPrazo] | None = None,
    ultima_assembleia_ordinaria: dt.date | None = None,
    periodicidade_ago: ParametroResolvido | None = None,
    prazo_aprovacao_contas: ParametroResolvido | None = None,
    exercicios_pendentes: list[int] | None = None,
) -> AgendaEntidade:
    agenda = AgendaEntidade()

    # 1. Fim de mandato e renovação da diretoria.
    for m in mandatos or []:
        if m.encerrado:
            continue
        agenda.prazos.append(PrazoCalculado(
            chave=f"FIM_MANDATO::{m.id}",
            tipo=TipoPrazo.FIM_MANDATO,
            descricao=f"Encerramento do mandato — {m.orgao} ({m.designacao})",
            data_limite=m.data_fim,
            origem="ESTATUTO",
            fundamento="Prazo de mandato cadastrado no estatuto",
            referencia_id=m.id,
        ))
        agenda.prazos.append(PrazoCalculado(
            chave=f"RENOVACAO::{m.id}",
            tipo=TipoPrazo.RENOVACAO_DIRETORIA,
            descricao=f"Realizar eleição para suceder a gestão {m.designacao}",
            # Convenção operacional explícita: a eleição precisa acontecer até o
            # fim do mandato. A antecedência recomendada vira alerta, não prazo novo.
            data_limite=m.data_fim,
            origem="ESTATUTO",
            fundamento="Decorre do prazo de mandato cadastrado",
            referencia_id=m.id,
        ))

    # 2. Assembleia ordinária — só quando a periodicidade está confirmada.
    if ultima_assembleia_ordinaria:
        if periodicidade_ago is not None and periodicidade_ago.utilizavel:
            meses = int(periodicidade_ago.valor)
            proxima = _somar_meses(ultima_assembleia_ordinaria, meses)
            agenda.prazos.append(PrazoCalculado(
                chave="ASSEMBLEIA_ORDINARIA",
                tipo=TipoPrazo.ASSEMBLEIA_ANUAL,
                descricao=f"Próxima assembleia ordinária (a cada {meses} meses)",
                data_limite=proxima,
                data_base=ultima_assembleia_ordinaria,
                origem="ESTATUTO",
                fundamento=str(periodicidade_ago.fundamento) if periodicidade_ago.fundamento else None,
            ))
        else:
            agenda.pendencias.append(PendenciaCalculada(
                codigo="PERIODICIDADE_AGO_NAO_CONFIRMADA",
                descricao="Periodicidade da assembleia ordinária não confirmada",
                prioridade=Prioridade.MEDIA,
                detalhamento="Sem esse parâmetro o sistema não calcula a data da próxima "
                             "assembleia ordinária. Confirme em Estatuto → Parâmetros.",
            ))

    # 3. Prestação de contas dos exercícios em aberto.
    for ano in exercicios_pendentes or []:
        if prazo_aprovacao_contas is not None and prazo_aprovacao_contas.utilizavel:
            limite = _interpretar_prazo_contas(prazo_aprovacao_contas.valor, ano + 1)
            if limite:
                agenda.prazos.append(PrazoCalculado(
                    chave=f"PRESTACAO_CONTAS::{ano}",
                    tipo=TipoPrazo.PRESTACAO_CONTAS,
                    descricao=f"Aprovar as contas do exercício de {ano}",
                    data_limite=limite,
                    origem="ESTATUTO",
                    fundamento=str(prazo_aprovacao_contas.fundamento)
                    if prazo_aprovacao_contas.fundamento else None,
                ))
                continue
        agenda.pendencias.append(PendenciaCalculada(
            codigo=f"PRAZO_CONTAS_NAO_DEFINIDO::{ano}",
            descricao=f"Prazo de aprovação das contas de {ano} não definido",
            prioridade=Prioridade.ALTA,
            detalhamento="O estatuto define até quando as contas devem ser aprovadas. "
                         "O sistema não arbitra essa data.",
        ))

    # 4. Certidões.
    for c in certidoes or []:
        if c.data_validade is None:
            agenda.pendencias.append(PendenciaCalculada(
                codigo=f"CERTIDAO_SEM_VALIDADE::{c.id}",
                descricao=f"Certidão “{c.tipo}” sem data de validade cadastrada",
                prioridade=Prioridade.BAIXA,
            ))
            continue
        agenda.prazos.append(PrazoCalculado(
            chave=f"CERTIDAO::{c.id}",
            tipo=TipoPrazo.CERTIDAO,
            descricao=f"Renovar certidão: {c.tipo}",
            data_limite=c.data_validade,
            origem="MANUAL",
            referencia_id=c.id,
            janelas=(30, 15, 7, 3, 1),
        ))

    # 5. Exigências de cartório.
    for e in exigencias or []:
        if e.cumprida:
            continue
        if e.prazo is None:
            agenda.pendencias.append(PendenciaCalculada(
                codigo=f"EXIGENCIA_SEM_PRAZO::{e.protocolo_id}",
                descricao=f"Exigência sem prazo cadastrado: {e.descricao}",
                prioridade=Prioridade.ALTA,
            ))
            continue
        agenda.prazos.append(PrazoCalculado(
            chave=f"EXIGENCIA::{e.protocolo_id}::{abs(hash(e.descricao)) % 10**8}",
            tipo=TipoPrazo.EXIGENCIA,
            descricao=f"Cumprir exigência do cartório: {e.descricao}",
            data_limite=e.prazo,
            origem="RCPJ",
            referencia_id=e.protocolo_id,
            janelas=(15, 7, 3, 1),
        ))

    agenda.prazos.sort(key=lambda p: p.data_limite)
    return agenda


def _somar_meses(data: dt.date, meses: int) -> dt.date:
    ano = data.year + (data.month - 1 + meses) // 12
    mes = (data.month - 1 + meses) % 12 + 1
    dias_no_mes = [31, 29 if _bissexto(ano) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1]
    return dt.date(ano, mes, min(data.day, dias_no_mes))


def _bissexto(ano: int) -> bool:
    return ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)


_MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


def _interpretar_prazo_contas(valor, ano: int) -> dt.date | None:
    """Lê expressões como "até 30 de abril" ou "31/03". Devolve None se não
    interpretar com segurança — e aí o motor gera pendência, não uma data."""
    import re

    if isinstance(valor, dt.date):
        return valor
    texto = str(valor).strip().lower()

    m = re.search(r"(\d{1,2})\s*(?:de\s*)?([a-zçã]+)", texto)
    if m and m.group(2) in _MESES:
        return dt.date(ano, _MESES[m.group(2)], int(m.group(1)))

    m = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", texto)
    if m:
        return dt.date(ano, int(m.group(2)), int(m.group(1)))

    if "quadrimestre" in texto:
        return dt.date(ano, 4, 30)
    if "trimestre" in texto:
        return dt.date(ano, 3, 31)
    if "semestre" in texto:
        return dt.date(ano, 6, 30)
    return None
