import datetime as dt

from app.core.enums import Prioridade, Semaforo
from app.engines.decisao.motor import PERGUNTAS, responder
from app.engines.inconsistencias.motor import RetratoCadastral, varrer


def test_pergunta_assembleia_pode_ser_realizada_com_prazo_curto(montar_contexto):
    ctx = montar_contexto(
        "ASSEMBLEIA_EXTRAORDINARIA", data_ato=dt.date(2026, 5, 20),
        dados={"data_edital": "2026-05-15", "convocado_por": "Presidente"},
    )
    r = responder(ctx, "assembleia_pode_ser_realizada")
    assert r.resultado is Semaforo.BLOQUEADO
    assert r.to_dict()["rotulo"] == "NÃO APTO"
    assert "prazo de convocação" in r.justificativa.lower()
    assert any("art. 60" in f for f in r.to_dict()["fundamentacao"])


def test_pergunta_quem_pode_convocar_le_o_estatuto(montar_contexto):
    ctx = montar_contexto("ASSEMBLEIA_ORDINARIA", data_ato=dt.date(2026, 5, 20))
    r = responder(ctx, "quem_pode_convocar")
    assert "Presidente" in r.justificativa
    assert "1/5 dos associados" in r.justificativa


def test_pergunta_documentos_necessarios_lista_o_checklist(montar_contexto):
    ctx = montar_contexto("ELEICAO_DIRETORIA", data_ato=dt.date(2026, 5, 20))
    r = responder(ctx, "documentos_necessarios")
    assert "Ata: Eleição de diretoria" in r.justificativa
    assert "Requerimento ao RCPJ" in r.justificativa


def test_todas_as_perguntas_respondem_sem_erro(montar_contexto):
    ctx = montar_contexto("ELEICAO_DIRETORIA", data_ato=dt.date(2026, 5, 20),
                          dados={"data_edital": "2026-05-01", "convocado_por": "Presidente",
                                 "total_presentes": 20, "eleitos": [{"nome": "A", "cargo": "Presidente"}]})
    for chave in PERGUNTAS:
        resposta = responder(ctx, chave)
        assert resposta.justificativa


def test_varredura_cadastral_prioriza_mandato_vencido():
    inconsistencias = varrer(
        RetratoCadastral(
            entidade_id="e1", razao_social="Associação X", cnpj=None,
            tem_estatuto_vigente=True, total_parametros=10, parametros_confirmados=6,
            mandato_vigente=False, mandato_designacao="GESTÃO 2022–2024",
            mandato_data_fim=dt.date(2024, 12, 31),
            certidoes_vencidas=["CND Federal"], protocolos_em_exigencia=1,
            rcpj_definido=True, impactos_normativos_abertos=2,
        ),
        hoje=dt.date(2026, 8, 24),
    )
    codigos = [i.codigo for i in inconsistencias]
    assert codigos[0] in ("MANDATO_VENCIDO", "PROTOCOLOS_EM_EXIGENCIA")
    assert "MANDATO_VENCIDO" in codigos
    mandato = next(i for i in inconsistencias if i.codigo == "MANDATO_VENCIDO")
    assert mandato.severidade is Semaforo.BLOQUEADO
    assert mandato.prioridade is Prioridade.URGENTE
    assert "IMPACTOS_NORMATIVOS" in codigos


def test_cadastro_saudavel_nao_gera_bloqueio():
    inconsistencias = varrer(
        RetratoCadastral(
            entidade_id="e1", razao_social="Associação X", cnpj="12.345.678/0001-90",
            rcpj_definido=True, tem_estatuto_vigente=True,
            total_parametros=12, parametros_confirmados=12,
            mandato_vigente=True, mandato_designacao="GESTÃO 2025–2027",
            mandato_data_fim=dt.date(2027, 6, 30),
            associados_ativos=40, associados_aptos=38,
        ),
        hoje=dt.date(2026, 8, 24),
    )
    assert not [i for i in inconsistencias if i.severidade is Semaforo.BLOQUEADO]
