"""Registro de checks do motor de validação.

Cada check declara a que eventos se aplica. Adicionar um ato novo ao sistema é
registrar checks — não é reescrever o motor (§55).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from app.engines.base import Achado
from app.engines.validacao.contexto import ContextoValidacao

FuncaoCheck = Callable[[ContextoValidacao], Iterable[Achado]]


@dataclass(frozen=True)
class Check:
    codigo: str
    descricao: str
    funcao: FuncaoCheck
    eventos: tuple[str, ...]      # ("*",) = todos
    grupo: str = "JURIDICO"
    fundamentos: tuple[str, ...] = ()   # chaves de fonte, para o cálculo de impacto

    def aplica_a(self, tipo_evento: str) -> bool:
        return "*" in self.eventos or tipo_evento in self.eventos


REGISTRO: dict[str, Check] = {}


def check(
    codigo: str,
    descricao: str,
    eventos: tuple[str, ...] = ("*",),
    grupo: str = "JURIDICO",
    fundamentos: tuple[str, ...] = (),
):
    def decorator(func: FuncaoCheck) -> FuncaoCheck:
        REGISTRO[codigo] = Check(codigo, descricao, func, eventos, grupo, fundamentos)
        return func

    return decorator


def checks_para(tipo_evento: str, grupos: tuple[str, ...] | None = None) -> list[Check]:
    selecionados = [c for c in REGISTRO.values() if c.aplica_a(tipo_evento)]
    if grupos:
        selecionados = [c for c in selecionados if c.grupo in grupos]
    return selecionados
