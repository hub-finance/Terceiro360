"""Agendador do TERCEIRO360 (§21, §37).

Duas tarefas, uma ideia: o sistema não pode depender de alguém lembrar de
olhar. Prazo de mandato vence sozinho e lei muda sozinha; quem não varre
periodicamente descobre tarde.

Roda como comando (`python -m app.agendador tudo`), não como processo residente,
para que a operação escolha o disparador — cron, systemd timer, Cloud Scheduler,
GitHub Actions. Um processo a menos para monitorar, e a execução fica registrada
em `execucoes_agendador` de qualquer jeito.
"""
from app.agendador.tarefas import rodar_prazos, rodar_tudo, rodar_vigilias

__all__ = ["rodar_prazos", "rodar_vigilias", "rodar_tudo"]
