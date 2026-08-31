"""Modelos padrão do TERCEIRO360 (§14, §15, §16).

Os modelos usam variáveis `{{ }}` e regras condicionais `{% if %}`. Variável sem
valor vira **DADO NÃO INFORMADO** e a lacuna fica registrada na versão do
documento — o texto nunca sai com um dado inventado no lugar (§46).

Estes são pontos de partida profissionais, não peças prontas para protocolo:
cada RCPJ tem suas exigências de forma, e a revisão jurídica continua sendo do
profissional habilitado (§47).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateSeed:
    codigo: str
    nome: str
    tipo_documento: str
    corpo: str
    tipos_entidade: tuple[str, ...] = ()
    tipos_evento: tuple[str, ...] = ()
    fundamentos: tuple[str, ...] = field(default_factory=tuple)


CABECALHO = """{{ RAZAO_SOCIAL | maiusculas }}
CNPJ nº {{ CNPJ }}
{{ ENDERECO }}
"""

EDITAL = CABECALHO + """
EDITAL DE CONVOCAÇÃO
ASSEMBLEIA GERAL {{ TIPO_ASSEMBLEIA | maiusculas }}

{% if TIPO_ENTIDADE == 'ORGANIZACAO_RELIGIOSA' or TIPO_ENTIDADE == 'IGREJA' %}
O {{ CONVOCADO_POR }}, no uso das atribuições que lhe confere o Estatuto,
convoca os membros em pleno gozo de seus direitos estatutários para a
Assembleia Geral {{ TIPO_ASSEMBLEIA }}, a realizar-se em
{{ DATA_ATO | data_extenso }}, às {{ HORA }}, em {{ LOCAL }}.
{% else %}
O {{ CONVOCADO_POR }}, no uso das atribuições que lhe confere o Estatuto Social,
convoca os associados em pleno gozo de seus direitos estatutários para a
Assembleia Geral {{ TIPO_ASSEMBLEIA }}, a realizar-se em
{{ DATA_ATO | data_extenso }}, às {{ HORA }}, em {{ LOCAL }}.
{% endif %}

ORDEM DO DIA
{% for item in ORDEM_DO_DIA %}
{{ loop.index }}. {{ item }};
{% endfor %}

{% if QUORUM_INSTALACAO_PRIMEIRA %}
A Assembleia instalar-se-á em primeira convocação com {{ QUORUM_INSTALACAO_PRIMEIRA }}.
{% endif %}
{% if QUORUM_INSTALACAO_SEGUNDA %}
Não havendo quórum em primeira convocação, a Assembleia instalar-se-á em segunda
convocação, trinta minutos após, com {{ QUORUM_INSTALACAO_SEGUNDA }}.
{% endif %}

{{ MUNICIPIO }}, {{ DATA_EDITAL | data_extenso }}.


_______________________________________________
{{ CONVOCADO_POR }}
"""

ATA_ELEICAO = CABECALHO + """
ATA DA ASSEMBLEIA GERAL {{ TIPO_ASSEMBLEIA | maiusculas }}
REALIZADA EM {{ DATA_ATO | data_extenso | maiusculas }}

Aos {{ DATA_ATO | data_extenso }}, às {{ HORA }}, em {{ LOCAL }}, reuniram-se em
Assembleia Geral {{ TIPO_ASSEMBLEIA }} os associados da {{ RAZAO_SOCIAL }},
inscrita no CNPJ sob o nº {{ CNPJ }}, convocados por meio de
{{ MEIO_CONVOCACAO }} publicado em {{ DATA_EDITAL | data_extenso }}, na forma do
Estatuto Social.

Verificado o quórum estatutário, com a presença de {{ TOTAL_PRESENTES }}
({{ TOTAL_PRESENTES | extenso }}) participantes habilitados, conforme lista de
presença que integra esta ata, a Assembleia foi instalada em
{{ CONVOCACAO }} convocação.

Assumiu a presidência dos trabalhos {{ PRESIDENTE_MESA }}, que convidou
{{ SECRETARIO_MESA }} para secretariar a sessão.

ORDEM DO DIA
{% for item in ORDEM_DO_DIA %}
{{ loop.index }}. {{ item }};
{% endfor %}

