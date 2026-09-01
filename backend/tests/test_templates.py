from app.engines.templates.motor import (
    MARCADOR_LACUNA,
    data_extenso,
    por_extenso,
    renderizar,
    validar_template,
    variaveis_do_template,
)

CORPO = """EDITAL DE CONVOCAÇÃO

{{ RAZAO_SOCIAL | maiusculas }}, inscrita no CNPJ sob o nº {{ CNPJ }}, com sede em
{{ MUNICIPIO }}/{{ UF }}, convoca seus associados para a Assembleia Geral
{{ TIPO_ASSEMBLEIA }} a realizar-se em {{ DATA_ASSEMBLEIA | data_extenso }}.

Ordem do dia:
{% for item in ORDEM_DO_DIA %}
{{ loop.index }}. {{ item }}
{% endfor %}
{% if CONSELHO_FISCAL %}
Haverá também eleição do Conselho Fiscal.
{% endif %}

{{ MUNICIPIO }}, {{ DATA_EDITAL | data_extenso }}.

{{ PRESIDENTE }}
Presidente
"""


def test_variaveis_detectadas():
    assert "RAZAO_SOCIAL" in variaveis_do_template(CORPO)
    assert "ORDEM_DO_DIA" in variaveis_do_template(CORPO)


def test_render_completo():
    r = renderizar(CORPO, {
        "RAZAO_SOCIAL": "Associação Novo Horizonte", "CNPJ": "12.345.678/0001-90",
        "MUNICIPIO": "Belo Horizonte", "UF": "MG", "TIPO_ASSEMBLEIA": "Ordinária",
        "DATA_ASSEMBLEIA": "2026-04-10", "DATA_EDITAL": "2026-03-20",
        "ORDEM_DO_DIA": ["Prestação de contas", "Eleição da diretoria"],
        "CONSELHO_FISCAL": True, "PRESIDENTE": "Maria Aparecida Souza",
    })
    assert r.completo
    assert "ASSOCIAÇÃO NOVO HORIZONTE" in r.texto
    assert "10 de abril de 2026" in r.texto
    assert "1. Prestação de contas" in r.texto
    assert "Conselho Fiscal" in r.texto


def test_variavel_ausente_vira_dado_nao_informado_e_e_registrada():
    r = renderizar(CORPO, {
        "RAZAO_SOCIAL": "Associação Novo Horizonte", "MUNICIPIO": "Belo Horizonte", "UF": "MG",
        "TIPO_ASSEMBLEIA": "Ordinária", "DATA_ASSEMBLEIA": "2026-04-10",
        "DATA_EDITAL": "2026-03-20", "ORDEM_DO_DIA": ["Eleição"],
        "CONSELHO_FISCAL": False, "PRESIDENTE": "Maria Aparecida Souza",
    })
    assert MARCADOR_LACUNA in r.texto
    assert "CNPJ" in r.lacunas
    assert not r.completo
    assert "Conselho Fiscal" not in r.texto


def test_condicional_por_tipo_de_entidade():
    corpo = ("{% if TIPO_ENTIDADE == 'ORGANIZACAO_RELIGIOSA' %}"
             "O Pastor Presidente declarou aberta a sessão."
             "{% else %}O Presidente declarou aberta a sessão.{% endif %}")
    assert "Pastor Presidente" in renderizar(corpo, {"TIPO_ENTIDADE": "ORGANIZACAO_RELIGIOSA"}).texto
    assert "Pastor" not in renderizar(corpo, {"TIPO_ENTIDADE": "ASSOCIACAO"}).texto


def test_numero_por_extenso():
    assert por_extenso(15) == "quinze"
    assert por_extenso(30) == "trinta"
    assert por_extenso(42) == "quarenta e dois"
    assert por_extenso(2026) == "dois mil e vinte e seis"
    assert data_extenso("2026-08-24") == "24 de agosto de 2026"


def test_template_com_sintaxe_invalida_nao_passa():
    ok, erro = validar_template("{% if X %} sem fim")
    assert ok is False and erro


def test_requerimento_nao_leva_codigo_de_enum_ao_cartorio():
    """O tipo do ato sai por extenso na peça, não como "ALTERACAO_DENOMINACAO"."""
    from app.core.enums import TipoEvento
    from app.modules.documentos.servicos import _titulo_do_ato

    assert _titulo_do_ato(TipoEvento.ALTERACAO_DENOMINACAO) == "Alteração de denominação"
    assert _titulo_do_ato(TipoEvento.ELEICAO_DIRETORIA) == "Eleição de diretoria"
    # Tipo fora da matriz não quebra a geração: cai numa forma legível.
    assert _titulo_do_ato("ATO_QUE_NAO_EXISTE") == "Ato que nao existe"
