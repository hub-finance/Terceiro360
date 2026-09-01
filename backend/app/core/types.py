"""Tipos portáveis entre PostgreSQL e SQLite.

O sistema roda em PostgreSQL; SQLite é usado nos testes. Os decorators abaixo
mantêm o mesmo comportamento nos dois dialetos.
"""
from __future__ import annotations

import uuid

from sqlalchemy import CHAR, JSON, String, TypeDecorator
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


class EnumType(TypeDecorator):
    """Guarda o *valor* do enum como texto e devolve o membro do enum.

    Sem isto, um `SituacaoMembro.ATIVO` gravado volta do banco como a string
    `"ATIVO"`, e comparações como `situacao is SituacaoMembro.ATIVO` passam a
    ser falsas silenciosamente — o tipo de erro que faz um ato parecer regular
    quando não é. Guardar texto (em vez de um ENUM nativo do PostgreSQL) mantém
    a migração simples quando um valor novo é acrescentado ao vocabulário.
    """

    impl = String
    cache_ok = True

    def __init__(self, enum_class, length: int = 40, **kw):
        self.enum_class = enum_class
        super().__init__(length=length, **kw)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value
        # Valor desconhecido falha aqui, e não silenciosamente lá na frente.
        return self.enum_class(value).value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum_class(value)


class DadoCifrado(TypeDecorator):
    """Coluna que guarda o valor cifrado e devolve em claro (§33).

    O código da aplicação continua lendo `pessoa.cpf` como texto normal; quem
    lê o banco direto vê `cif:gAAAAA...`. É a diferença entre um backup vazado
    ser um incidente de segurança e ser um vazamento de dado pessoal.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        from app.core.cifra import cifrar

        return cifrar(value)

    def process_result_value(self, value, dialect):
        from app.core.cifra import decifrar

        return decifrar(value)