DELIBERAÇÕES

Posta em votação a eleição da nova Diretoria, foram eleitos, por
{% if VOTOS_FAVOR %}{{ VOTOS_FAVOR }} ({{ VOTOS_FAVOR | extenso }}) votos favoráveis{% else %}deliberação da Assembleia{% endif %},
para o mandato de {{ MANDATO_INICIO | data }} a {{ MANDATO_FIM | data }},
os seguintes membros:

{% for eleito in ELEITOS %}
{{ loop.index }}. {{ eleito.cargo }}: {{ eleito.nome }}{% if eleito.cpf %}, CPF nº {{ eleito.cpf }}{% endif %};
{% endfor %}

{% if CONSELHO_FISCAL_ELEITO %}
Foi igualmente eleito o Conselho Fiscal para o mesmo período.
{% endif %}

Os eleitos, presentes ao ato, declararam aceitar os cargos para os quais foram
eleitos, tomando posse na forma do Estatuto Social.

{% if OBSERVACOES %}
OBSERVAÇÕES: {{ OBSERVACOES }}
{% endif %}

Nada mais havendo a tratar, foi encerrada a sessão e lavrada a presente ata,
que, lida e achada conforme, vai assinada pelo Presidente e pelo Secretário
da mesa.

{{ MUNICIPIO }}, {{ DATA_ATO | data_extenso }}.


_______________________________________________
{{ PRESIDENTE_MESA }} — Presidente da mesa


_______________________________________________
{{ SECRETARIO_MESA }} — Secretário da mesa
"""

ATA_GENERICA = CABECALHO + """
ATA DA ASSEMBLEIA GERAL {{ TIPO_ASSEMBLEIA | maiusculas }}
REALIZADA EM {{ DATA_ATO | data_extenso | maiusculas }}

Aos {{ DATA_ATO | data_extenso }}, às {{ HORA }}, em {{ LOCAL }}, reuniram-se em
Assembleia Geral {{ TIPO_ASSEMBLEIA }} os membros da {{ RAZAO_SOCIAL }},
inscrita no CNPJ sob o nº {{ CNPJ }}, convocados por {{ MEIO_CONVOCACAO }} em
{{ DATA_EDITAL | data_extenso }}.

Presentes {{ TOTAL_PRESENTES }} participantes habilitados, instalada a Assembleia
em {{ CONVOCACAO }} convocação, assumiu a presidência {{ PRESIDENTE_MESA }},
secretariado por {{ SECRETARIO_MESA }}.

ORDEM DO DIA
{% for item in ORDEM_DO_DIA %}
{{ loop.index }}. {{ item }};
{% endfor %}

DELIBERAÇÕES
{% if VOTOS_FAVOR %}
As matérias da ordem do dia foram aprovadas por {{ VOTOS_FAVOR }} votos
favoráveis{% if VOTOS_CONTRA %}, {{ VOTOS_CONTRA }} contrários{% endif %}{% if ABSTENCOES %} e {{ ABSTENCOES }} abstenções{% endif %}.
{% else %}
{{ DELIBERACOES }}
{% endif %}

{% if OBSERVACOES %}
OBSERVAÇÕES: {{ OBSERVACOES }}
{% endif %}

Nada mais havendo a tratar, foi lavrada a presente ata.

{{ MUNICIPIO }}, {{ DATA_ATO | data_extenso }}.


_______________________________________________
{{ PRESIDENTE_MESA }} — Presidente da mesa


_______________________________________________
{{ SECRETARIO_MESA }} — Secretário da mesa
"""

ATA_REFORMA = CABECALHO + """
ATA DA ASSEMBLEIA GERAL EXTRAORDINÁRIA DE REFORMA ESTATUTÁRIA
REALIZADA EM {{ DATA_ATO | data_extenso | maiusculas }}

Aos {{ DATA_ATO | data_extenso }}, às {{ HORA }}, em {{ LOCAL }}, reuniram-se em
Assembleia Geral Extraordinária, especialmente convocada para deliberar sobre a
reforma do Estatuto Social, os associados da {{ RAZAO_SOCIAL }}, CNPJ nº
{{ CNPJ }}, convocados por {{ MEIO_CONVOCACAO }} em
{{ DATA_EDITAL | data_extenso }}.

