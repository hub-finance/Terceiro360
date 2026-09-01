"""Comando do agendador.

    python -m app.agendador tudo
    python -m app.agendador vigilias
    python -m app.agendador prazos --json

Pensado para cron ou timer:

    0 6 * * *  cd /app && python -m app.agendador tudo >> /var/log/t360.log 2>&1

Sai com código 1 quando a rodada teve falhas, para que o supervisor perceba.
"""
from __future__ import annotations

import argparse
import json
import sys

from app.agendador.tarefas import TAREFAS, executar
from app.core.db import SessionLocal


def main(argv: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(
        prog="python -m app.agendador",
        description="Varreduras periódicas do TERCEIRO360.",
    )
    analisador.add_argument(
        "tarefa",
        choices=[*[t.lower() for t in TAREFAS], "tudo"],
        help="vigilias = confere as fontes normativas; prazos = recalcula a "
             "agenda e dispara alertas; tudo = as duas, na ordem.",
    )
    analisador.add_argument("--json", action="store_true", help="Saída em JSON.")
    argumentos = analisador.parse_args(argv)

    nomes = list(TAREFAS) if argumentos.tarefa == "tudo" else [argumentos.tarefa.upper()]
    saida = []
    with SessionLocal() as db:
        for nome in nomes:
            registro = executar(db, nome, acionada_por="AGENDADOR")
            saida.append({
                "tarefa": registro.tarefa,
                "resultado": registro.resultado,
                "duracao_s": round(registro.duracao_segundos or 0, 2),
                "numeros": registro.numeros,
                "falhas": registro.falhas,
                "detalhe": registro.detalhe,
            })

    if argumentos.json:
        print(json.dumps(saida, ensure_ascii=False, indent=2))
    else:
        for linha in saida:
            print(f"[{linha['resultado']}] {linha['tarefa']} "
                  f"({linha['duracao_s']}s): {linha['detalhe']}")
            for falha in linha["falhas"]:
                print(f"    ! {falha['alvo']}: {falha['erro']}", file=sys.stderr)

    return 1 if any(linha["resultado"] != "OK" for linha in saida) else 0


if __name__ == "__main__":
    raise SystemExit(main())
