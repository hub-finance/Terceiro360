import datetime as dt

from app.core.enums import Prioridade, StatusParametro, TipoPrazo
from app.engines.base import ParametroResolvido
from app.engines.prazos.motor import (
    CertidaoParaPrazo,
    ExigenciaParaPrazo,
    MandatoParaPrazo,
    gerar_agenda,
)

HOJE = dt.date(2026, 8, 24)


def _confirmado(chave, valor):
    return ParametroResolvido(chave=chave, valor=valor, status=StatusParametro.CONFIRMADO)


def test_fim_de_mandato_gera_prazo_e_alerta():
    agenda = gerar_agenda(HOJE, mandatos=[
        MandatoParaPrazo("m1", "GESTÃO 2024–2026", "DIRETORIA", dt.date(2026, 9, 30))
    ])
    fim = next(p for p in agenda.prazos if p.tipo is TipoPrazo.FIM_MANDATO)
    assert fim.dias_restantes(HOJE) == 37
    assert fim.janela_ativa(HOJE) == 60
    assert fim.prioridade(HOJE) is Prioridade.MEDIA


def test_prazo_vencido_e_urgente():
    agenda = gerar_agenda(HOJE, mandatos=[
        MandatoParaPrazo("m1", "GESTÃO 2022–2024", "DIRETORIA", dt.date(2024, 12, 31))
    ])
    fim = agenda.prazos[0]
    assert fim.vencido(HOJE)
    assert fim.prioridade(HOJE) is Prioridade.URGENTE


def test_assembleia_ordinaria_so_e_calculada_com_parametro_confirmado():
    sem = gerar_agenda(HOJE, ultima_assembleia_ordinaria=dt.date(2025, 4, 10))
    assert not [p for p in sem.prazos if p.tipo is TipoPrazo.ASSEMBLEIA_ANUAL]
    assert sem.pendencias[0].codigo == "PERIODICIDADE_AGO_NAO_CONFIRMADA"

    com = gerar_agenda(
        HOJE, ultima_assembleia_ordinaria=dt.date(2025, 4, 10),
        periodicidade_ago=_confirmado("AGO_PERIODICIDADE_MESES", 12),
    )
    prazo = next(p for p in com.prazos if p.tipo is TipoPrazo.ASSEMBLEIA_ANUAL)
    assert prazo.data_limite == dt.date(2026, 4, 10)


def test_prestacao_de_contas_sem_prazo_estatutario_vira_pendencia_nao_data_inventada():
    agenda = gerar_agenda(HOJE, exercicios_pendentes=[2025])
    assert not [p for p in agenda.prazos if p.tipo is TipoPrazo.PRESTACAO_CONTAS]
    assert agenda.pendencias[0].codigo == "PRAZO_CONTAS_NAO_DEFINIDO::2025"
    assert agenda.pendencias[0].prioridade is Prioridade.ALTA


def test_prestacao_de_contas_com_prazo_estatutario():
    agenda = gerar_agenda(
        HOJE, exercicios_pendentes=[2025],
        prazo_aprovacao_contas=_confirmado("AGO_PRAZO_APROVACAO_CONTAS", "até 30 de abril"),
    )
    prazo = next(p for p in agenda.prazos if p.tipo is TipoPrazo.PRESTACAO_CONTAS)
    assert prazo.data_limite == dt.date(2026, 4, 30)


def test_certidoes_e_exigencias_entram_na_agenda():
    agenda = gerar_agenda(
        HOJE,
        certidoes=[CertidaoParaPrazo("c1", "CND Federal", dt.date(2026, 9, 1)),
                   CertidaoParaPrazo("c2", "CRF/FGTS", None)],
        exigencias=[ExigenciaParaPrazo("pr1", "Juntar termo de posse com firma reconhecida",
                                       dt.date(2026, 8, 26))],
    )
    tipos = {p.tipo for p in agenda.prazos}
    assert TipoPrazo.CERTIDAO in tipos and TipoPrazo.EXIGENCIA in tipos
    exigencia = next(p for p in agenda.prazos if p.tipo is TipoPrazo.EXIGENCIA)
    assert exigencia.prioridade(HOJE) is Prioridade.URGENTE
    assert any(p.codigo.startswith("CERTIDAO_SEM_VALIDADE") for p in agenda.pendencias)


def test_chave_de_idempotencia_evita_prazo_duplicado():
    a1 = gerar_agenda(HOJE, mandatos=[MandatoParaPrazo("m1", "G", "DIRETORIA", dt.date(2027, 1, 1))])
    a2 = gerar_agenda(HOJE, mandatos=[MandatoParaPrazo("m1", "G", "DIRETORIA", dt.date(2027, 1, 1))])
    assert [p.chave for p in a1.prazos] == [p.chave for p in a2.prazos]
