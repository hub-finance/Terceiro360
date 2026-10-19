"""Grava no cadastro o que foi lido de uma ata antiga — depois de conferido.

Duas garantias, porque é aqui que a leitura vira dado:

**Nada já cadastrado é sobrescrito.** A pessoa que já existe (pelo CPF, ou pelo
nome quando não há CPF) só tem preenchidos os campos vazios. Onde a ata diz uma
coisa e o cadastro outra, a diferença é devolvida para a pessoa decidir — o
cadastro pode estar mais atualizado do que uma ata de três anos atrás.

**Gravar duas vezes não duplica.** Pessoa, cargo e mandato são reencontrados
antes de criados. Reimportar a mesma ata depois de corrigir um campo não deixa
duas Marias nem dois mandatos iguais.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cifra import indice
from app.core.enums import TipoOrgao
from app.modules.entidades.models import Entidade
from app.modules.juridico.models import Cargo, Mandato, MandatoMembro, Orgao, Pessoa

CAMPOS = ("cpf", "rg", "orgao_expedidor", "nacionalidade", "estado_civil", "profissao",
          "logradouro", "numero", "complemento", "bairro", "municipio", "uf", "cep")


def _comparavel(valor) -> str:
    texto = unicodedata.normalize("NFD", str(valor or ""))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s.\-/]+", "", texto.lower())


def partir_endereco(texto: str | None) -> dict:
    """'Rua das Flores, nº 120, apto 3, Bairro Centro, Aracaju/SE' em partes.

    O cadastro guarda o endereço em campos, e é deles que os documentos montam
    a linha de endereço. O que não se consegue separar com segurança fica
    inteiro no logradouro — melhor um campo carregado do que um dado perdido.
    """
    if not texto:
        return {}
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    saida: dict = {}
    restantes = []
    for parte in partes:
        if re.fullmatch(r"(?:n[º°o]\.?|n[uú]mero)\s*(\S+)", parte, re.I):
            saida["numero"] = re.sub(r"^(?:n[º°o]\.?|n[uú]mero)\s*", "", parte, flags=re.I)
        elif m := re.fullmatch(r"(?:bairro|b\.)\s+(.+)", parte, re.I):
            saida["bairro"] = m.group(1)
        elif m := re.fullmatch(r"(.+?)\s*[/-]\s*([A-Z]{2})", parte):
            saida["municipio"], saida["uf"] = m.group(1), m.group(2)
        elif re.match(r"(?:apto|apartamento|ap\.|casa|bloco|sala|lote|quadra|qd\.?)\b", parte, re.I):
            saida["complemento"] = parte
        else:
            restantes.append(parte)
    if restantes:
        saida["logradouro"] = restantes[0]
        # Sobrou um trecho sem rótulo depois do logradouro: costuma ser o
        # bairro escrito sem a palavra "Bairro".
        if len(restantes) > 1 and "bairro" not in saida:
            saida["bairro"] = restantes[1]
    return saida


@dataclass
class Resultado:
    pessoas_criadas: list[str] = field(default_factory=list)
    pessoas_completadas: list[dict] = field(default_factory=list)
    conflitos: list[dict] = field(default_factory=list)
    mandatos: list[dict] = field(default_factory=list)
    membros_incluidos: int = 0
    avisos: list[str] = field(default_factory=list)


def _achar_pessoa(db: Session, cliente_id: uuid.UUID, dados: dict) -> Pessoa | None:
    if dados.get("cpf"):
        encontrada = db.scalar(
            select(Pessoa).where(Pessoa.cliente_id == cliente_id,
                                 Pessoa.cpf_indice == indice(dados["cpf"]))
        )
        if encontrada:
            return encontrada
    # Sem CPF (ou CPF ainda não cadastrado), o nome exato evita a duplicata
    # mais comum: a mesma ata importada duas vezes.
    return db.scalar(
        select(Pessoa).where(Pessoa.cliente_id == cliente_id, Pessoa.nome == dados["nome"])
    )


def _gravar_pessoa(db: Session, cliente_id: uuid.UUID, dados: dict, r: Resultado) -> Pessoa:
    lidos = {**{k: dados.get(k) for k in CAMPOS}, **partir_endereco(dados.get("endereco"))}
    lidos = {k: (v.strip() if isinstance(v, str) else v) for k, v in lidos.items() if v}

    pessoa = _achar_pessoa(db, cliente_id, dados)
    if pessoa is None:
        pessoa = Pessoa(cliente_id=cliente_id, nome=dados["nome"],
                        base_legal_tratamento="EXERCICIO_REGULAR_DE_DIREITOS", **lidos)
        db.add(pessoa)
        db.flush()
        r.pessoas_criadas.append(pessoa.nome)
        return pessoa

    preenchidos = []
    for campo, valor in lidos.items():
        atual = getattr(pessoa, campo)
        if not atual:
            setattr(pessoa, campo, valor)
            preenchidos.append(campo)
        elif _comparavel(atual) != _comparavel(valor):
            r.conflitos.append({
                "pessoa": pessoa.nome, "campo": campo,
                "no_cadastro": atual, "na_ata": valor,
            })
    if preenchidos:
        db.add(pessoa)
        r.pessoas_completadas.append({"pessoa": pessoa.nome, "campos": preenchidos})
    return pessoa


def _orgao_do_cargo(cargo: str) -> tuple[str, str, TipoOrgao]:
    """Conselho fiscal tem mandato e órgão próprios; o resto é diretoria."""
    if re.search(r"conselh|fiscal", cargo, re.I):
        return "CONSELHO_FISCAL", "Conselho Fiscal", TipoOrgao.FISCALIZADOR
    return "DIRETORIA", "Diretoria", TipoOrgao.EXECUTIVO


def _codigo(nome: str) -> str:
    texto = unicodedata.normalize("NFD", nome)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\b(\d)\s*[ºo°ª]", r"\1", texto)
    return re.sub(r"[^A-Z0-9]+", "_", texto.upper()).strip("_")


def gravar(
    db: Session,
    entidade: Entidade,
    pessoas: list[dict],
    registrar_diretoria: bool,
    mandato_inicio: dt.date | None,
    mandato_fim: dt.date | None,
) -> Resultado:
    r = Resultado()
    gravadas = []
    for dados in pessoas:
        if not (dados.get("nome") or "").strip():
            continue
        dados = {**dados, "nome": dados["nome"].strip()}
        gravadas.append((_gravar_pessoa(db, entidade.cliente_id, dados, r), dados.get("cargo")))

    if not registrar_diretoria:
        db.commit()
        return r
    if not (mandato_inicio and mandato_fim):
        r.avisos.append("A diretoria não foi registrada: faltam as datas de início e fim do mandato.")
        db.commit()
        return r
    if mandato_fim < mandato_inicio:
        r.avisos.append("A diretoria não foi registrada: o fim do mandato é anterior ao início.")
        db.commit()
        return r

    mandatos: dict[str, Mandato] = {}
    for pessoa, cargo_nome in gravadas:
        if not cargo_nome:
            r.avisos.append(f"{pessoa.nome} não entrou na diretoria: cargo não informado.")
            continue
        codigo_orgao, nome_orgao, tipo_orgao = _orgao_do_cargo(cargo_nome)
        orgao = db.scalar(select(Orgao).where(Orgao.entidade_id == entidade.id,
                                              Orgao.codigo == codigo_orgao))
        if orgao is None:
            orgao = Orgao(entidade_id=entidade.id, nome=nome_orgao, codigo=codigo_orgao,
                          tipo=tipo_orgao)
            db.add(orgao)
            db.flush()

        codigo_cargo = _codigo(cargo_nome)
        cargo = next((c for c in db.scalars(select(Cargo).where(Cargo.orgao_id == orgao.id))
                      if c.codigo == codigo_cargo or _comparavel(c.nome) == _comparavel(cargo_nome)),
                     None)
        if cargo is None:
            cargo = Cargo(orgao_id=orgao.id, nome=cargo_nome, codigo=codigo_cargo)
            db.add(cargo)
            db.flush()

        mandato = mandatos.get(codigo_orgao) or db.scalar(
            select(Mandato).where(Mandato.entidade_id == entidade.id, Mandato.orgao_id == orgao.id,
                                  Mandato.data_inicio == mandato_inicio,
                                  Mandato.data_fim == mandato_fim)
        )
        if mandato is None:
            mandato = Mandato(entidade_id=entidade.id, orgao_id=orgao.id,
                              designacao=f"GESTÃO {mandato_inicio.year}–{mandato_fim.year}",
                              data_inicio=mandato_inicio, data_fim=mandato_fim)
            db.add(mandato)
            db.flush()
            r.mandatos.append({"orgao": nome_orgao, "designacao": mandato.designacao, "criado": True})
        elif codigo_orgao not in mandatos:
            r.mandatos.append({"orgao": nome_orgao, "designacao": mandato.designacao, "criado": False})
        mandatos[codigo_orgao] = mandato

        ja_membro = db.scalar(select(MandatoMembro).where(
            MandatoMembro.mandato_id == mandato.id, MandatoMembro.pessoa_id == pessoa.id,
            MandatoMembro.cargo_id == cargo.id))
        if ja_membro is None:
            db.add(MandatoMembro(mandato_id=mandato.id, pessoa_id=pessoa.id, cargo_id=cargo.id,
                                 data_inicio=mandato_inicio, data_fim=mandato_fim))
            r.membros_incluidos += 1

    db.commit()
    return r
