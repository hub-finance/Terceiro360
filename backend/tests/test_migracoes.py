"""As migrações precisam descrever exatamente o modelo (§20).

Modelo e migração que divergem produzem o pior tipo de falha: o código espera
uma coluna que o banco de produção não tem, e o erro só aparece na hora do ato.
Este teste compara os dois e falha se sobrar diferença.

Roda apenas quando há um PostgreSQL apontado — comparar schema em SQLite não
prova nada sobre produção.
"""
from __future__ import annotations

import os
import pathlib

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.skipif(
    not os.getenv("T360_TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="exige um PostgreSQL: defina T360_TEST_DATABASE_URL",
)

RAIZ = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture
def banco_migrado():
    """Sobe um banco limpo aplicando as migrações, e devolve a engine."""
    from alembic import command
    from alembic.config import Config

    url = os.environ["T360_TEST_DATABASE_URL"]
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))

    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


def test_migracoes_reproduzem_o_modelo(banco_migrado):
    """Depois de aplicar tudo, o autogenerate não pode ter o que fazer."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.models import Base

    with banco_migrado.connect() as conexao:
        contexto = MigrationContext.configure(
            conexao, opts={"compare_type": True, "compare_server_default": True}
        )
        diferencas = compare_metadata(contexto, Base.metadata)

    relevantes = [d for d in diferencas if _relevante(d)]
    assert not relevantes, (
        "Modelo e migrações divergiram. Gere a migração que falta com:\n"
        "  alembic revision --autogenerate -m \"<o que mudou>\"\n\n"
        "Diferenças encontradas:\n  " + "\n  ".join(str(d) for d in relevantes)
    )


def test_migracoes_sobem_e_descem(banco_migrado):
    """Uma migração que não desce não pode ser revertida em produção."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "alembic"))
    config.set_main_option("sqlalchemy.url", os.environ["T360_TEST_DATABASE_URL"])

    command.downgrade(config, "base")
    with banco_migrado.connect() as conexao:
        restantes = conexao.execute(text(
            "select count(*) from information_schema.tables "
            "where table_schema='public' and table_name <> 'alembic_version'"
        )).scalar()
    assert restantes == 0, f"{restantes} tabela(s) sobraram após o downgrade"

    command.upgrade(config, "head")
    with banco_migrado.connect() as conexao:
        total = conexao.execute(text(
            "select count(*) from information_schema.tables "
            "where table_schema='public' and table_name <> 'alembic_version'"
        )).scalar()
    assert total == 52, f"esperava 52 tabelas, o banco tem {total}"


def test_tipos_nativos_do_postgres_foram_usados(banco_migrado):
    """UUID e JSONB nativos: é o que dá índice e consulta decentes."""
    with banco_migrado.connect() as conexao:
        uuids = conexao.execute(text(
            "select count(*) from information_schema.columns "
            "where table_schema='public' and data_type='uuid'"
        )).scalar()
        jsonb = conexao.execute(text(
            "select count(*) from information_schema.columns "
            "where table_schema='public' and data_type='jsonb'"
        )).scalar()
    assert uuids > 100, f"apenas {uuids} colunas UUID nativas"
    assert jsonb > 20, f"apenas {jsonb} colunas JSONB nativas"


def _relevante(diferenca) -> bool:
    """Ignora ruído que o autogenerate produz sem ser divergência real."""
    if isinstance(diferenca, list):
        return any(_relevante(d) for d in diferenca)
    if not isinstance(diferenca, tuple):
        return True
    acao = diferenca[0]
    # O SQLAlchemy às vezes reporta variação de tipo entre VARCHAR equivalentes.
    if acao == "modify_type":
        return False
    return True
