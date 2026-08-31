"""TERCEIRO360 IA — camada auxiliar (§37).

A IA propõe; o responsável confirma. Nenhuma sugestão vira parâmetro válido
sem passar pela confirmação humana (§46, §49).
"""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, entidade_do_escopo, exigir, sessao_atual
from app.core.enums import OrigemDado
from app.modules.entidades.models import Entidade
from app.modules.ia.extracao import extrair_parametros
from app.modules.ia.models import AnaliseIA, SugestaoIA
from app.modules.juridico.models import Estatuto, EstatutoParametro, EstatutoVersao

router = APIRouter(prefix="/ia", tags=["IA"])


class ExtracaoIn(BaseModel):
    estatuto_versao_id: uuid.UUID
    texto: str | None = None


@router.post("/extrair-estatuto")
def extrair(
    dados: ExtracaoIn,
    sessao: Sessao = Depends(exigir("ia:analisar")),
    db: Session = Depends(get_db),
):
    """§49 — 'IA EXTRAI REGRAS'. O passo seguinte é sempre a confirmação humana."""
    versao = db.get(EstatutoVersao, dados.estatuto_versao_id)
    if versao is None:
        raise HTTPException(404, "Versão do estatuto não encontrada.")
    estatuto = db.get(Estatuto, versao.estatuto_id)
    entidade = db.get(Entidade, estatuto.entidade_id)
    if entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Versão do estatuto não encontrada.")

    texto = dados.texto or versao.texto
    if not texto:
        raise HTTPException(
            422,
            "Não há texto do estatuto para analisar. Envie o texto no corpo da requisição "
            "ou cadastre-o na versão.",
        )

    resultado = extrair_parametros(texto)

    analise = AnaliseIA(
        entidade_id=entidade.id,
        estatuto_versao_id=versao.id,
        tipo="EXTRACAO_ESTATUTO",
        modelo=resultado.metodo,
        resumo=(
            f"{len(resultado.sugestoes)} parâmetro(s) localizado(s) no texto; "
            f"{len(resultado.nao_localizados)} não localizado(s)."
        ),
        solicitado_por_id=sessao.usuario.id,
        concluida_em=dt.datetime.utcnow(),
    )
    db.add(analise)
    db.flush()

    for s in resultado.sugestoes:
        db.add(SugestaoIA(
            analise_id=analise.id,
            chave=s.chave,
            valor_sugerido=str(s.valor),
            dispositivo=s.dispositivo,
            trecho=s.trecho,
            confianca=s.confianca,
            status="SUGERIDA" if s.confianca >= 0.7 else "VALIDACAO_NECESSARIA",
            pergunta_validacao=s.pergunta_validacao,
        ))
    db.commit()
    db.refresh(analise)

    return {
        "analise_id": str(analise.id),
        "metodo": resultado.metodo,
        "aviso": "Estas são sugestões extraídas do texto. Nenhuma delas é usada nas "
                 "validações antes de ser confirmada por um responsável.",
        "sugestoes": [
            {
                "chave": s.chave, "valor": s.valor, "dispositivo": s.dispositivo,
                "trecho": s.trecho, "confianca": s.confianca,
                "pergunta_validacao": s.pergunta_validacao,
            }
            for s in resultado.sugestoes
        ],
        "nao_localizados": resultado.nao_localizados,
    }


@router.get("/analises/{analise_id}")
def obter_analise(
    analise_id: uuid.UUID,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    analise = db.get(AnaliseIA, analise_id)
    if analise is None:
        raise HTTPException(404, "Análise não encontrada.")
    entidade = db.get(Entidade, analise.entidade_id)
    if entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Análise não encontrada.")
    return {
        "id": str(analise.id), "tipo": analise.tipo, "resumo": analise.resumo,
        "modelo": analise.modelo,
        "concluida_em": analise.concluida_em.isoformat() if analise.concluida_em else None,
        "sugestoes": [
            {
                "id": str(s.id), "chave": s.chave, "valor": s.valor_sugerido,
                "dispositivo": s.dispositivo, "trecho": s.trecho,
                "confianca": float(s.confianca) if s.confianca is not None else None,
                "status": s.status, "pergunta_validacao": s.pergunta_validacao,
                "aceita": s.aceita_em is not None,
            }
            for s in analise.sugestoes
        ],
    }


class AceiteIn(BaseModel):
    sugestoes: list[uuid.UUID]


@router.post("/analises/{analise_id}/aceitar")
def aceitar(
    analise_id: uuid.UUID,
    dados: AceiteIn,
    sessao: Sessao = Depends(exigir("juridico:estatuto:editar")),
    db: Session = Depends(get_db),
):
    """Converte sugestões aceitas em parâmetros do estatuto — já confirmados,
    porque houve ato humano de aceite (§49)."""
    analise = db.get(AnaliseIA, analise_id)
    if analise is None:
        raise HTTPException(404, "Análise não encontrada.")
    entidade = db.get(Entidade, analise.entidade_id)
    if entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Análise não encontrada.")
    if analise.estatuto_versao_id is None:
        raise HTTPException(422, "Análise não está vinculada a uma versão do estatuto.")

    agora = dt.datetime.utcnow()
    existentes = {
        p.chave: p
        for p in db.scalars(
            select(EstatutoParametro).where(
                EstatutoParametro.versao_id == analise.estatuto_versao_id
            )
        ).all()
    }

    aceitas = 0
    for sugestao_id in dados.sugestoes:
        s = db.get(SugestaoIA, sugestao_id)
        if s is None or s.analise_id != analise.id:
            continue
        p = existentes.get(s.chave) or EstatutoParametro(
            versao_id=analise.estatuto_versao_id, chave=s.chave
        )
        p.valor = s.valor_sugerido
        p.dispositivo = s.dispositivo
        p.trecho = s.trecho
        p.origem = OrigemDado.IA_SUGERIDO
        p.confianca = s.confianca
        p.confirmado = True
        p.confirmado_por_id = sessao.usuario.id
        p.confirmado_em = agora
        db.add(p)

        s.status = "ACEITA"
        s.aceita_por_id = sessao.usuario.id
        s.aceita_em = agora
        db.add(s)
        aceitas += 1

    db.commit()
    return {"aceitas": aceitas, "confirmadas_por": sessao.usuario.nome}
