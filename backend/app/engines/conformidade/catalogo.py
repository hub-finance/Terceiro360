"""Catálogo de parâmetros estatutários (§7, §52).

Cada chave define: o que é, como se pergunta ao usuário em linguagem simples,
qual o tipo do valor e — quando existe — qual dispositivo legal trata do tema.

Atenção à REGRA CRÍTICA (§4): a existência de um dispositivo legal sobre o tema
NÃO significa que o sistema possa preencher o valor sozinho. Na maior parte dos
casos a lei devolve a definição ao estatuto (é o caso do quórum, após a
Lei nº 11.127/2005). Por isso `valor_supletivo` é quase sempre None.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DefinicaoParametro:
    chave: str
    rotulo: str
    pergunta_simples: str          # §52 — linguagem do usuário, não do jurista
    tipo: str                      # inteiro|decimal|texto|booleano|fracao|lista
    unidade: str | None = None
    grupo: str = "GERAL"
    obrigatorio_para: tuple[str, ...] = ()
    fonte_legal: str | None = None      # chave da fonte na Central de Fontes
    dispositivo_legal: str | None = None
    # Valor que a lei impõe independentemente do estatuto. Quase sempre None:
    # a lei brasileira devolve estes temas à autonomia estatutária.
    valor_supletivo: object | None = None
    nota: str | None = None
    exemplos: tuple[str, ...] = field(default_factory=tuple)


CATALOGO: dict[str, DefinicaoParametro] = {}


def _reg(d: DefinicaoParametro) -> DefinicaoParametro:
    CATALOGO[d.chave] = d
    return d


# ------------------------------------------------------------------ Mandato
_reg(DefinicaoParametro(
    chave="MANDATO_DURACAO_MESES",
    rotulo="Duração do mandato",
    pergunta_simples="Por quanto tempo a diretoria fica no cargo depois de eleita?",
    tipo="inteiro", unidade="meses", grupo="MANDATO",
    obrigatorio_para=("ELEICAO_DIRETORIA", "REELEICAO_DIRETORIA", "POSSE_DIRETORIA"),
    nota="A lei não fixa duração de mandato para associações: quem define é o estatuto.",
    exemplos=("24 (2 anos)", "36 (3 anos)", "48 (4 anos)"),
))
_reg(DefinicaoParametro(
    chave="MANDATO_PERMITE_REELEICAO",
    rotulo="Reeleição permitida",
    pergunta_simples="A diretoria pode ser reeleita para um novo mandato?",
    tipo="booleano", grupo="MANDATO",
))
_reg(DefinicaoParametro(
    chave="MANDATO_LIMITE_REELEICOES",
    rotulo="Limite de reeleições",
    pergunta_simples="Quantas vezes seguidas a mesma pessoa pode ser reeleita?",
    tipo="inteiro", unidade="vezes", grupo="MANDATO",
))
_reg(DefinicaoParametro(
    chave="MANDATO_ORGAO_ELEITOR",
    rotulo="Órgão que elege",
    pergunta_simples="Quem elege a diretoria?",
    tipo="texto", grupo="MANDATO",
    exemplos=("Assembleia Geral", "Conselho Deliberativo", "Convenção"),
))
_reg(DefinicaoParametro(
    chave="MANDATO_FORMA_ELEICAO",
    rotulo="Forma de eleição",
    pergunta_simples="Como é feita a votação?",
    tipo="texto", grupo="MANDATO",
    exemplos=("Voto secreto por chapa", "Voto aberto por cargo", "Aclamação"),
))
_reg(DefinicaoParametro(
    chave="MANDATO_INICIO_APOS_POSSE",
    rotulo="Início do mandato",
    pergunta_simples="O mandato começa a contar da eleição ou da posse?",
    tipo="texto", grupo="MANDATO", exemplos=("ELEICAO", "POSSE"),
))

# ------------------------------------------------------------------ Convocação
_reg(DefinicaoParametro(
    chave="CONVOCACAO_PRAZO_DIAS",
    rotulo="Antecedência mínima da convocação",
    pergunta_simples="Com quantos dias de antecedência a assembleia precisa ser convocada?",
    tipo="inteiro", unidade="dias", grupo="CONVOCACAO",
    obrigatorio_para=("ASSEMBLEIA_ORDINARIA", "ASSEMBLEIA_EXTRAORDINARIA", "ELEICAO_DIRETORIA",
                      "REFORMA_ESTATUTARIA", "DESTITUICAO", "APROVACAO_CONTAS", "DISSOLUCAO"),
    fonte_legal="CC_2002", dispositivo_legal="art. 60",
    nota="O art. 60 do Código Civil manda convocar 'na forma do estatuto'. O prazo, "
         "portanto, é o do estatuto — o sistema não arbitra um padrão.",
    exemplos=("8", "15", "30"),
))
_reg(DefinicaoParametro(
    chave="CONVOCACAO_MEIO",
    rotulo="Meio de convocação",
    pergunta_simples="Como os membros são avisados da assembleia?",
    tipo="lista", grupo="CONVOCACAO",
    exemplos=("Edital afixado na sede", "Publicação em jornal", "E-mail", "Aplicativo de mensagens"),
))
_reg(DefinicaoParametro(
    chave="CONVOCACAO_LEGITIMADOS",
    rotulo="Quem pode convocar",
    pergunta_simples="Quem tem poder para convocar a assembleia?",
    tipo="lista", grupo="CONVOCACAO",
    fonte_legal="CC_2002", dispositivo_legal="art. 60",
    nota="Além de quem o estatuto indicar, o art. 60 do Código Civil garante a 1/5 dos "
         "associados o direito de promover a convocação.",
    exemplos=("Presidente", "Diretoria", "Conselho Fiscal", "1/5 dos associados"),
))
_reg(DefinicaoParametro(
    chave="CONVOCACAO_FRACAO_ASSOCIADOS",
    rotulo="Fração de associados que pode convocar",
    pergunta_simples="Que fração dos associados pode convocar a assembleia por conta própria?",
    tipo="fracao", grupo="CONVOCACAO",
    fonte_legal="CC_2002", dispositivo_legal="art. 60",
    valor_supletivo=0.2,
    nota="Piso legal: 1/5 dos associados (art. 60 do Código Civil). O estatuto pode "
         "facilitar, exigindo fração menor, mas não pode suprimir a garantia legal.",
))

# ------------------------------------------------------------------ Quórum
_reg(DefinicaoParametro(
    chave="QUORUM_INSTALACAO_PRIMEIRA",
    rotulo="Quórum de instalação — 1ª convocação",
    pergunta_simples="Quantas pessoas precisam estar presentes para a assembleia começar "
                     "na primeira convocação?",
    tipo="fracao", grupo="QUORUM",
    obrigatorio_para=("ASSEMBLEIA_ORDINARIA", "ASSEMBLEIA_EXTRAORDINARIA", "ELEICAO_DIRETORIA"),
    exemplos=("1/2 + 1 dos associados", "2/3 dos associados", "Sem exigência de quórum mínimo"),
))
_reg(DefinicaoParametro(
    chave="QUORUM_INSTALACAO_SEGUNDA",
    rotulo="Quórum de instalação — 2ª convocação",
    pergunta_simples="E na segunda convocação, quantas pessoas precisam estar presentes?",
    tipo="fracao", grupo="QUORUM",
    exemplos=("Qualquer número", "1/3 dos associados"),
))
_reg(DefinicaoParametro(
    chave="QUORUM_APROVACAO_GERAL",
    rotulo="Quórum de aprovação (matérias comuns)",
    pergunta_simples="Quantos votos são necessários para aprovar uma decisão comum?",
    tipo="fracao", grupo="QUORUM",
    exemplos=("Maioria simples dos presentes", "Maioria absoluta dos associados"),
))
_reg(DefinicaoParametro(
    chave="QUORUM_REFORMA_ESTATUTARIA",
    rotulo="Quórum para reforma estatutária",
    pergunta_simples="Quantos votos são necessários para mudar o estatuto?",
    tipo="fracao", grupo="QUORUM",
    obrigatorio_para=("REFORMA_ESTATUTARIA", "ALTERACAO_FINALIDADE", "ALTERACAO_DENOMINACAO",
                      "ALTERACAO_ORGAOS", "ALTERACAO_MANDATO", "ALTERACAO_QUORUM"),
    fonte_legal="CC_2002", dispositivo_legal="art. 59, II e parágrafo único",
    nota="Competência privativa da assembleia geral, em reunião especialmente convocada "
         "para esse fim. O quórum é o estabelecido no estatuto (redação da Lei nº 11.127/2005) "
         "— o sistema não presume 2/3 nem qualquer outro número.",
))
_reg(DefinicaoParametro(
    chave="QUORUM_DESTITUICAO",
    rotulo="Quórum para destituição de administradores",
    pergunta_simples="Quantos votos são necessários para destituir um dirigente?",
    tipo="fracao", grupo="QUORUM",
    obrigatorio_para=("DESTITUICAO",),
    fonte_legal="CC_2002", dispositivo_legal="art. 59, I e parágrafo único",
    nota="Competência privativa da assembleia geral especialmente convocada; quórum definido "
         "no estatuto.",
))
_reg(DefinicaoParametro(
    chave="QUORUM_DISSOLUCAO",
    rotulo="Quórum para dissolução",
    pergunta_simples="Quantos votos são necessários para dissolver a entidade?",
    tipo="fracao", grupo="QUORUM",
    obrigatorio_para=("DISSOLUCAO",),
    fonte_legal="CC_2002", dispositivo_legal="art. 54, VI",
    nota="O estatuto deve prever as condições de dissolução, sob pena de nulidade.",
))

# ------------------------------------------------------------------ Assembleia ordinária
_reg(DefinicaoParametro(
    chave="AGO_PERIODICIDADE_MESES",
    rotulo="Periodicidade da assembleia ordinária",
    pergunta_simples="De quanto em quanto tempo a assembleia ordinária precisa acontecer?",
    tipo="inteiro", unidade="meses", grupo="ASSEMBLEIA",
    exemplos=("12 (anual)", "24 (bienal)"),
))
_reg(DefinicaoParametro(
    chave="AGO_PRAZO_APROVACAO_CONTAS",
    rotulo="Prazo para aprovação de contas",
    pergunta_simples="Até quando as contas do ano anterior precisam ser aprovadas?",
    tipo="texto", grupo="ASSEMBLEIA",
    fonte_legal="CC_2002", dispositivo_legal="art. 54, VII",
    nota="O estatuto define a forma de aprovação das contas; o prazo é o estatutário.",
    exemplos=("Até 31 de março", "Até 30 de abril", "No primeiro quadrimestre"),
))

# ------------------------------------------------------------------ Órgãos
_reg(DefinicaoParametro(
    chave="CONSELHO_FISCAL_EXISTE",
    rotulo="Conselho Fiscal",
    pergunta_simples="A entidade tem Conselho Fiscal previsto no estatuto?",
    tipo="booleano", grupo="ORGAOS",
))
_reg(DefinicaoParametro(
    chave="CONSELHO_FISCAL_PARECER_OBRIGATORIO",
    rotulo="Parecer do Conselho Fiscal obrigatório",
    pergunta_simples="O parecer do Conselho Fiscal é obrigatório para aprovar as contas?",
    tipo="booleano", grupo="ORGAOS",
    obrigatorio_para=("APROVACAO_CONTAS", "PRESTACAO_CONTAS"),
))
_reg(DefinicaoParametro(
    chave="REPRESENTACAO_FORMA",
    rotulo="Forma de representação",
    pergunta_simples="Quem assina pela entidade e como?",
    tipo="texto", grupo="ORGAOS",
    fonte_legal="CC_2002", dispositivo_legal="art. 46, III",
    nota="O modo de administração e representação deve constar do registro.",
    exemplos=("Presidente isoladamente", "Presidente e Tesoureiro em conjunto"),
))

# ------------------------------------------------------------------ Associados
_reg(DefinicaoParametro(
    chave="ASSOCIADO_CARENCIA_VOTO_MESES",
    rotulo="Carência para votar",
    pergunta_simples="O associado precisa ter quanto tempo de casa para poder votar?",
    tipo="inteiro", unidade="meses", grupo="ASSOCIADOS",
))
_reg(DefinicaoParametro(
    chave="ASSOCIADO_CARENCIA_ELEGIBILIDADE_MESES",
    rotulo="Carência para ser eleito",
    pergunta_simples="E para poder ser eleito, quanto tempo de associação é exigido?",
    tipo="inteiro", unidade="meses", grupo="ASSOCIADOS",
))
_reg(DefinicaoParametro(
    chave="ASSOCIADO_CATEGORIAS_COM_VOTO",
    rotulo="Categorias com direito a voto",
    pergunta_simples="Quais categorias de associado têm direito a voto?",
    tipo="lista", grupo="ASSOCIADOS",
    exemplos=("Efetivos", "Fundadores e efetivos", "Membros ativos"),
))
_reg(DefinicaoParametro(
    chave="ASSOCIADO_ADMITE_PROCURACAO",
    rotulo="Voto por procuração",
    pergunta_simples="O associado pode ser representado por procuração na assembleia?",
    tipo="booleano", grupo="ASSOCIADOS",
))

# ------------------------------------------------------------------ Patrimônio
_reg(DefinicaoParametro(
    chave="DESTINACAO_PATRIMONIAL",
    rotulo="Destinação do patrimônio na dissolução",
    pergunta_simples="Para onde vai o patrimônio se a entidade for dissolvida?",
    tipo="texto", grupo="PATRIMONIO",
    obrigatorio_para=("DISSOLUCAO", "DESTINACAO_PATRIMONIAL", "REFORMA_ESTATUTARIA"),
    fonte_legal="CC_2002", dispositivo_legal="art. 61",
    nota="Dissolvida a associação, o remanescente do patrimônio líquido é destinado à "
         "entidade de fins não econômicos designada no estatuto.",
))


def por_grupo() -> dict[str, list[DefinicaoParametro]]:
    grupos: dict[str, list[DefinicaoParametro]] = {}
    for d in CATALOGO.values():
        grupos.setdefault(d.grupo, []).append(d)
    return grupos


def obrigatorios_para(tipo_evento: str) -> list[DefinicaoParametro]:
    return [d for d in CATALOGO.values() if tipo_evento in d.obrigatorio_para]
