"""Registro das execuções do agendador (§21, §37, §46).

Num sistema de conformidade, "a vigília rodou ontem?" precisa ter resposta —
e a resposta não pode ser o log do servidor, que ninguém guarda por anos. Cada
execução deixa aqui uma linha com o que fez, quanto tempo levou e o que falhou.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UUIDMixin
from app.core.types import JSONType


class ExecucaoTarefa(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "execucoes_agendador"

    tarefa: Mapped[str] = mapped_column(String(40), index=True)  # VIGILIAS|PRAZOS
    iniciada_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    concluida_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # OK = correu inteira; PARCIAL = correu com falhas isoladas; ERRO = abortou.
    resultado: Mapped[str] = mapped_column(String(10), default="OK", index=True)
    # Contadores da rodada (verificadas, mudancas, alertas...) — o que responde
    # "o que esse agendador fez de útil no mês passado".
    numeros: Mapped[dict] = mapped_column(JSONType(), default=dict)
    falhas: Mapped[list] = mapped_column(JSONType(), default=list)
    detalhe: Mapped[str | None] = mapped_column(Text)
    acionada_por: Mapped[str] = mapped_column(String(20), default="AGENDADOR")  # ou MANUAL

    @property
    def duracao_segundos(self) -> float | None:
        if self.concluida_em is None:
            return None
        return (self.concluida_em - self.iniciada_em).total_seconds()
