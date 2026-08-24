"""Tipos portáveis entre PostgreSQL e SQLite.

O sistema roda em PostgreSQL; SQLite é usado nos testes. Os decorators abaixo
mantêm o mesmo comportamento nos dois dialetos.
"""
from __future__ import annotations

import uuid

from sqlalchemy import CHAR, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID


class GUID(TypeDecorator):
    """UUID nativo no PostgreSQL, CHAR(36) nos demais dialetos."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return value if dialect.name == "postgresql" else str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def JSONType():
    """JSONB no PostgreSQL, JSON nos demais dialetos."""
    return JSON().with_variant(JSONB(), "postgresql")


def novo_id() -> uuid.UUID:
    return uuid.uuid4()
