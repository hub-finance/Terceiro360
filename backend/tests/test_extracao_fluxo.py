"""Leitura do estatuto, de ponta a ponta: texto → sugestão → aceite → validação.

Duas coisas que os testes da leitura isolada não pegavam:

1. Estatuto escrito como os cartórios recebem — "Art. 15." com ponto, número
   com extenso entre parênteses ("4 (quatro) anos"), título de capítulo entre
   artigos, "meia hora após" no lugar de "segunda convocação". O texto dos
   testes antigos usava o formato inverso, e a leitura só funcionava nele.

2. O aceite. A sugestão é guardada como texto; se o tipo da regra se perde no
   caminho, "reeleição vedada" chega à validação como a palavra "False" — que
   não é falsa para ninguém — e uma reeleição proibida passa como verde.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, get_db
from app.main import app
from app.models import Base as ModelosBase  # noqa: F401
from app.modules.ia.extracao import extrair_parametros
from app.seeds.carga import popular

ESTATUTO_DE_CARTORIO = """ESTATUTO SOCIAL DA ASSOCIAÇÃO BENEFICENTE SÃO JOSÉ

CAPÍTULO IV - DA ADMINISTRAÇÃO

Art. 15. A Associação será administrada por uma Diretoria Executiva, eleita pela \
Assembleia Geral para um mandato de 4 (quatro) anos, podendo seus membros ser \
reconduzidos por uma única vez.

CAPÍTULO V - DA ASSEMBLEIA GERAL

Art. 20. A Assembleia Geral reunir-se-á ordinariamente uma vez por ano, até o dia 30 \
de abril, para apreciar o relatório anual da Diretoria e aprovar as contas do \
exercício anterior.

Art. 21. A convocação da Assembleia Geral far-se-á por edital afixado na sede \
social, com antecedência mínima de 10 (dez) dias, pelo Presidente ou por um quinto \
dos associados em pleno gozo de seus direitos.

Art. 22. A Assembleia Geral instalar-se-á em primeira convocação com a maioria \
absoluta dos associados e, meia hora após, com qualquer número de presentes.

Art. 23. Para a destituição dos administradores e para a alteração do presente \
Estatuto é exigido o voto concorde de dois terços dos presentes à assembleia \
especialmente convocada para esse fim.

CAPÍTULO VI - DO CONSELHO FISCAL

Art. 30. O Conselho Fiscal, composto de 3 (três) membros efetivos e 3 (três) \
suplentes, terá por atribuição examinar os livros e documentos e emitir parecer \
sobre o balanço anual.

CAPÍTULO IX - DA DISSOLUÇÃO

