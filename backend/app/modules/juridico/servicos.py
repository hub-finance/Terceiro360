"""Serviços do módulo jurídico — a ponte entre o banco e os motores."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import SituacaoAssociado, SituacaoMembro, StatusEvento
from app.engines.conformidade.base_normativa import BaseNormativaDB
from app.engines.conformidade.resolucao import ParametroEstatutario, ResolvedorParametros
from app.engines.validacao.contexto import (
    ContextoValidacao,
    EntidadeInfo,
    EstatutoInfo,
    ImpactoNormativoInfo,
    MandatoInfo,
    MembroInfo,
    RCPJInfo,
    RegraRCPJInfo,
)
from app.modules.documentos.models import Documento
from app.modules.entidades.models import Entidade
from app.modules.juridico.models import (
    Associado,
    Estatuto,
    EstatutoParametro,
    EstatutoVersao,
    Evento,
    Mandato,
)
from app.modules.normativo.models import AtualizacaoNormativa, ImpactoNormativo
from app.modules.registral.models import RCPJ, RegraRCPJ


def versao_vigente(db: Session, entidade_id: uuid.UUID) -> EstatutoVersao | None:
    estatuto = db.scalar(select(Estatuto).where(Estatuto.entidade_id == entidade_id))
    if estatuto is None:
        return None
    return db.scalar(
        select(EstatutoVersao)
        .where(EstatutoVersao.estatuto_id == estatuto.id, EstatutoVersao.vigente.is_(True))
        .order_by(EstatutoVersao.numero_versao.desc())
    )


def parametros_da_entidade(db: Session, entidade_id: uuid.UUID) -> list[ParametroEstatutario]:
    versao = versao_vigente(db, entidade_id)
    if versao is None:
        return []
    registros = db.scalars(
        select(EstatutoParametro).where(EstatutoParametro.versao_id == versao.id)
    ).all()
    return [
        ParametroEstatutario(
            chave=p.chave,
            valor=_converter(p.valor, p.tipo_valor),
            confirmado=p.confirmado,
            dispositivo=p.dispositivo,
            trecho=p.trecho,
            origem=p.origem,
            observacao=p.observacao,
        )
        for p in registros
    ]


def _converter(valor: str | None, tipo: str):
    if valor is None:
        return None
    if tipo == "inteiro":
        try:
            return int(valor)
        except ValueError:
            return valor
    if tipo == "decimal":
        try:
            return float(valor)
        except ValueError:
            return valor
    if tipo == "booleano":
        return str(valor).strip().upper() in ("TRUE", "SIM", "1", "S", "V")
    if tipo == "lista":
        return [p.strip() for p in str(valor).split(";") if p.strip()]
    return valor


def mandatos_da_entidade(db: Session, entidade_id: uuid.UUID) -> list[MandatoInfo]:
    mandatos = db.scalars(select(Mandato).where(Mandato.entidade_id == entidade_id)).all()
    resultado = []
    for m in mandatos:
        membros = [
            MembroInfo(
                pessoa_id=str(mm.pessoa_id),
                nome=mm.pessoa.nome,
                cargo=mm.cargo.nome,
                cargo_codigo=mm.cargo.codigo,
                situacao=str(mm.situacao),
            )
            for mm in m.membros
            if mm.situacao is SituacaoMembro.ATIVO
        ]
        resultado.append(
            MandatoInfo(
                id=str(m.id),
                orgao=m.orgao.codigo or m.orgao.nome,
                designacao=m.designacao,
                data_inicio=m.data_inicio,
                data_fim=m.data_fim,
                encerrado=m.encerrado,
                membros=membros,
            )
        )
    return resultado


def contar_associados(db: Session, entidade_id: uuid.UUID, data: dt.date) -> tuple[int, int]:
    associados = db.scalars(select(Associado).where(Associado.entidade_id == entidade_id)).all()
    ativos = [a for a in associados if a.situacao is SituacaoAssociado.ATIVO]
    aptos = [a for a in associados if a.apto_a_votar_em(data)]
    return len(ativos), len(aptos)


def rcpj_da_entidade(
    db: Session, entidade: Entidade, tipo_evento: str, hoje: dt.date
) -> RCPJInfo | None:
    rcpj = None
    if entidade.rcpj_id:
        rcpj = db.get(RCPJ, entidade.rcpj_id)
    elif entidade.municipio and entidade.uf:
        rcpj = db.scalar(
            select(RCPJ).where(RCPJ.uf == entidade.uf, RCPJ.municipio == entidade.municipio)
        )
    if rcpj is None:
        return None

    regra = db.scalar(
        select(RegraRCPJ).where(RegraRCPJ.rcpj_id == rcpj.id, RegraRCPJ.tipo_evento == tipo_evento)
    )
    return RCPJInfo(
        id=str(rcpj.id),
        nome=rcpj.nome,
        uf=rcpj.uf,
        municipio=rcpj.municipio,
        exige_reconhecimento_firma=rcpj.exige_reconhecimento_firma,
        exige_visto_advogado=rcpj.exige_visto_advogado,
        data_ultima_verificacao=rcpj.data_ultima_verificacao,
        regras_desatualizadas=rcpj.regras_desatualizadas_em(hoje),
        regra_evento=(
            RegraRCPJInfo(
                tipo_evento=regra.tipo_evento,
                documentos_exigidos=regra.documentos_exigidos or [],
                exige_reconhecimento_firma=regra.exige_reconhecimento_firma,
                exige_visto_advogado=regra.exige_visto_advogado,
                vias=regra.vias,
                fonte_informacao=regra.fonte_informacao,
                data_ultima_verificacao=regra.data_ultima_verificacao,
            )
            if regra
            else None
        ),
    )


def impactos_abertos(db: Session, entidade_id: uuid.UUID) -> list[ImpactoNormativoInfo]:
    """Mudanças normativas publicadas que ainda não foram tratadas."""
    registros = db.scalars(
        select(ImpactoNormativo)
        .join(AtualizacaoNormativa)
        .where(
            ImpactoNormativo.status == "ABERTO",
            AtualizacaoNormativa.situacao == "PUBLICADA",
            (ImpactoNormativo.entidade_id.is_(None))
            | (ImpactoNormativo.entidade_id == entidade_id),
        )
    ).all()
    return [
        ImpactoNormativoInfo(
            alvo_tipo=str(i.alvo_tipo),
            alvo_ref=i.alvo_ref,
            severidade=str(i.severidade),
            descricao=i.descricao or "Mudança normativa pendente de revisão.",
            norma=i.atualizacao.titulo if i.atualizacao else None,
        )
        for i in registros
    ]


def documentos_anexados(db: Session, evento_id: uuid.UUID) -> set[str]:
    tipos = db.scalars(select(Documento.tipo).where(Documento.evento_id == evento_id)).all()
    return {str(t) for t in tipos}


def montar_contexto(db: Session, evento: Evento) -> ContextoValidacao:
    """Reúne LEI + ESTATUTO + RCPJ + DADOS DA ENTIDADE para um ato concreto (§4)."""
    entidade = db.get(Entidade, evento.entidade_id)
    hoje = dt.date.today()
    data_ato = evento.data_referencia or hoje

    versao = versao_vigente(db, entidade.id)
    estatuto_info = None
    if versao is not None:
        total = db.scalar(
            select(func.count(EstatutoParametro.id)).where(EstatutoParametro.versao_id == versao.id)
        ) or 0
        confirmados = db.scalar(
            select(func.count(EstatutoParametro.id)).where(
                EstatutoParametro.versao_id == versao.id, EstatutoParametro.confirmado.is_(True)
            )
        ) or 0
        estatuto_info = EstatutoInfo(
            versao=versao.numero_versao,
            vigente=versao.vigente,
            data_estatuto=versao.data_estatuto,
            data_registro=versao.data_registro,
            numero_registro=versao.numero_registro,
            livro=versao.livro,
            folha=versao.folha,
            total_parametros=total,
            parametros_confirmados=confirmados,
        )

    ativos, aptos = contar_associados(db, entidade.id, data_ato)

    return ContextoValidacao(
        entidade=EntidadeInfo(
            id=str(entidade.id),
            razao_social=entidade.razao_social,
            tipo_entidade=entidade.tipo_entidade,
            cnpj=entidade.cnpj,
            municipio=entidade.municipio,
            uf=entidade.uf,
            data_constituicao=entidade.data_constituicao,
        ),
        tipo_evento=str(evento.tipo),
        resolvedor=ResolvedorParametros(
            parametros_da_entidade(db, entidade.id),
            normas=BaseNormativaDB(db),
            data_referencia=data_ato,
        ),
        data_ato=data_ato,
        hoje=hoje,
        dados=evento.dados or {},
        estatuto=estatuto_info,
        mandatos=mandatos_da_entidade(db, entidade.id),
        total_associados=ativos,
        associados_aptos=aptos,
        rcpj=rcpj_da_entidade(db, entidade, str(evento.tipo), hoje),
        documentos_anexados=documentos_anexados(db, evento.id),
        impactos_normativos=impactos_abertos(db, entidade.id),
    )


def registrar_validacao(db: Session, evento: Evento, resultado) -> Evento:
    evento.semaforo = resultado.semaforo
    evento.validado_em = dt.datetime.utcnow()
    evento.resultado_validacao = resultado.to_dict()
    if evento.status is StatusEvento.RASCUNHO:
        evento.status = StatusEvento.EM_VALIDACAO
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento
