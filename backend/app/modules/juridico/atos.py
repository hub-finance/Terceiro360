"""Ciclo de vida do ato e atualização automática do cadastro (§28, §41, §42).

Quando um ato chega a REGISTRADO, o sistema reflete o resultado no cadastro:
a nova gestão entra, a anterior é **encerrada — nunca apagada** — e a linha do
tempo jurídica ganha um marco.
"""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import SituacaoMembro, StatusEvento, TipoEvento
from app.modules.compliance.models import RegistroAuditoria
from app.modules.governanca.models import EventoLinhaTempo
from app.modules.juridico.models import Cargo, Evento, Mandato, MandatoMembro, Orgao, Pessoa

# §28 — a ordem do ciclo. Voltar atrás só por CANCELADO.
ORDEM = [
    StatusEvento.RASCUNHO, StatusEvento.EM_VALIDACAO, StatusEvento.GERADO,
    StatusEvento.EM_REVISAO, StatusEvento.REVISADO, StatusEvento.APROVADO,
    StatusEvento.ASSINADO, StatusEvento.PROTOCOLADO, StatusEvento.EM_EXIGENCIA,
    StatusEvento.REGISTRADO, StatusEvento.ARQUIVADO,
]


def transicionar(
    db: Session, evento: Evento, novo: StatusEvento, usuario_id: uuid.UUID,
    observacao: str | None = None,
) -> Evento:
    atual = evento.status
    if novo is StatusEvento.CANCELADO:
        pass
    elif atual is StatusEvento.CANCELADO:
        raise HTTPException(409, "Ato cancelado não avança de etapa.")
    elif novo is not StatusEvento.EM_EXIGENCIA and ORDEM.index(novo) < ORDEM.index(atual):
        raise HTTPException(
            409,
            f"Não é possível voltar de {atual} para {novo}. Registre um novo ato ou cancele este.",
        )

    db.add(RegistroAuditoria(
        entidade_id=evento.entidade_id,
        tabela="eventos",
        registro_id=str(evento.id),
        operacao="UPDATE",
        antes={"status": str(atual)},
        depois={"status": str(novo)},
        usuario_id=usuario_id,
        motivo=observacao,
    ))
    evento.status = novo
    db.add(evento)
    db.commit()
    return evento


def concluir_registro(db: Session, evento: Evento, usuario_id: uuid.UUID) -> dict:
    """Fecha o ciclo: marca REGISTRADO e reflete o efeito no cadastro."""
    transicionar(db, evento, StatusEvento.REGISTRADO, usuario_id,
                 "Registro concluído no RCPJ")

    efeitos: list[str] = []
    tipo = str(evento.tipo)

    if tipo in (TipoEvento.ELEICAO_DIRETORIA.value, TipoEvento.REELEICAO_DIRETORIA.value,
                TipoEvento.POSSE_DIRETORIA.value, TipoEvento.CONSTITUICAO.value):
        efeitos.extend(_atualizar_quadro_diretivo(db, evento))

    if tipo == TipoEvento.RENUNCIA.value:
        efeitos.extend(_encerrar_membro(db, evento, SituacaoMembro.RENUNCIANTE))

    if tipo == TipoEvento.DESTITUICAO.value:
        efeitos.extend(_encerrar_membro(db, evento, SituacaoMembro.DESTITUIDO))

    db.add(EventoLinhaTempo(
        entidade_id=evento.entidade_id,
        data=evento.data_referencia or dt.date.today(),
        titulo=evento.titulo or tipo.replace("_", " ").title(),
        descricao="; ".join(efeitos) if efeitos else None,
        evento_id=evento.id,
    ))
    db.commit()
    return {"evento_id": str(evento.id), "status": str(evento.status), "efeitos": efeitos}


