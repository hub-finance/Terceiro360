"""TERCEIRO360 — Inteligência e automação para o Terceiro Setor.

Ponto de entrada da aplicação.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.seguranca_http import CabecalhosSeguranca, FreioDeRequisicoes
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.enums import Modulo

logger = logging.getLogger("terceiro360")

DESCRICAO = """
**TERCEIRO360** — ERP jurídico-societário do Terceiro Setor.

Motor de atos jurídicos, societários, registrais e documentais para associações,
fundações, OSCs, OSCIPs, institutos, igrejas e organizações religiosas.

### Princípio de operação

    CADASTRAR → ANALISAR → PARAMETRIZAR → VALIDAR → ALERTAR → GERAR
    → REVISAR → ASSINAR → PROTOCOLAR → ARQUIVAR → CONTROLAR PRAZOS

### Regra de não invenção

O sistema não inventa lei, artigo, prazo, exigência de cartório nem dado
cadastral. Quando falta informação, responde **DADO NÃO INFORMADO**; quando há
dúvida, **VALIDAÇÃO NECESSÁRIA**; quando as fontes se contradizem,
**INCONSISTÊNCIA IDENTIFICADA**.

### Responsabilidade profissional

A automação auxilia na preparação, organização, validação e geração de
documentos, mas **não substitui a análise profissional** quando esta for
necessária.
"""

# Em produção a documentação interativa fica fechada. Ela lista cada rota, cada
# parâmetro e cada formato de resposta — é o mapa que um atacante levaria uma
# semana para levantar sozinho, servido de graça.
_publica = not settings.em_producao

app = FastAPI(
    title=settings.app_name,
    description=DESCRICAO,
    summary=settings.app_slogan,
    version="0.1.0",
    docs_url="/docs" if _publica else None,
    redoc_url="/redoc" if _publica else None,
    openapi_url="/openapi.json" if _publica else None,
)

# A ordem importa: o middleware registrado por último é o primeiro a ver a
# requisição. O freio vem antes de tudo, para que uma enxurrada não chegue a
# abrir conexão com o banco.
app.add_middleware(CabecalhosSeguranca)
app.add_middleware(
    FreioDeRequisicoes,
    limite=settings.limite_requisicoes_minuto,
    janela_segundos=60,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origens,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def erro_inesperado(request: Request, exc: Exception):
    """Falha inesperada não vira 'ato aprovado': vira erro explícito."""
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "erro": "Falha interna ao processar a solicitação.",
            "detalhe": str(exc) if settings.debug else None,
            "orientacao": "Nenhuma conclusão jurídica foi produzida nesta requisição. "
                          "Repita a operação ou acione o suporte.",
        },
    )


@app.get("/", tags=["Sistema"])
def raiz():
    return {
        "sistema": settings.app_name,
        "slogan": settings.app_slogan,
        "versao": app.version,
        "modulos": [
            {"codigo": Modulo.JURIDICO.value, "nome": "TERCEIRO360 JURÍDICO",
             "descricao": "Atos societários, estatutos, assembleias, atas e RCPJ."},
            {"codigo": Modulo.GOVERNANCA.value, "nome": "TERCEIRO360 GOVERNANÇA",
             "descricao": "Mandatos, órgãos, compliance e indicadores."},
            {"codigo": Modulo.DOCUMENTOS.value, "nome": "TERCEIRO360 DOCUMENTOS",
             "descricao": "Gestão e geração documental."},
            {"codigo": Modulo.IGREJAS.value, "nome": "TERCEIRO360 IGREJAS",
             "descricao": "Núcleo especializado para igrejas e organizações religiosas."},
            {"codigo": Modulo.IA.value, "nome": "TERCEIRO360 IA",
             "descricao": "Análise de estatutos, documentos e conformidade."},
        ],
        "modulos_reservados": [
            {"codigo": "TERCEIRO360_CONTABIL", "nome": "TERCEIRO360 CONTÁBIL",
             "situacao": "Especificado e reservado para fase posterior.",
             "especificacao": "docs/reservado/modulo-contabil.md"},
        ],
        "documentacao": "/docs",
    }


@app.get("/saude", tags=["Sistema"])
def saude():
    from sqlalchemy import text

    from app.core.db import engine

    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        banco = "ok"
    except Exception as exc:  # noqa: BLE001
        banco = f"indisponível: {exc}"
    return {"status": "ok" if banco == "ok" else "degradado", "banco": banco,
            "ambiente": settings.environment}


app.include_router(api_router, prefix=settings.api_prefix)
