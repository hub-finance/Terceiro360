"""Leitura de ata antiga: quem foi eleito, a qualificação de cada um, o mandato.

Serve a um caso concreto: a entidade chega ao sistema com a última ata de
eleição na mão, e o cadastro ainda vazio. Em vez de transcrever nome, RG, CPF,
endereço, estado civil e profissão de cada dirigente — o que o cartório exige
em toda ata nova —, a pessoa cola o texto e confere o que foi lido.

A regra é a mesma da leitura do estatuto: **o que sai daqui é sugestão, com o
trecho de onde veio.** Nada entra no cadastro sem que alguém confira e grave.
Quando a leitura não tem certeza, ela deixa o campo vazio e diz por quê; um
nome plausível no campo errado é pior do que um campo em branco.

Por que padrões de texto, e não um modelo de IA: funciona sem rede, sem custo
por documento e sem mandar CPF de ninguém para fora do sistema. Atas de
eleição seguem fórmulas muito estáveis ("brasileiro, casado, comerciante,
portador do RG nº…"), e é sobre essas fórmulas que a leitura trabalha.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import asdict, dataclass, field

# ------------------------------------------------------------- Utilidades


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _limpo(texto: str | None) -> str | None:
    if texto is None:
        return None
    texto = re.sub(r"\s+", " ", texto).strip(" ,;.:–-")
    return texto or None


# ------------------------------------------------------ Números por extenso

_UNIDADES = {
    "um": 1, "uma": 1, "primeiro": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
}
_ESPECIAIS = {
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
}
_DEZENAS = {
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
    "setenta": 70, "oitenta": 80, "noventa": 90,
}
_CENTENAS = {
    "cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300,
    "trezentas": 300, "quatrocentos": 400, "quatrocentas": 400, "quinhentos": 500,
    "quinhentas": 500, "seiscentos": 600, "seiscentas": 600, "setecentos": 700,
    "setecentas": 700, "oitocentos": 800, "oitocentas": 800, "novecentos": 900,
    "novecentas": 900,
}
_PALAVRA_NUMERO = {**_UNIDADES, **_ESPECIAIS, **_DEZENAS, **_CENTENAS}
_PADRAO_EXTENSO = (
    r"(?:(?:" + "|".join(sorted(list(_PALAVRA_NUMERO) + ["mil"], key=len, reverse=True))
    + r")(?:\s+e\s+|\s+|(?=\W|$)))+"
)


def numero_por_extenso(texto: str) -> int | None:
    """'dois mil e vinte e quatro' -> 2024; '15' -> 15; 'quinze' -> 15."""
    texto = _sem_acento(texto.lower()).strip()
    digitos = re.match(r"^(\d+)", texto)
    if digitos:
        return int(digitos.group(1))
    total, atual, achou = 0, 0, False
    for palavra in re.findall(r"[a-z]+", texto):
        if palavra == "e":
            continue
        if palavra == "mil":
            total += (atual or 1) * 1000
            atual, achou = 0, True
        elif palavra in _PALAVRA_NUMERO:
            atual += _PALAVRA_NUMERO[palavra]
            achou = True
        else:
            break
    return total + atual if achou else None


# ------------------------------------------------------------------ Datas

_MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
_MES = r"(janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
_NUM = r"(\d{1,4}|" + _PADRAO_EXTENSO + r")"
_DIA = r"(\d{1,2}|1[ºo°]|" + _PADRAO_EXTENSO + r")"

# "15/03/2024", "15.03.2024"
_DATA_NUMERICA = r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})"
# "15 de março de 2024", "1º de abril de 2024", "dez de março de dois mil e vinte e quatro"
_DATA_EXTENSO = _DIA + r"\s*(?:\([^)]{0,30}\)\s*)?de\s+" + _MES + r"\s+(?:de|do\s+ano\s+de)\s+" + _NUM


def _data(dia, mes, ano) -> dt.date | None:
    try:
        d = numero_por_extenso(str(dia).replace("º", "").replace("°", "")) if not isinstance(dia, int) else dia
        m = _MESES.get(_sem_acento(str(mes).lower()), None) if not str(mes).isdigit() else int(mes)
        a = numero_por_extenso(str(ano)) if not isinstance(ano, int) else ano
        if d and m and a and 1900 < a < 2200:
            return dt.date(a, m, d)
    except ValueError:
        pass
    return None


def _primeira_data(texto: str) -> dt.date | None:
    m = re.search(_DATA_NUMERICA, texto)
    candidatos = []
    if m:
        candidatos.append((m.start(), _data(int(m.group(1)), m.group(2), int(m.group(3)))))
    m2 = re.search(_DATA_EXTENSO, texto, re.IGNORECASE)
    if m2:
        candidatos.append((m2.start(), _data(m2.group(1), m2.group(2), m2.group(3))))
    candidatos = [c for c in candidatos if c[1]]
    return min(candidatos)[1] if candidatos else None


# --------------------------------------------------------------- Pessoas

# Cargos que aparecem em ata de eleição. A ordem importa: o mais específico
# primeiro ("Vice-Presidente" antes de "Presidente").
_CARGO = (
    r"(?:(?:1|2|3)[ºo°ª]?\s*|primeir[oa]\s+|segund[oa]\s+|terceir[oa]\s+)?"
    r"(?:vice[\s-]*presidente|pastor[a]?\s+presidente|presidente"
    r"|secret[aá]ri[oa](?:[\s-]+geral)?|tesoureir[oa](?:[\s-]+geral)?"
    r"|diretor[a]?(?:\s+(?:de|do|da)?\s*[a-zçãéíóú]+){0,2}"
    r"|conselheir[oa]\s+fiscal(?:\s+(?:efetiv[oa]|titular|suplente))?"
    r"|membro\s+(?:efetivo\s+|suplente\s+)?do\s+conselho\s+fiscal"
    r"|suplente(?:\s+do\s+conselho\s+fiscal)?)"
)

# "Presidente: NOME", "Presidente – NOME", "para o cargo de Presidente, o Sr. NOME",
# "para Presidente, NOME".
_MARCADOR_PESSOA = re.compile(
    r"(?:para\s+(?:o\s+cargo\s+de\s+|a\s+fun[cç][aã]o\s+de\s+)?)?(?P<cargo>" + _CARGO + r")"
    r"\s*(?:[:–—-]|,)\s*(?:(?:o|a)\s+)?(?:(?:sr|sra|senhor|senhora|irm[aã]o|irm[aã]|pastor|pr)\.?\s+)?"
    r"(?P<nome>[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁ-ú'’.-]+(?:\s+(?:(?:da|de|do|das|dos|e|DA|DE|DO|DAS|DOS|E)\s+)?"
    r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁ-ú'’.-]+){1,7})",
    re.IGNORECASE,
)

_CPF = re.compile(r"(\d{3}\.?\d{3}\.?\d{3}\s*-?\s*\d{2})")
_RG = re.compile(
    r"(?:\bRG\b|\bR\.G\.|c[ée]dula\s+de\s+identidade(?:\s+RG)?|carteira\s+de\s+identidade)"
    r"\s*(?:n[º°o]\.?\s*|sob\s+o\s+n[º°o]\.?\s*)?:?\s*(?P<numero>[\dXx][\d.\-Xx]{3,14}\d|[\dXx]{4,})"
    r"(?:\s*[,–-]?\s*(?:expedid[ao]\s+pel[ao]\s+)?(?P<orgao>[A-Z]{2,6}\s*[/-]\s*[A-Z]{2})\b)?",
    re.IGNORECASE,
)
_NACIONALIDADE = re.compile(
    r"\b(brasileir[oa]|portugu[eê]s[a]?|estrangeir[oa]|naturalizad[oa](?:\s+brasileir[oa])?)\b",
    re.IGNORECASE,
)
_ESTADO_CIVIL = re.compile(
    r"\b(solteir[oa]|casad[oa]|divorciad[oa]|vi[uú]v[oa]|separad[oa](?:\s+judicialmente)?"
    r"|em\s+uni[aã]o\s+est[aá]vel|convivente)\b",
    re.IGNORECASE,
)
_ENDERECO = re.compile(
    r"resident[e]?\s+(?:e\s+domiciliad[oa]\s+)?(?:na|no|[àa]|em)\s+(?P<endereco>.+?)"
    r"(?=,?\s*CEP\b|;|\n|$)",
    re.IGNORECASE | re.DOTALL,
)
_CEP = re.compile(r"CEP\s*(?:n[º°o]\.?\s*)?:?\s*(\d{2}\.?\d{3}\s*-?\s*\d{3})", re.IGNORECASE)
# Palavras que marcam que um trecho entre vírgulas já não é profissão.
_NAO_E_PROFISSAO = re.compile(
    r"portador|inscrit|\bRG\b|CPF|resident|domicil|c[ée]dula|nascid|identidade|CEP|filh[oa]",
    re.IGNORECASE,
)


def cpf_valido(cpf: str) -> bool:
    d = re.sub(r"\D", "", cpf or "")
    if len(d) != 11 or d == d[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(d[tamanho]):
            return False
    return True


def _formatar_cpf(cpf: str) -> str:
    d = re.sub(r"\D", "", cpf)
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}" if len(d) == 11 else cpf


def _formatar_cep(cep: str) -> str:
    d = re.sub(r"\D", "", cep)
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else cep


def _titulo(texto: str | None) -> str | None:
    """'JOSÉ CARLOS DOS SANTOS' -> 'José Carlos dos Santos'. Nome já em caixa
    mista fica como veio: a grafia é da pessoa, não do sistema."""
    if not texto or not texto.isupper():
        return texto
    minusculas = {"da", "de", "do", "das", "dos", "e"}
    return " ".join(
        p.lower() if p.lower() in minusculas and i else p.capitalize()
        for i, p in enumerate(texto.split())
    )


def _cargo_legivel(cargo: str) -> str:
    cargo = _limpo(cargo) or ""
    cargo = re.sub(r"^(1|2|3)\s*[o°]", r"\1º", cargo, flags=re.IGNORECASE)
    return cargo[:1].upper() + cargo[1:]


@dataclass
class PessoaLida:
    nome: str | None
    cargo: str | None
    cpf: str | None = None
    rg: str | None = None
    orgao_expedidor: str | None = None
    nacionalidade: str | None = None
    estado_civil: str | None = None
    profissao: str | None = None
    endereco: str | None = None
    cep: str | None = None
    trecho: str = ""
    avisos: list[str] = field(default_factory=list)


@dataclass
class AtaLida:
    pessoas: list[PessoaLida] = field(default_factory=list)
    data_assembleia: dt.date | None = None
    trecho_data: str | None = None
    mandato_inicio: dt.date | None = None
    mandato_fim: dt.date | None = None
    trecho_mandato: str | None = None
    total_presentes: int | None = None
    trecho_presentes: str | None = None
    avisos: list[str] = field(default_factory=list)

    def para_json(self) -> dict:
        dados = asdict(self)
        for chave in ("data_assembleia", "mandato_inicio", "mandato_fim"):
            if dados[chave]:
                dados[chave] = dados[chave].isoformat()
        return dados


def _qualificacao(segmento: str, pessoa: PessoaLida) -> int:
    """Preenche a qualificação a partir do trecho da pessoa. Devolve quantos
    elementos achou — é isso que separa um eleito qualificado de uma menção
    de passagem ("convocada pelo Presidente, Sr. Fulano")."""
    achados = 0

    m = _CPF.search(segmento)
    if m:
        pessoa.cpf = _formatar_cpf(m.group(1))
        achados += 2
        if not cpf_valido(pessoa.cpf):
            pessoa.avisos.append("O CPF lido não confere pelos dígitos verificadores — confira na ata.")

    m = _RG.search(segmento)
    if m:
        pessoa.rg = _limpo(m.group("numero"))
        if m.group("orgao"):
            pessoa.orgao_expedidor = re.sub(r"\s+", "", m.group("orgao")).upper()
        achados += 1

    m = _NACIONALIDADE.search(segmento)
    if m:
        pessoa.nacionalidade = m.group(1).lower()
        achados += 1

    m = _ESTADO_CIVIL.search(segmento)
    if m:
        pessoa.estado_civil = re.sub(r"\s+", " ", m.group(1).lower())
        achados += 1
        # Profissão: o trecho entre vírgulas logo depois do estado civil, se
        # não for já documento ou endereço.
        depois = segmento[m.end():]
        partes = [p.strip() for p in depois.split(",")]
        candidata = next((p for p in partes if p), "")
        if candidata and not _NAO_E_PROFISSAO.search(candidata) and len(candidata) <= 80:
            pessoa.profissao = _limpo(candidata)
            achados += 1

    m = _ENDERECO.search(segmento)
    if m:
        pessoa.endereco = _limpo(m.group("endereco"))
        achados += 1

    m = _CEP.search(segmento)
    if m:
        pessoa.cep = _formatar_cep(m.group(1))
        achados += 1

    return achados


def _pessoas(texto: str) -> list[PessoaLida]:
    marcadores = list(_MARCADOR_PESSOA.finditer(texto))
    pessoas: list[PessoaLida] = []
    for i, m in enumerate(marcadores):
        fim = marcadores[i + 1].start() if i + 1 < len(marcadores) else len(texto)
        # O trecho da pessoa termina no próximo marcador ou no fim do parágrafo.
        segmento = texto[m.start():fim]
        quebra = re.search(r"\n\s*\n", segmento)
        if quebra:
            segmento = segmento[: quebra.start()]

        pessoa = PessoaLida(
            nome=_titulo(_limpo(m.group("nome"))),
            cargo=_cargo_legivel(m.group("cargo")),
            trecho=_limpo(segmento) or "",
        )
        # Menção de passagem não é eleito: sem ao menos dois elementos de
        # qualificação (ou um CPF), a linha é descartada.
        if _qualificacao(segmento[m.end() - m.start():], pessoa) < 2:
            continue
        if not pessoa.cpf:
            pessoa.avisos.append("CPF não encontrado neste trecho.")
        pessoas.append(pessoa)
    return pessoas


# --------------------------------------------- Mandato, data e presença


def _mandato(texto: str) -> tuple[dt.date | None, dt.date | None, str | None]:
    data = r"(?:" + _DATA_NUMERICA + r"|" + _DATA_EXTENSO + r")"
    padrao = re.compile(
        r"(?:mandato|per[ií]odo|gest[aã]o|bi[eê]nio|tri[eê]nio|quadri[eê]nio)[^.;]{0,80}?"
        r"(?:de|com\s+in[ií]cio\s+em|a\s+partir\s+de|iniciando\s+em)\s+(?P<inicio>" + data + r")"
        r"[^.;]{0,40}?(?:a|at[eé]|e\s+t[eé]rmino\s+em|e\s+encerramento\s+em|terminando\s+em)\s+"
        r"(?P<fim>" + data + r")",
        re.IGNORECASE,
    )
    m = padrao.search(texto)
    if not m:
        return None, None, None
    return (
        _primeira_data(m.group("inicio")),
        _primeira_data(m.group("fim")),
        _limpo(m.group(0)),
    )


def _data_assembleia(texto: str) -> tuple[dt.date | None, str | None]:
    m = re.search(
        r"aos?\s+" + _DIA + r"\s*(?:\([^)]{0,30}\)\s*)?dias?\s+do\s+m[eê]s\s+de\s+" + _MES
        + r"\s+(?:de|do\s+ano\s+de)\s+" + _NUM,
        texto, re.IGNORECASE,
    )
    if m:
        return _data(m.group(1), m.group(2), m.group(3)), _limpo(m.group(0))
    m = re.search(r"(?:em|no\s+dia)\s+(" + _DATA_NUMERICA + r"|" + _DATA_EXTENSO + r")",
                  texto[:600], re.IGNORECASE)
    if m:
        return _primeira_data(m.group(1)), _limpo(m.group(0))
    return None, None


def _presentes(texto: str) -> tuple[int | None, str | None]:
    m = re.search(
        r"(?:presen[cç]a\s+de|compareceram|estando\s+presentes|presentes)\s+"
        r"(?P<n>\d+|" + _PADRAO_EXTENSO + r")\s*(?:\([^)]{0,40}\)\s*)?"
        r"(?:associad|membr|s[oó]ci|pessoas|filiad|irm[aã]os)",
        texto, re.IGNORECASE,
    )
    if not m:
        return None, None
    return numero_por_extenso(m.group("n")), _limpo(m.group(0))


# ------------------------------------------------------------- Entrada


def ler_ata(texto: str) -> AtaLida:
    texto = texto.replace("\r\n", "\n")
    resultado = AtaLida(pessoas=_pessoas(texto))
    resultado.data_assembleia, resultado.trecho_data = _data_assembleia(texto)
    resultado.mandato_inicio, resultado.mandato_fim, resultado.trecho_mandato = _mandato(texto)
    resultado.total_presentes, resultado.trecho_presentes = _presentes(texto)

    if not resultado.pessoas:
        resultado.avisos.append(
            "Nenhum eleito com qualificação foi encontrado. A leitura procura o cargo "
            "seguido do nome e da qualificação (\"Presidente: Fulano, brasileiro, "
            "casado…\"). Confira se o texto colado inclui a parte da eleição."
        )
    if resultado.mandato_inicio is None and re.search(r"bi[eê]nio|tri[eê]nio|mandato", texto, re.I):
        resultado.avisos.append(
            "O mandato é mencionado, mas sem as duas datas por extenso ou em número. "
            "Informe início e fim antes de gravar a diretoria."
        )
    return resultado
