"""Cadastro central da entidade e dashboard (§6, §51)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, entidade_do_escopo, exigir, sessao_atual
from app.core.enums import TipoEntidade
from app.modules.entidades.models import Entidade
from app.modules.governanca.servicos import agenda, dashboard, retrato
from app.modules.governanca.models import ScoreSnapshot
from app.engines.inconsistencias.motor import varrer
from app.engines.score.motor import calcular
from app.modules.governanca.servicos import fotografia_score

router = APIRouter(prefix="/entidades", tags=["Entidades"])


class EntidadeIn(BaseModel):
    razao_social: str = Field(min_length=3, max_length=300)
    nome_fantasia: str | None = None
    cnpj: str | None = None
    tipo_entidade: TipoEntidade = TipoEntidade.ASSOCIACAO
    data_constituicao: dt.date | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    municipio: str | None = None
    uf: str | None = Field(default=None, max_length=2)
    cep: str | None = None
    email: str | None = None
    telefone: str | None = None
    site: str | None = None
    rcpj_id: uuid.UUID | None = None
    codigo_interno: str | None = None


class EntidadeOut(BaseModel):
    id: uuid.UUID
    razao_social: str
    nome_fantasia: str | None
    cnpj: str | None
    tipo_entidade: str
    municipio: str | None
    uf: str | None
    ativa: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[EntidadeOut])
def listar(
    sessao: Sessao = Depends(exigir("entidades:ler")),
    db: Session = Depends(get_db),
    busca: str | None = Query(default=None),
):
    consulta = select(Entidade).where(Entidade.cliente_id == sessao.cliente_id)
    if sessao.entidades_permitidas is not None:
        consulta = consulta.where(Entidade.id.in_(sessao.entidades_permitidas))
    if busca:
        termo = f"%{busca}%"
        consulta = consulta.where(Entidade.razao_social.ilike(termo))
    return db.scalars(consulta.order_by(Entidade.razao_social)).all()


@router.post("", response_model=EntidadeOut, status_code=201)
def criar(
    dados: EntidadeIn,
    sessao: Sessao = Depends(exigir("entidades:criar")),
    db: Session = Depends(get_db),
):
    entidade = Entidade(cliente_id=sessao.cliente_id, **dados.model_dump())
    db.add(entidade)
    db.commit()
    db.refresh(entidade)
    return entidade


@router.get("/{entidade_id}", response_model=EntidadeOut)
def obter(entidade: Entidade = Depends(entidade_do_escopo)):
    return entidade


@router.put("/{entidade_id}", response_model=EntidadeOut)
def atualizar(
    dados: EntidadeIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("entidades:editar")),
    db: Session = Depends(get_db),
):
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(entidade, campo, valor)
    db.add(entidade)
    db.commit()
    db.refresh(entidade)
    return entidade


@router.get("/{entidade_id}/dashboard")
def painel(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    return dashboard(db, entidade)


@router.get("/{entidade_id}/score")
def score(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    registrar: bool = Query(default=False, description="Grava um snapshot do score"),
):
    resultado = calcular(fotografia_score(db, entidade))
    if registrar:
        db.add(ScoreSnapshot(
            entidade_id=entidade.id,
            data_referencia=resultado.data_referencia,
            pontuacao=resultado.pontuacao,
            classificacao=resultado.classificacao,
            criterios=resultado.to_dict()["criterios"],
        ))
        db.commit()
    return resultado.to_dict()


@router.get("/{entidade_id}/pendencias")
def pendencias(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    return [i.to_dict() for i in varrer(retrato(db, entidade))]


@router.get("/{entidade_id}/prazos")
def prazos(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    hoje = dt.date.today()
    ag = agenda(db, entidade, hoje)
    return {
        "prazos": [
            {
                "chave": p.chave, "tipo": p.tipo.value, "descricao": p.descricao,
                "data_limite": p.data_limite.isoformat(),
                "dias_restantes": p.dias_restantes(hoje),
                "prioridade": p.prioridade(hoje).value,
                "vencido": p.vencido(hoje),
                "origem": p.origem, "fundamento": p.fundamento,
            }
            for p in ag.prazos
        ],
        "alertas": [
            {"descricao": p.descricao, "janela_dias": j} for p, j in ag.alertas(hoje)
        ],
        "pendencias_de_parametrizacao": [
            {"codigo": p.codigo, "descricao": p.descricao, "prioridade": p.prioridade.value,
             "detalhamento": p.detalhamento}
            for p in ag.pendencias
        ],
    }
