"""Estatuto como dado parametrizável (§7, §49, §52)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, entidade_do_escopo, exigir, sessao_atual
from app.core.tempo import agora
from app.core.enums import OrigemDado
from app.engines.conformidade.catalogo import CATALOGO, por_grupo
from app.modules.entidades.models import Entidade
from app.modules.juridico.models import Estatuto, EstatutoParametro, EstatutoVersao

router = APIRouter(tags=["Estatuto"])


class VersaoIn(BaseModel):
    data_estatuto: dt.date | None = None
    data_registro: dt.date | None = None
    numero_registro: str | None = None
    livro: str | None = None
    folha: str | None = None
    municipio: str | None = None
    uf: str | None = None
    texto: str | None = None
    motivo_alteracao: str | None = None
    vigente: bool = True


class ParametroIn(BaseModel):
    chave: str
    valor: str | None = None
    tipo_valor: str = "texto"
    unidade: str | None = None
    dispositivo: str | None = None
    trecho: str | None = None
    confirmado: bool = False
    observacao: str | None = None


@router.get("/catalogo/parametros-estatutarios")
def catalogo(_: Sessao = Depends(sessao_atual)):
    """O vocabulário do estatuto, em linguagem de usuário (§52)."""
    return {
        grupo: [
            {
                "chave": d.chave, "rotulo": d.rotulo, "pergunta": d.pergunta_simples,
                "tipo": d.tipo, "unidade": d.unidade, "exemplos": list(d.exemplos),
                "nota": d.nota, "obrigatorio_para": list(d.obrigatorio_para),
                "fonte_legal": d.fonte_legal, "dispositivo_legal": d.dispositivo_legal,
            }
            for d in definicoes
        ]
        for grupo, definicoes in por_grupo().items()
    }


@router.get("/entidades/{entidade_id}/estatuto")
def obter(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    estatuto = db.scalar(select(Estatuto).where(Estatuto.entidade_id == entidade.id))
    if estatuto is None:
        return {"versoes": [], "vigente": None}
    versoes = db.scalars(
        select(EstatutoVersao).where(EstatutoVersao.estatuto_id == estatuto.id)
        .order_by(EstatutoVersao.numero_versao.desc())
    ).all()
    return {
        "estatuto_id": str(estatuto.id),
        "versoes": [
            {
                "id": str(v.id), "numero": v.numero_versao, "vigente": v.vigente,
                "data_estatuto": v.data_estatuto.isoformat() if v.data_estatuto else None,
                "data_registro": v.data_registro.isoformat() if v.data_registro else None,
                "numero_registro": v.numero_registro, "livro": v.livro, "folha": v.folha,
                "motivo_alteracao": v.motivo_alteracao,
                "parametros": len(v.parametros),
                "parametros_confirmados": len([p for p in v.parametros if p.confirmado]),
            }
            for v in versoes
        ],
    }


@router.post("/entidades/{entidade_id}/estatuto/versoes", status_code=201)
def nova_versao(
    dados: VersaoIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("juridico:estatuto:editar")),
    db: Session = Depends(get_db),
):
    """§20 — nova redação vira nova versão; a anterior nunca é sobrescrita."""
    estatuto = db.scalar(select(Estatuto).where(Estatuto.entidade_id == entidade.id))
    if estatuto is None:
        estatuto = Estatuto(entidade_id=entidade.id)
        db.add(estatuto)
        db.flush()

    ultimo = db.scalar(
        select(EstatutoVersao).where(EstatutoVersao.estatuto_id == estatuto.id)
        .order_by(EstatutoVersao.numero_versao.desc())
    )
    if dados.vigente and ultimo is not None:
        for v in db.scalars(
            select(EstatutoVersao).where(EstatutoVersao.estatuto_id == estatuto.id)
        ).all():
            v.vigente = False
            db.add(v)

    versao = EstatutoVersao(
        estatuto_id=estatuto.id,
        numero_versao=(ultimo.numero_versao + 1) if ultimo else 1,
        **dados.model_dump(),
    )
    db.add(versao)
    db.flush()
    if versao.vigente:
        estatuto.versao_vigente_id = versao.id
        db.add(estatuto)
    db.commit()
    db.refresh(versao)
    return {"id": str(versao.id), "numero": versao.numero_versao, "vigente": versao.vigente}


@router.get("/estatuto/versoes/{versao_id}/parametros")
def listar_parametros(
    versao_id: uuid.UUID,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    versao = _versao_do_escopo(db, sessao, versao_id)
    registrados = {p.chave: p for p in versao.parametros}
    saida = []
    for chave, definicao in CATALOGO.items():
        p = registrados.get(chave)
        saida.append({
            "chave": chave,
            "rotulo": definicao.rotulo,
            "pergunta": definicao.pergunta_simples,
            "grupo": definicao.grupo,
            "tipo": definicao.tipo,
            "unidade": definicao.unidade,
            "exemplos": list(definicao.exemplos),
            "nota": definicao.nota,
            "valor": p.valor if p else None,
            "dispositivo": p.dispositivo if p else None,
            "trecho": p.trecho if p else None,
            "confirmado": p.confirmado if p else False,
            "origem": str(p.origem) if p else None,
            "confianca": float(p.confianca) if p and p.confianca is not None else None,
            "status": (
                "CONFIRMADO" if p and p.confirmado
                else "VALIDACAO_NECESSARIA" if p
                else "DADO_NAO_INFORMADO"
            ),
        })
    return saida


@router.put("/estatuto/versoes/{versao_id}/parametros")
def gravar_parametros(
    versao_id: uuid.UUID,
    parametros: list[ParametroIn],
    sessao: Sessao = Depends(exigir("juridico:estatuto:editar")),
    db: Session = Depends(get_db),
):
    versao = _versao_do_escopo(db, sessao, versao_id)
    existentes = {p.chave: p for p in versao.parametros}
    momento = agora()

    for entrada in parametros:
        if entrada.chave not in CATALOGO:
            raise HTTPException(422, f"Parâmetro desconhecido: {entrada.chave}")
        p = existentes.get(entrada.chave)
        if p is None:
            p = EstatutoParametro(versao_id=versao.id, chave=entrada.chave)
        p.valor = entrada.valor
        p.tipo_valor = entrada.tipo_valor
        p.unidade = entrada.unidade
        p.dispositivo = entrada.dispositivo
        p.trecho = entrada.trecho
        p.observacao = entrada.observacao
        p.origem = OrigemDado.ESTATUTO
        p.confirmado = entrada.confirmado
        if entrada.confirmado:
            p.confirmado_por_id = sessao.usuario.id
            p.confirmado_em = momento
        db.add(p)

    db.commit()
    return {"gravados": len(parametros)}


@router.post("/estatuto/versoes/{versao_id}/parametros/{chave}/confirmar")
def confirmar(
    versao_id: uuid.UUID,
    chave: str,
    sessao: Sessao = Depends(exigir("juridico:estatuto:editar")),
    db: Session = Depends(get_db),
):
    """§49 — o passo 'USUÁRIO CONFIRMA REGRAS'."""
    versao = _versao_do_escopo(db, sessao, versao_id)
    p = next((x for x in versao.parametros if x.chave == chave), None)
    if p is None:
        raise HTTPException(404, "Parâmetro não cadastrado nesta versão do estatuto.")
    if p.valor in (None, ""):
        raise HTTPException(422, "Não é possível confirmar um parâmetro sem valor.")
    p.confirmado = True
    p.confirmado_por_id = sessao.usuario.id
    p.confirmado_em = agora()
    db.add(p)
    db.commit()
    return {"chave": chave, "confirmado": True, "por": sessao.usuario.nome}


def _versao_do_escopo(db: Session, sessao: Sessao, versao_id: uuid.UUID) -> EstatutoVersao:
    versao = db.get(EstatutoVersao, versao_id)
    if versao is None:
        raise HTTPException(404, "Versão do estatuto não encontrada.")
    estatuto = db.get(Estatuto, versao.estatuto_id)
    entidade = db.get(Entidade, estatuto.entidade_id)
    if entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Versão do estatuto não encontrada.")
    if sessao.entidades_permitidas is not None and entidade.id not in sessao.entidades_permitidas:
        raise HTTPException(403, "Sem acesso a esta entidade.")
    return versao
