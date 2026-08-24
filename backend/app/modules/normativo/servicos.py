"""Serviços da Central de Fontes e do Motor de Atualização Normativa."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import (
    AlvoImpacto,
    OrigemDeteccao,
    SeveridadeImpacto,
    SituacaoAtualizacao,
    SituacaoVersaoNorma,
)
from app.engines.normativo.coletor import Coleta, ColetorHTTP, ColetorManual
from app.engines.normativo.motor import MotorAtualizacaoNormativa, Vinculo
from app.modules.identity.models import Usuario
from app.modules.normativo.models import (
    AtualizacaoNormativa,
    Dispositivo,
    FonteJuridica,
    FonteVersao,
    ImpactoNormativo,
    MonitoramentoNormativo,
    VinculoNormativo,
)
from app.modules.prazos.models import Pendencia
from app.core.enums import Prioridade


class CuradoriaNegada(RuntimeError):
    """Quem publica norma precisa ter habilitação profissional registrada."""


def _vinculos(db: Session) -> list[Vinculo]:
    return [
        Vinculo(
            alvo_tipo=v.alvo_tipo,
            alvo_ref=v.alvo_ref,
            fonte_chave=v.fonte_chave,
            dispositivo=v.dispositivo,
        )
        for v in db.scalars(select(VinculoNormativo)).all()
    ]


def verificar_monitoramento(
    db: Session, monitoramento: MonitoramentoNormativo, coleta: Coleta | None = None
) -> AtualizacaoNormativa | None:
    """Executa uma vigília. Devolve a atualização criada, se houve mudança."""
    coletor = ColetorHTTP() if monitoramento.modo == "HTTP" else ColetorManual()
    motor = MotorAtualizacaoNormativa(coletor)

    versao_atual = _versao_vigente(db, monitoramento.fonte_id) if monitoramento.fonte_id else None
    deteccao = motor.verificar(
        url=monitoramento.url,
        hash_anterior=monitoramento.ultimo_hash,
        texto_anterior=versao_atual.texto_referencia if versao_atual else None,
        coleta=coleta,
    )

    monitoramento.ultima_verificacao = dt.datetime.utcnow()
    monitoramento.ultimo_erro = deteccao.erro
    if deteccao.hash_novo:
        monitoramento.ultimo_hash = deteccao.hash_novo
    db.add(monitoramento)

    if deteccao.exige_conferencia_manual:
        _abrir_pendencia_conferencia(db, monitoramento, deteccao.motivo)
        db.commit()
        return None

    if not deteccao.houve_mudanca:
        db.commit()
        return None

    atualizacao = AtualizacaoNormativa(
        fonte_id=monitoramento.fonte_id,
        rcpj_id=monitoramento.rcpj_id,
        monitoramento_id=monitoramento.id,
        origem=OrigemDeteccao.MONITOR,
        situacao=SituacaoAtualizacao.DETECTADA,
        titulo=f"Possível alteração em {monitoramento.nome}",
        resumo=deteccao.motivo,
        diff=deteccao.diff,
        url_evidencia=monitoramento.url,
        hash_anterior=deteccao.hash_anterior,
        hash_novo=deteccao.hash_novo,
        detectado_em=dt.datetime.utcnow(),
    )
    db.add(atualizacao)
    db.flush()

    _abrir_pendencia_triagem(db, atualizacao, monitoramento.responsavel_id)
    db.commit()
    db.refresh(atualizacao)
    return atualizacao


def registrar_atualizacao_manual(
    db: Session, fonte_id: uuid.UUID, titulo: str, resumo: str,
    url_evidencia: str | None = None, usuario_id: uuid.UUID | None = None,
) -> AtualizacaoNormativa:
    atualizacao = AtualizacaoNormativa(
        fonte_id=fonte_id,
        origem=OrigemDeteccao.MANUAL,
        situacao=SituacaoAtualizacao.EM_ANALISE,
        titulo=titulo,
        resumo=resumo,
        url_evidencia=url_evidencia,
        detectado_em=dt.datetime.utcnow(),
        analisado_por_id=usuario_id,
    )
    db.add(atualizacao)
    db.commit()
    db.refresh(atualizacao)
    return atualizacao


def publicar_atualizacao(
    db: Session,
    atualizacao: AtualizacaoNormativa,
    texto_novo: str,
    vigente_desde: dt.date,
    curador: Usuario,
    dispositivos_alterados: list[str] | None = None,
    resumo: str | None = None,
) -> AtualizacaoNormativa:
    """Publica a nova redação. Exige curador com habilitação registrada (§47)."""
    if not curador.registro_profissional:
        raise CuradoriaNegada(
            "A publicação de norma exige responsável com registro profissional cadastrado "
            "(OAB/CRC). Isso é o que sustenta a fundamentação usada nos atos."
        )

    fonte = db.get(FonteJuridica, atualizacao.fonte_id)
    if fonte is None:
        raise ValueError("Atualização sem fonte vinculada.")

    versao_atual = _versao_vigente(db, fonte.id)
    motor = MotorAtualizacaoNormativa()
    resultado = motor.publicar(
        versao_atual=_para_motor(versao_atual),
        texto_novo=texto_novo,
        vigente_desde=vigente_desde,
        curado_por=str(curador.id),
        resumo=resumo,
        dispositivos_alterados=dispositivos_alterados,
        fonte_chave=fonte.chave,
        vinculos=_vinculos(db),
    )

    if versao_atual is not None:
        versao_atual.situacao = SituacaoVersaoNorma.SUPERADA
        versao_atual.vigente_ate = resultado.versao_anterior.vigente_ate
        db.add(versao_atual)

    nova = FonteVersao(
        fonte_id=fonte.id,
        numero_versao=resultado.versao_nova.numero,
        situacao=SituacaoVersaoNorma.VIGENTE,
        vigente_desde=vigente_desde,
        publicado_em=dt.date.today(),
        resumo_alteracao=resumo or atualizacao.resumo,
        texto_referencia=texto_novo,
        url_captura=atualizacao.url_evidencia,
        hash_conteudo=resultado.versao_nova.hash_conteudo,
        origem_captura=atualizacao.origem,
        curado_por_id=curador.id,
        curado_em=dt.datetime.utcnow(),
        registro_profissional_curador=curador.registro_profissional,
    )
    db.add(nova)
    db.flush()

    for identificacao in dispositivos_alterados or []:
        db.add(Dispositivo(versao_id=nova.id, identificacao=identificacao))

    atualizacao.situacao = SituacaoAtualizacao.PUBLICADA
    atualizacao.publicado_em = dt.datetime.utcnow()
    atualizacao.fonte_versao_gerada_id = nova.id
    atualizacao.analisado_por_id = curador.id
    db.add(atualizacao)

    for impacto in resultado.impactos:
        db.add(ImpactoNormativo(
            atualizacao_id=atualizacao.id,
            alvo_tipo=impacto.alvo_tipo,
            alvo_ref=impacto.alvo_ref,
            severidade=impacto.severidade,
            descricao=impacto.descricao,
            status="ABERTO",
        ))

    db.commit()
    db.refresh(atualizacao)
    return atualizacao


def tratar_impacto(
    db: Session, impacto: ImpactoNormativo, usuario_id: uuid.UUID, dispensado: bool = False
) -> ImpactoNormativo:
    impacto.status = "DISPENSADO" if dispensado else "TRATADO"
    impacto.tratado_por_id = usuario_id
    impacto.tratado_em = dt.datetime.utcnow()
    db.add(impacto)
    db.commit()
    db.refresh(impacto)
    return impacto


def vigilancias_vencidas(db: Session, agora: dt.datetime | None = None) -> list[dict]:
    agora = agora or dt.datetime.utcnow()
    resultado = []
    for m in db.scalars(select(MonitoramentoNormativo).where(MonitoramentoNormativo.ativo)).all():
        situacao = MotorAtualizacaoNormativa.situacao_da_vigilancia(
            m.ultima_verificacao, m.periodicidade_dias, agora
        )
        if situacao != "EM_DIA":
            resultado.append({
                "id": str(m.id),
                "nome": m.nome,
                "modo": m.modo,
                "situacao": situacao,
                "ultima_verificacao": m.ultima_verificacao.isoformat() if m.ultima_verificacao else None,
                "periodicidade_dias": m.periodicidade_dias,
                "proxima_verificacao": MotorAtualizacaoNormativa.proxima_verificacao(
                    m.ultima_verificacao, m.periodicidade_dias
                ).isoformat(),
            })
    return resultado


def _versao_vigente(db: Session, fonte_id: uuid.UUID | None) -> FonteVersao | None:
    if fonte_id is None:
        return None
    return db.scalar(
        select(FonteVersao)
        .where(FonteVersao.fonte_id == fonte_id, FonteVersao.situacao == SituacaoVersaoNorma.VIGENTE)
        .order_by(FonteVersao.numero_versao.desc())
    )


def _para_motor(versao: FonteVersao | None):
    if versao is None:
        return None
    from app.engines.normativo.motor import VersaoNorma

    return VersaoNorma(
        numero=versao.numero_versao,
        situacao=versao.situacao,
        vigente_desde=versao.vigente_desde,
        vigente_ate=versao.vigente_ate,
        texto=versao.texto_referencia,
        hash_conteudo=versao.hash_conteudo,
        curado_por=str(versao.curado_por_id) if versao.curado_por_id else None,
        curado_em=versao.curado_em,
    )


def _abrir_pendencia_conferencia(db: Session, m: MonitoramentoNormativo, motivo: str) -> None:
    db.add(Pendencia(
        entidade_id=None,
        tipo="NORMATIVO",
        codigo=f"CONFERENCIA_MANUAL::{m.id}",
        descricao=f"Reconferir manualmente: {m.nome}",
        detalhamento=motivo,
        prioridade=Prioridade.MEDIA,
        responsavel_id=m.responsavel_id,
        origem="MONITORAMENTO",
    ))


def _abrir_pendencia_triagem(
    db: Session, atualizacao: AtualizacaoNormativa, responsavel_id: uuid.UUID | None
) -> None:
    db.add(Pendencia(
        entidade_id=None,
        tipo="NORMATIVO",
        codigo=f"TRIAGEM_NORMA::{atualizacao.id}",
        descricao=f"Triar alteração normativa: {atualizacao.titulo}",
        detalhamento="Mudança detectada na fonte oficial. Analise o diff e decida se gera nova "
                     "versão da norma na Central de Fontes.",
        prioridade=Prioridade.ALTA,
        responsavel_id=responsavel_id,
        origem="MONITORAMENTO",
    ))
