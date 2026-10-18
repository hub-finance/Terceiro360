"""Cópia de segurança do escritório, baixada pelo próprio usuário.

O banco no Supabase já é a cópia primária. Esta é a outra: um arquivo fora do
sistema, que sobrevive mesmo que a conta, o provedor ou o próprio sistema
deixem de existir. Por isso três decisões que não são óbvias:

**Os dados pessoais saem decifrados.** CPF e RG são guardados cifrados com
`T360_CHAVE_DADOS`. Uma cópia que dependesse dessa chave não protegeria contra
o cenário em que ela se perde — que é justamente um dos que a cópia existe para
cobrir. O preço é que o arquivo é sensível, e a tela diz isso com todas as
letras; e cada exportação fica registrada, com quem e quando (LGPD, art. 37).

**Segredos de acesso nunca saem.** Hash de senha, segredo do segundo fator,
códigos de recuperação, índice cego do CPF. Nenhum serve para restaurar dados,
e todos servem para atacar.

**Cada tabela tem que estar classificada.** `ESCOPO` diz como cada tabela do
escritório se liga a ele; `GLOBAIS` lista as que são do sistema. Um teste
exige que as duas listas cubram o banco inteiro: tabela nova que ninguém
classificou derruba a suíte, em vez de ficar fora da cópia em silêncio — ou de
vazar dado de outro escritório.
"""
from __future__ import annotations

import base64
import datetime as dt
import decimal
import enum
import hashlib
import io
import json
import re
import unicodedata
import uuid
import zipfile

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.tempo import agora
from app.models import Base as _ModelosBase  # noqa: F401  (registra as tabelas)

FORMATO_VERSAO = 1

# Ordem importa: uma tabela filha só pode ser lida depois do seu pai, porque é
# dos ids exportados do pai que ela tira o próprio filtro.
#
#   ("proprio",)                o registro do próprio escritório
#   ("cliente",)                coluna cliente_id
#   ("entidade",)               coluna entidade_id, nas entidades do escritório
#   ("pai", coluna, tabela)     coluna aponta para linha já exportada de `tabela`
#   ("entidade_ou_usuario",)    entidade do escritório, ou feito por usuário dele —
#                               registros de acesso e auditoria podem não ter entidade
ESCOPO: list[tuple[str, tuple]] = [
    ("clientes", ("proprio",)),
    ("entidades", ("cliente",)),
    ("usuarios", ("cliente",)),
    ("pessoas", ("cliente",)),
    # Perfis e modelos com cliente_id nulo são os padrão do sistema: o filtro
    # por cliente já os deixa de fora, e só os personalizados entram.
    ("perfis", ("cliente",)),
    ("templates", ("cliente",)),
    ("configuracoes_score", ("cliente",)),
    # Permissão por entidade pode ter a entidade vazia (vale para o escritório
    # todo); o vínculo seguro é o usuário.
    ("usuario_perfis", ("pai", "usuario_id", "usuarios")),
    ("orgaos", ("entidade",)),
    ("cargos", ("pai", "orgao_id", "orgaos")),
    ("mandatos", ("entidade",)),
    ("mandato_membros", ("pai", "mandato_id", "mandatos")),
    ("associados", ("entidade",)),
    ("estatutos", ("entidade",)),
    ("estatuto_versoes", ("pai", "estatuto_id", "estatutos")),
    ("estatuto_parametros", ("pai", "versao_id", "estatuto_versoes")),
    ("eventos", ("entidade",)),
    ("assembleias", ("entidade",)),
    ("convocacoes", ("pai", "assembleia_id", "assembleias")),
    ("deliberacoes", ("pai", "assembleia_id", "assembleias")),
    ("listas_presenca", ("pai", "assembleia_id", "assembleias")),
    ("documentos", ("entidade",)),
    ("documento_versoes", ("pai", "documento_id", "documentos")),
    ("assinaturas", ("pai", "documento_id", "documentos")),
    ("pareceres_juridicos", ("pai", "evento_id", "eventos")),
    ("checklists", ("pai", "evento_id", "eventos")),
    ("checklist_itens", ("pai", "checklist_id", "checklists")),
    ("protocolos", ("entidade",)),
    ("prazos", ("entidade",)),
    ("pendencias", ("entidade",)),
    ("certidoes", ("entidade",)),
    ("notificacoes", ("entidade",)),
    ("linha_tempo", ("entidade",)),
    ("score_snapshots", ("entidade",)),
    ("impactos_normativos", ("entidade",)),
    ("analises_ia", ("entidade",)),
    ("sugestoes_ia", ("pai", "analise_id", "analises_ia")),
    ("ministros", ("entidade",)),
    ("unidades_eclesiasticas", ("entidade",)),
    ("modelos_governanca_eclesiastica", ("entidade",)),
    ("logs", ("entidade_ou_usuario",)),
    ("auditoria", ("entidade_ou_usuario",)),
]

