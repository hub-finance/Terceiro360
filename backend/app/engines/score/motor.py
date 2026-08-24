"""SCORE DE CONFORMIDADE / GOVERNANÇA (§30).

Pontuação de 0 a 100 com pesos configuráveis. Cada critério devolve a razão da
nota — score sem explicação é número solto, e número solto não sustenta decisão.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

PESOS_PADRAO: dict[str, int] = {
    "ESTATUTO_ATUALIZADO": 12,
    "PARAMETROS_CONFIRMADOS": 10,
    "DIRETORIA_REGULAR": 15,
    "MANDATO_VIGENTE": 13,
    "ATAS_EM_DIA": 10,
    "PRESTACAO_CONTAS": 12,
    "CONSELHO_FISCAL": 6,
    "DOCUMENTACAO": 8,
    "CERTIDOES": 6,
    "REGISTROS": 8,
}


@dataclass
class Criterio:
    codigo: str
    rotulo: str
    peso: int
    atingido: float          # 0.0 a 1.0
    justificativa: str

    @property
    def pontos(self) -> float:
        return round(self.peso * self.atingido, 2)


@dataclass
class Score:
    pontuacao: float
    classificacao: str
    criterios: list[Criterio] = field(default_factory=list)
    data_referencia: dt.date = field(default_factory=dt.date.today)

    @property
    def cor(self) -> str:
        return {"Excelente": "🟢", "Regular": "🟡", "Atenção": "🟠", "Risco elevado": "🔴"}[
            self.classificacao
        ]

    def to_dict(self) -> dict:
        return {
            "pontuacao": self.pontuacao,
            "classificacao": self.classificacao,
            "cor": self.cor,
            "data_referencia": self.data_referencia.isoformat(),
            "criterios": [
                {
                    "codigo": c.codigo, "rotulo": c.rotulo, "peso": c.peso,
                    "atingido": c.atingido, "pontos": c.pontos,
                    "justificativa": c.justificativa,
                }
                for c in self.criterios
            ],
        }


def classificar(pontuacao: float) -> str:
    if pontuacao >= 90:
        return "Excelente"
    if pontuacao >= 75:
        return "Regular"
    if pontuacao >= 50:
        return "Atenção"
    return "Risco elevado"


@dataclass
class FotografiaEntidade:
    """Dados mínimos para pontuar uma entidade."""

    tem_estatuto_vigente: bool = False
    anos_desde_ultima_alteracao_estatuto: float | None = None
    total_parametros: int = 0
    parametros_confirmados: int = 0
    cargos_obrigatorios: int = 0
    cargos_preenchidos: int = 0
    mandato_vigente: bool = False
    dias_para_fim_mandato: int | None = None
    meses_desde_ultima_assembleia: float | None = None
    exercicios_pendentes_aprovacao: int = 0
    tem_conselho_fiscal: bool | None = None
    conselho_fiscal_preenchido: bool = False
    documentos_obrigatorios: int = 0
    documentos_presentes: int = 0
    certidoes_totais: int = 0
    certidoes_validas: int = 0
    atos_pendentes_registro: int = 0
    atos_registrados: int = 0


def calcular(f: FotografiaEntidade, pesos: dict[str, int] | None = None,
             hoje: dt.date | None = None) -> Score:
    pesos = {**PESOS_PADRAO, **(pesos or {})}
    hoje = hoje or dt.date.today()
    criterios: list[Criterio] = []

    def add(codigo, rotulo, atingido, justificativa):
        criterios.append(Criterio(codigo, rotulo, pesos.get(codigo, 0), max(0.0, min(1.0, atingido)),
                                  justificativa))

    # Estatuto
    if not f.tem_estatuto_vigente:
        add("ESTATUTO_ATUALIZADO", "Estatuto vigente cadastrado", 0.0,
            "Nenhuma versão vigente do estatuto está cadastrada.")
    elif f.anos_desde_ultima_alteracao_estatuto is None:
        add("ESTATUTO_ATUALIZADO", "Estatuto vigente cadastrado", 0.7,
            "Estatuto cadastrado, mas sem data da última alteração.")
    else:
        anos = f.anos_desde_ultima_alteracao_estatuto
        atingido = 1.0 if anos <= 10 else (0.6 if anos <= 20 else 0.3)
        add("ESTATUTO_ATUALIZADO", "Estatuto vigente cadastrado", atingido,
            f"Última alteração há {anos:.0f} ano(s).")

    # Parâmetros confirmados
    if f.total_parametros:
        razao = f.parametros_confirmados / f.total_parametros
        add("PARAMETROS_CONFIRMADOS", "Regras do estatuto confirmadas", razao,
            f"{f.parametros_confirmados} de {f.total_parametros} parâmetros confirmados.")
    else:
        add("PARAMETROS_CONFIRMADOS", "Regras do estatuto confirmadas", 0.0,
            "Nenhum parâmetro estatutário cadastrado.")

    # Diretoria
    if f.cargos_obrigatorios:
        razao = f.cargos_preenchidos / f.cargos_obrigatorios
        add("DIRETORIA_REGULAR", "Diretoria completa", razao,
            f"{f.cargos_preenchidos} de {f.cargos_obrigatorios} cargos obrigatórios preenchidos.")
    else:
        add("DIRETORIA_REGULAR", "Diretoria completa", 0.0, "Nenhum cargo cadastrado.")

    # Mandato
    if not f.mandato_vigente:
        add("MANDATO_VIGENTE", "Mandato vigente", 0.0,
            "Não há mandato vigente na data de hoje.")
    else:
        dias = f.dias_para_fim_mandato
        atingido = 1.0 if dias is None or dias > 90 else (0.6 if dias > 30 else 0.3)
        add("MANDATO_VIGENTE", "Mandato vigente", atingido,
            f"Mandato vigente{f', encerra em {dias} dias' if dias is not None else ''}.")

    # Atas / assembleias
    meses = f.meses_desde_ultima_assembleia
    if meses is None:
        add("ATAS_EM_DIA", "Assembleias em dia", 0.0, "Nenhuma assembleia registrada.")
    else:
        atingido = 1.0 if meses <= 12 else (0.5 if meses <= 24 else 0.0)
        add("ATAS_EM_DIA", "Assembleias em dia", atingido,
            f"Última assembleia há {meses:.0f} meses.")

    # Prestação de contas
    pendentes = f.exercicios_pendentes_aprovacao
    atingido = 1.0 if pendentes == 0 else (0.5 if pendentes == 1 else 0.0)
    add("PRESTACAO_CONTAS", "Contas aprovadas", atingido,
        "Nenhum exercício pendente." if pendentes == 0
        else f"{pendentes} exercício(s) sem aprovação registrada.")

    # Conselho fiscal
    if f.tem_conselho_fiscal is None:
        add("CONSELHO_FISCAL", "Conselho Fiscal", 0.5,
            "Não está cadastrado se o estatuto prevê Conselho Fiscal.")
    elif not f.tem_conselho_fiscal:
        add("CONSELHO_FISCAL", "Conselho Fiscal", 1.0,
            "Estatuto não prevê Conselho Fiscal — critério não aplicável.")
    else:
        add("CONSELHO_FISCAL", "Conselho Fiscal", 1.0 if f.conselho_fiscal_preenchido else 0.0,
            "Conselho Fiscal composto." if f.conselho_fiscal_preenchido
            else "Estatuto prevê Conselho Fiscal, mas não há membros cadastrados.")

    # Documentação
    if f.documentos_obrigatorios:
        razao = f.documentos_presentes / f.documentos_obrigatorios
        add("DOCUMENTACAO", "Documentação essencial", razao,
            f"{f.documentos_presentes} de {f.documentos_obrigatorios} documentos essenciais no acervo.")
    else:
        add("DOCUMENTACAO", "Documentação essencial", 0.5, "Acervo documental não parametrizado.")

    # Certidões
    if f.certidoes_totais:
        razao = f.certidoes_validas / f.certidoes_totais
        add("CERTIDOES", "Certidões válidas", razao,
            f"{f.certidoes_validas} de {f.certidoes_totais} certidões dentro da validade.")
    else:
        add("CERTIDOES", "Certidões válidas", 0.0, "Nenhuma certidão cadastrada.")

    # Registros
    total_atos = f.atos_pendentes_registro + f.atos_registrados
    if total_atos:
        razao = f.atos_registrados / total_atos
        add("REGISTROS", "Atos levados a registro", razao,
            f"{f.atos_pendentes_registro} ato(s) aguardando registro.")
    else:
        add("REGISTROS", "Atos levados a registro", 1.0, "Nenhum ato pendente de registro.")

    peso_total = sum(c.peso for c in criterios) or 1
    pontuacao = round(sum(c.pontos for c in criterios) / peso_total * 100, 2)
    return Score(pontuacao, classificar(pontuacao), criterios, hoje)
