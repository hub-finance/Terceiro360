"""Sessão, engine e Base declarativa."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Iterator

from sqlalchemy import DateTime, MetaData, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.core.config import settings
from app.core.types import GUID, novo_id

convencao = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convencao)


class TimestampMixin:
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=novo_id)


def _pelo_pooler(url: str) -> bool:
    """Detecta o pooler em modo transação do Supabase.

    Ele atende na porta 6543 (a 5432 é a conexão direta) e no host
    `pooler.supabase.com`. Em modo transação, cada consulta pode cair numa
    conexão diferente do banco — e é isso que quebra prepared statements.
    """
    return ":6543" in url or "pooler.supabase.com" in url


def _connect_args() -> dict:
    if settings.database_url.startswith("sqlite"):
        return {"check_same_thread": False}

    args: dict = {}
    if _pelo_pooler(settings.database_url):
        # O psycopg prepara automaticamente a consulta repetida pela quinta vez
        # e depois a reaproveita pelo nome. Passando pelo pooler em modo
        # transação, a conexão seguinte não conhece aquele nome e a aplicação
        # começa a receber "prepared statement does not exist" — de forma
        # intermitente, só sob carga, e nunca em desenvolvimento.
        args["prepare_threshold"] = None
    return args


def _pool() -> dict:
    """Tamanho do pool. O pooler já multiplexa; abrir muitas conexões contra
    ele só consome a cota do projeto sem ganho nenhum."""
    if settings.database_url.startswith("sqlite"):
        return {}
    if _pelo_pooler(settings.database_url):
        return {"pool_size": 5, "max_overflow": 5, "pool_recycle": 300}
    return {"pool_size": 10, "max_overflow": 10, "pool_recycle": 1800}


engine = create_engine(
    settings.database_url,
    connect_args=_connect_args(),
    future=True,
    # Conexão que o provedor derrubou por ociosidade é descoberta na hora de
    # usar, não no meio de uma transação do usuário.
    pool_pre_ping=True,
    **_pool(),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
