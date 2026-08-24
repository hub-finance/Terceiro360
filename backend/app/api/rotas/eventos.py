"""MOTOR DE EVENTOS — o fluxo completo de um ato (§10, §40, §49)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, entidade_do_escopo, exigir, sessao_atual
from app.core.enums import Semaforo, StatusEvento, TipoDocumento, TipoEvento
from app.engines.checklist.motor import montar
from app.engines.decisao.motor import PERGUNTAS, responder, responder_tudo
from app.engines.validacao.motor import validar
from app.modules.documentos.servicos import gerar_documento
from app.modules.entidades.models import Entidade
from app.modules.juridico.models import Evento
from app.modules.juridico.questionarios import campos_faltantes, questionario_de
from app.modules.juridico.servicos import montar_contexto, registrar_validacao
from app.modules.juridico import atos

router = APIRouter(tags=["Eventos"])


class EventoIn(BaseModel):
    tipo: TipoEvento
    titulo: str | None = None
    data_referencia: dt.date | None = None
    dados: dict = {}


class EventoOut(BaseModel):
    id: uuid.UUID
    tipo: str
    titulo: str | None
    status: str
    semaforo: str | None
    data_referencia: dt.date | None
    dados: dict

    model_config = {"from_attributes": True}


# Documentos gerados por ato, na ordem do fluxo do §40.
DOCUMENTOS_POR_ATO: dict[str, tuple[TipoDocumento, ...]] = {
    TipoEvento.ELEICAO_DIRETORIA.value: (
        TipoDocumento.EDITAL_CONVOCACAO, TipoDocumento.LISTA_PRESENCA, TipoDocumento.ATA,
        TipoDocumento.TERMO_POSSE, TipoDocumento.RELACAO_DIRETORIA,
        TipoDocumento.REQUERIMENTO_RCPJ,
    ),
    TipoEvento.REFORMA_ESTATUTARIA.value: (
        TipoDocumento.EDITAL_CONVOCACAO, TipoDocumento.LISTA_PRESENCA, TipoDocumento.ATA,
        TipoDocumento.QUADRO_COMPARATIVO, TipoDocumento.REQUERIMENTO_RCPJ,
    ),
    TipoEvento.APROVACAO_CONTAS.value: (
        TipoDocumento.EDITAL_CONVOCACAO, TipoDocumento.LISTA_PRESENCA, TipoDocumento.ATA,
    ),
    TipoEvento.ALTERACAO_ENDERECO.value: (
        TipoDocumento.ATA, TipoDocumento.REQUERIMENTO_RCPJ,
    ),
    TipoEvento.RENUNCIA.value: (
        TipoDocumento.TERMO_RENUNCIA, TipoDocumento.REQUERIMENTO_RCPJ,
    ),
}


@router.get("/catalogo/eventos")
def catalogo_eventos(_: Sessao = Depends(sessao_atual)):
    """§10 — 'qual ato você deseja realizar?'"""
    categorias = {
        "CONSTITUIÇÃO": [TipoEvento.CONSTITUICAO, TipoEvento.APROVACAO_ESTATUTO,
                         TipoEvento.REGISTRO_INICIAL],
        "DIRETORIA": [TipoEvento.ELEICAO_DIRETORIA, TipoEvento.REELEICAO_DIRETORIA,
                      TipoEvento.POSSE_DIRETORIA, TipoEvento.RENUNCIA, TipoEvento.DESTITUICAO,
                      TipoEvento.SUBSTITUICAO, TipoEvento.VACANCIA, TipoEvento.ALTERACAO_CARGOS],
        "ESTATUTO": [TipoEvento.REFORMA_ESTATUTARIA, TipoEvento.ALTERACAO_FINALIDADE,
                     TipoEvento.ALTERACAO_ENDERECO, TipoEvento.ALTERACAO_DENOMINACAO,
                     TipoEvento.ALTERACAO_ORGAOS, TipoEvento.ALTERACAO_MANDATO,
                     TipoEvento.ALTERACAO_QUORUM],
        "ASSEMBLEIAS": [TipoEvento.ASSEMBLEIA_ORDINARIA, TipoEvento.ASSEMBLEIA_EXTRAORDINARIA],
        "PRESTAÇÃO DE CONTAS": [TipoEvento.APROVACAO_CONTAS, TipoEvento.PRESTACAO_CONTAS,
                                TipoEvento.PARECER_CONSELHO_FISCAL],
        "ENCERRAMENTO": [TipoEvento.DISSOLUCAO, TipoEvento.LIQUIDACAO,
                         TipoEvento.DESTINACAO_PATRIMONIAL, TipoEvento.ENCERRAMENTO],
    }
    return {
        categoria: [
            {"tipo": t.value, "titulo": questionario_de(t.value).titulo}
            for t in tipos
        ]
        for categoria, tipos in categorias.items()
    }


@router.get("/catalogo/eventos/{tipo}/questionario")
def questionario(tipo: TipoEvento, _: Sessao = Depends(sessao_atual)):
    return questionario_de(tipo.value).to_dict()


@router.post("/entidades/{entidade_id}/eventos", response_model=EventoOut, status_code=201)
def criar_evento(
    dados: EventoIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    sessao: Sessao = Depends(exigir("juridico:evento:criar")),
    db: Session = Depends(get_db),
):
    evento = Evento(
        entidade_id=entidade.id,
        tipo=dados.tipo,
        titulo=dados.titulo or questionario_de(dados.tipo.value).titulo,
        data_referencia=dados.data_referencia or _data_dos_dados(dados.dados),
        dados=dados.dados,
        criado_por_id=sessao.usuario.id,
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


@router.get("/entidades/{entidade_id}/eventos", response_model=list[EventoOut])
def listar_eventos(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Evento).where(Evento.entidade_id == entidade.id)
        .order_by(Evento.criado_em.desc())
    ).all()


@router.get("/eventos/{evento_id}", response_model=EventoOut)
def obter_evento(
    evento_id: uuid.UUID,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    return _evento_do_escopo(db, sessao, evento_id)


@router.put("/eventos/{evento_id}/respostas", response_model=EventoOut)
def responder_questionario(
    evento_id: uuid.UUID,
    respostas: dict,
    sessao: Sessao = Depends(exigir("juridico:evento:criar")),
    db: Session = Depends(get_db),
):
    evento = _evento_do_escopo(db, sessao, evento_id)
    evento.dados = {**(evento.dados or {}), **respostas}
    if respostas.get("data_ato"):
        evento.data_referencia = _para_data(respostas["data_ato"])
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


@router.post("/eventos/{evento_id}/validar")
def validar_evento(
    evento_id: uuid.UUID,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    """§12/§13 — roda o motor de validação e devolve o semáforo."""
    evento = _evento_do_escopo(db, sessao, evento_id)
    ctx = montar_contexto(db, evento)
    resultado = validar(ctx)
    registrar_validacao(db, evento, resultado)

    saida = resultado.to_dict()
    saida["campos_faltantes"] = campos_faltantes(str(evento.tipo), evento.dados or {})
    saida["checklist"] = montar(ctx).to_dict()
    return saida


@router.get("/eventos/{evento_id}/checklist")
def checklist_evento(
    evento_id: uuid.UUID,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    evento = _evento_do_escopo(db, sessao, evento_id)
    return montar(montar_contexto(db, evento)).to_dict()


@router.get("/eventos/{evento_id}/decisao")
def decisao(
    evento_id: uuid.UUID,
    pergunta: str | None = None,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    """§39 — RESULTADO + JUSTIFICATIVA + FUNDAMENTAÇÃO."""
    evento = _evento_do_escopo(db, sessao, evento_id)
    ctx = montar_contexto(db, evento)
    if pergunta:
        if pergunta not in PERGUNTAS:
            raise HTTPException(422, f"Pergunta desconhecida. Disponíveis: {list(PERGUNTAS)}")
        return responder(ctx, pergunta).to_dict()
    return [r.to_dict() for r in responder_tudo(ctx)]


@router.post("/eventos/{evento_id}/gerar-documentos")
def gerar_documentos(
    evento_id: uuid.UUID,
    sessao: Sessao = Depends(exigir("documentos:gerar")),
    db: Session = Depends(get_db),
    forcar: bool = False,
):
    """§13 — 🔴 impede a geração. 🟡 gera, mas registra a ressalva."""
    evento = _evento_do_escopo(db, sessao, evento_id)
    ctx = montar_contexto(db, evento)
    resultado = validar(ctx)
    registrar_validacao(db, evento, resultado)

    if resultado.semaforo is Semaforo.BLOQUEADO and not forcar:
        raise HTTPException(
            409,
            {
                "mensagem": "Existem inconsistências que impedem a geração dos documentos.",
                "semaforo": resultado.semaforo.value,
                "bloqueios": [a.to_dict() for a in resultado.bloqueios],
            },
        )

    gerados, sem_modelo = [], []
    for tipo in DOCUMENTOS_POR_ATO.get(str(evento.tipo), (TipoDocumento.ATA,)):
        resultado_geracao = gerar_documento(db, evento, ctx, tipo, sessao.usuario.id)
        if resultado_geracao is None:
            sem_modelo.append(tipo.value)
            continue
        documento, versao = resultado_geracao
        gerados.append({
            "documento_id": str(documento.id),
            "tipo": tipo.value,
            "titulo": documento.titulo,
            "versao": versao.numero,
            "lacunas": versao.lacunas,
        })

    evento.status = StatusEvento.GERADO
    db.add(evento)
    db.commit()

    return {
        "semaforo": resultado.semaforo.value,
        "gerados": gerados,
        "sem_modelo_cadastrado": sem_modelo,
        "ressalvas": [a.to_dict() for a in resultado.pendencias],
    }


class TransicaoIn(BaseModel):
    status: StatusEvento
    observacao: str | None = None


@router.post("/eventos/{evento_id}/status", response_model=EventoOut)
def mudar_status(
    evento_id: uuid.UUID,
    dados: TransicaoIn,
    sessao: Sessao = Depends(exigir("juridico:evento:editar")),
    db: Session = Depends(get_db),
):
    evento = _evento_do_escopo(db, sessao, evento_id)
    atos.transicionar(db, evento, dados.status, sessao.usuario.id, dados.observacao)
    db.refresh(evento)
    return evento


@router.post("/eventos/{evento_id}/registrar")
def registrar_ato(
    evento_id: uuid.UUID,
    sessao: Sessao = Depends(exigir("juridico:evento:editar")),
    db: Session = Depends(get_db),
):
    """§41 — registro concluído atualiza o quadro diretivo, sem apagar o anterior."""
    evento = _evento_do_escopo(db, sessao, evento_id)
    resultado = atos.concluir_registro(db, evento, sessao.usuario.id)
    return resultado


def _evento_do_escopo(db: Session, sessao: Sessao, evento_id: uuid.UUID) -> Evento:
    evento = db.get(Evento, evento_id)
    if evento is None:
        raise HTTPException(404, "Ato não encontrado.")
    entidade = db.get(Entidade, evento.entidade_id)
    if entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Ato não encontrado.")
    if sessao.entidades_permitidas is not None and entidade.id not in sessao.entidades_permitidas:
        raise HTTPException(403, "Sem acesso a esta entidade.")
    return evento


def _data_dos_dados(dados: dict) -> dt.date | None:
    valor = dados.get("data_ato")
    return _para_data(valor) if valor else None


def _para_data(valor) -> dt.date | None:
    if isinstance(valor, dt.date):
        return valor
    try:
        return dt.date.fromisoformat(str(valor))
    except ValueError:
        return None
