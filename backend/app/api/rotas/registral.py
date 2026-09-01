"""Motor de RCPJ e protocolos (§22, §23)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, entidade_do_escopo, exigir, sessao_atual
from app.core.enums import StatusProtocolo, TipoEvento
from app.modules.entidades.models import Entidade
from app.modules.juridico.models import Evento
from app.modules.registral.models import RCPJ, Protocolo, RegraRCPJ

router = APIRouter(tags=["Registral"])


class RCPJIn(BaseModel):
    uf: str
    municipio: str
    nome: str
    endereco: str | None = None
    site: str | None = None
    contato: str | None = None
    forma_protocolo: str | None = None
    formatos_aceitos: list[str] = []
    exige_reconhecimento_firma: bool | None = None
    exige_visto_advogado: bool | None = None
    observacoes: str | None = None
    fonte_informacao: str | None = None
    validade_regras_dias: int = 180


class RegraIn(BaseModel):
    tipo_evento: TipoEvento
    documentos_exigidos: list[dict] = []
    vias: int | None = None
    exige_reconhecimento_firma: bool | None = None
    exige_visto_advogado: bool | None = None
    custas_estimadas: float | None = None
    prazo_estimado_dias: int | None = None
    observacoes: str | None = None
    fonte_informacao: str | None = None


@router.get("/rcpj")
def listar_rcpj(
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    uf: str | None = None,
    municipio: str | None = None,
):
    consulta = select(RCPJ)
    if uf:
        consulta = consulta.where(RCPJ.uf == uf.upper())
    if municipio:
        consulta = consulta.where(RCPJ.municipio.ilike(f"%{municipio}%"))
    hoje = dt.date.today()
    return [
        {
            "id": str(r.id), "uf": r.uf, "municipio": r.municipio, "nome": r.nome,
            "forma_protocolo": r.forma_protocolo,
            "exige_reconhecimento_firma": r.exige_reconhecimento_firma,
            "exige_visto_advogado": r.exige_visto_advogado,
            "ultima_verificacao": (
                r.data_ultima_verificacao.isoformat() if r.data_ultima_verificacao else None
            ),
            "regras_desatualizadas": r.regras_desatualizadas_em(hoje),
            "atos_cadastrados": len(r.regras),
            "fonte": r.fonte_informacao,
        }
        for r in db.scalars(consulta.order_by(RCPJ.uf, RCPJ.municipio)).all()
    ]


@router.post("/rcpj", status_code=201)
def criar_rcpj(
    dados: RCPJIn,
    sessao: Sessao = Depends(exigir("registral:rcpj:editar")),
    db: Session = Depends(get_db),
):
    rcpj = RCPJ(
        atualizado_por_id=sessao.usuario.id,
        data_ultima_verificacao=dt.date.today(),
        **dados.model_dump(),
    )
    db.add(rcpj)
    db.commit()
    db.refresh(rcpj)
    return {"id": str(rcpj.id), "nome": rcpj.nome}


@router.get("/rcpj/{rcpj_id}/regras")
def listar_regras(
    rcpj_id: uuid.UUID,
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    rcpj = db.get(RCPJ, rcpj_id)
    if rcpj is None:
        raise HTTPException(404, "RCPJ não encontrado.")
    return [
        {
            "id": str(r.id), "tipo_evento": r.tipo_evento,
            "documentos_exigidos": r.documentos_exigidos, "vias": r.vias,
            "exige_reconhecimento_firma": r.exige_reconhecimento_firma,
            "exige_visto_advogado": r.exige_visto_advogado,
            "custas_estimadas": float(r.custas_estimadas) if r.custas_estimadas else None,
            "prazo_estimado_dias": r.prazo_estimado_dias,
            "fonte": r.fonte_informacao,
            "ultima_verificacao": (
                r.data_ultima_verificacao.isoformat() if r.data_ultima_verificacao else None
            ),
        }
        for r in rcpj.regras
    ]


@router.put("/rcpj/{rcpj_id}/regras")
def gravar_regra(
    rcpj_id: uuid.UUID,
    dados: RegraIn,
    sessao: Sessao = Depends(exigir("registral:rcpj:editar")),
    db: Session = Depends(get_db),
):
    """§22 — as exigências do cartório são alimentadas manualmente e datadas."""
    rcpj = db.get(RCPJ, rcpj_id)
    if rcpj is None:
        raise HTTPException(404, "RCPJ não encontrado.")

    regra = db.scalar(
        select(RegraRCPJ).where(
            RegraRCPJ.rcpj_id == rcpj.id, RegraRCPJ.tipo_evento == dados.tipo_evento.value
        )
    )
    if regra is None:
        regra = RegraRCPJ(rcpj_id=rcpj.id, tipo_evento=dados.tipo_evento.value)
    for campo, valor in dados.model_dump(exclude={"tipo_evento"}).items():
        setattr(regra, campo, valor)
    regra.data_ultima_verificacao = dt.date.today()
    db.add(regra)

    rcpj.data_ultima_verificacao = dt.date.today()
    rcpj.atualizado_por_id = sessao.usuario.id
    db.add(rcpj)
    db.commit()
    return {"id": str(regra.id), "tipo_evento": regra.tipo_evento,
            "verificada_em": regra.data_ultima_verificacao.isoformat()}


@router.post("/rcpj/{rcpj_id}/reconferir")
def reconferir(
    rcpj_id: uuid.UUID,
    sessao: Sessao = Depends(exigir("registral:rcpj:editar")),
    db: Session = Depends(get_db),
):
    """Registra que um responsável reconferiu as exigências junto ao cartório."""
    rcpj = db.get(RCPJ, rcpj_id)
    if rcpj is None:
        raise HTTPException(404, "RCPJ não encontrado.")
    rcpj.data_ultima_verificacao = dt.date.today()
    rcpj.atualizado_por_id = sessao.usuario.id
    db.add(rcpj)
    db.commit()
    return {"id": str(rcpj.id), "verificado_em": rcpj.data_ultima_verificacao.isoformat(),
            "por": sessao.usuario.nome}


# ---------------------------------------------------------------- Protocolos


class ProtocoloIn(BaseModel):
    evento_id: uuid.UUID
    rcpj_id: uuid.UUID | None = None
    numero: str | None = None
    data_protocolo: dt.date | None = None
    custas: float | None = None
    observacoes: str | None = None


class ExigenciaIn(BaseModel):
    descricao: str
    prazo: dt.date | None = None


@router.get("/entidades/{entidade_id}/protocolos")
def listar_protocolos(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    protocolos = db.scalars(
        select(Protocolo).where(Protocolo.entidade_id == entidade.id)
        .order_by(Protocolo.criado_em.desc())
    ).all()
    return [
        {
            "id": str(p.id), "numero": p.numero, "status": str(p.status),
            "evento_id": str(p.evento_id),
            "data_protocolo": p.data_protocolo.isoformat() if p.data_protocolo else None,
            "data_registro": p.data_registro.isoformat() if p.data_registro else None,
            "numero_registro": p.numero_registro, "livro": p.livro, "folha": p.folha,
            "exigencias": p.exigencias,
            "exigencias_abertas": len([e for e in (p.exigencias or []) if not e.get("cumprida")]),
        }
        for p in protocolos
    ]


@router.post("/entidades/{entidade_id}/protocolos", status_code=201)
def criar_protocolo(
    dados: ProtocoloIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("registral:protocolo:editar")),
    db: Session = Depends(get_db),
):
    evento = db.get(Evento, dados.evento_id)
    if evento is None or evento.entidade_id != entidade.id:
        raise HTTPException(404, "Ato não encontrado nesta entidade.")

    protocolo = Protocolo(
        entidade_id=entidade.id,
        status=StatusProtocolo.PROTOCOLADO if dados.data_protocolo else StatusProtocolo.PREPARACAO,
        rcpj_id=dados.rcpj_id or entidade.rcpj_id,
        **dados.model_dump(exclude={"rcpj_id"}),
    )
    db.add(protocolo)
    db.commit()
    db.refresh(protocolo)
    return {"id": str(protocolo.id), "status": str(protocolo.status)}


@router.post("/protocolos/{protocolo_id}/exigencias")
def lancar_exigencia(
    protocolo_id: uuid.UUID,
    dados: ExigenciaIn,
    sessao: Sessao = Depends(exigir("registral:protocolo:editar")),
    db: Session = Depends(get_db),
):
    protocolo = _protocolo_do_escopo(db, sessao, protocolo_id)
    exigencias = list(protocolo.exigencias or [])
    exigencias.append({
        "descricao": dados.descricao,
        "prazo": dados.prazo.isoformat() if dados.prazo else None,
        "cumprida": False,
        "lancada_em": dt.date.today().isoformat(),
    })
    protocolo.exigencias = exigencias
    protocolo.status = StatusProtocolo.EM_EXIGENCIA
    db.add(protocolo)
    db.commit()
    return {"id": str(protocolo.id), "status": str(protocolo.status), "exigencias": exigencias}


class CumprimentoIn(BaseModel):
    observacao: str | None = None
    data_cumprimento: dt.date | None = None


@router.post("/protocolos/{protocolo_id}/exigencias/{indice}/cumprir")
def cumprir_exigencia(
    protocolo_id: uuid.UUID,
    indice: int,
    dados: CumprimentoIn,
    sessao: Sessao = Depends(exigir("registral:protocolo:editar")),
    db: Session = Depends(get_db),
):
    """Dá baixa numa exigência do cartório.

    Sem isto o protocolo entrava em EM_EXIGENCIA e não saía mais: o registro
    é barrado enquanto houver exigência aberta e não havia como fechá-la.
    O índice identifica a exigência porque elas são uma lista JSON ordenada —
    o cartório as numera na intimação, e a ordem é a mesma.
    """
    protocolo = _protocolo_do_escopo(db, sessao, protocolo_id)
    exigencias = list(protocolo.exigencias or [])
    if not 0 <= indice < len(exigencias):
        raise HTTPException(404, "Exigência não encontrada neste protocolo.")

    exigencia = dict(exigencias[indice])
    if exigencia.get("cumprida"):
        raise HTTPException(409, "Esta exigência já estava cumprida.")
    exigencia.update({
        "cumprida": True,
        "cumprida_em": (dados.data_cumprimento or dt.date.today()).isoformat(),
        "cumprida_por": sessao.usuario.nome,
        "observacao": dados.observacao,
    })
    exigencias[indice] = exigencia
    protocolo.exigencias = exigencias

    # Cumprida a última, o protocolo volta a aguardar o cartório: quem decide
    # se está registrado é o oficial, não o sistema.
    abertas = [e for e in exigencias if not e.get("cumprida")]
    if not abertas:
        protocolo.status = StatusProtocolo.PROTOCOLADO
    db.add(protocolo)
    db.commit()
    return {
        "id": str(protocolo.id),
        "status": str(protocolo.status),
        "exigencias_abertas": len(abertas),
        "exigencias": exigencias,
    }


class RegistroIn(BaseModel):
    data_registro: dt.date
    numero_registro: str
    livro: str | None = None
    folha: str | None = None


@router.post("/protocolos/{protocolo_id}/registrar")
def concluir_registro(
    protocolo_id: uuid.UUID,
    dados: RegistroIn,
    sessao: Sessao = Depends(exigir("registral:protocolo:editar")),
    db: Session = Depends(get_db),
):
    protocolo = _protocolo_do_escopo(db, sessao, protocolo_id)
    abertas = [e for e in (protocolo.exigencias or []) if not e.get("cumprida")]
    if abertas:
        raise HTTPException(
            409,
            "Há exigências em aberto: " + "; ".join(e["descricao"] for e in abertas),
        )
    for campo, valor in dados.model_dump().items():
        setattr(protocolo, campo, valor)
    protocolo.status = StatusProtocolo.REGISTRADO
    db.add(protocolo)
    db.commit()
    return {"id": str(protocolo.id), "status": str(protocolo.status),
            "numero_registro": protocolo.numero_registro}


def _protocolo_do_escopo(db: Session, sessao: Sessao, protocolo_id: uuid.UUID) -> Protocolo:
    protocolo = db.get(Protocolo, protocolo_id)
    if protocolo is None:
        raise HTTPException(404, "Protocolo não encontrado.")
    entidade = db.get(Entidade, protocolo.entidade_id)
    if entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Protocolo não encontrado.")
    return protocolo
