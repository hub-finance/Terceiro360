"""CENTRAL DE FONTES JURÍDICAS e MOTOR DE ATUALIZAÇÃO NORMATIVA (§4, §38, §46)."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, exigir, sessao_atual
from app.core.tempo import agora
from app.core.enums import (
    Jurisdicao,
    OrigemDeteccao,
    SituacaoAtualizacao,
    SituacaoVersaoNorma,
    TipoFonte,
)
from app.engines.normativo.coletor import Coleta, impressao_digital
from app.modules.normativo import servicos
from app.modules.normativo.models import (
    AtualizacaoNormativa,
    Dispositivo,
    FonteJuridica,
    FonteVersao,
    ImpactoNormativo,
    MonitoramentoNormativo,
    VinculoNormativo,
)

router = APIRouter(prefix="/normativo", tags=["Central de Fontes"])


# ------------------------------------------------------------------- Fontes


class FonteIn(BaseModel):
    chave: str
    identificacao: str
    apelido: str | None = None
    tipo: TipoFonte = TipoFonte.LEI
    jurisdicao: Jurisdicao = Jurisdicao.FEDERAL
    uf: str | None = None
    municipio: str | None = None
    orgao_emissor: str | None = None
    url_oficial: str | None = None
    ementa: str | None = None


@router.get("/fontes")
def listar_fontes(
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    apenas_pendentes_curadoria: bool = False,
):
    hoje = dt.date.today()
    fontes = db.scalars(select(FonteJuridica).order_by(FonteJuridica.identificacao)).all()
    saida = []
    for f in fontes:
        vigente = f.versao_vigente_em(hoje)
        if apenas_pendentes_curadoria and (vigente is None or vigente.curada):
            continue
        saida.append({
            "id": str(f.id), "chave": f.chave, "identificacao": f.identificacao,
            "apelido": f.apelido, "tipo": str(f.tipo), "jurisdicao": str(f.jurisdicao),
            "url_oficial": f.url_oficial, "ementa": f.ementa,
            "versao_vigente": vigente.numero_versao if vigente else None,
            "vigente_desde": (
                vigente.vigente_desde.isoformat() if vigente and vigente.vigente_desde else None
            ),
            # §46 — a interface precisa dizer se a redação já foi conferida.
            "curada": vigente.curada if vigente else False,
            "curador": (
                vigente.registro_profissional_curador if vigente and vigente.curada else None
            ),
            "total_versoes": len(f.versoes),
        })
    return saida


@router.post("/fontes", status_code=201)
def criar_fonte(
    dados: FonteIn,
    _: Sessao = Depends(exigir("normativo:fonte:editar")),
    db: Session = Depends(get_db),
):
    if db.scalar(select(FonteJuridica).where(FonteJuridica.chave == dados.chave)):
        raise HTTPException(409, f"Já existe fonte com a chave “{dados.chave}”.")
    fonte = FonteJuridica(**dados.model_dump())
    db.add(fonte)
    db.commit()
    db.refresh(fonte)
    return {"id": str(fonte.id), "chave": fonte.chave}


@router.get("/fontes/{chave}")
def obter_fonte(
    chave: str,
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    em: dt.date | None = None,
):
    """A redação aplicável numa data — o ato de 2024 é julgado pela lei de 2024."""
    fonte = db.scalar(select(FonteJuridica).where(FonteJuridica.chave == chave))
    if fonte is None:
        raise HTTPException(404, "Fonte não encontrada.")
    versao = fonte.versao_vigente_em(em or dt.date.today())
    return {
        "chave": fonte.chave, "identificacao": fonte.identificacao, "apelido": fonte.apelido,
        "url_oficial": fonte.url_oficial, "ementa": fonte.ementa,
        "consultado_em": (em or dt.date.today()).isoformat(),
        "versao_aplicavel": (
            {
                "numero": versao.numero_versao,
                "situacao": str(versao.situacao),
                "vigente_desde": versao.vigente_desde.isoformat() if versao.vigente_desde else None,
                "vigente_ate": versao.vigente_ate.isoformat() if versao.vigente_ate else None,
                "curada": versao.curada,
                "resumo_alteracao": versao.resumo_alteracao,
                "dispositivos": [
                    {"identificacao": d.identificacao, "texto": d.texto, "tags": d.tags,
                     "revogado": d.revogado}
                    for d in versao.dispositivos
                ],
            }
            if versao else None
        ),
        "historico": [
            {
                "numero": v.numero_versao, "situacao": str(v.situacao),
                "vigente_desde": v.vigente_desde.isoformat() if v.vigente_desde else None,
                "vigente_ate": v.vigente_ate.isoformat() if v.vigente_ate else None,
                "resumo": v.resumo_alteracao, "curada": v.curada,
            }
            for v in sorted(fonte.versoes, key=lambda v: v.numero_versao, reverse=True)
        ],
    }


class VersaoIn(BaseModel):
    vigente_desde: dt.date
    texto_referencia: str
    resumo_alteracao: str | None = None
    dispositivos: list[dict] = []
    url_captura: str | None = None


@router.post("/fontes/{chave}/versoes", status_code=201)
def publicar_versao_inicial(
    chave: str,
    dados: VersaoIn,
    sessao: Sessao = Depends(exigir("normativo:fonte:curar")),
    db: Session = Depends(get_db),
):
    """Publica a redação de referência de uma norma. Exige curador habilitado."""
    if not sessao.usuario.registro_profissional:
        raise HTTPException(
            403,
            "A curadoria de normas exige responsável com registro profissional cadastrado "
            "(OAB/CRC). É esse registro que sustenta a fundamentação usada nos atos.",
        )
    fonte = db.scalar(select(FonteJuridica).where(FonteJuridica.chave == chave))
    if fonte is None:
        raise HTTPException(404, "Fonte não encontrada.")

    anterior = db.scalar(
        select(FonteVersao).where(
            FonteVersao.fonte_id == fonte.id, FonteVersao.situacao == SituacaoVersaoNorma.VIGENTE
        )
    )
    if anterior:
        anterior.situacao = SituacaoVersaoNorma.SUPERADA
        anterior.vigente_ate = dados.vigente_desde - dt.timedelta(days=1)
        db.add(anterior)

    versao = FonteVersao(
        fonte_id=fonte.id,
        numero_versao=(anterior.numero_versao + 1) if anterior else 1,
        situacao=SituacaoVersaoNorma.VIGENTE,
        vigente_desde=dados.vigente_desde,
        publicado_em=dt.date.today(),
        resumo_alteracao=dados.resumo_alteracao,
        texto_referencia=dados.texto_referencia,
        url_captura=dados.url_captura or fonte.url_oficial,
        hash_conteudo=impressao_digital(dados.texto_referencia),
        origem_captura=OrigemDeteccao.MANUAL,
        curado_por_id=sessao.usuario.id,
        curado_em=agora(),
        registro_profissional_curador=sessao.usuario.registro_profissional,
    )
    db.add(versao)
    db.flush()
    for d in dados.dispositivos:
        db.add(Dispositivo(
            versao_id=versao.id,
            identificacao=d.get("identificacao", ""),
            texto=d.get("texto"),
            tags=d.get("tags", []),
        ))
    db.commit()
    return {"versao": versao.numero_versao, "curada_por": sessao.usuario.nome}


# ----------------------------------------------------------- Monitoramentos


class MonitoramentoIn(BaseModel):
    nome: str
    fonte_chave: str | None = None
    rcpj_id: uuid.UUID | None = None
    url: str | None = None
    modo: str = "MANUAL"          # HTTP | MANUAL
    periodicidade_dias: int = 30
    responsavel_id: uuid.UUID | None = None


@router.get("/monitoramentos")
def listar_monitoramentos(
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    momento = agora()
    from app.engines.normativo.motor import MotorAtualizacaoNormativa

    return [
        {
            "id": str(m.id), "nome": m.nome, "modo": m.modo, "url": m.url,
            "periodicidade_dias": m.periodicidade_dias,
            "ultima_verificacao": (
                m.ultima_verificacao.isoformat() if m.ultima_verificacao else None
            ),
            "proxima_verificacao": MotorAtualizacaoNormativa.proxima_verificacao(
                m.ultima_verificacao, m.periodicidade_dias
            ).isoformat(),
            "situacao": MotorAtualizacaoNormativa.situacao_da_vigilancia(
                m.ultima_verificacao, m.periodicidade_dias, momento
            ),
            "ultimo_erro": m.ultimo_erro, "ativo": m.ativo,
        }
        for m in db.scalars(select(MonitoramentoNormativo)).all()
    ]


@router.get("/monitoramentos/vencidos")
def vencidos(_: Sessao = Depends(sessao_atual), db: Session = Depends(get_db)):
    """O que precisa ser reconferido — a fila de trabalho da vigilância."""
    return servicos.vigilancias_vencidas(db)


@router.post("/monitoramentos", status_code=201)
def criar_monitoramento(
    dados: MonitoramentoIn,
    sessao: Sessao = Depends(exigir("normativo:fonte:editar")),
    db: Session = Depends(get_db),
):
    fonte_id = None
    if dados.fonte_chave:
        fonte = db.scalar(select(FonteJuridica).where(FonteJuridica.chave == dados.fonte_chave))
        if fonte is None:
            raise HTTPException(404, f"Fonte “{dados.fonte_chave}” não cadastrada.")
        fonte_id = fonte.id

    monitoramento = MonitoramentoNormativo(
        fonte_id=fonte_id,
        responsavel_id=dados.responsavel_id or sessao.usuario.id,
        **dados.model_dump(exclude={"fonte_chave", "responsavel_id"}),
    )
    db.add(monitoramento)
    db.commit()
    db.refresh(monitoramento)
    return {"id": str(monitoramento.id), "nome": monitoramento.nome}


class VerificacaoIn(BaseModel):
    """Permite registrar uma conferência manual: o responsável colou o texto
    que encontrou na fonte oficial."""

    conteudo: str | None = None


@router.post("/monitoramentos/{monitoramento_id}/verificar")
def verificar(
    monitoramento_id: uuid.UUID,
    dados: VerificacaoIn | None = None,
    _: Sessao = Depends(exigir("normativo:fonte:editar")),
    db: Session = Depends(get_db),
):
    """Roda uma vigília. Se veio conteúdo no corpo, usa-o como coleta manual."""
    monitoramento = db.get(MonitoramentoNormativo, monitoramento_id)
    if monitoramento is None:
        raise HTTPException(404, "Monitoramento não encontrado.")

    coleta = None
    if dados and dados.conteudo:
        coleta = Coleta(True, dados.conteudo, impressao_digital(dados.conteudo))

    atualizacao = servicos.verificar_monitoramento(db, monitoramento, coleta)
    if atualizacao is None:
        return {
            "houve_mudanca": False,
            "verificado_em": monitoramento.ultima_verificacao.isoformat(),
            "erro": monitoramento.ultimo_erro,
        }
    return {
        "houve_mudanca": True,
        "atualizacao_id": str(atualizacao.id),
        "titulo": atualizacao.titulo,
        "situacao": str(atualizacao.situacao),
        "diff": atualizacao.diff,
    }


# ----------------------------------------------------------- Atualizações


class AtualizacaoManualIn(BaseModel):
    fonte_chave: str
    titulo: str
    resumo: str
    url_evidencia: str | None = None


@router.get("/atualizacoes")
def listar_atualizacoes(
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    situacao: SituacaoAtualizacao | None = None,
):
    consulta = select(AtualizacaoNormativa).order_by(AtualizacaoNormativa.criado_em.desc())
    if situacao:
        consulta = consulta.where(AtualizacaoNormativa.situacao == situacao)
    return [
        {
            "id": str(a.id), "titulo": a.titulo, "situacao": str(a.situacao),
            "origem": str(a.origem), "resumo": a.resumo,
            "detectado_em": a.detectado_em.isoformat() if a.detectado_em else None,
            "publicado_em": a.publicado_em.isoformat() if a.publicado_em else None,
            "url_evidencia": a.url_evidencia,
            "impactos_abertos": len([i for i in a.impactos if i.status == "ABERTO"]),
            "tem_diff": bool(a.diff),
        }
        for a in db.scalars(consulta).all()
    ]


@router.post("/atualizacoes", status_code=201)
def registrar_manual(
    dados: AtualizacaoManualIn,
    sessao: Sessao = Depends(exigir("normativo:fonte:editar")),
    db: Session = Depends(get_db),
):
    fonte = db.scalar(select(FonteJuridica).where(FonteJuridica.chave == dados.fonte_chave))
    if fonte is None:
        raise HTTPException(404, "Fonte não cadastrada.")
    atualizacao = servicos.registrar_atualizacao_manual(
        db, fonte.id, dados.titulo, dados.resumo, dados.url_evidencia, sessao.usuario.id
    )
    return {"id": str(atualizacao.id), "situacao": str(atualizacao.situacao)}


@router.get("/atualizacoes/{atualizacao_id}")
def obter_atualizacao(
    atualizacao_id: uuid.UUID,
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
):
    a = db.get(AtualizacaoNormativa, atualizacao_id)
    if a is None:
        raise HTTPException(404, "Atualização não encontrada.")
    return {
        "id": str(a.id), "titulo": a.titulo, "situacao": str(a.situacao),
        "origem": str(a.origem), "resumo": a.resumo, "diff": a.diff,
        "url_evidencia": a.url_evidencia,
        "hash_anterior": a.hash_anterior, "hash_novo": a.hash_novo,
        "parecer_curadoria": a.parecer_curadoria,
        "impactos": [
            {
                "id": str(i.id), "alvo_tipo": str(i.alvo_tipo), "alvo_ref": i.alvo_ref,
                "severidade": str(i.severidade), "descricao": i.descricao, "status": i.status,
            }
            for i in a.impactos
        ],
    }


class PublicacaoIn(BaseModel):
    texto_novo: str
    vigente_desde: dt.date
    resumo: str | None = None
    dispositivos_alterados: list[str] = []
    parecer_curadoria: str | None = None


@router.post("/atualizacoes/{atualizacao_id}/publicar")
def publicar(
    atualizacao_id: uuid.UUID,
    dados: PublicacaoIn,
    sessao: Sessao = Depends(exigir("normativo:fonte:curar")),
    db: Session = Depends(get_db),
):
    """Publica a nova redação e calcula o que ela atinge.

    Só um responsável com registro profissional pode publicar (§37, §46, §47).
    """
    atualizacao = db.get(AtualizacaoNormativa, atualizacao_id)
    if atualizacao is None:
        raise HTTPException(404, "Atualização não encontrada.")
    if atualizacao.situacao is SituacaoAtualizacao.PUBLICADA:
        raise HTTPException(409, "Esta atualização já foi publicada.")

    if dados.parecer_curadoria:
        atualizacao.parecer_curadoria = dados.parecer_curadoria
        db.add(atualizacao)

    try:
        resultado = servicos.publicar_atualizacao(
            db, atualizacao, dados.texto_novo, dados.vigente_desde, sessao.usuario,
            dados.dispositivos_alterados, dados.resumo,
        )
    except servicos.CuradoriaNegada as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    return {
        "id": str(resultado.id),
        "situacao": str(resultado.situacao),
        "curado_por": sessao.usuario.nome,
        "registro": sessao.usuario.registro_profissional,
        "impactos": [
            {"alvo_tipo": str(i.alvo_tipo), "alvo_ref": i.alvo_ref,
             "severidade": str(i.severidade), "descricao": i.descricao}
            for i in resultado.impactos
        ],
    }


@router.post("/atualizacoes/{atualizacao_id}/descartar")
def descartar(
    atualizacao_id: uuid.UUID,
    parecer: dict,
    sessao: Sessao = Depends(exigir("normativo:fonte:curar")),
    db: Session = Depends(get_db),
):
    """Mudança detectada que não altera o conteúdo normativo (ex.: só o layout
    da página oficial mudou). Fica registrada com o parecer de quem decidiu."""
    atualizacao = db.get(AtualizacaoNormativa, atualizacao_id)
    if atualizacao is None:
        raise HTTPException(404, "Atualização não encontrada.")
    atualizacao.situacao = SituacaoAtualizacao.DESCARTADA
    atualizacao.parecer_curadoria = parecer.get("parecer")
    atualizacao.analisado_por_id = sessao.usuario.id
    db.add(atualizacao)
    db.commit()
    return {"id": str(atualizacao.id), "situacao": str(atualizacao.situacao)}


# --------------------------------------------------------------- Impactos


@router.get("/impactos")
def listar_impactos(
    _: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db),
    apenas_abertos: bool = True,
):
    consulta = select(ImpactoNormativo)
    if apenas_abertos:
        consulta = consulta.where(ImpactoNormativo.status == "ABERTO")
    return [
        {
            "id": str(i.id), "alvo_tipo": str(i.alvo_tipo), "alvo_ref": i.alvo_ref,
            "severidade": str(i.severidade), "descricao": i.descricao, "status": i.status,
            "norma": i.atualizacao.titulo if i.atualizacao else None,
            "publicado_em": (
                i.atualizacao.publicado_em.isoformat()
                if i.atualizacao and i.atualizacao.publicado_em else None
            ),
        }
        for i in db.scalars(consulta).all()
    ]


@router.post("/impactos/{impacto_id}/tratar")
def tratar(
    impacto_id: uuid.UUID,
    sessao: Sessao = Depends(exigir("normativo:fonte:editar")),
    db: Session = Depends(get_db),
    dispensado: bool = False,
):
    impacto = db.get(ImpactoNormativo, impacto_id)
    if impacto is None:
        raise HTTPException(404, "Impacto não encontrado.")
    servicos.tratar_impacto(db, impacto, sessao.usuario.id, dispensado)
    return {"id": str(impacto.id), "status": impacto.status, "por": sessao.usuario.nome}


# --------------------------------------------------------------- Vínculos


class VinculoIn(BaseModel):
    alvo_tipo: str
    alvo_ref: str
    fonte_chave: str
    dispositivo: str | None = None
    observacao: str | None = None


@router.get("/vinculos")
def listar_vinculos(_: Sessao = Depends(sessao_atual), db: Session = Depends(get_db)):
    """O mapa que responde: se esta lei mudar, o que para de valer?"""
    return [
        {
            "id": str(v.id), "alvo_tipo": str(v.alvo_tipo), "alvo_ref": v.alvo_ref,
            "fonte_chave": v.fonte_chave, "dispositivo": v.dispositivo,
            "observacao": v.observacao,
        }
        for v in db.scalars(select(VinculoNormativo).order_by(VinculoNormativo.fonte_chave)).all()
    ]


@router.post("/vinculos", status_code=201)
def criar_vinculo(
    dados: VinculoIn,
    _: Sessao = Depends(exigir("normativo:fonte:editar")),
    db: Session = Depends(get_db),
):
    vinculo = VinculoNormativo(**dados.model_dump())
    db.add(vinculo)
    db.commit()
    db.refresh(vinculo)
    return {"id": str(vinculo.id)}
