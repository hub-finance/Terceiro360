"""MATRIZ DE ATOS — o que cada ato é, juridicamente (§10, §39).

Antes desta matriz, cada parte do sistema respondia à sua maneira se um ato
era assembleia ordinária ou extraordinária, se exigia reforma estatutária e
qual quórum se aplicava. Regra espalhada é regra que diverge.

Aqui há **uma** declaração por ato, e todo o resto — questionário, validação,
checklist, geração de documentos e motor de decisão — lê daqui.

RESSALVA IMPORTANTE
-------------------
A matriz declara o que a lei fixa e o que ela devolve ao estatuto. Onde a lei
devolve, o campo diz `CONFORME_ESTATUTO` — e o sistema vai buscar o parâmetro
cadastrado em vez de arbitrar. Um exemplo que motivou esta matriz: a eleição da
diretoria pode acontecer dentro da assembleia ordinária, se o estatuto assim
dispuser. Presumir "extraordinária" seria errado.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.enums import TipoDocumento, TipoEvento


class EspecieAssembleia:
    ORDINARIA = "ORDINARIA"
    EXTRAORDINARIA = "EXTRAORDINARIA"
    CONFORME_ESTATUTO = "CONFORME_ESTATUTO"
    NAO_ASSEMBLEAR = "NAO_ASSEMBLEAR"


class ExigeReforma:
    SEMPRE = "SEMPRE"
    NUNCA = "NUNCA"
    DEPENDE_DO_ESTATUTO = "DEPENDE_DO_ESTATUTO"
    NAO_APLICAVEL = "NAO_APLICAVEL"


class EfeitoRegistral:
    REGISTRO = "REGISTRO"        # inscrição do ato constitutivo
    AVERBACAO = "AVERBACAO"      # anotação de alteração no registro existente
    INTERNO = "INTERNO"          # não vai a registro


@dataclass(frozen=True)
class Ato:
    tipo: str
    titulo: str
    categoria: str
    descricao: str

    orgao_competente: str = "ASSEMBLEIA_GERAL"
    especie_assembleia: str = EspecieAssembleia.EXTRAORDINARIA
    exige_reforma_estatutaria: str = ExigeReforma.NUNCA
    # Competência privativa da assembleia geral em reunião especialmente
    # convocada para esse fim (Código Civil, art. 59 e parágrafo único).
    exige_convocacao_especifica: bool = False
    chave_quorum: str | None = "QUORUM_APROVACAO_GERAL"
    efeito_registral: str = EfeitoRegistral.AVERBACAO

    documentos: tuple[str, ...] = ()
    fundamentos: tuple[tuple[str, str], ...] = ()   # (chave da fonte, dispositivo)
    parametros_relevantes: tuple[str, ...] = ()
    nota: str | None = None
    alertas: tuple[str, ...] = field(default_factory=tuple)

    @property
    def assemblear(self) -> bool:
        return self.especie_assembleia != EspecieAssembleia.NAO_ASSEMBLEAR

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "titulo": self.titulo,
            "categoria": self.categoria,
            "descricao": self.descricao,
            "orgao_competente": self.orgao_competente,
            "especie_assembleia": self.especie_assembleia,
            "exige_reforma_estatutaria": self.exige_reforma_estatutaria,
            "exige_convocacao_especifica": self.exige_convocacao_especifica,
            "chave_quorum": self.chave_quorum,
            "efeito_registral": self.efeito_registral,
            "assemblear": self.assemblear,
            "documentos": list(self.documentos),
            "fundamentos": [{"fonte": f, "dispositivo": d} for f, d in self.fundamentos],
            "parametros_relevantes": list(self.parametros_relevantes),
            "nota": self.nota,
            "alertas": list(self.alertas),
        }


MATRIZ: dict[str, Ato] = {}


def _reg(ato: Ato) -> None:
    MATRIZ[ato.tipo] = ato


D = TipoDocumento
E = TipoEvento

# Documentos que praticamente todo ato assemblear produz.
_ASSEMBLEAR = (D.EDITAL_CONVOCACAO.value, D.LISTA_PRESENCA.value, D.ATA.value)

# ─────────────────────────────────────────────────────────────── Constituição

_reg(Ato(
    tipo=E.CONSTITUICAO.value,
    titulo="Constituição da entidade",
    categoria="CONSTITUIÇÃO",
    descricao="Assembleia de fundação: aprova o estatuto, elege a primeira "
              "diretoria e dá origem à pessoa jurídica.",
    especie_assembleia=EspecieAssembleia.EXTRAORDINARIA,
    exige_reforma_estatutaria=ExigeReforma.NAO_APLICAVEL,
    chave_quorum=None,
    efeito_registral=EfeitoRegistral.REGISTRO,
    documentos=(D.ATA.value, D.LISTA_PRESENCA.value, D.ESTATUTO_CONSOLIDADO.value,
                D.TERMO_POSSE.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 45"), ("CC_2002", "art. 46"), ("CC_2002", "art. 54"),
                 ("LRP_1973", "art. 114")),
    nota="A existência legal começa com a inscrição do ato constitutivo no registro "
         "competente. Antes disso a entidade não tem personalidade jurídica.",
))

_reg(Ato(
    tipo=E.APROVACAO_ESTATUTO.value,
    titulo="Aprovação do estatuto",
    categoria="CONSTITUIÇÃO",
    descricao="Deliberação que aprova o texto do estatuto social.",
    exige_reforma_estatutaria=ExigeReforma.NAO_APLICAVEL,
    efeito_registral=EfeitoRegistral.REGISTRO,
    documentos=(*_ASSEMBLEAR, D.ESTATUTO_CONSOLIDADO.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 54"),),
))

_reg(Ato(
    tipo=E.REGISTRO_INICIAL.value,
    titulo="Registro inicial no RCPJ",
    categoria="CONSTITUIÇÃO",
    descricao="Protocolo dos atos constitutivos no Registro Civil de Pessoas Jurídicas.",
    orgao_competente="DIRETORIA",
    especie_assembleia=EspecieAssembleia.NAO_ASSEMBLEAR,
    exige_reforma_estatutaria=ExigeReforma.NAO_APLICAVEL,
    chave_quorum=None,
    efeito_registral=EfeitoRegistral.REGISTRO,
    documentos=(D.REQUERIMENTO_RCPJ.value, D.RELACAO_DOCUMENTOS.value, D.CAPA_PROTOCOLO.value),
    fundamentos=(("LRP_1973", "art. 120"), ("LRP_1973", "art. 121")),
))

# ───────────────────────────────────────────────────────────────── Diretoria

_reg(Ato(
    tipo=E.ELEICAO_DIRETORIA.value,
    titulo="Eleição de diretoria",
    categoria="DIRETORIA",
    descricao="Escolha dos administradores para o próximo mandato.",
    # O estatuto decide se a eleição ocorre em assembleia ordinária ou
    # extraordinária, e qual órgão elege.
    especie_assembleia=EspecieAssembleia.CONFORME_ESTATUTO,
    chave_quorum="QUORUM_APROVACAO_GERAL",
    documentos=(*_ASSEMBLEAR, D.TERMO_POSSE.value, D.RELACAO_DIRETORIA.value,
                D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 59"), ("CC_2002", "art. 60")),
    parametros_relevantes=("MANDATO_DURACAO_MESES", "MANDATO_ORGAO_ELEITOR",
                           "MANDATO_FORMA_ELEICAO", "CONVOCACAO_PRAZO_DIAS",
                           "QUORUM_INSTALACAO_PRIMEIRA"),
    nota="Os critérios de eleição dos administradores são os estabelecidos no "
         "estatuto (art. 59, parágrafo único, do Código Civil).",
))

_reg(Ato(
    tipo=E.REELEICAO_DIRETORIA.value,
    titulo="Reeleição de diretoria",
    categoria="DIRETORIA",
    descricao="Recondução dos mesmos administradores para novo mandato.",
    especie_assembleia=EspecieAssembleia.CONFORME_ESTATUTO,
    documentos=(*_ASSEMBLEAR, D.TERMO_POSSE.value, D.RELACAO_DIRETORIA.value,
                D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 59"),),
    parametros_relevantes=("MANDATO_PERMITE_REELEICAO", "MANDATO_LIMITE_REELEICOES",
                           "MANDATO_DURACAO_MESES"),
    alertas=("Confirme se o estatuto admite reeleição e quantas vezes seguidas.",),
))

_reg(Ato(
    tipo=E.POSSE_DIRETORIA.value,
    titulo="Posse de diretoria",
    categoria="DIRETORIA",
    descricao="Investidura dos eleitos nos cargos.",
    orgao_competente="DIRETORIA",
    especie_assembleia=EspecieAssembleia.NAO_ASSEMBLEAR,
    chave_quorum=None,
    documentos=(D.TERMO_POSSE.value, D.RELACAO_DIRETORIA.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 46"),),
    parametros_relevantes=("MANDATO_INICIO_APOS_POSSE",),
    nota="Verifique no estatuto se o mandato conta da eleição ou da posse — a "
         "diferença muda a data de término.",
))

_reg(Ato(
    tipo=E.RENUNCIA.value,
    titulo="Renúncia de dirigente",
    categoria="DIRETORIA",
    descricao="Ato unilateral pelo qual o administrador deixa o cargo.",
    orgao_competente="DIRETORIA",
    especie_assembleia=EspecieAssembleia.NAO_ASSEMBLEAR,
    chave_quorum=None,
    documentos=(D.TERMO_RENUNCIA.value, D.ATA.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 45"),),
    nota="A renúncia é unilateral e não depende de aceitação, mas produz efeitos "
         "perante terceiros a partir da averbação no registro.",
    alertas=("Se a renúncia deixa o cargo vago, registre também a substituição ou "
             "a vacância.",),
))

_reg(Ato(
    tipo=E.DESTITUICAO.value,
    titulo="Destituição de administrador",
    categoria="DIRETORIA",
    descricao="Afastamento do administrador por deliberação da assembleia.",
    especie_assembleia=EspecieAssembleia.EXTRAORDINARIA,
    exige_convocacao_especifica=True,
    chave_quorum="QUORUM_DESTITUICAO",
    documentos=(*_ASSEMBLEAR, D.TERMO_DESTITUICAO.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 59"),),
    parametros_relevantes=("QUORUM_DESTITUICAO", "CONVOCACAO_PRAZO_DIAS"),
    nota="Competência privativa da assembleia geral, em reunião especialmente "
         "convocada para esse fim, com o quórum estabelecido no estatuto.",
    alertas=("A matéria precisa constar expressamente da ordem do dia do edital.",
             "Assegure e documente o direito de defesa: sua ausência é causa "
             "frequente de anulação."),
))

_reg(Ato(
    tipo=E.SUBSTITUICAO.value,
    titulo="Substituição de dirigente",
    categoria="DIRETORIA",
    descricao="Preenchimento de cargo vago por quem o estatuto indicar.",
    especie_assembleia=EspecieAssembleia.CONFORME_ESTATUTO,
    documentos=(D.ATA.value, D.TERMO_POSSE.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 46"),),
    nota="Se o estatuto prevê substituto automático (vice, suplente), a "
         "substituição pode dispensar assembleia. Confirme a regra.",
))

_reg(Ato(
    tipo=E.VACANCIA.value,
    titulo="Vacância de cargo",
    categoria="DIRETORIA",
    descricao="Declaração de que o cargo está vago.",
    especie_assembleia=EspecieAssembleia.CONFORME_ESTATUTO,
    documentos=(D.ATA.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 46"),),
    alertas=("Cargo obrigatório vago compromete a representação da entidade: "
             "resolva antes de praticar novos atos.",),
))

_reg(Ato(
    tipo=E.ALTERACAO_CARGOS.value,
    titulo="Alteração de cargos da diretoria",
    categoria="DIRETORIA",
    descricao="Redistribuição de pessoas entre os cargos existentes.",
    especie_assembleia=EspecieAssembleia.CONFORME_ESTATUTO,
    documentos=(D.ATA.value, D.RELACAO_DIRETORIA.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 46"),),
    nota="Trocar quem ocupa cada cargo é uma coisa; criar ou extinguir cargos é "
         "outra, e essa exige reforma estatutária.",
))

# ────────────────────────────────────────────────────────────────── Estatuto

_ALTERACAO_ESTATUTARIA = {
    "categoria": "ESTATUTO",
    "especie_assembleia": EspecieAssembleia.EXTRAORDINARIA,
    "exige_convocacao_especifica": True,
    "exige_reforma_estatutaria": ExigeReforma.SEMPRE,
    "chave_quorum": "QUORUM_REFORMA_ESTATUTARIA",
    "documentos": (*_ASSEMBLEAR, D.ESTATUTO_CONSOLIDADO.value, D.QUADRO_COMPARATIVO.value,
                   D.REQUERIMENTO_RCPJ.value),
    "fundamentos": (("CC_2002", "art. 59"), ("CC_2002", "art. 54")),
    "parametros_relevantes": ("QUORUM_REFORMA_ESTATUTARIA", "CONVOCACAO_PRAZO_DIAS"),
}

_reg(Ato(
    tipo=E.REFORMA_ESTATUTARIA.value,
    titulo="Reforma estatutária",
    categoria="ESTATUTO",
    descricao="Alteração do texto do estatuto social.",
    especie_assembleia=EspecieAssembleia.EXTRAORDINARIA,
    exige_convocacao_especifica=True,
    exige_reforma_estatutaria=ExigeReforma.SEMPRE,
    chave_quorum="QUORUM_REFORMA_ESTATUTARIA",
    documentos=_ALTERACAO_ESTATUTARIA["documentos"],
    fundamentos=(("CC_2002", "art. 59"), ("CC_2002", "art. 54"), ("CC_2002", "art. 45")),
    parametros_relevantes=("QUORUM_REFORMA_ESTATUTARIA", "CONVOCACAO_PRAZO_DIAS"),
    nota="Competência privativa da assembleia geral, em reunião especialmente "
         "convocada para esse fim. O quórum é o do estatuto.",
    alertas=("Toda alteração do ato constitutivo precisa ser averbada no registro.",),
))

_reg(Ato(
    tipo=E.ALTERACAO_DENOMINACAO.value,
    titulo="Alteração de denominação (mudança de nome)",
    descricao="Troca do nome da entidade.",
    nota="A denominação é conteúdo obrigatório do estatuto (art. 54, I, do Código "
         "Civil). Mudá-la é, necessariamente, reforma estatutária.",
    alertas=("Depois do registro, atualize CNPJ, certidões, contas bancárias e "
             "convênios: o nome antigo deixa de existir.",),
    **_ALTERACAO_ESTATUTARIA,
))

_reg(Ato(
    tipo=E.ALTERACAO_FINALIDADE.value,
    titulo="Alteração de finalidade",
    descricao="Mudança dos fins a que a entidade se destina.",
    nota="Os fins são conteúdo obrigatório do estatuto (art. 54, I). A alteração "
         "exige reforma estatutária.",
    alertas=("Mudança de finalidade pode afetar imunidade tributária, títulos e "
             "qualificações (OSCIP, CEBAS) e parcerias vigentes.",),
    **_ALTERACAO_ESTATUTARIA,
))

_reg(Ato(
    tipo=E.ALTERACAO_ORGAOS.value,
    titulo="Alteração de órgãos",
    descricao="Criação, extinção ou reestruturação de órgãos da entidade.",
    nota="O modo de constituição e funcionamento dos órgãos deliberativos é "
         "conteúdo obrigatório do estatuto (art. 54, V).",
    **_ALTERACAO_ESTATUTARIA,
))

_reg(Ato(
    tipo=E.ALTERACAO_MANDATO.value,
    titulo="Alteração do prazo de mandato",
    descricao="Mudança na duração do mandato dos administradores.",
    nota="Altera a forma de gestão administrativa prevista no estatuto.",
    alertas=("Defina se a nova duração vale para o mandato em curso ou só para o "
             "próximo: aplicar ao mandato vigente costuma gerar exigência.",),
    **_ALTERACAO_ESTATUTARIA,
))

_reg(Ato(
    tipo=E.ALTERACAO_QUORUM.value,
    titulo="Alteração de quórum",
    descricao="Mudança nos quóruns de instalação ou de deliberação.",
    nota="As condições para alteração das disposições estatutárias são conteúdo "
         "obrigatório do estatuto (art. 54, VI).",
    alertas=("A alteração é deliberada pelo quórum ANTIGO; o novo só vale para as "
             "assembleias seguintes.",
             "O estatuto não pode suprimir a garantia legal de convocação por 1/5 "
             "dos associados."),
    **_ALTERACAO_ESTATUTARIA,
))

_reg(Ato(
    tipo=E.ALTERACAO_ENDERECO.value,
    titulo="Alteração de endereço",
    categoria="ESTATUTO",
    descricao="Transferência da sede da entidade.",
    especie_assembleia=EspecieAssembleia.CONFORME_ESTATUTO,
    exige_reforma_estatutaria=ExigeReforma.DEPENDE_DO_ESTATUTO,
    chave_quorum="QUORUM_APROVACAO_GERAL",
    documentos=(D.ATA.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 54"), ("CC_2002", "art. 45")),
    nota="A sede é conteúdo obrigatório do estatuto (art. 54, I), mas o nível de "
         "detalhe varia: estatuto que fixa só o município comporta mudança de "
         "endereço dentro dele por averbação; estatuto que traz o endereço "
         "completo exige reforma. Mudança de município exige reforma em qualquer "
         "caso — e pode mudar o RCPJ competente.",
))

# ────────────────────────────────────────────────────────────── Assembleias

_reg(Ato(
    tipo=E.ASSEMBLEIA_ORDINARIA.value,
    titulo="Assembleia Geral Ordinária",
    categoria="ASSEMBLEIAS",
    descricao="Assembleia periódica prevista no estatuto.",
    especie_assembleia=EspecieAssembleia.ORDINARIA,
    documentos=_ASSEMBLEAR,
    fundamentos=(("CC_2002", "art. 60"),),
    parametros_relevantes=("AGO_PERIODICIDADE_MESES", "CONVOCACAO_PRAZO_DIAS",
                           "QUORUM_INSTALACAO_PRIMEIRA", "QUORUM_INSTALACAO_SEGUNDA"),
))

_reg(Ato(
    tipo=E.ASSEMBLEIA_EXTRAORDINARIA.value,
    titulo="Assembleia Geral Extraordinária",
    categoria="ASSEMBLEIAS",
    descricao="Assembleia convocada fora do calendário ordinário.",
    especie_assembleia=EspecieAssembleia.EXTRAORDINARIA,
    documentos=_ASSEMBLEAR,
    fundamentos=(("CC_2002", "art. 60"),),
    parametros_relevantes=("CONVOCACAO_PRAZO_DIAS", "CONVOCACAO_LEGITIMADOS"),
))

# ───────────────────────────────────────────────────────── Prestação de contas

_reg(Ato(
    tipo=E.APROVACAO_CONTAS.value,
    titulo="Aprovação de contas",
    categoria="PRESTAÇÃO DE CONTAS",
    descricao="Deliberação da assembleia sobre as contas do exercício.",
    especie_assembleia=EspecieAssembleia.ORDINARIA,
    chave_quorum="QUORUM_APROVACAO_GERAL",
    efeito_registral=EfeitoRegistral.INTERNO,
    documentos=(*_ASSEMBLEAR, D.DEMONSTRACOES_CONTABEIS.value,
                D.PARECER_CONSELHO_FISCAL.value),
    fundamentos=(("CC_2002", "art. 54"),),
    parametros_relevantes=("AGO_PRAZO_APROVACAO_CONTAS", "CONSELHO_FISCAL_PARECER_OBRIGATORIO",
                           "QUORUM_APROVACAO_GERAL"),
    nota="A forma de aprovação das contas é conteúdo obrigatório do estatuto "
         "(art. 54, VII). A ata de aprovação costuma não ir a registro, mas é "
         "exigida em prestações de contas de convênios e parcerias.",
))

_reg(Ato(
    tipo=E.PRESTACAO_CONTAS.value,
    titulo="Prestação de contas do exercício",
    categoria="PRESTAÇÃO DE CONTAS",
    descricao="Apresentação das demonstrações e do relatório do exercício aos "
              "órgãos competentes.",
    especie_assembleia=EspecieAssembleia.ORDINARIA,
    chave_quorum="QUORUM_APROVACAO_GERAL",
    efeito_registral=EfeitoRegistral.INTERNO,
    documentos=(*_ASSEMBLEAR, D.DEMONSTRACOES_CONTABEIS.value,
                D.PARECER_CONSELHO_FISCAL.value),
    fundamentos=(("CC_2002", "art. 54"), ("MROSC_2014", "art. 33"),
                 ("OSCIP_1999", "art. 4º")),
    parametros_relevantes=("AGO_PRAZO_APROVACAO_CONTAS", "AGO_PERIODICIDADE_MESES",
                           "CONSELHO_FISCAL_PARECER_OBRIGATORIO"),
    alertas=("Entidade com parceria pública ou qualificação (OSCIP, CEBAS) tem "
             "exigências próprias de prestação de contas, além da estatutária.",),
))

_reg(Ato(
    tipo=E.PARECER_CONSELHO_FISCAL.value,
    titulo="Parecer do Conselho Fiscal",
    categoria="PRESTAÇÃO DE CONTAS",
    descricao="Manifestação do órgão fiscalizador sobre as contas.",
    orgao_competente="CONSELHO_FISCAL",
    especie_assembleia=EspecieAssembleia.NAO_ASSEMBLEAR,
    chave_quorum=None,
    efeito_registral=EfeitoRegistral.INTERNO,
    documentos=(D.PARECER_CONSELHO_FISCAL.value, D.ATA.value),
    fundamentos=(("OSCIP_1999", "art. 4º"),),
    parametros_relevantes=("CONSELHO_FISCAL_EXISTE", "CONSELHO_FISCAL_PARECER_OBRIGATORIO"),
))

# ────────────────────────────────────────────────────────────── Encerramento

_reg(Ato(
    tipo=E.DISSOLUCAO.value,
    titulo="Dissolução",
    categoria="ENCERRAMENTO",
    descricao="Deliberação que põe fim à entidade e abre a liquidação.",
    especie_assembleia=EspecieAssembleia.EXTRAORDINARIA,
    exige_convocacao_especifica=True,
    chave_quorum="QUORUM_DISSOLUCAO",
    documentos=(*_ASSEMBLEAR, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 54"), ("CC_2002", "art. 61")),
    parametros_relevantes=("QUORUM_DISSOLUCAO", "DESTINACAO_PATRIMONIAL"),
    nota="As condições de dissolução devem constar do estatuto, sob pena de "
         "nulidade (art. 54, VI).",
    alertas=("A entidade só se extingue ao fim da liquidação: dissolver não é "
             "encerrar.",),
))

_reg(Ato(
    tipo=E.LIQUIDACAO.value,
    titulo="Liquidação",
    categoria="ENCERRAMENTO",
    descricao="Apuração do ativo, pagamento do passivo e apuração do remanescente.",
    orgao_competente="LIQUIDANTE",
    especie_assembleia=EspecieAssembleia.NAO_ASSEMBLEAR,
    chave_quorum=None,
    documentos=(D.ATA.value, D.DEMONSTRACOES_CONTABEIS.value, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 61"),),
))

_reg(Ato(
    tipo=E.DESTINACAO_PATRIMONIAL.value,
    titulo="Destinação do patrimônio",
    categoria="ENCERRAMENTO",
    descricao="Definição do destino do patrimônio remanescente.",
    especie_assembleia=EspecieAssembleia.EXTRAORDINARIA,
    chave_quorum="QUORUM_DISSOLUCAO",
    documentos=(*_ASSEMBLEAR, D.REQUERIMENTO_RCPJ.value),
    fundamentos=(("CC_2002", "art. 61"),),
    parametros_relevantes=("DESTINACAO_PATRIMONIAL",),
    nota="O remanescente é destinado à entidade de fins não econômicos designada "
         "no estatuto; sendo ele omisso, por deliberação dos associados, a "
         "instituição de fins idênticos ou semelhantes.",
))

_reg(Ato(
    tipo=E.ENCERRAMENTO.value,
    titulo="Encerramento e baixa",
    categoria="ENCERRAMENTO",
    descricao="Averbação da extinção no registro e baixa nos demais cadastros.",
    orgao_competente="LIQUIDANTE",
    especie_assembleia=EspecieAssembleia.NAO_ASSEMBLEAR,
    chave_quorum=None,
    documentos=(D.ATA.value, D.REQUERIMENTO_RCPJ.value, D.RELACAO_DOCUMENTOS.value),
    fundamentos=(("CC_2002", "art. 45"), ("LRP_1973", "art. 114")),
    alertas=("A baixa no CNPJ e nas inscrições municipais e estaduais é separada "
             "da averbação no RCPJ.",),
))


# ─────────────────────────────────────────────────────────────────── Consulta


def ato(tipo: str) -> Ato | None:
    return MATRIZ.get(tipo)


def por_categoria() -> dict[str, list[Ato]]:
    categorias: dict[str, list[Ato]] = {}
    for a in MATRIZ.values():
        categorias.setdefault(a.categoria, []).append(a)
    return categorias


def exige_reforma(tipo: str) -> str:
    a = MATRIZ.get(tipo)
    return a.exige_reforma_estatutaria if a else ExigeReforma.NUNCA


def chave_quorum(tipo: str) -> str | None:
    a = MATRIZ.get(tipo)
    return a.chave_quorum if a else "QUORUM_APROVACAO_GERAL"


def documentos_do_ato(tipo: str) -> tuple[str, ...]:
    a = MATRIZ.get(tipo)
    return a.documentos if a else (TipoDocumento.ATA.value,)
