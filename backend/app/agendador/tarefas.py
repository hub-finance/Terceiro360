"""As varreduras periódicas (§21, §37).

Regras que valem para as duas tarefas:

* **Falha isolada não derruba a rodada.** Uma fonte fora do ar não pode impedir
  a verificação das outras trinta; o erro é registrado e a varredura segue.
* **Rodar duas vezes no mesmo dia não duplica nada.** Prazo tem chave de
  idempotência, alerta guarda a janela já disparada, pendência é procurada
  antes de ser aberta. Um agendador que gera lixo ao repetir é um agendador
  que ninguém deixa ligado.
"""
from __future__ import annotations

import datetime as dt
import traceback
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Prioridade, StatusPendencia, StatusPrazo
from app.core.tempo import agora
from app.modules.agendador.models import ExecucaoTarefa
from app.modules.entidades.models import Entidade
from app.modules.governanca.servicos import agenda
from app.modules.identity.models import Usuario
from app.modules.normativo.models import MonitoramentoNormativo
from app.modules.normativo.servicos import verificar_monitoramento
from app.modules.prazos.models import Notificacao, Pendencia, Prazo


@dataclass
class Relatorio:
    tarefa: str
    numeros: dict[str, int] = field(default_factory=dict)
    falhas: list[dict] = field(default_factory=list)

    def contar(self, chave: str, quanto: int = 1) -> None:
        self.numeros[chave] = self.numeros.get(chave, 0) + quanto

    def falhar(self, alvo: str, erro: Exception) -> None:
        self.falhas.append({
            "alvo": alvo,
            "erro": f"{type(erro).__name__}: {erro}",
            "traco": traceback.format_exc(limit=3),
        })

    @property
    def resultado(self) -> str:
        return "PARCIAL" if self.falhas else "OK"

    def resumo(self) -> str:
        partes = [f"{v} {k}" for k, v in self.numeros.items()]
        texto = ", ".join(partes) if partes else "nada a fazer"
        if self.falhas:
            texto += f" — {len(self.falhas)} falha(s)"
        return texto


# --------------------------------------------------------------- vigílias


def rodar_vigilias(db: Session, momento: dt.datetime | None = None) -> Relatorio:
    """Verifica as fontes cuja periodicidade venceu.

    Só as vencidas: verificar tudo todo dia castiga os sites oficiais sem
    ganho nenhum — a periodicidade de cada fonte foi cadastrada por alguém que
    sabe com que frequência aquela norma muda.
    """
    from app.engines.normativo.motor import MotorAtualizacaoNormativa

    referencia = momento or agora()
    relatorio = Relatorio("VIGILIAS")

    monitoramentos = db.scalars(
        select(MonitoramentoNormativo).where(MonitoramentoNormativo.ativo)
    ).all()

    for m in monitoramentos:
        situacao = MotorAtualizacaoNormativa.situacao_da_vigilancia(
            m.ultima_verificacao, m.periodicidade_dias, referencia
        )
        if situacao == "EM_DIA":
            continue
        if m.modo != "HTTP":
            # Fonte de conferência manual: o agendador não tem como coletar,
            # então cobra o responsável em vez de fingir que verificou.
            _abrir_pendencia_unica(
                db,
                codigo=f"CONFERENCIA_MANUAL::{m.id}",
                descricao=f"Reconferir manualmente: {m.nome}",
                detalhamento="Esta fonte não é coletada automaticamente. "
                             "Compare o texto oficial com a redação registrada.",
                prioridade=Prioridade.MEDIA,
                responsavel_id=m.responsavel_id,
            )
            relatorio.contar("cobranças de conferência manual")
            continue
        try:
            atualizacao = verificar_monitoramento(db, m)
            relatorio.contar("fontes verificadas")
            if atualizacao is not None:
                relatorio.contar("mudanças detectadas")
        except Exception as erro:  # noqa: BLE001 — uma fonte não derruba a rodada
            db.rollback()
            relatorio.falhar(m.nome, erro)

    db.commit()
    return relatorio


