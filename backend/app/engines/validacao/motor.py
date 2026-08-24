"""Motor de validação — executa os checks e consolida o semáforo (§12, §13)."""
from __future__ import annotations

from app.core.enums import Semaforo
from app.engines.base import Achado, ResultadoValidacao
from app.engines.validacao import checks as _checks  # noqa: F401  (registra os checks)
from app.engines.validacao.contexto import ContextoValidacao
from app.engines.validacao.registro import checks_para


def validar(ctx: ContextoValidacao, grupos: tuple[str, ...] | None = None) -> ResultadoValidacao:
    achados: list[Achado] = []
    for check in checks_para(ctx.tipo_evento, grupos):
        try:
            achados.extend(check.funcao(ctx))
        except Exception as exc:  # um check com defeito não pode derrubar o ato
            achados.append(
                Achado(
                    codigo=f"CHECK_FALHOU::{check.codigo}",
                    severidade=Semaforo.PENDENCIA,
                    titulo=f"Verificação “{check.descricao}” não pôde ser concluída",
                    mensagem=f"Erro interno ao executar a verificação: {exc}. "
                             f"O ato precisa de conferência manual neste ponto.",
                )
            )

    resultado = ResultadoValidacao(achados=achados)
    resultado.parametros = dict(ctx.resolvedor._cache)
    return resultado
