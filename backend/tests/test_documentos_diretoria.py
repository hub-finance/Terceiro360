"""Termo de posse na substituição e relação da diretoria na alteração de cargos.

Os dois atos tinham o documento previsto na matriz e nenhum modelo que
servisse. A tentação era ligar os modelos de eleição a eles — e o resultado
seria um termo de posse sem ninguém tomando posse: os modelos de eleição leem
a lista de eleitos, e estes questionários não perguntam por eleitos.

Por isso os testes de ponta a ponta usam exatamente o que os questionários
coletam, e não um dicionário genérico que serve a todos os atos.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, get_db
from app.engines.templates.motor import MARCADOR_LACUNA
from app.main import app
from app.models import Base as ModelosBase  # noqa: F401
from app.modules.documentos.servicos import aplicar_remanejamentos, quem_sai
from app.seeds.carga import popular

DIRETORIA = [
    {"nome": "Maria Souza", "cargo": "Presidente"},
    {"nome": "João Lima", "cargo": "Secretário"},
    {"nome": "Ana Prado", "cargo": "Tesoureira"},
]


def _por_cargo(linhas):
    return {l["cargo"]: l for l in linhas}


# --------------------------------------------------------- Remanejamento


def test_permuta_entre_dois_membros_nao_deixa_vaga():
    r = _por_cargo(aplicar_remanejamentos(DIRETORIA, [
        {"nome": "Ana Prado", "cargo": "Presidente"},
        {"nome": "Maria Souza", "cargo": "Tesoureira"},
    ]))
    assert r["Presidente"]["nome"] == "Ana Prado"
    assert r["Tesoureira"]["nome"] == "Maria Souza"
    assert not any(l["vago"] for l in r.values())
    assert r["Secretário"]["alterado"] is False


def test_quem_muda_de_cargo_deixa_o_anterior_vago():
    # O sistema não supõe quem assumiu o cargo que ficou para trás.
    r = _por_cargo(aplicar_remanejamentos(DIRETORIA, [
        {"nome": "João Lima", "cargo": "Tesoureira"},
    ]))
    assert r["Tesoureira"]["nome"] == "João Lima"
    assert r["Secretário"]["vago"] is True
    assert r["Secretário"]["nome"] is None


def test_composicao_inteira_e_preservada():
    # A relação que vai ao cartório é a diretoria toda, não só quem mudou.
    linhas = aplicar_remanejamentos(DIRETORIA, [{"nome": "Ana Prado", "cargo": "Presidente"}])
    assert [l["cargo"] for l in linhas] == ["Presidente", "Secretário", "Tesoureira"]


def test_cargo_digitado_de_outro_jeito_e_o_mesmo_cargo():
    board = DIRETORIA + [{"nome": "Rui Alves", "cargo": "Vice-Presidente"}]
    linhas = aplicar_remanejamentos(board, [{"nome": "João Lima", "cargo": "vice presidente"}])
    vices = [l for l in linhas if "vice" in l["cargo"].lower()]
    assert len(vices) == 1
    assert vices[0]["nome"] == "João Lima"


def test_cargo_inexistente_entra_ao_final():
    linhas = aplicar_remanejamentos(DIRETORIA, [{"nome": "Rui Alves", "cargo": "Diretor Social"}])
    assert linhas[-1] == {"cargo": "Diretor Social", "nome": "Rui Alves",
                          "alterado": True, "vago": False}


def test_quem_e_deslocado_sem_novo_cargo_sai_por_escrito():
    # João assume a tesouraria; Ana, que era tesoureira, não recebeu cargo.
    # Ela deixa a diretoria — e isso tem que constar, não sumir em silêncio.
    linhas = aplicar_remanejamentos(DIRETORIA, [{"nome": "João Lima", "cargo": "Tesoureira"}])
    assert quem_sai(DIRETORIA, linhas) == [{"nome": "Ana Prado", "cargo": "Tesoureira"}]


def test_permuta_nao_tira_ninguem_da_diretoria():
    linhas = aplicar_remanejamentos(DIRETORIA, [
        {"nome": "Ana Prado", "cargo": "Presidente"},
        {"nome": "Maria Souza", "cargo": "Tesoureira"},
    ])
    assert quem_sai(DIRETORIA, linhas) == []


def test_remanejamento_incompleto_e_ignorado():
    linhas = aplicar_remanejamentos(DIRETORIA, [{"nome": "Rui Alves"}, {"cargo": "Presidente"}])
    assert linhas == [dict(m, alterado=False, vago=False) for m in DIRETORIA]


# ------------------------------------------------------------- API real


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("banco") / "diretoria.db"
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
        yield cliente, auth, entidade
    app.dependency_overrides.clear()


def _gerar(cliente, auth, entidade, tipo, dados):
    ev = cliente.post(f"/api/v1/entidades/{entidade}/eventos", headers=auth,
                      json={"tipo": tipo, "data_referencia": "2026-11-20", "dados": dados})
    assert ev.status_code == 201, ev.text
    r = cliente.post(f"/api/v1/eventos/{ev.json()['id']}/gerar-documentos?forcar=true",
                     headers=auth)
    assert r.status_code == 200, r.text
    return r.json()


def _corrido(texto: str) -> str:
    """O texto como o leitor o vê: o modelo quebra linhas no meio da frase, e o
    exportador as junta num parágrafo só. Comparar o texto cru faria o teste
    depender de onde caiu a quebra no arquivo do modelo."""
    return " ".join(texto.split())


def _conteudo(cliente, auth, resultado, tipo):
    doc = next(g for g in resultado["gerados"] if g["tipo"] == tipo)
    return cliente.get(f"/api/v1/documentos/{doc['documento_id']}", headers=auth).json()["conteudo"]


def test_substituicao_gera_termo_de_posse_do_substituto(api):
    cliente, auth, entidade = api
    resultado = _gerar(cliente, auth, entidade, "SUBSTITUICAO", {
        "data_ato": "2026-11-20",
        "pessoa_substituida": "Maria Souza",
        "cargo": "Presidente",
        "motivo_vacancia": "RENUNCIA",
        "substituto": "Rui Alves",
        "substituicao_automatica": True,
        "mandato_fim": "2027-06-30",
    })
    assert "TERMO_POSSE" not in resultado["sem_modelo_cadastrado"]
    texto = _corrido(_conteudo(cliente, auth, resultado, "TERMO_POSSE"))

    assert "TERMO DE POSSE EM SUBSTITUIÇÃO" in texto
    assert "Rui Alves toma posse no cargo de Presidente" in texto
    assert "em substituição a Maria Souza" in texto
    assert "vagou por renúncia" in texto
    assert "na forma de substituição prevista no Estatuto Social" in texto
    assert "30/06/2027" in texto
    # O modelo de eleição diria isto — e numa substituição seria falso.
    assert "eleitos na" not in texto
    assert MARCADOR_LACUNA not in texto


def test_substituicao_sem_motivo_informado_nao_inventa_causa(api):
    cliente, auth, entidade = api
    resultado = _gerar(cliente, auth, entidade, "SUBSTITUICAO", {
        "data_ato": "2026-11-20", "pessoa_substituida": "Maria Souza",
        "cargo": "Presidente", "motivo_vacancia": "OUTRO", "substituto": "Rui Alves",
        "mandato_fim": "2027-06-30",
    })
    texto = _corrido(_conteudo(cliente, auth, resultado, "TERMO_POSSE"))
    assert "vagou por" not in texto
    assert "deliberação do órgão competente" in texto


def test_alteracao_de_cargos_gera_relacao_com_a_diretoria_inteira(api):
    cliente, auth, entidade = api
    mandatos = cliente.get(f"/api/v1/entidades/{entidade}/mandatos", headers=auth).json()
    membros = [m for m in next(m for m in mandatos if m["vigente"])["membros"]]
    assert len(membros) >= 2, "a demonstração precisa de ao menos dois dirigentes"
    a, b = membros[0], membros[1]

    resultado = _gerar(cliente, auth, entidade, "ALTERACAO_CARGOS", {
        "data_ato": "2026-11-20",
        "orgao_deliberante": "Diretoria",
        "cria_ou_extingue_cargo": False,
        "remanejamentos": [
            {"nome": a["pessoa"], "cargo": b["cargo"]},
            {"nome": b["pessoa"], "cargo": a["cargo"]},
        ],
    })
    assert "RELACAO_DIRETORIA" not in resultado["sem_modelo_cadastrado"]
    texto = _conteudo(cliente, auth, resultado, "RELACAO_DIRETORIA")

    assert "Composição após alteração de cargos" in texto
    # Todos os membros aparecem, não só os dois que trocaram.
    for m in membros:
        assert m["pessoa"] in texto
    assert texto.count("(alterado nesta deliberação)") == 2
    assert "CARGO VAGO" not in texto
    assert "deliberada pelo(a) Diretoria" in _corrido(texto)


def test_relacao_declara_quem_deixa_a_diretoria(api):
    cliente, auth, entidade = api
    mandatos = cliente.get(f"/api/v1/entidades/{entidade}/mandatos", headers=auth).json()
    membros = next(m for m in mandatos if m["vigente"])["membros"]
    movido, deslocado = membros[1], membros[2]

    resultado = _gerar(cliente, auth, entidade, "ALTERACAO_CARGOS", {
        "data_ato": "2026-11-20", "orgao_deliberante": "Diretoria",
        "remanejamentos": [{"nome": movido["pessoa"], "cargo": deslocado["cargo"]}],
    })
    texto = _conteudo(cliente, auth, resultado, "RELACAO_DIRETORIA")

    assert "CARGO VAGO" in texto
    assert "Deixam a Diretoria nesta deliberação:" in texto
    assert f"{deslocado['pessoa']}, que ocupava o cargo de {deslocado['cargo']}" in _corrido(texto)
    # Mesmo formato da relação de eleição: recuo e uma linha entre cargos.
    assert "\n    Nome: " in texto
    assert "\n\n2. " in texto
