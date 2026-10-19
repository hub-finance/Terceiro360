"""Importação de ata antiga (roteiro comercial, item 1.1).

Em dois passos, de propósito: `ler` não grava nada — devolve o que foi lido,
com o trecho de cada coisa, para a pessoa conferir e corrigir na tela; só
`gravar` toca o cadastro, e só com o que ela confirmou.
"""
from __future__ import annotations

import datetime as dt
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Sessao, entidade_do_escopo, exigir
from app.core.security import tem_permissao
from app.modules.entidades.models import Entidade
from app.modules.importacao.ata import ler_ata
from app.modules.importacao.servico import gravar

router = APIRouter(prefix="/entidades/{entidade_id}/importar-ata", tags=["Importação de ata"])

LIMITE_TEXTO = 200_000      # caracteres — uma ata longa tem uns 20 mil
LIMITE_ARQUIVO = 10 * 1024 * 1024


class TextoIn(BaseModel):
    texto: str = Field(min_length=20, max_length=LIMITE_TEXTO)


@router.post("/ler")
def ler_texto(
    dados: TextoIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("juridico:pessoa:criar")),
):
    return ler_ata(dados.texto).para_json()


def _texto_do_arquivo(nome: str, conteudo: bytes) -> str:
    nome = (nome or "").lower()
    if nome.endswith(".docx"):
        from docx import Document

        documento = Document(io.BytesIO(conteudo))
        return "\n".join(p.text for p in documento.paragraphs)
    if nome.endswith(".pdf"):
        from pypdf import PdfReader

        texto = "\n".join((pagina.extract_text() or "") for pagina in PdfReader(io.BytesIO(conteudo)).pages)
        if len(texto.strip()) < 50:
            # PDF sem texto dentro é foto de papel: não há o que ler sem
            # reconhecimento de imagem, e dizer isso é melhor que "nada achado".
            raise HTTPException(
                422,
                "Este PDF é uma imagem escaneada, sem texto dentro. A leitura de "
                "documento escaneado ainda não está disponível — cole o texto da ata, "
                "ou envie a versão em Word.",
            )
        return texto
    if nome.endswith(".txt"):
        return conteudo.decode("utf-8", errors="replace")
    if nome.endswith((".jpg", ".jpeg", ".png", ".heic", ".webp")):
        raise HTTPException(
            415,
            "Foto de ata ainda não é lida — essa leitura depende de reconhecimento de "
            "imagem, que está no roteiro. Por enquanto, cole o texto ou envie Word ou PDF.",
        )
    raise HTTPException(415, "Envie a ata em Word (.docx), PDF ou texto (.txt).")


@router.post("/ler-arquivo")
async def ler_arquivo(
    arquivo: UploadFile = File(...),
    entidade: Entidade = Depends(entidade_do_escopo),
    _: Sessao = Depends(exigir("juridico:pessoa:criar")),
):
    conteudo = await arquivo.read(LIMITE_ARQUIVO + 1)
    if len(conteudo) > LIMITE_ARQUIVO:
        raise HTTPException(413, "Arquivo acima de 10 MB.")
    try:
        texto = _texto_do_arquivo(arquivo.filename, conteudo)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "Não foi possível abrir o arquivo. Ele pode estar corrompido.")
    return ler_ata(texto[:LIMITE_TEXTO]).para_json()


class PessoaIn(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    cargo: str | None = Field(default=None, max_length=120)
    cpf: str | None = None
    rg: str | None = None
    orgao_expedidor: str | None = Field(default=None, max_length=20)
    nacionalidade: str | None = Field(default=None, max_length=60)
    estado_civil: str | None = Field(default=None, max_length=40)
    profissao: str | None = Field(default=None, max_length=100)
    endereco: str | None = Field(default=None, max_length=300)
    cep: str | None = Field(default=None, max_length=9)


class GravarIn(BaseModel):
    pessoas: list[PessoaIn] = Field(max_length=60)
    registrar_diretoria: bool = False
    mandato_inicio: dt.date | None = None
    mandato_fim: dt.date | None = None


@router.post("/gravar")
def gravar_importacao(
    dados: GravarIn,
    entidade: Entidade = Depends(entidade_do_escopo),
    sessao: Sessao = Depends(exigir("juridico:pessoa:criar")),
    db: Session = Depends(get_db),
):
    if dados.registrar_diretoria and not (
        tem_permissao(sessao.permissoes, "juridico:mandato:criar")
        and tem_permissao(sessao.permissoes, "juridico:orgao:criar")
    ):
        raise HTTPException(403, "Seu perfil não pode registrar diretoria.")
    resultado = gravar(
        db, entidade, [p.model_dump() for p in dados.pessoas],
        dados.registrar_diretoria, dados.mandato_inicio, dados.mandato_fim,
    )
    return resultado.__dict__
