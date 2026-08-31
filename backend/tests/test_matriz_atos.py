"""A matriz de atos e o que ela responde (§10, §39)."""
import datetime as dt

import pytest

from app.core.enums import TipoEvento
from app.engines.conformidade.matriz import (
    MATRIZ,
    EspecieAssembleia,
    ExigeReforma,
    ato,
    documentos_do_ato,
)
from app.engines.decisao.motor import responder
from app.engines.validacao.motor import validar
from app.modules.juridico.questionarios import QUESTIONARIOS, questionario_de


def test_todo_ato_do_catalogo_esta_classificado():
    faltando = [t.value for t in TipoEvento if t.value not in MATRIZ]
    assert not faltando, f"atos sem classificação: {faltando}"


def test_todo_ato_tem_questionario_proprio():
    faltando = [t.value for t in TipoEvento if t.value not in QUESTIONARIOS]
    assert not faltando, f"atos sem questionário: {faltando}"


def test_mudanca_de_nome_e_sempre_reforma_estatutaria():
    """A denominação é conteúdo obrigatório do estatuto (CC, art. 54, I)."""
    a = ato(TipoEvento.ALTERACAO_DENOMINACAO.value)
    assert a.exige_reforma_estatutaria is ExigeReforma.SEMPRE
    assert a.exige_convocacao_especifica is True
    assert a.chave_quorum == "QUORUM_REFORMA_ESTATUTARIA"
    assert "art. 54" in a.nota


def test_eleicao_nao_presume_especie_de_assembleia():
    """O caso que motivou a matriz: a eleição pode ocorrer na assembleia
    ordinária, se o estatuto assim dispuser."""
    a = ato(TipoEvento.ELEICAO_DIRETORIA.value)
    assert a.especie_assembleia is EspecieAssembleia.CONFORME_ESTATUTO
    assert a.exige_reforma_estatutaria is ExigeReforma.NUNCA


def test_alteracao_de_endereco_depende_do_estatuto():
    a = ato(TipoEvento.ALTERACAO_ENDERECO.value)
    assert a.exige_reforma_estatutaria is ExigeReforma.DEPENDE_DO_ESTATUTO


def test_prestacao_de_contas_e_ordinaria_e_nao_vai_a_registro():
    a = ato(TipoEvento.PRESTACAO_CONTAS.value)
    assert a.especie_assembleia is EspecieAssembleia.ORDINARIA
    assert a.efeito_registral == "INTERNO"
    assert "AGO_PRAZO_APROVACAO_CONTAS" in a.parametros_relevantes


def test_atos_de_encerramento_exigem_destinacao_do_patrimonio():
    dissolucao = ato(TipoEvento.DISSOLUCAO.value)
    assert "DESTINACAO_PATRIMONIAL" in dissolucao.parametros_relevantes
    assert any(f == "CC_2002" and d == "art. 61" for f, d in dissolucao.fundamentos)


def test_documentos_saem_da_matriz_e_variam_por_ato():
    eleicao = set(documentos_do_ato(TipoEvento.ELEICAO_DIRETORIA.value))
    reforma = set(documentos_do_ato(TipoEvento.REFORMA_ESTATUTARIA.value))
    assert "TERMO_POSSE" in eleicao and "TERMO_POSSE" not in reforma
    assert "ESTATUTO_CONSOLIDADO" in reforma and "ESTATUTO_CONSOLIDADO" not in eleicao


def test_questionario_de_mudanca_de_nome_pergunta_o_que_e_proprio_dele():
    campos = {c.nome for c in questionario_de(TipoEvento.ALTERACAO_DENOMINACAO.value).campos}
    assert {"denominacao_anterior", "denominacao_nova", "redacao_aprovada"} <= campos
    # E também o esqueleto de toda alteração estatutária.
    assert {"artigos_alterados", "votos_favor", "ordem_do_dia"} <= campos


def test_questionario_de_prestacao_de_contas_cobre_o_exercicio():
    campos = {c.nome for c in questionario_de(TipoEvento.PRESTACAO_CONTAS.value).campos}
    assert {"exercicio", "parecer_conselho_fiscal", "recursos_publicos"} <= campos


@pytest.mark.parametrize("tipo", [t.value for t in TipoEvento])
def test_nenhum_questionario_pergunta_o_que_ja_esta_no_cadastro(tipo):
    """§53 — uma vez cadastrada, a informação não é digitada de novo."""
    proibidos = {"razao_social", "cnpj", "endereco_sede", "natureza_juridica"}
    campos = {c.nome for c in questionario_de(tipo).campos}
    assert not (campos & proibidos), f"{tipo} repergunta dados do cadastro"


# ------------------------------------------------------- Motor de decisão


def test_decisao_responde_se_a_mudanca_de_nome_exige_reforma(montar_contexto):
    ctx = montar_contexto(
        "ALTERACAO_DENOMINACAO", data_ato=dt.date(2026, 5, 20),
        dados={"data_edital": "2026-05-01", "convocado_por": "Presidente",
               "ordem_do_dia": ["Alteração da denominação social"], "total_presentes": 25},
    )
    r = responder(ctx, "exige_reforma_estatutaria")
    assert r.justificativa.startswith("Sim.")
    assert "art. 54" in r.justificativa


def test_decisao_nao_arbitra_a_especie_da_assembleia_na_eleicao(montar_contexto):
    ctx = montar_contexto("ELEICAO_DIRETORIA", data_ato=dt.date(2026, 5, 20))
    r = responder(ctx, "especie_de_assembleia")
    assert "Depende do estatuto" in r.justificativa


def test_decisao_avisa_da_convocacao_especifica_na_destituicao(montar_contexto):
    ctx = montar_contexto("DESTITUICAO", data_ato=dt.date(2026, 5, 20))
    r = responder(ctx, "especie_de_assembleia")
    assert "Extraordinária" in r.justificativa
    assert "especialmente convocada" in r.justificativa


def test_endereco_no_estatuto_muda_o_regime_do_ato(montar_contexto):
    """Mesma mudança de endereço, dois regimes — conforme o estatuto."""
    comuns = {"data_edital": "2026-05-01", "convocado_por": "Presidente",
              "endereco_novo": "Rua Nova, 500, Centro, Belo Horizonte/MG"}

    sem_previsao = montar_contexto("ALTERACAO_ENDERECO", data_ato=dt.date(2026, 5, 20),
                                   dados={**comuns, "consta_do_estatuto": False})
    codigos = {a.codigo for a in validar(sem_previsao).achados}
    assert "ALTERACAO_ENDERECO_EXIGE_REFORMA" not in codigos

    com_previsao = montar_contexto("ALTERACAO_ENDERECO", data_ato=dt.date(2026, 5, 20),
                                   dados={**comuns, "consta_do_estatuto": True})
    achado = next(
        a for a in validar(com_previsao).achados
        if a.codigo == "ALTERACAO_ENDERECO_EXIGE_REFORMA"
    )
    assert "2/3 dos presentes" in achado.mensagem


def test_mudanca_de_municipio_alerta_sobre_o_cartorio(montar_contexto):
    ctx = montar_contexto(
        "ALTERACAO_ENDERECO", data_ato=dt.date(2026, 5, 20),
        dados={"data_edital": "2026-05-01", "convocado_por": "Presidente",
               "consta_do_estatuto": False,
               "endereco_novo": "Av. Central, 10, Contagem/MG"},
    )
    achado = next(a for a in validar(ctx).achados if a.codigo == "MUDANCA_DE_MUNICIPIO")
    assert "RCPJ competente" in achado.mensagem
