"""O dispositivo de atualização da legislação (§4, §38, §46)."""
import datetime as dt

import pytest

from app.core.enums import AlvoImpacto, SeveridadeImpacto, SituacaoVersaoNorma
from app.engines.normativo.coletor import Coleta, impressao_digital
from app.engines.normativo.motor import (
    CuradoriaObrigatoria,
    MotorAtualizacaoNormativa,
    VersaoNorma,
    Vinculo,
)

TEXTO_V1 = ("Art. 60. A convocação dos órgãos deliberativos far-se-á na forma do estatuto, "
            "garantido a 1/5 (um quinto) dos associados o direito de promovê-la.")
TEXTO_V2 = ("Art. 60. A convocação dos órgãos deliberativos far-se-á na forma do estatuto, "
            "garantido a 1/10 (um décimo) dos associados o direito de promovê-la.")


@pytest.fixture
def motor():
    return MotorAtualizacaoNormativa()


def test_primeira_coleta_apenas_registra_linha_de_base(motor):
    d = motor.verificar(url="https://exemplo", hash_anterior=None,
                        coleta=Coleta(True, TEXTO_V1, impressao_digital(TEXTO_V1)))
    assert d.houve_mudanca is False
    assert d.hash_novo == impressao_digital(TEXTO_V1)


def test_conteudo_identico_nao_gera_atualizacao(motor):
    h = impressao_digital(TEXTO_V1)
    d = motor.verificar("https://exemplo", h, TEXTO_V1, Coleta(True, TEXTO_V1, h))
    assert d.houve_mudanca is False


def test_mudanca_de_texto_gera_deteccao_com_diff(motor):
    d = motor.verificar(
        "https://exemplo", impressao_digital(TEXTO_V1), TEXTO_V1,
        Coleta(True, TEXTO_V2, impressao_digital(TEXTO_V2)),
    )
    assert d.houve_mudanca is True
    assert "um quinto" in d.diff and "um décimo" in d.diff


def test_falha_de_coleta_nao_e_lida_como_sem_alteracao(motor):
    """Rede fora do ar não pode virar 'nada mudou' — vira conferência manual."""
    d = motor.verificar("https://exemplo", impressao_digital(TEXTO_V1), TEXTO_V1,
                        Coleta(False, erro="timeout"))
    assert d.houve_mudanca is False
    assert d.exige_conferencia_manual is True
    assert d.erro == "timeout"


def test_publicacao_exige_curador_humano(motor):
    with pytest.raises(CuradoriaObrigatoria):
        motor.publicar(versao_atual=None, texto_novo=TEXTO_V2,
                       vigente_desde=dt.date(2026, 1, 1), curado_por=None)


def test_publicacao_preserva_a_redacao_anterior_para_atos_passados(motor):
    v1 = VersaoNorma(1, SituacaoVersaoNorma.VIGENTE, dt.date(2003, 1, 11), texto=TEXTO_V1,
                     hash_conteudo=impressao_digital(TEXTO_V1),
                     curado_por="u1", curado_em=dt.datetime(2026, 1, 1))
    pub = motor.publicar(v1, TEXTO_V2, dt.date(2026, 6, 1), curado_por="advogada-oab-123456")

    assert pub.versao_nova.numero == 2
    assert pub.versao_nova.situacao is SituacaoVersaoNorma.VIGENTE
    assert pub.versao_anterior.situacao is SituacaoVersaoNorma.SUPERADA
    # A redação antiga continua citável até a véspera da nova.
    assert pub.versao_anterior.vigente_ate == dt.date(2026, 5, 31)


def test_impacto_alcanca_apenas_quem_declarou_o_vinculo(motor):
    vinculos = [
        Vinculo(AlvoImpacto.REGRA_VALIDACAO, "CONVOCACAO_LEGITIMIDADE", "CC_2002", "art. 60",
                SeveridadeImpacto.REVISAO_OBRIGATORIA),
        Vinculo(AlvoImpacto.TEMPLATE, "EDITAL_CONVOCACAO_PADRAO", "CC_2002", "art. 60"),
        Vinculo(AlvoImpacto.REGRA_VALIDACAO, "QUORUM_DELIBERACAO", "CC_2002", "art. 59"),
        Vinculo(AlvoImpacto.TEMPLATE, "REQUERIMENTO_RCPJ", "LRP_1973", "art. 121"),
    ]
    impactos = motor.calcular_impactos("CC_2002", ["art. 60"], vinculos)
    refs = {i.alvo_ref for i in impactos}
    assert refs == {"CONVOCACAO_LEGITIMIDADE", "EDITAL_CONVOCACAO_PADRAO"}
    assert next(i for i in impactos if i.alvo_ref == "CONVOCACAO_LEGITIMIDADE").severidade \
        is SeveridadeImpacto.REVISAO_OBRIGATORIA


def test_alteracao_sem_dispositivo_identificado_alcanca_toda_a_norma(motor):
    vinculos = [
        Vinculo(AlvoImpacto.REGRA_VALIDACAO, "CONVOCACAO_LEGITIMIDADE", "CC_2002", "art. 60"),
        Vinculo(AlvoImpacto.REGRA_VALIDACAO, "QUORUM_DELIBERACAO", "CC_2002", "art. 59"),
    ]
    impactos = motor.calcular_impactos("CC_2002", None, vinculos)
    assert len(impactos) == 2


def test_vigilancia_reporta_atraso():
    m = MotorAtualizacaoNormativa
    agora = dt.datetime(2026, 8, 24)
    assert m.situacao_da_vigilancia(None, 30, agora) == "NUNCA_VERIFICADA"
    assert m.situacao_da_vigilancia(dt.datetime(2026, 8, 10), 30, agora) == "EM_DIA"
    assert m.situacao_da_vigilancia(dt.datetime(2026, 7, 1), 30, agora) == "VENCIDA"
    assert m.situacao_da_vigilancia(dt.datetime(2026, 1, 1), 30, agora) == "ATRASADA"
