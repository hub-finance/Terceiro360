"""TERCEIRO360 IGREJAS — núcleo eclesiástico (§17)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, entidade_do_escopo, exigir, sessao_atual
from app.core.enums import FuncaoEclesiastica, TipoUnidadeEclesiastica
from app.modules.entidades.models import Entidade
from app.modules.igrejas.models import (
    Ministro,
    ModeloGovernancaEclesiastica,
    UnidadeEclesiastica,
)

router = APIRouter(tags=["Igrejas"])

# Modelos organizacionais reconhecidos. São *opções de cadastro*, não presunções:
# a estrutura de cada igreja vem do seu estatuto e regimento (§17).
MODELOS_REFERENCIA = [
    {
        "codigo": "EPISCOPAL",
        "nome": "Episcopal",
        "descricao": "Autoridade concentrada em bispo ou pastor presidente, com hierarquia "
                     "definida acima da igreja local.",
    },
    {
        "codigo": "PRESBITERAL",
        "nome": "Presbiteral",
        "descricao": "Governo por conselho de presbíteros; decisões colegiadas.",
    },
    {
        "codigo": "CONGREGACIONAL",
        "nome": "Congregacional",
        "descricao": "Assembleia dos membros é a instância máxima da igreja local.",
    },
    {
        "codigo": "CONVENCIONAL",
        "nome": "Convencional",
        "descricao": "Igreja local autônoma, filiada a uma convenção que estabelece regras "
                     "de comunhão e de credenciamento ministerial.",
    },
    {
        "codigo": "MISTO",
        "nome": "Misto",
        "descricao": "Combina elementos dos modelos acima. Exige descrição própria.",
    },
]


@router.get("/catalogo/modelos-governanca-eclesiastica")
def catalogo_modelos(_: Sessao = Depends(sessao_atual)):
    return {
        "modelos": MODELOS_REFERENCIA,
        "aviso": "O sistema não presume que todas as igrejas tenham a mesma estrutura. "
                 "O modelo escolhido é apenas um ponto de partida: quem define quem convoca, "
                 "quem elege e quem representa é o ESTATUTO + REGIMENTO INTERNO + modelo "
                 "organizacional da denominação.",
    }


class UnidadeIn(BaseModel):
    tipo: TipoUnidadeEclesiastica
    nome: str
    unidade_pai_id: uuid.UUID | None = None
    possui_cnpj_proprio: bool = False
    cnpj: str | None = None
    endereco: str | None = None
    municipio: str | None = None
    uf: str | None = None
    responsavel_pessoa_id: uuid.UUID | None = None
    data_fundacao: dt.date | None = None


@router.get("/entidades/{entidade_id}/igreja/unidades")
def listar_unidades(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    unidades = db.scalars(
        select(UnidadeEclesiastica).where(UnidadeEclesiastica.entidade_id == entidade.id)
    ).all()

    def montar(pai_id):
        return [
            {
                "id": str(u.id), "tipo": str(u.tipo), "nome": u.nome,
                "possui_cnpj_proprio": u.possui_cnpj_proprio, "cnpj": u.cnpj,
                "municipio": u.municipio, "uf": u.uf, "ativa": u.ativa,
                "filhas": montar(u.id),
            }
            for u in unidades
            if u.unidade_pai_id == pai_id
        ]

    return {"entidade": entidade.razao_social, "unidades": montar(None)}


@router.post("/entidades/{entidade_id}/igreja/unidades", status_code=201)
def criar_unidade(
    dados: UnidadeIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("juridico:orgao:criar")),
    db: Session = Depends(get_db),
):
    unidade = UnidadeEclesiastica(entidade_id=entidade.id, **dados.model_dump())
    db.add(unidade)
    db.commit()
    db.refresh(unidade)
    return {"id": str(unidade.id), "nome": unidade.nome}


class MinistroIn(BaseModel):
    pessoa_id: uuid.UUID
    funcao: FuncaoEclesiastica
    unidade_id: uuid.UUID | None = None
    data_ordenacao: dt.date | None = None
    credencial: str | None = None
    orgao_credenciador: str | None = None
    observacoes: str | None = None


@router.get("/entidades/{entidade_id}/igreja/ministros")
def listar_ministros(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    ministros = db.scalars(
        select(Ministro).where(Ministro.entidade_id == entidade.id)
    ).all()
    from app.modules.juridico.models import Pessoa

    return [
        {
            "id": str(m.id), "funcao": str(m.funcao), "situacao": m.situacao,
            "pessoa": db.get(Pessoa, m.pessoa_id).nome,
            "data_ordenacao": m.data_ordenacao.isoformat() if m.data_ordenacao else None,
            "credencial": m.credencial, "orgao_credenciador": m.orgao_credenciador,
        }
        for m in ministros
    ]


@router.post("/entidades/{entidade_id}/igreja/ministros", status_code=201)
def criar_ministro(
    dados: MinistroIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("juridico:pessoa:criar")),
    db: Session = Depends(get_db),
):
    """Função eclesiástica não se confunde com cargo estatutário: um pastor pode
    não ser presidente, e um presidente pode não ser ministro ordenado."""
    ministro = Ministro(entidade_id=entidade.id, **dados.model_dump())
    db.add(ministro)
    db.commit()
    db.refresh(ministro)
    return {"id": str(ministro.id)}


class ModeloIn(BaseModel):
    nome: str
    descricao: str | None = None
    denominacao: str | None = None
    convencao: str | None = None
    regras: dict = {}
    fonte: str | None = None
    confirmado: bool = False


@router.get("/entidades/{entidade_id}/igreja/governanca")
def obter_modelo(
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    modelo = db.scalar(
        select(ModeloGovernancaEclesiastica).where(
            ModeloGovernancaEclesiastica.entidade_id == entidade.id
        )
    )
    if modelo is None:
        return {
            "cadastrado": False,
            "aviso": "Modelo de governança eclesiástica não cadastrado. Sem ele o sistema "
                     "não tem como saber quem convoca, quem elege e quem representa esta "
                     "igreja — e essas regras variam entre denominações.",
        }
    return {
        "cadastrado": True, "nome": modelo.nome, "descricao": modelo.descricao,
        "denominacao": modelo.denominacao, "convencao": modelo.convencao,
        "regras": modelo.regras, "fonte": modelo.fonte, "confirmado": modelo.confirmado,
    }


@router.put("/entidades/{entidade_id}/igreja/governanca")
def gravar_modelo(
    dados: ModeloIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("juridico:estatuto:editar")),
    db: Session = Depends(get_db),
):
    if not entidade.eclesiastica:
        raise HTTPException(
            422,
            "Esta entidade não está classificada como igreja ou organização religiosa. "
            "Ajuste o tipo de entidade no cadastro antes de definir governança eclesiástica.",
        )
    modelo = db.scalar(
        select(ModeloGovernancaEclesiastica).where(
            ModeloGovernancaEclesiastica.entidade_id == entidade.id
        )
    )
    if modelo is None:
        modelo = ModeloGovernancaEclesiastica(entidade_id=entidade.id)
    for campo, valor in dados.model_dump().items():
        setattr(modelo, campo, valor)
    db.add(modelo)
    db.commit()
    return {"nome": modelo.nome, "confirmado": modelo.confirmado}
