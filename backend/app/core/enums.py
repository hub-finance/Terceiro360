"""Vocabulário controlado do TERCEIRO360.

Enums são declarados como `str, Enum` para trafegarem legíveis na API e no banco.
"""
from __future__ import annotations

from enum import Enum


class TextoEnum(str, Enum):
    """Enum de texto cujo `str()` devolve o valor, não `Classe.MEMBRO`.

    Isso importa: o valor viaja em JSON, entra em comparações com strings vindas
    do banco e é usado como chave de registro dos checks. `str(TipoEvento.X)`
    precisa dar `"X"`.
    """

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self.name}"


class Semaforo(TextoEnum):
    """§13 — Sistema de semáforo."""

    APTO = "APTO"                # 🟢
    PENDENCIA = "PENDENCIA"      # 🟡
    BLOQUEADO = "BLOQUEADO"      # 🔴

    @property
    def icone(self) -> str:
        return {"APTO": "🟢", "PENDENCIA": "🟡", "BLOQUEADO": "🔴"}[self.value]

    @property
    def peso(self) -> int:
        return {"APTO": 0, "PENDENCIA": 1, "BLOQUEADO": 2}[self.value]


class OrigemDado(TextoEnum):
    """§4 — de onde veio o parâmetro usado numa validação."""

    LEI = "LEI"
    ESTATUTO = "ESTATUTO"
    REGIMENTO = "REGIMENTO"
    RCPJ = "RCPJ"
    CADASTRO = "CADASTRO"
    INFORMADO = "INFORMADO"
    IA_SUGERIDO = "IA_SUGERIDO"


class StatusParametro(TextoEnum):
    """§46 — regra de não invenção."""

    CONFIRMADO = "CONFIRMADO"
    NAO_INFORMADO = "DADO_NAO_INFORMADO"
    VALIDACAO_NECESSARIA = "VALIDACAO_NECESSARIA"
    INCONSISTENCIA = "INCONSISTENCIA_IDENTIFICADA"


class TipoEntidade(TextoEnum):
    """§6 — classificação."""

    ASSOCIACAO = "ASSOCIACAO"
    FUNDACAO = "FUNDACAO"
    ORGANIZACAO_RELIGIOSA = "ORGANIZACAO_RELIGIOSA"
    IGREJA = "IGREJA"
    INSTITUTO = "INSTITUTO"
    OSC = "OSC"
    OSCIP = "OSCIP"
    ENTIDADE_FILANTROPICA = "ENTIDADE_FILANTROPICA"
    ENTIDADE_EDUCACIONAL = "ENTIDADE_EDUCACIONAL"
    ENTIDADE_ASSISTENCIAL = "ENTIDADE_ASSISTENCIAL"
    OUTRA = "OUTRA"


class TipoEvento(TextoEnum):
    """§10 — motor de eventos."""

    # Constituição
    CONSTITUICAO = "CONSTITUICAO"
    APROVACAO_ESTATUTO = "APROVACAO_ESTATUTO"
    REGISTRO_INICIAL = "REGISTRO_INICIAL"
    # Diretoria
    ELEICAO_DIRETORIA = "ELEICAO_DIRETORIA"
    REELEICAO_DIRETORIA = "REELEICAO_DIRETORIA"
    POSSE_DIRETORIA = "POSSE_DIRETORIA"
    RENUNCIA = "RENUNCIA"
    DESTITUICAO = "DESTITUICAO"
    SUBSTITUICAO = "SUBSTITUICAO"
    VACANCIA = "VACANCIA"
    ALTERACAO_CARGOS = "ALTERACAO_CARGOS"
    # Estatuto
    REFORMA_ESTATUTARIA = "REFORMA_ESTATUTARIA"
    ALTERACAO_FINALIDADE = "ALTERACAO_FINALIDADE"
    ALTERACAO_ENDERECO = "ALTERACAO_ENDERECO"
    ALTERACAO_DENOMINACAO = "ALTERACAO_DENOMINACAO"
    ALTERACAO_ORGAOS = "ALTERACAO_ORGAOS"
    ALTERACAO_MANDATO = "ALTERACAO_MANDATO"
    ALTERACAO_QUORUM = "ALTERACAO_QUORUM"
    # Assembleias
    ASSEMBLEIA_ORDINARIA = "ASSEMBLEIA_ORDINARIA"
    ASSEMBLEIA_EXTRAORDINARIA = "ASSEMBLEIA_EXTRAORDINARIA"
    # Prestação de contas (ato societário; a escrituração fica no módulo CONTÁBIL,
    # reservado — ver docs/reservado/modulo-contabil.md)
    APROVACAO_CONTAS = "APROVACAO_CONTAS"
    PRESTACAO_CONTAS = "PRESTACAO_CONTAS"
    PARECER_CONSELHO_FISCAL = "PARECER_CONSELHO_FISCAL"
    # Encerramento
    DISSOLUCAO = "DISSOLUCAO"
    LIQUIDACAO = "LIQUIDACAO"
    DESTINACAO_PATRIMONIAL = "DESTINACAO_PATRIMONIAL"
    ENCERRAMENTO = "ENCERRAMENTO"


