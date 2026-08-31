"""Datas e horas do TERCEIRO360.

Todas as colunas de instante são `DateTime(timezone=True)`. O PostgreSQL as
devolve com fuso; o SQLite, sem. Comparar uma com a outra levanta
`can't subtract offset-naive and offset-aware datetimes` — e o erro só aparece
no banco de produção, que é o pior lugar para descobri-lo.

Por isso: grave sempre com `agora()`, e normalize com `garantir_utc()` tudo que
vier do banco antes de comparar.
"""
from __future__ import annotations

import datetime as dt

UTC = dt.timezone.utc


def agora() -> dt.datetime:
    """Instante atual, sempre com fuso."""
    return dt.datetime.now(UTC)


def hoje() -> dt.date:
    return agora().date()


def garantir_utc(momento: dt.datetime | None) -> dt.datetime | None:
    """Anexa UTC ao instante que vier sem fuso (o caso do SQLite)."""
    if momento is None:
        return None
    if momento.tzinfo is None:
        return momento.replace(tzinfo=UTC)
    return momento.astimezone(UTC)


def dias_entre(inicio: dt.datetime | None, fim: dt.datetime | None) -> int | None:
    """Diferença em dias, imune à mistura de instantes com e sem fuso."""
    a, b = garantir_utc(inicio), garantir_utc(fim)
    if a is None or b is None:
        return None
    return (b - a).days
