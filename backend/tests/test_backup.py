"""Cópia de segurança: completa, isolada por escritório, sem segredos.

O que se testa é o que custa caro quando falha:
- um escritório levar dado de outro na cópia dele;
- a cópia levar hash de senha ou segredo de segundo fator;
- uma tabela nova ficar fora da cópia sem ninguém perceber;
- a cópia depender da chave de cifra para ser lida.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, get_db
from app.core.security import hash_senha
from app.main import app
from app.models import Base as ModelosBase  # noqa: F401
from app.modules.backup.servico import ESCOPO, GLOBAIS
from app.seeds.carga import popular

CPF_DO_OUTRO = "111.444.777-35"


def test_toda_tabela_esta_classificada():
    """Tabela nova precisa de decisão: é do escritório ou do sistema?

    Sem este teste ela ficaria fora da cópia em silêncio — ou, se alguém a
    pusesse num escopo errado, vazaria dado de outro escritório.
    """
    do_escritorio = [nome for nome, _ in ESCOPO]
    assert len(do_escritorio) == len(set(do_escritorio)), "tabela repetida em ESCOPO"
    banco = set(Base.metadata.tables)
    classificadas = set(do_escritorio) | (GLOBAIS - {"alembic_version"})
    assert banco - classificadas == set(), f"sem classificação: {banco - classificadas}"
    assert classificadas - banco == set(), f"classificada mas inexistente: {classificadas - banco}"
    assert not set(do_escritorio) & GLOBAIS


def test_filha_vem_depois_do_pai():
    vistas = set()
    for nome, escopo in ESCOPO:
        if escopo[0] == "pai":
            assert escopo[2] in vistas, f"{nome} lida antes de {escopo[2]}"
        if escopo[0] in ("entidade", "entidade_ou_usuario"):
            assert "entidades" in vistas
        vistas.add(nome)


# ------------------------------------------------------------- API real


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("banco") / "backup.db"
    engine = create_engine(f"sqlite+pysqlite:///{caminho}",
                           connect_args={"check_same_thread": False})
    Sessao = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    with Sessao() as db:
        popular(db, com_demonstracao=True)
        # Um segundo escritório, que nunca pode aparecer na cópia do primeiro.
        from app.modules.entidades.models import Entidade
        from app.modules.identity.models import Cliente, Perfil, Usuario, UsuarioPerfil
        from app.modules.juridico.models import Pessoa

        outro = Cliente(nome="Escritório Vizinho Ltda")
        db.add(outro); db.flush()
        db.add(Entidade(cliente_id=outro.id, razao_social="Igreja do Vizinho"))
        db.add(Pessoa(cliente_id=outro.id, nome="Pessoa do Vizinho", cpf=CPF_DO_OUTRO))
        # E, no escritório da demonstração, alguém sem permissão de cópia.
        demo = db.scalar(select(Cliente).where(Cliente.nome == "Escritório Demonstração"))
        leitor = Usuario(cliente_id=demo.id, nome="Leitor", email="leitor@demo.local",
                         senha_hash=hash_senha("senha-do-leitor-123"))
        db.add(leitor); db.flush()
        perfil = db.scalar(select(Perfil).where(Perfil.cliente_id.is_(None),
                                                Perfil.codigo == "VISUALIZADOR"))
        db.add(UsuarioPerfil(usuario_id=leitor.id, perfil_id=perfil.id))
        db.commit()

    def _db():
        db = Sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as cliente:
        def entrar(email, senha):
            r = cliente.post("/api/v1/auth/login", data={"username": email, "password": senha})
            return {"Authorization": f"Bearer {r.json()['access_token']}"}

        admin = entrar("admin@demo.terceiro360.local", "terceiro360")
        r = cliente.get("/api/v1/backup", headers=admin)
        assert r.status_code == 200, r.text
        yield {
            "cliente": cliente, "admin": admin,
            "leitor": entrar("leitor@demo.local", "senha-do-leitor-123"),
            "resposta": r, "zip": zipfile.ZipFile(io.BytesIO(r.content)),
        }
    app.dependency_overrides.clear()


def _tabela(z, nome):
    return json.loads(z.read(f"tabelas/{nome}.json"))


def _tudo(z) -> str:
    return "".join(z.read(n).decode("utf-8") for n in z.namelist())


def test_entrega_um_zip_com_nome_e_sem_cache(api):
    r = api["resposta"]
    assert r.headers["content-type"] == "application/zip"
    assert 'filename="terceiro360-copia-escritorio-demonstracao-' in r.headers["content-disposition"]
    assert r.headers["cache-control"] == "no-store"
    nomes = set(api["zip"].namelist())
    assert {"LEIA-ME.txt", "manifesto.json", "referencias_globais.json"} <= nomes
    assert {f"tabelas/{n}.json" for n, _ in ESCOPO} <= nomes


def test_traz_os_dados_do_escritorio(api):
    z = api["zip"]
    entidades = _tabela(z, "entidades")
    assert [e["razao_social"] for e in entidades] == [
        "Associação Comunitária Novo Horizonte (demonstração)"
    ]
    assert _tabela(z, "mandato_membros"), "a diretoria precisa estar na cópia"
    assert _tabela(z, "estatuto_parametros"), "as regras do estatuto precisam estar na cópia"


def test_cpf_sai_legivel_sem_depender_da_chave(api):
    # A cópia existe também para o dia em que a chave de cifra se perder.
    pessoas = _tabela(api["zip"], "pessoas")
    cpfs = [p["cpf"] for p in pessoas if p.get("cpf")]
    assert cpfs, "a demonstração tem pessoas com CPF"
    assert all(not c.startswith("cif:") for c in cpfs)


def test_nada_do_outro_escritorio(api):
    texto = _tudo(api["zip"])
    for vestigio in ("Escritório Vizinho", "Igreja do Vizinho", "Pessoa do Vizinho", CPF_DO_OUTRO):
        assert vestigio not in texto


def test_nenhum_segredo_de_acesso(api):
    z = api["zip"]
    for u in _tabela(z, "usuarios"):
        assert not {"senha_hash", "mfa_segredo", "mfa_codigos_recuperacao"} & set(u)
    assert not any("cpf_indice" in p for p in _tabela(z, "pessoas"))
    # Nenhum hash bcrypt em lugar nenhum do arquivo.
    assert "$2b$" not in _tudo(z) and "$2a$" not in _tudo(z)


def test_manifesto_confere_com_o_conteudo(api):
    z = api["zip"]
    manifesto = json.loads(z.read("manifesto.json"))
    assert manifesto["escritorio"]["nome"] == "Escritório Demonstração"
    assert manifesto["gerado_por"]["email"] == "admin@demo.terceiro360.local"
    assert manifesto["dados_pessoais_decifrados"] is True
    for caminho, info in manifesto["arquivos"].items():
        conteudo = z.read(caminho)
        assert hashlib.sha256(conteudo).hexdigest() == info["sha256"], caminho
        if caminho.startswith("tabelas/"):
            assert len(json.loads(conteudo)) == info["linhas"], caminho


def test_referencias_globais_permitem_reencontrar_pelo_codigo(api):
    refs = json.loads(api["zip"].read("referencias_globais.json"))
    assert "ADMINISTRADOR" in {p["codigo"] for p in refs["perfis"]}


def test_sem_permissao_nao_baixa(api):
    r = api["cliente"].get("/api/v1/backup", headers=api["leitor"])
    assert r.status_code == 403


def test_cada_exportacao_fica_registrada(api):
    historico = api["cliente"].get("/api/v1/backup/historico", headers=api["admin"]).json()
    assert historico and historico[0]["por"] == "Administrador de Demonstração"