# Do sistema, não do escritório: a mesma para todos, e reconstruída pela carga
# inicial. O que o escritório usa delas sai em `referencias_globais.json`.
GLOBAIS = frozenset({
    "alembic_version",
    "execucoes_agendador",
    "fontes_juridicas",
    "fonte_versoes",
    "dispositivos",
    "vinculos_normativos",
    "monitoramentos_normativos",
    "atualizacoes_normativas",
    "naturezas_juridicas",
    "rcpj",
    "regras_rcpj",
})

# Segredos de acesso: não restauram dado nenhum, e servem para atacar.
COLUNAS_EXCLUIDAS = {
    "usuarios": {"senha_hash", "mfa_segredo", "mfa_codigos_recuperacao"},
    # Índice cego: derivado da chave de cifra, inútil fora do sistema.
    "pessoas": {"cpf_indice"},
}

LEIA_ME = """CÓPIA DE SEGURANÇA — TERCEIRO360

Este arquivo contém os dados do escritório indicado em manifesto.json, como
estavam no momento da exportação.

ATENÇÃO: CONTÉM DADOS PESSOAIS SEM CIFRA
CPF, RG, endereços e demais dados de dirigentes e associados estão legíveis
neste arquivo. Guarde-o como guardaria o próprio cadastro: em local com senha,
nunca em grupo de mensagens ou e-mail sem proteção. A exportação ficou
registrada no sistema, com o nome de quem a fez e o horário.

O QUE ESTÁ AQUI
- tabelas/       um arquivo JSON por tabela, uma linha do banco por item;
- referencias_globais.json
                 os registros do sistema que os seus dados usam (perfis e
                 modelos padrão, cartórios), para permitir a restauração;
- manifesto.json data, versão, quantidade de linhas e a impressão digital
                 (SHA-256) de cada arquivo, para conferir que nada foi alterado.

O QUE NÃO ESTÁ AQUI
- senhas, segredos do segundo fator e códigos de recuperação — por segurança;
- a base normativa (leis e dispositivos) — é do sistema, igual para todos.

Os documentos gerados estão em tabelas/documento_versoes.json, campo
"conteudo", em todas as versões.
"""


# ---------------------------------------------------------------- Valores