Art. 40. A dissolução da Associação somente poderá ser deliberada por 2/3 (dois \
terços) dos associados, e o patrimônio remanescente será destinado a outra \
instituição congênere, com personalidade jurídica, sede e atividade no Estado.
"""


def _por_chave(resultado):
    return {s.chave: s for s in resultado.sugestoes}


# ----------------------------------------------- Redação comum de cartório


def test_le_numero_com_extenso_entre_parenteses():
    s = _por_chave(extrair_parametros(ESTATUTO_DE_CARTORIO))
    assert s["MANDATO_DURACAO_MESES"].valor == 48            # "4 (quatro) anos"
    assert s["CONVOCACAO_PRAZO_DIAS"].valor == 10            # "10 (dez) dias"


def test_titulo_de_capitulo_nao_desloca_a_citacao():
    s = _por_chave(extrair_parametros(ESTATUTO_DE_CARTORIO))
    # "CAPÍTULO VI - DO CONSELHO FISCAL" fica entre os arts. 23 e 30. Colado
    # ao art. 23, fazia a leitura citar o artigo errado.
    assert s["CONSELHO_FISCAL_EXISTE"].dispositivo == "art. 30"
    assert "CAPÍTULO" not in s["QUORUM_DESTITUICAO"].trecho


def test_segunda_convocacao_descrita_pelo_intervalo():
    s = _por_chave(extrair_parametros(ESTATUTO_DE_CARTORIO))
    assert s["QUORUM_INSTALACAO_PRIMEIRA"].valor == "maioria absoluta dos associados"
    assert s["QUORUM_INSTALACAO_SEGUNDA"].valor == "qualquer número de presentes"


def test_reconducao_e_reeleicao_e_assembleia_ordinaria_sem_a_palavra_ordinaria():
    s = _por_chave(extrair_parametros(ESTATUTO_DE_CARTORIO))
    assert s["MANDATO_PERMITE_REELEICAO"].valor is True
    assert s["AGO_PERIODICIDADE_MESES"].valor == 12
    assert s["AGO_PRAZO_APROVACAO_CONTAS"].valor == "até 30 de abril"


def test_quorum_nao_e_cortado_no_meio_da_palavra():
    s = _por_chave(extrair_parametros(ESTATUTO_DE_CARTORIO))
    assert s["QUORUM_REFORMA_ESTATUTARIA"].valor == "dois terços dos presentes à assembleia"


def test_cobertura_no_estatuto_de_cartorio():
    assert len(extrair_parametros(ESTATUTO_DE_CARTORIO).sugestoes) == 14


# ------------------------------------------------------------- API real


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("banco") / "extracao.db"
    engine = create_engine(f"sqlite+pysqlite:///{caminho}",
                           connect_args={"check_same_thread": False})
    Sessao = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    with Sessao() as db:
        popular(db, com_demonstracao=True)

    def _db():
        db = Sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as cliente:
        token = cliente.post("/api/v1/auth/login", data={
            "username": "admin@demo.terceiro360.local", "password": "terceiro360",
        }).json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}
        entidade = cliente.get("/api/v1/entidades", headers=auth).json()[0]["id"]
        yield cliente, auth, entidade, Sessao
    app.dependency_overrides.clear()


def _ler_e_aceitar_tudo(cliente, auth, entidade, texto):
    versao = cliente.post(f"/api/v1/entidades/{entidade}/estatuto/versoes", headers=auth,
                          json={"texto": texto, "vigente": True,
                                "motivo_alteracao": "teste de leitura"})
    assert versao.status_code == 201, versao.text
    analise = cliente.post("/api/v1/ia/extrair-estatuto", headers=auth,
                           json={"estatuto_versao_id": versao.json()["id"]})
    assert analise.status_code == 200, analise.text
    analise_id = analise.json()["analise_id"]
    ids = [s["id"] for s in
           cliente.get(f"/api/v1/ia/analises/{analise_id}", headers=auth).json()["sugestoes"]]
    aceite = cliente.post(f"/api/v1/ia/analises/{analise_id}/aceitar", headers=auth,
                          json={"sugestoes": ids})
    assert aceite.status_code == 200, aceite.text
    return versao.json()["id"]


def _validar(cliente, auth, entidade, tipo, dados):
    ev = cliente.post(f"/api/v1/entidades/{entidade}/eventos", headers=auth,
                      json={"tipo": tipo, "data_referencia": "2026-11-20", "dados": dados})
    assert ev.status_code == 201, ev.text
    r = cliente.post(f"/api/v1/eventos/{ev.json()['id']}/validar", headers=auth)
    assert r.status_code == 200, r.text
    return r.json()


def _codigos(validacao):
    achados = validacao.get("achados") or (
        validacao.get("bloqueios", []) + validacao.get("pendencias", [])
    )
    return {a["codigo"] for a in achados}


def test_reeleicao_vedada_lida_e_aceita_bloqueia_a_reeleicao(api):
    """O caso que importa: a regra veio da leitura, foi aceita, e tem que valer."""
    cliente, auth, entidade, _ = api
    vedada = ESTATUTO_DE_CARTORIO.replace(
        "podendo seus membros ser \\\nreconduzidos por uma única vez",
        "vedada a reeleição",
    ).replace("podendo seus membros ser reconduzidos por uma única vez", "vedada a reeleição")
    assert "vedada a reeleição" in vedada
    _ler_e_aceitar_tudo(cliente, auth, entidade, vedada)

    validacao = _validar(cliente, auth, entidade, "REELEICAO_DIRETORIA", {
        "data_ato": "2026-11-20", "eleitos": [{"nome": "Ana Prado", "cargo": "Presidente"}],
        "mandato_inicio": "2027-01-01", "mandato_fim": "2030-12-31",
    })
    assert "REELEICAO_VEDADA" in _codigos(validacao), validacao


def test_regras_aceitas_chegam_a_validacao_com_o_tipo_certo(api):
    """O que a validação recebe, já convertido — e não o texto gravado."""
    import uuid

    from app.modules.juridico.servicos import parametros_da_entidade

    cliente, auth, entidade, Sessao = api
    _ler_e_aceitar_tudo(cliente, auth, entidade, ESTATUTO_DE_CARTORIO)
    with Sessao() as db:
        params = {p.chave: p for p in parametros_da_entidade(db, uuid.UUID(entidade))}

    assert params["MANDATO_DURACAO_MESES"].valor == 48
    assert params["MANDATO_PERMITE_REELEICAO"].valor is True
    assert params["CONVOCACAO_PRAZO_DIAS"].valor == 10
    # A lista volta como lista, e não como um item só com colchetes e aspas.
    assert params["CONVOCACAO_LEGITIMADOS"].valor == ["Presidente", "um quinto dos associados"]
    assert all(p.confirmado for p in params.values())


def test_sugestao_gravada_no_formato_antigo_tambem_e_aceita_certo():
    from app.api.rotas.ia import _para_gravar

    assert _para_gravar("False", "booleano") == "false"
    assert _para_gravar("True", "booleano") == "true"
    assert _para_gravar("['Presidente', 'Diretoria']", "lista") == "Presidente; Diretoria"
    assert _para_gravar("48", "inteiro") == "48"
