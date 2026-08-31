"""Carga inicial do TERCEIRO360.

Popula o que o sistema precisa para funcionar já na primeira execução:
perfis, base normativa, vínculos, vigílias, modelos de documento. Opcionalmente
cria uma entidade de demonstração para percorrer o fluxo do §49 de ponta a ponta.

Idempotente: rodar duas vezes não duplica nada.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tempo import agora
from app.core.enums import (
    AlvoImpacto,
    OrigemDado,
    OrigemDeteccao,
    Plano,
    SituacaoVersaoNorma,
    TipoDocumento,
    TipoEntidade,
    TipoEvento,
    TipoOrgao,
)
from app.core.security import PERFIS_PADRAO, hash_senha
from app.engines.normativo.coletor import impressao_digital
from app.engines.templates.motor import variaveis_do_template
from app.modules.documentos.models import Template
from app.modules.entidades.models import Entidade, NaturezaJuridica
from app.modules.identity.models import Cliente, Perfil, Usuario, UsuarioPerfil
from app.modules.juridico.models import (
    Associado,
    Cargo,
    Estatuto,
    EstatutoParametro,
    EstatutoVersao,
    Mandato,
    MandatoMembro,
    Orgao,
    Pessoa,
)
from app.modules.normativo.models import (
    Dispositivo,
    FonteJuridica,
    FonteVersao,
    MonitoramentoNormativo,
    VinculoNormativo,
)
from app.modules.registral.models import RCPJ, RegraRCPJ
from app.seeds.fontes import FONTES
from app.seeds.templates import TEMPLATES

# Naturezas jurídicas sem fins lucrativos mais usadas no Terceiro Setor.
NATUREZAS = (
    ("306-9", "Fundação Privada"),
    ("307-7", "Serviço Social Autônomo"),
    ("322-0", "Organização Religiosa"),
    ("330-1", "Organização Social (OS)"),
    ("399-9", "Associação Privada"),
)

# §38 — o que cada regra e cada modelo usa como fundamento. É este mapa que
# permite responder, quando uma lei muda: o que exatamente parou de valer?
VINCULOS = (
    (AlvoImpacto.REGRA_VALIDACAO, "CONVOCACAO_PRAZO", "CC_2002", "art. 60"),
    (AlvoImpacto.REGRA_VALIDACAO, "CONVOCACAO_LEGITIMIDADE", "CC_2002", "art. 60"),
    (AlvoImpacto.REGRA_VALIDACAO, "COMPETENCIA_ORGAO", "CC_2002", "art. 59"),
    (AlvoImpacto.REGRA_VALIDACAO, "QUORUM_DELIBERACAO", "CC_2002", "art. 59"),
    (AlvoImpacto.REGRA_VALIDACAO, "ESTATUTO_VIGENTE", "CC_2002", "art. 54"),
    (AlvoImpacto.REGRA_VALIDACAO, "DOCUMENTOS_PRESTACAO_CONTAS", "CC_2002", "art. 54"),
    (AlvoImpacto.REGRA_VALIDACAO, "RCPJ_COMPETENTE", "LRP_1973", "art. 114"),
    (AlvoImpacto.PARAMETRO_ESTATUTARIO, "DESTINACAO_PATRIMONIAL", "CC_2002", "art. 61"),
    (AlvoImpacto.PARAMETRO_ESTATUTARIO, "CONVOCACAO_FRACAO_ASSOCIADOS", "CC_2002", "art. 60"),
    (AlvoImpacto.TEMPLATE, "EDITAL_PADRAO", "CC_2002", "art. 60"),
    (AlvoImpacto.TEMPLATE, "ATA_ELEICAO_PADRAO", "CC_2002", "art. 59"),
    (AlvoImpacto.TEMPLATE, "ATA_REFORMA_PADRAO", "CC_2002", "art. 59"),
    (AlvoImpacto.TEMPLATE, "REQUERIMENTO_PADRAO", "LRP_1973", "art. 120"),
    (AlvoImpacto.TEMPLATE, "REQUERIMENTO_PADRAO", "LRP_1973", "art. 121"),
    (AlvoImpacto.CHECKLIST, "VISTO_ADVOGADO", "EOAB_1994", "art. 1º, §2º"),
)


def popular(db: Session, com_demonstracao: bool = False) -> dict:
    resumo = {
        "perfis": _perfis(db),
        "naturezas": _naturezas(db),
        "fontes": _fontes(db),
        "vinculos": _vinculos(db),
        "monitoramentos": _monitoramentos(db),
        "templates": _templates(db),
    }
    if com_demonstracao:
        resumo["demonstracao"] = _demonstracao(db)
    db.commit()
    return resumo


# ------------------------------------------------------------------ Perfis


def _perfis(db: Session) -> int:
    criados = 0
    for codigo, dados in PERFIS_PADRAO.items():
        existente = db.scalar(
            select(Perfil).where(Perfil.cliente_id.is_(None), Perfil.codigo == codigo)
        )
        if existente:
            existente.permissoes = dados["permissoes"]
            db.add(existente)
            continue
        db.add(Perfil(
            cliente_id=None,
            codigo=codigo,
            nome=dados["nome"],
            permissoes=dados["permissoes"],
            exige_habilitacao_profissional=dados["exige_habilitacao"],
        ))
        criados += 1
    db.flush()
    return criados


def _naturezas(db: Session) -> int:
    criadas = 0
    vistos: set[str] = set()
    for codigo, descricao in NATUREZAS:
        if codigo in vistos:
            continue
        vistos.add(codigo)
        if db.scalar(select(NaturezaJuridica).where(NaturezaJuridica.codigo == codigo)):
            continue
        db.add(NaturezaJuridica(codigo=codigo, descricao=descricao))
        criadas += 1
    db.flush()
    return criadas


# ------------------------------------------------------- Base normativa


def _fontes(db: Session) -> int:
    """Carrega a base legal de trabalho.

    As versões entram VIGENTES — as leis estão de fato em vigor — mas **sem
    curador**. A API expõe `curada: false` até que um responsável habilitado
    confira cada redação (§46). Nada aqui finge conferência humana.
    """
    criadas = 0
    for seed in FONTES:
        fonte = db.scalar(select(FonteJuridica).where(FonteJuridica.chave == seed.chave))
        if fonte is None:
            fonte = FonteJuridica(
                chave=seed.chave,
                identificacao=seed.identificacao,
                apelido=seed.apelido,
                tipo=seed.tipo,
                jurisdicao=seed.jurisdicao,
                orgao_emissor=seed.orgao_emissor,
                url_oficial=seed.url_oficial,
                ementa=seed.ementa,
            )
            db.add(fonte)
            db.flush()
            criadas += 1

        if fonte.versoes:
            continue

        texto = "\n\n".join(f"{d.identificacao} — {d.sintese}" for d in seed.dispositivos)
        versao = FonteVersao(
            fonte_id=fonte.id,
            numero_versao=1,
            situacao=SituacaoVersaoNorma.VIGENTE,
            vigente_desde=seed.vigente_desde,
            resumo_alteracao="Carga inicial da base normativa. Redação pendente de "
                             "conferência por responsável habilitado.",
            texto_referencia=texto,
            url_captura=seed.url_oficial,
            hash_conteudo=impressao_digital(texto),
            origem_captura=OrigemDeteccao.MANUAL,
            # curado_por_id permanece nulo: a curadoria é ato humano (§46).
        )
        db.add(versao)
        db.flush()
        for d in seed.dispositivos:
            db.add(Dispositivo(
                versao_id=versao.id,
                identificacao=d.identificacao,
                texto=d.sintese,
                tags=list(d.tags),
            ))
    db.flush()
    return criadas


def _vinculos(db: Session) -> int:
    criados = 0
    for alvo_tipo, alvo_ref, fonte_chave, dispositivo in VINCULOS:
        existente = db.scalar(
            select(VinculoNormativo).where(
                VinculoNormativo.alvo_tipo == alvo_tipo,
                VinculoNormativo.alvo_ref == alvo_ref,
                VinculoNormativo.fonte_chave == fonte_chave,
                VinculoNormativo.dispositivo == dispositivo,
            )
        )
        if existente:
            continue
        db.add(VinculoNormativo(
            alvo_tipo=alvo_tipo, alvo_ref=alvo_ref,
            fonte_chave=fonte_chave, dispositivo=dispositivo,
        ))
        criados += 1
    db.flush()
    return criados


def _monitoramentos(db: Session) -> int:
    """Uma vigília por fonte federal, apontando para o texto compilado oficial."""
    criados = 0
    for seed in FONTES:
        fonte = db.scalar(select(FonteJuridica).where(FonteJuridica.chave == seed.chave))
        if fonte is None:
            continue
        if db.scalar(
            select(MonitoramentoNormativo).where(MonitoramentoNormativo.fonte_id == fonte.id)
        ):
            continue
        db.add(MonitoramentoNormativo(
            fonte_id=fonte.id,
            nome=f"{seed.apelido} — texto compilado oficial",
            url=seed.url_oficial,
            modo="HTTP" if seed.url_oficial else "MANUAL",
            periodicidade_dias=90,
        ))
        criados += 1
    db.flush()
    return criados


def _templates(db: Session) -> int:
    criados = 0
    for seed in TEMPLATES:
        if db.scalar(
            select(Template).where(Template.cliente_id.is_(None), Template.codigo == seed.codigo)
        ):
            continue
        db.add(Template(
            cliente_id=None,
            codigo=seed.codigo,
            nome=seed.nome,
            tipo_documento=seed.tipo_documento,
            corpo=seed.corpo,
            tipos_entidade=list(seed.tipos_entidade),
            tipos_evento=list(seed.tipos_evento),
            variaveis=variaveis_do_template(seed.corpo),
            fundamentos=list(seed.fundamentos),
            versao=1,
        ))
        criados += 1
    db.flush()
    return criados


# ------------------------------------------------------------ Demonstração


def _demonstracao(db: Session) -> dict:
    """Cria um cenário navegável: escritório, entidade, estatuto, diretoria.

    Todos os dados são fictícios e assim identificados.
    """
    if db.scalar(select(Cliente).where(Cliente.nome == "Escritório Demonstração")):
        return {"situacao": "já existia"}

    cliente = Cliente(
        nome="Escritório Demonstração",
        plano=Plano.ESCRITORIO,
        limite_entidades=50,
    )
    db.add(cliente)
    db.flush()

    admin = Usuario(
        cliente_id=cliente.id,
        nome="Administrador de Demonstração",
        email="admin@demo.terceiro360.local",
        senha_hash=hash_senha("terceiro360"),
        registro_profissional="OAB/MG 000.000",
        uf_registro="MG",
    )
    db.add(admin)
    db.flush()

    perfil_admin = db.scalar(
        select(Perfil).where(Perfil.cliente_id.is_(None), Perfil.codigo == "ADMINISTRADOR")
    )
    db.add(UsuarioPerfil(usuario_id=admin.id, perfil_id=perfil_admin.id))

    rcpj = RCPJ(
        uf="MG",
        municipio="Belo Horizonte",
        nome="Registro Civil das Pessoas Jurídicas de Belo Horizonte (exemplo)",
        forma_protocolo="presencial",
        formatos_aceitos=["papel"],
        observacoes="Cadastro de demonstração. Antes de qualquer protocolo real, confirme "
                    "as exigências diretamente com o cartório competente.",
        fonte_informacao="Cadastro de demonstração — não conferido junto ao cartório.",
        data_ultima_verificacao=dt.date.today(),
    )
    db.add(rcpj)
    db.flush()

    db.add(RegraRCPJ(
        rcpj_id=rcpj.id,
        tipo_evento=TipoEvento.ELEICAO_DIRETORIA.value,
        documentos_exigidos=[
            {"codigo": "EDITAL_CONVOCACAO", "descricao": "Edital de convocação",
             "obrigatorio": True},
            {"codigo": "ATA", "descricao": "Ata da assembleia", "obrigatorio": True},
            {"codigo": "LISTA_PRESENCA", "descricao": "Lista de presença", "obrigatorio": True},
            {"codigo": "TERMO_POSSE", "descricao": "Termos de posse", "obrigatorio": True},
            {"codigo": "REQUERIMENTO_RCPJ", "descricao": "Requerimento", "obrigatorio": True},
        ],
        vias=2,
        observacoes="Exigências de demonstração, não conferidas junto ao cartório.",
        fonte_informacao="Cadastro de demonstração.",
        data_ultima_verificacao=dt.date.today(),
    ))

    entidade = Entidade(
        cliente_id=cliente.id,
        razao_social="Associação Comunitária Novo Horizonte (demonstração)",
        nome_fantasia="ACNH",
        cnpj="12.345.678/0001-90",
        tipo_entidade=TipoEntidade.ASSOCIACAO,
        data_constituicao=dt.date(2015, 3, 10),
        logradouro="Rua das Acácias",
        numero="120",
        bairro="Centro",
        municipio="Belo Horizonte",
        uf="MG",
        cep="30110-000",
        email="contato@acnh.demo",
        situacao_cadastral="ATIVA",
        rcpj_id=rcpj.id,
    )
    db.add(entidade)
    db.flush()

    estatuto = Estatuto(entidade_id=entidade.id)
    db.add(estatuto)
    db.flush()
    versao = EstatutoVersao(
        estatuto_id=estatuto.id,
        numero_versao=1,
        data_estatuto=dt.date(2021, 5, 12),
        data_registro=dt.date(2021, 6, 2),
        numero_registro="123456",
        livro="A-15",
        folha="220",
        rcpj_id=rcpj.id,
        municipio="Belo Horizonte",
        uf="MG",
        vigente=True,
    )
    db.add(versao)
    db.flush()
    estatuto.versao_vigente_id = versao.id
    db.add(estatuto)

    parametros = [
        ("MANDATO_DURACAO_MESES", "24", "inteiro", "meses", "art. 18"),
        ("MANDATO_PERMITE_REELEICAO", "SIM", "booleano", None, "art. 18, §1º"),
        ("CONVOCACAO_PRAZO_DIAS", "15", "inteiro", "dias", "art. 21"),
        ("CONVOCACAO_LEGITIMADOS", "Presidente;Diretoria;1/5 dos associados", "lista", None,
         "art. 21"),
        ("CONVOCACAO_MEIO", "Edital afixado na sede;E-mail", "lista", None, "art. 21"),
        ("QUORUM_INSTALACAO_PRIMEIRA", "metade mais um dos associados", "texto", None, "art. 22"),
        ("QUORUM_INSTALACAO_SEGUNDA", "qualquer número", "texto", None, "art. 22, p. único"),
        ("QUORUM_APROVACAO_GERAL", "maioria simples dos presentes", "texto", None, "art. 23"),
        ("QUORUM_REFORMA_ESTATUTARIA", "dois terços dos presentes", "texto", None, "art. 30"),
        ("QUORUM_DESTITUICAO", "dois terços dos presentes", "texto", None, "art. 31"),
        ("CONSELHO_FISCAL_EXISTE", "SIM", "booleano", None, "art. 25"),
        ("CONSELHO_FISCAL_PARECER_OBRIGATORIO", "SIM", "booleano", None, "art. 26"),
        ("AGO_PERIODICIDADE_MESES", "12", "inteiro", "meses", "art. 20"),
        ("AGO_PRAZO_APROVACAO_CONTAS", "até 30 de abril", "texto", None, "art. 20, §1º"),
        ("DESTINACAO_PATRIMONIAL",
         "Entidade congênere sem fins lucrativos designada pela Assembleia Geral",
         "texto", None, "art. 40"),
    ]
    momento = agora()
    for chave, valor, tipo, unidade, dispositivo in parametros:
        db.add(EstatutoParametro(
            versao_id=versao.id, chave=chave, valor=valor, tipo_valor=tipo, unidade=unidade,
            dispositivo=dispositivo, origem=OrigemDado.ESTATUTO,
            confirmado=True, confirmado_por_id=admin.id, confirmado_em=momento,
        ))

    diretoria = Orgao(
        entidade_id=entidade.id, nome="Diretoria", codigo="DIRETORIA",
        tipo=TipoOrgao.EXECUTIVO, dispositivo_estatutario="art. 15",
    )
    assembleia = Orgao(
        entidade_id=entidade.id, nome="Assembleia Geral", codigo="ASSEMBLEIA_GERAL",
        tipo=TipoOrgao.SUPERIOR, dispositivo_estatutario="art. 12",
    )
    conselho = Orgao(
        entidade_id=entidade.id, nome="Conselho Fiscal", codigo="CONSELHO_FISCAL",
        tipo=TipoOrgao.FISCALIZADOR, dispositivo_estatutario="art. 25",
    )
    db.add_all([assembleia, diretoria, conselho])
    db.flush()
    diretoria.orgao_pai_id = assembleia.id
    conselho.orgao_pai_id = assembleia.id
    db.add_all([diretoria, conselho])

    cargos = {}
    for ordem, (nome, codigo) in enumerate(
        [("Presidente", "PRESIDENTE"), ("Vice-Presidente", "VICE_PRESIDENTE"),
         ("Secretário", "SECRETARIO"), ("Tesoureiro", "TESOUREIRO")], start=1
    ):
        cargo = Cargo(orgao_id=diretoria.id, nome=nome, codigo=codigo, ordem=ordem)
        db.add(cargo)
        cargos[codigo] = cargo
    db.flush()

    pessoas = {}
    for nome, cpf, codigo in [
        ("Maria Aparecida Souza", "111.111.111-11", "PRESIDENTE"),
        ("João Carlos Lima", "222.222.222-22", "VICE_PRESIDENTE"),
        ("Ana Paula Ferreira", "333.333.333-33", "SECRETARIO"),
        ("Roberto Dias Menezes", "444.444.444-44", "TESOUREIRO"),
    ]:
        pessoa = Pessoa(
            cliente_id=cliente.id, nome=nome, cpf=cpf, nacionalidade="brasileira",
            estado_civil="casado(a)", profissao="administrador(a)",
            municipio="Belo Horizonte", uf="MG",
            base_legal_tratamento="EXERCICIO_REGULAR_DE_DIREITOS",
        )
        db.add(pessoa)
        pessoas[codigo] = pessoa
    db.flush()

    hoje = dt.date.today()
    mandato = Mandato(
        entidade_id=entidade.id, orgao_id=diretoria.id,
        designacao=f"GESTÃO {hoje.year - 1}–{hoje.year + 1}",
        data_inicio=dt.date(hoje.year - 1, 7, 1),
        data_fim=dt.date(hoje.year + 1, 6, 30),
    )
    db.add(mandato)
    db.flush()
    for codigo, pessoa in pessoas.items():
        db.add(MandatoMembro(
            mandato_id=mandato.id, pessoa_id=pessoa.id, cargo_id=cargos[codigo].id,
            data_inicio=mandato.data_inicio, data_fim=mandato.data_fim,
        ))

    for i in range(1, 41):
        associado_pessoa = Pessoa(
            cliente_id=cliente.id, nome=f"Associado Demonstração {i:02d}",
            cpf=f"{i:03d}.000.000-{i:02d}", municipio="Belo Horizonte", uf="MG",
        )
        db.add(associado_pessoa)
        db.flush()
        db.add(Associado(
            entidade_id=entidade.id, pessoa_id=associado_pessoa.id, categoria="efetivo",
            data_admissao=dt.date(2020, 1, 15), direito_voto=True, elegivel=True,
        ))

    db.flush()
    return {
        "cliente": str(cliente.id),
        "entidade": str(entidade.id),
        "usuario": admin.email,
        "senha": "terceiro360",
        "aviso": "Dados fictícios, para demonstração e testes.",
    }
