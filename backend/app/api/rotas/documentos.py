"""Repositório documental, versões e assinaturas (§19, §20, §28)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, entidade_do_escopo, exigir, sessao_atual
from app.core.enums import (
    CategoriaDocumento,
    StatusAssinatura,
    StatusDocumento,
    TipoAssinatura,
    TipoDocumento,
)
from app.engines.templates.motor import (
    marcar_lacunas_html,
    validar_template,
    variaveis_do_template,
)
from app.modules.documentos.models import (
    Assinatura,
    Certidao,
    Documento,
    DocumentoVersao,
    Template,
)
from app.modules.entidades.models import Entidade

router = APIRouter(tags=["Documentos"])

# §28 — a ordem em que um documento amadurece.
ORDEM_STATUS = [
    StatusDocumento.RASCUNHO, StatusDocumento.GERADO, StatusDocumento.REVISADO,
    StatusDocumento.APROVADO, StatusDocumento.ASSINADO, StatusDocumento.PROTOCOLADO,
    StatusDocumento.REGISTRADO, StatusDocumento.ARQUIVADO,
]


@router.get("/entidades/{entidade_id}/documentos")
def listar(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    categoria: CategoriaDocumento | None = None,
    status: StatusDocumento | None = None,
):
    consulta = select(Documento).where(Documento.entidade_id == entidade.id)
    if categoria:
        consulta = consulta.where(Documento.categoria == categoria)
    if status:
        consulta = consulta.where(Documento.status == status)
    documentos = db.scalars(consulta.order_by(Documento.criado_em.desc())).all()
    return [
        {
            "id": str(d.id), "tipo": str(d.tipo), "categoria": str(d.categoria),
            "titulo": d.titulo, "status": str(d.status), "versao_atual": d.versao_atual,
            "data": d.data_documento.isoformat() if d.data_documento else None,
            "evento_id": str(d.evento_id) if d.evento_id else None,
            "origem": d.origem, "template": d.template_codigo,
            "assinaturas_pendentes": len(
                [a for a in d.assinaturas if a.status is StatusAssinatura.PENDENTE]
            ),
        }
        for d in documentos
    ]


@router.get("/documentos/{documento_id}")
def obter(
    documento_id: uuid.UUID,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    html: bool = False,
):
    documento = _documento_do_escopo(db, sessao, documento_id)
    atual = next(
        (v for v in documento.versoes if v.numero == documento.versao_atual), None
    )
    conteudo = atual.conteudo if atual else None
    return {
        "id": str(documento.id),
        "tipo": str(documento.tipo),
        "titulo": documento.titulo,
        "status": str(documento.status),
        "versao_atual": documento.versao_atual,
        "conteudo": marcar_lacunas_html(conteudo) if (html and conteudo) else conteudo,
        "lacunas": atual.lacunas if atual else [],
        "fundamentos": atual.fundamentos if atual else [],
        "versoes": [
            {
                "numero": v.numero, "criado_em": v.criado_em.isoformat(),
                "motivo": v.motivo, "lacunas": len(v.lacunas or []),
                "hash": v.hash_conteudo,
            }
            for v in documento.versoes
        ],
        "assinaturas": [
            {
                "id": str(a.id), "signatario": a.nome_signatario, "papel": a.papel,
                "tipo": str(a.tipo), "status": str(a.status),
                "reconhecimento_firma": a.exige_reconhecimento_firma,
                "data": a.data_assinatura.isoformat() if a.data_assinatura else None,
            }
            for a in documento.assinaturas
        ],
    }


@router.get("/documentos/{documento_id}/versoes/{numero}")
def obter_versao(
    documento_id: uuid.UUID,
    numero: int,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    """§20 — a versão antiga continua acessível, sempre."""
    documento = _documento_do_escopo(db, sessao, documento_id)
    versao = next((v for v in documento.versoes if v.numero == numero), None)
    if versao is None:
        raise HTTPException(404, "Versão não encontrada.")
    return {
        "numero": versao.numero, "conteudo": versao.conteudo,
        "criado_em": versao.criado_em.isoformat(), "motivo": versao.motivo,
        "lacunas": versao.lacunas, "dados_snapshot": versao.dados_snapshot,
        "hash": versao.hash_conteudo,
    }


class StatusIn(BaseModel):
    status: StatusDocumento
    observacao: str | None = None


@router.post("/documentos/{documento_id}/status")
def mudar_status(
    documento_id: uuid.UUID,
    dados: StatusIn,
    sessao: Sessao = Depends(exigir("documentos:aprovar")),
    db: Session = Depends(get_db),
):
    documento = _documento_do_escopo(db, sessao, documento_id)
    if dados.status is not StatusDocumento.CANCELADO:
        if ORDEM_STATUS.index(dados.status) < ORDEM_STATUS.index(documento.status):
            raise HTTPException(
                409,
                f"Documento em {documento.status} não retrocede para {dados.status}. "
                f"Gere uma nova versão em vez de rebaixar o status.",
            )
    if dados.status is StatusDocumento.ASSINADO:
        pendentes = [a for a in documento.assinaturas if a.status is StatusAssinatura.PENDENTE]
        if pendentes:
            raise HTTPException(
                409,
                f"Há {len(pendentes)} assinatura(s) pendente(s): "
                + ", ".join(a.nome_signatario for a in pendentes),
            )
    documento.status = dados.status
    if dados.observacao:
        documento.observacoes = dados.observacao
    db.add(documento)
    db.commit()
    return {"id": str(documento.id), "status": str(documento.status)}


class AssinaturaIn(BaseModel):
    nome_signatario: str
    papel: str | None = None
    pessoa_id: uuid.UUID | None = None
    tipo: TipoAssinatura = TipoAssinatura.FISICA
    exige_reconhecimento_firma: bool = False


@router.post("/documentos/{documento_id}/assinaturas", status_code=201)
def adicionar_assinatura(
    documento_id: uuid.UUID,
    dados: AssinaturaIn,
    sessao: Sessao = Depends(exigir("documentos:gerar")),
    db: Session = Depends(get_db),
):
    documento = _documento_do_escopo(db, sessao, documento_id)
    versao_atual = next(
        (v for v in documento.versoes if v.numero == documento.versao_atual), None
    )
    assinatura = Assinatura(
        documento_id=documento.id,
        documento_versao_id=versao_atual.id if versao_atual else None,
        **dados.model_dump(),
    )
    db.add(assinatura)
    db.commit()
    db.refresh(assinatura)
    return {"id": str(assinatura.id), "status": str(assinatura.status)}


class RegistroAssinaturaIn(BaseModel):
    data_assinatura: dt.datetime | None = None
    provedor: str | None = None
    evidencia: dict = {}


@router.post("/assinaturas/{assinatura_id}/registrar")
def registrar_assinatura(
    assinatura_id: uuid.UUID,
    dados: RegistroAssinaturaIn,
    sessao: Sessao = Depends(exigir("documentos:aprovar")),
    db: Session = Depends(get_db),
):
    """Registra que a assinatura ocorreu. A evidência vem de fora — o sistema
    não a fabrica (§46)."""
    assinatura = db.get(Assinatura, assinatura_id)
    if assinatura is None:
        raise HTTPException(404, "Assinatura não encontrada.")
    _documento_do_escopo(db, sessao, assinatura.documento_id)

    assinatura.status = StatusAssinatura.ASSINADO
    assinatura.data_assinatura = dados.data_assinatura or dt.datetime.utcnow()
    assinatura.provedor = dados.provedor
    assinatura.evidencia = dados.evidencia
    db.add(assinatura)
    db.commit()

    documento = db.get(Documento, assinatura.documento_id)
    if all(a.status is StatusAssinatura.ASSINADO for a in documento.assinaturas):
        documento.status = StatusDocumento.ASSINADO
        db.add(documento)
        db.commit()
    return {"id": str(assinatura.id), "status": str(assinatura.status),
            "documento_status": str(documento.status)}


# ------------------------------------------------------------------ Templates


class TemplateIn(BaseModel):
    codigo: str
    nome: str
    tipo_documento: TipoDocumento
    corpo: str
    tipos_entidade: list[str] = []
    tipos_evento: list[str] = []
    uf: str | None = None
    fundamentos: list[str] = []


@router.get("/templates")
def listar_templates(
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    tipo_documento: TipoDocumento | None = None,
):
    consulta = select(Template).where(
        (Template.cliente_id.is_(None)) | (Template.cliente_id == sessao.cliente_id)
    )
    if tipo_documento:
        consulta = consulta.where(Template.tipo_documento == tipo_documento)
    return [
        {
            "id": str(t.id), "codigo": t.codigo, "nome": t.nome,
            "tipo_documento": str(t.tipo_documento), "versao": t.versao, "ativo": t.ativo,
            "padrao_do_sistema": t.cliente_id is None,
            "tipos_entidade": t.tipos_entidade, "tipos_evento": t.tipos_evento,
            "uf": t.uf, "variaveis": t.variaveis, "fundamentos": t.fundamentos,
        }
        for t in db.scalars(consulta.order_by(Template.nome)).all()
    ]


@router.post("/templates", status_code=201)
def criar_template(
    dados: TemplateIn,
    sessao: Sessao = Depends(exigir("documentos:template:editar")),
    db: Session = Depends(get_db),
):
    ok, erro = validar_template(dados.corpo)
    if not ok:
        raise HTTPException(422, f"Modelo com erro de sintaxe. {erro}")

    anterior = db.scalar(
        select(Template).where(
            Template.cliente_id == sessao.cliente_id, Template.codigo == dados.codigo
        ).order_by(Template.versao.desc())
    )
    template = Template(
        cliente_id=sessao.cliente_id,
        versao=(anterior.versao + 1) if anterior else 1,
        variaveis=variaveis_do_template(dados.corpo),
        **dados.model_dump(),
    )
    if anterior:
        anterior.ativo = False
        db.add(anterior)
    db.add(template)
    db.commit()
    db.refresh(template)
    return {"id": str(template.id), "codigo": template.codigo, "versao": template.versao,
            "variaveis": template.variaveis}


@router.post("/templates/validar")
def validar_corpo(corpo: dict, _: Sessao = Depends(sessao_atual)):
    texto = corpo.get("corpo", "")
    ok, erro = validar_template(texto)
    return {"valido": ok, "erro": erro, "variaveis": variaveis_do_template(texto) if ok else []}


# ------------------------------------------------------------------ Certidões


class CertidaoIn(BaseModel):
    tipo: str
    orgao_emissor: str | None = None
    numero: str | None = None
    data_emissao: dt.date | None = None
    data_validade: dt.date | None = None
    observacoes: str | None = None


@router.get("/entidades/{entidade_id}/certidoes")
def listar_certidoes(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    hoje = dt.date.today()
    certidoes = db.scalars(select(Certidao).where(Certidao.entidade_id == entidade.id)).all()
    return [
        {
            "id": str(c.id), "tipo": c.tipo, "orgao": c.orgao_emissor, "numero": c.numero,
            "emissao": c.data_emissao.isoformat() if c.data_emissao else None,
            "validade": c.data_validade.isoformat() if c.data_validade else None,
            "vencida": bool(c.data_validade and c.data_validade < hoje),
            "dias_restantes": (c.data_validade - hoje).days if c.data_validade else None,
        }
        for c in certidoes
    ]


@router.post("/entidades/{entidade_id}/certidoes", status_code=201)
def criar_certidao(
    dados: CertidaoIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("documentos:gerar")),
    db: Session = Depends(get_db),
):
    certidao = Certidao(entidade_id=entidade.id, **dados.model_dump())
    db.add(certidao)
    db.commit()
    db.refresh(certidao)
    return {"id": str(certidao.id)}


def _documento_do_escopo(db: Session, sessao: Sessao, documento_id: uuid.UUID) -> Documento:
    documento = db.get(Documento, documento_id)
    if documento is None:
        raise HTTPException(404, "Documento não encontrado.")
    entidade = db.get(Entidade, documento.entidade_id)
    if entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Documento não encontrado.")
    if sessao.entidades_permitidas is not None and entidade.id not in sessao.entidades_permitidas:
        raise HTTPException(403, "Sem acesso a esta entidade.")
    return documento
