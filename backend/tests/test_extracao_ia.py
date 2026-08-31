"""A IA propõe; o responsável confirma (§37, §46)."""
from app.modules.ia.extracao import extrair_parametros

ESTATUTO = """
ESTATUTO SOCIAL DA ASSOCIAÇÃO COMUNITÁRIA NOVO HORIZONTE

Art. 18 - O mandato da Diretoria será de dois (2) anos, permitida a reeleição
por igual período.

Art. 21 - A Assembleia Geral será convocada pelo Presidente, pela Diretoria ou
por um quinto dos associados, mediante edital afixado na sede com antecedência
mínima de quinze (15) dias.

Art. 22 - A Assembleia Geral instalar-se-á, em primeira convocação, com a
presença da metade mais um dos associados e, em segunda convocação, meia hora
depois, com qualquer número de presentes.

Art. 25 - A entidade terá um Conselho Fiscal composto por três membros efetivos.

Art. 26 - Compete ao Conselho Fiscal emitir parecer sobre as contas anuais,
que será submetido à Assembleia Geral juntamente com o balanço do exercício.

Art. 30 - O presente Estatuto poderá ser reformado por deliberação de dois terços
dos presentes em Assembleia Geral especialmente convocada para esse fim.

Art. 31 - A destituição de membros da Diretoria dependerá do voto de dois terços
dos presentes.

Art. 40 - Em caso de dissolução, o patrimônio remanescente será destinado a
entidade congênere sem fins lucrativos designada pela Assembleia Geral.
"""


def _por_chave(resultado):
    return {s.chave: s for s in resultado.sugestoes}


def test_extrai_duracao_do_mandato_em_meses():
    s = _por_chave(extrair_parametros(ESTATUTO))
    assert s["MANDATO_DURACAO_MESES"].valor == 24
    assert s["MANDATO_DURACAO_MESES"].dispositivo == "art. 18"


def test_extrai_prazo_de_convocacao():
    s = _por_chave(extrair_parametros(ESTATUTO))
    assert s["CONVOCACAO_PRAZO_DIAS"].valor == 15
    assert "quinze" in s["CONVOCACAO_PRAZO_DIAS"].trecho


def test_extrai_quoruns_de_instalacao():
    s = _por_chave(extrair_parametros(ESTATUTO))
    assert "metade mais um" in s["QUORUM_INSTALACAO_PRIMEIRA"].valor.lower()
    assert "qualquer" in s["QUORUM_INSTALACAO_SEGUNDA"].valor.lower()


def test_extrai_quorum_de_reforma_e_destituicao():
    s = _por_chave(extrair_parametros(ESTATUTO))
    assert "dois ter" in s["QUORUM_REFORMA_ESTATUTARIA"].valor.lower()
    assert "dois ter" in s["QUORUM_DESTITUICAO"].valor.lower()


def test_identifica_conselho_fiscal_e_parecer():
    s = _por_chave(extrair_parametros(ESTATUTO))
    assert s["CONSELHO_FISCAL_EXISTE"].valor is True
    assert s["CONSELHO_FISCAL_PARECER_OBRIGATORIO"].valor is True


def test_reporta_o_que_nao_conseguiu_localizar():
    """O que a IA não acha não é chutado: é listado como não localizado."""
    r = extrair_parametros(ESTATUTO)
    assert "ASSOCIADO_CARENCIA_VOTO_MESES" in r.nao_localizados
    assert r.metodo == "leitura-deterministica"


def test_sugestoes_de_baixa_confianca_pedem_validacao():
    r = extrair_parametros(ESTATUTO)
    baixa = [s for s in r.sugestoes if s.confianca < 0.7]
    assert baixa, "esperava ao menos uma sugestão marcada para validação"
    assert all(s.pergunta_validacao for s in baixa)


def test_texto_sem_regras_nao_inventa_nada():
    r = extrair_parametros("Este documento não contém regras estatutárias.")
    assert r.sugestoes == []
    assert len(r.nao_localizados) == 26