# ----------------------------------------------------------------- prazos


def rodar_prazos(db: Session, hoje: dt.date | None = None) -> Relatorio:
    """Recalcula a agenda de cada entidade e dispara os alertas de janela."""
    hoje = hoje or agora().date()
    relatorio = Relatorio("PRAZOS")

    for entidade in db.scalars(select(Entidade)).all():
        try:
            _sincronizar_entidade(db, entidade, hoje, relatorio)
            db.commit()
        except Exception as erro:  # noqa: BLE001
            db.rollback()
            relatorio.falhar(entidade.razao_social, erro)

    return relatorio


def _sincronizar_entidade(
    db: Session, entidade: Entidade, hoje: dt.date, relatorio: Relatorio
) -> None:
    calculada = agenda(db, entidade, hoje)
    existentes = {
        p.chave_idempotencia: p
        for p in db.scalars(select(Prazo).where(Prazo.entidade_id == entidade.id)).all()
        if p.chave_idempotencia
    }

    vistos: set[str] = set()
    for calculado in calculada.prazos:
        vistos.add(calculado.chave)
        prazo = existentes.get(calculado.chave)
        if prazo is None:
            prazo = Prazo(
                entidade_id=entidade.id,
                tipo=calculado.tipo,
                descricao=calculado.descricao,
                data_base=calculado.data_base,
                data_limite=calculado.data_limite,
                origem=calculado.origem,
                fundamento=calculado.fundamento,
                janelas_alerta=list(calculado.janelas),
                alertas_disparados=[],
                chave_idempotencia=calculado.chave,
            )
            db.add(prazo)
            db.flush()
            relatorio.contar("prazos abertos")
        elif prazo.data_limite != calculado.data_limite:
            # A data mudou (o mandato foi prorrogado, a certidão renovada):
            # os alertas já disparados valiam para a data antiga.
            prazo.data_limite = calculado.data_limite
            prazo.alertas_disparados = []
            prazo.status = StatusPrazo.ABERTO
            db.add(prazo)
            relatorio.contar("prazos remarcados")

        if prazo.status is StatusPrazo.ABERTO:
            _atualizar_status(prazo, hoje)
            _disparar_alertas(db, prazo, calculado, hoje, relatorio)

    # O que saiu da agenda foi resolvido no mundo real (mandato encerrado,
    # exigência cumprida). Fecha em vez de deixar alertando para sempre.
    for chave, prazo in existentes.items():
        if chave not in vistos and prazo.status is StatusPrazo.ABERTO:
            prazo.status = StatusPrazo.CUMPRIDO
            db.add(prazo)
            relatorio.contar("prazos encerrados")

    for pendencia in calculada.pendencias:
        if _abrir_pendencia_unica(
            db,
            codigo=pendencia.codigo,
            descricao=pendencia.descricao,
            detalhamento=pendencia.detalhamento,
            prioridade=pendencia.prioridade,
            entidade_id=entidade.id,
        ):
            relatorio.contar("pendências abertas")


def _atualizar_status(prazo: Prazo, hoje: dt.date) -> None:
    if prazo.data_limite < hoje:
        prazo.status = StatusPrazo.VENCIDO


def _disparar_alertas(
    db: Session, prazo: Prazo, calculado, hoje: dt.date, relatorio: Relatorio
) -> None:
    janela = calculado.janela_ativa(hoje)
    if janela is None:
        return
    disparados = list(prazo.alertas_disparados or [])
    if janela in disparados:
        return

    dias = prazo.dias_restantes(hoje)
    if dias < 0:
        titulo = f"Prazo vencido há {abs(dias)} dia(s): {prazo.descricao}"
    elif dias == 0:
        titulo = f"Prazo vence hoje: {prazo.descricao}"
    else:
        titulo = f"Faltam {dias} dia(s): {prazo.descricao}"

    mensagem = (
        f"Data limite: {prazo.data_limite:%d/%m/%Y}. "
        f"Origem: {prazo.origem}."
        + (f" Fundamento: {prazo.fundamento}." if prazo.fundamento else "")
    )

    for usuario_id in _destinatarios(db, prazo):
        db.add(Notificacao(
            usuario_id=usuario_id,
            entidade_id=prazo.entidade_id,
            prazo_id=prazo.id,
            titulo=titulo[:200],
            mensagem=mensagem,
        ))
        relatorio.contar("alertas enviados")

    disparados.append(janela)
    prazo.alertas_disparados = disparados
    db.add(prazo)