class StatusEvento(TextoEnum):
    """§28 — ciclo de vida do ato."""

    RASCUNHO = "RASCUNHO"
    EM_VALIDACAO = "EM_VALIDACAO"
    GERADO = "GERADO"
    EM_REVISAO = "EM_REVISAO"
    REVISADO = "REVISADO"
    APROVADO = "APROVADO"
    ASSINADO = "ASSINADO"
    PROTOCOLADO = "PROTOCOLADO"
    EM_EXIGENCIA = "EM_EXIGENCIA"
    REGISTRADO = "REGISTRADO"
    ARQUIVADO = "ARQUIVADO"
    CANCELADO = "CANCELADO"


class TipoOrgao(TextoEnum):
    """§18 — mapa de governança."""

    SUPERIOR = "SUPERIOR"
    DELIBERATIVO = "DELIBERATIVO"
    EXECUTIVO = "EXECUTIVO"
    FISCALIZADOR = "FISCALIZADOR"
    CONSULTIVO = "CONSULTIVO"
    DEPARTAMENTO = "DEPARTAMENTO"
    MINISTERIO = "MINISTERIO"


class SituacaoMembro(TextoEnum):
    ATIVO = "ATIVO"
    RENUNCIANTE = "RENUNCIANTE"
    DESTITUIDO = "DESTITUIDO"
    SUBSTITUIDO = "SUBSTITUIDO"
    ENCERRADO = "ENCERRADO"


class SituacaoAssociado(TextoEnum):
    ATIVO = "ATIVO"
    SUSPENSO = "SUSPENSO"
    DESLIGADO = "DESLIGADO"
    LICENCIADO = "LICENCIADO"


class TipoAssembleia(TextoEnum):
    ORDINARIA = "ORDINARIA"
    EXTRAORDINARIA = "EXTRAORDINARIA"


class Convocacao(TextoEnum):
    PRIMEIRA = "PRIMEIRA"
    SEGUNDA = "SEGUNDA"


class TipoDocumento(TextoEnum):
    """§14 — gerador de documentos."""

    EDITAL_CONVOCACAO = "EDITAL_CONVOCACAO"
    AVISO_CONVOCACAO = "AVISO_CONVOCACAO"
    COMUNICACAO_MEMBROS = "COMUNICACAO_MEMBROS"
    ATA = "ATA"
    LISTA_PRESENCA = "LISTA_PRESENCA"
    RELACAO_VOTANTES = "RELACAO_VOTANTES"
    BOLETIM_VOTACAO = "BOLETIM_VOTACAO"
    TERMO_POSSE = "TERMO_POSSE"
    TERMO_ELEICAO = "TERMO_ELEICAO"
    TERMO_RENUNCIA = "TERMO_RENUNCIA"
    TERMO_DESTITUICAO = "TERMO_DESTITUICAO"
    TERMO_NOMEACAO = "TERMO_NOMEACAO"
    DECLARACAO_ACEITE = "DECLARACAO_ACEITE"
    ESTATUTO_CONSOLIDADO = "ESTATUTO_CONSOLIDADO"
    ALTERACAO_ESTATUTARIA = "ALTERACAO_ESTATUTARIA"
    QUADRO_COMPARATIVO = "QUADRO_COMPARATIVO"
    REQUERIMENTO_RCPJ = "REQUERIMENTO_RCPJ"
    CAPA_PROTOCOLO = "CAPA_PROTOCOLO"
    RELACAO_DOCUMENTOS = "RELACAO_DOCUMENTOS"
    CHECKLIST_REGISTRAL = "CHECKLIST_REGISTRAL"
    RELACAO_DIRETORIA = "RELACAO_DIRETORIA"
    PARECER_CONSELHO_FISCAL = "PARECER_CONSELHO_FISCAL"
    DEMONSTRACOES_CONTABEIS = "DEMONSTRACOES_CONTABEIS"
    OUTRO = "OUTRO"


