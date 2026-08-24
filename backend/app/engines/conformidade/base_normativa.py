"""Provedor de fundamentos normativos para os motores.

Os motores nunca citam uma norma "de cabeça": pedem o fundamento a um provedor,
que devolve a *versão* aplicável à data do ato e informa se aquela redação já
passou por curadoria humana (§38, §46).
"""
from __future__ import annotations

import datetime as dt
from typing import Protocol

from app.core.enums import OrigemDado
from app.engines.base import Fundamento
from app.seeds.fontes import FONTES_POR_CHAVE


class ProvedorNormas(Protocol):
    def fundamento(
        self, chave_fonte: str, dispositivo: str | None = None, data: dt.date | None = None
    ) -> Fundamento | None: ...


class BaseNormativaEstatica:
    """Lê a base embarcada em `app.seeds.fontes`.

    Usada em testes e como piso quando o banco ainda não foi populado. As
    redações aqui não estão curadas — `curado=False` é propagado até a interface.
    """

    def fundamento(
        self, chave_fonte: str, dispositivo: str | None = None, data: dt.date | None = None
    ) -> Fundamento | None:
        fonte = FONTES_POR_CHAVE.get(chave_fonte)
        if fonte is None:
            return None
        if data and fonte.vigente_desde > data:
            return None
        trecho = None
        if dispositivo:
            achado = next((d for d in fonte.dispositivos if d.identificacao == dispositivo), None)
            if achado is None:
                # Nunca inventar dispositivo: cita a norma sem o artigo.
                dispositivo = None
            else:
                trecho = achado.sintese
        return Fundamento(
            origem=OrigemDado.LEI,
            referencia=fonte.identificacao,
            dispositivo=dispositivo,
            trecho=trecho,
            versao_norma=f"vigente desde {fonte.vigente_desde:%d/%m/%Y}",
            curado=False,
            url=fonte.url_oficial,
        )


class BaseNormativaDB:
    """Lê a Central de Fontes do banco, respeitando vigência e curadoria."""

    def __init__(self, db):
        self._db = db
        self._fallback = BaseNormativaEstatica()

    def fundamento(
        self, chave_fonte: str, dispositivo: str | None = None, data: dt.date | None = None
    ) -> Fundamento | None:
        from sqlalchemy import select

        from app.modules.normativo.models import Dispositivo, FonteJuridica

        data = data or dt.date.today()
        fonte = self._db.scalar(select(FonteJuridica).where(FonteJuridica.chave == chave_fonte))
        if fonte is None:
            return self._fallback.fundamento(chave_fonte, dispositivo, data)

        versao = fonte.versao_vigente_em(data)
        if versao is None:
            return None

        trecho = None
        if dispositivo:
            disp = self._db.scalar(
                select(Dispositivo).where(
                    Dispositivo.versao_id == versao.id,
                    Dispositivo.identificacao == dispositivo,
                )
            )
            if disp is None:
                dispositivo = None
            else:
                trecho = disp.texto

        return Fundamento(
            origem=OrigemDado.LEI,
            referencia=fonte.identificacao,
            dispositivo=dispositivo,
            trecho=trecho,
            versao_norma=(
                f"vigente desde {versao.vigente_desde:%d/%m/%Y}" if versao.vigente_desde else None
            ),
            curado=versao.curada,
            url=fonte.url_oficial,
        )
