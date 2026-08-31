"""CHECKLIST AUTOMÁTICO DE PROTOCOLO (§23).

O checklist é montado a partir de três origens declaradas — nunca de suposição:

    ATO (o que o próprio ato produz)  +  ESTATUTO  +  REGRA DO RCPJ COMPETENTE

Quando não há regra de RCPJ cadastrada, o checklist sai assim mesmo, mas
sinalizando que a parte cartorária não foi conferida (§46).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.enums import StatusParametro, TipoDocumento, TipoEvento
from app.engines.conformidade.matriz import ato, documentos_do_ato
from app.engines.validacao.contexto import ContextoValidacao


@dataclass
class ItemChecklist:
    codigo: str
    descricao: str
    obrigatorio: bool = True
    origem: str = "SISTEMA"          # ATO|ESTATUTO|RCPJ|LEI
    fundamento: str | None = None
    status: str = "PENDENTE"          # PENDENTE|OK|NAO_APLICAVEL
    observacao: str | None = None
    # Um mesmo documento costuma ser exigido por mais de uma fonte: a ata é
    # produzida pelo ato e também cobrada pelo cartório. Guardar todas as
    # origens evita que uma esconda a outra.
    origens: list[str] = field(default_factory=list)


@dataclass
class Checklist:
    tipo_evento: str
    itens: list[ItemChecklist] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def completo(self) -> bool:
        return all(i.status != "PENDENTE" for i in self.itens if i.obrigatorio)

    @property
    def pendentes(self) -> list[ItemChecklist]:
        return [i for i in self.itens if i.obrigatorio and i.status == "PENDENTE"]

    def to_dict(self) -> dict:
        return {
            "tipo_evento": self.tipo_evento,
            "completo": self.completo,
            "total": len(self.itens),
            "pendentes": len(self.pendentes),
            "avisos": self.avisos,
            "itens": [i.__dict__ for i in self.itens],
        }


# O que cada ato produz vem da matriz de atos: uma declaração só, lida por
# todo o sistema (§55).
DESCRICOES = {
    TipoDocumento.EDITAL_CONVOCACAO.value: "Edital de convocação",
    TipoDocumento.AVISO_CONVOCACAO.value: "Aviso de convocação",
    TipoDocumento.ATA.value: "Ata",
    TipoDocumento.LISTA_PRESENCA.value: "Lista de presença",
    TipoDocumento.TERMO_POSSE.value: "Termos de posse",
    TipoDocumento.TERMO_RENUNCIA.value: "Termo de renúncia",
    TipoDocumento.TERMO_DESTITUICAO.value: "Termo de destituição",
    TipoDocumento.RELACAO_DIRETORIA.value: "Relação da diretoria",
    TipoDocumento.ESTATUTO_CONSOLIDADO.value: "Estatuto consolidado",
    TipoDocumento.QUADRO_COMPARATIVO.value: "Quadro comparativo (redação anterior x aprovada)",
    TipoDocumento.REQUERIMENTO_RCPJ.value: "Requerimento ao RCPJ",
    TipoDocumento.RELACAO_DOCUMENTOS.value: "Relação de documentos",
    TipoDocumento.CAPA_PROTOCOLO.value: "Capa de protocolo",
    TipoDocumento.DEMONSTRACOES_CONTABEIS.value: "Demonstrações do exercício",
    TipoDocumento.PARECER_CONSELHO_FISCAL.value: "Parecer do Conselho Fiscal",
    TipoDocumento.BOLETIM_VOTACAO.value: "Boletim de votação",
}

# Documentos que instruem o ato mas não são obrigatórios em todo cartório.
OPCIONAIS = {
    TipoDocumento.QUADRO_COMPARATIVO.value,
    TipoDocumento.BOLETIM_VOTACAO.value,
    TipoDocumento.PARECER_CONSELHO_FISCAL.value,
}

# Documentos cujo nome só faz sentido junto do ato: "Ata" não diz nada,
# "Ata: Eleição de diretoria" diz. O checklist é lido por quem vai ao cartório.
QUALIFICADOS_PELO_ATO = {
    TipoDocumento.ATA.value,
    TipoDocumento.EDITAL_CONVOCACAO.value,
    TipoDocumento.REQUERIMENTO_RCPJ.value,
}


def descricao_documento(codigo: str, tipo_evento: str) -> str:
    base = DESCRICOES.get(codigo, codigo.replace("_", " ").capitalize())
    definicao = ato(tipo_evento)
    if definicao and codigo in QUALIFICADOS_PELO_ATO:
        return f"{base}: {definicao.titulo}"
    return base


def montar(ctx: ContextoValidacao) -> Checklist:
    checklist = Checklist(tipo_evento=ctx.tipo_evento)
    vistos: dict[str, ItemChecklist] = {}

    # Quando duas fontes pedem o mesmo documento, a exigência mais forte manda:
    # o cartório rejeita o protocolo, o estatuto vicia a deliberação.
    forca = {"SISTEMA": 0, "ATO": 1, "ESTATUTO": 2, "LEI": 3, "RCPJ": 4}

    def adicionar(codigo, descricao, obrigatorio, origem, fundamento=None, observacao=None):
        existente = vistos.get(codigo)
        if existente is not None:
            if origem not in existente.origens:
                existente.origens.append(origem)
            if forca.get(origem, 0) > forca.get(existente.origem, 0):
                existente.origem = origem
                existente.fundamento = fundamento or existente.fundamento
            existente.obrigatorio = existente.obrigatorio or obrigatorio
            existente.observacao = existente.observacao or observacao
            return
        item = ItemChecklist(
            codigo=codigo,
            descricao=descricao,
            obrigatorio=obrigatorio,
            origem=origem,
            origens=[origem],
            fundamento=fundamento,
            status="OK" if codigo in ctx.documentos_anexados else "PENDENTE",
            observacao=observacao,
        )
        vistos[codigo] = item
        checklist.itens.append(item)

    # 1. O que o ato produz, conforme a matriz.
    for codigo in documentos_do_ato(ctx.tipo_evento):
        adicionar(
            codigo,
            descricao_documento(codigo, ctx.tipo_evento),
            codigo not in OPCIONAIS,
            "ATO",
        )

    # 2. Estatuto vigente sempre acompanha o protocolo.
    adicionar(
        "ESTATUTO_VIGENTE", "Cópia do estatuto vigente registrado", True, "ATO",
        fundamento="Documento de instrução usual do protocolo registral",
    )

    # 3. Exigências estatutárias específicas.
    parecer = ctx.param("CONSELHO_FISCAL_PARECER_OBRIGATORIO")
    if parecer.utilizavel and parecer.valor in (True, "true", "SIM", 1) and ctx.tipo_evento in (
        TipoEvento.APROVACAO_CONTAS.value, TipoEvento.PRESTACAO_CONTAS.value
    ):
        adicionar(
            TipoDocumento.PARECER_CONSELHO_FISCAL.value,
            "Parecer do Conselho Fiscal (exigido pelo estatuto)", True, "ESTATUTO",
            fundamento=str(parecer.fundamento) if parecer.fundamento else "Estatuto Social",
        )
    elif parecer.status is StatusParametro.NAO_INFORMADO and ctx.tipo_evento in (
        TipoEvento.APROVACAO_CONTAS.value, TipoEvento.PRESTACAO_CONTAS.value
    ):
        checklist.avisos.append(
            "Não está cadastrado se o estatuto exige parecer do Conselho Fiscal para aprovar "
            "as contas. Confirme antes de protocolar."
        )

    # 4. Exigências do RCPJ competente.
    if ctx.rcpj is None:
        checklist.avisos.append(
            "RCPJ competente não definido: as exigências cartorárias não foram conferidas. "
            "Este checklist cobre apenas os documentos produzidos pelo próprio ato."
        )
        return checklist

    regra = ctx.rcpj.regra_evento
    if regra is None:
        checklist.avisos.append(
            f"Não há exigências cadastradas no {ctx.rcpj.nome} para este ato. "
            f"Confirme a lista junto ao cartório antes do protocolo."
        )
        return checklist

    for doc in regra.documentos_exigidos:
        adicionar(
            doc.get("codigo", doc.get("descricao", "DOC")),
            doc.get("descricao", "Documento exigido pelo cartório"),
            doc.get("obrigatorio", True),
            "RCPJ",
            fundamento=f"{ctx.rcpj.nome}"
                       + (f" — conferido em {regra.data_ultima_verificacao:%d/%m/%Y}"
                          if regra.data_ultima_verificacao else ""),
            observacao=doc.get("observacao"),
        )

    exige_firma = (
        regra.exige_reconhecimento_firma
        if regra.exige_reconhecimento_firma is not None
        else ctx.rcpj.exige_reconhecimento_firma
    )
    if exige_firma:
        adicionar("RECONHECIMENTO_FIRMA", "Reconhecimento de firma nas assinaturas exigidas",
                  True, "RCPJ", fundamento=ctx.rcpj.nome)
    elif exige_firma is None:
        checklist.avisos.append("Reconhecimento de firma: exigência não conferida neste cartório.")

    exige_advogado = (
        regra.exige_visto_advogado
        if regra.exige_visto_advogado is not None
        else ctx.rcpj.exige_visto_advogado
    )
    if exige_advogado:
        adicionar("VISTO_ADVOGADO", "Visto de advogado com número de inscrição na OAB",
                  True, "RCPJ", fundamento=ctx.rcpj.nome)
    elif exige_advogado is None:
        checklist.avisos.append("Visto de advogado: exigência não conferida neste cartório.")

    if regra.vias and regra.vias > 1:
        checklist.avisos.append(f"Protocolo em {regra.vias} vias, conforme cadastro do cartório.")

    if ctx.rcpj.regras_desatualizadas:
        checklist.avisos.append(
            "As exigências deste cartório estão fora do prazo de reconferência. "
            "Trate o checklist como provisório."
        )
    return checklist
