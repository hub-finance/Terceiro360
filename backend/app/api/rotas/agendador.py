"""Agendador e alertas (§21, §37).

A varredura roda por fora, como comando. Estas rotas existem para responder
duas perguntas que a tela precisa fazer: *ela rodou?* e *o que ela achou?*
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agendador.tarefas import TAREFAS, executar
from app.core.db import get_db
from app.core.deps import Sessao, exigir, sessao_atual
from app.core.enums import StatusPendencia, StatusPrazo
from app.core.tempo import agora, hoje
from app.modules.agendador.models import ExecucaoTarefa
from app.modules.entidades.models import Entidade
from app.modules.prazos.models import Notificacao, Pendencia, Prazo

router = APIRouter(tags=["Agendador"])


@router.get("/agendador/execucoes")
def listar_execucoes(
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    limite: int = Query(default=20, le=100),
):
    execucoes = db.scalars(
        select(ExecucaoTarefa).order_by(ExecucaoTarefa.iniciada_em.desc()).limit(limite)
    ).all()
    return [
        {
            "id": str(e.id), "tarefa": e.tarefa, "resultado": e.resultado,
            "iniciada_em": e.iniciada_em.isoformat(),
            "concluida_em": e.concluida_em.isoformat() if e.concluida_em else None,
            "duracao_s": e.duracao_segundos,
            "numeros": e.numeros, "falhas": e.falhas, "detalhe": e.detalhe,
            "acionada_por": e.acionada_por,
        }
        for e in execucoes
    ]


@router.post("/agendador/executar/{tarefa}")
def executar_agora(
    tarefa: str,
    sessao: Sessao = Depends(exigir("normativo:monitorar")),
    db: Session = Depends(get_db),
):
    """Roda a varredura fora do horário — para não esperar o dia seguinte
    quando se sabe que uma lei acabou de mudar."""
    if tarefa.upper() not in TAREFAS:
        raise HTTPException(422, f"Tarefa inválida. Use: {', '.join(t.lower() for t in TAREFAS)}.")
    registro = executar(db, tarefa, acionada_por="MANUAL")
    return {
        "tarefa": registro.tarefa, "resultado": registro.resultado,
        "detalhe": registro.detalhe, "numeros": registro.numeros,
        "falhas": registro.falhas,
    }


@router.get("/notificacoes")
def minhas_notificacoes(
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    apenas_nao_lidas: bool = True,
    limite: int = Query(default=50, le=200),
):
    consulta = select(Notificacao).where(Notificacao.usuario_id == sessao.usuario.id)
    if apenas_nao_lidas:
        consulta = consulta.where(Notificacao.lida.is_(False))
    itens = db.scalars(consulta.order_by(Notificacao.criado_em.desc()).limit(limite)).all()
    return [
        {
            "id": str(n.id), "titulo": n.titulo, "mensagem": n.mensagem,
            "lida": n.lida, "criado_em": n.criado_em.isoformat(),
            "entidade_id": str(n.entidade_id) if n.entidade_id else None,
            "prazo_id": str(n.prazo_id) if n.prazo_id else None,
        }
        for n in itens
    ]


@router.post("/notificacoes/{notificacao_id}/lida")
def marcar_lida(
    notificacao_id: uuid.UUID,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    notificacao = db.get(Notificacao, notificacao_id)
    if notificacao is None or notificacao.usuario_id != sessao.usuario.id:
        raise HTTPException(404, "Notificação não encontrada.")
    notificacao.lida = True
    db.add(notificacao)
    db.commit()
    return {"id": str(notificacao.id), "lida": True}


@router.get("/entidades/{entidade_id}/prazos/registrados")
def prazos_registrados(
    entidade_id: uuid.UUID,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    """Os prazos materializados pelo agendador — com o histórico de alertas.

    Diferente de `/entidades/{id}/prazos`, que recalcula a agenda na hora: aqui
    se vê o que o sistema já vinha acompanhando, inclusive o que já venceu.
    """
    entidade = db.get(Entidade, entidade_id)
    if entidade is None or entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Entidade não encontrada.")

    referencia = hoje()
    prazos = db.scalars(
        select(Prazo).where(Prazo.entidade_id == entidade.id).order_by(Prazo.data_limite)
    ).all()
    return [
        {
            "id": str(p.id), "tipo": str(p.tipo), "descricao": p.descricao,
            "data_limite": p.data_limite.isoformat(),
            "dias_restantes": p.dias_restantes(referencia),
            "status": str(p.status), "origem": p.origem, "fundamento": p.fundamento,
            "alertas_disparados": p.alertas_disparados,
            "chave": p.chave_idempotencia,
        }
        for p in prazos
    ]


@router.get("/pendencias")
def pendencias_abertas(
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    entidade_id: uuid.UUID | None = None,
):
    """Central de pendências (§43).

    Inclui as pendências sem entidade — as da base normativa, que valem para
    todos os clientes e não pertencem a nenhuma organização em particular.
    """
    permitidas = {
        e.id for e in db.scalars(
            select(Entidade).where(Entidade.cliente_id == sessao.cliente_id)
        ).all()
    }
    if entidade_id and entidade_id not in permitidas:
        raise HTTPException(404, "Entidade não encontrada.")

    consulta = select(Pendencia).where(
        Pendencia.status.in_([StatusPendencia.ABERTA, StatusPendencia.EM_ANDAMENTO])
    )
    if entidade_id:
        consulta = consulta.where(Pendencia.entidade_id == entidade_id)

    itens = [
        p for p in db.scalars(consulta.order_by(Pendencia.criado_em.desc())).all()
        if p.entidade_id is None or p.entidade_id in permitidas
    ]
    nomes = {e.id: e.razao_social for e in db.scalars(
        select(Entidade).where(Entidade.cliente_id == sessao.cliente_id)
    ).all()}
    return [
        {
            "id": str(p.id), "tipo": p.tipo, "codigo": p.codigo,
            "descricao": p.descricao, "detalhamento": p.detalhamento,
            "prioridade": str(p.prioridade), "status": str(p.status),
            "origem": p.origem,
            "entidade": nomes.get(p.entidade_id) if p.entidade_id else None,
            "entidade_id": str(p.entidade_id) if p.entidade_id else None,
            "prazo_limite": p.prazo_limite.isoformat() if p.prazo_limite else None,
            "criado_em": p.criado_em.isoformat(),
        }
        for p in itens
    ]


@router.post("/pendencias/{pendencia_id}/resolver")
def resolver_pendencia(
    pendencia_id: uuid.UUID,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    pendencia = db.get(Pendencia, pendencia_id)
    if pendencia is None:
        raise HTTPException(404, "Pendência não encontrada.")
    if pendencia.entidade_id is not None:
        entidade = db.get(Entidade, pendencia.entidade_id)
        if entidade is None or entidade.cliente_id != sessao.cliente_id:
            raise HTTPException(404, "Pendência não encontrada.")
    pendencia.status = StatusPendencia.RESOLVIDA
    pendencia.resolvida_em = agora()
    db.add(pendencia)
    db.commit()
    return {"id": str(pendencia.id), "status": str(pendencia.status)}
