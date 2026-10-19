"""Geração de documentos a partir de templates (§14, §15, §16, §53).

O princípio central do §53 vive aqui: **uma vez cadastrada, a informação não é
digitada de novo**. O dicionário de variáveis é montado do cadastro; o
questionário do evento só acrescenta o que é próprio daquele ato.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import unicodedata
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cifra import indice
from app.core.enums import CategoriaDocumento, StatusDocumento, TipoDocumento
from app.engines.conformidade.matriz import EspecieAssembleia, ato
from app.engines.templates.motor import renderizar
from app.engines.validacao.contexto import ContextoValidacao
from app.modules.documentos.models import Documento, DocumentoVersao, Template
from app.modules.entidades.models import Entidade
from app.modules.juridico.models import Evento
from app.modules.juridico.servicos import versao_vigente

CATEGORIA_POR_TIPO = {
    TipoDocumento.EDITAL_CONVOCACAO: CategoriaDocumento.EDITAL,
    TipoDocumento.AVISO_CONVOCACAO: CategoriaDocumento.EDITAL,
    TipoDocumento.ATA: CategoriaDocumento.ATA,
    TipoDocumento.LISTA_PRESENCA: CategoriaDocumento.ATA,
    TipoDocumento.TERMO_POSSE: CategoriaDocumento.TERMO,
    TipoDocumento.TERMO_ELEICAO: CategoriaDocumento.TERMO,
    TipoDocumento.TERMO_RENUNCIA: CategoriaDocumento.TERMO,
    TipoDocumento.TERMO_DESTITUICAO: CategoriaDocumento.TERMO,
    TipoDocumento.ESTATUTO_CONSOLIDADO: CategoriaDocumento.ESTATUTO,
    TipoDocumento.ALTERACAO_ESTATUTARIA: CategoriaDocumento.ESTATUTO,
    TipoDocumento.REQUERIMENTO_RCPJ: CategoriaDocumento.REGISTRO,
    TipoDocumento.CAPA_PROTOCOLO: CategoriaDocumento.PROTOCOLO,
    TipoDocumento.PARECER_CONSELHO_FISCAL: CategoriaDocumento.PARECER,
}


class ErroGeracao(Exception):
    """Um documento que não pôde ser montado — dito, e não gravado em branco."""

    def __init__(self, documento: str, motivo: str):
        super().__init__(f"{documento}: {motivo}")
        self.documento = documento
        self.motivo = motivo


def montar_variaveis(db: Session, evento: Evento, ctx: ContextoValidacao) -> dict:
    """O dicionário que alimenta os templates."""
    entidade: Entidade = db.get(Entidade, evento.entidade_id)
    versao = versao_vigente(db, entidade.id)
    mandato = ctx.mandato_vigente("DIRETORIA")

    variaveis: dict = {
        # Entidade
        "RAZAO_SOCIAL": entidade.razao_social,
        "NOME_FANTASIA": entidade.nome_fantasia,
        "CNPJ": entidade.cnpj,
        "TIPO_ENTIDADE": str(entidade.tipo_entidade),
        "ENDERECO": _endereco(entidade),
        "LOGRADOURO": entidade.logradouro,
        "NUMERO": entidade.numero,
        "COMPLEMENTO": entidade.complemento,
        "BAIRRO": entidade.bairro,
        "MUNICIPIO": entidade.municipio,
        "UF": entidade.uf,
        "CEP": entidade.cep,
        "EMAIL": entidade.email,
        "TELEFONE": entidade.telefone,
        # Estatuto
        "ESTATUTO_DATA": versao.data_estatuto if versao else None,
        "ESTATUTO_REGISTRO": versao.numero_registro if versao else None,
        "ESTATUTO_LIVRO": versao.livro if versao else None,
        "ESTATUTO_FOLHA": versao.folha if versao else None,
        # Registro
        "RCPJ": ctx.rcpj.nome if ctx.rcpj else None,
        # Ato — o título da matriz, não o código do enum: este texto vai
        # impresso no requerimento que chega ao balcão do cartório, e
        # "ALTERACAO_DENOMINACAO" numa peça jurídica é erro de acabamento.
        "TIPO_ATO": _titulo_do_ato(evento.tipo),
        "DATA_ATO": evento.data_referencia,
        "DATA_HOJE": dt.date.today(),
        # Governança
        "CONSELHO_FISCAL": _param_bool(ctx, "CONSELHO_FISCAL_EXISTE"),
        "MANDATO_DURACAO_MESES": _param_valor(ctx, "MANDATO_DURACAO_MESES"),
        "QUORUM_INSTALACAO_PRIMEIRA": _param_valor(ctx, "QUORUM_INSTALACAO_PRIMEIRA"),
        "QUORUM_INSTALACAO_SEGUNDA": _param_valor(ctx, "QUORUM_INSTALACAO_SEGUNDA"),
        "CONVOCACAO_PRAZO_DIAS": _param_valor(ctx, "CONVOCACAO_PRAZO_DIAS"),
        "TOTAL_ASSOCIADOS": ctx.total_associados or None,
        "TOTAL_APTOS": ctx.associados_aptos or None,
    }

    if mandato:
        variaveis.update({
            "MANDATO_DESIGNACAO": mandato.designacao,
            "MANDATO_INICIO": mandato.data_inicio,
            "MANDATO_FIM": mandato.data_fim,
            "DIRETORIA": [
                {"nome": m.nome, "cargo": m.cargo, "cargo_codigo": m.cargo_codigo}
                for m in mandato.membros
            ],
        })
        for membro in mandato.membros:
            if membro.cargo_codigo:
                variaveis[membro.cargo_codigo.upper()] = membro.nome

    # As respostas do questionário do evento têm precedência: são o que há de
    # específico naquele ato (§11).
    for chave, valor in (evento.dados or {}).items():
        variaveis[chave.upper()] = valor

    # §53 — o que o sistema consegue deduzir, ele não pergunta.
    variaveis.setdefault("TIPO_ASSEMBLEIA", _tipo_assembleia(evento, ctx))
    if variaveis.get("MOTIVO_VACANCIA") in MOTIVOS_VACANCIA:
        variaveis["MOTIVO_VACANCIA_TEXTO"] = MOTIVOS_VACANCIA[variaveis["MOTIVO_VACANCIA"]]
    if str(evento.tipo) == "ALTERACAO_CARGOS":
        anterior = variaveis.get("DIRETORIA") or []
        atualizada = aplicar_remanejamentos(anterior, variaveis.get("REMANEJAMENTOS") or [])
        variaveis["DIRETORIA_ATUALIZADA"] = atualizada
        variaveis["SAEM_DA_DIRETORIA"] = quem_sai(anterior, atualizada)
    if mandato:
        representante = mandato.ocupante("PRESIDENTE") or (
            mandato.membros[0] if mandato.membros else None
        )
        if representante:
            variaveis.setdefault("CARGO_REPRESENTANTE", representante.cargo)
            variaveis.setdefault("REPRESENTANTE", representante.nome)

    # Quem já está no cadastro entra completo nos documentos, sem redigitação.
    if variaveis.get("ELEITOS"):
        variaveis["ELEITOS"] = _completar_pessoas(db, entidade, variaveis["ELEITOS"])

    return {k: v for k, v in variaveis.items() if v is not None}


# Como o motivo entra no texto do termo. "OUTRO" fica de fora de propósito: o
# termo diz "cujo cargo vagou" sem inventar uma causa que ninguém informou.
MOTIVOS_VACANCIA = {
    "RENUNCIA": "renúncia",
    "DESTITUICAO": "destituição",
    "FALECIMENTO": "falecimento",
    "IMPEDIMENTO": "impedimento",
    "ABANDONO": "abandono",
    "PERDA_DE_REQUISITO": "perda de requisito estatutário",
}


def _chave_cargo(cargo: object) -> str:
    """Cargo comparável: sem acento, sem caixa, sem espaço sobrando.

    O remanejamento chega digitado ("vice-presidente", "Vice Presidente") e o
    quadro vem do cadastro ("Vice-Presidente"). Comparar o texto cru faria o
    mesmo cargo aparecer duas vezes na relação.
    """
    texto = unicodedata.normalize("NFD", str(cargo or ""))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.lower().replace("-", " ").split())


def aplicar_remanejamentos(diretoria: list, remanejamentos: list) -> list:
    """A diretoria como fica depois de uma alteração de cargos.

    A relação que vai ao cartório precisa ser a composição *inteira* após a
    mudança. Listar só quem mudou faria parecer que a diretoria é só aquilo.

    Regras, na ordem:
    - quem foi remanejado passa a ocupar o cargo indicado;
    - o cargo que essa pessoa deixou fica VAGO, a menos que outro
      remanejamento o preencha — o sistema não supõe quem assumiu;
    - cargo indicado que não existe no quadro entra ao final. Criar cargo é
      reforma estatutária, e o validador já cobra isso; aqui ele só aparece.

    Cada linha leva `alterado` para o documento distinguir o que mudou.
    """
    linhas = [
        {"cargo": m.get("cargo"), "nome": m.get("nome"), "alterado": False, "vago": False}
        for m in diretoria
        if isinstance(m, dict)
    ]
    por_cargo = {_chave_cargo(l["cargo"]): l for l in linhas}

    for r in remanejamentos:
        if not isinstance(r, dict) or not r.get("nome") or not r.get("cargo"):
            continue
        nome, destino = r["nome"], _chave_cargo(r["cargo"])

        # Sai do cargo que ocupava antes, se ocupava algum outro.
        for linha in linhas:
            if linha["nome"] == nome and _chave_cargo(linha["cargo"]) != destino:
                linha.update(nome=None, vago=True, alterado=True)

        if destino in por_cargo:
            por_cargo[destino].update(nome=nome, vago=False, alterado=True)
        else:
            nova = {"cargo": r["cargo"], "nome": nome, "alterado": True, "vago": False}
            linhas.append(nova)
            por_cargo[destino] = nova

    return linhas


def quem_sai(diretoria: list, linhas: list) -> list[dict]:
    """Quem estava na diretoria e não aparece mais na composição final.

    É consequência lógica — um cargo, um ocupante: quem foi deslocado e não
    recebeu outro cargo deixou a diretoria. Mas isso precisa estar escrito no
    documento. Sem esta lista a pessoa simplesmente sumia da relação, e quem
    conferisse não teria como notar que, talvez, alguém esqueceu de informar o
    novo cargo dela.
    """
    ficam = {l["nome"] for l in linhas if l.get("nome")}
    return [
        {"nome": m["nome"], "cargo": m.get("cargo")}
        for m in diretoria
        if isinstance(m, dict) and m.get("nome") and m["nome"] not in ficam
    ]


_ROTULO_ESPECIE = {
    EspecieAssembleia.ORDINARIA: "Ordinária",
    EspecieAssembleia.EXTRAORDINARIA: "Extraordinária",
}


def _tipo_assembleia(evento: Evento, ctx: ContextoValidacao) -> str | None:
    """Ordinária ou extraordinária — sem arbitrar o que é do estatuto.

    A matriz diz o que a lei fixa. Onde ela devolve a escolha ao estatuto
    (o caso da eleição, que pode ocorrer dentro da assembleia ordinária), o
    sistema pergunta ou deixa a variável em branco — nunca inventa a espécie,
    porque a espécie errada na ata é vício que o cartório enxerga.
    """
    informado = (evento.dados or {}).get("tipo_assembleia")
    if informado:
        return informado

    definicao = ato(str(evento.tipo))
    if definicao is None:
        return None
    if definicao.especie_assembleia in _ROTULO_ESPECIE:
        return _ROTULO_ESPECIE[definicao.especie_assembleia]
    if definicao.especie_assembleia == EspecieAssembleia.NAO_ASSEMBLEAR:
        return None

    # CONFORME_ESTATUTO: só responde se o parâmetro estiver confirmado.
    orgao = ctx.param("MANDATO_ORGAO_ELEITOR")
    if orgao.utilizavel and "ordin" in str(orgao.valor).lower():
        return "Ordinária"
    return None


def _completar_pessoas(db: Session, entidade: Entidade, pessoas: list) -> list:
    """Enriquece a lista de eleitos com o que já existe no cadastro de pessoas."""
    from app.modules.juridico.models import Pessoa

    completados = []
    for item in pessoas:
        if not isinstance(item, dict):
            completados.append(item)
            continue
        dados = dict(item)
        registro = None
        if dados.get("cpf"):
            registro = db.scalar(
                select(Pessoa).where(
                    Pessoa.cliente_id == entidade.cliente_id,
                    Pessoa.cpf_indice == indice(dados["cpf"]),
                )
            )
        if registro is None and dados.get("nome"):
            registro = db.scalar(
                select(Pessoa).where(
                    Pessoa.cliente_id == entidade.cliente_id, Pessoa.nome == dados["nome"]
                )
            )
        if registro is not None:
            # Preenche o que está ausente *ou vazio*. `setdefault` só cobria o
            # ausente — e o questionário manda "cpf": "" quando a pessoa é
            # digitada só pelo nome. A pessoa cadastrada com CPF saía sem CPF
            # na ata.
            def completar(chave, valor):
                if valor and not dados.get(chave):
                    dados[chave] = valor

            completar("cpf", registro.cpf)
            completar("rg", registro.rg)
            completar("qualificacao", registro.qualificacao)
            completar("endereco", ", ".join(
                p for p in (registro.logradouro, registro.numero, registro.bairro,
                            registro.municipio, registro.uf) if p
            ))
        completados.append(dados)
    return completados


def _endereco(e: Entidade) -> str | None:
    partes = [p for p in (e.logradouro, e.numero, e.complemento, e.bairro) if p]
    if not partes:
        return None
    linha = ", ".join(partes)
    if e.municipio and e.uf:
        linha += f", {e.municipio}/{e.uf}"
    if e.cep:
        linha += f", CEP {e.cep}"
    return linha


def _param_valor(ctx: ContextoValidacao, chave: str):
    p = ctx.param(chave)
    return p.valor if p.utilizavel else None


def _titulo_do_ato(tipo) -> str:
    """"ALTERACAO_DENOMINACAO" -> "Alteração de denominação".

    O parêntese que o catálogo usa para ajudar a achar o ato ("(mudança de
    nome)") não vai para a peça: ali ele é sinônimo de busca, não parte do
    nome do ato.
    """
    definicao = ato(str(tipo))
    if definicao is None:
        return str(tipo).replace("_", " ").capitalize()
    return re.sub(r"\s*\([^)]*\)\s*$", "", definicao.titulo)


def _param_bool(ctx: ContextoValidacao, chave: str) -> bool | None:
    p = ctx.param(chave)
    if not p.utilizavel:
        return None
    return p.valor in (True, "true", "SIM", "Sim", 1)


def selecionar_template(
    db: Session, tipo_documento: TipoDocumento, tipo_entidade: str, tipo_evento: str,
    cliente_id: uuid.UUID | None = None, uf: str | None = None,
) -> Template | None:
    """Escolhe o modelo mais específico disponível.

    Ordem de preferência: template do cliente > template da UF > template padrão;
    dentro disso, o que declara o tipo de entidade e o tipo de evento vence o genérico.
    """
    candidatos = db.scalars(
        select(Template).where(
            Template.tipo_documento == tipo_documento, Template.ativo.is_(True)
        )
    ).all()

    def pontuar(t: Template) -> tuple:
        return (
            2 if t.cliente_id == cliente_id and cliente_id else (0 if t.cliente_id else 1),
            1 if (t.uf and t.uf == uf) else 0,
            1 if tipo_entidade in (t.tipos_entidade or []) else 0,
            1 if tipo_evento in (t.tipos_evento or []) else 0,
            t.versao,
        )

    aplicaveis = [
        t for t in candidatos
        if (not t.tipos_entidade or tipo_entidade in t.tipos_entidade)
        and (not t.tipos_evento or tipo_evento in t.tipos_evento)
        and (t.cliente_id is None or t.cliente_id == cliente_id)
        and (t.uf is None or t.uf == uf)
    ]
    return max(aplicaveis, key=pontuar) if aplicaveis else None


def gerar_documento(
    db: Session,
    evento: Evento,
    ctx: ContextoValidacao,
    tipo_documento: TipoDocumento,
    usuario_id: uuid.UUID | None = None,
    motivo: str | None = None,
) -> tuple[Documento, DocumentoVersao] | None:
    """Gera (ou versiona) um documento do evento. §20: nunca sobrescreve."""
    entidade: Entidade = db.get(Entidade, evento.entidade_id)
    template = selecionar_template(
        db, tipo_documento, str(entidade.tipo_entidade), str(evento.tipo),
        cliente_id=entidade.cliente_id, uf=entidade.uf,
    )
    if template is None:
        return None

    variaveis = montar_variaveis(db, evento, ctx)
    resultado = renderizar(template.corpo, variaveis)
    if resultado.erro or not resultado.texto.strip():
        # Nunca gravar documento vazio como se fosse gerado. Foi o que
        # acontecia quando um modelo quebrava: a versão ia ao acervo em
        # branco, sem lacuna apontada, e o ato seguia como "gerado".
        raise ErroGeracao(template.nome, resultado.erro or "o modelo produziu um documento vazio")

    documento = db.scalar(
        select(Documento).where(
            Documento.evento_id == evento.id, Documento.tipo == tipo_documento
        )
    )
    if documento is None:
        documento = Documento(
            entidade_id=entidade.id,
            evento_id=evento.id,
            tipo=tipo_documento,
            categoria=CATEGORIA_POR_TIPO.get(tipo_documento, CategoriaDocumento.OUTRO),
            titulo=template.nome,
            data_documento=evento.data_referencia or dt.date.today(),
            status=StatusDocumento.GERADO,
            responsavel_id=usuario_id,
            template_codigo=template.codigo,
            origem="GERADO",
        )
        db.add(documento)
        db.flush()

    numero = (documento.versao_atual or 0) + 1
    versao = DocumentoVersao(
        documento_id=documento.id,
        numero=numero,
        conteudo=resultado.texto,
        formato="texto",
        hash_conteudo=hashlib.sha256(resultado.texto.encode("utf-8")).hexdigest(),
        template_id=template.id,
        dados_snapshot=_serializavel(variaveis),
        lacunas=resultado.lacunas,
        fundamentos=template.fundamentos or [],
        gerado_por_id=usuario_id,
        motivo=motivo or ("Geração inicial" if numero == 1 else "Nova geração após alteração"),
    )
    documento.versao_atual = numero
    documento.status = StatusDocumento.GERADO
    db.add_all([documento, versao])
    db.commit()
    db.refresh(documento)
    db.refresh(versao)
    return documento, versao


def _serializavel(dados: dict) -> dict:
    saida = {}
    for chave, valor in dados.items():
        if isinstance(valor, (dt.date, dt.datetime)):
            saida[chave] = valor.isoformat()
        elif isinstance(valor, (str, int, float, bool, list, dict)) or valor is None:
            saida[chave] = valor
        else:
            saida[chave] = str(valor)
    return saida