Presentes {{ TOTAL_PRESENTES }} participantes habilitados, a Assembleia foi
instalada em {{ CONVOCACAO }} convocação, sob a presidência de
{{ PRESIDENTE_MESA }}, secretariada por {{ SECRETARIO_MESA }}.

ORDEM DO DIA
{% for item in ORDEM_DO_DIA %}
{{ loop.index }}. {{ item }};
{% endfor %}

DELIBERAÇÃO

Submetida a matéria à votação, a reforma estatutária foi aprovada por
{{ VOTOS_FAVOR }} ({{ VOTOS_FAVOR | extenso }}) votos favoráveis{% if VOTOS_CONTRA %}, {{ VOTOS_CONTRA }} contrários{% endif %}{% if ABSTENCOES %} e {{ ABSTENCOES }} abstenções{% endif %},
atingido o quórum estatutário de {{ QUORUM_REFORMA_ESTATUTARIA }}.

DISPOSITIVOS ALTERADOS
{% for artigo in ARTIGOS_ALTERADOS %}
- {{ artigo }};
{% endfor %}

REDAÇÃO ANTERIOR
{{ REDACAO_ANTERIOR }}

REDAÇÃO APROVADA
{{ REDACAO_APROVADA }}

{% if CONSOLIDACAO %}
A Assembleia aprovou, ainda, a consolidação do Estatuto Social em texto único,
que passa a vigorar com a redação ora aprovada, ficando a Diretoria autorizada a
promover o respectivo registro.
{% endif %}

Nada mais havendo a tratar, foi lavrada a presente ata.

{{ MUNICIPIO }}, {{ DATA_ATO | data_extenso }}.


_______________________________________________
{{ PRESIDENTE_MESA }} — Presidente da mesa


_______________________________________________
{{ SECRETARIO_MESA }} — Secretário da mesa
"""

LISTA_PRESENCA = CABECALHO + """
LISTA DE PRESENÇA
ASSEMBLEIA GERAL {{ TIPO_ASSEMBLEIA | maiusculas }} DE {{ DATA_ATO | data }}

Local: {{ LOCAL }}
Convocação: {{ CONVOCACAO }}
Total de participantes habilitados: {{ TOTAL_APTOS }}

Nº  | NOME COMPLETO                     | CPF              | ASSINATURA
----|-----------------------------------|------------------|---------------------
 1  |                                   |                  |
 2  |                                   |                  |
 3  |                                   |                  |
 4  |                                   |                  |
 5  |                                   |                  |
 6  |                                   |                  |
 7  |                                   |                  |
 8  |                                   |                  |
 9  |                                   |                  |
10  |                                   |                  |

Encerrada a lista com {{ TOTAL_PRESENTES }} presentes.

{{ MUNICIPIO }}, {{ DATA_ATO | data_extenso }}.


_______________________________________________
{{ SECRETARIO_MESA }} — Secretário da mesa
"""

TERMO_POSSE = CABECALHO + """
TERMO DE POSSE

Aos {{ DATA_POSSE | data_extenso }}, na sede da {{ RAZAO_SOCIAL }}, inscrita no
CNPJ sob o nº {{ CNPJ }}, tomam posse nos cargos para os quais foram eleitos na
Assembleia Geral realizada em {{ DATA_ATO | data_extenso }}, para o mandato de
{{ MANDATO_INICIO | data }} a {{ MANDATO_FIM | data }}, os seguintes membros:

{% for eleito in ELEITOS %}
{{ loop.index }}. {{ eleito.cargo | maiusculas }}
    Nome: {{ eleito.nome }}
    CPF: {{ eleito.cpf }}

    Assinatura: ______________________________________

{% endfor %}

Os empossados declaram conhecer e aceitar as atribuições dos respectivos cargos,
comprometendo-se a exercê-los na forma do Estatuto Social e da legislação
aplicável, e declaram não estar impedidos por lei de exercer a administração da
entidade.

{{ MUNICIPIO }}, {{ DATA_POSSE | data_extenso }}.


