"""Pessoas, órgãos, cargos, quadro diretivo e associados (§8, §9, §18)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, entidade_do_escopo, exigir, sessao_atual
from app.core.enums import SituacaoAssociado, SituacaoMembro, TipoOrgao
from app.modules.entidades.models import Entidade
from app.modules.juridico.models import (
    Associado,
    Cargo,
    Mandato,
    MandatoMembro,
    Orgao,
    Pessoa,
)

router = APIRouter(tags=["Cadastros"])


# ------------------------------------------------------------------ Pessoas


class PessoaIn(BaseModel):
    nome: str
    cpf: str | None = None
    rg: str | None = None
    orgao_expedidor: str | None = None
    nacionalidade: str | None = None
    estado_civil: str | None = None
    profissao: str | None = None
    data_nascimento: dt.date | None = None
    logradouro: str | None = None
    numero: str | None = None
    bairro: str | None = None
    municipio: str | None = None
    uf: str | None = None
    cep: str | None = None
    email: str | None = None
    telefone: str | None = None


class PessoaOut(PessoaIn):
    id: uuid.UUID
    qualificacao: str | None = None

    model_config = {"from_attributes": True}


@router.get("/pessoas", response_model=list[PessoaOut])
def listar_pessoas(
    sessao: Sessao = Depends(exigir("entidades:ler")),
    db: Session = Depends(get_db),
    busca: str | None = None,
):
    consulta = select(Pessoa).where(Pessoa.cliente_id == sessao.cliente_id)
    if busca:
        consulta = consulta.where(Pessoa.nome.ilike(f"%{busca}%"))
    return db.scalars(consulta.order_by(Pessoa.nome).limit(200)).all()


@router.post("/pessoas", response_model=PessoaOut, status_code=201)
def criar_pessoa(
    dados: PessoaIn,
    sessao: Sessao = Depends(exigir("juridico:pessoa:criar")),
    db: Session = Depends(get_db),
):
    pessoa = Pessoa(cliente_id=sessao.cliente_id, **dados.model_dump())
    db.add(pessoa)
    db.commit()
    db.refresh(pessoa)
    return pessoa


# ------------------------------------------------------------------- Órgãos


class OrgaoIn(BaseModel):
    nome: str
    codigo: str | None = None
    tipo: TipoOrgao = TipoOrgao.EXECUTIVO
    orgao_pai_id: uuid.UUID | None = None
    competencias: list[str] = []
    dispositivo_estatutario: str | None = None


class CargoIn(BaseModel):
    nome: str
    codigo: str | None = None
    ordem: int = 0
    obrigatorio: bool = True
    vagas: int = 1
    poderes_representacao: str | None = None
    forma_assinatura: str | None = None
    dispositivo_estatutario: str | None = None


@router.get("/entidades/{entidade_id}/orgaos")
def listar_orgaos(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    orgaos = db.scalars(select(Orgao).where(Orgao.entidade_id == entidade.id)).all()
    return [
        {
            "id": str(o.id), "nome": o.nome, "codigo": o.codigo, "tipo": str(o.tipo),
            "orgao_pai_id": str(o.orgao_pai_id) if o.orgao_pai_id else None,
            "competencias": o.competencias, "dispositivo": o.dispositivo_estatutario,
            "cargos": [
                {"id": str(c.id), "nome": c.nome, "codigo": c.codigo, "ordem": c.ordem,
                 "obrigatorio": c.obrigatorio, "vagas": c.vagas}
                for c in sorted(o.cargos, key=lambda c: c.ordem)
            ],
        }
        for o in orgaos
    ]


@router.post("/entidades/{entidade_id}/orgaos", status_code=201)
def criar_orgao(
    dados: OrgaoIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("juridico:orgao:criar")),
    db: Session = Depends(get_db),
):
    orgao = Orgao(entidade_id=entidade.id, **dados.model_dump())
    db.add(orgao)
    db.commit()
    db.refresh(orgao)
    return {"id": str(orgao.id), "nome": orgao.nome}


@router.post("/orgaos/{orgao_id}/cargos", status_code=201)
def criar_cargo(
    orgao_id: uuid.UUID,
    dados: CargoIn,
    sessao: Sessao = Depends(exigir("juridico:orgao:criar")),
    db: Session = Depends(get_db),
):
    orgao = db.get(Orgao, orgao_id)
    if orgao is None:
        raise HTTPException(404, "Órgão não encontrado.")
    entidade = db.get(Entidade, orgao.entidade_id)
    if entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Órgão não encontrado.")
    cargo = Cargo(orgao_id=orgao.id, **dados.model_dump())
    db.add(cargo)
    db.commit()
    db.refresh(cargo)
    return {"id": str(cargo.id), "nome": cargo.nome, "codigo": cargo.codigo}


@router.get("/entidades/{entidade_id}/governanca/mapa")
def mapa_governanca(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    """§18 — mapa organizacional hierárquico."""
    orgaos = db.scalars(select(Orgao).where(Orgao.entidade_id == entidade.id)).all()
    hoje = dt.date.today()
    mandatos = db.scalars(select(Mandato).where(Mandato.entidade_id == entidade.id)).all()
    vigentes = {m.orgao_id: m for m in mandatos if m.vigente_em(hoje)}

    def montar(pai_id):
        return [
            {
                "id": str(o.id), "nome": o.nome, "tipo": str(o.tipo), "codigo": o.codigo,
                "responsaveis": [
                    {"nome": mm.pessoa.nome, "cargo": mm.cargo.nome}
                    for mm in (vigentes[o.id].membros if o.id in vigentes else [])
                    if mm.situacao is SituacaoMembro.ATIVO
                ],
                "mandato": vigentes[o.id].designacao if o.id in vigentes else None,
                "filhos": montar(o.id),
            }
            for o in orgaos
            if o.orgao_pai_id == pai_id
        ]

    return {"entidade": entidade.razao_social, "orgaos": montar(None)}


# ------------------------------------------------------------- Quadro diretivo


class MandatoIn(BaseModel):
    orgao_id: uuid.UUID
    designacao: str
    data_inicio: dt.date
    data_fim: dt.date


class MembroIn(BaseModel):
    pessoa_id: uuid.UUID
    cargo_id: uuid.UUID
    data_inicio: dt.date | None = None
    data_fim: dt.date | None = None


@router.get("/entidades/{entidade_id}/mandatos")
def listar_mandatos(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    hoje = dt.date.today()
    mandatos = db.scalars(
        select(Mandato).where(Mandato.entidade_id == entidade.id)
        .order_by(Mandato.data_inicio.desc())
    ).all()
    return [
        {
            "id": str(m.id), "designacao": m.designacao, "orgao": m.orgao.nome,
            "data_inicio": m.data_inicio.isoformat(), "data_fim": m.data_fim.isoformat(),
            "vigente": m.vigente_em(hoje), "encerrado": m.encerrado,
            "membros": [
                {"pessoa": mm.pessoa.nome, "cpf": mm.pessoa.cpf, "cargo": mm.cargo.nome,
                 "situacao": str(mm.situacao)}
                for mm in m.membros
            ],
        }
        for m in mandatos
    ]


@router.post("/entidades/{entidade_id}/mandatos", status_code=201)
def criar_mandato(
    dados: MandatoIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("juridico:mandato:criar")),
    db: Session = Depends(get_db),
):
    mandato = Mandato(entidade_id=entidade.id, **dados.model_dump())
    db.add(mandato)
    db.commit()
    db.refresh(mandato)
    return {"id": str(mandato.id), "designacao": mandato.designacao}


@router.post("/mandatos/{mandato_id}/membros", status_code=201)
def adicionar_membro(
    mandato_id: uuid.UUID,
    dados: MembroIn,
    sessao: Sessao = Depends(exigir("juridico:mandato:criar")),
    db: Session = Depends(get_db),
):
    mandato = db.get(Mandato, mandato_id)
    if mandato is None:
        raise HTTPException(404, "Mandato não encontrado.")
    entidade = db.get(Entidade, mandato.entidade_id)
    if entidade.cliente_id != sessao.cliente_id:
        raise HTTPException(404, "Mandato não encontrado.")

    membro = MandatoMembro(
        mandato_id=mandato.id,
        pessoa_id=dados.pessoa_id,
        cargo_id=dados.cargo_id,
        data_inicio=dados.data_inicio or mandato.data_inicio,
        data_fim=dados.data_fim or mandato.data_fim,
    )
    db.add(membro)
    db.commit()
    return {"id": str(membro.id)}


# --------------------------------------------------------------- Associados


class AssociadoIn(BaseModel):
    pessoa_id: uuid.UUID
    categoria: str | None = None
    data_admissao: dt.date | None = None
    situacao: SituacaoAssociado = SituacaoAssociado.ATIVO
    direito_voto: bool = True
    elegivel: bool = True
    data_suspensao: dt.date | None = None
    data_desligamento: dt.date | None = None


@router.get("/entidades/{entidade_id}/associados")
def listar_associados(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    hoje = dt.date.today()
    associados = db.scalars(select(Associado).where(Associado.entidade_id == entidade.id)).all()
    return {
        "total": len(associados),
        "aptos_a_votar": len([a for a in associados if a.apto_a_votar_em(hoje)]),
        "associados": [
            {
                "id": str(a.id), "pessoa": a.pessoa.nome, "cpf": a.pessoa.cpf,
                "categoria": a.categoria, "situacao": str(a.situacao),
                "direito_voto": a.direito_voto, "elegivel": a.elegivel,
                "apto_hoje": a.apto_a_votar_em(hoje),
                "data_admissao": a.data_admissao.isoformat() if a.data_admissao else None,
            }
            for a in associados
        ],
    }


@router.post("/entidades/{entidade_id}/associados", status_code=201)
def criar_associado(
    dados: AssociadoIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("juridico:associado:criar")),
    db: Session = Depends(get_db),
):
    associado = Associado(entidade_id=entidade.id, **dados.model_dump())
    db.add(associado)
    db.commit()
    db.refresh(associado)
    return {"id": str(associado.id)}
