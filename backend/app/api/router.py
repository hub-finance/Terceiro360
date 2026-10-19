"""Agregador das rotas da API."""
from fastapi import APIRouter

from app.api.rotas import (
    agendador,
    auth,
    backup,
    cadastros,
    documentos,
    entidades,
    estatutos,
    eventos,
    ia,
    igrejas,
    importacao,
    normativo,
    registral,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(agendador.router)
api_router.include_router(entidades.router)
api_router.include_router(estatutos.router)
api_router.include_router(cadastros.router)
api_router.include_router(eventos.router)
api_router.include_router(documentos.router)
api_router.include_router(registral.router)
api_router.include_router(normativo.router)
api_router.include_router(igrejas.router)
api_router.include_router(ia.router)
api_router.include_router(backup.router)
api_router.include_router(importacao.router)
