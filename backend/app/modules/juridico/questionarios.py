"""QUESTIONÁRIO INTELIGENTE (§11, §52).

O sistema não joga dezenas de campos na tela: cada ato pede apenas o que é
próprio dele. Todo o resto vem do cadastro (§53).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.enums import TipoEvento


@dataclass(frozen=True)
class Campo:
    nome: str
    pergunta: str
    tipo: str                  # data|texto|numero|opcao|lista|booleano|pessoas
    obrigatorio: bool = True
    opcoes: tuple[str, ...] = ()
    ajuda: str | None = None
    # Parâmetro do estatuto exibido ao lado do campo como referência (§52).
    referencia_estatutaria: str | None = None


@dataclass(frozen=True)
class Questionario:
    tipo_evento: str
    titulo: str
    campos: tuple[Campo, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "tipo_evento": self.tipo_evento,
            "titulo": self.titulo,
            "campos": [
                {
                    "nome": c.nome, "pergunta": c.pergunta, "tipo": c.tipo,
                    "obrigatorio": c.obrigatorio, "opcoes": list(c.opcoes),
                    "ajuda": c.ajuda, "referencia_estatutaria": c.referencia_estatutaria,
                }
                for c in self.campos
            ],
        }


_ASSEMBLEIA_BASE = (
    Campo("data_ato", "Em que dia será (ou foi) a assembleia?", "data"),
    Campo("hora", "A que horas?", "texto", obrigatorio=False),
    Campo("local", "Onde?", "texto", obrigatorio=False,
          ajuda="Se não informar, o sistema usa o endereço da sede."),
    Campo("convocacao", "É primeira ou segunda convocação?", "opcao",
          opcoes=("PRIMEIRA", "SEGUNDA"),
          referencia_estatutaria="QUORUM_INSTALACAO_PRIMEIRA"),
    Campo("data_edital", "Quando o edital/aviso foi publicado?", "data",
          referencia_estatutaria="CONVOCACAO_PRAZO_DIAS",
          ajuda="O sistema confere a antecedência contra o prazo do estatuto."),
    Campo("meio_convocacao", "Como os membros foram avisados?", "texto", obrigatorio=False,
          referencia_estatutaria="CONVOCACAO_MEIO"),
    Campo("convocado_por", "Quem convocou?", "texto",
          referencia_estatutaria="CONVOCACAO_LEGITIMADOS"),
    Campo("ordem_do_dia", "Quais assuntos constam da ordem do dia?", "lista"),
    Campo("total_presentes", "Quantas pessoas estiveram presentes?", "numero",
          obrigatorio=False, referencia_estatutaria="QUORUM_INSTALACAO_PRIMEIRA"),
    Campo("presidente_mesa", "Quem presidiu a assembleia?", "texto", obrigatorio=False),
    Campo("secretario_mesa", "Quem secretariou?", "texto", obrigatorio=False),
)

QUESTIONARIOS: dict[str, Questionario] = {}


def _reg(q: Questionario) -> None:
    QUESTIONARIOS[q.tipo_evento] = q


_reg(Questionario(
    TipoEvento.ELEICAO_DIRETORIA.value, "Eleição de Diretoria",
    _ASSEMBLEIA_BASE + (
        Campo("eleitos", "Quem foi eleito e para qual cargo?", "pessoas"),
        Campo("votos_favor", "Quantos votos a chapa/candidatos receberam?", "numero",
              obrigatorio=False),
        Campo("data_posse", "Quando será a posse?", "data", obrigatorio=False),
        Campo("mandato_inicio", "Quando começa o mandato?", "data",
              referencia_estatutaria="MANDATO_DURACAO_MESES"),
        Campo("mandato_fim", "Quando termina o mandato?", "data",
              referencia_estatutaria="MANDATO_DURACAO_MESES"),
        Campo("conselho_fiscal_eleito", "Também houve eleição do Conselho Fiscal?", "booleano",
              obrigatorio=False, referencia_estatutaria="CONSELHO_FISCAL_EXISTE"),
        Campo("observacoes", "Alguma observação sobre a eleição?", "texto", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.REFORMA_ESTATUTARIA.value, "Reforma Estatutária",
    _ASSEMBLEIA_BASE + (
        Campo("artigos_alterados", "Quais artigos foram alterados?", "lista"),
        Campo("redacao_anterior", "Qual era a redação anterior?", "texto", obrigatorio=False),
        Campo("redacao_aprovada", "Qual é a nova redação aprovada?", "texto"),
        Campo("votos_favor", "Quantos votos a favor?", "numero",
              referencia_estatutaria="QUORUM_REFORMA_ESTATUTARIA"),
        Campo("votos_contra", "Quantos votos contra?", "numero", obrigatorio=False),
        Campo("abstencoes", "Quantas abstenções?", "numero", obrigatorio=False),
        Campo("consolidacao", "O estatuto será consolidado em texto único?", "booleano",
              obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.APROVACAO_CONTAS.value, "Aprovação de Contas",
    _ASSEMBLEIA_BASE + (
        Campo("exercicio", "A que exercício se referem as contas?", "numero"),
        Campo("parecer_conselho_fiscal", "Houve parecer do Conselho Fiscal?", "booleano",
              obrigatorio=False, referencia_estatutaria="CONSELHO_FISCAL_PARECER_OBRIGATORIO"),
        Campo("resultado_parecer", "Qual foi a conclusão do parecer?", "texto",
              obrigatorio=False),
        Campo("votos_favor", "Quantos votos pela aprovação?", "numero", obrigatorio=False),
        Campo("ressalvas", "Houve ressalvas?", "texto", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.ALTERACAO_ENDERECO.value, "Alteração de Endereço",
    (
        Campo("data_ato", "Quando a mudança foi deliberada?", "data"),
        Campo("endereco_novo", "Qual é o novo endereço completo?", "texto"),
        Campo("orgao_deliberante", "Qual órgão deliberou a mudança?", "texto",
              ajuda="Se o endereço consta do estatuto, a mudança exige reforma estatutária."),
        Campo("consta_do_estatuto", "O endereço está escrito no estatuto?", "booleano"),
        Campo("data_edital", "Data da convocação, se houve assembleia", "data",
              obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.RENUNCIA.value, "Renúncia de Dirigente",
    (
        Campo("data_ato", "Qual a data da renúncia?", "data"),
        Campo("pessoa", "Quem renunciou?", "texto"),
        Campo("cargo", "De qual cargo?", "texto"),
        Campo("motivo", "Motivo declarado (opcional)", "texto", obrigatorio=False),
        Campo("substituto", "Quem assume o cargo?", "texto", obrigatorio=False,
              ajuda="Se o estatuto prevê substituto automático, informe aqui."),
        Campo("data_ciencia", "Quando a diretoria/assembleia tomou ciência?", "data",
              obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.DESTITUICAO.value, "Destituição de Administrador",
    _ASSEMBLEIA_BASE + (
        Campo("pessoa", "Quem foi destituído?", "texto"),
        Campo("cargo", "De qual cargo?", "texto"),
        Campo("motivacao", "Qual a motivação apresentada?", "texto"),
        Campo("direito_defesa", "Foi assegurado direito de defesa?", "booleano",
              ajuda="O estatuto deve disciplinar o procedimento; a ausência de defesa é "
                    "causa frequente de anulação."),
        Campo("votos_favor", "Quantos votos pela destituição?", "numero",
              referencia_estatutaria="QUORUM_DESTITUICAO"),
    ),
))

_reg(Questionario(
    TipoEvento.CONSTITUICAO.value, "Constituição da Entidade",
    (
        Campo("data_ato", "Data da assembleia de fundação", "data"),
        Campo("local", "Local da assembleia", "texto"),
        Campo("fundadores", "Quem são os fundadores?", "pessoas"),
        Campo("finalidades", "Quais são as finalidades da entidade?", "lista"),
        Campo("eleitos", "Quem compõe a primeira diretoria?", "pessoas"),
        Campo("mandato_inicio", "Início do primeiro mandato", "data"),
        Campo("mandato_fim", "Término do primeiro mandato", "data"),
        Campo("sede", "Endereço da sede", "texto"),
    ),
))

_reg(Questionario(
    TipoEvento.POSSE_DIRETORIA.value, "Posse de Diretoria",
    (
        Campo("data_ato", "Data da posse", "data"),
        Campo("eleitos", "Quem toma posse e em qual cargo?", "pessoas"),
        Campo("mandato_inicio", "Início do mandato", "data"),
        Campo("mandato_fim", "Término do mandato", "data"),
        Campo("ata_eleicao", "Referência da ata de eleição", "texto", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.ASSEMBLEIA_ORDINARIA.value, "Assembleia Geral Ordinária", _ASSEMBLEIA_BASE
))
_reg(Questionario(
    TipoEvento.ASSEMBLEIA_EXTRAORDINARIA.value, "Assembleia Geral Extraordinária", _ASSEMBLEIA_BASE
))



# ─────────────────────────────────────────── Alterações estatutárias específicas

def _alteracao_estatutaria(campos_proprios: tuple[Campo, ...]) -> tuple[Campo, ...]:
    """Toda alteração do estatuto pede o mesmo esqueleto: o que mudou, a redação
    antes e depois, e a votação que aprovou."""
    return _ASSEMBLEIA_BASE + campos_proprios + (
        Campo("artigos_alterados", "Quais artigos foram alterados?", "lista"),
        Campo("redacao_anterior", "Qual era a redação anterior?", "texto", obrigatorio=False),
        Campo("redacao_aprovada", "Qual é a nova redação aprovada?", "texto"),
        Campo("votos_favor", "Quantos votos a favor?", "numero",
              referencia_estatutaria="QUORUM_REFORMA_ESTATUTARIA"),
        Campo("votos_contra", "Quantos votos contra?", "numero", obrigatorio=False),
        Campo("abstencoes", "Quantas abstenções?", "numero", obrigatorio=False),
        Campo("consolidacao", "O estatuto será consolidado em texto único?", "booleano",
              obrigatorio=False),
    )


_reg(Questionario(
    TipoEvento.ALTERACAO_DENOMINACAO.value, "Alteração de Denominação",
    _alteracao_estatutaria((
        Campo("denominacao_anterior", "Qual é o nome atual da entidade?", "texto"),
        Campo("denominacao_nova", "Qual será o novo nome?", "texto"),
        Campo("motivo", "Por que o nome está mudando?", "texto", obrigatorio=False),
        Campo("manter_nome_fantasia", "O nome fantasia permanece o mesmo?", "booleano",
              obrigatorio=False),
    )),
))

_reg(Questionario(
    TipoEvento.ALTERACAO_FINALIDADE.value, "Alteração de Finalidade",
    _alteracao_estatutaria((
        Campo("finalidades_anteriores", "Quais são as finalidades atuais?", "lista"),
        Campo("finalidades_novas", "Quais serão as novas finalidades?", "lista"),
        Campo("mantem_sem_fins_lucrativos",
              "A entidade continua sem fins lucrativos?", "booleano",
              ajuda="Perder essa característica muda a natureza jurídica e afeta "
                    "imunidades e qualificações."),
        Campo("afeta_qualificacoes",
              "A entidade tem OSCIP, CEBAS ou parceria pública vigente?", "booleano",
              obrigatorio=False),
    )),
))

_reg(Questionario(
    TipoEvento.ALTERACAO_ORGAOS.value, "Alteração de Órgãos",
    _alteracao_estatutaria((
        Campo("orgaos_criados", "Que órgãos serão criados?", "lista", obrigatorio=False),
        Campo("orgaos_extintos", "Que órgãos serão extintos?", "lista", obrigatorio=False),
        Campo("orgaos_alterados", "Que órgãos mudam de composição ou competência?",
              "lista", obrigatorio=False),
        Campo("destino_mandatos_em_curso",
              "O que acontece com os mandatos em curso nos órgãos afetados?", "texto",
              obrigatorio=False),
    )),
))

_reg(Questionario(
    TipoEvento.ALTERACAO_MANDATO.value, "Alteração do Prazo de Mandato",
    _alteracao_estatutaria((
        Campo("mandato_anterior_meses", "Qual é a duração atual do mandato, em meses?",
              "numero", referencia_estatutaria="MANDATO_DURACAO_MESES"),
        Campo("mandato_novo_meses", "Qual será a nova duração, em meses?", "numero"),
        Campo("aplica_ao_mandato_vigente",
              "A nova duração vale para o mandato em curso?", "booleano",
              ajuda="Aplicar ao mandato vigente costuma gerar exigência no registro. "
                    "O usual é valer a partir da próxima gestão."),
    )),
))

_reg(Questionario(
    TipoEvento.ALTERACAO_QUORUM.value, "Alteração de Quórum",
    _alteracao_estatutaria((
        Campo("quorum_alterado", "Qual quórum está sendo alterado?", "opcao",
              opcoes=("INSTALACAO_PRIMEIRA", "INSTALACAO_SEGUNDA", "APROVACAO_GERAL",
                      "REFORMA_ESTATUTARIA", "DESTITUICAO", "DISSOLUCAO")),
        Campo("quorum_anterior", "Qual é o quórum atual?", "texto"),
        Campo("quorum_novo", "Qual será o novo quórum?", "texto"),
    )),
))

# ────────────────────────────────────────────────────────── Diretoria — demais

_reg(Questionario(
    TipoEvento.REELEICAO_DIRETORIA.value, "Reeleição de Diretoria",
    _ASSEMBLEIA_BASE + (
        Campo("eleitos", "Quem foi reeleito e para qual cargo?", "pessoas"),
        Campo("mandatos_anteriores_consecutivos",
              "Quantos mandatos seguidos cada reeleito já cumpriu?", "numero",
              obrigatorio=False, referencia_estatutaria="MANDATO_LIMITE_REELEICOES"),
        Campo("votos_favor", "Quantos votos favoráveis?", "numero", obrigatorio=False),
        Campo("mandato_inicio", "Quando começa o novo mandato?", "data",
              referencia_estatutaria="MANDATO_DURACAO_MESES"),
        Campo("mandato_fim", "Quando termina?", "data"),
        Campo("data_posse", "Data da posse", "data", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.SUBSTITUICAO.value, "Substituição de Dirigente",
    (
        Campo("data_ato", "Data da substituição", "data"),
        Campo("pessoa_substituida", "Quem está sendo substituído?", "texto"),
        Campo("cargo", "Qual cargo?", "texto"),
        Campo("motivo_vacancia", "Por que o cargo ficou vago?", "opcao",
              opcoes=("RENUNCIA", "DESTITUICAO", "FALECIMENTO", "IMPEDIMENTO", "OUTRO")),
        Campo("substituto", "Quem assume o cargo?", "texto"),
        Campo("substituicao_automatica",
              "O estatuto prevê substituto automático para este cargo?", "booleano",
              ajuda="Havendo previsão (vice, suplente), a substituição pode dispensar "
                    "assembleia."),
        Campo("mandato_fim", "Até quando vai o mandato do substituto?", "data",
              obrigatorio=False,
              ajuda="Em regra o substituto completa o mandato em curso."),
    ),
))

_reg(Questionario(
    TipoEvento.VACANCIA.value, "Declaração de Vacância",
    (
        Campo("data_ato", "Data da declaração", "data"),
        Campo("cargo", "Qual cargo está vago?", "texto"),
        Campo("pessoa", "Quem ocupava o cargo?", "texto", obrigatorio=False),
        Campo("motivo_vacancia", "Motivo da vacância", "opcao",
              opcoes=("RENUNCIA", "DESTITUICAO", "FALECIMENTO", "ABANDONO",
                      "PERDA_DE_REQUISITO", "OUTRO")),
        Campo("providencia", "Como o cargo será preenchido?", "texto", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.ALTERACAO_CARGOS.value, "Alteração de Cargos da Diretoria",
    (
        Campo("data_ato", "Data da deliberação", "data"),
        Campo("remanejamentos", "Quem passa a ocupar qual cargo?", "pessoas"),
        Campo("orgao_deliberante", "Qual órgão deliberou?", "texto"),
        Campo("cria_ou_extingue_cargo",
              "Algum cargo está sendo criado ou extinto?", "booleano",
              ajuda="Criar ou extinguir cargo exige reforma estatutária; apenas "
                    "remanejar pessoas, não."),
    ),
))

_reg(Questionario(
    TipoEvento.APROVACAO_ESTATUTO.value, "Aprovação do Estatuto",
    _ASSEMBLEIA_BASE + (
        Campo("votos_favor", "Quantos votos pela aprovação?", "numero"),
        Campo("texto_aprovado", "Texto do estatuto aprovado", "texto", obrigatorio=False),
        Campo("consolidacao", "O texto será consolidado?", "booleano", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.REGISTRO_INICIAL.value, "Registro Inicial no RCPJ",
    (
        Campo("data_ato", "Data do protocolo", "data"),
        Campo("rcpj", "Qual cartório receberá o protocolo?", "texto", obrigatorio=False),
        Campo("representante", "Quem assina o requerimento?", "texto"),
        Campo("vias", "Quantas vias serão apresentadas?", "numero", obrigatorio=False),
        Campo("observacoes", "Observações", "texto", obrigatorio=False),
    ),
))

# ────────────────────────────────────────────── Prestação de contas — demais

_reg(Questionario(
    TipoEvento.PRESTACAO_CONTAS.value, "Prestação de Contas do Exercício",
    _ASSEMBLEIA_BASE + (
        Campo("exercicio", "A que exercício se refere a prestação de contas?", "numero",
              referencia_estatutaria="AGO_PRAZO_APROVACAO_CONTAS"),
        Campo("data_inicio_exercicio", "Início do exercício", "data", obrigatorio=False),
        Campo("data_fim_exercicio", "Encerramento do exercício", "data", obrigatorio=False),
        Campo("receitas_totais", "Receitas totais do exercício", "numero", obrigatorio=False),
        Campo("despesas_totais", "Despesas totais do exercício", "numero", obrigatorio=False),
        Campo("resultado", "Resultado do exercício (superávit ou déficit)", "texto",
              obrigatorio=False),
        Campo("demonstracoes_anexadas", "Quais demonstrações acompanham a prestação?",
              "lista", obrigatorio=False,
              ajuda="Balanço patrimonial, demonstração do resultado, notas explicativas."),
        Campo("parecer_conselho_fiscal", "Houve parecer do Conselho Fiscal?", "booleano",
              referencia_estatutaria="CONSELHO_FISCAL_PARECER_OBRIGATORIO"),
        Campo("resultado_parecer", "Qual foi a conclusão do parecer?", "texto",
              obrigatorio=False),
        Campo("recursos_publicos",
              "O exercício teve convênio, parceria ou subvenção pública?", "booleano",
              obrigatorio=False,
              ajuda="Havendo recurso público, existem exigências de prestação de "
                    "contas além da estatutária."),
        Campo("votos_favor", "Quantos votos pela aprovação?", "numero", obrigatorio=False),
        Campo("ressalvas", "Houve ressalvas?", "texto", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.PARECER_CONSELHO_FISCAL.value, "Parecer do Conselho Fiscal",
    (
        Campo("data_ato", "Data do parecer", "data"),
        Campo("exercicio", "A que exercício se refere?", "numero"),
        Campo("membros_presentes", "Quais conselheiros assinam o parecer?", "pessoas"),
        Campo("conclusao", "Qual a conclusão?", "opcao",
              opcoes=("APROVACAO", "APROVACAO_COM_RESSALVAS", "REPROVACAO",
                      "ABSTENCAO")),
        Campo("ressalvas", "Descreva as ressalvas, se houver", "texto", obrigatorio=False),
        Campo("documentos_examinados", "Que documentos foram examinados?", "lista",
              obrigatorio=False),
    ),
))

# ──────────────────────────────────────────────────────────────── Encerramento

_reg(Questionario(
    TipoEvento.DISSOLUCAO.value, "Dissolução da Entidade",
    _ASSEMBLEIA_BASE + (
        Campo("motivo", "Qual o motivo da dissolução?", "texto"),
        Campo("votos_favor", "Quantos votos pela dissolução?", "numero",
              referencia_estatutaria="QUORUM_DISSOLUCAO"),
        Campo("liquidante", "Quem foi nomeado liquidante?", "texto"),
        Campo("prazo_liquidacao", "Prazo estimado para a liquidação", "texto",
              obrigatorio=False),
        Campo("destinacao_patrimonio", "Para onde vai o patrimônio remanescente?",
              "texto", referencia_estatutaria="DESTINACAO_PATRIMONIAL"),
        Campo("existem_dividas", "A entidade tem dívidas ou obrigações pendentes?",
              "booleano", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.LIQUIDACAO.value, "Liquidação",
    (
        Campo("data_ato", "Data do ato", "data"),
        Campo("liquidante", "Quem é o liquidante?", "texto"),
        Campo("ativo_apurado", "Ativo apurado", "numero", obrigatorio=False),
        Campo("passivo_pago", "Passivo pago", "numero", obrigatorio=False),
        Campo("remanescente", "Patrimônio remanescente", "numero", obrigatorio=False),
        Campo("prestacao_contas_liquidacao",
              "As contas da liquidação foram prestadas?", "booleano", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.DESTINACAO_PATRIMONIAL.value, "Destinação do Patrimônio",
    _ASSEMBLEIA_BASE + (
        Campo("bens", "Quais bens compõem o remanescente?", "lista"),
        Campo("entidade_destinataria", "Qual entidade receberá o patrimônio?", "texto",
              referencia_estatutaria="DESTINACAO_PATRIMONIAL"),
        Campo("cnpj_destinataria", "CNPJ da destinatária", "texto", obrigatorio=False),
        Campo("destinataria_sem_fins_lucrativos",
              "A destinatária é entidade de fins não econômicos?", "booleano",
              ajuda="A lei exige que o remanescente vá para entidade de fins não "
                    "econômicos."),
        Campo("votos_favor", "Quantos votos favoráveis?", "numero", obrigatorio=False),
    ),
))

_reg(Questionario(
    TipoEvento.ENCERRAMENTO.value, "Encerramento e Baixa",
    (
        Campo("data_ato", "Data do encerramento", "data"),
        Campo("liquidacao_encerrada", "A liquidação foi concluída?", "booleano"),
        Campo("patrimonio_destinado", "O patrimônio já foi destinado?", "booleano"),
        Campo("baixas_pendentes", "Que baixas ainda faltam?", "lista", obrigatorio=False,
              ajuda="CNPJ, inscrição municipal, inscrição estadual, contas bancárias."),
        Campo("responsavel", "Quem responde pelo encerramento?", "texto"),
    ),
))


def questionario_de(tipo_evento: str) -> Questionario:
    return QUESTIONARIOS.get(
        tipo_evento,
        Questionario(tipo_evento, tipo_evento.replace("_", " ").title(), _ASSEMBLEIA_BASE),
    )


def campos_faltantes(tipo_evento: str, dados: dict) -> list[str]:
    q = questionario_de(tipo_evento)
    return [c.nome for c in q.campos if c.obrigatorio and not dados.get(c.nome)]