class CategoriaDocumento(TextoEnum):
    """§19 — repositório documental."""

    ESTATUTO = "ESTATUTO"
    ATA = "ATA"
    EDITAL = "EDITAL"
    TERMO = "TERMO"
    CERTIDAO = "CERTIDAO"
    CNPJ = "CNPJ"
    DOCUMENTO_DIRIGENTE = "DOCUMENTO_DIRIGENTE"
    CONTABIL = "CONTABIL"
    DEMONSTRACAO = "DEMONSTRACAO"
    PARECER = "PARECER"
    REGISTRO = "REGISTRO"
    PROTOCOLO = "PROTOCOLO"
    COMPROVANTE = "COMPROVANTE"
    PROCURACAO = "PROCURACAO"
    JURIDICO = "JURIDICO"
    OUTRO = "OUTRO"


class StatusDocumento(TextoEnum):
    """§28 — GERADO → REVISADO → APROVADO → ASSINADO → PROTOCOLADO → REGISTRADO."""

    RASCUNHO = "RASCUNHO"
    GERADO = "GERADO"
    REVISADO = "REVISADO"
    APROVADO = "APROVADO"
    ASSINADO = "ASSINADO"
    PROTOCOLADO = "PROTOCOLADO"
    REGISTRADO = "REGISTRADO"
    ARQUIVADO = "ARQUIVADO"
    CANCELADO = "CANCELADO"


class TipoAssinatura(TextoEnum):
    FISICA = "FISICA"
    ELETRONICA = "ELETRONICA"
    ICP_BRASIL = "ICP_BRASIL"


class StatusAssinatura(TextoEnum):
    PENDENTE = "PENDENTE"
    ASSINADO = "ASSINADO"
    RECUSADO = "RECUSADO"
    CANCELADO = "CANCELADO"


class StatusProtocolo(TextoEnum):
    PREPARACAO = "PREPARACAO"
    PROTOCOLADO = "PROTOCOLADO"
    EM_EXIGENCIA = "EM_EXIGENCIA"
    REGISTRADO = "REGISTRADO"
    INDEFERIDO = "INDEFERIDO"
    DESISTENCIA = "DESISTENCIA"


class StatusParecer(TextoEnum):
    """§27 — módulo de advocacia."""

    EM_ANALISE = "EM_ANALISE"
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    APROVADO_COM_RESSALVAS = "APROVADO_COM_RESSALVAS"
    REPROVADO = "REPROVADO"
    NECESSITA_ALTERACAO = "NECESSITA_ALTERACAO"


class Prioridade(TextoEnum):
    """§43 — central de pendências."""

    URGENTE = "URGENTE"   # 🔴
    ALTA = "ALTA"         # 🟠
    MEDIA = "MEDIA"       # 🟡
    BAIXA = "BAIXA"       # 🟢


class StatusPendencia(TextoEnum):
    ABERTA = "ABERTA"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    RESOLVIDA = "RESOLVIDA"
    CANCELADA = "CANCELADA"


class TipoPrazo(TextoEnum):
    """§21 — módulo de prazos."""

    FIM_MANDATO = "FIM_MANDATO"
    ASSEMBLEIA_ANUAL = "ASSEMBLEIA_ANUAL"
    PRESTACAO_CONTAS = "PRESTACAO_CONTAS"
    RENOVACAO_DIRETORIA = "RENOVACAO_DIRETORIA"
    CONVOCACAO = "CONVOCACAO"
    CERTIDAO = "CERTIDAO"
    OBRIGACAO_ACESSORIA = "OBRIGACAO_ACESSORIA"
    PROTOCOLO = "PROTOCOLO"
    EXIGENCIA = "EXIGENCIA"
    OUTRO = "OUTRO"


class StatusPrazo(TextoEnum):
    ABERTO = "ABERTO"
    CUMPRIDO = "CUMPRIDO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"


