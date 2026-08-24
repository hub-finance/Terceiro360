import datetime as dt

import pytest

from app.core.enums import TipoEntidade
from app.engines.conformidade.resolucao import ParametroEstatutario, ResolvedorParametros
from app.engines.validacao.contexto import (
    ContextoValidacao,
    EntidadeInfo,
    EstatutoInfo,
    MandatoInfo,
    MembroInfo,
    RCPJInfo,
    RegraRCPJInfo,
)

HOJE = dt.date(2026, 8, 24)


@pytest.fixture
def entidade():
    return EntidadeInfo(
        id="e1",
        razao_social="ASSOCIAÇÃO COMUNITÁRIA NOVO HORIZONTE",
        tipo_entidade=TipoEntidade.ASSOCIACAO,
        cnpj="12.345.678/0001-90",
        municipio="Belo Horizonte",
        uf="MG",
        data_constituicao=dt.date(2015, 3, 10),
    )


@pytest.fixture
def parametros_padrao():
    """Estatuto cadastrado e confirmado — o cenário 'entidade organizada'."""
    return [
        ParametroEstatutario("MANDATO_DURACAO_MESES", 24, confirmado=True, dispositivo="art. 18"),
        ParametroEstatutario("MANDATO_PERMITE_REELEICAO", True, confirmado=True, dispositivo="art. 18, §1º"),
        ParametroEstatutario("CONVOCACAO_PRAZO_DIAS", 15, confirmado=True, dispositivo="art. 21"),
        ParametroEstatutario("CONVOCACAO_LEGITIMADOS", ["Presidente", "Diretoria", "1/5 dos associados"],
                             confirmado=True, dispositivo="art. 21, §1º"),
        ParametroEstatutario("QUORUM_INSTALACAO_PRIMEIRA", "metade mais um dos associados",
                             confirmado=True, dispositivo="art. 22"),
        ParametroEstatutario("QUORUM_INSTALACAO_SEGUNDA", "qualquer número",
                             confirmado=True, dispositivo="art. 22, parágrafo único"),
        ParametroEstatutario("QUORUM_APROVACAO_GERAL", "maioria simples dos presentes",
                             confirmado=True, dispositivo="art. 23"),
        ParametroEstatutario("QUORUM_REFORMA_ESTATUTARIA", "2/3 dos presentes",
                             confirmado=True, dispositivo="art. 30"),
        ParametroEstatutario("QUORUM_DESTITUICAO", "2/3 dos presentes", confirmado=True, dispositivo="art. 31"),
        ParametroEstatutario("CONSELHO_FISCAL_EXISTE", True, confirmado=True, dispositivo="art. 25"),
        ParametroEstatutario("CONSELHO_FISCAL_PARECER_OBRIGATORIO", True, confirmado=True, dispositivo="art. 26"),
        ParametroEstatutario("DESTINACAO_PATRIMONIAL", "Entidade congênere designada pela assembleia",
                             confirmado=True, dispositivo="art. 40"),
    ]


@pytest.fixture
def mandato_vigente():
    return MandatoInfo(
        id="m1", orgao="DIRETORIA", designacao="GESTÃO 2024–2026",
        data_inicio=dt.date(2024, 7, 1), data_fim=dt.date(2026, 6, 30),
        membros=[
            MembroInfo("p1", "Maria Aparecida Souza", "Presidente", "PRESIDENTE"),
            MembroInfo("p2", "João Carlos Lima", "Secretário", "SECRETARIO"),
            MembroInfo("p3", "Ana Paula Ferreira", "Tesoureira", "TESOUREIRO"),
        ],
    )


@pytest.fixture
def rcpj():
    return RCPJInfo(
        id="r1", nome="1º Ofício de Registro Civil das Pessoas Jurídicas de Belo Horizonte",
        uf="MG", municipio="Belo Horizonte",
        exige_reconhecimento_firma=True, exige_visto_advogado=False,
        data_ultima_verificacao=dt.date(2026, 6, 1), regras_desatualizadas=False,
        regra_evento=RegraRCPJInfo(
            tipo_evento="ELEICAO_DIRETORIA",
            documentos_exigidos=[
                {"codigo": "EDITAL_CONVOCACAO", "descricao": "Edital de convocação", "obrigatorio": True},
                {"codigo": "ATA", "descricao": "Ata da assembleia", "obrigatorio": True},
                {"codigo": "LISTA_PRESENCA", "descricao": "Lista de presença", "obrigatorio": True},
                {"codigo": "REQUERIMENTO_RCPJ", "descricao": "Requerimento", "obrigatorio": True},
            ],
            exige_reconhecimento_firma=True, exige_visto_advogado=False, vias=2,
            data_ultima_verificacao=dt.date(2026, 6, 1),
        ),
    )


@pytest.fixture
def montar_contexto(entidade, parametros_padrao, mandato_vigente, rcpj):
    def _montar(tipo_evento, dados=None, data_ato=None, parametros=None,
                mandatos=None, associados_aptos=30, documentos=None, **kw):
        resolvedor = ResolvedorParametros(
            parametros if parametros is not None else parametros_padrao,
            data_referencia=data_ato or HOJE,
        )
        return ContextoValidacao(
            entidade=entidade,
            tipo_evento=tipo_evento,
            resolvedor=resolvedor,
            data_ato=data_ato,
            hoje=HOJE,
            dados=dados or {},
            estatuto=kw.pop("estatuto", EstatutoInfo(
                versao=3, vigente=True, data_estatuto=dt.date(2021, 5, 12),
                data_registro=dt.date(2021, 6, 2), numero_registro="123456",
                livro="A-15", folha="220", total_parametros=12, parametros_confirmados=12,
            )),
            mandatos=mandatos if mandatos is not None else [mandato_vigente],
            total_associados=42,
            associados_aptos=associados_aptos,
            rcpj=kw.pop("rcpj", rcpj),
            documentos_anexados=set(documentos or []),
            **kw,
        )

    return _montar