_______________________________________________
{{ PRESIDENTE_MESA }} — Presidente da mesa da Assembleia
"""

RELACAO_DIRETORIA = CABECALHO + """
RELAÇÃO DA DIRETORIA ELEITA
Mandato: {{ MANDATO_INICIO | data }} a {{ MANDATO_FIM | data }}

{% for eleito in ELEITOS %}
{{ loop.index }}. {{ eleito.cargo | maiusculas }}
    Nome: {{ eleito.nome }}
    CPF: {{ eleito.cpf }}
    RG: {{ eleito.rg }}
    Endereço: {{ eleito.endereco }}

{% endfor %}

Eleitos na Assembleia Geral realizada em {{ DATA_ATO | data_extenso }}.

{{ MUNICIPIO }}, {{ DATA_HOJE | data_extenso }}.


_______________________________________________
{{ PRESIDENTE }} — Presidente
"""

REQUERIMENTO = """Ao
{{ RCPJ }}
{{ MUNICIPIO }}/{{ UF }}

REQUERIMENTO DE REGISTRO

{{ RAZAO_SOCIAL | maiusculas }}, pessoa jurídica de direito privado sem fins
lucrativos, inscrita no CNPJ sob o nº {{ CNPJ }}, com sede em {{ ENDERECO }},
{% if ESTATUTO_REGISTRO %}
com atos constitutivos registrados sob o nº {{ ESTATUTO_REGISTRO }},
{% if ESTATUTO_LIVRO %}Livro {{ ESTATUTO_LIVRO }}, {% endif %}{% if ESTATUTO_FOLHA %}Folha {{ ESTATUTO_FOLHA }}, {% endif %}
{% endif %}
neste ato representada por seu {{ CARGO_REPRESENTANTE }}, {{ PRESIDENTE }},
vem, respeitosamente, REQUERER o registro/averbação dos atos referentes a:

{{ TIPO_ATO }}

realizado em {{ DATA_ATO | data_extenso }}, para o que apresenta os documentos
relacionados em anexo.

Nestes termos, pede deferimento.

{{ MUNICIPIO }}, {{ DATA_HOJE | data_extenso }}.


_______________________________________________
{{ PRESIDENTE }}
{{ CARGO_REPRESENTANTE }}
"""

TERMO_RENUNCIA = CABECALHO + """
TERMO DE RENÚNCIA

Eu, {{ PESSOA }}, ocupante do cargo de {{ CARGO }} da {{ RAZAO_SOCIAL }},
inscrita no CNPJ sob o nº {{ CNPJ }}, venho, pelo presente termo, apresentar
minha RENÚNCIA ao referido cargo, com efeitos a partir de
{{ DATA_ATO | data_extenso }}.

{% if MOTIVO %}
Motivo declarado: {{ MOTIVO }}
{% endif %}

Declaro estar ciente de que a renúncia produz efeitos perante a entidade desde a
data em que dela tomar conhecimento o órgão competente, e perante terceiros
após o respectivo registro.

{{ MUNICIPIO }}, {{ DATA_ATO | data_extenso }}.


_______________________________________________
{{ PESSOA }}
{{ CARGO }}
"""

QUADRO_COMPARATIVO = CABECALHO + """
QUADRO COMPARATIVO — REFORMA ESTATUTÁRIA
Assembleia Geral Extraordinária de {{ DATA_ATO | data_extenso }}

DISPOSITIVOS ALTERADOS
{% for artigo in ARTIGOS_ALTERADOS %}
- {{ artigo }};
{% endfor %}

┌─────────────────────────────────┬─────────────────────────────────┐
│ REDAÇÃO ANTERIOR                │ REDAÇÃO APROVADA                │
└─────────────────────────────────┴─────────────────────────────────┘

REDAÇÃO ANTERIOR
{{ REDACAO_ANTERIOR }}

REDAÇÃO APROVADA
{{ REDACAO_APROVADA }}

Aprovado por {{ VOTOS_FAVOR }} votos favoráveis, atingido o quórum estatutário
de {{ QUORUM_REFORMA_ESTATUTARIA }}.

{{ MUNICIPIO }}, {{ DATA_HOJE | data_extenso }}.


