"""DOCUMENTO INTELIGENTE — motor de templates (§15, §16, §46).

Não é substituição cega de variáveis:

* variável sem valor não vira espaço em branco nem invenção — vira
  **DADO NÃO INFORMADO**, e a lacuna fica registrada na versão do documento;
* o corpo aceita condicionais e laços, de modo que um mesmo modelo atenda
  associação e organização religiosa, com ou sem conselho fiscal;
* o resultado carrega a lista de variáveis usadas, faltantes e a fotografia
  dos dados — o documento é reproduzível.
"""
from __future__ import annotations

import datetime as dt
import html
import re
from dataclasses import dataclass, field

from jinja2 import Environment, StrictUndefined, Undefined, meta
from jinja2.exceptions import TemplateSyntaxError, UndefinedError

MARCADOR_LACUNA = "**DADO NÃO INFORMADO**"

MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro")

UNIDADES = ("zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove",
            "dez", "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete",
            "dezoito", "dezenove")
DEZENAS = ("", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta",
           "oitenta", "noventa")
CENTENAS = ("", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos",
            "setecentos", "oitocentos", "novecentos")


class LacunaUndefined(Undefined):
    """Toda variável ausente vira DADO NÃO INFORMADO — e é anotada."""

    lacunas: set[str] = set()

    def _registrar(self) -> str:
        nome = self._undefined_name or "?"
        type(self).lacunas.add(nome)
        return MARCADOR_LACUNA

    def __str__(self) -> str:  # noqa: D105
        return self._registrar()

    def __html__(self) -> str:
        return self._registrar()

    def __iter__(self):
        self._registrar()
        return iter(())

    def __bool__(self) -> bool:
        # Testar a variável num `{% if %}` não conta como lacuna: o modelo
        # está justamente prevendo que ela possa não existir.
        return False

    def __len__(self) -> int:
        self._registrar()
        return 0


def por_extenso(numero: int) -> str:
    """Números por extenso — usado em atas e editais ('quinze (15) dias')."""
    n = int(numero)
    if n < 0:
        return f"menos {por_extenso(-n)}"
    if n < 20:
        return UNIDADES[n]
    if n < 100:
        d, u = divmod(n, 10)
        return DEZENAS[d] + (f" e {UNIDADES[u]}" if u else "")
    if n == 100:
        return "cem"
    if n < 1000:
        c, r = divmod(n, 100)
        return CENTENAS[c] + (f" e {por_extenso(r)}" if r else "")
    if n < 1_000_000:
        milhares, r = divmod(n, 1000)
        prefixo = "mil" if milhares == 1 else f"{por_extenso(milhares)} mil"
        return prefixo + (f" e {por_extenso(r)}" if r else "")
    return str(n)


def data_extenso(valor) -> str:
    if valor in (None, ""):
        return MARCADOR_LACUNA
    if isinstance(valor, str):
        valor = dt.date.fromisoformat(valor)
    if isinstance(valor, dt.datetime):
        valor = valor.date()
    return f"{valor.day} de {MESES[valor.month - 1]} de {valor.year}"


def data_br(valor) -> str:
    if valor in (None, ""):
        return MARCADOR_LACUNA
    if isinstance(valor, str):
        valor = dt.date.fromisoformat(valor)
    if isinstance(valor, dt.datetime):
        valor = valor.date()
    return f"{valor:%d/%m/%Y}"


def hora_br(valor) -> str:
    if valor in (None, ""):
        return MARCADOR_LACUNA
    if isinstance(valor, str):
        return valor
    return f"{valor:%Hh%M}"


def maiusculas(valor) -> str:
    return str(valor).upper() if valor not in (None, "") else MARCADOR_LACUNA


def moeda(valor) -> str:
    if valor in (None, ""):
        return MARCADOR_LACUNA
    texto = f"{float(valor):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return f"R$ {texto}"


@dataclass
class ResultadoRenderizacao:
    texto: str
    lacunas: list[str] = field(default_factory=list)
    variaveis_usadas: list[str] = field(default_factory=list)
    erro: str | None = None

    @property
    def completo(self) -> bool:
        return not self.lacunas and self.erro is None


def _ambiente(estrito: bool = False) -> Environment:
    env = Environment(
        undefined=StrictUndefined if estrito else LacunaUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
    )
    env.filters.update({
        "extenso": por_extenso,
        "data_extenso": data_extenso,
        "data": data_br,
        "hora": hora_br,
        "maiusculas": maiusculas,
        "moeda": moeda,
    })
    return env


def variaveis_do_template(corpo: str) -> list[str]:
    env = _ambiente()
    try:
        ast = env.parse(corpo)
    except TemplateSyntaxError:
        return []
    return sorted(meta.find_undeclared_variables(ast))


def _ausencia_prevista(corpo: str) -> set[str]:
    """Nomes cuja ausência o próprio modelo já prevê, num `{% if %}`.

    Se o modelo testa a variável antes de usá-la, o texto simplesmente omite
    aquele trecho quando ela falta — não sai DADO NÃO INFORMADO. Tratar isso
    como lacuna encheria a revisão de alarme falso, e alarme falso demais faz
    o revisor parar de olhar.
    """
    previstas: set[str] = set()
    for bloco in re.findall(r"{%-?\s*(?:if|elif)\s+(.+?)\s*-?%}", corpo, re.DOTALL):
        previstas.update(re.findall(r"\b([A-Z][A-Z0-9_]*)\b", bloco))
    return previstas


def renderizar(corpo: str, contexto: dict) -> ResultadoRenderizacao:
    env = _ambiente()
    usadas = variaveis_do_template(corpo)
    LacunaUndefined.lacunas = set()
    try:
        texto = env.from_string(corpo).render(**contexto)
    except TemplateSyntaxError as exc:
        return ResultadoRenderizacao("", [], usadas, f"Erro de sintaxe no modelo: {exc.message}")
    except UndefinedError as exc:
        return ResultadoRenderizacao("", [], usadas, f"Variável indefinida: {exc.message}")

    lacunas = sorted(LacunaUndefined.lacunas)
    LacunaUndefined.lacunas = set()

    # Variável presente no contexto mas vazia também é lacuna — salvo quando o
    # modelo só a testa em condicional, caso já coberto acima.
    previstas = _ausencia_prevista(corpo)
    for nome in usadas:
        valor = contexto.get(nome)
        if valor in (None, "", [], {}) and nome not in lacunas and nome not in previstas:
            lacunas.append(nome)
    return ResultadoRenderizacao(texto, sorted(lacunas), usadas)


def validar_template(corpo: str) -> tuple[bool, str | None]:
    try:
        _ambiente().parse(corpo)
    except TemplateSyntaxError as exc:
        return False, f"Linha {exc.lineno}: {exc.message}"
    return True, None


def marcar_lacunas_html(texto: str) -> str:
    """Realça as lacunas para revisão na tela.

    Escapa **antes** de marcar. O texto do documento carrega dados digitados
    por usuários — razão social, nome de dirigente, resposta de questionário —
    e a tela do documento o renderiza como HTML para que o <mark> apareça. Sem
    escapar, bastava alguém gravar `<img src=x onerror=...>` num cadastro para
    o código rodar no navegador de quem abrisse a ata depois (XSS armazenado).
    """
    seguro = html.escape(texto, quote=False)
    return re.sub(
        re.escape(html.escape(MARCADOR_LACUNA, quote=False)),
        '<mark class="lacuna">DADO NÃO INFORMADO</mark>',
        seguro,
    )