def _valor(v):
    """Converte o que sai do banco em algo que o JSON representa sem perda."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (uuid.UUID, decimal.Decimal)):
        return str(v)
    if isinstance(v, (dt.datetime, dt.date, dt.time)):
        return v.isoformat()
    if isinstance(v, enum.Enum):
        return v.value
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"base64": base64.b64encode(bytes(v)).decode()}
    if isinstance(v, dict):
        return {str(k): _valor(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_valor(x) for x in v]
    return str(v)


def _ids(linhas: list[dict]) -> set:
    return {l["id"] for l in linhas if l.get("id") is not None}


# -------------------------------------------------------------- Exportação


def _ler(db: Session, nome: str, escopo: tuple, cliente_id, exportadas: dict) -> list[dict]:
    tabela = Base.metadata.tables[nome]
    tipo = escopo[0]

    if tipo == "proprio":
        filtro = tabela.c.id == cliente_id
    elif tipo == "cliente":
        filtro = tabela.c.cliente_id == cliente_id
    elif tipo == "entidade":
        filtro = tabela.c.entidade_id.in_(exportadas["entidades"])
    elif tipo == "pai":
        _, coluna, pai = escopo
        filtro = tabela.c[coluna].in_(exportadas[pai])
    elif tipo == "entidade_ou_usuario":
        filtro = or_(
            tabela.c.entidade_id.in_(exportadas["entidades"]),
            tabela.c.usuario_id.in_(exportadas["usuarios"]),
        )
    else:  # pragma: no cover — erro de programação, não de dado
        raise ValueError(f"escopo desconhecido para {nome}: {escopo}")

    excluidas = COLUNAS_EXCLUIDAS.get(nome, set())
    colunas = [c for c in tabela.columns if c.name not in excluidas]
    # Lido pela tabela, e não pelo modelo, mas com os tipos das colunas: é o
    # tipo `DadoCifrado` que decifra CPF e RG na leitura.
    ordem = [tabela.c.id] if "id" in tabela.c else []
    linhas = db.execute(select(*colunas).where(filtro).order_by(*ordem)).mappings().all()
    return [dict(l) for l in linhas]


def _referencias_globais(db: Session, dados: dict[str, list[dict]]) -> dict:
    """Os registros do sistema que os dados do escritório citam por id.

    Ids são gerados em cada instalação. Restaurar noutra instalação exige
    reencontrar "o perfil ADMINISTRADOR" ou "o modelo ATA_ELEICAO_PADRAO" pelo
    código — e é isso que este arquivo guarda.
    """
    perfis = Base.metadata.tables["perfis"]
    templates = Base.metadata.tables["templates"]
    rcpj = Base.metadata.tables["rcpj"]

    ids_perfis = {l["perfil_id"] for l in dados["usuario_perfis"]}
    ids_templates = {l["template_id"] for l in dados["documento_versoes"] if l.get("template_id")}
    ids_rcpj = {
        l["rcpj_id"]
        for t in ("entidades", "protocolos", "checklists", "estatuto_versoes")
        for l in dados[t]
        if l.get("rcpj_id")
    }

    def buscar(tabela, ids, *colunas):
        if not ids:
            return []
        consulta = select(*(tabela.c[c] for c in colunas)).where(tabela.c.id.in_(ids))
        return [dict(l) for l in db.execute(consulta).mappings().all()]

    return {
        "perfis": buscar(perfis, ids_perfis, "id", "codigo", "nome"),
        "templates": buscar(templates, ids_templates, "id", "codigo", "nome", "versao"),
        "rcpj": buscar(rcpj, ids_rcpj, "id", "nome", "uf", "municipio"),
    }


def _migracao(db: Session) -> str | None:
    try:
        return db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:  # banco criado sem Alembic (testes)
        db.rollback()
        return None


def _json(obj) -> bytes:
    return json.dumps(_valor(obj), ensure_ascii=False, indent=1).encode("utf-8")


def nome_do_arquivo(nome_escritorio: str, quando: dt.datetime) -> str:
    # Tira o acento antes de filtrar: sem isso "Escritório" virava "escrit-rio",
    # porque o "ó" inteiro caía no filtro em vez de virar "o".
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", nome_escritorio)
        if unicodedata.category(c) != "Mn"
    )
    base = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")[:40] or "escritorio"
    return f"terceiro360-copia-{base}-{quando:%Y-%m-%d-%H%M}.zip"


def exportar(db: Session, cliente_id: uuid.UUID, autor: dict) -> tuple[bytes, dict]:
    """Monta o ZIP da cópia. Devolve o arquivo e o manifesto."""
    exportadas: dict[str, set] = {}
    dados: dict[str, list[dict]] = {}

    for nome, escopo in ESCOPO:
        linhas = _ler(db, nome, escopo, cliente_id, exportadas)
        dados[nome] = linhas
        exportadas[nome] = _ids(linhas)

    quando = agora()
    escritorio = dados["clientes"][0] if dados["clientes"] else {"id": cliente_id, "nome": ""}

    arquivos: dict[str, bytes] = {
        f"tabelas/{nome}.json": _json(linhas) for nome, linhas in dados.items()
    }
    arquivos["referencias_globais.json"] = _json(_referencias_globais(db, dados))

    manifesto = {
        "sistema": "TERCEIRO360",
        "formato_versao": FORMATO_VERSAO,
        "gerado_em": quando,
        "gerado_por": autor,
        "escritorio": {"id": escritorio["id"], "nome": escritorio.get("nome")},
        "migracao_do_banco": _migracao(db),
        "dados_pessoais_decifrados": True,
        "arquivos": {
            caminho: {
                "linhas": len(dados[caminho[8:-5]]) if caminho.startswith("tabelas/") else None,
                "sha256": hashlib.sha256(conteudo).hexdigest(),
            }
            for caminho, conteudo in sorted(arquivos.items())
        },
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("LEIA-ME.txt", LEIA_ME)
        zf.writestr("manifesto.json", _json(manifesto))
        for caminho, conteudo in sorted(arquivos.items()):
            zf.writestr(caminho, conteudo)

    return buffer.getvalue(), _valor(manifesto)
