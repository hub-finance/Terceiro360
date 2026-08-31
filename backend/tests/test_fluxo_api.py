"""O fluxo completo do §40/§49, exercitado pela API real.

    entidade → estatuto → regras confirmadas → ato → validação → semáforo
    → documentos → checklist → protocolo → registro → quadro diretivo atualizado
"""
from __future__ import annotations

import datetime as dt
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, get_db
from app.main import app
from app.models import Base as ModelosBase  # noqa: F401
from app.seeds.carga import popular

HOJE = dt.date.today()


@pytest.fixture(scope="module")
def cliente_api(tmp_path_factory):
    """Roda contra SQLite por padrão; contra PostgreSQL quando indicado.

    O SQLite mantém a suíte rápida no dia a dia. Antes de publicar, a mesma
    suíte roda no banco de produção — é onde aparecem as diferenças que
    importam: JSONB, UUID nativo e o comportamento das constraints.

        T360_TEST_DATABASE_URL=postgresql+psycopg://... pytest
    """
    url = os.getenv("T360_TEST_DATABASE_URL")
    if url:
        engine = create_engine(url)
        Base.metadata.drop_all(engine)
    else:
        caminho = tmp_path_factory.mktemp("banco") / "teste.db"
        engine = create_engine(
            f"sqlite+pysqlite:///{caminho}", connect_args={"check_same_thread": False}
        )
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
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def token(cliente_api):
    r = cliente_api.post(
        "/api/v1/auth/login",
        data={"username": "admin@demo.terceiro360.local", "password": "terceiro360"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def entidade_id(cliente_api, auth):
    r = cliente_api.get("/api/v1/entidades", headers=auth)
    assert r.status_code == 200, r.text
    return r.json()[0]["id"]


# ------------------------------------------------------------------ Acesso


def test_sem_token_a_api_nega_acesso(cliente_api):
    assert cliente_api.get("/api/v1/entidades").status_code == 401


def test_senha_errada_nao_autentica(cliente_api):
    r = cliente_api.post(
        "/api/v1/auth/login",
        data={"username": "admin@demo.terceiro360.local", "password": "errada"},
    )
    assert r.status_code == 401


def test_raiz_lista_os_modulos_do_produto(cliente_api):
    corpo = cliente_api.get("/").json()
    codigos = {m["codigo"] for m in corpo["modulos"]}
    assert "TERCEIRO360_JURIDICO" in codigos
    assert "TERCEIRO360_IGREJAS" in codigos
    # O contábil está reservado, não ativo.
    assert "TERCEIRO360_CONTABIL" not in codigos
    assert corpo["modulos_reservados"][0]["codigo"] == "TERCEIRO360_CONTABIL"


# --------------------------------------------------------------- Dashboard


def test_dashboard_traz_diretoria_score_e_prazos(cliente_api, auth, entidade_id):
    painel = cliente_api.get(f"/api/v1/entidades/{entidade_id}/dashboard", headers=auth).json()
    assert painel["entidade"]["cnpj"] == "12.345.678/0001-90"
    assert painel["diretoria"]["vigente"] is True
    assert len(painel["diretoria"]["membros"]) == 4
    assert painel["estatuto"]["parametros_confirmados"] == 15
    assert painel["score"]["pontuacao"] > 0
    assert painel["score"]["classificacao"] in ("Excelente", "Regular", "Atenção", "Risco elevado")
    assert any(p["tipo"] == "FIM_MANDATO" for p in painel["prazos"])


def test_catalogo_de_parametros_fala_a_lingua_do_usuario(cliente_api, auth):
    catalogo = cliente_api.get("/api/v1/catalogo/parametros-estatutarios", headers=auth).json()
    quorum = {p["chave"]: p for p in catalogo["QUORUM"]}
    pergunta = quorum["QUORUM_INSTALACAO_SEGUNDA"]["pergunta"]
    assert "quantas pessoas" in pergunta.lower()


# ----------------------------------------------------- Fluxo de um ato


@pytest.fixture(scope="module")
def evento_eleicao(cliente_api, auth, entidade_id):
    """Eleição marcada dentro do mandato vigente e com edital no prazo."""
    data_ato = HOJE + dt.timedelta(days=40)
    data_edital = data_ato - dt.timedelta(days=20)
    r = cliente_api.post(
        f"/api/v1/entidades/{entidade_id}/eventos",
        headers=auth,
        json={
            "tipo": "ELEICAO_DIRETORIA",
            "data_referencia": data_ato.isoformat(),
            "dados": {
                "data_ato": data_ato.isoformat(),
                "data_edital": data_edital.isoformat(),
                "hora": "19h00",
                "local": "Sede da entidade",
                "convocacao": "PRIMEIRA",
                "convocado_por": "Presidente",
                "meio_convocacao": "edital afixado na sede",
                "ordem_do_dia": ["Eleição da Diretoria para o próximo mandato"],
                "total_presentes": 25,
                "presidente_mesa": "Maria Aparecida Souza",
                "secretario_mesa": "Ana Paula Ferreira",
                "votos_favor": 24,
                "mandato_inicio": (data_ato + dt.timedelta(days=30)).isoformat(),
                "mandato_fim": (data_ato + dt.timedelta(days=30 + 730)).isoformat(),
                "data_posse": (data_ato + dt.timedelta(days=30)).isoformat(),
                "eleitos": [
                    {"nome": "Carlos Eduardo Nunes", "cargo": "Presidente",
                     "cpf": "555.555.555-55"},
                    {"nome": "Beatriz Almeida Rocha", "cargo": "Secretário",
                     "cpf": "666.666.666-66"},
                    {"nome": "Rafael Moreira Pinto", "cargo": "Tesoureiro",
                     "cpf": "777.777.777-77"},
                ],
            },
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_questionario_pede_so_o_que_e_do_ato(cliente_api, auth):
    q = cliente_api.get(
        "/api/v1/catalogo/eventos/ELEICAO_DIRETORIA/questionario", headers=auth
    ).json()
    nomes = {c["nome"] for c in q["campos"]}
    assert "eleitos" in nomes and "data_edital" in nomes
    # Dados que já estão no cadastro não são perguntados de novo (§53).
    assert "razao_social" not in nomes and "cnpj" not in nomes


def test_validacao_aprova_ato_regular(cliente_api, auth, evento_eleicao):
    r = cliente_api.post(f"/api/v1/eventos/{evento_eleicao}/validar", headers=auth)
    assert r.status_code == 200, r.text
    resultado = r.json()
    assert resultado["semaforo"] in ("APTO", "PENDENCIA")
    assert resultado["pode_gerar_documentos"] is True
    codigos = {a["codigo"] for a in resultado["achados"]}
    assert "MANDATO_EXPIRADO" not in codigos
    assert "CONVOCACAO_PRAZO_INSUFICIENTE" not in codigos
    assert "QUORUM_INSTALACAO_OK" in codigos


def test_motor_de_decisao_responde_com_fundamentacao(cliente_api, auth, evento_eleicao):
    r = cliente_api.get(
        f"/api/v1/eventos/{evento_eleicao}/decisao",
        params={"pergunta": "quem_pode_convocar"},
        headers=auth,
    )
    resposta = r.json()
    assert "Presidente" in resposta["justificativa"]
    assert resposta["rotulo"] in ("APTO", "NECESSITA ANÁLISE", "NÃO APTO")


def test_checklist_mistura_ato_estatuto_e_cartorio(cliente_api, auth, evento_eleicao):
    checklist = cliente_api.get(
        f"/api/v1/eventos/{evento_eleicao}/checklist", headers=auth
    ).json()
    origens = {i["origem"] for i in checklist["itens"]}
    assert "ATO" in origens and "RCPJ" in origens
    codigos = {i["codigo"] for i in checklist["itens"]}
    assert {"EDITAL_CONVOCACAO", "ATA", "LISTA_PRESENCA", "REQUERIMENTO_RCPJ"} <= codigos


def test_geracao_produz_documentos_com_dados_do_cadastro(cliente_api, auth, evento_eleicao):
    r = cliente_api.post(f"/api/v1/eventos/{evento_eleicao}/gerar-documentos", headers=auth)
    assert r.status_code == 200, r.text
    gerados = {g["tipo"]: g for g in r.json()["gerados"]}
    assert {"EDITAL_CONVOCACAO", "ATA", "LISTA_PRESENCA", "TERMO_POSSE",
            "REQUERIMENTO_RCPJ"} <= set(gerados)

    documento = cliente_api.get(
        f"/api/v1/documentos/{gerados['ATA']['documento_id']}", headers=auth
    ).json()
    texto = documento["conteudo"]
    # §53 — o que está cadastrado não é digitado de novo.
    assert "ASSOCIAÇÃO COMUNITÁRIA NOVO HORIZONTE (DEMONSTRAÇÃO)" in texto
    assert "12.345.678/0001-90" in texto
    assert "Carlos Eduardo Nunes" in texto
    assert "Presidente da mesa" in texto


def test_edital_traz_o_quorum_lido_do_estatuto(cliente_api, auth, entidade_id):
    documentos = cliente_api.get(
        f"/api/v1/entidades/{entidade_id}/documentos", headers=auth
    ).json()
    edital = next(d for d in documentos if d["tipo"] == "EDITAL_CONVOCACAO")
    texto = cliente_api.get(f"/api/v1/documentos/{edital['id']}", headers=auth).json()["conteudo"]
    assert "metade mais um dos associados" in texto
    assert "qualquer número" in texto


def test_versao_anterior_do_documento_continua_acessivel(cliente_api, auth, evento_eleicao):
    """§20 — gerar de novo cria versão nova, não apaga a anterior."""
    cliente_api.post(f"/api/v1/eventos/{evento_eleicao}/gerar-documentos", headers=auth)
    documentos = cliente_api.get(f"/api/v1/eventos/{evento_eleicao}", headers=auth)
    assert documentos.status_code == 200

    lista = cliente_api.get(
        f"/api/v1/entidades/{lista_entidade(cliente_api, auth)}/documentos", headers=auth
    ).json()
    ata = next(d for d in lista if d["tipo"] == "ATA")
    detalhe = cliente_api.get(f"/api/v1/documentos/{ata['id']}", headers=auth).json()
    assert detalhe["versao_atual"] == 2
    v1 = cliente_api.get(f"/api/v1/documentos/{ata['id']}/versoes/1", headers=auth)
    assert v1.status_code == 200
    assert v1.json()["numero"] == 1


def lista_entidade(cliente_api, auth):
    return cliente_api.get("/api/v1/entidades", headers=auth).json()[0]["id"]


def test_registro_atualiza_o_quadro_diretivo_sem_apagar_historico(
    cliente_api, auth, entidade_id, evento_eleicao
):
    """§41 — a gestão anterior vira histórico; a nova entra."""
    for status in ("EM_REVISAO", "REVISADO", "APROVADO", "ASSINADO", "PROTOCOLADO"):
        r = cliente_api.post(
            f"/api/v1/eventos/{evento_eleicao}/status", headers=auth, json={"status": status}
        )
        assert r.status_code == 200, r.text

    r = cliente_api.post(f"/api/v1/eventos/{evento_eleicao}/registrar", headers=auth)
    assert r.status_code == 200, r.text
    efeitos = " ".join(r.json()["efeitos"])
    assert "Carlos Eduardo Nunes empossado" in efeitos
    assert "encerrada e arquivada no histórico" in efeitos

    mandatos = cliente_api.get(f"/api/v1/entidades/{entidade_id}/mandatos", headers=auth).json()
    assert len(mandatos) == 2
    encerrados = [m for m in mandatos if m["encerrado"]]
    assert len(encerrados) == 1
    assert any(mm["pessoa"] == "Maria Aparecida Souza" for mm in encerrados[0]["membros"])
    nova = next(m for m in mandatos if not m["encerrado"])
    assert any(mm["pessoa"] == "Carlos Eduardo Nunes" for mm in nova["membros"])


def test_ato_nao_retrocede_de_etapa(cliente_api, auth, evento_eleicao):
    r = cliente_api.post(
        f"/api/v1/eventos/{evento_eleicao}/status", headers=auth, json={"status": "RASCUNHO"}
    )
    assert r.status_code == 409


# ------------------------------------------------- Ato com inconsistência


def test_ato_com_edital_fora_do_prazo_e_bloqueado_na_geracao(cliente_api, auth, entidade_id):
    data_ato = HOJE + dt.timedelta(days=20)
    r = cliente_api.post(
        f"/api/v1/entidades/{entidade_id}/eventos",
        headers=auth,
        json={
            "tipo": "ASSEMBLEIA_EXTRAORDINARIA",
            "data_referencia": data_ato.isoformat(),
            "dados": {
                "data_ato": data_ato.isoformat(),
                "data_edital": (data_ato - dt.timedelta(days=5)).isoformat(),
                "convocado_por": "Presidente",
                "ordem_do_dia": ["Assuntos gerais"],
            },
        },
    )
    evento_id = r.json()["id"]

    validacao = cliente_api.post(f"/api/v1/eventos/{evento_id}/validar", headers=auth).json()
    assert validacao["semaforo"] == "BLOQUEADO"
    bloqueio = next(
        a for a in validacao["achados"] if a["codigo"] == "CONVOCACAO_PRAZO_INSUFICIENTE"
    )
    assert bloqueio["dados"] == {"exigido": 15, "realizado": 5}
    fundamentos = " ".join(f["referencia"] + str(f["dispositivo"]) for f in bloqueio["fundamentos"])
    assert "Estatuto Social" in fundamentos and "art. 60" in fundamentos

    geracao = cliente_api.post(f"/api/v1/eventos/{evento_id}/gerar-documentos", headers=auth)
    assert geracao.status_code == 409
    assert "impedem a geração" in str(geracao.json())


def test_ato_bloqueado_pode_ser_gerado_com_decisao_explicita(cliente_api, auth, entidade_id):
    """O bloqueio é forte, mas não é uma parede: um responsável pode assumir a
    decisão. O que não existe é gerar sem que o sistema tenha avisado."""
    eventos = cliente_api.get(f"/api/v1/entidades/{entidade_id}/eventos", headers=auth).json()
    bloqueado = next(e for e in eventos if e["semaforo"] == "BLOQUEADO")
    r = cliente_api.post(
        f"/api/v1/eventos/{bloqueado['id']}/gerar-documentos",
        headers=auth, params={"forcar": True},
    )
    assert r.status_code == 200
    assert r.json()["semaforo"] == "BLOQUEADO"