def _destinatarios(db: Session, prazo: Prazo) -> list:
    """Quem recebe o alerta.

    Com responsável definido, é dele o aviso. Sem responsável, avisa todo mundo
    do cliente: um prazo sem dono é justamente o que não pode passar em branco.
    """
    if prazo.responsavel_id:
        return [prazo.responsavel_id]
    entidade = db.get(Entidade, prazo.entidade_id)
    if entidade is None:
        return []
    return list(db.scalars(
        select(Usuario.id).where(Usuario.cliente_id == entidade.cliente_id, Usuario.ativo)
    ).all())


# ------------------------------------------------------------------ apoio


def _abrir_pendencia_unica(
    db: Session,
    codigo: str,
    descricao: str,
    detalhamento: str | None = None,
    prioridade: Prioridade = Prioridade.MEDIA,
    responsavel_id=None,
    entidade_id=None,
) -> bool:
    """Abre a pendência só se não houver uma igual ainda aberta.

    Sem esta checagem, um agendador diário transformaria uma pendência não
    resolvida em trinta pendências iguais por mês — e a central de pendências,
    que existe para orientar o trabalho, viraria ruído.
    """
    ja_aberta = db.scalar(
        select(Pendencia.id).where(
            Pendencia.codigo == codigo,
            Pendencia.status.in_([StatusPendencia.ABERTA, StatusPendencia.EM_ANDAMENTO]),
        )
    )
    if ja_aberta:
        return False
    db.add(Pendencia(
        entidade_id=entidade_id,
        tipo="NORMATIVO" if entidade_id is None else "PRAZO",
        codigo=codigo,
        descricao=descricao[:400],
        detalhamento=detalhamento,
        prioridade=prioridade,
        responsavel_id=responsavel_id,
        origem="AGENDADOR",
    ))
    return True


# --------------------------------------------------------------- execução


TAREFAS = {"VIGILIAS": rodar_vigilias, "PRAZOS": rodar_prazos}


def executar(db: Session, tarefa: str, acionada_por: str = "AGENDADOR") -> ExecucaoTarefa:
    """Roda uma tarefa e registra a execução, tenha ela dado certo ou não."""
    nome = tarefa.upper()
    if nome not in TAREFAS:
        raise ValueError(f"Tarefa desconhecida: {tarefa}. Use {', '.join(TAREFAS)}.")

    registro = ExecucaoTarefa(
        tarefa=nome, iniciada_em=agora(), acionada_por=acionada_por, resultado="ERRO"
    )
    try:
        relatorio = TAREFAS[nome](db)
        registro.numeros = relatorio.numeros
        registro.falhas = relatorio.falhas
        registro.resultado = relatorio.resultado
        registro.detalhe = relatorio.resumo()
    except Exception as erro:  # noqa: BLE001
        db.rollback()
        registro.detalhe = f"{type(erro).__name__}: {erro}"
        registro.falhas = [{"alvo": nome, "erro": registro.detalhe,
                            "traco": traceback.format_exc(limit=5)}]
    finally:
        registro.concluida_em = agora()
        db.add(registro)
        db.commit()
        db.refresh(registro)
    return registro


def rodar_tudo(db: Session, acionada_por: str = "AGENDADOR") -> list[ExecucaoTarefa]:
    return [executar(db, nome, acionada_por) for nome in TAREFAS]
