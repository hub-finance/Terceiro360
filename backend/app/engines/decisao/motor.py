"""MOTOR DE DECISÃO (§39).

Responde perguntas objetivas sobre um ato — sempre em três partes:

    RESULTADO (🟢/🟡/🔴)  +  JUSTIFICATIVA  +  FUNDAMENTAÇÃO

Cada pergunta é respondida pelos mesmos checks que validam o ato; não há uma
segunda lógica paralela que possa divergir da primeira.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.enums import Semaforo, StatusParametro
from app.engines.base import Achado, Fundamento
from app.engines.validacao.contexto import ContextoValidacao
from app.engines.validacao.motor import validar
from app.engines.validacao.registro import REGISTRO


@dataclass
class Resposta:
    pergunta: str
    resultado: Semaforo
    justificativa: str
    fundamentos: list[Fundamento] = field(default_factory=list)
    achados: list[Achado] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pergunta": self.pergunta,
            "resultado": self.resultado.value,
            "icone": self.resultado.icone,
            "rotulo": {"APTO": "APTO", "PENDENCIA": "NECESSITA ANÁLISE",
                       "BLOQUEADO": "NÃO APTO"}[self.resultado.value],
            "justificativa": self.justificativa,
            "fundamentacao": [str(f) for f in self.fundamentos],
            "achados": [a.to_dict() for a in self.achados],
        }


# Pergunta → checks que a respondem.
PERGUNTAS: dict[str, tuple[str, tuple[str, ...]]] = {
    "assembleia_pode_ser_realizada": (
        "Essa assembleia pode ser realizada?",
        ("ESTATUTO_VIGENTE", "PARAMETROS_ESTATUTARIOS", "CONVOCACAO_PRAZO",
         "CONVOCACAO_LEGITIMIDADE", "COMPETENCIA_ORGAO", "QUORUM_INSTALACAO", "MANDATO_VIGENTE"),
    ),
    "edital_no_prazo": ("O edital foi convocado dentro do prazo?", ("CONVOCACAO_PRAZO",)),
    "existe_quorum": ("Existe quórum?", ("QUORUM_INSTALACAO", "QUORUM_DELIBERACAO")),
    "quem_pode_convocar": ("Quem pode convocar?", ("CONVOCACAO_LEGITIMIDADE",)),
    "mandato_vigente": ("O mandato está vigente?", ("MANDATO_VIGENTE",)),
    "exige_reforma_estatutaria": ("Essa alteração exige reforma estatutária?", ("COMPETENCIA_ORGAO",)),
    "existe_pendencia": ("Existe alguma pendência?", ()),
    "documentos_necessarios": ("Quais documentos precisam ser gerados?", ()),
}


def responder(ctx: ContextoValidacao, pergunta: str) -> Resposta:
    if pergunta not in PERGUNTAS:
        raise KeyError(f"Pergunta desconhecida: {pergunta}")
    enunciado, codigos = PERGUNTAS[pergunta]

    resultado_completo = validar(ctx)
    if codigos:
        relevantes = [
            a for a in resultado_completo.achados
            if a.codigo.split("::")[0] in _codigos_derivados(codigos)
        ]
    else:
        relevantes = resultado_completo.achados

    severidade = (
        max((a.severidade for a in relevantes), key=lambda s: s.peso) if relevantes else Semaforo.APTO
    )
    fundamentos: list[Fundamento] = []
    for a in relevantes:
        for f in a.fundamentos:
            if f not in fundamentos:
                fundamentos.append(f)

    return Resposta(
        pergunta=enunciado,
        resultado=severidade,
        justificativa=_justificar(pergunta, severidade, relevantes, ctx),
        fundamentos=fundamentos,
        achados=relevantes,
    )


def responder_tudo(ctx: ContextoValidacao) -> list[Resposta]:
    return [responder(ctx, chave) for chave in PERGUNTAS]


def _codigos_derivados(codigos: tuple[str, ...]) -> set[str]:
    """Um check pode emitir vários códigos de achado; mapeia todos."""
    derivados: set[str] = set()
    for codigo in codigos:
        derivados.add(codigo)
        check = REGISTRO.get(codigo)
        if check:
            derivados.update(_ACHADOS_POR_CHECK.get(codigo, ()))
    return derivados


_ACHADOS_POR_CHECK: dict[str, tuple[str, ...]] = {
    "ESTATUTO_VIGENTE": ("ESTATUTO_NAO_CADASTRADO", "ESTATUTO_SEM_VERSAO_VIGENTE",
                         "ESTATUTO_SEM_REGISTRO"),
    "PARAMETROS_ESTATUTARIOS": ("PARAMETRO_AUSENTE", "PARAMETRO_NAO_CONFIRMADO",
                                "PARAMETRO_CONFLITANTE"),
    "CONVOCACAO_PRAZO": ("CONVOCACAO_SEM_DATA", "CONVOCACAO_PRAZO_INSUFICIENTE"),
    "CONVOCACAO_LEGITIMIDADE": ("CONVOCANTE_NAO_INFORMADO", "CONVOCANTE_SEM_PREVISAO"),
    "COMPETENCIA_ORGAO": ("ORDEM_DO_DIA_AUSENTE", "MATERIA_FORA_DA_ORDEM_DO_DIA"),
    "QUORUM_INSTALACAO": ("QUORUM_INSTALACAO_OK", "QUORUM_INSTALACAO_INSUFICIENTE",
                          "QUORUM_SEM_BASE_DE_CALCULO", "QUORUM_NAO_INTERPRETAVEL"),
    "QUORUM_DELIBERACAO": ("QUORUM_DELIBERACAO_INSUFICIENTE",),
    "MANDATO_VIGENTE": ("MANDATO_EXPIRADO", "MANDATO_A_VENCER", "MANDATO_INEXISTENTE"),
}


def _justificar(pergunta: str, severidade: Semaforo, achados: list[Achado],
                ctx: ContextoValidacao) -> str:
    if pergunta == "quem_pode_convocar":
        p = ctx.param("CONVOCACAO_LEGITIMADOS")
        if p.status is StatusParametro.CONFIRMADO:
            legitimados = p.valor if isinstance(p.valor, (list, tuple)) else [p.valor]
            return ("Segundo o estatuto cadastrado, podem convocar: "
                    + ", ".join(map(str, legitimados))
                    + ". A lei ainda garante a 1/5 dos associados o direito de promover a "
                      "convocação.")
        return ("O estatuto cadastrado não informa quem pode convocar. Confirme o parâmetro "
                "antes de emitir o edital.")

    if pergunta == "documentos_necessarios":
        from app.engines.checklist.motor import montar

        checklist = montar(ctx)
        obrigatorios = [i.descricao for i in checklist.itens if i.obrigatorio]
        return "Documentos exigidos para este ato: " + "; ".join(obrigatorios) + "."

    if severidade is Semaforo.APTO:
        return "Nenhuma inconsistência encontrada nos pontos verificados."

    bloqueios = [a for a in achados if a.severidade is Semaforo.BLOQUEADO]
    if bloqueios:
        return " ".join(f"{a.titulo}: {a.mensagem}" for a in bloqueios[:3])
    return " ".join(f"{a.titulo}: {a.mensagem}" for a in achados[:3])
