"""Resolução de parâmetros: LEI + ESTATUTO + RCPJ + DADOS DA ENTIDADE (§4).

A regra crítica do projeto está aqui: a legislação federal não é a única fonte
de validação, e o estatuto não pode ser sobreposto silenciosamente pela lei.
Quando as fontes se contradizem, o resultado é INCONSISTENCIA_IDENTIFICADA —
o sistema aponta o conflito em vez de escolher sozinho.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.core.enums import OrigemDado, StatusParametro
from app.engines.base import Fundamento, ParametroResolvido
from app.engines.conformidade.base_normativa import BaseNormativaEstatica, ProvedorNormas
from app.engines.conformidade.catalogo import CATALOGO


@dataclass
class ParametroEstatutario:
    """Forma desacoplada do ORM — o motor não depende do banco."""

    chave: str
    valor: object | None = None
    confirmado: bool = False
    dispositivo: str | None = None
    trecho: str | None = None
    origem: OrigemDado = OrigemDado.ESTATUTO
    observacao: str | None = None


# Parâmetros cujo valor legal é um piso de garantia: o estatuto pode facilitar,
# nunca dificultar. Exigir mais que o piso restringe direito assegurado em lei.
_PISOS_DE_GARANTIA = {"CONVOCACAO_FRACAO_ASSOCIADOS"}


class ResolvedorParametros:
    def __init__(
        self,
        parametros: list[ParametroEstatutario] | None = None,
        normas: ProvedorNormas | None = None,
        data_referencia: dt.date | None = None,
    ) -> None:
        self._por_chave = {p.chave: p for p in (parametros or [])}
        self._normas = normas or BaseNormativaEstatica()
        self._data = data_referencia or dt.date.today()
        self._cache: dict[str, ParametroResolvido] = {}

    # ------------------------------------------------------------------ API

    def resolver(self, chave: str) -> ParametroResolvido:
        if chave in self._cache:
            return self._cache[chave]
        resultado = self._resolver(chave)
        self._cache[chave] = resultado
        return resultado

    def resolver_varios(self, chaves: list[str]) -> dict[str, ParametroResolvido]:
        return {c: self.resolver(c) for c in chaves}

    # -------------------------------------------------------------- interno

    def _fundamento_legal(self, chave: str) -> Fundamento | None:
        definicao = CATALOGO.get(chave)
        if not definicao or not definicao.fonte_legal:
            return None
        return self._normas.fundamento(definicao.fonte_legal, definicao.dispositivo_legal, self._data)

    def _resolver(self, chave: str) -> ParametroResolvido:
        definicao = CATALOGO.get(chave)
        param = self._por_chave.get(chave)
        fundamento_legal = self._fundamento_legal(chave)
        supletivo = definicao.valor_supletivo if definicao else None

        # 1. Nada no estatuto.
        if param is None or param.valor in (None, ""):
            if supletivo is not None:
                return ParametroResolvido(
                    chave=chave,
                    valor=supletivo,
                    status=StatusParametro.CONFIRMADO,
                    origem=OrigemDado.LEI,
                    fundamento=fundamento_legal,
                    observacao="Estatuto silente; aplicada a regra legal supletiva.",
                )
            return ParametroResolvido(
                chave=chave,
                status=StatusParametro.NAO_INFORMADO,
                fundamento=fundamento_legal,
                observacao=(
                    definicao.nota
                    if definicao and definicao.nota
                    else "Parâmetro não cadastrado no estatuto da entidade."
                ),
            )

        fundamento_estatuto = Fundamento(
            origem=param.origem,
            referencia="Estatuto Social da entidade",
            dispositivo=param.dispositivo,
            trecho=param.trecho,
        )

        # 2. Cadastrado, mas ainda não confirmado por um responsável (§49).
        if not param.confirmado:
            return ParametroResolvido(
                chave=chave,
                valor=param.valor,
                status=StatusParametro.VALIDACAO_NECESSARIA,
                origem=param.origem,
                fundamento=fundamento_estatuto,
                observacao=(
                    "Valor extraído do estatuto mas ainda não confirmado por um responsável. "
                    "Confirme antes de utilizar em atos."
                ),
            )

        # 3. Confirmado — resta checar conflito com piso legal de garantia.
        if chave in _PISOS_DE_GARANTIA and supletivo is not None:
            conflito = self._conflita_com_piso(param.valor, supletivo)
            if conflito:
                return ParametroResolvido(
                    chave=chave,
                    valor=param.valor,
                    status=StatusParametro.INCONSISTENCIA,
                    origem=param.origem,
                    fundamento=fundamento_estatuto,
                    conflito_com=[f for f in (fundamento_legal,) if f],
                    observacao=(
                        f"O estatuto exige {param.valor}, valor mais restritivo que a garantia "
                        f"legal de {supletivo}. A regra estatutária restringe direito assegurado "
                        f"em lei e precisa de análise jurídica."
                    ),
                )

        return ParametroResolvido(
            chave=chave,
            valor=param.valor,
            status=StatusParametro.CONFIRMADO,
            origem=param.origem,
            fundamento=fundamento_estatuto,
            observacao=param.observacao,
        )

    @staticmethod
    def _conflita_com_piso(valor: object, piso: object) -> bool:
        from app.engines.conformidade.quorum import interpretar_quorum

        exigencia = interpretar_quorum(valor)  # type: ignore[arg-type]
        if exigencia is None or exigencia.fracao is None:
            return False
        try:
            return exigencia.fracao > float(piso)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