_______________________________________________
{{ PRESIDENTE }} — Presidente
"""

ATA_ALTERACAO_ENDERECO = CABECALHO + """
ATA DE DELIBERAÇÃO — ALTERAÇÃO DE ENDEREÇO
{{ DATA_ATO | data_extenso | maiusculas }}

Aos {{ DATA_ATO | data_extenso }}, reuniu-se o {{ ORGAO_DELIBERANTE }} da
{{ RAZAO_SOCIAL }}, CNPJ nº {{ CNPJ }}, para deliberar sobre a alteração do
endereço da sede.

DELIBERAÇÃO

Foi aprovada a transferência da sede para o endereço:

{{ ENDERECO_NOVO }}

{% if CONSTA_DO_ESTATUTO %}
Considerando que o endereço da sede consta expressamente do Estatuto Social, a
presente alteração implica reforma estatutária, observados o quórum e o
procedimento previstos no Estatuto.
{% else %}
Considerando que o Estatuto Social não fixa o endereço completo da sede, a
alteração é levada a registro por averbação.
{% endif %}

Nada mais havendo a tratar, foi lavrada a presente ata.

{{ MUNICIPIO }}, {{ DATA_ATO | data_extenso }}.


_______________________________________________
{{ PRESIDENTE }} — Presidente
"""


TEMPLATES: tuple[TemplateSeed, ...] = (
    TemplateSeed("EDITAL_PADRAO", "Edital de convocação", "EDITAL_CONVOCACAO", EDITAL,
                 fundamentos=("CC_2002:art. 60",)),
    TemplateSeed("ATA_ELEICAO_PADRAO", "Ata de assembleia de eleição de diretoria", "ATA",
                 ATA_ELEICAO, tipos_evento=("ELEICAO_DIRETORIA", "REELEICAO_DIRETORIA"),
                 fundamentos=("CC_2002:art. 59",)),
    TemplateSeed("ATA_REFORMA_PADRAO", "Ata de reforma estatutária", "ATA", ATA_REFORMA,
                 tipos_evento=("REFORMA_ESTATUTARIA", "ALTERACAO_FINALIDADE",
                               "ALTERACAO_DENOMINACAO", "ALTERACAO_ORGAOS",
                               "ALTERACAO_MANDATO", "ALTERACAO_QUORUM"),
                 fundamentos=("CC_2002:art. 59",)),
    TemplateSeed("ATA_ENDERECO_PADRAO", "Ata de alteração de endereço", "ATA",
                 ATA_ALTERACAO_ENDERECO, tipos_evento=("ALTERACAO_ENDERECO",),
                 fundamentos=("CC_2002:art. 45",)),
    TemplateSeed("ATA_PADRAO", "Ata de assembleia geral", "ATA", ATA_GENERICA),
    TemplateSeed("LISTA_PRESENCA_PADRAO", "Lista de presença", "LISTA_PRESENCA", LISTA_PRESENCA),
    TemplateSeed("TERMO_POSSE_PADRAO", "Termo de posse", "TERMO_POSSE", TERMO_POSSE,
                 tipos_evento=("ELEICAO_DIRETORIA", "REELEICAO_DIRETORIA", "POSSE_DIRETORIA",
                               "CONSTITUICAO")),
    TemplateSeed("RELACAO_DIRETORIA_PADRAO", "Relação da diretoria", "RELACAO_DIRETORIA",
                 RELACAO_DIRETORIA,
                 tipos_evento=("ELEICAO_DIRETORIA", "REELEICAO_DIRETORIA", "POSSE_DIRETORIA")),
    TemplateSeed("REQUERIMENTO_PADRAO", "Requerimento ao RCPJ", "REQUERIMENTO_RCPJ", REQUERIMENTO,
                 fundamentos=("LRP_1973:art. 120", "LRP_1973:art. 121")),
    TemplateSeed("TERMO_RENUNCIA_PADRAO", "Termo de renúncia", "TERMO_RENUNCIA", TERMO_RENUNCIA,
                 tipos_evento=("RENUNCIA",)),
    TemplateSeed("QUADRO_COMPARATIVO_PADRAO", "Quadro comparativo de reforma estatutária",
                 "QUADRO_COMPARATIVO", QUADRO_COMPARATIVO,
                 tipos_evento=("REFORMA_ESTATUTARIA",)),
)
