"""Ambiente das migrações.

A URL vem sempre da configuração da aplicação (`T360_DATABASE_URL`), nunca do
alembic.ini — assim a mesma migração roda em desenvolvimento, homologação e
produção sem editar arquivo versionado.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.models import Base  # importa todos os mapeamentos

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def _url_do_banco() -> str:
    """URL explícita vence; na falta dela, a da aplicação.

    Quem chama a migração de dentro de um teste ou de um script de implantação
    passa a URL pela Config. Sobrescrever isso aqui faria a migração rodar no
    banco errado — em silêncio, que é o pior jeito de errar de banco.
    """
    informada = config.get_main_option("sqlalchemy.url", None)
    if informada:
        return informada
    return settings.database_url


config.set_main_option("sqlalchemy.url", _url_do_banco().replace("%", "%%"))
target_metadata = Base.metadata


def renderizar_item(tipo_item, objeto, autogen_context):
    """Escreve na migração o tipo do *banco*, não a classe Python.

    `GUID` e `EnumType` são decoradores da aplicação. Se a migração os citasse,
    renomear ou mover a classe quebraria migrações antigas — que precisam
    continuar rodando anos depois, exatamente como foram escritas.
    """
    if tipo_item != "type":
        return False

    from app.core.types import GUID, EnumType

    if isinstance(objeto, GUID):
        autogen_context.imports.add("from sqlalchemy.dialects import postgresql")
        return "postgresql.UUID(as_uuid=True)"
    if isinstance(objeto, EnumType):
        return f"sa.String(length={objeto.impl.length or 40})"
    return False


def incluir_objeto(objeto, nome, tipo, reflexivo, comparar_com):
    """Mantém fora das migrações o que não é do domínio (ex.: tabelas de
    extensões instaladas no schema public)."""
    if tipo == "table" and nome in {"spatial_ref_sys"}:
        return False
    return True


def executar_offline() -> None:
    """Gera o SQL sem conectar — útil para revisão do DDL antes de aplicar."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=incluir_objeto,
        render_item=renderizar_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def executar_online() -> None:
    conectavel = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectavel.connect() as conexao:
        context.configure(
            connection=conexao,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=incluir_objeto,
            render_item=renderizar_item,
            # Uma migração que falha no meio não pode deixar o banco meio migrado.
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    executar_offline()
else:
    executar_online()
