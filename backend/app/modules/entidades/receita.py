"""Consulta de CNPJ na base pública da Receita Federal.

A Receita não publica uma API aberta de consulta cadastral. O que existe são
serviços que republicam a base de dados abertos que ela distribui — usamos a
BrasilAPI, gratuita e sem cadastro, com a ReceitaWS como segunda tentativa.

Três decisões que valem explicar:

**O dígito verificador é conferido aqui, antes de sair da máquina.** Um CNPJ
digitado errado é o caso comum; não vale gastar uma chamada de rede com ele.

**O que volta é sugestão, não verdade.** A base da Receita é a situação
declarada no cadastro fiscal, que atrasa em relação ao que está registrado no
cartório — uma entidade que mudou de nome em assembleia pode levar meses para
constar assim. Por isso a consulta preenche a tela e a pessoa confirma; nada é
gravado direto.

**Falha de rede não pode impedir o cadastro.** Se o serviço estiver fora, o
cadastro manual continua funcionando como sempre. A consulta é um atalho, não
um caminho obrigatório.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import re
import unicodedata

import httpx

from app.core.enums import TipoEntidade
from app.core.tempo import agora

TEMPO_LIMITE = httpx.Timeout(8.0, connect=4.0)


class ErroConsulta(Exception):
    """Base das falhas de consulta, todas com mensagem para o usuário final."""


class CnpjInvalido(ErroConsulta):
    pass


class NaoEncontrado(ErroConsulta):
    pass


class ServicoIndisponivel(ErroConsulta):
    pass


# ------------------------------------------------------------------ CNPJ


def apenas_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def formatar(cnpj: str) -> str:
    d = apenas_digitos(cnpj)
    if len(d) != 14:
        return cnpj
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def validar(cnpj: str) -> str:
    """Devolve o CNPJ só com dígitos, ou levanta CnpjInvalido.

    O cálculo do dígito verificador é o do módulo 11 com pesos 2..9 cíclicos,
    da direita para a esquerda. A rejeição de sequências repetidas (00000…,
    11111…) é necessária porque elas passam no cálculo.
    """
    d = apenas_digitos(cnpj)
    if len(d) != 14:
        raise CnpjInvalido("O CNPJ precisa ter 14 dígitos.")
    if d == d[0] * 14:
        raise CnpjInvalido("CNPJ inválido.")

    def digito(base: str) -> str:
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base):]
        soma = sum(int(c) * p for c, p in zip(base, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    if digito(d[:12]) != d[12] or digito(d[:13]) != d[13]:
        raise CnpjInvalido("CNPJ inválido: o dígito verificador não confere.")
    return d


# ------------------------------------------------------- Natureza jurídica


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn"
    ).lower()


def tipo_pela_natureza(natureza: str | None) -> TipoEntidade | None:
    """Traduz a natureza jurídica da Receita para o tipo do sistema.

    Devolve None quando não reconhece — e isso é o comportamento certo: uma
    entidade com natureza que não está aqui (sindicato, condomínio, partido)
    não é do escopo deste sistema, e chutar um tipo seria pior do que deixar a
    pessoa escolher.

    Note que OSCIP, OS e filantrópica NÃO aparecem: não são naturezas
    jurídicas, são qualificações concedidas a uma associação ou fundação já
    existente. A Receita registra a natureza; a qualificação vive noutro
    lugar, e quem informa é o usuário.
    """
    if not natureza:
        return None
    texto = _sem_acento(natureza)
    if "religiosa" in texto:
        return TipoEntidade.ORGANIZACAO_RELIGIOSA
    if "fundacao" in texto:
        return TipoEntidade.FUNDACAO
    if "associacao" in texto:
        return TipoEntidade.ASSOCIACAO
    return None


SITUACOES_DE_ALERTA = {"BAIXADA", "INAPTA", "SUSPENSA", "NULA"}


# ------------------------------------------------------------- Resultado


@dataclasses.dataclass(frozen=True)
class DadosReceita:
    cnpj: str
    razao_social: str | None
    nome_fantasia: str | None
    tipo_entidade: str | None
    natureza_juridica: str | None
    data_constituicao: dt.date | None
    logradouro: str | None
    numero: str | None
    complemento: str | None
    bairro: str | None
    municipio: str | None
    uf: str | None
    cep: str | None
    email: str | None
    telefone: str | None
    situacao_cadastral: str | None
    situacao_exige_atencao: bool
    fonte: str
    consultado_em: str

    def para_json(self) -> dict:
        return dataclasses.asdict(self)


def _data(valor) -> dt.date | None:
    if not valor:
        return None
    texto = str(valor)[:10]
    try:
        return dt.date.fromisoformat(texto)
    except ValueError:
        pass
    try:  # a ReceitaWS devolve dd/mm/aaaa
        return dt.datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None


def _texto(valor) -> str | None:
    texto = str(valor).strip() if valor is not None else ""
    return texto or None


def _cep(valor) -> str | None:
    d = apenas_digitos(str(valor or ""))
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else _texto(valor)


def interpretar_brasilapi(dados: dict) -> DadosReceita:
    situacao = _texto(dados.get("descricao_situacao_cadastral"))
    natureza = _texto(dados.get("natureza_juridica"))
    tipo = tipo_pela_natureza(natureza)
    telefone = _texto(dados.get("ddd_telefone_1"))
    return DadosReceita(
        cnpj=formatar(str(dados.get("cnpj", ""))),
        razao_social=_texto(dados.get("razao_social")),
        nome_fantasia=_texto(dados.get("nome_fantasia")),
        tipo_entidade=tipo.value if tipo else None,
        natureza_juridica=natureza,
        data_constituicao=_data(dados.get("data_inicio_atividade")),
        logradouro=_texto(dados.get("logradouro")),
        numero=_texto(dados.get("numero")),
        complemento=_texto(dados.get("complemento")),
        bairro=_texto(dados.get("bairro")),
        municipio=_texto(dados.get("municipio")),
        uf=_texto(dados.get("uf")),
        cep=_cep(dados.get("cep")),
        email=_texto(dados.get("email")),
        telefone=telefone,
        situacao_cadastral=situacao,
        situacao_exige_atencao=bool(situacao and situacao.upper() in SITUACOES_DE_ALERTA),
        fonte="BrasilAPI (base de dados abertos da Receita Federal)",
        consultado_em=agora().isoformat(),
    )


def interpretar_receitaws(dados: dict) -> DadosReceita:
    situacao = _texto(dados.get("situacao"))
    natureza = _texto(dados.get("natureza_juridica"))
    tipo = tipo_pela_natureza(natureza)
    return DadosReceita(
        cnpj=formatar(str(dados.get("cnpj", ""))),
        razao_social=_texto(dados.get("nome")),
        nome_fantasia=_texto(dados.get("fantasia")),
        tipo_entidade=tipo.value if tipo else None,
        natureza_juridica=natureza,
        data_constituicao=_data(dados.get("abertura")),
        logradouro=_texto(dados.get("logradouro")),
        numero=_texto(dados.get("numero")),
        complemento=_texto(dados.get("complemento")),
        bairro=_texto(dados.get("bairro")),
        municipio=_texto(dados.get("municipio")),
        uf=_texto(dados.get("uf")),
        cep=_cep(dados.get("cep")),
        email=_texto(dados.get("email")),
        telefone=_texto(dados.get("telefone")),
        situacao_cadastral=situacao,
        situacao_exige_atencao=bool(situacao and situacao.upper() in SITUACOES_DE_ALERTA),
        fonte="ReceitaWS (base de dados abertos da Receita Federal)",
        consultado_em=agora().isoformat(),
    )


FONTES = (
    ("https://brasilapi.com.br/api/cnpj/v1/{cnpj}", interpretar_brasilapi),
    ("https://receitaws.com.br/v1/cnpj/{cnpj}", interpretar_receitaws),
)


def consultar(cnpj: str, cliente: httpx.Client | None = None) -> DadosReceita:
    """Consulta o CNPJ. Levanta ErroConsulta com mensagem pronta para a tela."""
    numero = validar(cnpj)

    proprio = cliente is None
    cliente = cliente or httpx.Client(timeout=TEMPO_LIMITE, follow_redirects=True)
    try:
        indisponivel = 0
        for modelo, interpretar in FONTES:
            try:
                resposta = cliente.get(modelo.format(cnpj=numero))
            except httpx.HTTPError:
                indisponivel += 1
                continue

            if resposta.status_code == 404:
                raise NaoEncontrado(
                    "CNPJ não encontrado na base da Receita Federal. Confira o número — "
                    "e lembre que uma entidade recém-inscrita pode levar dias para constar."
                )
            if resposta.status_code != 200:
                # 429 (limite de consultas) e 5xx são do serviço, não do CNPJ:
                # vale tentar a próxima fonte antes de desistir.
                indisponivel += 1
                continue

            try:
                return interpretar(resposta.json())
            except (ValueError, KeyError, TypeError):
                indisponivel += 1
                continue

        if indisponivel:
            raise ServicoIndisponivel(
                "A consulta à Receita Federal não respondeu agora. Cadastre os dados "
                "manualmente — nada se perde, e a consulta pode ser refeita depois."
            )
        raise NaoEncontrado("CNPJ não encontrado na base da Receita Federal.")
    finally:
        if proprio:
            cliente.close()