class TipoFonte(TextoEnum):
    """§38 — central de fontes jurídicas."""

    LEI = "LEI"
    DECRETO = "DECRETO"
    NORMA_CONTABIL = "NORMA_CONTABIL"
    INSTRUCAO_NORMATIVA = "INSTRUCAO_NORMATIVA"
    REGRA_RCPJ = "REGRA_RCPJ"
    ESTATUTO = "ESTATUTO"
    REGIMENTO = "REGIMENTO"


class FuncaoEclesiastica(TextoEnum):
    """§17 — núcleo de igrejas."""

    PASTOR_PRESIDENTE = "PASTOR_PRESIDENTE"
    PASTOR = "PASTOR"
    MINISTRO = "MINISTRO"
    EVANGELISTA = "EVANGELISTA"
    PRESBITERO = "PRESBITERO"
    DIACONO = "DIACONO"
    MISSIONARIO = "MISSIONARIO"
    OBREIRO = "OBREIRO"


class TipoUnidadeEclesiastica(TextoEnum):
    DENOMINACAO = "DENOMINACAO"
    CONVENCAO = "CONVENCAO"
    IGREJA_SEDE = "IGREJA_SEDE"
    CONGREGACAO = "CONGREGACAO"
    CAMPO = "CAMPO"
    FILIAL = "FILIAL"
    TEMPLO = "TEMPLO"
    MINISTERIO = "MINISTERIO"


class Modulo(TextoEnum):
    """Módulos comerciais do TERCEIRO360.

    TERCEIRO360 CONTÁBIL está especificado e reservado para fase posterior
    (docs/reservado/modulo-contabil.md); por isso não figura aqui.
    """

    JURIDICO = "TERCEIRO360_JURIDICO"
    GOVERNANCA = "TERCEIRO360_GOVERNANCA"
    DOCUMENTOS = "TERCEIRO360_DOCUMENTOS"
    IGREJAS = "TERCEIRO360_IGREJAS"
    IA = "TERCEIRO360_IA"


class Plano(TextoEnum):
    """§45 — modelo de negócio. O plano CONTÁBIL entra com o módulo reservado."""

    BASICO = "BASICO"
    PROFISSIONAL = "PROFISSIONAL"
    ESCRITORIO = "ESCRITORIO"


class Jurisdicao(TextoEnum):
    """Alcance territorial/institucional de uma fonte normativa."""

    FEDERAL = "FEDERAL"
    ESTADUAL = "ESTADUAL"
    MUNICIPAL = "MUNICIPAL"
    CARTORARIA = "CARTORARIA"
    INTERNA = "INTERNA"


class SituacaoVersaoNorma(TextoEnum):
    """Ciclo de vida de uma versão de norma na Central de Fontes."""

    RASCUNHO = "RASCUNHO"
    EM_CURADORIA = "EM_CURADORIA"
    VIGENTE = "VIGENTE"
    SUPERADA = "SUPERADA"
    REVOGADA = "REVOGADA"


class OrigemDeteccao(TextoEnum):
    """Como uma possível mudança normativa chegou ao sistema."""

    MONITOR = "MONITOR"
    MANUAL = "MANUAL"
    IMPORTACAO = "IMPORTACAO"
    COMUNICADO_RCPJ = "COMUNICADO_RCPJ"


class SituacaoAtualizacao(TextoEnum):
    """§38/§46 — nenhuma atualização vale sem curadoria humana."""

    DETECTADA = "DETECTADA"
    EM_ANALISE = "EM_ANALISE"
    APROVADA = "APROVADA"
    PUBLICADA = "PUBLICADA"
    DESCARTADA = "DESCARTADA"


class AlvoImpacto(TextoEnum):
    """O que pode ser atingido por uma mudança normativa."""

    REGRA_VALIDACAO = "REGRA_VALIDACAO"
    TEMPLATE = "TEMPLATE"
    CHECKLIST = "CHECKLIST"
    PARAMETRO_ESTATUTARIO = "PARAMETRO_ESTATUTARIO"
    REGRA_RCPJ = "REGRA_RCPJ"
    EVENTO_EM_ANDAMENTO = "EVENTO_EM_ANDAMENTO"
    ENTIDADE = "ENTIDADE"


class SeveridadeImpacto(TextoEnum):
    INFORMATIVA = "INFORMATIVA"
    REVISAO_RECOMENDADA = "REVISAO_RECOMENDADA"
    REVISAO_OBRIGATORIA = "REVISAO_OBRIGATORIA"
    BLOQUEANTE = "BLOQUEANTE"
