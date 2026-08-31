"""Extração de regras a partir do texto do estatuto (§37, §49).

Duas estratégias, na ordem:

1. **Leitura determinística** — expressões regulares sobre o vocabulário
   jurídico usual em estatutos brasileiros. Roda sempre, não depende de rede,
   e devolve o trecho e o artigo de onde tirou cada valor.
2. **Modelo de linguagem** — quando houver provedor configurado, entra como
   camada adicional para os parâmetros que a leitura determinística não achou.

Em qualquer caso vale a regra do §46: **nada vira parâmetro válido sem
confirmação humana**. A saída aqui é sugestão, com confiança e origem.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.engines.conformidade.catalogo import CATALOGO


@dataclass
class Sugestao:
    chave: str
    valor: object
    trecho: str | None = None
    dispositivo: str | None = None
    confianca: float = 0.6
    pergunta_validacao: str | None = None


@dataclass
class ResultadoExtracao:
    sugestoes: list[Sugestao] = field(default_factory=list)
    nao_localizados: list[str] = field(default_factory=list)
    metodo: str = "leitura-deterministica"


_NUM_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
    "quinze": 15, "vinte": 20, "trinta": 30, "sessenta": 60, "noventa": 90,
    "vinte e quatro": 24, "trinta e seis": 36, "quarenta e oito": 48,
}


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _numero(bruto: str) -> int | None:
    bruto = bruto.strip().lower()
    if bruto.isdigit():
        return int(bruto)
    return _NUM_EXTENSO.get(_sem_acento(bruto))


def _artigos(texto: str) -> list[tuple[str, str]]:
    """Quebra o estatuto em (identificação do artigo, texto do artigo)."""
    padrao = re.compile(r"(art(?:igo)?\.?\s*\d+\s*[ºo°]?)", re.IGNORECASE)
    partes = padrao.split(texto)
    if len(partes) < 3:
        return [("", texto)]

    blocos = []
    for i in range(1, len(partes), 2):
        rotulo = re.sub(r"\s+", " ", partes[i].strip())
        rotulo = re.sub(r"^art(?:igo)?\.?\s*", "art. ", rotulo, flags=re.IGNORECASE)
        blocos.append((rotulo, partes[i + 1] if i + 1 < len(partes) else ""))
    return blocos


# Cada regra: (chave, padrão, extrator, confiança)
def _regra_mandato(bloco: str) -> object | None:
    m = re.search(
        r"mandato[^.]{0,80}?(?:de|por|ser[áa]\s+de|dura[çc][ãa]o\s+de)\s+"
        r"(\d+|[a-zç]+(?:\s+e\s+[a-zç]+)?)\s*\(?\s*\d*\s*\)?\s*(anos?|meses)",
        bloco, re.IGNORECASE,
    )
    if not m:
        return None
    quantidade = _numero(m.group(1))
    if quantidade is None:
        return None
    return quantidade * 12 if m.group(2).lower().startswith("ano") else quantidade


def _regra_prazo_convocacao(bloco: str) -> object | None:
    m = re.search(
        r"(?:antecedência|antecedencia|anteced[êe]ncia\s+m[íi]nima)\s+(?:m[íi]nima\s+)?"
        r"de\s+(\d+|[a-zç]+)\s*\(?\s*\d*\s*\)?\s*dias",
        bloco, re.IGNORECASE,
    )
    if not m:
        m = re.search(
            r"com\s+(\d+|[a-zç]+)\s*\(?\s*\d*\s*\)?\s*dias\s+de\s+antecedência",
            bloco, re.IGNORECASE,
        )
    return _numero(m.group(1)) if m else None


_EXPRESSOES_QUORUM = (
    r"maioria\s+absoluta[^.,;]{0,40}",
    r"maioria\s+simples[^.,;]{0,40}",
    r"metade\s+mais\s+um[^.,;]{0,40}",
    r"qualquer\s+n[úu]mero[^.,;]{0,40}",
    r"\d+\s*/\s*\d+[^.,;]{0,40}",
    r"(?:dois|tr[êe]s|quatro|cinco)\s+(?:ter[çc]os|quintos|quartos)[^.,;]{0,40}",
    r"\d+\s*%[^.,;]{0,40}",
)


def _quorum_no_bloco(bloco: str) -> str | None:
    for expressao in _EXPRESSOES_QUORUM:
        m = re.search(expressao, bloco, re.IGNORECASE)
        if m:
            return re.sub(r"\s+", " ", m.group(0)).strip(" ,;.")
    return None


def _partir_por_segunda_convocacao(bloco: str) -> tuple[str, bool, str]:
    """Separa o que vale para a primeira convocação do que vale para a segunda."""
    m = re.search(r"(?:em\s+)?segunda\s+convoca[çc][ãa]o", bloco, re.IGNORECASE)
    if not m:
        return bloco, False, ""
    return bloco[: m.start()], True, bloco[m.start():]


def _tem(bloco: str, *termos: str) -> bool:
    normalizado = _sem_acento(bloco.lower())
    return all(_sem_acento(t.lower()) in normalizado for t in termos)


def extrair_parametros(texto: str) -> ResultadoExtracao:
    resultado = ResultadoExtracao()
    encontrados: set[str] = set()
    blocos = _artigos(texto)

    def registrar(chave, valor, bloco, rotulo, confianca, pergunta=None):
        if chave in encontrados or valor in (None, ""):
            return
        encontrados.add(chave)
        trecho = re.sub(r"\s+", " ", bloco.strip())[:400]
        resultado.sugestoes.append(
            Sugestao(chave, valor, trecho, rotulo or None, confianca, pergunta)
        )

    for rotulo, bloco in blocos:
        normalizado = _sem_acento(bloco.lower())

        if "mandato" in normalizado:
            valor = _regra_mandato(bloco)
            registrar("MANDATO_DURACAO_MESES", valor, bloco, rotulo, 0.8)
            if "reelei" in normalizado:
                permite = not re.search(r"(vedad|proibid|n[ãa]o\s+ser[áa]\s+permitid)",
                                        normalizado)
                registrar("MANDATO_PERMITE_REELEICAO", permite, bloco, rotulo, 0.7)

        if _tem(bloco, "convoca") and "dias" in normalizado:
            registrar("CONVOCACAO_PRAZO_DIAS", _regra_prazo_convocacao(bloco), bloco, rotulo, 0.8)

        if _tem(bloco, "convoca"):
            legitimados = []
            for termo, rotulo_legitimado in (
                ("presidente", "Presidente"),
                ("diretoria", "Diretoria"),
                ("conselho fiscal", "Conselho Fiscal"),
                ("pastor presidente", "Pastor Presidente"),
            ):
                if _sem_acento(termo) in normalizado:
                    legitimados.append(rotulo_legitimado)
            fracao = re.search(r"(\d+\s*/\s*\d+|um\s+quinto|1/5)[^.,;]{0,40}associados",
                               normalizado)
            if fracao:
                legitimados.append(re.sub(r"\s+", " ", fracao.group(0)).strip())
            if legitimados:
                registrar("CONVOCACAO_LEGITIMADOS", legitimados, bloco, rotulo, 0.6,
                          "Confirme se esta é a lista completa de quem pode convocar.")

        # O estatuto costuma tratar as duas convocações no mesmo artigo, com
        # quóruns diferentes. Por isso o bloco é partido antes de ler cada um.
        fala_de_instalacao = (
            "quorum" in normalizado or "instala" in normalizado or "convoca" in normalizado
        )
        if fala_de_instalacao:
            antes, marcador, depois = _partir_por_segunda_convocacao(bloco)
            if "primeira convoca" in normalizado or "instala" in normalizado:
                registrar("QUORUM_INSTALACAO_PRIMEIRA", _quorum_no_bloco(antes), antes,
                          rotulo, 0.65,
                          "Confirme o quórum de instalação em primeira convocação.")
            if marcador:
                registrar("QUORUM_INSTALACAO_SEGUNDA", _quorum_no_bloco(depois), depois,
                          rotulo, 0.65,
                          "Confirme o quórum de instalação em segunda convocação.")

        if _tem(bloco, "estatuto") and re.search(r"(reforma|altera)", normalizado):
            quorum = _quorum_no_bloco(bloco)
            registrar("QUORUM_REFORMA_ESTATUTARIA", quorum, bloco, rotulo, 0.7,
                      "Confirme o quórum exigido para alterar o estatuto.")

        if "destitui" in normalizado:
            registrar("QUORUM_DESTITUICAO", _quorum_no_bloco(bloco), bloco, rotulo, 0.7,
                      "Confirme o quórum exigido para destituir administradores.")

        if "dissolu" in normalizado or "dissolv" in normalizado:
            registrar("QUORUM_DISSOLUCAO", _quorum_no_bloco(bloco), bloco, rotulo, 0.7,
                      "Confirme o quórum exigido para dissolver a entidade.")
            m = re.search(r"patrim[oô]nio[^.]{0,200}", bloco, re.IGNORECASE)
            if m:
                registrar("DESTINACAO_PATRIMONIAL",
                          re.sub(r"\s+", " ", m.group(0)).strip()[:300], bloco, rotulo, 0.6,
                          "Confirme a destinação do patrimônio em caso de dissolução.")

        if "conselho fiscal" in normalizado:
            registrar("CONSELHO_FISCAL_EXISTE", True, bloco, rotulo, 0.85)
            if "parecer" in normalizado and ("contas" in normalizado or "balanc" in normalizado):
                registrar("CONSELHO_FISCAL_PARECER_OBRIGATORIO", True, bloco, rotulo, 0.7,
                          "Confirme se o parecer do Conselho Fiscal é obrigatório para "
                          "aprovar as contas.")

        if "assembleia geral ordin" in normalizado:
            if re.search(r"(anualmente|uma vez por ano|todo ano|anual)", normalizado):
                registrar("AGO_PERIODICIDADE_MESES", 12, bloco, rotulo, 0.75)
            m = re.search(r"at[ée]\s+(?:o\s+dia\s+)?(\d{1,2}\s*(?:de\s+)?[a-zç]+)", bloco,
                          re.IGNORECASE)
            if m and ("contas" in normalizado or "balanc" in normalizado):
                registrar("AGO_PRAZO_APROVACAO_CONTAS", f"até {m.group(1)}", bloco, rotulo, 0.6,
                          "Confirme o prazo estatutário para aprovação das contas.")

    resultado.nao_localizados = sorted(set(CATALOGO) - encontrados)
    return resultado
