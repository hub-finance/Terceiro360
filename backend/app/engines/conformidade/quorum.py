"""Leitura de expressões de quórum escritas em português (§52).

O estatuto diz "metade mais um dos associados", "dois terços dos presentes",
"qualquer número". Aqui isso vira um número comparável — e, quando a frase não
é interpretável com segurança, o resultado é VALIDACAO_NECESSARIA, nunca um
chute (§46).
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum


class BaseQuorum(str, Enum):
    APTOS = "APTOS"          # sobre o total de associados aptos
    PRESENTES = "PRESENTES"  # sobre os presentes à assembleia


class TipoQuorum(str, Enum):
    QUALQUER_NUMERO = "QUALQUER_NUMERO"
    FRACAO = "FRACAO"
    NUMERO_FIXO = "NUMERO_FIXO"
    METADE_MAIS_UM = "METADE_MAIS_UM"
    MAIORIA_SIMPLES = "MAIORIA_SIMPLES"


@dataclass(frozen=True)
class ExigenciaQuorum:
    tipo: TipoQuorum
    fracao: float | None = None
    numero: int | None = None
    base: BaseQuorum = BaseQuorum.APTOS
    texto_original: str = ""

    def minimo(self, total: int) -> int:
        """Quantas pessoas satisfazem a exigência sobre um total."""
        if self.tipo is TipoQuorum.QUALQUER_NUMERO:
            return 1
        if self.tipo is TipoQuorum.NUMERO_FIXO:
            return int(self.numero or 0)
        if self.tipo is TipoQuorum.METADE_MAIS_UM:
            return math.floor(total / 2) + 1
        if self.tipo is TipoQuorum.MAIORIA_SIMPLES:
            return math.floor(total / 2) + 1
        return math.ceil(total * (self.fracao or 0) - 1e-9)

    def descricao(self, total: int | None = None) -> str:
        base = "dos associados aptos" if self.base is BaseQuorum.APTOS else "dos presentes"
        if self.tipo is TipoQuorum.QUALQUER_NUMERO:
            return "qualquer número de presentes"
        if self.tipo is TipoQuorum.NUMERO_FIXO:
            return f"{self.numero} pessoas"
        if self.tipo is TipoQuorum.METADE_MAIS_UM:
            alvo = f" ({self.minimo(total)} pessoas)" if total else ""
            return f"metade mais um {base}{alvo}"
        if self.tipo is TipoQuorum.MAIORIA_SIMPLES:
            alvo = f" ({self.minimo(total)} votos)" if total else ""
            return f"maioria simples {base}{alvo}"
        pct = (self.fracao or 0) * 100
        alvo = f" ({self.minimo(total)} pessoas)" if total else ""
        return f"{pct:.6g}% {base}{alvo}"


_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
}
_DENOMINADOR = {
    "meio": 2, "meios": 2, "metade": 2, "terco": 3, "tercos": 3, "quarto": 4, "quartos": 4,
    "quinto": 5, "quintos": 5, "sexto": 6, "sextos": 6, "setimo": 7, "setimos": 7,
    "oitavo": 8, "oitavos": 8, "nono": 9, "nonos": 9, "decimo": 10, "decimos": 10,
}


def _normalizar(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento).strip()


def interpretar_quorum(texto: str | int | float | None) -> ExigenciaQuorum | None:
    """Devolve None quando a expressão não é interpretável com segurança."""
    if texto is None:
        return None
    if isinstance(texto, (int, float)) and not isinstance(texto, bool):
        valor = float(texto)
        if 0 < valor <= 1:
            return ExigenciaQuorum(TipoQuorum.FRACAO, fracao=valor, texto_original=str(texto))
        return ExigenciaQuorum(TipoQuorum.NUMERO_FIXO, numero=int(valor), texto_original=str(texto))

    original = str(texto).strip()
    t = _normalizar(original)
    if not t:
        return None

    base = BaseQuorum.PRESENTES if "presente" in t or "votante" in t else BaseQuorum.APTOS

    if any(p in t for p in ("qualquer numero", "qualquer quantidade", "sem exigencia",
                            "sem quorum", "independentemente do numero", "nao ha exigencia")):
        return ExigenciaQuorum(TipoQuorum.QUALQUER_NUMERO, base=base, texto_original=original)

    if "metade mais um" in t or "maioria absoluta" in t or re.search(r"\b50\s*%\s*\+\s*1", t):
        return ExigenciaQuorum(TipoQuorum.METADE_MAIS_UM, base=base, texto_original=original)

    if "maioria simples" in t or t.strip() == "maioria" or "maioria dos votos" in t:
        return ExigenciaQuorum(TipoQuorum.MAIORIA_SIMPLES, base=base, texto_original=original)

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", t)
    if m:
        return ExigenciaQuorum(
            TipoQuorum.FRACAO, fracao=float(m.group(1).replace(",", ".")) / 100,
            base=base, texto_original=original,
        )

    m = re.search(r"(\d+)\s*/\s*(\d+)", t)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        if den and num <= den:
            resto = t[m.end():]
            if re.match(r"\s*\+\s*1\b", resto) and num * 2 == den:
                return ExigenciaQuorum(TipoQuorum.METADE_MAIS_UM, base=base, texto_original=original)
            return ExigenciaQuorum(TipoQuorum.FRACAO, fracao=num / den, base=base, texto_original=original)

    # "dois terços", "três quintos", "um quinto"
    m = re.search(r"\b(" + "|".join(_EXTENSO) + r"|\d+)\s+(" + "|".join(_DENOMINADOR) + r")\b", t)
    if m:
        bruto = m.group(1)
        num = int(bruto) if bruto.isdigit() else _EXTENSO[bruto]
        den = _DENOMINADOR[m.group(2)]
        if num <= den:
            return ExigenciaQuorum(TipoQuorum.FRACAO, fracao=num / den, base=base, texto_original=original)

    if "metade" in t:
        return ExigenciaQuorum(TipoQuorum.FRACAO, fracao=0.5, base=base, texto_original=original)

    m = re.fullmatch(r"(\d+)(\s+(pessoas|associados|membros|votos))?", t)
    if m:
        return ExigenciaQuorum(TipoQuorum.NUMERO_FIXO, numero=int(m.group(1)),
                               base=base, texto_original=original)

    return None