def _atualizar_quadro_diretivo(db: Session, evento: Evento) -> list[str]:
    dados = evento.dados or {}
    eleitos = dados.get("eleitos") or []
    if not eleitos:
        return ["Nenhum eleito informado: quadro diretivo não alterado."]

    inicio = _data(dados.get("mandato_inicio")) or evento.data_referencia or dt.date.today()
    fim = _data(dados.get("mandato_fim"))
    if fim is None:
        return ["Término do mandato não informado: quadro diretivo não alterado. "
                "Informe as datas do mandato e registre novamente."]

    orgao = db.scalar(
        select(Orgao).where(Orgao.entidade_id == evento.entidade_id, Orgao.codigo == "DIRETORIA")
    )
    if orgao is None:
        orgao = Orgao(entidade_id=evento.entidade_id, nome="Diretoria", codigo="DIRETORIA",
                      tipo="EXECUTIVO")
        db.add(orgao)
        db.flush()

    efeitos = []
    # A gestão anterior é encerrada, não apagada (§41).
    anteriores = db.scalars(
        select(Mandato).where(
            Mandato.entidade_id == evento.entidade_id,
            Mandato.orgao_id == orgao.id,
            Mandato.encerrado.is_(False),
        )
    ).all()
    for m in anteriores:
        m.encerrado = True
        db.add(m)
        for membro in m.membros:
            if membro.situacao is SituacaoMembro.ATIVO:
                membro.situacao = SituacaoMembro.ENCERRADO
                membro.data_fim = membro.data_fim or m.data_fim
                db.add(membro)
        efeitos.append(f"Gestão {m.designacao} encerrada e arquivada no histórico.")

    designacao = dados.get("mandato_designacao") or f"GESTÃO {inicio.year}–{fim.year}"
    mandato = Mandato(
        entidade_id=evento.entidade_id, orgao_id=orgao.id, designacao=designacao,
        data_inicio=inicio, data_fim=fim, evento_origem_id=evento.id,
    )
    db.add(mandato)
    db.flush()

    for eleito in eleitos:
        nome = eleito.get("nome")
        cargo_nome = eleito.get("cargo")
        if not nome or not cargo_nome:
            continue
        pessoa = _pessoa(db, evento, nome, eleito.get("cpf"))
        cargo = _cargo(db, orgao, cargo_nome)
        db.add(MandatoMembro(
            mandato_id=mandato.id, pessoa_id=pessoa.id, cargo_id=cargo.id,
            data_inicio=inicio, data_fim=fim, situacao=SituacaoMembro.ATIVO,
        ))
        efeitos.append(f"{nome} empossado(a) como {cargo_nome}.")

    efeitos.append(f"Nova gestão registrada: {designacao} ({inicio:%d/%m/%Y} a {fim:%d/%m/%Y}).")
    db.commit()
    return efeitos


def _encerrar_membro(db: Session, evento: Evento, situacao: SituacaoMembro) -> list[str]:
    dados = evento.dados or {}
    nome = dados.get("pessoa")
    if not nome:
        return ["Pessoa não informada: quadro diretivo não alterado."]

    membros = db.scalars(
        select(MandatoMembro)
        .join(Mandato)
        .join(Pessoa)
        .where(
            Mandato.entidade_id == evento.entidade_id,
            Pessoa.nome == nome,
            MandatoMembro.situacao == SituacaoMembro.ATIVO,
        )
    ).all()
    if not membros:
        return [f"Não foi encontrado vínculo ativo de “{nome}” no quadro diretivo."]

    data = evento.data_referencia or dt.date.today()
    efeitos = []
    for membro in membros:
        membro.situacao = situacao
        membro.data_fim = data
        db.add(membro)
        efeitos.append(
            f"{nome} deixou o cargo de {membro.cargo.nome} em {data:%d/%m/%Y} "
            f"({situacao.value.lower()})."
        )
    db.commit()
    return efeitos


def _pessoa(db: Session, evento: Evento, nome: str, cpf: str | None) -> Pessoa:
    from app.modules.entidades.models import Entidade

    entidade = db.get(Entidade, evento.entidade_id)
    consulta = select(Pessoa).where(Pessoa.cliente_id == entidade.cliente_id)
    pessoa = db.scalar(consulta.where(Pessoa.cpf == cpf)) if cpf else None
    if pessoa is None:
        pessoa = db.scalar(consulta.where(Pessoa.nome == nome))
    if pessoa is None:
        pessoa = Pessoa(cliente_id=entidade.cliente_id, nome=nome, cpf=cpf)
        db.add(pessoa)
        db.flush()
    return pessoa


def _cargo(db: Session, orgao: Orgao, nome: str) -> Cargo:
    codigo = _codigo_cargo(nome)
    cargo = db.scalar(
        select(Cargo).where(Cargo.orgao_id == orgao.id, Cargo.codigo == codigo)
    )
    if cargo is None:
        cargo = Cargo(orgao_id=orgao.id, nome=nome, codigo=codigo)
        db.add(cargo)
        db.flush()
    return cargo


def _codigo_cargo(nome: str) -> str:
    import unicodedata

    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", nome) if unicodedata.category(c) != "Mn"
    )
    return sem_acento.strip().upper().replace(" ", "_").replace("-", "_")


def _data(valor) -> dt.date | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, dt.date):
        return valor
    try:
        return dt.date.fromisoformat(str(valor))
    except ValueError:
        return None
