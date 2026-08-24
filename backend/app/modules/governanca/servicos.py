"""Dashboard, score e linha do tempo (§29, §30, §42, §51)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import (
    SituacaoAssociado,
    SituacaoMembro,
    StatusDocumento,
    StatusEvento,
    StatusProtocolo,
)
from app.engines.inconsistencias.motor import RetratoCadastral, varrer
from app.engines.prazos.motor import (
    CertidaoParaPrazo,
    ExigenciaParaPrazo,
    MandatoParaPrazo,
    gerar_agenda,
)
from app.engines.score.motor import FotografiaEntidade, calcular
from app.modules.documentos.models import Certidao, Documento
from app.modules.entidades.models import Entidade
from app.modules.juridico.models import Assembleia, Associado, Cargo, Evento, Mandato, Orgao
from app.modules.juridico.servicos import parametros_da_entidade, versao_vigente
from app.modules.normativo.models import AtualizacaoNormativa, ImpactoNormativo
from app.modules.registral.models import Protocolo


def _mandato_atual(db: Session, entidade_id: uuid.UUID, hoje: dt.date) -> Mandato | None:
    mandatos = db.scalars(
        select(Mandato).where(Mandato.entidade_id == entidade_id).order_by(Mandato.data_fim.desc())
    ).all()
    vigentes = [m for m in mandatos if m.vigente_em(hoje)]
    return vigentes[0] if vigentes else (mandatos[0] if mandatos else None)


def retrato(db: Session, entidade: Entidade, hoje: dt.date | None = None) -> RetratoCadastral:
    hoje = hoje or dt.date.today()
    versao = versao_vigente(db, entidade.id)
    parametros = parametros_da_entidade(db, entidade.id)
    mandato = _mandato_atual(db, entidade.id, hoje)

    cargos_vagos: list[str] = []
    if mandato:
        ocupados = {
            m.cargo_id for m in mandato.membros if m.situacao is SituacaoMembro.ATIVO
        }
        cargos = db.scalars(
            select(Cargo).join(Orgao).where(
                Orgao.entidade_id == entidade.id, Cargo.obrigatorio.is_(True)
            )
        ).all()
        cargos_vagos = [c.nome for c in cargos if c.id not in ocupados]

    pessoas_sem_cpf = []
    if mandato:
        pessoas_sem_cpf = [
            m.pessoa.nome for m in mandato.membros
            if m.situacao is SituacaoMembro.ATIVO and not m.pessoa.cpf
        ]

    associados = db.scalars(select(Associado).where(Associado.entidade_id == entidade.id)).all()
    certidoes = db.scalars(select(Certidao).where(Certidao.entidade_id == entidade.id)).all()

    protocolos_exigencia = db.scalar(
        select(func.count(Protocolo.id)).where(
            Protocolo.entidade_id == entidade.id, Protocolo.status == StatusProtocolo.EM_EXIGENCIA
        )
    ) or 0
    docs_sem_assinatura = db.scalar(
        select(func.count(Documento.id)).where(
            Documento.entidade_id == entidade.id, Documento.status == StatusDocumento.APROVADO
        )
    ) or 0
    impactos = db.scalar(
        select(func.count(ImpactoNormativo.id))
        .join(AtualizacaoNormativa)
        .where(ImpactoNormativo.status == "ABERTO", AtualizacaoNormativa.situacao == "PUBLICADA")
    ) or 0

    return RetratoCadastral(
        entidade_id=str(entidade.id),
        razao_social=entidade.razao_social,
        cnpj=entidade.cnpj,
        municipio=entidade.municipio,
        uf=entidade.uf,
        rcpj_definido=entidade.rcpj_id is not None,
        rcpj_regras_desatualizadas=False,
        tem_estatuto_vigente=versao is not None,
        total_parametros=len(parametros),
        parametros_confirmados=len([p for p in parametros if p.confirmado]),
        mandato_vigente=bool(mandato and mandato.vigente_em(hoje)),
        mandato_designacao=mandato.designacao if mandato else None,
        mandato_data_fim=mandato.data_fim if mandato else None,
        cargos_obrigatorios_vagos=cargos_vagos,
        pessoas_sem_cpf=pessoas_sem_cpf,
        associados_ativos=len([a for a in associados if a.situacao is SituacaoAssociado.ATIVO]),
        associados_aptos=len([a for a in associados if a.apto_a_votar_em(hoje)]),
        certidoes_vencidas=[
            c.tipo for c in certidoes if c.data_validade and c.data_validade < hoje
        ],
        protocolos_em_exigencia=protocolos_exigencia,
        documentos_aguardando_assinatura=docs_sem_assinatura,
        impactos_normativos_abertos=impactos,
    )


def fotografia_score(db: Session, entidade: Entidade, hoje: dt.date | None = None) -> FotografiaEntidade:
    hoje = hoje or dt.date.today()
    r = retrato(db, entidade, hoje)
    versao = versao_vigente(db, entidade.id)
    mandato = _mandato_atual(db, entidade.id, hoje)

    ultima_assembleia = db.scalar(
        select(func.max(Assembleia.data_hora)).where(Assembleia.entidade_id == entidade.id)
    )
    meses_desde = None
    if ultima_assembleia:
        data = ultima_assembleia.date() if isinstance(ultima_assembleia, dt.datetime) else ultima_assembleia
        meses_desde = (hoje - data).days / 30.44

    anos_estatuto = None
    if versao and versao.data_estatuto:
        anos_estatuto = (hoje - versao.data_estatuto).days / 365.25

    registrados = db.scalar(
        select(func.count(Evento.id)).where(
            Evento.entidade_id == entidade.id, Evento.status == StatusEvento.REGISTRADO
        )
    ) or 0
    pendentes = db.scalar(
        select(func.count(Evento.id)).where(
            Evento.entidade_id == entidade.id,
            Evento.status.in_([StatusEvento.PROTOCOLADO, StatusEvento.EM_EXIGENCIA]),
        )
    ) or 0

    cargos_obrigatorios = db.scalar(
        select(func.count(Cargo.id)).join(Orgao).where(
            Orgao.entidade_id == entidade.id, Cargo.obrigatorio.is_(True)
        )
    ) or 0

    return FotografiaEntidade(
        tem_estatuto_vigente=r.tem_estatuto_vigente,
        anos_desde_ultima_alteracao_estatuto=anos_estatuto,
        total_parametros=r.total_parametros,
        parametros_confirmados=r.parametros_confirmados,
        cargos_obrigatorios=cargos_obrigatorios,
        cargos_preenchidos=max(0, cargos_obrigatorios - len(r.cargos_obrigatorios_vagos)),
        mandato_vigente=r.mandato_vigente,
        dias_para_fim_mandato=(mandato.data_fim - hoje).days if mandato else None,
        meses_desde_ultima_assembleia=meses_desde,
        exercicios_pendentes_aprovacao=0,
        tem_conselho_fiscal=_tem_conselho_fiscal(db, entidade.id),
        conselho_fiscal_preenchido=_conselho_preenchido(db, entidade.id, hoje),
        documentos_obrigatorios=0,
        documentos_presentes=0,
        certidoes_totais=db.scalar(
            select(func.count(Certidao.id)).where(Certidao.entidade_id == entidade.id)
        ) or 0,
        certidoes_validas=max(
            0,
            (db.scalar(select(func.count(Certidao.id)).where(Certidao.entidade_id == entidade.id)) or 0)
            - len(r.certidoes_vencidas),
        ),
        atos_pendentes_registro=pendentes,
        atos_registrados=registrados,
    )


def _tem_conselho_fiscal(db: Session, entidade_id: uuid.UUID) -> bool | None:
    orgao = db.scalar(
        select(Orgao).where(Orgao.entidade_id == entidade_id, Orgao.codigo == "CONSELHO_FISCAL")
    )
    return True if orgao else None


def _conselho_preenchido(db: Session, entidade_id: uuid.UUID, hoje: dt.date) -> bool:
    mandato = db.scalar(
        select(Mandato).join(Orgao).where(
            Mandato.entidade_id == entidade_id, Orgao.codigo == "CONSELHO_FISCAL"
        ).order_by(Mandato.data_fim.desc())
    )
    return bool(mandato and mandato.vigente_em(hoje) and mandato.membros)


def agenda(db: Session, entidade: Entidade, hoje: dt.date | None = None):
    hoje = hoje or dt.date.today()
    from app.engines.conformidade.resolucao import ResolvedorParametros

    resolvedor = ResolvedorParametros(parametros_da_entidade(db, entidade.id), data_referencia=hoje)
    mandatos = db.scalars(select(Mandato).where(Mandato.entidade_id == entidade.id)).all()
    certidoes = db.scalars(select(Certidao).where(Certidao.entidade_id == entidade.id)).all()
    protocolos = db.scalars(
        select(Protocolo).where(
            Protocolo.entidade_id == entidade.id, Protocolo.status == StatusProtocolo.EM_EXIGENCIA
        )
    ).all()

    exigencias = [
        ExigenciaParaPrazo(
            protocolo_id=str(p.id),
            descricao=e.get("descricao", "Exigência do cartório"),
            prazo=dt.date.fromisoformat(e["prazo"]) if e.get("prazo") else None,
            cumprida=e.get("cumprida", False),
        )
        for p in protocolos
        for e in (p.exigencias or [])
    ]

    ultima_ago = db.scalar(
        select(func.max(Assembleia.data_hora)).where(
            Assembleia.entidade_id == entidade.id, Assembleia.tipo == "ORDINARIA"
        )
    )

    return gerar_agenda(
        hoje=hoje,
        mandatos=[
            MandatoParaPrazo(str(m.id), m.designacao, m.orgao.codigo or m.orgao.nome,
                             m.data_fim, m.encerrado)
            for m in mandatos
        ],
        certidoes=[CertidaoParaPrazo(str(c.id), c.tipo, c.data_validade) for c in certidoes],
        exigencias=exigencias,
        ultima_assembleia_ordinaria=(
            ultima_ago.date() if isinstance(ultima_ago, dt.datetime) else ultima_ago
        ),
        periodicidade_ago=resolvedor.resolver("AGO_PERIODICIDADE_MESES"),
        prazo_aprovacao_contas=resolvedor.resolver("AGO_PRAZO_APROVACAO_CONTAS"),
    )


def dashboard(db: Session, entidade: Entidade, hoje: dt.date | None = None) -> dict:
    """§51 — a primeira tela da entidade."""
    hoje = hoje or dt.date.today()
    r = retrato(db, entidade, hoje)
    score = calcular(fotografia_score(db, entidade, hoje), hoje=hoje)
    inconsistencias = varrer(r, hoje)
    ag = agenda(db, entidade, hoje)
    mandato = _mandato_atual(db, entidade.id, hoje)
    versao = versao_vigente(db, entidade.id)

    atos_andamento = db.scalars(
        select(Evento).where(
            Evento.entidade_id == entidade.id,
            Evento.status.notin_([StatusEvento.REGISTRADO, StatusEvento.ARQUIVADO,
                                  StatusEvento.CANCELADO]),
        ).order_by(Evento.criado_em.desc()).limit(10)
    ).all()

    return {
        "entidade": {
            "id": str(entidade.id),
            "razao_social": entidade.razao_social,
            "cnpj": entidade.cnpj,
            "tipo": str(entidade.tipo_entidade),
            "municipio": entidade.municipio,
            "uf": entidade.uf,
            "situacao_cadastral": entidade.situacao_cadastral,
        },
        "estatuto": {
            "versao": versao.numero_versao if versao else None,
            "data": versao.data_estatuto.isoformat() if versao and versao.data_estatuto else None,
            "registro": versao.numero_registro if versao else None,
            "parametros_confirmados": r.parametros_confirmados,
            "parametros_totais": r.total_parametros,
        },
        "diretoria": {
            "gestao": mandato.designacao if mandato else None,
            "vigente": r.mandato_vigente,
            "inicio": mandato.data_inicio.isoformat() if mandato else None,
            "fim": mandato.data_fim.isoformat() if mandato else None,
            "membros": [
                {"nome": m.pessoa.nome, "cargo": m.cargo.nome}
                for m in (mandato.membros if mandato else [])
                if m.situacao is SituacaoMembro.ATIVO
            ],
            "cargos_vagos": r.cargos_obrigatorios_vagos,
        },
        "score": score.to_dict(),
        "pendencias": [i.to_dict() for i in inconsistencias],
        "prazos": [
            {
                "descricao": p.descricao,
                "tipo": p.tipo.value,
                "data_limite": p.data_limite.isoformat(),
                "dias_restantes": p.dias_restantes(hoje),
                "prioridade": p.prioridade(hoje).value,
                "origem": p.origem,
                "fundamento": p.fundamento,
            }
            for p in ag.prazos[:15]
        ],
        "alertas": [
            {"descricao": p.descricao, "janela_dias": j, "data_limite": p.data_limite.isoformat()}
            for p, j in ag.alertas(hoje)
        ],
        "atos_em_andamento": [
            {
                "id": str(e.id),
                "tipo": str(e.tipo),
                "titulo": e.titulo,
                "status": str(e.status),
                "semaforo": str(e.semaforo) if e.semaforo else None,
                "data": e.data_referencia.isoformat() if e.data_referencia else None,
            }
            for e in atos_andamento
        ],
    }
