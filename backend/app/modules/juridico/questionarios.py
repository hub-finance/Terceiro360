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


def questionario_de(tipo_evento: str) -> Questionario:
    return QUESTIONARIOS.get(
        tipo_evento,
        Questionario(tipo_evento, tipo_evento.replace("_", " ").title(), _ASSEMBLEIA_BASE),
    )


def campos_faltantes(tipo_evento: str, dados: dict) -> list[str]:
    q = questionario_de(tipo_evento)
    return [c.nome for c in q.campos if c.obrigatorio and not dados.get(c.nome)]
